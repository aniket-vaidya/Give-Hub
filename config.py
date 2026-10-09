import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key_for_development')

    # Database Configuration
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = os.environ.get('DATABASE_PASSWORD', 'Password')
    DB_NAME = "givehub_db"

    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    CERTIFICATE_FOLDER = os.path.join('static', 'certificates')
    PRESCRIPTION_FOLDER = os.path.join('static', 'prescriptions')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Flask-Mail Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'givehubdonation@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'fmyd alnh hhli hhuc')