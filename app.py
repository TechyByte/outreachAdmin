import os
from flask import Flask, render_template, redirect, url_for, request, flash


from models import db, School, Program, TemplateCourse, TemplateEvent, TemplateAgendaItem, User, \
    Event, AgendaItem, Course  # Import db from models.py
from init_db import initialize_database  # Import initialization function
from sqlalchemy.orm import joinedload, selectinload
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # Initialize db with the app

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/register', methods=['GET', 'POST'])
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
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
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
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'lecturer':
                return redirect(url_for('lecturer_dashboard'))
            elif user.role == 'school_contact':
                return redirect(url_for('school_dashboard'))
            else:
                flash('Unknown user role.', 'danger')
                return redirect(url_for('login'))

        flash('Invalid credentials.', 'danger')

    return render_template('login.html')


@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@app.route('/lecturer-dashboard')
@login_required
def lecturer_dashboard():
    if current_user.role != 'lecturer' and current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    agenda_items = AgendaItem.query.filter_by(lecturer_id=current_user.id)  # Assigned agenda items
    return render_template('lecturer_dashboard.html', agenda_items=agenda_items)

@app.route('/school-dashboard')
@login_required
def school_dashboard():
    if current_user.role != 'school_contact' and current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    school = School.query.filter_by(user_id=current_user.id).first()
    return render_template('school_dashboard.html', school=school)

# 🔹 Delete a User (Only Admins Can Do This)
@app.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    """Deletes a user (Admin Only)."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('admin_dashboard'))

    user_id = request.form.get('user_id')
    user = User.query.get(user_id)

    if user:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully!", "success")
    else:
        flash("User not found.", "danger")

    return redirect(url_for('admin_dashboard'))

# 🔹 Change User Role (Admin Only)
@app.route('/change_user_type', methods=['POST'])
@login_required
def change_user_type():
    """Changes the role of a user (Admin Only)."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('admin_dashboard'))

    user_id = request.form.get('user_id')
    new_role = request.form.get('new_role')

    user = User.query.get(user_id)

    if user:
        user.role = new_role
        db.session.commit()
        flash(f"User role updated to {new_role}!", "success")
    else:
        flash("User not found.", "danger")

    return redirect(url_for('admin_dashboard'))



@app.route('/logout')
@login_required
def logout():
    """Handles user logout."""
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


def check_database():
    """Ensures the database is created and initialized before running the app."""
    if not os.path.exists("database.db"):
        print("📦 No database found. Initializing...")
        with app.app_context():
            initialize_database()
    else:
        with app.app_context():
            inspector = db.engine.inspect(db.engine)
            if not inspector.has_table("school"):
                print("⚠️ Table 'school' not found. Recreating database...")
                initialize_database()


@app.route('/schools', methods=['GET', 'POST'])
def manage_schools():
    """Handles displaying and adding schools."""
    if request.method == 'POST':  # Handle form submission
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

        with app.app_context():  # Ensure DB context
            db.session.add(new_school)
            db.session.commit()

        return redirect(url_for('manage_schools'))  # Redirect to refresh list

    # ✅ Fix: Use `joinedload()` to eagerly load programs
    with app.app_context():
        schools = db.session.query(School).options(joinedload(School.programs)).all()

    return render_template('schools.html', schools=schools)

# Programs
@app.route('/programs', methods=['GET', 'POST'])
def manage_programs():
    """Handles displaying and adding programs."""
    if request.method == 'POST':  # Handle form submission
        name = request.form['name']
        new_program = Program(name=name)

        with app.app_context():
            db.session.add(new_program)
            db.session.commit()

        return redirect(url_for('manage_programs'))  # Refresh list

    # ✅ Fix: Use `selectinload()` for many-to-many
    with app.app_context():
        programs = db.session.query(Program).options(selectinload(Program.schools)).all()

    return render_template('programs.html', programs=programs)


@app.route('/enroll', methods=['GET', 'POST'])
def enroll():
    """Handles school enrollment and copies templates into independent records."""
    if request.method == 'POST':
        school_id = request.form.get('school_id')
        program_id = request.form.get('program_id')

        with app.app_context():
            school = School.query.get(school_id)
            program = Program.query.get(program_id)

            if not school or not program:
                return "Invalid school or program selection", 400

            # Prevent duplicate enrollment
            if program not in school.programs:
                school.programs.append(program)

                # Copy courses from template
                template_courses = TemplateCourse.query.filter_by(program=Program.id).all()
                for template_course in template_courses:
                    new_course = Course(name=template_course.name, program_id=program.id, school_id=school.id)
                    db.session.add(new_course)
                    db.session.commit()

                    # Copy events from template course
                    template_events = TemplateEvent.query.filter_by(template_course_id=template_course.id).all()
                    for template_event in template_events:
                        new_event = Event(name=template_event.name, course_id=new_course.id, school_id=school.id)
                        db.session.add(new_event)
                        db.session.commit()

                        # Copy agenda items from template event
                        template_agendas = TemplateAgendaItem.query.filter_by(template_event_id=template_event.id).all()
                        for template_agenda in template_agendas:
                            new_agenda = AgendaItem(title=template_agenda.title, event_id=new_event.id)
                            db.session.add(new_agenda)

                db.session.commit()

        return redirect(url_for('manage_enrollment'))

    with app.app_context():
        schools = School.query.options(selectinload(School.programs)).all()
        programs = Program.query.all()

    return render_template('enroll.html', schools=schools, programs=programs)


@app.route('/unenroll', methods=['POST'])
def unenroll():
    """Handles school unenrollment and removes independent records."""
    school_id = request.form.get('school_id')
    program_id = request.form.get('program_id')

    with app.app_context():
        school = School.query.get(school_id)
        program = Program.query.get(program_id)

        if not school or not program:
            return "Invalid school or program selection", 400

        # Remove the school from the program
        if program in school.programs:
            school.programs.remove(program)

            # Delete courses, events, and agenda items specific to this school-program
            courses_to_delete = Course.query.filter_by(program_id=program.id, school_id=school.id).all()
            for course in courses_to_delete:
                events_to_delete = Event.query.filter_by(course_id=course.id).all()
                for event in events_to_delete:
                    AgendaItem.query.filter_by(event_id=event.id).delete()
                Event.query.filter_by(course_id=course.id).delete()
                db.session.delete(course)

            db.session.commit()

    return redirect(url_for('manage_enrollment'))


@app.route('/manage-enrollment')
def manage_enrollment():
    """Displays schools and their enrolled programs."""
    with app.app_context():
        schools = db.session.query(School).options(selectinload(School.programs)).all()
        programs = Program.query.all()

    return render_template('enroll.html', schools=schools, programs=programs)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/manage-templates', methods=['GET', 'POST'])
@login_required
def manage_templates():
    """Allows admins to manage template courses and agenda items."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    program_id = request.args.get('program_id')
    course_id = request.args.get('course_id')

    selected_program = None
    selected_course = None
    assigned_courses = []
    available_courses = []

    with app.app_context():
        programs = Program.query.all()

        if program_id:
            selected_program = Program.query.get(program_id)
            assigned_courses = selected_program.template_courses  # ✅ Get assigned courses via many-to-many
            available_courses = TemplateCourse.query.filter(~TemplateCourse.programs.any(Program.id == selected_program.id)).all()  # ✅ Get unassigned courses

        if course_id:
            selected_course = TemplateCourse.query.get(course_id)

    return render_template(
        "manage_templates.html",
        programs=programs,
        selected_program=selected_program,
        assigned_courses=assigned_courses,
        available_courses=available_courses,
        selected_course=selected_course
    )


@app.route('/assign-template-course', methods=['POST'])
@login_required
def assign_template_course():
    """Assigns a template course to a program (Allows Multiple Assignments)."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('manage_templates'))

    course_id = request.form.get('course_id')
    program_id = request.form.get('program_id')

    with app.app_context():
        program = Program.query.get(program_id)
        course = TemplateCourse.query.get(course_id)

        if course and program and course not in program.template_courses:
            program.template_courses.append(course)  # ✅ Assign course to multiple programs
            db.session.commit()

    flash("Template course assigned successfully!", "success")
    return redirect(url_for('manage_templates', program_id=program_id))


@app.route('/remove-template-course', methods=['POST'])
@login_required
def remove_template_course():
    """Removes a template course from a specific program without deleting it."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('manage_templates'))

    course_id = request.form.get('course_id')
    program_id = request.form.get('program_id')

    with app.app_context():
        program = Program.query.get(program_id)
        course = TemplateCourse.query.get(course_id)

        if program and course and course in program.template_courses:
            program.template_courses.remove(course)  # ✅ Unassign without deleting
            db.session.commit()

    flash("Template course unassigned from program.", "warning")
    return redirect(url_for('manage_templates', program_id=program_id))



@app.route('/edit_agenda_item', methods=['POST'])
@login_required
def edit_agenda_item():
    """Allows editing of template agenda items."""
    if current_user.role not in ['admin', 'lecturer']:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('manage_templates'))

    agenda_item_id = request.form.get('agenda_item_id')
    new_title = request.form.get('new_title')

    with app.app_context():
        agenda_item = TemplateAgendaItem.query.get(agenda_item_id)
        if agenda_item:
            agenda_item.title = new_title
            db.session.commit()
            flash("Agenda item updated successfully!", "success")

    return redirect(url_for('manage_templates'))


@app.route('/edit-template-course/<int:course_id>', methods=['GET'])
@login_required
def edit_template_course(course_id):
    """Displays the template course and allows editing of events & agenda items."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    with app.app_context():
        selected_course = TemplateCourse.query.get(course_id)

        if not selected_course:
            flash("Course not found.", "danger")
            return redirect(url_for('manage_templates'))

        # ✅ Get the first program this template course is assigned to
        selected_program = selected_course.programs[0] if selected_course.programs else None

    return render_template(
        "edit_template_course.html",
        selected_course=selected_course,
        selected_program=selected_program
    )

@app.route('/add-template-event', methods=['POST'])
@login_required
def add_template_event():
    """Adds a new template event to a course."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('manage_templates'))

    course_id = request.form.get('course_id')
    event_name = request.form.get('event_name')

    with app.app_context():
        new_event = TemplateEvent(name=event_name, template_course_id=course_id)
        db.session.add(new_event)
        db.session.commit()

    flash("New event added successfully!", "success")
    return redirect(url_for('edit_template_course', course_id=course_id))


@app.route('/edit-template-event', methods=['POST'])
@login_required
def edit_template_event():
    """Edits an existing template event."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('manage_templates'))

    event_id = request.form.get('event_id')
    new_name = request.form.get('new_event_name')

    with app.app_context():
        event = TemplateEvent.query.get(event_id)
        if event:
            event.name = new_name
            db.session.commit()

    flash("Event updated successfully!", "success")
    return redirect(url_for('edit_template_course', course_id=event.template_course_id))


@app.route('/delete-template-event', methods=['POST'])
@login_required
def delete_template_event():
    """Deletes a template event and its associated agenda items."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('manage_templates'))

    event_id = request.form.get('event_id')

    with app.app_context():
        event = TemplateEvent.query.get(event_id)
        if event:
            db.session.delete(event)
            db.session.commit()

    flash("Event deleted successfully!", "danger")
    return redirect(url_for('edit_template_course', course_id=event.template_course_id))


@app.route('/add-template-agenda-item', methods=['POST'])
@login_required
def add_template_agenda_item():
    """Adds a new agenda item to a template event."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('manage_templates'))

    event_id = request.form.get('event_id')
    agenda_title = request.form.get('agenda_title')

    with app.app_context():
        new_agenda = TemplateAgendaItem(title=agenda_title, template_event_id=event_id)
        db.session.add(new_agenda)
        db.session.commit()

    flash("New agenda item added successfully!", "success")
    return redirect(url_for('edit_template_course', course_id=TemplateEvent.query.get(event_id).template_course_id))


@app.route('/edit-template-agenda-item', methods=['POST'])
@login_required
def edit_template_agenda_item():
    """Edits an existing template agenda item."""
    if current_user.role != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('manage_templates'))

    agenda_item_id = request.form.get('agenda_item_id')
    new_title = request.form.get('new_agenda_title')

    with app.app_context():
        agenda_item = TemplateAgendaItem.query.get(agenda_item_id)
        if agenda_item:
            agenda_item.title = new_title
            db.session.commit()

    flash("Agenda item updated successfully!", "success")
    return redirect(url_for('edit_template_course', course_id=agenda_item.event.template_course_id))


# @app.route('/delete-template-agenda-item', methods=['POST'])
# @login_required
# def delete_template_agenda_item():
#     """Deletes a template agenda item from a template event."""
#     if current_user.role != 'admin':
#         flash("Unauthorized access!", "danger")
#         return redirect(url_for('manage_templates'))
#
#     agenda_item_id = request.form.get('agenda_item_id')
#
#     with app.app_context():
#         agenda_item = TemplateAgendaItem.query.get(agenda_item_id)
#         if agenda_item:
#             course_id = agenda_item.event.template_course_id  # Get associated course before deleting
#             db.session.delete(agenda_item)
#             db.session.commit()
#             flash("Agenda item deleted successfully!", "danger")
#             return redirect(url_for('edit_template_course', course_id=course_id))
#
#     flash("Agenda item not found!", "warning")
#     return redirect(url_for('manage_templates'))
#


if __name__ == '__main__':
    app.run(debug=True)
