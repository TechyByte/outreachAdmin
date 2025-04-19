from flask import Blueprint, render_template, redirect, url_for, request, current_app, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import db, School, User, Program, Course

bp = Blueprint('school_mgmt', __name__)


@bp.route('/schools', methods=['GET', 'POST'])
@login_required
def manage_schools():
    """Handles displaying and adding schools."""
    if request.method == 'POST' and current_user.role == 'admin':  # Handle form submission
        name = request.form['name']
        contact_name = request.form['contact_name']
        contact_email = request.form['contact_email']
        contact_phone = request.form['contact_phone']

        new_school = School(
            name=name,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone
        )

        with current_app.app_context():  # Ensure DB context
            db.session.add(new_school)
            db.session.commit()

        return redirect(url_for('school_mgmt.manage_schools'))  # Redirect to refresh list

    with current_app.app_context():
        users = User.query.all()
        schools = db.session.query(School).options(joinedload(School.programs)).all()

    return render_template('schools.html', schools=schools, users=users)


@bp.route('/schools/<int:school_id>/delete', methods=['GET'])
@login_required
def delete_school(school_id):
    """Handles deleting a school."""
    if current_user.role != 'admin':
        return "Unauthorized", 403

    with current_app.app_context():
        school = School.query.get(school_id)

        if not school:
            return "School not found", 404

        db.session.delete(school)
        db.session.commit()

    return redirect(url_for('school_mgmt.manage_schools'))


@bp.route('/school/<int:school_id>/update', methods=['POST'])
@login_required
def update_school(school_id):
    school = School.query.get_or_404(school_id)
    school.name = request.form['name']
    school.contact_name = request.form['contact_name']
    school.contact_email = request.form['contact_email']
    school.contact_phone = request.form['contact_phone']
    db.session.commit()
    flash('School details updated successfully.', 'success')
    return redirect(url_for('school_mgmt.manage_schools'))


@bp.route('/user/<int:user_id>/assign', methods=['POST'])
@login_required
def assign_user(user_id):
    user = User.query.get_or_404(user_id)
    user.school_id = request.form['school_id']
    db.session.commit()
    flash('User assigned to school successfully.', 'success')
    return redirect(url_for('school_mgmt.manage_schools'))


@bp.route('/user/<int:user_id>/unassign', methods=['POST'])
@login_required
def unassign_user(user_id):
    user = User.query.get_or_404(user_id)
    user.school_id = None
    db.session.commit()
    flash('User unassigned from school successfully.', 'success')
    return redirect(url_for('school_mgmt.manage_schools'))


@bp.route('/school/<int:school_id>/program/<int:program_id>', methods=['GET'])
@login_required
def manage_school_program(school_id, program_id):
    """View and manage courses, events, and agenda items for a school-program."""
    school = School.query.get_or_404(school_id)
    program = Program.query.get_or_404(program_id)
    courses = Course.query.filter_by(school_id=school_id, program_id=program_id).all()

    # Fetch events and agenda items based on user-configurable filters
    include_events = request.args.get('include_events', 'true') == 'true'
    include_agenda_items = request.args.get('include_agenda_items', 'true') == 'true'

    return render_template(
        'manage_school_program.html',
        school=school,
        program=program,
        courses=courses,
        include_events=include_events,
        include_agenda_items=include_agenda_items
    )
