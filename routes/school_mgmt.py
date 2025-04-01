from flask import Blueprint, render_template, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import db, School

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
        schools = db.session.query(School).options(joinedload(School.programs)).all()

    return render_template('schools.html', schools=schools)


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