from flask import Blueprint, render_template, redirect, url_for, request, current_app
from flask_login import login_required
from sqlalchemy.orm import selectinload

from models import db, Program

bp = Blueprint('programme_mgmt', __name__)


# Programs
@bp.route('/programs', methods=['GET', 'POST'])
@login_required
def manage_programs():
    """Handles displaying and adding programs."""
    if request.method == 'POST':  # Handle form submission
        name = request.form['name']
        new_program = Program(name=name)

        with current_app.app_context():
            db.session.add(new_program)
            db.session.commit()

        return redirect(url_for('manage_programs'))  # Refresh list

    with current_app.app_context():
        programs = db.session.query(Program).options(selectinload(Program.schools)).all()

    return render_template('programs.html', programs=programs)
