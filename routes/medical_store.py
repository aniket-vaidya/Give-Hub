from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from decorators import login_required, role_required
from db import get_db
from datetime import date, datetime
import mysql.connector

medical_store_bp = Blueprint('medical_store', __name__, url_prefix='/medical_store')
medical_store_required = role_required('Medical Store')

def get_ms_id(user_id):
    """Helper function to get the medical_store id from a user_id."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id FROM medical_stores WHERE user_id = %s", (user_id,))
    ms_info = cur.fetchone()
    return ms_info['id'] if ms_info else None

@medical_store_bp.route('/dashboard')
@login_required
@medical_store_required
def dashboard():
    medical_store_id = get_ms_id(session['user_id'])
    if not medical_store_id:
        flash('Medical Store profile not found.', 'danger')
        return redirect(url_for('main.index'))

    assigned_donations = []
    stock_medicines = []
    assigned_requests = []

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)

        # Fetch donations assigned for verification
        cur.execute("""
            SELECT d.id, d.donor_name, d.created_at, COUNT(dm.id) as medicine_count
            FROM donations d
            JOIN donation_medicines dm ON d.id = dm.donation_id
            WHERE d.medical_store_id = %s AND d.medical_store_status = 'Assigned to Medical Store'
            GROUP BY d.id, d.donor_name, d.created_at
            ORDER BY d.created_at DESC
        """, (medical_store_id,))
        assigned_donations = cur.fetchall()

        # Fetch current stock
        cur.execute("""
            SELECT medicine_name, SUM(quantity) as total_quantity, MIN(expiry_date) as expiry_date
            FROM medical_store_stock
            WHERE medical_store_id = %s AND quantity > 0 AND expiry_date > CURDATE()
            GROUP BY medicine_name
            ORDER BY expiry_date ASC, medicine_name ASC
        """, (medical_store_id,))
        stock_medicines = cur.fetchall()

        # Fetch requests assigned for fulfillment
        cur.execute("""
            SELECT r.*, u.name AS ngo_name
            FROM requests r
            JOIN users u ON r.requester_id = u.id
            WHERE r.medical_store_id = %s AND r.status = 'Assigned to MS'
            ORDER BY r.created_at DESC
        """, (medical_store_id,))
        assigned_requests = cur.fetchall()

    except Exception as e:
        flash(f"Error fetching Medical Store data: {e}", 'danger')

    return render_template('medical_store/dashboard.html',
                           assigned_donations=assigned_donations,
                           stock_medicines=stock_medicines,
                           assigned_requests=assigned_requests)

@medical_store_bp.route('/confirm_donation_receipt/<int:donation_id>', methods=['GET', 'POST'])
@login_required
@medical_store_required
def confirm_donation_receipt(donation_id):
    medical_store_id = get_ms_id(session['user_id'])
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            cur.execute("SELECT id FROM donation_medicines WHERE donation_id = %s", (donation_id,))
            medicines_in_donation = cur.fetchall()

            for med in medicines_in_donation:
                med_id = med['id']
                batch_no = request.form.get(f'batch_no_{med_id}')
                expiry_date = request.form.get(f'expiry_date_{med_id}')
                quantity = int(request.form.get(f'quantity_{med_id}', 0))
                medicine_name = request.form.get(f'medicine_name_{med_id}')

                if not batch_no or not expiry_date or quantity <= 0:
                    raise Exception(f"Missing details for medicine '{medicine_name}'. Please fill all fields.")

                cur.execute("""
                    UPDATE donation_medicines SET batch_no = %s, expiry_date = %s
                    WHERE id = %s
                """, (batch_no, expiry_date, med_id))

                cur.execute("""
                    INSERT INTO medical_store_stock (medical_store_id, medicine_name, quantity, batch_no, expiry_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (medical_store_id, medicine_name, quantity, batch_no, expiry_date))

            cur.execute("""
                UPDATE donations SET
                status = 'Approved by MS',
                medical_store_status = 'Received by MS',
                central_hub_status = 'Awaiting CH Receipt'
                WHERE id = %s AND medical_store_id = %s
            """, (donation_id, medical_store_id))
            
            db.commit()
            flash('Donation receipt confirmed and medicines added to stock.', 'success')
            return redirect(url_for('medical_store.dashboard'))

        except Exception as e:
            db.rollback()
            flash(f"Error confirming donation: {e}", 'danger')
            return redirect(url_for('medical_store.confirm_donation_receipt', donation_id=donation_id))

    cur.execute("SELECT * FROM donations WHERE id = %s AND medical_store_id = %s", (donation_id, medical_store_id))
    donation = cur.fetchone()
    if not donation:
        flash("Donation not found or not assigned to this store.", "danger")
        return redirect(url_for('medical_store.dashboard'))

    cur.execute("SELECT * FROM donation_medicines WHERE donation_id = %s", (donation_id,))
    medicines_to_confirm = cur.fetchall()
    
    today = date.today().isoformat()
    for med in medicines_to_confirm:
        if isinstance(med.get('expiry_date'), date):
            med['expiry_date_str'] = med['expiry_date'].isoformat()
        else:
            med['expiry_date_str'] = ''

    return render_template('medical_store/confirm_receipt.html', 
                           donation=donation, 
                           medicines=medicines_to_confirm,
                           today=today)

@medical_store_bp.route('/reject_donation/<int:donation_id>', methods=['POST'])
@login_required
@medical_store_required
def reject_donation(donation_id):
    medical_store_id = get_ms_id(session['user_id'])
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            UPDATE donations SET status = 'Rejected by MS', medical_store_status = 'Rejected by MS'
            WHERE id = %s AND medical_store_id = %s
        """, (donation_id, medical_store_id))
        db.commit()
        flash('Donation has been rejected.', 'info')
    except Exception as e:
        flash(f"Error rejecting donation: {e}", 'danger')
        
    return redirect(url_for('medical_store.dashboard'))

@medical_store_bp.route('/fulfill_request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@medical_store_required
def fulfill_request(request_id):
    medical_store_id = get_ms_id(session['user_id'])
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM requests WHERE id = %s AND medical_store_id = %s AND status = 'Assigned to MS'", (request_id, medical_store_id))
    request_data = cur.fetchone()
    if not request_data:
        flash("Request not found or not in a state to be fulfilled by this store.", "danger")
        return redirect(url_for('medical_store.dashboard'))

    if request.method == 'POST':
        try:
            cur.execute("SELECT medicine, quantity FROM request_medicines WHERE request_id = %s", (request_id,))
            requested_medicines = cur.fetchall()

            for item in requested_medicines:
                med_name = item['medicine']
                requested_qty = item['quantity']

                cur.execute("""
                    SELECT id, quantity FROM medical_store_stock
                    WHERE medical_store_id = %s AND medicine_name = %s AND quantity > 0 AND expiry_date > CURDATE()
                    ORDER BY expiry_date ASC FOR UPDATE
                """, (medical_store_id, med_name))
                available_batches = cur.fetchall()
                
                total_available = sum(batch['quantity'] for batch in available_batches)
                if total_available < requested_qty:
                    raise Exception(f"Insufficient stock for {med_name}. Available: {total_available}, Requested: {requested_qty}.")

                qty_to_deduct = requested_qty
                for batch in available_batches:
                    if qty_to_deduct <= 0: break
                    deduct_from_this_batch = min(qty_to_deduct, batch['quantity'])
                    cur.execute("UPDATE medical_store_stock SET quantity = quantity - %s WHERE id = %s", (deduct_from_this_batch, batch['id']))
                    qty_to_deduct -= deduct_from_this_batch

            cur.execute("UPDATE requests SET status = 'Fulfilled by MS' WHERE id = %s", (request_id,))
            db.commit()
            flash('Request fulfilled successfully and stock has been updated!', 'success')
            return redirect(url_for('medical_store.dashboard'))
        except Exception as e:
            db.rollback()
            flash(f"Error fulfilling request: {e}", 'danger')
            return redirect(url_for('medical_store.fulfill_request', request_id=request_id))

    cur.execute("SELECT medicine AS medicine_name, quantity AS quantity_needed FROM request_medicines WHERE request_id = %s", (request_id,))
    medicines_needed = cur.fetchall()

    for med in medicines_needed:
        cur.execute("""
            SELECT SUM(quantity) as total_stock 
            FROM medical_store_stock 
            WHERE medical_store_id = %s AND medicine_name = %s AND quantity > 0 AND expiry_date > CURDATE()
        """, (medical_store_id, med['medicine_name']))
        stock_info = cur.fetchone()
        med['quantity_available'] = stock_info['total_stock'] if stock_info and stock_info['total_stock'] else 0

    return render_template('medical_store/fulfill_request.html', 
                           request_data=request_data, 
                           medicines_needed=medicines_needed)
