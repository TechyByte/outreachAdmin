from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, School, Program, Course, Event, AgendaItem, TemplateCourse, TemplateEvent, TemplateAgendaItem

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')

            if user.role == 'admin':
                return redirect(url_for('dashboard.admin_dashboard'))
            elif user.role == 'lecturer':
                return redirect(url_for('dashboard.lecturer_dashboard'))
            elif user.role == 'school_contact':
                return redirect(url_for('dashboard.school_dashboard'))
            else:
                flash('Unknown user role.', 'danger')
                return redirect(url_for('auth.login'))

        flash('Invalid credentials.', 'danger')

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    """Handles user logout."""
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')
