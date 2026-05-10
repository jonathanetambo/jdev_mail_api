# app.py - Version complète et corrigée
from flask import Flask, render_template, jsonify, g, request, make_response
from flask_cors import CORS
from config import config
from extensions import db, jwt, bcrypt, limiter
from routes.auth import auth_bp
from routes.sites import sites_bp
from routes.email import email_bp
from flask_jwt_extended import jwt_required, verify_jwt_in_request, get_jwt_identity, decode_token
from models import User
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Configuration CORS complète
    CORS(app, 
         resources={
             r"/api/*": {
                 "origins": [
                     "http://localhost",
                     "http://localhost:5000",
                     "http://localhost:5500",
                     "http://127.0.0.1",
                     "http://127.0.0.1:5000",
                     "http://127.0.0.1:5500",
                     "https://dzoko243.pythonanywhere.com",
                     "https://*.pythonanywhere.com",
                     "*"  # En développement uniquement
                 ],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
                 "expose_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "max_age": 3600
             },
             r"/auth/*": {
                 "origins": "*",
                 "methods": ["GET", "POST", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True
             }
         })
    
    # Middleware CORS personnalisé pour toutes les routes
    @app.after_request
    def after_request(response):
        """Ajouter les headers CORS à toutes les réponses"""
        origin = request.headers.get('Origin')
        
        # Origines autorisées
        allowed_origins = [
            'http://localhost',
            'http://localhost:5000',
            'http://localhost:5500',
            'http://127.0.0.1',
            'http://127.0.0.1:5000',
            'http://127.0.0.1:5500',
            'https://dzoko243.pythonanywhere.com'
        ]
        
        # Vérifier si l'origine est autorisée
        if origin:
            if origin in allowed_origins or 'pythonanywhere.com' in origin or 'localhost' in origin:
                response.headers.add('Access-Control-Allow-Origin', origin)
                response.headers.add('Access-Control-Allow-Credentials', 'true')
                response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
                response.headers.add('Access-Control-Expose-Headers', 'Content-Type, Authorization')
                response.headers.add('Access-Control-Max-Age', '3600')
        
        return response
    
    # Gérer les requêtes OPTIONS (preflight)
    @app.route('/api/<path:path>', methods=['OPTIONS'])
    @app.route('/auth/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        """Répondre aux requêtes OPTIONS pour CORS preflight"""
        response = make_response()
        origin = request.headers.get('Origin')
        
        if origin:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
            response.headers.add('Access-Control-Max-Age', '3600')
        
        return response, 200
    
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
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
    
    # Routes HTML
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
    def logout():
        """Page de déconnexion"""
        return render_template('logout.html')
    
    # Load current user for templates
    @app.before_request
    def load_current_user():
        """Load current user for templates"""
        g.current_user = None
        
        # Skip for static files and API routes
        if request.endpoint and (request.endpoint.startswith('static') or request.path.startswith('/api/')):
            return
        
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                decoded = decode_token(token)
                user_id = decoded.get('sub')
                if user_id:
                    user = User.query.get(int(user_id))
                    g.current_user = user
            except Exception as e:
                logger.debug(f"Token validation error: {str(e)}")
    
    @app.context_processor
    def inject_user():
        """Make current_user available in all templates"""
        return {'current_user': g.current_user}
    
    # JWT Error handlers
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        logger.warning(f"JWT INVALID ERROR: {error}")
        return jsonify({
            "success": False,
            "error": "Token invalide",
            "details": str(error)
        }), 422
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        logger.warning(f"JWT MISSING ERROR: {error}")
        return jsonify({
            "success": False,
            "error": "Token manquant. Veuillez vous authentifier.",
            "details": str(error)
        }), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        logger.warning("JWT EXPIRED")
        return jsonify({
            "success": False,
            "error": "Token expiré. Veuillez vous reconnecter.",
            "code": "token_expired"
        }), 401
    
    # Error handlers généraux
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "success": False,
            "error": "Ressource non trouvée"
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            "success": False,
            "error": "Erreur interne du serveur"
        }), 500
    
    # Endpoint de test CORS
    @app.route('/api/test-cors', methods=['GET', 'OPTIONS'])
    def test_cors():
        """Endpoint pour tester la configuration CORS"""
        if request.method == 'OPTIONS':
            return _build_cors_preflight_response()
        
        return jsonify({
            "success": True,
            "message": "CORS est correctement configuré !",
            "origin": request.headers.get('Origin'),
            "method": request.method
        })
    
    def _build_cors_preflight_response():
        """Construire la réponse preflight CORS"""
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response
    
    return app

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    
    # Démarrer l'application
    host = '0.0.0.0' if os.environ.get('FLASK_ENV') == 'production' else '127.0.0.1'
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Starting JDev Mail API on {host}:{port}")
    app.run(debug=True, host=host, port=port)