from datetime import time, datetime

from flask import Flask, render_template, request
from flask_login import LoginManager, login_required, current_user

from datetime import datetime, timedelta

from utils import check_permission
import os

from models import db, User, valid_user_roles
from routes.auth import bp as auth_bp
from routes.dashboard import bp as dashboard_bp
from routes.enrolment import bp as enrolment_bp
from routes.event_mgmt import bp as event_mgmt_bp
from routes.programme_mgmt import bp as programme_mgmt_bp
from routes.school_mgmt import bp as school_mgmt_bp
from routes.template_mgmt import bp as template_mgmt_bp
from routes.user_mgmt import bp as user_mgmt_bp
from routes.config_mgmt import bp as config_mgmt_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True
app.config['VALID_USER_ROLES'] = valid_user_roles



db.init_app(app)  # Initialize db with the app

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.template_filter('short_time')
def short_time_filter(value):
    if isinstance(value, (time, datetime)):
        return value.strftime('%H:%M')  # 24-hour format without seconds
    if isinstance(value, timedelta):
        hours = value.seconds // 3600
        mod_minutes = (value.seconds % 3600) // 60
        if hours >= 1:
            return f'{hours}h {mod_minutes}m'
        else:
            return f'{mod_minutes}m'
    return value


@app.route('/')
def index():
    return render_template('index.html')


app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(enrolment_bp)
app.register_blueprint(user_mgmt_bp)
app.register_blueprint(school_mgmt_bp)
app.register_blueprint(programme_mgmt_bp)
app.register_blueprint(event_mgmt_bp)
app.register_blueprint(template_mgmt_bp)
app.register_blueprint(config_mgmt_bp)

if __name__ == '__main__':
    app.run(debug=True)


@app.template_filter('mailto_link')
def mailto_link(event_or_item):
    template_path = os.path.join('mail_templates', 'default.txt')
    with open(template_path) as f:
        template = f.read()
    contact_email = event_or_item.event.school.contact_email if hasattr(event_or_item,
                                                                        'event') else event_or_item.school.contact_email
    body = template.format(
        school_name=event_or_item.event.school.name,
        event_name=event_or_item.event.name,
        date=str(event_or_item.event.date)
    )
    return f"mailto:{contact_email}?subject=Upcoming Event&body={body}"
