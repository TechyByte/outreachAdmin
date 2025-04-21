from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_required
from sqlalchemy.orm import selectinload

from models import db, School, Program, Course, Event, AgendaItem, TemplateCourse, TemplateEvent, \
    TemplateAgendaItem, program_template_course
from utils import check_permission

bp = Blueprint('enrolment', __name__)


# AJAX endpoints

@bp.route('/_get_programs/<int:school_id>')
def get_programs_for_school(school_id):
    school = School.query.get_or_404(school_id)
    enrolled_ids = {p.id for p in school.programs}
    available_programs = Program.query.filter(~Program.id.in_(enrolled_ids)).all()
    return jsonify([{'id': p.id, 'name': p.name} for p in available_programs])


@bp.route('/_get_template_courses/<int:program_id>')
def get_template_courses(program_id):
    courses = TemplateCourse.query \
        .join(program_template_course) \
        .filter(program_template_course.c.program_id == program_id).all()
    return jsonify([{'id': c.id, 'name': c.name} for c in courses])


@bp.route('/enroll', methods=['GET', 'POST'])
@check_permission('enroll_school')
@login_required
def enroll(school_id=None, program_id=None):
    """Handles enrollment of School on Program."""
    if request.method == 'POST' or (school_id and program_id):
        if not school_id:
            school_id = request.form.get('school_id')
        if not program_id:
            program_id = request.form.get('program_id')
        selected_course_ids = request.form.getlist('course_ids') if request.method == 'POST' else []

        with current_app.app_context():
            school = School.query.get(school_id)
            program = Program.query.get(program_id)

            if not school or not program:
                return "Invalid school or program selection", 400

            if program not in school.programs:
                school.programs.append(program)

                # Copy selected template courses
                for template_course_id in selected_course_ids:
                    template_course = TemplateCourse.query.get(template_course_id)
                    new_course = Course(name=template_course.name, program_id=program.id, school_id=school.id)
                    db.session.add(new_course)
                    db.session.commit()

                    # Copy events
                    template_events = TemplateEvent.query.filter_by(template_course_id=template_course.id).all()
                    for template_event in template_events:
                        new_event = Event(name=template_event.name, course_id=new_course.id, school_id=school.id)
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
        flash('School enrolled successfully!', 'success')
        return redirect(url_for('enrolment.manage_enrollment'))
    else:
        # GET method
        if not school_id:
            school_id = request.args.get('school_id')
        if not program_id:
            program_id = request.args.get('program_id')

    # GET method
    with current_app.app_context():
        if school_id:
            schools = School.query.filter(School.id == school_id).all()
        else:
            schools = School.query.options(selectinload(School.programs)).all()
        programs = Program.query.all()
        template_courses = TemplateCourse.query.all()

        return render_template(
            'enroll.html',
            schools=schools,
            programs=programs,
            template_courses=template_courses
        )


@bp.route('/unenroll', methods=['POST'])
@check_permission('unenroll_school')
@login_required
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
                    db.session.delete(event)
                Event.query.filter_by(course_id=course.id).delete()
                db.session.delete(course)

            db.session.commit()
    flash('School unenrolled successfully.', 'info')
    return redirect(url_for('enrolment.manage_enrollment'))


@bp.route('/manage-enrollment')
@login_required
def manage_enrollment():
    """Displays schools and their enrolled programs."""
    with current_app.app_context():
        schools = db.session.query(School).options(selectinload(School.programs)).all()
        programs = db.session.query(Program).options(selectinload(Program.courses)).all()

    return render_template('enroll.html', schools=schools, programs=programs)
