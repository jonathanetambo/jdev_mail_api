# app.py
from flask import Flask, render_template, jsonify, g, request
from config import config
from extensions import db, jwt, bcrypt, limiter
from routes.auth import auth_bp
from routes.sites import sites_bp
from routes.email import email_bp
from flask_jwt_extended import jwt_required, verify_jwt_in_request, get_jwt_identity
from models import User
import os

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(sites_bp, url_prefix='/api')
    app.register_blueprint(email_bp, url_prefix='')
    
    # Create directories
    os.makedirs('logs/encrypted', exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/login')
    def login_page():
        return render_template('login.html')
    
    @app.route('/register')
    def register_page():
        return render_template('register.html')
    
    # app.py - Ajouter ces routes après les routes existantes

    @app.route('/features')
    def features():
        return render_template('features.html')

    @app.route('/pricing')
    def pricing():
        return render_template('pricing.html')

    @app.route('/docs')
    def documentation():
        return render_template('docs.html')

    @app.route('/logout')
    @jwt_required(optional=True)
    def logout():
        # Le frontend supprimera les tokens JWT
        return render_template('logout.html')
    
    # app.py - Vérifiez que cette partie est correcte

    @app.before_request
    def load_current_user():
        """Load current user for templates"""
        g.current_user = None
        # Skip for static files
        if request.endpoint and request.endpoint.startswith('static'):
            return
        
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # Verify JWT token
                from flask_jwt_extended import decode_token
                decoded = decode_token(token)
                user_id = decoded.get('sub')
                if user_id:
                    user = User.query.get(int(user_id))
                    g.current_user = user
            except:
                pass
        
        # Also check for token in cookies/localStorage via request args
        # This is for page loads that don't have Authorization header

    @app.context_processor
    def inject_user():
        """Make current_user available in all templates"""
        return {'current_user': g.current_user}
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print("JWT INVALID ERROR:", error)
        return jsonify({
            "success": False,
            "error": "Token invalide",
            "details": error
        }), 422

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        print("JWT MISSING ERROR:", error)
        return jsonify({
            "success": False,
            "error": "Token manquant",
            "details": error
        }), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        print("JWT EXPIRED")
        return jsonify({
            "success": False,
            "error": "Token expiré"
        }), 401
    
    return app

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    app.run(debug=True, host='0.0.0.0', port=5000)