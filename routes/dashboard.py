from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models import db, User, School, Program, Course, Event, AgendaItem, TemplateCourse, TemplateEvent, TemplateAgendaItem

bp = Blueprint('dashboard', __name__)


@bp.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@bp.route('/school-dashboard')
@login_required
def school_dashboard():
    if current_user.role != 'school_contact' and current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    school = School.query.filter_by(user_id=current_user.id).first()
    return render_template('school_dashboard.html', school=school)

@bp.route('/lecturer-dashboard')
@login_required
def lecturer_dashboard():
    if current_user.role != 'lecturer' and current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    agenda_items = AgendaItem.query.filter_by(lecturer_id=current_user.id)  # Assigned agenda items
    return render_template('lecturer_dashboard.html', agenda_items=agenda_items)

