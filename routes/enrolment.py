from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.orm import selectinload
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, School, Program, Course, Event, AgendaItem, TemplateCourse, TemplateEvent, TemplateAgendaItem

bp = Blueprint('enrolment', __name__)


@bp.route('/enroll', methods=['GET', 'POST'])
def enroll():
    """Handles school enrollment and copies templates into independent records."""
    if request.method == 'POST':
        school_id = request.form.get('school_id')
        program_id = request.form.get('program_id')

        with current_app.app_context():
            school = School.query.get(school_id)
            program = Program.query.get(program_id)

            if not school or not program:
                return "Invalid school or program selection", 400

            # Prevent duplicate enrollment
            if program not in school.programs:
                school.programs.append(program)

                # Copy courses from template
                template_courses = TemplateCourse.query.filter_by(program=Program.id).all()
                for template_course in template_courses:
                    new_course = Course(name=template_course.name, program_id=program.id, school_id=school.id)
                    db.session.add(new_course)
                    db.session.commit()

                    # Copy events from template course
                    template_events = TemplateEvent.query.filter_by(template_course_id=template_course.id).all()
                    for template_event in template_events:
                        new_event = Event(name=template_event.name, course_id=new_course.id, school_id=school.id)
                        db.session.add(new_event)
                        db.session.commit()

                        # Copy agenda items from template event
                        template_agendas = TemplateAgendaItem.query.filter_by(template_event_id=template_event.id).all()
                        for template_agenda in template_agendas:
                            new_agenda = AgendaItem(title=template_agenda.title, event_id=new_event.id)
                            db.session.add(new_agenda)

                db.session.commit()

        return redirect(url_for('manage_enrollment'))

    with current_app.app_context():
        schools = School.query.options(selectinload(School.programs)).all()
        programs = Program.query.all()

    return render_template('enroll.html', schools=schools, programs=programs)


@bp.route('/unenroll', methods=['POST'])
def unenroll():
    """Handles school unenrollment and removes independent records."""
    school_id = request.form.get('school_id')
    program_id = request.form.get('program_id')

    with current_app.app_context():
        school = School.query.get(school_id)
        program = Program.query.get(program_id)

        if not school or not program:
            return "Invalid school or program selection", 400

        # Remove the school from the program
        if program in school.programs:
            school.programs.remove(program)

            # Delete courses, events, and agenda items specific to this school-program
            courses_to_delete = Course.query.filter_by(program_id=program.id, school_id=school.id).all()
            for course in courses_to_delete:
                events_to_delete = Event.query.filter_by(course_id=course.id).all()
                for event in events_to_delete:
                    AgendaItem.query.filter_by(event_id=event.id).delete()
                Event.query.filter_by(course_id=course.id).delete()
                db.session.delete(course)

            db.session.commit()

    return redirect(url_for('manage_enrollment'))


@bp.route('/manage-enrollment')
def manage_enrollment():
    """Displays schools and their enrolled programs."""
    with current_app.app_context():
        schools = db.session.query(School).options(selectinload(School.programs)).all()
        programs = Program.query.all()

    return render_template('enroll.html', schools=schools, programs=programs)
