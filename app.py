import os
from flask import Flask
from extensions import mail
from config import Config
from db import close_db
from utils import b64encode_filter

def create_app(config_class=Config):
    """
    Application factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance folder exists for uploads
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['CERTIFICATE_FOLDER'], exist_ok=True)
        os.makedirs(app.config['PRESCRIPTION_FOLDER'], exist_ok=True)
    except OSError:
        pass

    # Initialize Flask extensions with the app instance
    mail.init_app(app)

    # --- Register Blueprints ---
    # Import the blueprints from their respective files
    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.donor import donor_bp
    from routes.ngo import ngo_bp
    from routes.medical_store import medical_store_bp
    from routes.central_hub import central_hub_bp
    from routes.uploads import uploads_bp

    # Register each blueprint with the app
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp) # auth routes will be at /login, /register, etc.
    app.register_blueprint(admin_bp) # admin routes will be at /admin/dashboard, etc.
    app.register_blueprint(donor_bp)
    app.register_blueprint(ngo_bp)
    app.register_blueprint(medical_store_bp)
    app.register_blueprint(central_hub_bp)
    app.register_blueprint(uploads_bp)
    
    # --- Register Custom Template Filters ---
    app.jinja_env.filters['b64encode'] = b64encode_filter

    # --- Register Database Teardown Function ---
    # This ensures the database connection is closed after each request
    app.teardown_appcontext(close_db)

    return app

# This is the entry point for running the application
if __name__ == '__main__':
    app = create_app()
    # The host='0.0.0.0' makes the server accessible on your local network
    app.run(debug=True, host='0.0.0.0')
