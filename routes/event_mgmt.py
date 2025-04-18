import logging as logger
logging = logger.getLogger(__name__)
from datetime import datetime, timedelta

from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import login_required, current_user

from models import Event, db, AgendaItem, User, Course, AgendaItemStatus, EventNote, AgendaItemNote, Location, valid_user_roles
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
    locations = db.session.query(Location).all()

    if request.method == 'POST':
        event.name = request.form['name']
        if len(request.form['location']) > 0:
            location_id = int(request.form['location'])  # Convert the location ID to an integer
            event.location = Location.query.get_or_404(location_id)  # Query the Location object
        if len(request.form['date']) > 0:
            event.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        db.session.commit()
        flash('Event updated.')
        return redirect(url_for('dashboard.schedule'))
    return render_template('edit_event.html', event=event, course=course, notes=event.filtered_notes,
                           locations=locations,
                           can_add_note=check_permission('add_event_note'),
                           can_archive_note=check_permission('archive_event_note'))

@bp.route('/event/<int:event_id>/notes', methods=['GET', 'POST'])
@login_required
def event_notes(event_id):
    event = Event.query.get_or_404(event_id)

    # Check if the user has permission to add notes
    can_add_note = check_permission('add_event_note')
    can_archive_note = check_permission('archive_event_note')

    if request.method == 'POST' and can_add_note:
        content = request.form.get('content')
        if content:
            note = EventNote(
                event_id=event_id,
                user_id=current_user.id,
                datetime=datetime.utcnow(),
                content=content
            )
            db.session.add(note)
            db.session.commit()
            flash('Note added successfully.', 'success')
            return redirect(url_for('event_mgmt.edit_event', event_id=event_id))

        else:
            flash('Note content cannot be empty.', 'danger')


    return render_template('event_notes.html', event=event, notes=event.filtered_notes, can_add_note=can_add_note,
                           can_archive_note=can_archive_note)


@bp.route('/event_note/<int:note_id>/archive', methods=['POST'])
@login_required
@check_permission('archive_event_note')
def archive_event_note(note_id):
    note = EventNote.query.get_or_404(note_id)
    event_id = note.event_id
    note.delete()
    flash('Note archived successfully.', 'success')
    return redirect(url_for('event_mgmt.edit_event', event_id=event_id))


@bp.route('/agenda_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
@check_permission('edit_agenda_item')
def edit_agenda_item(item_id):
    item = AgendaItem.query.get_or_404(item_id)
    lecturers = User.query.filter((User.role == 'lecturer') | (User.role == 'admin')).all()

    event = db.session.query(Event).get(item.event_id)
    course = db.session.query(Course).get(event.course_id)  # Retrieve the course

    can_add_note = check_permission('add_agenda_item_note')
    can_archive_note = check_permission('archive_agenda_item_note')

    if request.method == 'POST':
        item.title = request.form['title']
        item.description = request.form['description']
        try:
            if len(request.form['time']) > 5:
                item.time = datetime.strptime(request.form['time'], '%H:%M:%S').time()
            else:
                item.time = datetime.strptime(request.form['time'], '%H:%M').time()
        except ValueError:
            logging.debug('Invalid time format')

        if len(request.form['duration']) > 0:
            item.duration = timedelta(minutes=int(request.form['duration']))

        new_lecturer_id = request.form.get('lecturer_id')
        if new_lecturer_id:
            if new_lecturer_id == item.lecturer_id:
                # No change in lecturer
                pass
            else:
                # Change in lecturer
                item.lecturer_id = new_lecturer_id
                item.status = AgendaItemStatus.TENTATIVE
        else:
            # No lecturer assigned
            item.lecturer_id = None
            item.status = AgendaItemStatus.UNSCHEDULED

        # if request.form.get('status') is not None:
        #     item.status = request.form.get('status') if request.form.get(
        #         'status') in AgendaItemStatus.__members__ else None
        #
        db.session.commit()
        flash('Agenda item updated.')
        return redirect(url_for('event_mgmt.edit_event', event_id=item.event_id))
    return render_template('edit_agenda_item.html', item=item, lecturers=lecturers, course=course, event=event,
                           AgendaItemStatus=AgendaItemStatus, notes=item.filtered_notes,
                           can_add_note=can_add_note, can_archive_note=can_archive_note)


@bp.route('/agenda_item/<int:agenda_item_id>/notes', methods=['GET', 'POST'])
@login_required
def agenda_item_notes(agenda_item_id):
    agenda_item = AgendaItem.query.get_or_404(agenda_item_id)

    can_add_note = check_permission('add_agenda_item_note')
    can_archive_note = check_permission('archive_agenda_item_note')

    if request.method == 'POST' and can_add_note:
        content = request.form.get('content')
        if content:
            note = AgendaItemNote(
                agenda_item_id=agenda_item_id,
                user_id=current_user.id,
                datetime=datetime.utcnow(),
                content=content
            )
            db.session.add(note)
            db.session.commit()
            flash('Note added successfully.', 'success')
            return redirect(url_for('event_mgmt.edit_agenda_item', item_id=agenda_item_id))
        else:
            flash('Note content cannot be empty.', 'danger')

    return render_template('agenda_item_notes.html', agenda_item=agenda_item, notes=agenda_item.filtered_notes,
                           can_add_note=can_add_note, can_archive_note=can_archive_note)


@bp.route('/agenda_item/<int:item_id>/confirm', methods=['POST'])
@login_required
@check_permission('confirm_agenda_item')
def confirm_agenda_item(item_id):
    item = AgendaItem.query.get_or_404(item_id)
    item.status = AgendaItemStatus.CONFIRMED
    db.session.commit()
    flash('Agenda item confirmed successfully.', 'success')
    return redirect(url_for('event_mgmt.edit_agenda_item', item_id=item_id))


@bp.route('/agenda_item/<int:item_id>/reject', methods=['POST'])
@login_required
@check_permission('reject_agenda_item')
def reject_agenda_item(item_id):
    item = AgendaItem.query.get_or_404(item_id)
    item.status = AgendaItemStatus.UNSCHEDULED
    item.lecturer_id = None
    db.session.commit()
    flash('Agenda item rejected successfully.', 'success')
    return redirect(url_for('event_mgmt.edit_agenda_item', item_id=item_id))


@bp.route('/agenda_item_note/<int:note_id>/archive', methods=['POST'])
@login_required
@check_permission('archive_agenda_item_note')
def archive_agenda_item_note(note_id):
    note = AgendaItemNote.query.get_or_404(note_id)
    agenda_item_id = note.agenda_item_id
    note.delete()
    flash('Note archived successfully.', 'success')
    return redirect(url_for('event_mgmt.edit_agenda_item', item_id=agenda_item_id))

