from functools import wraps
from flask import session, flash, redirect, url_for

def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            flash('You need to be logged in to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    """
    Decorator factory to ensure a user has a specific role.
    Usage: @role_required('Admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'loggedin' not in session or session.get('role') != role_name:
                flash(f'Access denied. You must be a {role_name} to view this page.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator # This was the line with the error.
