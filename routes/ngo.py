from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
import random

from db import get_db
from decorators import login_required, role_required
from utils import allowed_document_file

ngo_bp = Blueprint('ngo', __name__)
ngo_required = role_required('NGO')

@ngo_bp.route('/request', methods=['GET', 'POST'])
@login_required
@ngo_required
def request_medicine():
    if request.method == 'POST':
        num_beneficiaries = int(request.form.get('num_beneficiaries', 0))
        requester_name = request.form.get('name')
        address = request.form.get('location')
        requester_id = session.get('user_id')

        db = get_db()
        try:
            cur = db.cursor()
            db.start_transaction()

            cur.execute("""
                INSERT INTO requests (num_beneficiaries, requester_name, address, status, requester_id)
                VALUES (%s, %s, %s, 'Pending', %s)
            """, (num_beneficiaries, requester_name, address, requester_id))
            request_id = cur.lastrowid

            for i in range(1, num_beneficiaries + 1):
                bname = request.form.get(f'beneficiary_name_{i}')
                age = int(request.form.get(f'beneficiary_age_{i}', 0))
                sex = request.form.get(f'beneficiary_sex_{i}')
                doc = request.files.get(f'doctor_letter_{i}')
                doc_path = None
                
                if not all([bname, age > 0, sex, doc]):
                    flash(f'Incomplete details or missing prescription for Beneficiary {i}.', 'danger')
                    db.rollback()
                    return render_template('ngo/create_request.html', form_data=request.form)

                if doc and allowed_document_file(doc.filename):
                    from flask import current_app
                    fname = secure_filename(doc.filename)
                    doc_path = f"prescription_{request_id}_{i}_{random.randint(1000,9999)}_{fname}"
                    doc.save(os.path.join(current_app.config['PRESCRIPTION_FOLDER'], doc_path))
                
                cur.execute("""
                    INSERT INTO request_beneficiaries (request_id, beneficiary_name, age, sex, doctor_prescription_path)
                    VALUES (%s, %s, %s, %s, %s)
                """, (request_id, bname, age, sex, doc_path))

                # Logic to add requested medicines for this beneficiary
                num_meds = int(request.form.get(f'num_medicines_{i}', 0))
                for j in range(1, num_meds + 1):
                    med_name = request.form.get(f'request_medicine_name_{i}_{j}')
                    qty = int(request.form.get(f'request_quantity_{i}_{j}', 0))
                    if med_name and qty > 0:
                        cur.execute("""
                            INSERT INTO request_medicines (request_id, medicine, quantity)
                            VALUES (%s, %s, %s)
                        """, (request_id, med_name, qty))

            db.commit()
            flash('Request submitted successfully!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.rollback()
            flash(f"Error submitting request: {e}", 'danger')

    return render_template('ngo/create_request.html', form_data={})