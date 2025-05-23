import json
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user

from models import db, Program, TemplateCourse, TemplateEvent, TemplateAgendaItem, MailMergeTemplate, Event, AgendaItem, \
    Course, User, School, MailMergeTemplateSend, CourseStatus, EventStatus, AgendaItemStatus  # Import the status enums

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
            available_courses = TemplateCourse.query.filter(
                ~TemplateCourse.programs.any(Program.id == selected_program.id)).all()  # ✅ Get unassigned courses

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
            program.template_courses.remove(course)
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
    agenda_time = request.form.get('agenda_time')
    agenda_time = datetime.strptime(agenda_time, '%H:%M').time()
    lecturer_id = request.form.get('lecturer_id')

    with current_app.app_context():
        new_agenda = TemplateAgendaItem(title=agenda_title,
                                        template_event_id=event_id,
                                        time=agenda_time,
                                        lecturer_id=int(lecturer_id) if lecturer_id and lecturer_id != "0" else None
                                        )
        db.session.add(new_agenda)
        db.session.commit()

    flash("New agenda item added successfully!", "success")
    return redirect(
        url_for('template_mgmt.edit_template_course', course_id=TemplateEvent.query.get(event_id).template_course_id))


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


@bp.route('/manage-mail-templates', methods=['GET', 'POST'])
@login_required
def manage_mail_templates():
    """Allows admins to create and edit mail merge templates."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    templates = MailMergeTemplate.query.all()
    programs = Program.query.all()
    template_courses = TemplateCourse.query.all()
    template_events = TemplateEvent.query.all()
    template_agenda_items = TemplateAgendaItem.query.all()

    if request.method == 'POST':
        template_name = request.form.get('template_name')
        content = request.form.get('content')
        recipient_type = request.form.get('recipient_type')  # 'lecturer' or 'school_contact'
        sendable_statuses = request.form.getlist('sendable_statuses')  # List of statuses
        template_type = request.form.get('template_type')  # 'program', 'template_course', 'template_event', 'template_agenda_item'

        # Create a new template
        new_template = MailMergeTemplate(
            name=template_name,
            content=content,
            recipient_type=recipient_type,
            sendable_statuses=sendable_statuses
        )

        # Assign based on selected type
        if template_type == 'program':
            program_ids = request.form.getlist('program_ids')
            new_template.programs = Program.query.filter(Program.id.in_(program_ids)).all()
        elif template_type == 'template_course':
            template_course_ids = request.form.getlist('template_course_ids')
            new_template.template_courses = TemplateCourse.query.filter(TemplateCourse.id.in_(template_course_ids)).all()
        elif template_type == 'template_event':
            template_event_ids = request.form.getlist('template_event_ids')
            new_template.template_events = TemplateEvent.query.filter(TemplateEvent.id.in_(template_event_ids)).all()
        elif template_type == 'template_agenda_item':
            template_agenda_item_ids = request.form.getlist('template_agenda_item_ids')
            new_template.template_agenda_items = TemplateAgendaItem.query.filter(TemplateAgendaItem.id.in_(template_agenda_item_ids)).all()

        db.session.add(new_template)
        db.session.commit()
        flash("Mail merge template created successfully!", "success")
        return redirect(url_for('template_mgmt.manage_mail_templates'))

    # Load statuses for JavaScript
    course_statuses = {key: value.name for key, value in CourseStatus.__members__.items()}
    event_statuses = {key: value.name for key, value in EventStatus.__members__.items()}
    agenda_item_statuses = {key: value.name for key, value in AgendaItemStatus.__members__.items()}

    return render_template(
        'manage_mail_templates.html',
        templates=templates,
        programs=programs,
        template_courses=template_courses,
        template_events=template_events,
        template_agenda_items=template_agenda_items,
        course_statuses=json.dumps(course_statuses),
        event_statuses=json.dumps(event_statuses),
        agenda_item_statuses=json.dumps(agenda_item_statuses)
    )


@bp.route('/edit-mail-template/<int:template_id>', methods=['GET', 'POST'])
@login_required
def edit_mail_template(template_id):
    """Allows editing of a mail merge template."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    template = MailMergeTemplate.query.get_or_404(template_id)
    programs = Program.query.all()
    template_courses = TemplateCourse.query.all()
    template_events = TemplateEvent.query.all()
    template_agenda_items = TemplateAgendaItem.query.all()

    if request.method == 'POST':
        template.name = request.form.get('template_name')
        template.content = request.form.get('content')
        template.recipient_type = request.form.get('recipient_type')
        template.sendable_statuses = request.form.getlist('sendable_statuses')
        template_type = request.form.get('template_type')  # 'program', 'template_course', 'template_event', 'template_agenda_item'

        # Clear all associations
        template.program_id = None
        template.template_course_id = None
        template.template_event_id = None
        template.template_agenda_item_id = None

        # Assign based on selected type
        if template_type == 'program':
            program_ids = request.form.getlist('program_ids')
            template.programs = Program.query.filter(Program.id.in_(program_ids)).all()
        elif template_type == 'template_course':
            template_course_ids = request.form.getlist('template_course_ids')
            template.template_courses = TemplateCourse.query.filter(TemplateCourse.id.in_(template_course_ids)).all()
        elif template_type == 'template_event':
            template_event_ids = request.form.getlist('template_event_ids')
            template.template_events = TemplateEvent.query.filter(TemplateEvent.id.in_(template_event_ids)).all()
        elif template_type == 'template_agenda_item':
            template_agenda_item_ids = request.form.getlist('template_agenda_item_ids')
            template.template_agenda_items = TemplateAgendaItem.query.filter(TemplateAgendaItem.id.in_(template_agenda_item_ids)).all()

        db.session.commit()
        flash("Mail merge template updated successfully!", "success")
        return redirect(url_for('template_mgmt.manage_mail_templates'))

    # Load statuses for JavaScript
    course_statuses = {key: value.name for key, value in CourseStatus.__members__.items()}
    event_statuses = {key: value.name for key, value in EventStatus.__members__.items()}
    agenda_item_statuses = {key: value.name for key, value in AgendaItemStatus.__members__.items()}

    return render_template(
        'edit_mail_template.html',
        template=template,
        programs=programs,
        template_courses=template_courses,
        template_events=template_events,
        template_agenda_items=template_agenda_items,
        course_statuses=json.dumps(course_statuses),
        event_statuses=json.dumps(event_statuses),
        agenda_item_statuses=json.dumps(agenda_item_statuses)
    )


@bp.route('/comms-panel', methods=['GET'])
@login_required
def comms_panel():
    """Displays sent and unsent email templates for school_program, courses, events, and agenda items."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    templates_status = []

    # Check school_program entries
    school_programs = db.session.query(School, Program).join(School.programs).all()
    for school, program in school_programs:
        for template in program.mail_merge_templates:
            sent_records = MailMergeTemplateSend.query.filter_by(
                mail_merge_template_id=template.id, program_id=program.id
            ).all()
            templates_status.append({
                'type': 'School Program',
                'name': f"{school.name} - {program.name}",
                'school_name': school.name,
                'program_name': program.name,
                'template': template,
                'sent': bool(sent_records),
                'program_id': program.id,
                'school_id': school.id
            })

    # Check courses
    courses = Course.query.all()
    for course in courses:
        if course.template_course:  # Ensure the course is linked to a template course
            for template in course.template_course.mail_merge_templates:
                sent_records = MailMergeTemplateSend.query.filter_by(
                    mail_merge_template_id=template.id, course_id=course.id
                ).all()
                templates_status.append({
                    'type': 'Course',
                    'name': course.name,
                    'template': template,
                    'sent': bool(sent_records),
                    'course_id': course.id
                })

    # Check events
    events = Event.query.all()
    for event in events:
        if event.template_event:
            for template in event.template_event.mail_merge_templates:
                sent_records = MailMergeTemplateSend.query.filter_by(
                    mail_merge_template_id=template.id, event_id=event.id
                ).all()
                templates_status.append({
                    'type': 'Event',
                    'name': event.name,
                    'template': template,
                    'sent': bool(sent_records),
                    'event_id': event.id
                })

    # Check agenda items
    agenda_items = AgendaItem.query.all()
    for item in agenda_items:
        if item.template_agenda_item:
            for template in item.template_agenda_item.mail_merge_templates:
                sent_records = MailMergeTemplateSend.query.filter_by(
                    mail_merge_template_id=template.id, agenda_item_id=item.id
                ).all()
                templates_status.append({
                    'type': 'Agenda Item',
                    'name': item.title,
                    'template': template,
                    'sent': bool(sent_records),
                    'agenda_item_id': item.id
                })

    return render_template('comms_panel.html', templates_status=templates_status)


@bp.route('/send-mail/<int:template_id>', methods=['POST'])
@login_required
def send_mail(template_id):
    """Generates a mailto link or sends an email using SSO/O365."""
    template = MailMergeTemplate.query.get_or_404(template_id)

    # Determine the relevant entity (program, course, event, or agenda item)
    program_id = request.form.get('program_id')
    course_id = request.form.get('course_id')
    event_id = request.form.get('event_id')
    agenda_item_id = request.form.get('agenda_item_id')

    # Build the context based on the selected entity
    context = {}
    if program_id:
        context['program'] = Program.query.get_or_404(program_id)
    if course_id:
        context['course'] = Course.query.get_or_404(course_id)
    if event_id:
        context['event'] = Event.query.get_or_404(event_id)
    if agenda_item_id:
        context['agenda_item'] = AgendaItem.query.get_or_404(agenda_item_id)

    # Render the email content
    generated_content = template.render_content(context)

    recipient_email = request.form.get('recipient_email')
    if not recipient_email:
        flash("Recipient email is required!", "danger")
        return redirect(url_for('template_mgmt.comms_panel'))

    if request.form.get('action') == 'mailto':
        mailto_link = f"mailto:{recipient_email}?subject={template.name}&body={generated_content}"
        flash("Please confirm whether the email was sent.", "info")
        return render_template(
            'confirm_mail_sent.html',
            mailto_link=mailto_link,
            template_id=template_id,
            recipient_email=recipient_email,
            generated_content=generated_content,
            program_id=program_id,
            course_id=course_id,
            event_id=event_id,
            agenda_item_id=agenda_item_id
        )

    elif request.form.get('action') == 'send':
        # Create a record in MailMergeTemplateSend
        sent_mail = MailMergeTemplateSend(
            mail_merge_template_id=template.id,
            recipient_email=recipient_email,
            generated_content=generated_content,
            program_id=program_id,
            course_id=course_id,
            event_id=event_id,
            agenda_item_id=agenda_item_id
        )
        # db.session.add(sent_mail)
        # db.session.commit()
        # flash("Email sent successfully!", "success")
        flash("not implemented yet", "warning")
        return redirect(url_for('template_mgmt.comms_panel'))

    flash("Invalid action!", "danger")
    return redirect(url_for('template_mgmt.comms_panel'))


@bp.route('/confirm-mail-sent', methods=['POST'])
@login_required
def confirm_mail_sent():
    """Handles confirmation of email sent after generating a mailto link."""
    template_id = request.form.get('template_id')
    recipient_email = request.form.get('recipient_email')
    generated_content = request.form.get('generated_content')
    program_id = request.form.get('program_id')
    course_id = request.form.get('course_id')
    event_id = request.form.get('event_id')
    agenda_item_id = request.form.get('agenda_item_id')

    # Create a record in MailMergeTemplateSend
    sent_mail = MailMergeTemplateSend(
        mail_merge_template_id=template_id,
        recipient_email=recipient_email,
        generated_content=generated_content,
        program_id=program_id,
        course_id=course_id,
        event_id=event_id,
        agenda_item_id=agenda_item_id
    )
    db.session.add(sent_mail)
    db.session.commit()
    flash("Email marked as sent successfully!", "success")
    return redirect(url_for('template_mgmt.comms_panel'))






