import sqlalchemy
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, event
from sqlalchemy import Enum
from enum import Enum as PyEnum

from sqlalchemy.orm import object_session

db = SQLAlchemy()

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


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Store hashed password
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'lecturer', or 'school_contact'
    # TODO: accept only roles as defined in permissions.yaml
    # TODO: derive default_role using registered users' email domain
    # TODO: create configured_role for each user
    # TODO: return role as configured_role, if set, else return default_role
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=True)
    school = db.relationship('School', back_populates='users')
    default_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)  # Allow null if no default location assigned
    default_location = db.relationship('Location', backref='users')  # Allow null if no default location assigned


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


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    program = db.relationship('Program', backref='courses')
    school = db.relationship('School', backref='courses')
    events = db.relationship('Event', backref='course', order_by='Event.date.asc()', cascade='all, delete-orphan')


class EventNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hidden = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text, nullable=False)

    def delete(self):
        # Perform a soft delete by setting hidden=True
        self.hidden = True
        db.session.add(self)
        db.session.commit()




class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    school = db.relationship('School', backref='events')

    notes = db.relationship('EventNote', backref='event', order_by='EventNote.datetime.desc()')



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
            return "Unscheduled"
        elif any(item.lecturer is None for item in self.agenda_items):
            return "Partially Scheduled"
        elif all(item.status == AgendaItemStatus.CONFIRMED for item in self.agenda_items):
            return "Fully Scheduled"
        elif all(item.status in [AgendaItemStatus.CONFIRMED, AgendaItemStatus.TENTATIVE] for item in self.agenda_items):
            return "Tentatively Scheduled"
        return "Unknown"



@event.listens_for(EventNote, 'before_delete')
def prevent_EventNote_deletion(mapper, connection, target):
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

