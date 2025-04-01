"""
Authentication decorators for route protection
"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user

def admin_required(f):
    """
    Decorator to require admin privileges for a route
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            if current_user.is_authenticated:
                return abort(403)
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def approved_required(f):
    """
    Decorator to require approved account status for a route
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_approved:
            flash('Your account needs to be approved to access this page.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function