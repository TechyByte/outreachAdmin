import pytest
import sqlalchemy

from app import app as flask_app
from models import db, User, Program, Course, Event, AgendaItem, School, TemplateCourse, TemplateEvent, \
    TemplateAgendaItem, Location, EventNote
from flask import Flask
from datetime import date, time, timedelta
from init_db import initialize_database

@pytest.fixture(scope='module')
def test_client():
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        yield flask_app.test_client()
        db.drop_all()

def test_user_crud(test_client):
    with flask_app.app_context():
        user = User(username='testuser', password='hashed', role='admin')
        db.session.add(user)
        db.session.commit()

        assert User.query.count() == 1

        user.username = 'updateduser'
        db.session.commit()
        assert User.query.first().username == 'updateduser'

        db.session.delete(user)
        db.session.commit()
        assert User.query.count() == 0


def test_program_crud(test_client):
    with flask_app.app_context():
        program = Program(name='Test Program')
        db.session.add(program)
        db.session.commit()

        assert Program.query.count() == 1
        program.name = 'Updated Program'
        db.session.commit()
        assert Program.query.first().name == 'Updated Program'

        db.session.delete(program)
        db.session.commit()
        assert Program.query.count() == 0


def test_school_and_course_relationship(test_client):
    with flask_app.app_context():
        school = School(name='Test School', contact_name='Alice', contact_email='alice@example.com', contact_phone='123456789')
        program = Program(name='School Program')
        school.programs.append(program)
        db.session.add(school)
        db.session.commit()

        course = Course(name='Course 101', program_id=program.id, school_id=school.id)
        db.session.add(course)
        db.session.commit()

        assert course.school.name == 'Test School'
        assert course.program.name == 'School Program'


def test_event_and_agenda_relationship(test_client):
    with flask_app.app_context():
        school = School(name='Event School', contact_name='Bob', contact_email='bob@example.com', contact_phone='987654321')
        program = Program(name='Event Program')
        db.session.add_all([school, program])
        db.session.commit()

        course = Course(name='Event Course', program_id=program.id, school_id=school.id)
        db.session.add(course)
        db.session.commit()

        event = Event(name='Launch Event', course_id=course.id, school_id=school.id, date=date.today())
        db.session.add(event)
        db.session.commit()

        user = User(username='lecturer1', password='hashed', role='lecturer')
        db.session.add(user)
        db.session.commit()

        agenda = AgendaItem(title='Welcome Talk', event_id=event.id, lecturer_id=user.id, time=time(9, 0), duration=timedelta(minutes=30), description='Intro')
        db.session.add(agenda)
        db.session.commit()

        assert agenda.lecturer.username == 'lecturer1'
        assert event.agenda_items[0].title == 'Welcome Talk'


def test_template_hierarchy(test_client):
    with flask_app.app_context():
        template_course = TemplateCourse(name='Template Course')
        db.session.add(template_course)
        db.session.commit()

        template_event = TemplateEvent(name='Template Event', template_course_id=template_course.id)
        db.session.add(template_event)
        db.session.commit()

        user = User(username='templ_lecturer', password='hashed', role='lecturer')
        db.session.add(user)
        db.session.commit()

        template_agenda = TemplateAgendaItem(
            title='Template Intro',
            template_event_id=template_event.id,
            lecturer_id=user.id,
            description='Overview',
            duration=timedelta(minutes=45),
            time=time(10, 0)
        )
        db.session.add(template_agenda)
        db.session.commit()

        assert template_event.template_agenda_items[0].title == 'Template Intro'
        assert template_agenda.lecturer.username == 'templ_lecturer'


def test_eventnote_prevent_deletion(test_client):
    with flask_app.app_context():
        # Create a user and an event
        user = User(username='note_user', password='hashed', role='admin')
        school = School(name='Note School', contact_name='Charlie', contact_email='charlie@example.com', contact_phone='555555555')
        program = Program(name='Note Program')
        db.session.add_all([user, school, program])
        db.session.commit()

        course = Course(name='Note Course', program_id=program.id, school_id=school.id)
        db.session.add(course)
        db.session.commit()

        event = Event(name='Note Event', course_id=course.id, school_id=school.id, date=date.today())
        db.session.add(event)
        db.session.commit()

        # Create an EventNote
        note = EventNote(event_id=event.id, user_id=user.id, datetime=date.today(), content='Test Note')
        db.session.add(note)
        db.session.commit()

        # Verify the note exists
        assert EventNote.query.count() == 1
        assert not note.hidden

        # Delete note the wrong way
        with pytest.raises(sqlalchemy.exc.InvalidRequestError):
            db.session.delete(note)
            db.session.commit()

        db.session.rollback()

        # Verify the note still exists
        assert EventNote.query.count() == 1
        assert not note.hidden

        # Attempt to delete the note
        note.delete()
        db.session.commit()

        # Verify the note is not deleted but hidden is set to True
        assert EventNote.query.count() == 1
        assert note.hidden