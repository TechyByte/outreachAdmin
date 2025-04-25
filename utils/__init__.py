import yaml


# Permissions check helper (utils/permissions.py)
from flask import flash, redirect, url_for
from flask_login import current_user

with open('permissions.yaml') as f:
    perms = yaml.safe_load(f)

def check_permission(action):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                # attempt to get guest permissions if not authenticated
                try:
                    user_perms = perms.get("guest", {})
                except AttributeError:
                    flash("Guest access is not configured. No permissions found for role 'guest'", "danger")
                    return redirect(url_for("auth.login"))
            else:
                # if authenticated, attempt to get user permissions based on role
                try:
                    user_perms = perms.get(current_user.role, {})
                except AttributeError:
                    #if user role is not found in permissions, check for default user permissions
                    try:
                        user_perms = perms.get("user", {})
                    except AttributeError:
                        flash("User access is not configured. No permissions found for role 'user'", "danger")
                        return redirect(url_for("auth.login"))
            if not user_perms.get(action, False):
                flash('Permission denied.', 'danger')
                return redirect(url_for('index'))
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
