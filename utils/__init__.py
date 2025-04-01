import yaml


# Permissions check helper (utils/permissions.py)
from flask import flash, redirect, url_for
from flask_login import current_user


def check_permission(action):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with open('permissions.yaml') as f:
                perms = yaml.safe_load(f)
            user_perms = perms.get(current_user.role, {})
            if not user_perms.get(action, False):
                flash('Permission denied.')
                return redirect(url_for('index'))
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
