import pytest
from app import app as flask_app
from flask import url_for
from models import db, User, Program, School, TemplateCourse, TemplateEvent, TemplateAgendaItem, Course, Event, AgendaItem
from werkzeug.security import generate_password_hash
from datetime import date, time, timedelta
from routes.enrolment import enroll

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        user = User(username='admin', password=generate_password_hash('test'), configured_role='admin')
        db.session.add(user)
        db.session.commit()
        yield flask_app.test_client()
        db.drop_all()


def login(client):
    return client.post("/login", data=dict(username="admin", password="test"), follow_redirects=True)


def test_login_route(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_program_list(client):
    login(client)
    response = client.get("/programs")
    assert response.status_code == 200


def test_school_view(client):
    login(client)
    response = client.get("/schools")
    assert response.status_code == 200


def test_template_listing(client):
    login(client)
    response = client.get("/manage-templates")
    assert response.status_code == 200


def test_event_schedule_table(client):
    login(client)
    response = client.get("/schedule-table")
    assert response.status_code == 200


def test_event_schedule_calendar(client):
    login(client)
    response = client.get("/schedule-calendar")
    assert response.status_code == 200


def test_program_create_form(client):
    login(client)
    response = client.post("/programs", data=dict(name="New Program"))
    assert response.status_code == 302
    programs = Program.query.filter_by(name="New Program")
    assert programs.count() > 0


def test_rest_program_crud(client):
    login(client)

    # Create
    response = client.post("/programs", data=dict(name="REST Program"), follow_redirects=True)
    assert response.status_code in (200, 201)

    # Read
    response = client.get("/programs")
    assert response.status_code == 200
    assert b"REST Program" in response.data

    # # Update
    # program = Program.query.filter_by(name="REST Program").first()
    # response = client.put(f"/programs/{program.id}", json={"name": "Updated REST Program"})
    # assert response.status_code == 200


    # # Delete
    # response = client.delete(f"/api/programs/{program.id}")
    # assert response.status_code == 200



def test_enroll_school_on_program(client):
    login(client)

    # Create template course with event and agenda
    template_course = TemplateCourse(name="Template Outreach")
    db.session.add(template_course)
    db.session.commit()

    template_event = TemplateEvent(name="Intro Day", template_course_id=template_course.id)
    db.session.add(template_event)
    db.session.commit()

    lecturer = User(username='lecturer', password=generate_password_hash('pass'), configured_role='lecturer')
    db.session.add(lecturer)
    db.session.commit()

    agenda = TemplateAgendaItem(
        title="Welcome Talk",
        template_event_id=template_event.id,
        lecturer_id=lecturer.id,
        description="Intro to the day",
        duration=timedelta(minutes=45),
        time=time(9, 0)
    )
    db.session.add(agenda)
    db.session.commit()

    # Attach template course to a program
    program = Program(name="Health Program")
    db.session.add(program)
    program.template_courses.append(template_course)
    db.session.commit()

    # Enroll a school onto the program using the actual enroll logic
    school = School(name="Riverdale High", contact_name="Jane Doe", contact_email="jane@example.com", contact_phone="123456")
    db.session.add(school)
    db.session.commit()

    response = client.post("/enroll", data={
        "school_id": school.id,
        "program_id": program.id,
        "course_ids": [template_course.id]
    }, follow_redirects=True)

    # Assertions
    course = Course.query.filter_by(school_id=school.id, program_id=program.id).first()
    assert course is not None
    assert course.name.startswith("Template")

    events = Event.query.filter_by(course_id=course.id).all()
    assert len(events) == 1
    assert events[0].name == "Intro Day"

    agenda_items = AgendaItem.query.filter_by(event_id=events[0].id).all()
    assert len(agenda_items) == 1
    assert agenda_items[0].title == "Welcome Talk"
    assert agenda_items[0].description == "Intro to the day"
    assert agenda_items[0].lecturer.username == "lecturer"


def test_unenroll_school_from_program(client):
    login(client)

    # Create template course with event and agenda
    template_course = TemplateCourse(name="Template Outreach")
    db.session.add(template_course)
    db.session.commit()

    template_event = TemplateEvent(name="Intro Day", template_course_id=template_course.id)
    db.session.add(template_event)
    db.session.commit()

    lecturer = User(username='lecturer', password=generate_password_hash('pass'), configured_role='lecturer')
    db.session.add(lecturer)
    db.session.commit()

    agenda = TemplateAgendaItem(
        title="Welcome Talk",
        template_event_id=template_event.id,
        lecturer_id=lecturer.id,
        description="Intro to the day",
        duration=timedelta(minutes=45),
        time=time(9, 0)
    )
    db.session.add(agenda)
    db.session.commit()

    # Attach template course to a program
    program = Program(name="Health Program")
    db.session.add(program)
    program.template_courses.append(template_course)
    db.session.commit()

    # Enroll a school onto the program
    school = School(name="Riverdale High", contact_name="Jane Doe", contact_email="jane@example.com", contact_phone="123456")
    db.session.add(school)
    db.session.commit()

    client.post("/enroll", data={
        "school_id": school.id,
        "program_id": program.id,
        "course_ids": [template_course.id]
    }, follow_redirects=True)

    # Unenroll the school from the program
    response = client.post("/unenroll", data={
        "school_id": school.id,
        "program_id": program.id
    }, follow_redirects=True)

    # Assertions
    assert response.status_code == 200
    assert program not in school.programs

    courses = Course.query.filter_by(school_id=school.id, program_id=program.id).all()
    assert len(courses) == 0

    events = Event.query.filter_by(school_id=school.id).all()
    assert len(events) == 0

    agenda_items = AgendaItem.query.filter_by(event_id=None).all()
    assert len(agenda_items) == 0