import logging as logger
logging = logger.getLogger(__name__)
from datetime import datetime, timedelta

from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import login_required, current_user

from models import Event, db, AgendaItem, User, Course, AgendaItemStatus, EventNote, AgendaItemNote, Location, \
    valid_user_roles, School, Program, TemplateEvent
from utils import check_permission

bp = Blueprint('event_mgmt', __name__)


@bp.route('/course/<int:course_id>', methods=['GET', 'POST'])
@login_required
@check_permission('edit_course')
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    school = School.query.get_or_404(course.school_id)
    program = Program.query.get_or_404(course.program_id)
    if request.method == 'POST':
        course.name = request.form['name']
        db.session.commit()
        flash('Course updated.')
        return redirect(url_for('dashboard.admin_dashboard'))
    return render_template('edit_course.html', course=course, school=school, program=program)



@bp.route('/event/<int:event_id>', methods=['GET', 'POST'])
@login_required
@check_permission('edit_event')
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    course = db.session.query(Course).get(event.course_id)
    school = School.query.get_or_404(course.school_id)
    program = Program.query.get_or_404(course.program_id)
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
                           can_archive_note=check_permission('archive_event_note'),
                           can_view_note=check_permission('view_event_note'),
                           school=school, program=program)

@bp.route('/event/<int:event_id>/notes', methods=['GET', 'POST'])
@check_permission('view_event_note')
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
                datetime=datetime.now(),
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
    school = School.query.get_or_404(course.school_id)
    program = Program.query.get_or_404(course.program_id)

    can_add_note = check_permission('add_agenda_item_note')
    can_archive_note = check_permission('archive_agenda_item_note')
    can_view_note = check_permission('view_agenda_item_note')

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

        try:
            new_lecturer_id = int(request.form.get('lecturer_id'))
            if new_lecturer_id:
                if new_lecturer_id != item.lecturer_id:
                    # Change in lecturer
                    item.lecturer_id = new_lecturer_id
                    item.status = AgendaItemStatus.TENTATIVE
            else:
                # No lecturer assigned
                item.lecturer_id = None
                item.status = AgendaItemStatus.UNSCHEDULED
        except ValueError:
            logging.debug('Invalid lecturer ID')

        # if request.form.get('status') is not None:
        #     item.status = request.form.get('status') if request.form.get(
        #         'status') in AgendaItemStatus.__members__ else None
        #
        db.session.commit()
        flash('Agenda item updated.')
        #return redirect(url_for('event_mgmt.edit_event', event_id=item.event_id))
    return render_template('edit_agenda_item.html', item=item, lecturers=lecturers, course=course, event=event,
                           AgendaItemStatus=AgendaItemStatus, notes=item.filtered_notes,
                           can_add_note=can_add_note, can_archive_note=can_archive_note, can_view_note=can_view_note,
                           school=school, program=program)


@bp.route('/agenda_item/<int:agenda_item_id>/notes', methods=['GET', 'POST'])
@check_permission('view_agenda_item_note')

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
                datetime=datetime.now(),
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
    item = AgendaItem.query.get_or_404(item_id)
    item.status = AgendaItemStatus.CONFIRMED

    # Create a note to record the action
    note = AgendaItemNote(
        agenda_item_id=item_id,
        user_id=current_user.id,
        datetime=datetime.now(),
        content=f"Agenda item confirmed by {current_user.username}."
    )
    db.session.add(note)

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
    # Create a note to record the action
    note = AgendaItemNote(
        agenda_item_id=item_id,
        user_id=current_user.id,
        datetime=datetime.now(),
        content=f"Agenda item rejected by {current_user.username}."
    )
    db.session.add(note)
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


@bp.route('/course/<int:course_id>/create_event', methods=['GET', 'POST'])
@login_required
@check_permission('create_event')
def create_event(course_id):
    course = Course.query.get_or_404(course_id)
    templates = TemplateEvent.query.all()  # Fetch all template events
    if request.method == 'POST':
        event_name = request.form.get('name')
        template_id = request.form.get('template_id')
        new_event = Event(name=event_name, course_id=course.id, school_id=course.school_id)

        if template_id and template_id != "none":
            template = TemplateEvent.query.get(template_id)
            if template:
                db.session.add(new_event)
                db.session.commit()

                # Copy agenda items from template
                for template_item in template.template_agenda_items:
                    new_agenda_item = AgendaItem(
                        title=template_item.title,
                        event_id=new_event.id,
                        time=template_item.time,
                        duration=template_item.duration,
                        description=template_item.description
                    )
                    db.session.add(new_agenda_item)
        else:
            db.session.add(new_event)

        db.session.commit()
        flash('Event created successfully.', 'success')
        return redirect(url_for('event_mgmt.edit_course', course_id=course.id))

    return render_template('create_event.html', course=course, templates=templates)


@bp.route('/event/<int:event_id>/create_agenda_item', methods=['GET', 'POST'])
@login_required
@check_permission('add_agenda_item')
def create_agenda_item(event_id):
    event = Event.query.get_or_404(event_id)
    lecturers = User.query.filter((User.role == 'lecturer') | (User.role == 'admin')).all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        time = request.form.get('time')
        duration = request.form.get('duration')
        lecturer_id = request.form.get('lecturer_id')

        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('event_mgmt.create_agenda_item', event_id=event_id))

        new_item = AgendaItem(
            title=title,
            description=description,
            event_id=event_id,
            time=datetime.strptime(time, '%H:%M').time() if time else None,
            duration=timedelta(minutes=int(duration)) if duration else None,
            lecturer_id=int(lecturer_id) if lecturer_id and lecturer_id != "0" else None,
            status=AgendaItemStatus.TENTATIVE if lecturer_id and lecturer_id != "0" else AgendaItemStatus.UNSCHEDULED
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Agenda item created successfully.', 'success')
        return redirect(url_for('event_mgmt.edit_event', event_id=event_id))

    return render_template('create_agenda_item.html', event=event, lecturers=lecturers)
