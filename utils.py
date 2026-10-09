import os
import base64
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from flask import current_app
from flask_mail import Message

from config import Config

# --- File Upload Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def allowed_document_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_DOCUMENT_EXTENSIONS

# --- Base64 Encode Filter ---
def b64encode_filter(data):
    if data:
        return base64.b64encode(data).decode('utf-8')
    return ''

# --- Certificate Generation & Emailing ---
def generate_certificate(donor_name, donation_id):
    try:
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color='#e0f7fa')
        d = ImageDraw.Draw(img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 48)
            font_body = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            print("Warning: Arial font not found. Using default PIL font.")
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()

        # Simplified certificate text
        d.text((width/2, 50), "Certificate of Appreciation", fill=(0, 102, 102), font=font_title, anchor="mt")
        d.text((width/2, 200), donor_name.upper(), fill=(0, 102, 102), font=font_title, anchor="mm")
        d.text((width/2, 300), "For your generous contribution of medicines.", fill=(0, 0, 0), font=font_body, anchor="mt")
        d.text((50, height - 100), f"Date: {datetime.now().strftime('%B %d, %Y')}", fill=(51, 51, 51), font=font_body)
        d.rectangle([20, 20, width - 20, height - 20], outline=(0, 102, 102), width=5)

        certificate_filename = f"certificate_{donation_id}.jpeg"
        certificate_path = os.path.join(current_app.config['CERTIFICATE_FOLDER'], certificate_filename)
        img.save(certificate_path, "JPEG")
        return certificate_path
    except Exception as e:
        print(f"Error generating certificate: {e}")
        return None

def send_certificate_email(mail_instance, recipient_email, donor_name, certificate_path):
    try:
        msg = Message("Thank You for Your Donation to GiveHub!",
                      sender=current_app.config['MAIL_USERNAME'],
                      recipients=[recipient_email])
        msg.body = f"Dear {donor_name},\n\nThank you for your generous donation. Attached is your certificate of appreciation.\n\nWarm regards,\nThe GiveHub Team"

        if certificate_path and os.path.exists(certificate_path):
            with current_app.open_resource(certificate_path) as cert_file:
                msg.attach(os.path.basename(certificate_path), "image/jpeg", cert_file.read())
        
        mail_instance.send(msg)
        return True
    except Exception as e:
        print(f"Error sending certificate email: {e}")
        return False