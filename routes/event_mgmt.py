from datetime import datetime, timedelta

from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import login_required

from models import Event, db, AgendaItem, User, Course, AgendaItemStatus
from utils import check_permission

bp = Blueprint('event_mgmt', __name__)


@bp.route('/course/<int:course_id>', methods=['GET', 'POST'])
@login_required
@check_permission('edit_course')
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        course.name = request.form['name']
        db.session.commit()
        flash('Course updated.')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_course.html', course=course)


@bp.route('/event/<int:event_id>', methods=['GET', 'POST'])
@login_required
@check_permission('edit_event')
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    course = db.session.query(Course).get(event.course_id)
    if request.method == 'POST':
        event.name = request.form['name']
        if len(request.form['location']) > 0:
            event.location = request.form['location']
        if len(request.form['date']) > 0:
            event.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        db.session.commit()
        flash('Event updated.')
        return redirect(url_for('dashboard.schedule'))
    return render_template('edit_event.html', event=event, course=course)


@bp.route('/agenda_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
@check_permission('edit_agenda_item')
def edit_agenda_item(item_id):
    item = AgendaItem.query.get_or_404(item_id)
    lecturers = User.query.filter((User.role == 'lecturer') | (User.role == 'admin')).all()
    event = db.session.query(Event).get(item.event_id)
    course = db.session.query(Course).get(event.course_id)  # Retrieve the course

    if request.method == 'POST':
        item.title = request.form['title']
        item.description = request.form['description']
        if len(request.form['time']) > 5:
            item.time = datetime.strptime(request.form['time'], '%H:%M:%S').time()
        else:
            item.time = datetime.strptime(request.form['time'], '%H:%M').time()

        if len(request.form['duration']) > 0:
            item.duration = timedelta(minutes=int(request.form['duration']))
        item.lecturer_id = request.form.get('lecturer_id') or None
        if request.form.get('status') is not None:
            item.status = request.form.get('status') if request.form.get('status') in AgendaItemStatus.__members__ else None
        db.session.commit()
        flash('Agenda item updated.')
        return redirect(url_for('event_mgmt.edit_event', event_id=item.event_id))
    return render_template('edit_agenda_item.html', item=item, lecturers=lecturers, course=course, event=event, AgendaItemStatus=AgendaItemStatus)

