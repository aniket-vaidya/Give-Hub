from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash
from decorators import login_required, role_required
from db import get_db
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
admin_required = role_required('Admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    Displays the main admin dashboard with pending approvals and lists of all
    donations and requests.
    """
    db = get_db()
    cur = db.cursor(dictionary=True)
    
    # Fetch pending medical store applications
    cur.execute("""
        SELECT ms.*, u.email 
        FROM medical_stores ms 
        JOIN users u ON ms.user_id = u.id 
        WHERE ms.approved = FALSE
    """)
    pending_medical_stores = cur.fetchall()

    # Fetch pending NGO applications
    cur.execute("""
        SELECT n.*, u.email 
        FROM ngos n 
        JOIN users u ON n.user_id = u.id 
        WHERE n.approved = FALSE
    """)
    pending_ngos = cur.fetchall()

    # Fetch all donations for a general overview
    cur.execute("""
        SELECT d.*, ms.name AS medical_store_name 
        FROM donations d 
        LEFT JOIN medical_stores ms ON d.medical_store_id = ms.id 
        ORDER BY d.created_at DESC
    """)
    all_donations = cur.fetchall()

    # Fetch all requests for a general overview
    cur.execute("""
        SELECT r.*, u.name AS ngo_name, ms.name AS medical_store_name 
        FROM requests r 
        JOIN users u ON r.requester_id = u.id 
        LEFT JOIN medical_stores ms ON r.medical_store_id = ms.id 
        ORDER BY r.created_at DESC
    """)
    all_requests = cur.fetchall()
    
    return render_template('admin/dashboard.html', 
                           pending_medical_stores=pending_medical_stores,
                           pending_ngos=pending_ngos,
                           all_donations=all_donations,
                           all_requests=all_requests)

@admin_bp.route('/approve_medical_store/<int:store_id>', methods=['POST'])
@login_required
@admin_required
def approve_medical_store(store_id):
    """Approves a pending medical store application."""
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE medical_stores SET approved = TRUE WHERE id = %s", (store_id,))
    db.commit()
    flash('Medical Store approved successfully!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/reject_medical_store/<int:store_id>', methods=['POST'])
@login_required
@admin_required
def reject_medical_store(store_id):
    """Rejects and deletes a medical store application and associated user."""
    db = get_db()
    cur = db.cursor()
    try:
        db.start_transaction()
        cur.execute("SELECT user_id FROM medical_stores WHERE id = %s", (store_id,))
        result = cur.fetchone()
        if result:
            user_id_to_delete = result[0]
            # First, delete the child record from medical_stores
            cur.execute("DELETE FROM medical_stores WHERE id = %s", (store_id,))
            # Then, delete the parent user record
            cur.execute("DELETE FROM users WHERE id = %s", (user_id_to_delete,))
            db.commit()
            flash('Medical Store application rejected and removed.', 'info')
        else:
            flash('Medical store not found.', 'warning')
            db.rollback()
    except Exception as e:
        db.rollback()
        flash(f"An error occurred while rejecting the medical store: {e}", 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/approve_ngo/<int:ngo_id>', methods=['POST'])
@login_required
@admin_required
def approve_ngo(ngo_id):
    """Approves a pending NGO application."""
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE ngos SET approved = TRUE WHERE id = %s", (ngo_id,))
    db.commit()
    flash('NGO approved successfully!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/reject_ngo/<int:ngo_id>', methods=['POST'])
@login_required
@admin_required
def reject_ngo(ngo_id):
    """Rejects and deletes an NGO application and associated user."""
    db = get_db()
    cur = db.cursor()
    try:
        db.start_transaction()
        cur.execute("SELECT user_id FROM ngos WHERE id = %s", (ngo_id,))
        result = cur.fetchone()
        if result:
            user_id_to_delete = result[0]
            # First, delete the child record from ngos
            cur.execute("DELETE FROM ngos WHERE id = %s", (ngo_id,))
            # Then, delete the parent user record
            cur.execute("DELETE FROM users WHERE id = %s", (user_id_to_delete,))
            db.commit()
            flash('NGO application rejected and removed.', 'info')
        else:
            flash('NGO not found.', 'warning')
            db.rollback()
    except Exception as e:
        db.rollback()
        flash(f"An error occurred while rejecting the NGO: {e}", 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/view_donation/<int:donation_id>')
@login_required
@admin_required
def view_donation_details(donation_id):
    """Displays a dedicated page with all details for a single donation."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT d.*, ms.name AS medical_store_name 
        FROM donations d 
        LEFT JOIN medical_stores ms ON d.medical_store_id = ms.id 
        WHERE d.id = %s
    """, (donation_id,))
    donation = cur.fetchone()
    if not donation:
        flash('Donation not found.', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    cur.execute("SELECT * FROM donation_medicines WHERE donation_id = %s", (donation_id,))
    medicines = cur.fetchall()
    return render_template('admin/view_donation.html', donation=donation, medicines=medicines)

@admin_bp.route('/view_request/<int:request_id>')
@login_required
@admin_required
def view_request_details(request_id):
    """Displays a dedicated page with all details for a single request."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT r.*, u.name AS ngo_name 
        FROM requests r 
        JOIN users u ON r.requester_id = u.id 
        WHERE r.id = %s
    """, (request_id,))
    request_data = cur.fetchone()
    if not request_data:
        flash('Request not found.', 'danger')
        return redirect(url_for('admin.dashboard'))

    cur.execute("SELECT * FROM request_medicines WHERE request_id = %s", (request_id,))
    medicines = cur.fetchall()
    cur.execute("SELECT * FROM request_beneficiaries WHERE request_id = %s", (request_id,))
    beneficiaries = cur.fetchall()
    return render_template('admin/view_request.html', 
                           request_data=request_data, 
                           medicines=medicines, 
                           beneficiaries=beneficiaries)

@admin_bp.route('/reports', methods=['GET'])
@login_required
@admin_required
def reports():
    """Renders the main page for generating reports."""
    return render_template('admin/reports.html')

@admin_bp.route('/stock_overview')
@login_required
@admin_required
def stock_overview():
    db = get_db()
    cur = db.cursor(dictionary=True)

    # Fetch Central Hub Inventory (Removing the expiry filter to ensure data shows)
    cur.execute("""
        SELECT * FROM central_inventory
        WHERE quantity > 0
        ORDER BY expiry_date ASC
    """)
    central_inventory = cur.fetchall()

    # Fetch Medical Store Inventories
    cur.execute("""
        SELECT ms.name as store_name, mss.medicine_name, mss.quantity, mss.expiry_date, mss.batch_no
        FROM medical_store_stock mss
        JOIN medical_stores ms ON mss.medical_store_id = ms.id
        WHERE mss.quantity > 0 AND ms.approved = TRUE
        ORDER BY ms.name, mss.expiry_date ASC
    """)
    all_ms_stock = cur.fetchall()

    # Grouping logic
    stores_stock = {}
    for item in all_ms_stock:
        store_name = item['store_name']
        if store_name not in stores_stock:
            stores_stock[store_name] = []
        stores_stock[store_name].append(item)

    return render_template('central_hub/stock_overview.html',
                           central_inventory=central_inventory,
                           stores_stock=stores_stock,
                           is_admin=True)

@admin_bp.route('/reports/generate', methods=['POST'])
@login_required
@admin_required
def generate_report():
    """Fetches data based on form submission and displays the generated report."""
    try:
        report_type = request.form.get('report_type')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not all([report_type, start_date_str, end_date_str]):
            flash('Please select a report type and a valid date range.', 'warning')
            return redirect(url_for('admin.reports'))

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(f'{end_date_str} 23:59:59', '%Y-%m-%d %H:%M:%S')

        db = get_db()
        cur = db.cursor(dictionary=True)
        
        report_data = []
        report_title = ""

        if report_type == 'donations':
            report_title = f"Donations Report ({start_date_str} to {end_date_str})"
            cur.execute("""
                SELECT d.*, ms.name AS medical_store_name, 
                       GROUP_CONCAT(dm.medicine_name, ' (Qty: ', dm.quantity, ')') AS medicines
                FROM donations d
                LEFT JOIN medical_stores ms ON d.medical_store_id = ms.id
                LEFT JOIN donation_medicines dm ON d.id = dm.donation_id
                WHERE d.created_at BETWEEN %s AND %s
                GROUP BY d.id
                ORDER BY d.created_at DESC
            """, (start_date, end_date))
            report_data = cur.fetchall()

        elif report_type == 'requests':
            report_title = f"Medicine Requests Report ({start_date_str} to {end_date_str})"
            cur.execute("""
                SELECT r.*, u.name AS ngo_name, ms.name AS medical_store_name,
                       GROUP_CONCAT(rm.medicine, ' (Qty: ', rm.quantity, ')') AS medicines
                FROM requests r
                JOIN users u ON r.requester_id = u.id
                LEFT JOIN medical_stores ms ON r.medical_store_id = ms.id
                LEFT JOIN request_medicines rm ON r.id = rm.request_id
                WHERE r.created_at BETWEEN %s AND %s
                GROUP BY r.id
                ORDER BY r.created_at DESC
            """, (start_date, end_date))
            report_data = cur.fetchall()
            
        else:
            flash('Invalid report type selected.', 'danger')
            return redirect(url_for('admin.reports'))

        return render_template('admin/report_view.html',
                               report_title=report_title,
                               report_data=report_data,
                               report_type=report_type,
                               generation_date=datetime.now())

    except Exception as e:
        flash(f"An error occurred while generating the report: {e}", 'danger')
        return redirect(url_for('admin.reports'))
