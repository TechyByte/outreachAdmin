from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Location
from utils import check_permission

bp = Blueprint('config_mgmt', __name__)

@bp.route('/admin/location', methods=['GET', 'POST'])
@login_required
@check_permission("manage_locations")
def location():
    if request.method == 'POST':
        # Handle creation of a new Location
        if request.form.get('location_id'):
            # Update existing Location
            location_id = request.form.get('location_id')
            location = Location.query.get(location_id)
            if location:
                if request.form.get('name'):
                    location.name = request.form.get('name')
                if request.form.get('address'):
                    location.address = request.form.get('address')
                db.session.commit()
                flash('Location updated successfully.', 'success')
            else:
                flash('Location not found.', 'danger')
        else:
            # Create a new Location
            name = request.form.get('name')
            address = request.form.get('address')
            if name:
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


@bp.route('/delete-location/<int:location_id>', methods=['POST'])
@login_required
@check_permission('manage_locations')
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    db.session.delete(location)
    db.session.commit()
    flash("Location deleted successfully!", "success")
    return redirect(url_for('config_mgmt.location'))