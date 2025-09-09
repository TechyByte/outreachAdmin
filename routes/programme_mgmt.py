import flask
from flask import Blueprint, render_template, redirect, url_for, request, current_app, flash
from flask_login import login_required
from sqlalchemy.orm import selectinload

from models import db, Program

from utils import check_permission, has_permission

bp = Blueprint('programme_mgmt', __name__)


# Programs
@bp.route('/programs', methods=['GET', 'POST'])
@login_required
@check_permission('view_programs')
def manage_programs():
    """Handles displaying and adding programs."""
    if request.method == 'POST' and has_permission("add_program"):  # Handle form submission
        name = request.form['name']
        new_program = Program(name=name)

        with current_app.app_context():
            db.session.add(new_program)
            db.session.commit()

        flash('Program "{}" successfully added.'.format(name), 'success')
        return redirect(url_for('programme_mgmt.manage_programs'))

    with current_app.app_context():
        programs = db.session.query(Program).options(selectinload(Program.schools)).all()

    return render_template('programs.html', programs=programs)
