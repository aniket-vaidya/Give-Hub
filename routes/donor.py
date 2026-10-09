from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
import os
import random
import mysql.connector

from db import get_db
from decorators import login_required, role_required
from utils import allowed_file

donor_bp = Blueprint('donor', __name__)
donor_required = role_required('Donor')

@donor_bp.route('/donation', methods=['GET', 'POST'])
@login_required
@donor_required
def donation():
    medical_stores = []
    form_data = {}

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, name FROM medical_stores WHERE approved = TRUE")
        medical_stores = cur.fetchall()
    except mysql.connector.Error as e:
        flash(f"Error fetching medical stores: {e}", 'danger')
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", 'danger')


    if request.method == 'POST':
        donor_name = request.form.get('donor_name')
        contact_number = request.form.get('contact_number')
        donor_email = request.form.get('email')
        address = request.form.get('address')
        medical_store_id = request.form.get('medical_store_id')
        num_meds = int(request.form.get('num_medicines', 0))
        
        db = get_db()
        try:
            cur = db.cursor()
            # db.start_transaction() # <-- ERROR: This line is redundant and causes the error. It has been removed.

            cur.execute("""
                INSERT INTO donations (donor_name, contact_number, email, address, medical_store_id, status, medical_store_status, central_hub_status)
                VALUES (%s, %s, %s, %s, %s, 'Pending', 'Assigned to Medical Store', 'Awaiting MS Receipt')
            """, (donor_name, contact_number, donor_email, address, medical_store_id))
            donation_id = cur.lastrowid

            for i in range(num_meds):
                name = request.form.get(f'medicine_name_{i}')
                qty = int(request.form.get(f'quantity_{i}', 0))
                expiry = request.form.get(f'expiry_date_{i}')
                image = request.files.get(f'image_{i}')
                
                image_filename = None
                if image and allowed_file(image.filename):
                    image_filename = secure_filename(f"donation_{donation_id}_med_{i}_{random.randint(1000,9999)}_{image.filename}")
                    image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename))
                
                cur.execute("""
                    INSERT INTO donation_medicines (donation_id, medicine_name, quantity, expiry_date, image_filename)
                    VALUES (%s, %s, %s, %s, %s)
                """, (donation_id, name, qty, expiry, image_filename))

            db.commit() # This finalizes the transaction
            flash('Donation submitted successfully!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.rollback() # This cancels the transaction if any error occurs
            flash(f"Database error during donation: {e}", 'danger')

    return render_template('donor/create_donation.html', medical_stores=medical_stores, form_data=form_data)
