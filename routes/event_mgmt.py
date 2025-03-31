from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, School, Program, Course, Event, AgendaItem, TemplateCourse, TemplateEvent, TemplateAgendaItem

bp = Blueprint('event_mgmt', __name__)

