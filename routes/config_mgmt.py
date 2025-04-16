from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Location

bp = Blueprint('config_mgmt', __name__)

@bp.route('/admin/location', methods=['GET', 'POST'])
@login_required
def location():
    if request.method == 'POST':
        # Handle creation of a new Location
        name = request.form.get('name')
        address = request.form.get('address')
        if name and address:
            new_location = Location(name=name, address=address)
            db.session.add(new_location)
            db.session.commit()
            flash('Location added successfully.', 'success')
        else:
            flash('Name and address are required.', 'danger')
        return redirect(url_for('config_mgmt.location'))

    # Fetch all Locations to display in the table
    locations = Location.query.all()
    return render_template('admin/location.html', locations=locations)