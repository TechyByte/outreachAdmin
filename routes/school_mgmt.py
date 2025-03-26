from flask import Blueprint, render_template, redirect, url_for, request, current_app, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from models import db, School, User

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

    # ✅ Fix: Use `joinedload()` to eagerly load programs
    with current_app.app_context():
        schools = db.session.query(School).options(joinedload(School.programs)).all()

    return render_template('schools.html', schools=schools)


@bp.route('/school/<int:school_id>/pupils', methods=['GET', 'POST'])
@login_required
def school_pupils(school_id):
    school = School.query.get_or_404(school_id)

    if request.method == 'POST':
        pupil_name = request.form['pupil_name']
        if pupil_name:
            new_pupil = User(username=pupil_name, role='pupil')
            school.pupils.append(new_pupil)
            db.session.add(new_pupil)
            db.session.commit()
            flash('Pupil added successfully.', 'success')
        return redirect(url_for('school_mgmt.school_pupils', school_id=school.id))

    return render_template('pupils.html', school=school)


@bp.route('/remove-pupil/<int:pupil_id>', methods=['POST'])
@login_required
def remove_pupil(pupil_id):
    pupil = User.query.get_or_404(pupil_id)
    db.session.delete(pupil)
    db.session.commit()
    flash('Pupil removed successfully.', 'info')
    return redirect(request.referrer or url_for('school_mgmt.school_pupils', school_id=1))
