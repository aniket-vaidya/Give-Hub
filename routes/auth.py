from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import mysql.connector
from flask_mail import Message

from db import get_db
from extensions import mail
from decorators import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Both email and password are required.', 'danger')
            return render_template('auth/login.html', form_data={'email': email})

        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute('SELECT id, name, email, password, role FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                # Check if Medical Store or NGO is approved
                if user['role'] == 'Medical Store':
                    cursor.execute("SELECT approved FROM medical_stores WHERE user_id = %s", (user['id'],))
                    store_status = cursor.fetchone()
                    if not store_status or not store_status['approved']:
                        flash('Your Medical Store account is pending admin approval.', 'warning')
                        return render_template('auth/login.html', form_data={'email': email})
                elif user['role'] == 'NGO':
                    cursor.execute("SELECT approved FROM ngos WHERE user_id = %s", (user['id'],))
                    ngo_status = cursor.fetchone()
                    if not ngo_status or not ngo_status['approved']:
                        flash('Your NGO account is pending admin approval.', 'warning')
                        return render_template('auth/login.html', form_data={'email': email})

                session['loggedin'] = True
                session['user_id'] = user['id']
                session['name'] = user['name']
                session['email'] = user['email']
                session['role'] = user['role']
                flash('Logged in successfully!', 'success')

                # Redirect based on role using correct blueprint endpoints
                role_redirects = {
                    'Admin': 'admin.dashboard',
                    'Medical Store': 'medical_store.dashboard',
                    'Donor': 'donor.donation',
                    'NGO': 'ngo.request_medicine',
                    'Central Hub': 'central_hub.dashboard'
                }
                endpoint = role_redirects.get(user['role'], 'main.index')
                return redirect(url_for(endpoint))
            else:
                flash('Incorrect email or password.', 'danger')
        except mysql.connector.Error as err:
            flash(f"Database error: {err}", 'danger')
            print(f"MySQL Error in login route: {err}")
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'danger')
            print(f"Unexpected error in login route: {e}")

    return render_template('auth/login.html', form_data={})

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('auth/register.html', form_data={})

    step = request.form.get('step')
    form_data = request.form.to_dict()

    if step == 'send_otp':
        email = form_data.get('email')
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register.html', form_data=form_data)

        otp = str(random.randint(100000, 999999))
        session['temp_user'] = form_data
        session['otp'] = otp
        session['otp_timestamp'] = datetime.now().timestamp()
        
        try:
            msg = Message("Your OTP for GiveHub Registration",
                          sender=current_app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f"Hello {form_data.get('name')},\n\nYour OTP is: {otp}\n\nIt is valid for 5 minutes."
            mail.send(msg)
            flash('An OTP has been sent to your email.', 'info')
            return render_template('auth/register.html', show_otp=True, email=email, form_data=form_data)
        except Exception as e:
            flash(f'Failed to send OTP: {e}', 'danger')
            return render_template('auth/register.html', form_data=form_data)

    elif step == 'verify_otp':
        user_otp = request.form.get('otp')
        if (datetime.now().timestamp() - session.get('otp_timestamp', 0)) > 300: # 5 minute expiry
            flash('OTP has expired. Please restart registration.', 'danger')
            return redirect(url_for('auth.register'))

        if user_otp == session.get('otp'):
            user_data = session.get('temp_user')
            hashed_password = generate_password_hash(user_data['password'])
            
            db = get_db()
            cur = db.cursor()
            db.start_transaction()
            
            try:
                cur.execute('INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)',
                           (user_data['name'], user_data['email'], hashed_password, user_data['role']))
                user_id = cur.lastrowid

                if user_data['role'] == 'Medical Store':
                    cur.execute(
                        "INSERT INTO medical_stores (user_id, name, email, contact_number, address, approved) VALUES (%s, %s, %s, %s, %s, %s)",
                        (user_id, user_data['name'], user_data['email'], user_data['ms_contact'], user_data['ms_address'], False)
                    )
                elif user_data['role'] == 'NGO':
                    cur.execute(
                        "INSERT INTO ngos (user_id, name, email, contact_person, contact_number, address, registration_number, approved) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (user_id, user_data['name'], user_data['email'], user_data['name'], user_data['ngo_contact'], user_data['ngo_address'], user_data['registration_number'], False)
                    )

                db.commit()
                flash('Registration successful! Please log in.', 'success')
                session.pop('temp_user', None)
                session.pop('otp', None)
                session.pop('otp_timestamp', None)
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.rollback()
                flash(f'Database Error: {e}', 'danger')
                return render_template('auth/register.html', form_data=user_data)
        else:
            flash('Invalid OTP.', 'danger')
            return render_template('auth/register.html', show_otp=True, email=session.get('temp_user', {}).get('email'), form_data=session.get('temp_user'))

    return render_template('auth/register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        step = request.form.get('step')
        email = request.form.get('email')

        if step == 'send_otp':
            db = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute('SELECT id, name FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()

            if user:
                otp = str(random.randint(100000, 999999))
                session['reset_email'] = email
                session['reset_otp'] = otp
                session['reset_otp_timestamp'] = datetime.now().timestamp()

                msg = Message("Your GiveHub Password Reset OTP",
                              sender=current_app.config['MAIL_USERNAME'],
                              recipients=[email])
                msg.body = f"Hello {user['name']},\n\nYour OTP to reset your password is: {otp}"
                mail.send(msg)
                flash('An OTP has been sent to your email.', 'info')
                return render_template('auth/reset_password.html', step='verify_otp', email=email)
            else:
                flash('Email not found.', 'danger')
                return render_template('auth/reset_password.html', step='send_otp', email=email)

        elif step == 'verify_otp':
            user_otp = request.form.get('otp')
            if (datetime.now().timestamp() - session.get('reset_otp_timestamp', 0)) > 300:
                flash('OTP has expired.', 'danger')
                return redirect(url_for('auth.forgot_password'))
            
            if user_otp == session.get('reset_otp'):
                flash('OTP verified. Please set your new password.', 'success')
                return render_template('auth/reset_password.html', step='set_password', email=session.get('reset_email'))
            else:
                flash('Invalid OTP.', 'danger')
                return render_template('auth/reset_password.html', step='verify_otp', email=session.get('reset_email'))

        elif step == 'set_password':
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            reset_email = session.get('reset_email')

            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('auth/reset_password.html', step='set_password', email=reset_email)

            hashed_password = generate_password_hash(new_password)
            db = get_db()
            cursor = db.cursor()
            cursor.execute('UPDATE users SET password = %s WHERE email = %s', (hashed_password, reset_email))
            db.commit()
            
            session.clear()
            flash('Password reset successfully. Please log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', step='send_otp')
