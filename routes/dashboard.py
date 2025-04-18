from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import User, School, AgendaItem, Event, Course, Program, Location
from utils import check_permission

bp = Blueprint('dashboard', __name__)


@bp.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('auth.login'))

    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)


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


@bp.route('/schedule')
@login_required
def schedule():
    view = request.args.get('view', 'week')  # Default to 'week' view
    n_days = int(request.args.get('n_days', 60))
    today = datetime.today().date()
    future = today + timedelta(days=n_days)

    # Filters
    school_ids = request.args.getlist('school')
    lecturer_ids = request.args.getlist('lecturer')
    program_ids = request.args.getlist('program')
    course_ids = request.args.getlist('course')
    location_ids = request.args.getlist('location')

    # Base query
    events_query = Event.query.join(Course).join(School).join(Location, isouter=True)

    # Apply filters
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

    # Date range filter
    if view in ['day', 'week']:
        events_query = events_query.filter((Event.date >= today) | (Event.date == None), Event.date <= future)

    events = events_query.options(joinedload(Event.agenda_items)).all()

    # Fetch filters data
    schools = School.query.all()
    lecturers = User.query.all()
    programs = Program.query.all()
    courses = Course.query.all()
    locations = Location.query.all()

    return render_template(
        'schedule.html',
        events=events,
        view=view,
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
    school_ids = request.args.getlist('school')
    lecturer_ids = request.args.getlist('lecturer')
    program_ids = request.args.getlist('program')
    course_ids = request.args.getlist('course')
    location_ids = request.args.getlist('location')
    n_days = int(request.args.get('n_days', 60))
    today = datetime.today().date()
    future = today + timedelta(days=n_days)

    # Base query
    events_query = Event.query.join(Course).join(School).join(Location, isouter=True)

    # Apply filters
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

    # Date range filter
    events_query = events_query.filter((Event.date >= today) | (Event.date == None), Event.date <= future)

    events = events_query.options(joinedload(Event.agenda_items)).all()

    # Prepare event data for the calendar
    event_list = []
    for event in events:
        # Add the main event
        event_list.append({
            'id': f'event-{event.id}',
            'title': event.name,
            'start': event.start_time.isoformat() if event.start_time else event.date.isoformat(),
            'end': event.end_time.isoformat() if event.end_time else event.date.isoformat(),
            'location': event.location.name if event.location else 'N/A',
            'backgroundColor': event.location.color if event.location else '#cccccc',
            'display': 'block',
            #'url': url_for('event_mgmt.edit_event', event_id=event.id),
        })
        # Add agenda items as overlapping events
        for item in event.agenda_items:
            if item.time and item.duration:
                start_time = datetime.combine(event.date, item.time)
                end_time = start_time + item.duration
                event_list.append({
                    'id': f'agenda-{item.id}',
                    'title': f'{item.title}',
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'backgroundColor': item.lecturer.color if item.lecturer else None,  # Use a neutral color for agenda items
                    #'url': url_for('event_mgmt.edit_agenda_item', item_id=item.id),
                })
    return event_list

