from flask import Blueprint, render_template, redirect, url_for, flash, request
from decorators import login_required, role_required
from db import get_db
from utils import generate_certificate, send_certificate_email
from extensions import mail

central_hub_bp = Blueprint('central_hub', __name__, url_prefix='/central_hub')
central_hub_required = role_required('Central Hub')

@central_hub_bp.route('/dashboard')
@login_required
@central_hub_required
def dashboard():
    db = get_db()
    cur = db.cursor(dictionary=True)
    
    # Donations awaiting Central Hub receipt from Medical Stores
    cur.execute("""
        SELECT d.*, ms.name AS medical_store_name
        FROM donations d
        JOIN medical_stores ms ON d.medical_store_id = ms.id
        WHERE d.medical_store_status = 'Received by MS' AND d.central_hub_status = 'Awaiting CH Receipt'
        ORDER BY d.created_at DESC
    """)
    assigned_donations = cur.fetchall()

    # Requests pending Central Hub approval
    cur.execute("""
        SELECT r.*, u.name AS ngo_name
        FROM requests r
        JOIN users u ON r.requester_id = u.id
        WHERE r.status = 'Pending'
        ORDER BY r.created_at DESC
    """)
    pending_requests = cur.fetchall()

    # Requests approved by Central Hub, awaiting assignment or fulfillment
    cur.execute("""
        SELECT r.*, u.name AS ngo_name, ms.name AS medical_store_name
        FROM requests r
        JOIN users u ON r.requester_id = u.id
        LEFT JOIN medical_stores ms ON r.medical_store_id = ms.id
        WHERE r.status IN ('Approved by CH', 'Assigned to MS')
        ORDER BY r.created_at DESC
    """)
    approved_requests = cur.fetchall()

    # Fetch approved medical stores for the assignment dropdown
    cur.execute("SELECT id, name FROM medical_stores WHERE approved = TRUE")
    medical_stores = cur.fetchall()

    return render_template('central_hub/dashboard.html',
                           assigned_donations=assigned_donations,
                           pending_requests=pending_requests,
                           approved_requests=approved_requests,
                           medical_stores=medical_stores)

@central_hub_bp.route('/stock_overview')
@login_required
@central_hub_required
def stock_overview():
    db = get_db()
    cur = db.cursor(dictionary=True)

    # Simplified: Get total quantity for each medicine in Central Hub
    cur.execute("""
        SELECT medicine_name, SUM(quantity) as total_quantity
        FROM central_inventory
        WHERE quantity > 0
        GROUP BY medicine_name
    """)
    central_inventory = cur.fetchall()

    # Simplified: Get total quantity per medicine per Medical Store
    cur.execute("""
        SELECT ms.name as store_name, mss.medicine_name, SUM(mss.quantity) as total_quantity
        FROM medical_store_stock mss
        JOIN medical_stores ms ON mss.medical_store_id = ms.id
        WHERE mss.quantity > 0 AND ms.approved = TRUE
        GROUP BY ms.name, mss.medicine_name
        ORDER BY ms.name, mss.medicine_name
    """)
    all_ms_stock = cur.fetchall()

    # Grouping by store for the template
    stores_stock = {}
    for item in all_ms_stock:
        store_name = item['store_name']
        if store_name not in stores_stock:
            stores_stock[store_name] = []
        stores_stock[store_name].append(item)

    return render_template('central_hub/stock_overview.html',
                           central_inventory=central_inventory,
                           stores_stock=stores_stock)

@central_hub_bp.route('/confirm_donation/<int:donation_id>', methods=['POST'])
@login_required
@central_hub_required
def confirm_donation(donation_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        db.start_transaction()

        cur.execute("SELECT donor_name, email, medical_store_id FROM donations WHERE id = %s", (donation_id,))
        donation_info = cur.fetchone()
        if not donation_info:
            raise Exception("Donation not found.")
        
        medical_store_id = donation_info['medical_store_id']

        cur.execute("SELECT * FROM donation_medicines WHERE donation_id = %s", (donation_id,))
        donated_medicines = cur.fetchall()
        if not donated_medicines:
            raise Exception("No medicines found for this donation.")

        for med in donated_medicines:
            cur.execute("""
                INSERT INTO central_inventory (medicine_name, quantity, batch_no, expiry_date, current_location) 
                VALUES (%s, %s, %s, %s, 'Central Hub')
            """, (med['medicine_name'], med['quantity'], med.get('batch_no'), med['expiry_date']))

            # This DELETE query is what keeps your stock overview "real-time". It works correctly.
            cur.execute("""
                DELETE FROM medical_store_stock 
                WHERE medical_store_id = %s 
                  AND medicine_name = %s 
                  AND batch_no = %s 
                  AND expiry_date = %s
                  AND quantity = %s
            """, (medical_store_id, med['medicine_name'], med.get('batch_no'), med['expiry_date'], med['quantity']))

        cur.execute("""
            UPDATE donations 
            SET status = 'Collected by CH', central_hub_status = 'Central Hub Received' 
            WHERE id = %s
        """, (donation_id,))
        
        certificate_path = generate_certificate(donation_info['donor_name'], donation_id)
        if certificate_path:
            cur.execute("UPDATE donations SET certificate_path = %s WHERE id = %s", (certificate_path, donation_id))
            send_certificate_email(mail, donation_info['email'], donation_info['donor_name'], certificate_path)
            flash('Donation confirmed, inventory updated, and certificate sent!', 'success')
        else:
            flash('Donation confirmed and inventory updated, but certificate failed to send.', 'warning')

        db.commit()
    except Exception as e:
        db.rollback()
        flash(f"Error confirming donation: {e}", 'danger')
        
    return redirect(url_for('central_hub.dashboard'))

@central_hub_bp.route('/approve_request/<int:request_id>', methods=['POST'])
@login_required
@central_hub_required
def approve_request(request_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("UPDATE requests SET status = 'Approved by CH' WHERE id = %s", (request_id,))
        db.commit()
        flash('Request approved. You can now assign it to a Medical Store or fulfill it directly.', 'success')
    except Exception as e:
        flash(f"Error approving request: {e}", 'danger')
    return redirect(url_for('central_hub.dashboard'))

@central_hub_bp.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
@central_hub_required
def reject_request(request_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("UPDATE requests SET status = 'Rejected by CH' WHERE id = %s", (request_id,))
        db.commit()
        flash('Request has been rejected.', 'info')
    except Exception as e:
        flash(f"Error rejecting request: {e}", 'danger')
    return redirect(url_for('central_hub.dashboard'))

# ### CHANGED: Renamed route and function to handle both assignment and reassignment ###
@central_hub_bp.route('/manage_assignment/<int:request_id>', methods=['POST'])
@login_required
@central_hub_required
def manage_assignment(request_id):
    medical_store_id = request.form.get('medical_store_id')
    if not medical_store_id:
        flash('You must select a Medical Store to assign.', 'danger')
        return redirect(url_for('central_hub.dashboard'))

    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        # Check current status to provide a better flash message
        cur.execute("SELECT status FROM requests WHERE id = %s", (request_id,))
        current_status = cur.fetchone()['status']

        cur.execute("UPDATE requests SET medical_store_id = %s, status = 'Assigned to MS' WHERE id = %s", (medical_store_id, request_id))
        db.commit()

        if current_status == 'Assigned to MS':
            flash(f'Request {request_id} has been successfully re-assigned.', 'success')
        else:
            flash(f'Request {request_id} has been assigned to a Medical Store.', 'success')
    except Exception as e:
        flash(f"Error assigning request: {e}", 'danger')
    return redirect(url_for('central_hub.dashboard'))

# ### CHANGED: Route name and logic to reflect its purpose ###
# In your central_hub routes file
@central_hub_bp.route('/fulfill_from_hub/<int:request_id>', methods=['GET', 'POST'])
@login_required
@central_hub_required
def fulfill_request_from_hub(request_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    # Fetch request details to ensure it exists and is valid for fulfillment
    cur.execute("""
        SELECT r.*, u.name AS ngo_name 
        FROM requests r 
        JOIN users u ON r.requester_id = u.id 
        WHERE r.id = %s AND r.status IN ('Approved by CH', 'Assigned to MS')
    """, (request_id,))
    request_data = cur.fetchone()

    if not request_data:
        flash("This request is either not found or not in a state to be fulfilled.", "danger")
        return redirect(url_for('central_hub.dashboard'))

    if request.method == 'POST':
        try:
            # FIX: Only start a transaction if one isn't already active
            if hasattr(db, 'in_transaction') and not db.in_transaction:
                db.start_transaction()
            elif not hasattr(db, 'in_transaction'):
                # Fallback for database drivers that don't support the in_transaction property
                db.start_transaction()

            cur.execute("SELECT medicine, quantity FROM request_medicines WHERE request_id = %s", (request_id,))
            requested_medicines = cur.fetchall()

            for item in requested_medicines:
                med_name = item['medicine']
                requested_qty = item['quantity']

                # Use UPPER and TRIM to match stock exactly as seen in your overview
                cur.execute("""
                    SELECT id, quantity 
                    FROM central_inventory
                    WHERE UPPER(TRIM(medicine_name)) = UPPER(TRIM(%s)) 
                    AND quantity > 0 
                    AND expiry_date > CURDATE()
                    ORDER BY expiry_date ASC FOR UPDATE
                """, (med_name,))
                available_batches = cur.fetchall()
                
                total_available = sum(batch['quantity'] for batch in available_batches)
                
                if total_available < requested_qty:
                    raise Exception(f"Insufficient stock for {med_name}. Available: {total_available}, Requested: {requested_qty}.")

                # Deduct quantities from the Hub inventory
                qty_to_deduct = requested_qty
                for batch in available_batches:
                    if qty_to_deduct <= 0: break
                    deduct_from_this_batch = min(qty_to_deduct, batch['quantity'])
                    cur.execute("UPDATE central_inventory SET quantity = quantity - %s WHERE id = %s", (deduct_from_this_batch, batch['id']))
                    qty_to_deduct -= deduct_from_this_batch

            # Finalize the request status
            cur.execute("UPDATE requests SET status = 'Fulfilled by CH', medical_store_id = NULL WHERE id = %s", (request_id,))
            
            db.commit()
            flash('Request fulfilled successfully from Central Hub inventory!', 'success')
            return redirect(url_for('central_hub.dashboard'))

        except Exception as e:
            # FIX: Always rollback on error to clear the transaction state
            try:
                db.rollback()
            except:
                pass 
            flash(f"Error fulfilling request: {e}", 'danger')
            return redirect(url_for('central_hub.dashboard'))

    # Logic for displaying available vs requested stock on the GET page
    cur.execute("SELECT medicine, quantity FROM request_medicines WHERE request_id = %s", (request_id,))
    medicines_needed = cur.fetchall()
    
    medicines_data = []
    for med in medicines_needed:
        cur.execute("""
            SELECT SUM(quantity) as total_quantity 
            FROM central_inventory 
            WHERE UPPER(TRIM(medicine_name)) = UPPER(TRIM(%s)) 
            AND quantity > 0 AND expiry_date > CURDATE()
        """, (med['medicine'],))
        
        stock_info = cur.fetchone()
        available_quantity = stock_info['total_quantity'] if stock_info and stock_info['total_quantity'] else 0
        
        medicines_data.append({
            'name': med['medicine'],
            'quantity_requested': med['quantity'],
            'quantity_available': available_quantity
        })

    return render_template('central_hub/fulfill_request.html', 
                           request_data=request_data, 
                           medicines_data=medicines_data)
@central_hub_bp.route('/view_request_details/<int:request_id>')
@login_required
@central_hub_required
def view_request_details(request_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    
    cur.execute("SELECT r.*, u.name AS ngo_name FROM requests r JOIN users u ON r.requester_id = u.id WHERE r.id = %s", (request_id,))
    request_data = cur.fetchone()
    if not request_data:
        flash("Request not found.", "danger")
        return redirect(url_for('central_hub.dashboard'))
        
    cur.execute("SELECT * FROM request_medicines WHERE request_id = %s", (request_id,))
    medicines = cur.fetchall()
    cur.execute("SELECT * FROM request_beneficiaries WHERE request_id = %s", (request_id,))
    beneficiaries = cur.fetchall()

    return render_template('central_hub/view_request.html', 
                           request_data=request_data, 
                           medicines=medicines, 
                           beneficiaries=beneficiaries)