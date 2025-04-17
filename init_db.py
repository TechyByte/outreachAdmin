import os
import sys

from flask import Flask
from werkzeug.security import generate_password_hash

from routes.enrolment import enroll
from models import db, User, School, Program, TemplateCourse, TemplateEvent, TemplateAgendaItem, Course, Event, \
    AgendaItem, Location

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def check_database():
    """Ensures the database is created and initialized before running the app."""
    if not os.path.exists("instance/database.db"):
        print("📦 No database found. Initializing...")
        with app.app_context():
            initialize_database()
    else:
        with app.app_context():
            inspector = db.engine.inspect(db.engine)
            if not inspector.has_table("school"):
                print("⚠️ Table 'school' not found. Recreating database...")
                initialize_database()


# noinspection PyArgumentList
def initialize_database():
    """Drops existing tables, recreates them, and adds example template and live data."""
    with app.app_context():
        if os.path.exists("instance/database.db"):
            if "--noinput" not in sys.argv:
                user_input = input("⚠️ Database already exists. Overwrite it? (yes/no): ").strip().lower()
                if user_input not in ["yes", "y"]:
                    print("✅ Keeping existing database. No changes made.")
                    return
            print("🛠 Dropping existing tables...")
            db.drop_all()

        print("📦 Creating new tables...")
        db.create_all()

        # Add Example Schools (first, since users will reference them)
        print("🏫 Adding example schools...")
        school1 = School(name="Springfield High", contact_name="John Doe", contact_email="john@school.com",
                         contact_phone="123456789")
        school2 = School(name="Riverdale Academy", contact_name="Jane Smith", contact_email="jane@school.com",
                         contact_phone="987654321")
        db.session.add_all([school1, school2])
        db.session.commit()

        # Add Example Users (with school_id assigned)
        print("👤 Adding example users...")
        admin = User(username="admin", password=generate_password_hash("admin123"), configured_role="admin")
        school_contact1 = User(username="john_doe", password=generate_password_hash("password"), configured_role="school_contact",
                               school_id=school1.id)
        school_contact2 = User(username="jane_smith", password=generate_password_hash("password"),
                               configured_role="school_contact", school_id=school2.id)

        user1 = User(username="user", password=generate_password_hash("password"))

        db.session.add_all([admin, school_contact1, school_contact2, user1])
        db.session.commit()

        # Add Example Programs
        print("📚 Adding example programs...")
        program1 = Program(name="STEM Education Program")
        program2 = Program(name="Business & Economics Program")
        db.session.add_all([program1, program2])
        db.session.commit()

        # Add Template Courses
        print("📖 Adding template courses...")
        template_course1 = TemplateCourse(name="Mathematics")
        template_course2 = TemplateCourse(name="Physics")
        template_course3 = TemplateCourse(name="Finance 101")
        db.session.add_all([template_course1, template_course2, template_course3])
        db.session.commit()

        # Assign Template Courses to Programs (Many-to-Many)
        print("🔗 Assigning template courses to programs...")
        program1.template_courses.append(template_course1)  # STEM gets Math
        program1.template_courses.append(template_course2)  # STEM gets Physics
        program2.template_courses.append(template_course3)  # Business gets Finance
        db.session.commit()

        # Add Example Template Events
        print("📅 Adding example template events...")
        template_event1 = TemplateEvent(name="Mathematics Quiz", template_course_id=template_course1.id)
        template_event2 = TemplateEvent(name="Physics Lab", template_course_id=template_course2.id)
        template_event3 = TemplateEvent(name="Finance Workshop", template_course_id=template_course3.id)
        db.session.add_all([template_event1, template_event2, template_event3])
        db.session.commit()

        # Add Example Template Agenda Items
        print("📝 Adding example template agenda items...")
        agenda_item1 = TemplateAgendaItem(title="Quiz Preparation", template_event_id=template_event1.id)
        agenda_item2 = TemplateAgendaItem(title="Lab Setup", template_event_id=template_event2.id)
        agenda_item3 = TemplateAgendaItem(title="Workshop Materials", template_event_id=template_event3.id)
        db.session.add_all([agenda_item1, agenda_item2, agenda_item3])
        db.session.commit()

        # Add Example Live Courses
        print("📅 Enrolling school in program...")
        school1.programs.append(program1)

        # Copy selected template courses
        new_course = Course(name=template_course1.name, program_id=program1.id, school_id=school1.id)
        db.session.add(new_course)
        db.session.commit()

        # Copy events
        template_events = TemplateEvent.query.filter_by(template_course_id=template_course1.id).all()
        for template_event in template_events:
            new_event = Event(name=template_event.name, course_id=new_course.id, school_id=school1.id)
            db.session.add(new_event)
            db.session.commit()

            # Copy agenda items
            template_agendas = TemplateAgendaItem.query.filter_by(template_event_id=template_event.id).all()
            for template_agenda in template_agendas:
                new_agenda = AgendaItem(title=template_agenda.title,
                                        event_id=new_event.id,
                                        lecturer_id=template_agenda.lecturer_id,
                                        time=template_agenda.time,
                                        duration=template_agenda.duration,
                                        description=template_agenda.description)
                db.session.add(new_agenda)

        db.session.commit()

        # Add example locations
        print("📍 Adding example locations...")
        location1 = Location(name="BWC-CH")
        location2 = Location(name="UHB-QE")
        location3 = Location(name="School")
        db.session.add_all([location1, location2, location3])
        db.session.commit()

        print("✅ Database initialized successfully with example data!")


if __name__ == '__main__':
    initialize_database()
