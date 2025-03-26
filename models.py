from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

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

# Association table: Pupils in Courses
pupil_course = db.Table('pupil_course',
    db.Column('pupil_id', db.Integer, db.ForeignKey('pupil.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    """Lecturers who can manage templates."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Store hashed password
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'lecturer', or 'school_contact'


class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(100), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # School Contact
    user = db.relationship('User', backref='school')
    programs = db.relationship('Program', secondary=school_program, back_populates='schools') # backref=db.backref('schools', lazy='dynamic'))

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


class TemplateEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_course_id = db.Column(db.Integer, db.ForeignKey('template_course.id'), nullable=False)

class TemplateAgendaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    template_event_id = db.Column(db.Integer, db.ForeignKey('template_event.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null if no lecturer assigned

    lecturer = db.relationship('User', backref='template_agenda_items')


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    location = db.Column(db.String(100), nullable=True)
    date = db.Column(db.String(50), nullable=True)

class Pupil(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    courses = db.relationship('Course', secondary=pupil_course, backref=db.backref('pupils', lazy='dynamic'))

class AgendaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    lecturer = db.Column(db.String(100), nullable=True)
