from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import User, School, AgendaItem, Event, Course
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
    n_days = int(request.args.get('n_days', 7))
    today = datetime.today().date()
    future = today + timedelta(days=n_days)
    # TODO: Include outer scope Program (via school_program)
    courses = Course.query \
        .join(Course.events) \
        .filter(((Event.date >= today) & (Event.date <= future)) | (Event.date == None)) \
        .options(joinedload(Course.events)) \
        .distinct() \
        .all()
    return render_template('schedule.html', courses=courses)

