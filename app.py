# app.py - Version complète avec CORS illimité
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
    
    # ============ CONFIGURATION CORS ILLIMITÉE ============
    # Accepter TOUTES les origines pour que n'importe quel domaine puisse utiliser l'API
    CORS(app, 
         resources={
             r"/*": {  # Appliquer à toutes les routes
                 "origins": "*",  # Accepter TOUTES les origines
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
                 "allow_headers": ["*"],  # Accepter tous les headers
                 "expose_headers": ["*"],
                 "supports_credentials": False,  # Mettre à False pour permettre origin *
                 "max_age": 86400  # Cache preflight pour 24h
             }
         })
    
    # Middleware CORS personnalisé pour garantir l'ajout des headers
    @app.after_request
    def add_cors_headers(response):
        """Ajouter les headers CORS à TOUTES les réponses sans restriction"""
        # Permettre toutes les origines
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin, X-CSRFToken'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '86400'
        response.headers['Access-Control-Allow-Credentials'] = 'false'
        
        return response
    
    # Gérer TOUTES les requêtes OPTIONS (preflight) 
    @app.before_request
    def handle_preflight():
        """Répondre immédiatement aux requêtes OPTIONS"""
        if request.method == "OPTIONS":
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin'
            response.headers['Access-Control-Max-Age'] = '86400'
            response.headers['Access-Control-Allow-Credentials'] = 'false'
            return response, 200
    
    # ============ FIN CONFIGURATION CORS ============
    
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
        return render_template('logout.html')
    
    # Endpoint de test public (sans authentification)
    @app.route('/api/test', methods=['GET', 'OPTIONS', 'POST'])
    def test_api():
        """Endpoint public pour tester l'API - aucun auth requis"""
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response, 200
        
        return jsonify({
            'success': True,
            'message': 'JDev Mail API is working!',
            'cors_enabled': True,
            'any_domain_allowed': True,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat()
        }), 200
    
    # Endpoint public pour obtenir les informations de l'API
    @app.route('/api/info', methods=['GET'])
    def api_info():
        """Informations publiques sur l'API"""
        return jsonify({
            'name': 'JDev Mail API',
            'version': '1.0.0',
            'description': 'Professional Email API Service',
            'endpoints': {
                'send_email': '/api/send-email',
                'test': '/api/test',
                'docs': '/docs'
            },
            'cors': {
                'enabled': True,
                'all_origins_allowed': True
            }
        }), 200
    
    # Endpoint de test CORS
    @app.route('/api/test-cors', methods=['GET', 'OPTIONS'])
    def test_cors():
        """Endpoint pour tester la configuration CORS"""
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response, 200
        
        return jsonify({
            "success": True,
            "message": "CORS is correctly configured!",
            "origin": request.headers.get('Origin', 'No origin'),
            "any_domain_allowed": True,
            "your_ip": request.remote_addr
        }), 200
    
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
        response = jsonify({
            "success": False,
            "error": "Token invalide",
            "details": str(error)
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 422
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        logger.warning(f"JWT MISSING ERROR: {error}")
        response = jsonify({
            "success": False,
            "error": "Token manquant. Veuillez vous authentifier.",
            "details": str(error)
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        logger.warning("JWT EXPIRED")
        response = jsonify({
            "success": False,
            "error": "Token expiré. Veuillez vous reconnecter.",
            "code": "token_expired"
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 401
    
    # Error handlers généraux avec CORS
    @app.errorhandler(404)
    def not_found_error(error):
        response = jsonify({
            "success": False,
            "error": "Ressource non trouvée"
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        response = jsonify({
            "success": False,
            "error": "Erreur interne du serveur"
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500
    
    return app

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    
    # Démarrer l'application
    host = '0.0.0.0'  # Écouter sur toutes les interfaces
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("=" * 50)
    logger.info("JDev Mail API - Server Starting")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"CORS: Enabled for ALL domains")
    logger.info(f"Test URL: http://{host}:{port}/api/test")
    logger.info("=" * 50)
    
    app.run(debug=True, host=host, port=port)