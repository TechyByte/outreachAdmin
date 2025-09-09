from flask import Blueprint, render_template, redirect, url_for, request, current_app, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from math import ceil  # Add this import for pagination
from utils import check_permission, has_permission

from models import db, School, User, Program, Course

bp = Blueprint('school_mgmt', __name__)


@bp.route('/schools', methods=['GET', 'POST'])
@login_required
@check_permission("view_school")
def manage_schools():
    """Handles displaying and adding schools."""
    if request.method == 'POST' and has_permission("add_school"):  # Handle form submission
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
        users = User.query.all()
        schools_query = db.session.query(School).options(joinedload(School.programs))

        # Fetch distinct values for filters
        all_types = db.session.query(School.type_of_establishment).distinct().all()
        all_phases = db.session.query(School.phase_of_education).distinct().all()

        # Apply filters
        type_filter = request.args.get('type')
        phase_filter = request.args.get('phase')
        search_filter = request.args.get('search')

        if type_filter:
            schools_query = schools_query.filter(School.type_of_establishment == type_filter)
        if phase_filter:
            schools_query = schools_query.filter(School.phase_of_education == phase_filter)
        if search_filter:
            search_filter = search_filter.lower()
            schools_query = schools_query.filter(
                (School.name.ilike(f"%{search_filter}%")) |
                (School.street.ilike(f"%{search_filter}%")) |
                (School.town.ilike(f"%{search_filter}%")) |
                (School.postcode.ilike(f"%{search_filter}%")) |
                (School.head_name.ilike(f"%{search_filter}%")) |
                (School.contact_name.ilike(f"%{search_filter}%")) |
                (School.urn.ilike(f"%{search_filter}%")) |
                (School.establishment_number.ilike(f"%{search_filter}%"))
            )

        # Pagination logic
        page = int(request.args.get('page', 1))
        per_page = 10  # Number of schools per page
        total_schools = schools_query.count()
        total_pages = ceil(total_schools / per_page)
        schools = schools_query.offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        'schools.html',
        schools=schools,
        users=users,
        page=page,
        total_pages=total_pages,
        pagination_range=range(max(1, page - 2), min(total_pages + 1, page + 3)),  # Limit to 5 pages around the current page
        type_filter=type_filter,
        phase_filter=phase_filter,
        search_filter=search_filter,
        all_types=[t[0] for t in all_types if t[0]],  # Extract non-null values
        all_phases=[p[0] for p in all_phases if p[0]]  # Extract non-null values
    )


@bp.route('/schools/<int:school_id>/delete', methods=['GET'])
@login_required
@check_permission("delete_school")
def delete_school(school_id):
    with current_app.app_context():
        school = School.query.get(school_id)

        if not school:
            return "School not found", 404

        db.session.delete(school)
        db.session.commit()

    return redirect(url_for('school_mgmt.manage_schools'))


@bp.route('/school/<int:school_id>/update', methods=['POST'])
@login_required
@check_permission("edit_school")
def update_school(school_id):
    school = School.query.get_or_404(school_id)
    school.name = request.form['name']
    school.contact_name = request.form['contact_name']
    school.contact_email = request.form['contact_email']
    school.contact_phone = request.form['contact_phone']
    db.session.commit()
    flash('School details updated successfully.', 'success')
    return redirect(url_for('school_mgmt.manage_schools'))


@bp.route('/user/<int:user_id>/assign', methods=['POST'])
@login_required
@check_permission("edit_school")
def assign_user(user_id):
    user = User.query.get_or_404(user_id)
    user.school_id = request.form['school_id']
    db.session.commit()
    flash('User assigned to school successfully.', 'success')
    return redirect(url_for('school_mgmt.manage_schools'))


@bp.route('/user/<int:user_id>/unassign', methods=['POST'])
@login_required
@check_permission("edit_school")
def unassign_user(user_id):
    user = User.query.get_or_404(user_id)
    user.school_id = None
    db.session.commit()
    flash('User unassigned from school successfully.', 'success')
    return redirect(url_for('school_mgmt.manage_schools'))


@bp.route('/school/<int:school_id>/program/<int:program_id>', methods=['GET'])
@login_required
@check_permission("view_school")
@check_permission("view_programs")
def manage_school_program(school_id, program_id):
    """View and manage courses, events, and agenda items for a school-program."""
    school = School.query.get_or_404(school_id)
    program = Program.query.get_or_404(program_id)
    courses = Course.query.filter_by(school_id=school_id, program_id=program_id).all()

    # Fetch events and agenda items based on user-configurable filters
    include_events = request.args.get('include_events', 'true') == 'true'
    include_agenda_items = request.args.get('include_agenda_items', 'true') == 'true'

    return render_template(
        'manage_school_program.html',
        school=school,
        program=program,
        courses=courses,
        include_events=include_events,
        include_agenda_items=include_agenda_items
    )


@bp.route('/schools/search', methods=['GET'])
@login_required
@check_permission("view_school")
def search_schools():
    """Handles AJAX requests for searching schools."""
    query = request.args.get('query', '').strip().lower()
    if len(query) < 3:
        return []

    schools = School.query.filter(
        (School.name.ilike(f"%{query}%")) |
        (School.street.ilike(f"%{query}%")) |
        (School.town.ilike(f"%{query}%")) |
        (School.postcode.ilike(f"%{query}%")) |
        (School.head_name.ilike(f"%{query}%")) |
        (School.contact_name.ilike(f"%{query}%")) |
        (School.urn.ilike(f"%{query}%")) |
        (School.establishment_number.ilike(f"%{query}%"))
    ).all()

    return [{'id': school.id, 'name': school.name, 'urn': school.urn} for school in schools]

