from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User

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
                return redirect(url_for('dashboard.home'))
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


# noinspection PyArgumentList
@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password=hashed_password, configured_role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

### Proposed integrating Office 365 login
#
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if app.config['USE_O365']:
#         if request.method == 'POST':
#             email = request.form.get('email')
#             o365_user = o365_interface.find_staff(email)
#             if o365_user:
#                 user = User.get_or_create_o365_user(
#                     o365_id=o365_user['id'],
#                     email=o365_user['mail'],
#                     username=o365_user['displayName']
#                 )
#                 # Log the user in
#                 login_user(user)
#                 flash('Logged in successfully via Office 365.', 'success')
#                 return redirect(url_for('index'))
#             else:
#                 flash('Office 365 user not found.', 'danger')
#         return render_template('o365_login.html')  # Create a template for O365 login
#     # ...existing Flask-Login logic for non-O365 login...
#     return render_template('login.html')
#
#
# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if app.config['USE_O365']:
#         if request.method == 'POST':
#             email = request.form.get('email')
#             o365_user = o365_interface.find_staff(email)
#             if o365_user:
#                 user = User.get_or_create_o365_user(
#                     o365_id=o365_user['id'],
#                     email=o365_user['mail'],
#                     username=o365_user['displayName']
#                 )
#                 flash('Signed up successfully via Office 365.', 'success')
#                 return redirect(url_for('login'))
#             else:
#                 flash('Office 365 user not found.', 'danger')
#         return render_template('o365_signup.html')  # Create a template for O365 signup
#     # ...existing sign-up logic for non-O365 signup...
#     return render_template('signup.html')
#
