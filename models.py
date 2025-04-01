from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date

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


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Store hashed password
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'lecturer', or 'school_contact'
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=True)
    school = db.relationship('School', back_populates='users')


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


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    location = db.Column(db.String(100), nullable=True)
    date = db.Column(Date, nullable=True)
    agenda_items = db.relationship('AgendaItem', backref='event', order_by='AgendaItem.time.asc()',
                                   cascade='all, delete-orphan')


class AgendaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null if no lecturer assigned
    lecturer_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    lecturer = db.relationship('User', backref='agenda_items')
    time = db.Column(db.Time, nullable=True)
    duration = db.Column(db.Interval, nullable=True)
    description = db.Column(db.Text, nullable=True)
