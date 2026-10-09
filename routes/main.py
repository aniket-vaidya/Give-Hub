from flask import Blueprint, render_template, session

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    session.pop('_flashed_messages', None)
    return render_template('index.html')

@main_bp.route('/about_us')
def about_us():
    return render_template('about_us.html')

@main_bp.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')