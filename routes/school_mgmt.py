from flask import Blueprint, render_template, redirect, url_for, request, current_app, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from models import db, School, User, PupilCourse, AgendaItem, Pupil, Course

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
            new_pupil = Pupil(name=pupil_name)
            school.pupils.append(new_pupil)
            db.session.add(new_pupil)
            db.session.commit()
            flash('Pupil added successfully.', 'success')
        return redirect(url_for('school_mgmt.school_pupils', school_id=school.id))

    return render_template('pupils.html', school=school)


@bp.route('/remove-pupil/<int:pupil_id>', methods=['POST'])
@login_required
def remove_pupil(pupil_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    school_id = Pupil.school_id
    db.session.delete(pupil)
    db.session.commit()
    flash('Pupil removed successfully.', 'info')
    return redirect(request.referrer or url_for('school_mgmt.school_pupils', school_id=school_id))


@bp.route('/pupil-courses')
@login_required
def pupil_courses():
    if current_user.role == 'school_contact':
        school = School.query.filter_by(contact_email=current_user.username).first()
        if not school:
            flash("School not found for current user.", "danger")
            return redirect(url_for('dashboard'))
        records = PupilCourse.query.join(Pupil).join(Course).filter(Course.school_id == school.id).all()
    elif current_user.role == 'lecturer':
        # Get all courses where the lecturer is linked to an agenda item
        lecturer_agendas = AgendaItem.query.filter_by(lecturer_id=current_user.id).all()
        course_ids = list(set(a.event.course_id for a in lecturer_agendas))
        records = PupilCourse.query.filter(PupilCourse.course_id.in_(course_ids)).all()
    else:
        # Default: admins or other roles see everything
        records = PupilCourse.query.all()

    return render_template('pupil_courses.html', pupil_courses=records)

