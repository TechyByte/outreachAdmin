from datetime import time, datetime

from flask import Flask, render_template, redirect, url_for, request, flash
from models import db, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from routes.auth import bp as auth_bp
from routes.dashboard import bp as dashboard_bp
from routes.enrolment import bp as enrolment_bp
from routes.user_mgmt import bp as user_mgmt_bp
from routes.school_mgmt import bp as school_mgmt_bp
from routes.programme_mgmt import bp as programme_mgmt_bp
from routes.event_mgmt import bp as event_mgmt_bp
from routes.template_mgmt import bp as template_mgmt_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

if __name__ == '__main__':
    app.run(debug=True)
