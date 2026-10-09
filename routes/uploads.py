from flask import Blueprint, send_from_directory, current_app
from decorators import login_required

# Create a blueprint named 'uploads'
uploads_bp = Blueprint('uploads', __name__)

@uploads_bp.route('/static/prescriptions/<path:filename>')
@login_required # IMPORTANT: Protects sensitive medical documents
def uploaded_prescription(filename):
    """
    Serves prescription files (PDFs) from the protected prescriptions folder.
    Only logged-in users (like Admins, Central Hub staff) can access this route.
    """
    return send_from_directory(current_app.config['PRESCRIPTION_FOLDER'], filename)

@uploads_bp.route('/static/certificates/<path:filename>')
@login_required # IMPORTANT: Protects personal certificates
def uploaded_certificate(filename):
    """
    Serves certificate files (images) from the protected certificates folder.
    Only logged-in users can access this route.
    """
    return send_from_directory(current_app.config['CERTIFICATE_FOLDER'], filename)

@uploads_bp.route('/static/uploads/<path:filename>')
def uploaded_image(filename):
    """
    Serves general image uploads (like medicine pictures) from the public uploads folder.
    This route is public and does not require a login.
    """
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
