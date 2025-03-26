from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, School, Program, Course, Event, AgendaItem, TemplateCourse, TemplateEvent, TemplateAgendaItem

bp = Blueprint('user_mgmt', __name__)

# 🔹 Delete a User (Only Admins Can Do This)
@bp.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    """Deletes a user (Admin Only)."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.admin_dashboard'))

    user_id = request.form.get('user_id')
    user = User.query.get(user_id)

    if user:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully!", "success")
    else:
        flash("User not found.", "danger")

    return redirect(url_for('dashboard.admin_dashboard'))

# 🔹 Change User Role (Admin Only)
@bp.route('/change_user_type', methods=['POST'])
@login_required
def change_user_type():
    """Changes the role of a user (Admin Only)."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.admin_dashboard'))

    user_id = request.form.get('user_id')
    new_role = request.form.get('new_role')

    user = User.query.get(user_id)

    if user:
        user.role = new_role
        db.session.commit()
        flash(f"User role updated to {new_role}!", "success")
    else:
        flash("User not found.", "danger")

    return redirect(url_for('dashboard.admin_dashboard'))
