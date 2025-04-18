from datetime import datetime, timedelta

import sqlalchemy
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, event
from sqlalchemy import Enum
from enum import Enum as PyEnum
import hashlib  # Add this import for hashing
import yaml
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property  # Import hybrid_property
from sqlalchemy.sql import case  # Import case for hybrid property expression

from sqlalchemy.event import Events
from sqlalchemy.orm import object_session
import logging as logger
logger.basicConfig(level=logger.DEBUG)
logging = logger.getLogger(__name__)


db = SQLAlchemy()


# Load roles from permissions.yaml
with open('permissions.yaml', 'r') as file:
    valid_user_roles = list(yaml.safe_load(file).keys())


# Many-to-Many Relationship Between Programs & Template Courses
program_template_course = db.Table(
    'program_template_course',
    db.Column('program_id', db.Integer, db.ForeignKey('program.id'), primary_key=True),
    db.Column('template_course_id', db.Integer, db.ForeignKey('template_course.id'), primary_key=True)
)

# Association table: Schools in Programs
school_program = db.Table('school_program',
                          db.Column('school_id', db.Integer, db.ForeignKey('school.id'), primary_key=True),
                          db.Column('program_id', db.Integer, db.ForeignKey('program.id'), primary_key=True)
                          )


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)

    is_school = db.Column(db.Boolean, default=False)  # True if location is a school

    #if address is set, type is fixed location, else set as virtual/mobile
    @property
    def is_fixed(self):
        return self.address is not None

    @property
    def color(self):
        # Generate a distinct color code using a hash of the location ID
        hash_object = hashlib.md5(str(self.id).encode())
        return f"#{hash_object.hexdigest()[:6]}"


class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Store hashed password
    configured_role = db.Column(db.String(20), nullable=True)


    @validates('configured_role')
    def validate_configured_role(self, key, value):
        if value not in valid_user_roles:
            raise ValueError(f"Invalid configured_role: {value}. Allowed configured_roles are: {valid_user_roles}")
        return value

    email = db.Column(db.String(120), unique=True, nullable=True) # TODO: make email not null?

    @hybrid_property
    def default_role(self):
        # TODO: replace example logic - derive default_role using user's email domain, only when email is confirmed or SSO
        if self.email:
            domain = self.email.split('@')[-1]
            if domain == 'school.edu':
                return 'school_contact'
            elif domain == 'lecturer.edu':
                return 'lecturer'
        return None

    @default_role.expression
    def default_role(cls):
        return sqlalchemy.case(
            (cls.email.like('%@school.edu'), 'school_contact'),
            (cls.email.like('%@lecturer.edu'), 'lecturer'),
            else_=None
        )

    @hybrid_property
    def role(self):
        logging.debug(f"Configured role: {self.configured_role}, Default role: {self.default_role}")
        if self.configured_role in valid_user_roles:
            return self.configured_role
        if self.default_role in valid_user_roles:
            return self.default_role
        return 'user' if self.email else 'guest'


    @role.expression
    def role(cls):
        # Use a case statement to replicate the logic in the database query
        return sqlalchemy.case(
            (cls.configured_role.in_(valid_user_roles), cls.configured_role),
            (sqlalchemy.literal_column(f"'{cls.default_role}'").in_(valid_user_roles), cls.default_role),
            else_='user'
        )


    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=True)
    school = db.relationship('School', back_populates='users')
    default_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)  # Allow null if no default location assigned
    default_location = db.relationship('Location', backref='users')  # Allow null if no default location assigned

    @property
    def color(self):
        # Generate a distinct color code using a hash of the user ID
        hash_object = hashlib.md5(str(self.id).encode())
        return f"#{hash_object.hexdigest()[:6]}"


class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(100), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    users = db.relationship('User', back_populates='school')
    programs = db.relationship('Program', secondary=school_program,
                               back_populates='schools')  # backref=db.backref('schools', lazy='dynamic'))


class Program(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # Many-to-many relationship
    schools = db.relationship('School', secondary=school_program, back_populates='programs')
    # ✅ Relationship with TemplateCourse (Many-to-Many)
    template_courses = db.relationship('TemplateCourse', secondary=program_template_course, back_populates='programs')


class TemplateCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=True)  # ✅ Allow NULL values
    #
    # program = db.relationship('Program', backref='template_courses', lazy=True)
    programs = db.relationship('Program', secondary=program_template_course, back_populates='template_courses')
    template_events = db.relationship('TemplateEvent', backref='template_course')


class TemplateEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_course_id = db.Column(db.Integer, db.ForeignKey('template_course.id'), nullable=False)
    template_agenda_items = db.relationship('TemplateAgendaItem', backref='template_event',
                                            order_by='TemplateAgendaItem.time.asc()')


class TemplateAgendaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    template_event_id = db.Column(db.Integer, db.ForeignKey('template_event.id', ondelete='cascade'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null if no lecturer assigned
    description = db.Column(db.Text, nullable=True)
    lecturer = db.relationship('User', backref='template_agenda_items')
    duration = db.Column(db.Interval, nullable=True)
    time = db.Column(db.Time, nullable=True)  # Time of day


class CourseStatus(PyEnum):
    UNSCHEDULED = "Unscheduled"
    PARTIALLY_SCHEDULED = "Partially Scheduled"
    FULLY_SCHEDULED = "Fully Scheduled"
    TENTATIVELY_SCHEDULED = "Tentatively Scheduled"
    UNKNOWN = "Unknown"


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    program = db.relationship('Program', backref='courses')
    school = db.relationship('School', backref='courses')
    events = db.relationship('Event', backref='course', order_by='Event.date.asc()', cascade='all, delete-orphan')

    @property
    def status(self):
        if all(event.status == EventStatus.UNSCHEDULED for event in self.events):
            return CourseStatus.UNSCHEDULED
        elif any(event.status == EventStatus.PARTIALLY_SCHEDULED for event in self.events):
            return CourseStatus.PARTIALLY_SCHEDULED
        elif all(event.status == EventStatus.FULLY_SCHEDULED for event in self.events):
            return CourseStatus.FULLY_SCHEDULED
        elif all(event.status in [EventStatus.FULLY_SCHEDULED, EventStatus.TENTATIVELY_SCHEDULED] for event in self.events):
            return CourseStatus.TENTATIVELY_SCHEDULED
        return CourseStatus.UNKNOWN


class BaseNote(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hidden = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text, nullable=False)

    def delete(self):
        # Perform a soft delete by setting hidden=True
        self.hidden = True
        db.session.add(self)
        db.session.commit()


class EventNote(BaseNote):
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    event = db.relationship('Event', back_populates='notes')
    user = db.relationship('User', backref='event_notes')


class AgendaItemNote(BaseNote):
    agenda_item_id = db.Column(db.Integer, db.ForeignKey('agenda_item.id'), nullable=False)
    agenda_item = db.relationship('AgendaItem', back_populates='notes')
    user = db.relationship('User', backref='agenda_item_notes')


class EventStatus(PyEnum):
    UNSCHEDULED = "Unscheduled"
    PARTIALLY_SCHEDULED = "Partially Scheduled"
    FULLY_SCHEDULED = "Fully Scheduled"
    TENTATIVELY_SCHEDULED = "Tentatively Scheduled"
    UNKNOWN = "Unknown"


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    school = db.relationship('School', backref='events')

    notes = db.relationship('EventNote', back_populates='event', order_by='EventNote.datetime.desc()')



    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)  # Allow null if no location assigned
    location = db.relationship('Location', backref='events')

    date = db.Column(Date, nullable=True)
    agenda_items = db.relationship('AgendaItem', backref='event', order_by='AgendaItem.time.asc()',
                                   cascade='all, delete-orphan')

    @property
    def filtered_notes(self):
        return EventNote.query.filter_by(event_id=self.id, hidden=False).order_by(EventNote.datetime.desc()).all()

    @property
    def status(self):
        if all(item.lecturer is None for item in self.agenda_items):
            return EventStatus.UNSCHEDULED
        elif any(item.lecturer is not None for item in self.agenda_items) and any(item.lecturer is None for item in self.agenda_items):
            return EventStatus.PARTIALLY_SCHEDULED
        elif all(item.status == AgendaItemStatus.CONFIRMED for item in self.agenda_items):
            return EventStatus.FULLY_SCHEDULED
        elif all(item.status in [AgendaItemStatus.CONFIRMED, AgendaItemStatus.TENTATIVE] for item in self.agenda_items):
            return EventStatus.TENTATIVELY_SCHEDULED
        return EventStatus.UNKNOWN

    @property
    def start_time(self):
        if not self.date or not self.agenda_items:
            return None  # Return None if date or agenda_items is missing
        first_item = min(self.agenda_items, key=lambda item: item.time)
        return datetime.combine(self.date, first_item.time) - timedelta(minutes=15)


    @property
    def end_time(self):
        if not self.date or not self.agenda_items:
            return None
        last_item = max(self.agenda_items, key=lambda item: item.time)
        end_time = datetime.combine(self.date, last_item.time) + last_item.duration + timedelta(minutes=15)
        return end_time


@event.listens_for(EventNote, 'before_delete')
def prevent_EventNote_deletion(mapper, connection, target):
    # Prevent the actual deletion
    raise sqlalchemy.exc.InvalidRequestError("EventNote deletion prevented.")

@event.listens_for(AgendaItemNote, 'before_delete')
def prevent_AgendaItemNote_deletion(mapper, connection, target):
    # Prevent the actual deletion
    raise sqlalchemy.exc.InvalidRequestError("EventNote deletion prevented.")

class AgendaItemStatus(PyEnum):
    UNSCHEDULED = "Unscheduled"
    TENTATIVE = "Tentative"
    CONFIRMED = "Confirmed"

class AgendaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null if no lecturer assigned
    status = db.Column(Enum(AgendaItemStatus), nullable=False, default=AgendaItemStatus.UNSCHEDULED)
    lecturer = db.relationship('User', backref='agenda_items')
    time = db.Column(db.Time, nullable=True)
    duration = db.Column(db.Interval, nullable=True)
    description = db.Column(db.Text, nullable=True)

    notes = db.relationship('AgendaItemNote', back_populates='agenda_item', order_by='AgendaItemNote.datetime.desc()')

    @property
    def filtered_notes(self):
        return AgendaItemNote.query.filter_by(agenda_item_id=self.id, hidden=False).order_by(AgendaItemNote.datetime.desc()).all()


