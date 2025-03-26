from flask import Flask
from models import db, User, School, Program, TemplateCourse, TemplateEvent, TemplateAgendaItem, Course, Event, AgendaItem, Pupil
import os
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def initialize_database():
    """Drops existing tables, recreates them, and adds example template and live data."""
    with app.app_context():
        if os.path.exists("database.db"):
            user_input = input("⚠️ Database already exists. Overwrite it? (yes/no): ").strip().lower()
            if user_input not in ["yes", "y"]:
                print("✅ Keeping existing database. No changes made.")
                return
            print("🛠 Dropping existing tables...")
            db.drop_all()

        print("📦 Creating new tables...")
        db.create_all()

        # Add Example Users
        print("👤 Adding example users...")
        admin = User(username="admin", password=generate_password_hash("admin123"), role="admin")
        school_contact1 = User(username="john_doe", password=generate_password_hash("password"), role="school_contact")
        school_contact2 = User(username="jane_smith", password=generate_password_hash("password"), role="school_contact")

        db.session.add_all([admin, school_contact1, school_contact2])
        db.session.commit()

        # Add Example Schools
        print("🏫 Adding example schools...")
        school1 = School(name="Springfield High", contact_name="John Doe", contact_email="john@school.com", contact_phone="123456789", user_id=school_contact1.id)
        school2 = School(name="Riverdale Academy", contact_name="Jane Smith", contact_email="jane@school.com", contact_phone="987654321", user_id=school_contact2.id)
        db.session.add_all([school1, school2])
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

        # Create Live Courses (Based on Templates)
        print("🎓 Creating live courses from templates...")
        course1 = Course(name="Mathematics", program_id=program1.id, school_id=school1.id)
        course2 = Course(name="Physics", program_id=program1.id, school_id=school1.id)
        course3 = Course(name="Finance 101", program_id=program2.id, school_id=school2.id)
        db.session.add_all([course1, course2, course3])
        db.session.commit()

        # Add Example Pupils
        print("👩‍🎓 Adding example pupils...")
        pupil1 = Pupil(name="Alice Johnson", school_id=school1.id)
        pupil2 = Pupil(name="Bob Smith", school_id=school1.id)
        pupil3 = Pupil(name="Charlie Brown", school_id=school2.id)
        db.session.add_all([pupil1, pupil2, pupil3])
        db.session.commit()

        # Enroll Pupils in Courses (Many-to-Many Relationship)
        print("🎓 Enrolling pupils into courses...")
        pupil1.courses.append(course1)  # Alice in Math
        pupil1.courses.append(course2)  # Alice in Physics
        pupil2.courses.append(course1)  # Bob in Math
        pupil3.courses.append(course3)  # Charlie in Finance
        db.session.commit()


        # Add Example Template Events
        print("📅 Adding example template events...")
        template_event1 = TemplateEvent(name="Mathematics Quiz", description="A quiz on basic math concepts")
        template_event2 = TemplateEvent(name="Physics Lab", description="A lab session on Newton's Laws")
        template_event3 = TemplateEvent(name="Finance Workshop", description="A workshop on personal finance")
        db.session.add_all([template_event1, template_event2, template_event3])
        db.session.commit()


        # Assign Template Events to Template Courses (Many-to-Many)
        print("🔗 Assigning template events to template courses...")
        template_course1.template_events.append(template_event1)  # Math gets Quiz
        template_course2.template_events.append(template_event2)  # Physics gets Lab
        template_course3.template_events.append(template_event3)  # Finance gets Workshop
        db.session.commit()


        # Create Live Events (Based on Templates)
        print("📅 Creating live events from templates...")
        event1 = Event(name="Mathematics Quiz", course_id=course1.id, date="2021-12-01")
        event2 = Event(name="Physics Lab", course_id=course2.id, date="2021-12-02")
        event3 = Event(name="Finance Workshop", course_id=course3.id, date="2021-12-03")
        db.session.add_all([event1, event2, event3])
        db.session.commit()


        print("✅ Database initialized successfully with example data!")

if __name__ == '__main__':
    initialize_database()
