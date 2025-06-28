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

from jinja2 import Template  # Import Jinja2 for rendering templates
from flask import render_template_string

import logging
logger = logging.getLogger(__name__)

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

# Many-to-Many Relationship Between MailMergeTemplate and TemplateCourse
mail_merge_template_template_course = db.Table(
    'mail_merge_template_template_course',
    db.Column('mail_merge_template_id', db.Integer, db.ForeignKey('mail_merge_template.id'), primary_key=True),
    db.Column('template_course_id', db.Integer, db.ForeignKey('template_course.id'), primary_key=True)
)

# Many-to-Many Relationship Between MailMergeTemplate and TemplateEvent
mail_merge_template_template_event = db.Table(
    'mail_merge_template_template_event',
    db.Column('mail_merge_template_id', db.Integer, db.ForeignKey('mail_merge_template.id'), primary_key=True),
    db.Column('template_event_id', db.Integer, db.ForeignKey('template_event.id'), primary_key=True)
)

# Many-to-Many Relationship Between MailMergeTemplate and TemplateAgendaItem
mail_merge_template_template_agenda_item = db.Table(
    'mail_merge_template_template_agenda_item',
    db.Column('mail_merge_template_id', db.Integer, db.ForeignKey('mail_merge_template.id'), primary_key=True),
    db.Column('template_agenda_item_id', db.Integer, db.ForeignKey('template_agenda_item.id'), primary_key=True)
)

# Many-to-Many Relationship Between MailMergeTemplate and Program
mail_merge_template_program = db.Table(
    'mail_merge_template_program',
    db.Column('mail_merge_template_id', db.Integer, db.ForeignKey('mail_merge_template.id'), primary_key=True),
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
    o365_id = db.Column(db.String(100), unique=True, nullable=True)  # Office 365 unique identifier
    email_verified = db.Column(db.Boolean, default=False)  # Whether the email has been verified via SSO
    display_name = db.Column(db.String(100), nullable=True)  # New field for display name
    specialty = db.Column(db.String(200), nullable=True)  # New field for specialty

    @staticmethod
    def get_or_create_o365_user(o365_id, email, username=None):
        """
        Retrieve an existing user by their Office 365 ID or create a new one.
        """
        user = User.query.filter_by(o365_id=o365_id).first()
        if user:
            return user
        else:
            user = User(
                o365_id=o365_id,
                email=email,
                username=username or email.split('@')[0],
                email_verified=True  # Assume email is verified if coming from SSO
            )
            db.session.add(user)
            db.session.commit()
            return user

    @validates('configured_role')
    def validate_configured_role(self, key, value):
        if value is not None and value not in valid_user_roles:
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
        logger.debug(f"Configured role: {self.configured_role}, Default role: {self.default_role}")
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
    urn = db.Column(db.String(20), nullable=True)
    la_code = db.Column(db.String(10), nullable=True)
    la_name = db.Column(db.String(100), nullable=True)
    establishment_number = db.Column(db.String(20), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    type_of_establishment = db.Column(db.String(100), nullable=True)
    phase_of_education = db.Column(db.String(100), nullable=True)
    statutory_low_age = db.Column(db.Integer, nullable=True)
    statutory_high_age = db.Column(db.Integer, nullable=True)
    street = db.Column(db.String(200), nullable=True)
    town = db.Column(db.String(100), nullable=True)
    postcode = db.Column(db.String(20), nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    head_name = db.Column(db.String(100), nullable=True)
    school_website = db.Column(db.String(200), nullable=True)
    number_of_pupils = db.Column(db.Integer, nullable=True)
    number_of_boys = db.Column(db.Integer, nullable=True)
    number_of_girls = db.Column(db.Integer, nullable=True)
    percentage_fsm = db.Column(db.Float, nullable=True)
    head_preferred_job_title = db.Column(db.String(100), nullable=True)
    nursery_provision = db.Column(db.String(100), nullable=True)
    establishment_status = db.Column(db.String(100), nullable=True)
    diocese = db.Column(db.String(100), nullable=True)
    gender = db.Column(db.String(50), nullable=True)
    school_capacity = db.Column(db.Integer, nullable=True)
    admissions_policy = db.Column(db.String(100), nullable=True)
    locality = db.Column(db.String(100), nullable=True)
    address3 = db.Column(db.String(200), nullable=True)
    parliamentary_constituency = db.Column(db.String(100), nullable=True)
    easting = db.Column(db.Integer, nullable=True)
    northing = db.Column(db.Integer, nullable=True)
    contact_name = db.Column(db.String(100), nullable=True)
    contact_email = db.Column(db.String(100), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    users = db.relationship('User', back_populates='school')
    programs = db.relationship('Program', secondary=school_program,
                               back_populates='schools')  # backref=db.backref('schools', lazy='dynamic'))  # TODO: back_populates "schools" to "school" ?

    @property
    def estimated_year_group_size(self):
        if self.statutory_low_age and self.statutory_high_age and self.number_of_pupils:
            est_year_groups = self.statutory_high_age - self.statutory_low_age
            if est_year_groups > 0:
                return self.number_of_pupils // est_year_groups
        return ""



class Program(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # Many-to-many relationship
    schools = db.relationship('School', secondary=school_program, back_populates='programs')
    # ✅ Relationship with TemplateCourse (Many-to-Many)
    template_courses = db.relationship('TemplateCourse', secondary=program_template_course, back_populates='programs')
    mail_merge_templates = db.relationship(
        'MailMergeTemplate',
        secondary=mail_merge_template_program,
        back_populates='programs'
    )


class TemplateCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=True)  # ✅ Allow NULL values
    #
    # program = db.relationship('Program', backref='template_courses', lazy=True)
    programs = db.relationship('Program', secondary=program_template_course, back_populates='template_courses')
    template_events = db.relationship('TemplateEvent', backref='template_course', order_by='TemplateEvent.sequence.asc()')
    mail_merge_templates = db.relationship(
        'MailMergeTemplate',
        secondary=mail_merge_template_template_course,
        back_populates='template_courses'
    )


class TemplateEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_course_id = db.Column(db.Integer, db.ForeignKey('template_course.id'), nullable=False)
    sequence = db.Column(db.Integer, nullable=True, default=0)  # Add this line to store event order
    default_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)
    default_location = db.relationship('Location', backref='template_events', foreign_keys=[default_location_id])
    template_agenda_items = db.relationship('TemplateAgendaItem', backref='template_event',
                                            order_by='TemplateAgendaItem.time.asc()')
    mail_merge_templates = db.relationship(
        'MailMergeTemplate',
        secondary=mail_merge_template_template_event,
        back_populates='template_events'
    )


class TemplateAgendaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    template_event_id = db.Column(db.Integer, db.ForeignKey('template_event.id', ondelete='cascade'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null if no lecturer assigned
    description = db.Column(db.Text, nullable=True)
    lecturer = db.relationship('User', backref='template_agenda_items')
    duration = db.Column(db.Interval, nullable=True)
    time = db.Column(db.Time, nullable=True)  # Time of day
    mail_merge_templates = db.relationship(
        'MailMergeTemplate',
        secondary=mail_merge_template_template_agenda_item,
        back_populates='template_agenda_items'
    )


class CourseStatus(PyEnum):
    UNSCHEDULED = "Unscheduled"
    PARTIALLY_SCHEDULED = "Partially Scheduled"
    FULLY_SCHEDULED = "Fully Scheduled"
    TENTATIVELY_SCHEDULED = "Tentatively Scheduled"
    UNKNOWN = "Unknown"
    ARCHIVED = "Archived"

    @property
    def color(self):
        return {
            CourseStatus.UNSCHEDULED: "#ff0000",
            CourseStatus.PARTIALLY_SCHEDULED: "#ffa500",
            CourseStatus.FULLY_SCHEDULED: "#008000",
            CourseStatus.TENTATIVELY_SCHEDULED: "#0000ff",
            CourseStatus.UNKNOWN: "#808080",
            CourseStatus.ARCHIVED: "#808080"
        }.get(self, "#000000")



class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    template_course_id = db.Column(db.Integer, db.ForeignKey('template_course.id'), nullable=True)  # Link to TemplateCourse

    program = db.relationship('Program', backref='courses')
    school = db.relationship('School', backref='courses')
    template_course = db.relationship('TemplateCourse', backref='courses')  # Relationship to TemplateCourse
    events = db.relationship('Event', backref='linked_course', order_by='Event.date.asc()', cascade='all, delete-orphan')

    @property
    def status(self):
        if all(event.status == EventStatus.ARCHIVED for event in self.events):
            return CourseStatus.ARCHIVED
        if all(event.status == EventStatus.UNSCHEDULED for event in self.events):
            return CourseStatus.UNSCHEDULED
        elif any(event.status in [EventStatus.UNSCHEDULED, EventStatus.PARTIALLY_SCHEDULED] for event in self.events):
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
    ARCHIVED = "Archived"

    @property
    def color(self):
        return {
            EventStatus.UNSCHEDULED: "#ff0000",
            EventStatus.PARTIALLY_SCHEDULED: "#ffa500",
            EventStatus.FULLY_SCHEDULED: "#008000",
            EventStatus.TENTATIVELY_SCHEDULED: "#0000ff",
            EventStatus.UNKNOWN: "#808080",
            EventStatus.ARCHIVED: "#808080"
        }.get(self, "#000000")


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    template_event_id = db.Column(db.Integer, db.ForeignKey('template_event.id'), nullable=True)  # Link to TemplateEvent

    school = db.relationship('School', backref='events')
    course = db.relationship('Course', backref='event_list')  # Use a unique backref name
    template_event = db.relationship('TemplateEvent', backref='events')  # Relationship to TemplateEvent

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
    def address(self):
        if self.location.is_school:
            return self.school.address
        else:
            return self.location.address if self.location and self.location.is_fixed else None


    @property
    def status(self):
        if self.date and self.date < datetime.today().date():
            # If the event date is in the past, consider it archived
            return EventStatus.ARCHIVED

        if any(item.lecturer is None for item in self.agenda_items) or not self.date:
            # If any item is missing a lecturer or if the event does not have a date, consider the event unscheduled
            return EventStatus.UNSCHEDULED  # Indicates that the event is missing a date or has items without lecturers
        elif any(item.status == AgendaItemStatus.UNSCHEDULED for item in self.agenda_items) and any(item.status in [AgendaItemStatus.CONFIRMED, AgendaItemStatus.TENTATIVE] for item in self.agenda_items):
            # If any item is unscheduled and any item is tentative or confirmed, consider the event partially scheduled
            return EventStatus.PARTIALLY_SCHEDULED  # Indicates that agenda items are not fully confirmed
        elif all(item.status == AgendaItemStatus.CONFIRMED for item in self.agenda_items):
            # If all agenda items are confirmed, consider the event fully scheduled
            return EventStatus.FULLY_SCHEDULED
        elif all(item.status in [AgendaItemStatus.CONFIRMED, AgendaItemStatus.TENTATIVE] for item in self.agenda_items):
            # If all agenda items are either confirmed or tentative, consider the event tentatively scheduled
            return EventStatus.TENTATIVELY_SCHEDULED
        return EventStatus.UNKNOWN

    @property
    def start_time(self):
        if not self.date or not self.agenda_items:
            return None  # Return None if date or agenda_items is missing
        for i in self.agenda_items:
            if i.time is None:
                return None
        first_item = min(self.agenda_items, key=lambda item: item.time)
        if first_item.time is None:
            return None
        return datetime.combine(self.date, first_item.time) - timedelta(minutes=15)


    @property
    def end_time(self):
        if not self.date or not self.agenda_items:
            return None
        last_item = max([item for item in self.agenda_items if item.time], key=lambda item: item.time)
        if last_item.duration is None:
            return None
        end_time = datetime.combine(self.date, last_item.time) + last_item.duration + timedelta(minutes=15)
        return end_time


    @property
    def duration(self):
        if not self.agenda_items:
            return None

        start = min([item for item in self.agenda_items if item.time], key=lambda item: item.time).time

        end = max([item for item in self.agenda_items if item.time and item.duration], key=lambda item: item.time)

        if end.time and end.duration:
            end = (datetime.combine(datetime.today(), end.time) + end.duration).time()
        else:
            end = datetime.combine(datetime.today(), end.time).time()

        if start and end:
            # Calculate duration based on start and end times
            start_datetime = datetime.combine(datetime.today(), start)
            end_datetime = datetime.combine(datetime.today(), end)
            return end_datetime - start_datetime
        return None


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

    @property
    def color(self):
        return {
            AgendaItemStatus.UNSCHEDULED: "#ff0000",
            AgendaItemStatus.TENTATIVE: "#ffa500",
            AgendaItemStatus.CONFIRMED: "#008000"
        }.get(self, "#000000")


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
    template_agenda_item_id = db.Column(db.Integer, db.ForeignKey('template_agenda_item.id'), nullable=True)  # Link to TemplateAgendaItem
    template_agenda_item = db.relationship('TemplateAgendaItem', backref='agenda_items')  # Relationship to TemplateAgendaItem

    notes = db.relationship('AgendaItemNote', back_populates='agenda_item', order_by='AgendaItemNote.datetime.desc()')

    @property
    def filtered_notes(self):
        return AgendaItemNote.query.filter_by(agenda_item_id=self.id, hidden=False).order_by(AgendaItemNote.datetime.desc()).all()


    @property
    def height(self):
        """
        Calculate the height of the agenda item based on its duration.
        :return: Height in pixels.
        """
        if self.duration:
            # Assuming 1 minute = 2 pixels
            return int(330 * self.duration.total_seconds() / self.event.duration.total_seconds())
        return 33


    @property
    def color(self):
        # Generate a distinct color code using a hash of the agenda item ID
        hash_object = hashlib.md5(str(self.id).encode())
        return f"#f{hash_object.hexdigest()[:4]}f"


class MailMergeTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    recipient_type = db.Column(db.String(50), nullable=False)  # 'lecturer' or 'school_contact'

    # Remove these redundant relationships
    # template_course_id = db.Column(db.Integer, db.ForeignKey('template_course.id'), nullable=True)
    # template_event_id = db.Column(db.Integer, db.ForeignKey('template_event.id'), nullable=True)
    # template_agenda_item_id = db.Column(db.Integer, db.ForeignKey('template_agenda_item.id'), nullable=True)

    # Many-to-Many Relationships
    template_courses = db.relationship(
        'TemplateCourse',
        secondary=mail_merge_template_template_course,
        back_populates='mail_merge_templates'
    )
    template_events = db.relationship(
        'TemplateEvent',
        secondary=mail_merge_template_template_event,
        back_populates='mail_merge_templates'
    )
    template_agenda_items = db.relationship(
        'TemplateAgendaItem',
        secondary=mail_merge_template_template_agenda_item,
        back_populates='mail_merge_templates'
    )
    programs = db.relationship(
        'Program',
        secondary=mail_merge_template_program,
        back_populates='mail_merge_templates'
    )

    # Sendable statuses
    sendable_statuses = db.Column(db.JSON, nullable=True)  # List of statuses when the template is sendable

    @property
    def is_live(self):
        """
        Determine if the template is live (linked to any programs, courses, events, or agenda items).
        """
        return bool(self.programs or self.template_courses or self.template_events or self.template_agenda_items)

    def is_sendable(self, entity):
        """
        Check if the template is sendable based on the status of a live entity.
        :param entity: A Program, Course, Event, or AgendaItem instance.
        :return: Boolean indicating if the template is sendable.
        """
        if isinstance(entity, Program):
            return entity in self.program.mail_merge_templates if self.program else False
        elif isinstance(entity, Course):
            return any(course in self.template_courses for course in entity.template_course.mail_merge_templates)
        elif isinstance(entity, Event):
            return any(event in self.template_events for event in entity.template_event.mail_merge_templates)
        elif isinstance(entity, AgendaItem):
            return any(item in self.template_agenda_items for item in entity.template_agenda_item.mail_merge_templates)
        return False


    def render_content(self, context):
        try:
            return render_template_string(self.content, **context)
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return self.content


class MailMergeTemplateSend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mail_merge_template_id = db.Column(db.Integer, db.ForeignKey('mail_merge_template.id'), nullable=False)
    recipient_email = db.Column(db.String(255), nullable=False)
    generated_content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships to link the sent mail to the relevant entity
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    agenda_item_id = db.Column(db.Integer, db.ForeignKey('agenda_item.id'), nullable=True)

    mail_merge_template = db.relationship('MailMergeTemplate', backref='sent_mails')
    program = db.relationship('Program', backref='sent_mails')
    course = db.relationship('Course', backref='sent_mails')
    event = db.relationship('Event', backref='sent_mails')
    agenda_item = db.relationship('AgendaItem', backref='sent_mails')
