from datetime import datetime, timedelta
from sqlalchemy.sql import or_

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import db, User, School, AgendaItem, Event, Course, Program, Location, valid_user_roles, MailMergeTemplateSend, \
    AgendaItemStatus, EventStatus
from utils import check_permission

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def home():
    # Determine sendable but unsent emails
    sendable_unsent_emails = []

    # Check school_program entries
    school_programs = db.session.query(School, Program).join(School.programs).all()
    for school, program in school_programs:
        for template in program.mail_merge_templates:
            sent_records = MailMergeTemplateSend.query.filter_by(
                mail_merge_template_id=template.id, program_id=program.id
            ).all()
            if not sent_records:
                sendable_unsent_emails.append({
                    'type': 'School Program',
                    'name': f"{school.name} - {program.name}",
                    'template': template,
                    'program_id': program.id,
                    'school_id': school.id
                })

    # Check courses
    courses = Course.query.all()
    for course in courses:
        if course.template_course:
            for template in course.template_course.mail_merge_templates:
                sent_records = MailMergeTemplateSend.query.filter_by(
                    mail_merge_template_id=template.id, course_id=course.id
                ).all()
                if not sent_records and course.status.name in template.sendable_statuses:
                    sendable_unsent_emails.append({
                        'type': 'Course',
                        'name': course.name,
                        'template': template,
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
                if not sent_records and event.status.name in template.sendable_statuses:
                    sendable_unsent_emails.append({
                        'type': 'Event',
                        'name': event.name,
                        'template': template,
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
                if not sent_records and item.status.name in template.sendable_statuses:
                    sendable_unsent_emails.append({
                        'type': 'Agenda Item',
                        'name': item.title,
                        'template': template,
                        'agenda_item_id': item.id
                    })

    # Fetch other data for the dashboard
    unconfirmed_events = Event.query.filter(
        or_(
            Event.date.is_(None),  # Event has no date
            Event.agenda_items.any(AgendaItem.lecturer_id.is_(None)),  # Any agenda item has no lecturer
            Event.agenda_items.any(AgendaItem.status != AgendaItemStatus.CONFIRMED)  # Any agenda item is not confirmed
        )
    ).all()
    tentative_agenda_items = AgendaItem.query.filter_by(status=AgendaItemStatus.TENTATIVE).all()
    unscheduled_agenda_items = AgendaItem.query.filter_by(status=AgendaItemStatus.UNSCHEDULED).all()

    return render_template(
        'index.html',
        sendable_unsent_emails=sendable_unsent_emails,
        unconfirmed_events=unconfirmed_events,
        tentative_agenda_items=tentative_agenda_items,
        unscheduled_agenda_items=unscheduled_agenda_items
    )


@bp.route('/admin-dashboard')
@login_required
@check_permission('admin_dashboard')
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    users = User.query.all()
    return render_template('admin_dashboard.html', users=users, valid_user_roles=valid_user_roles)


@bp.route('/school-dashboard')
@login_required
def school_dashboard():
    if current_user.role not in ['school_contact', 'admin']:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    if current_user.school_id is None:
        schools = School.query.all()
    else:
        schools = School.query.filter_by(id=current_user.school_id).all()
    return render_template('school_dashboard.html', schools=schools)


@bp.route('/lecturer-dashboard')
@login_required
def lecturer_dashboard():
    if current_user.role != 'lecturer' and current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    agenda_items = AgendaItem.query.filter_by(lecturer_id=current_user.id)  # Assigned agenda items
    return render_template('lecturer_dashboard.html', agenda_items=agenda_items)


@bp.route('/schedule-table')
@login_required
def schedule_table():
    # Filters
    school_ids = request.args.getlist('school')
    lecturer_ids = request.args.getlist('lecturer')
    program_ids = request.args.getlist('program')
    course_ids = request.args.getlist('course')
    location_ids = request.args.getlist('location')

    events_query = Event.query.join(Course).join(School).join(Location, isouter=True)

    if school_ids:
        events_query = events_query.filter(Event.school_id.in_(school_ids))
    if lecturer_ids:
        events_query = events_query.join(Event.agenda_items).filter(AgendaItem.lecturer_id.in_(lecturer_ids))
    if program_ids:
        events_query = events_query.filter(Course.program_id.in_(program_ids))
    if course_ids:
        events_query = events_query.filter(Event.course_id.in_(course_ids))
    if location_ids:
        events_query = events_query.filter(Event.location_id.in_(location_ids))

    events = events_query.options(joinedload(Event.agenda_items)).order_by(Event.date.asc()).all()

    # Fetch filters data
    schools = School.query.all()
    lecturers = User.query.filter(User.role.in_(['lecturer', 'admin'])).all()
    programs = Program.query.all()
    courses = Course.query.distinct(Course.name).all()
    locations = Location.query.all()

    return render_template(
        'schedule_table.html',
        events=events,
        schools=schools,
        lecturers=lecturers,
        programs=programs,
        courses=courses,
        locations=locations,
    )


@bp.route('/schedule-calendar')
@login_required
def schedule_calendar():
    # Fetch filters data for the filter form
    schools = School.query.all()
    lecturers = User.query.filter(User.role.in_(['lecturer', 'admin'])).all()
    programs = Program.query.all()
    courses = Course.query.distinct(Course.name).all()
    locations = Location.query.all()
    return render_template(
        'schedule_calendar.html',
        schools=schools,
        lecturers=lecturers,
        programs=programs,
        courses=courses,
        locations=locations,
    )


@bp.route('/schedule/events')
@login_required
def schedule_events():
    # Fetch filters from query parameters
    school_ids = request.args.getlist('school')  # Fetch school filter
    lecturer_ids = request.args.getlist('lecturer')
    program_ids = request.args.getlist('program')
    course_ids = request.args.getlist('course')
    location_ids = request.args.getlist('location')
    n_days = int(request.args.get('n_days', 60))
    today = datetime.today().date()
    future = today + timedelta(days=n_days)

    # Base query
    events_query = Event.query.join(Course).join(School)

    # Apply filters
    if school_ids:
        events_query = events_query.filter(Event.school_id.in_(school_ids))  # Apply school filter
    if lecturer_ids:
        events_query = events_query.join(Event.agenda_items).filter(AgendaItem.lecturer_id.in_(lecturer_ids))
    if program_ids:
        events_query = events_query.filter(Course.program_id.in_(program_ids))
    if course_ids:
        events_query = events_query.filter(Event.course_id.in_(course_ids))
    if location_ids:
        events_query = events_query.filter(Event.location_id.in_(location_ids))

    # Date range filter
    events_query = events_query.filter((Event.date >= today - timedelta(days=31)) | (Event.date == None), (Event.date <= future) | (Event.date == None))

    events = events_query.options(joinedload(Event.agenda_items)).all()

    # Prepare event data for the calendar
    event_list = []
    for event in events:
        # Add the main event
        if event.start_time:
            start_time = event.start_time
        elif event.date:
            start_time = event.date
        else:
            start_time = None

        if event.end_time:
            end_time = event.end_time
        elif event.date:
            end_time = event.date
        else:
            end_time = None

        event_list.append({
            'id': f'event-{event.id}',
            'title': event.name,
            'school': event.school.name,
            'course': event.course.name,
            'program': event.course.program.name,
            'start': start_time.isoformat() if start_time else None,
            'end': end_time.isoformat() if end_time else None,
            'location': event.location.name if event.location else 'N/A',
            'backgroundColor': event.status.color,
            'status': event.status.value,
            'url': url_for('event_mgmt.edit_event', event_id=event.id),
        })
        # Add agenda items as overlapping events
        for item in event.agenda_items:
            item_duration_str = None
            if event.date and item.time:
                start_time = datetime.combine(event.date, item.time)
                end_time = start_time + item.duration
                hours = item.duration.seconds // 3600
                mod_minutes = (item.duration.seconds % 3600) // 60

                if hours >= 1:
                    item_duration_str = f'{hours}h {mod_minutes}m'
                else:
                    item_duration_str = f'{mod_minutes}m'
            else:
                start_time = end_time = None


            event_list.append({
                'id': f'agenda-{item.id}',
                'title': f'{item.title}',
                'start': start_time.isoformat() if start_time else None,
                'end': end_time.isoformat() if end_time else None,
                'duration': item_duration_str if item_duration_str else None,
                'status' : item.status.value,
                'lecturer': item.lecturer.username if item.lecturer else 'unassigned',
                'eventId': f'event-{event.id}',  # Link to the main event
                'backgroundColor': item.status.color,
                'url': url_for('event_mgmt.edit_agenda_item', item_id=item.id),
            })
    return event_list

