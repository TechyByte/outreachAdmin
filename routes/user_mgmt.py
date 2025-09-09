from flask import Blueprint, redirect, url_for, request, flash, render_template
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from models import db, User, valid_user_roles
from utils import check_permission

bp = Blueprint('user_mgmt', __name__)


# 🔹 Delete a User (Only Admins Can Do This)
@bp.route('/delete_user', methods=['POST'])
@login_required
@check_permission('delete_user')
def delete_user():
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)

    if user:
        if user.configured_role == 'admin' and current_user.role != 'admin':
            flash("You do not have permission to delete an admin user.", "danger")
            return redirect(url_for('user_mgmt.user_list'))
        if user.id == current_user.id:
            flash("You cannot delete your own account.", "danger")
            return redirect(url_for('user_mgmt.user_list'))
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully!", "success")
    else:
        flash("User not found.", "danger")

    return redirect(url_for('user_mgmt.user_list'))


@bp.route('/create_user', methods=['POST'])
@login_required
@check_permission('create_user')
def create_user():

    username = request.form.get('username')
    display_name = request.form.get('display_name')
    specialty = request.form.get('specialty')
    email = request.form.get('email')
    configured_role = request.form.get('configured_role') or None
    password = request.form.get('password')

    if current_user.role != 'admin' and request.form.get('configured_role') == 'admin':
        flash("Non-admin may not edit admin account!", "danger")
        return redirect(url_for('user_mgmt.user_list'))

    if not username or not email or not password:
        flash("Username, email, and password are required.", "danger")
        return redirect(url_for('user_mgmt.user_list'))

    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "danger")
        return redirect(url_for('user_mgmt.user_list'))
    if User.query.filter_by(email=email).first():
        flash("Email already exists.", "danger")
        return redirect(url_for('user_mgmt.user_list'))

    user = User(
        username=username,
        display_name=display_name,
        specialty=specialty,
        email=email,
        configured_role=configured_role,
        password=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()
    flash("User created successfully!", "success")
    return redirect(url_for('user_mgmt.user_list'))


@bp.route('/edit_user', methods=['POST'])
@login_required
@check_permission('edit_user')
def edit_user():
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('user_mgmt.user_list'))

    if current_user.role != 'admin' and (user.configured_role == 'admin' or request.form.get('configured_role') == 'admin'):
        flash("Non-admin may not edit admin account!", "danger")
        return redirect(url_for('user_mgmt.user_list'))

    # Only update fields that are allowed
    user.display_name = request.form.get('display_name')
    user.specialty = request.form.get('specialty')
    user.email = request.form.get('email')
    user.configured_role = request.form.get('configured_role') or None
    db.session.commit()
    flash("User updated successfully!", "success")
    return redirect(url_for('user_mgmt.user_list'))


@bp.route('/user-list')
@login_required
@check_permission('user_list')
def user_list():
    users = User.query.all()
    return render_template('user_list.html', users=users, valid_user_roles=valid_user_roles)
