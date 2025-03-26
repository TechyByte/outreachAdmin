from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from models import db, Program, TemplateCourse, TemplateEvent, TemplateAgendaItem

bp = Blueprint('template_mgmt', __name__)


@bp.route('/manage-templates', methods=['GET', 'POST'])
@login_required
def manage_templates():
    """Allows admins to manage template courses and agenda items."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    program_id = request.args.get('program_id')
    course_id = request.args.get('course_id')

    selected_program = None
    selected_course = None
    assigned_courses = []
    available_courses = []

    with current_app.app_context():
        programs = Program.query.all()

        if program_id:
            selected_program = Program.query.get(program_id)
            assigned_courses = selected_program.template_courses  # ✅ Get assigned courses via many-to-many
            available_courses = TemplateCourse.query.filter(~TemplateCourse.programs.any(Program.id == selected_program.id)).all()  # ✅ Get unassigned courses

        if course_id:
            selected_course = TemplateCourse.query.get(course_id)

    return render_template(
        "manage_templates.html",
        programs=programs,
        selected_program=selected_program,
        assigned_courses=assigned_courses,
        available_courses=available_courses,
        selected_course=selected_course
    )


@bp.route('/assign-template-course', methods=['POST'])
@login_required
def assign_template_course():
    """Assigns a template course to a program (Allows Multiple Assignments)."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    course_id = request.form.get('course_id')
    program_id = request.form.get('program_id')

    with current_app.app_context():
        program = Program.query.get(program_id)
        course = TemplateCourse.query.get(course_id)

        if course and program and course not in program.template_courses:
            program.template_courses.append(course)  # ✅ Assign course to multiple programs
            db.session.commit()

    flash("Template course assigned successfully!", "success")
    return redirect(url_for('template_mgmt.manage_templates', program_id=program_id))


@bp.route('/remove-template-course', methods=['POST'])
@login_required
def remove_template_course():
    """Removes a template course from a specific program without deleting it."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    course_id = request.form.get('course_id')
    program_id = request.form.get('program_id')

    with current_app.app_context():
        program = Program.query.get(program_id)
        course = TemplateCourse.query.get(course_id)

        if program and course and course in program.template_courses:
            program.template_courses.remove(course)  # ✅ Unassign without deleting
            db.session.commit()

    flash("Template course unassigned from program.", "warning")
    return redirect(url_for('template_mgmt.manage_templates', program_id=program_id))



@bp.route('/edit_agenda_item', methods=['POST'])
@login_required
def edit_agenda_item():
    """Allows editing of template agenda items."""
    if current_user.role not in ['admin', 'lecturer']:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    agenda_item_id = request.form.get('agenda_item_id')
    new_title = request.form.get('new_title')

    with current_app.app_context():
        agenda_item = TemplateAgendaItem.query.get(agenda_item_id)
        if agenda_item:
            agenda_item.title = new_title
            db.session.commit()
            flash("Agenda item updated successfully!", "success")

    return redirect(url_for('template_mgmt.manage_templates'))


@bp.route('/edit-template-course/<int:course_id>', methods=['GET'])
@login_required
def edit_template_course(course_id):
    """Displays the template course and allows editing of events & agenda items."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    with current_app.app_context():
        selected_course = TemplateCourse.query.get(course_id)

        if not selected_course:
            flash("Course not found.", "danger")
            return redirect(url_for('template_mgmt.manage_templates'))

        # ✅ Get the first program this template course is assigned to
        selected_program = selected_course.programs[0] if selected_course.programs else None

        return render_template(
            "edit_template_course.html",
            selected_course=selected_course,
            selected_program=selected_program
        )

@bp.route('/add-template-event', methods=['POST'])
@login_required
def add_template_event():
    """Adds a new template event to a course."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    course_id = request.form.get('course_id')
    event_name = request.form.get('event_name')

    with current_app.app_context():
        new_event = TemplateEvent(name=event_name, template_course_id=course_id)
        db.session.add(new_event)
        db.session.commit()

    flash("New event added successfully!", "success")
    return redirect(url_for('template_mgmt.edit_template_course', course_id=course_id))


@bp.route('/edit-template-event', methods=['POST'])
@login_required
def edit_template_event():
    """Edits an existing template event."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    event_id = request.form.get('event_id')
    new_name = request.form.get('new_event_name')

    with current_app.app_context():
        event = TemplateEvent.query.get(event_id)
        if event:
            event.name = new_name
            db.session.commit()

    flash("Event updated successfully!", "success")
    return redirect(url_for('template_mgmt.edit_template_course', course_id=event.template_course_id))


@bp.route('/delete-template-event', methods=['POST'])
@login_required
def delete_template_event():
    """Deletes a template event and its associated agenda items."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    event_id = request.form.get('event_id')

    with current_app.app_context():
        event = TemplateEvent.query.get(event_id)
        if event:
            db.session.delete(event)
            db.session.commit()

    flash("Event deleted successfully!", "danger")
    return redirect(url_for('template_mgmt.edit_template_course', course_id=event.template_course_id))


@bp.route('/add-template-agenda-item', methods=['POST'])
@login_required
def add_template_agenda_item():
    """Adds a new agenda item to a template event."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    event_id = request.form.get('event_id')
    agenda_title = request.form.get('agenda_title')

    with current_app.app_context():
        new_agenda = TemplateAgendaItem(title=agenda_title, template_event_id=event_id)
        db.session.add(new_agenda)
        db.session.commit()

    flash("New agenda item added successfully!", "success")
    return redirect(url_for('template_mgmt.edit_template_course', course_id=TemplateEvent.query.get(event_id).template_course_id))


@bp.route('/edit-template-agenda-item', methods=['POST'])
@login_required
def edit_template_agenda_item():
    """Edits an existing template agenda item."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    agenda_item_id = request.form.get('agenda_item_id')
    new_title = request.form.get('new_agenda_title')

    with current_app.app_context():
        agenda_item = TemplateAgendaItem.query.get(agenda_item_id)
        if agenda_item:
            agenda_item.title = new_title
            db.session.commit()

    flash("Agenda item updated successfully!", "success")
    return redirect(url_for('template_mgmt.edit_template_course', course_id=agenda_item.event.template_course_id))




@bp.route('/delete-template-agenda-item', methods=['POST'])
@login_required
def delete_template_agenda_item():
    """Deletes a template agenda item from a template event."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('template_mgmt.manage_templates'))

    agenda_item_id = request.form.get('agenda_item_id')

    with current_app.app_context():
        agenda_item = TemplateAgendaItem.query.get(agenda_item_id)
        if agenda_item:
            course_id = agenda_item.template_event.template_course_id  # Get associated course before deleting
            db.session.delete(agenda_item)
            db.session.commit()
            flash("Agenda item deleted successfully!", "danger")
            return redirect(url_for('template_mgmt.edit_template_course', course_id=course_id))

    flash("Agenda item not found!", "warning")
    return redirect(url_for('template_mgmt.manage_templates'))

