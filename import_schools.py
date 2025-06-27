import csv
import os.path

from fuzzywuzzy import fuzz

from app import app
from models import db, School

extra_schools_file = "../schools_extra.csv"


with app.app_context():
    schools = [
        {
            "URN": school.urn,
            "LA (code)": school.la_code,
            "LA (name)": school.la_name,
            "EstablishmentNumber": school.establishment_number,
            "EstablishmentName": school.name,
            "TypeOfEstablishment (name)": school.type_of_establishment,
            "PhaseOfEducation (name)": school.phase_of_education,
            "StatutoryLowAge": school.statutory_low_age,
            "StatutoryHighAge": school.statutory_high_age,
            "Street": school.street,
            "Town": school.town,
            "Postcode": school.postcode,
            "TelephoneNum": school.telephone,
            "HeadFirstName": school.head_name.split()[0] if school.head_name else None,
            "HeadLastName": school.head_name.split()[1] if school.head_name and len(school.head_name.split()) > 1 else None,
            "SchoolWebsite": school.school_website,
            "NumberOfPupils": school.number_of_pupils,
            "NumberOfBoys": school.number_of_boys,
            "NumberOfGirls": school.number_of_girls,
            "PercentageFSM": school.percentage_fsm,
            "HeadPreferredJobTitle": school.head_preferred_job_title,
            "NurseryProvision (name)": school.nursery_provision,
            "EstablishmentStatus (name)": school.establishment_status,
            "Diocese (name)": school.diocese,
            "Gender (name)": school.gender,
            "SchoolCapacity": school.school_capacity,
            "AdmissionsPolicy (name)": school.admissions_policy,
            "Locality": school.locality,
            "Address3": school.address3,
            "ParliamentaryConstituency (name)": school.parliamentary_constituency,
            "Easting": school.easting,
            "Northing": school.northing,
            "id": school.id
        }
        for school in db.session.query(School).all()
    ]


with open(extra_schools_file, mode='r', encoding='latin1') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        #print(row['URN'])
        # if row['LA (name)'] == "Birmingham" and row['EstablishmentStatus (name)'] == "Open" and row[
        #     'PhaseOfEducation (name)'] != "Nursery":
        #     school = School(
        #         urn=row['URN'],
        #         la_code=row['LA (code)'],
        #         la_name=row['LA (name)'],
        #         establishment_number=row['EstablishmentNumber'],
        #         name=row['EstablishmentName'],
        #         type_of_establishment=row['TypeOfEstablishment (name)'],
        #         phase_of_education=row['PhaseOfEducation (name)'],
        #         statutory_low_age=row['StatutoryLowAge'],
        #         statutory_high_age=row['StatutoryHighAge'],
        #         street=row['Street'],
        #         town=row['Town'],
        #         postcode=row['Postcode'],
        #         telephone=row['TelephoneNum'],
        #         head_name=f"{row['HeadFirstName']} {row['HeadLastName']}",
        #         school_website=row['SchoolWebsite'],
        #         number_of_pupils=row['NumberOfPupils'],
        #         number_of_boys=row['NumberOfBoys'],
        #         number_of_girls=row['NumberOfGirls'],
        #         percentage_fsm=row['PercentageFSM'] if row['PercentageFSM'] != "" else None,
        #         head_preferred_job_title=row['HeadPreferredJobTitle'],
        #         nursery_provision=row['NurseryProvision (name)'],
        #         establishment_status=row['EstablishmentStatus (name)'],
        #         diocese=row['Diocese (name)'],
        #         gender=row['Gender (name)'],
        #         school_capacity=row['SchoolCapacity'],
        #         admissions_policy=row['AdmissionsPolicy (name)'],
        #         locality=row['Locality'],
        #         address3=row['Address3'],
        #         parliamentary_constituency=row['ParliamentaryConstituency (name)'],
        #         easting=row['Easting'],
        #         northing=row['Northing']
        #
        #     )

        best_match = None
        second_best_match = None
        highest_score = 0

        for school in schools:
            name_score = fuzz.token_sort_ratio(row['School name'], school['EstablishmentName'])
            constituency_score = fuzz.token_sort_ratio(row['Constituency'],
                                                       school['ParliamentaryConstituency (name)'])
            category_score = fuzz.token_sort_ratio(row['Type'],
                                                   school['TypeOfEstablishment (name)'])
            street_score = fuzz.token_sort_ratio(row['Street'], school['Street'])
            town_score = fuzz.token_sort_ratio(row['Town'], school['Town'])
            postcode_score = fuzz.token_sort_ratio(row['Postcode'], school['Postcode'])

            total_score = (
                    name_score * 0.50 +
                    constituency_score * 0.05 +
                    category_score * 0.30 +
                    street_score * 0.1 +
                    postcode_score * 0.05
            )

            # Update the best match if the current score is higher
            if total_score > highest_score:
                highest_score = total_score
                second_best_match = best_match
                best_match = school

        if best_match and highest_score > 75:
            if highest_score < 90:
                pass
                #print(f"Closest match for [Amy] {row['School name']}: [Gov] {best_match['EstablishmentName']} with score {highest_score}")
                #print(f"Second best match: [Gov] {second_best_match['EstablishmentName']}")
            else:
                #print(f"Matched [Amy] {row['School name']}: [Gov] {best_match['EstablishmentName']} with score {highest_score}")

                with app.app_context():
                    if len(row['School contact']) > 1:
                        db.session.query(School).filter(School.id == best_match["id"]).update({"contact_name": row['School contact'],
                                                                                            "contact_email": row['Contact email'],
                                                                                            "contact_phone": row['Telephone number']})
                        db.session.commit()
                        print("Updated school:", best_match['EstablishmentName'])
        else:
            print(f"No match found for {row['School name']}")
