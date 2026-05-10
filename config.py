# config.py - Version avec CORS illimité
import os
from datetime import timedelta
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class Config:
    """Configuration de base"""
    
    # Secrets
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get('JWT_ACCESS_EXPIRY_HOURS', 24)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_EXPIRY_DAYS', 30)))
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///jdev_mail.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_overflow': 20
    }
    
    # Security
    BCRYPT_LOG_ROUNDS = 12
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME_MINUTES = 15
    CSRF_ENABLED = os.environ.get('CSRF_ENABLED', 'False').lower() == 'true'  # Désactivé par défaut
    
    # Session Security
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'None'  # Changé pour permettre CORS
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Rate Limiting
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100/hour')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True
    
    # Email Configuration
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'localhost')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 25))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'False').lower() == 'true'
    SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'False').lower() == 'true'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@jdevmail.com')
    DEFAULT_FROM_NAME = os.environ.get('DEFAULT_FROM_NAME', 'JDev Mail API')
    
    # Email Direct Send
    DIRECT_EMAIL_ENABLED = os.environ.get('DIRECT_EMAIL_ENABLED', 'False').lower() == 'true'
    FALLBACK_TO_RELAY = os.environ.get('FALLBACK_TO_RELAY', 'True').lower() == 'true'
    
    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', '')
    
    # ============ CORS CONFIGURATION ILLIMITÉE ============
    # Accepter TOUTES les origines pour que n'importe quel domaine puisse utiliser l'API
    CORS_ORIGINS = ['*']  # '*' signifie toutes les origines
    CORS_ALLOW_CREDENTIALS = False  # Doit être False quand origin = '*'
    CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'HEAD']
    CORS_ALLOW_HEADERS = ['*']  # Accepter tous les headers
    CORS_EXPOSE_HEADERS = ['Content-Type', 'Authorization']
    CORS_MAX_AGE = 86400  # 24 heures
    
    # ============ FIN CORS ============
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Application
    DEBUG = False
    TESTING = False
    ENV = os.environ.get('FLASK_ENV', 'production')
    
    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    
    # Cache
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = 300
    
    @classmethod
    def init_app(cls, app):
        """Initialisation de l'application avec la configuration"""
        # Créer les dossiers nécessaires
        os.makedirs('logs', exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs('instance', exist_ok=True)
        os.makedirs('logs/encrypted', exist_ok=True)
        
        # Vérifier la clé de chiffrement
        if not cls.ENCRYPTION_KEY and cls.ENV == 'production':
            app.logger.warning('ENCRYPTION_KEY not set in production!')
        
        # Configurer le logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            file_handler = RotatingFileHandler(
                cls.LOG_FILE, 
                maxBytes=cls.LOG_MAX_BYTES, 
                backupCount=cls.LOG_BACKUP_COUNT
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            app.logger.addHandler(file_handler)
            app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))
            app.logger.info('Application startup')

class DevelopmentConfig(Config):
    """Configuration de développement - CORS illimité"""
    
    DEBUG = True
    TESTING = False
    ENV = 'development'
    
    # Sécurité désactivée en développement
    SESSION_COOKIE_SECURE = False
    CSRF_ENABLED = False
    
    # Rate limiting moins strict
    RATELIMIT_DEFAULT = "1000/hour"
    
    # Email configuration pour développement
    SMTP_SERVER = os.environ.get('DEV_SMTP_SERVER', 'localhost')
    SMTP_PORT = int(os.environ.get('DEV_SMTP_PORT', 1025))
    SMTP_USERNAME = os.environ.get('DEV_SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('DEV_SMTP_PASSWORD', '')
    SMTP_USE_TLS = False
    SMTP_USE_SSL = False
    DEFAULT_FROM_EMAIL = 'dev@jdevmail.local'
    
    # Base de données SQLite pour développement
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL', 'sqlite:///jdev_mail_dev.db')
    
    # CORS large pour développement - Accepter TOUTES les origines
    CORS_ORIGINS = ['*']
    CORS_ALLOW_CREDENTIALS = False
    CORS_ALLOW_HEADERS = ['*']
    
    # Direct email désactivé en développement
    DIRECT_EMAIL_ENABLED = False
    FALLBACK_TO_RELAY = False

class TestingConfig(Config):
    """Configuration de test"""
    
    TESTING = True
    DEBUG = True
    ENV = 'testing'
    
    # Base de données en mémoire pour les tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
    
    # Désactiver rate limiting pour les tests
    RATELIMIT_ENABLED = False
    
    # Désactiver email pour les tests
    DIRECT_EMAIL_ENABLED = False
    FALLBACK_TO_RELAY = False
    
    # Sessions sans sécurité
    SESSION_COOKIE_SECURE = False
    CSRF_ENABLED = False
    
    # CORS large pour les tests
    CORS_ORIGINS = ['*']
    CORS_ALLOW_CREDENTIALS = False
    
    # Logging minimal
    LOG_LEVEL = 'ERROR'

class ProductionConfig(Config):
    """Configuration de production - CORS configurable"""
    
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # Sécurité renforcée
    SESSION_COOKIE_SECURE = True
    CSRF_ENABLED = os.environ.get('CSRF_ENABLED', 'False').lower() == 'true'
    
    # Rate limiting strict
    RATELIMIT_DEFAULT = "100/hour"
    
    # Base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///jdev_mail_prod.db')
    
    # Email configuration
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'localhost')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 25))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'False').lower() == 'true'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@jdevmail.com')
    
    # CORS pour production - Peut être configuré via variable d'environnement
    # Par défaut, accepter toutes les origines pour que l'API soit accessible partout
    cors_origins_env = os.environ.get('CORS_ORIGINS', '*')
    if cors_origins_env == '*':
        CORS_ORIGINS = ['*']
        CORS_ALLOW_CREDENTIALS = False
    else:
        CORS_ORIGINS = cors_origins_env.split(',')
        CORS_ALLOW_CREDENTIALS = True
    
    CORS_ALLOW_HEADERS = ['*']
    
    # Direct email
    DIRECT_EMAIL_ENABLED = os.environ.get('DIRECT_EMAIL_ENABLED', 'False').lower() == 'true'
    FALLBACK_TO_RELAY = True
    
    # Logging
    LOG_LEVEL = 'WARNING'

class PythonAnywhereConfig(ProductionConfig):
    """Configuration spécifique pour PythonAnywhere - CORS illimité"""
    
    # PythonAnywhere configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 1,
        'pool_recycle': 300,
        'pool_pre_ping': True
    }
    
    # SMTP PythonAnywhere
    SMTP_SERVER = 'smtp.pythonanywhere.com'
    SMTP_PORT = 587
    SMTP_USE_TLS = True
    SMTP_USERNAME = os.environ.get('PA_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('PA_PASSWORD', '')
    DEFAULT_FROM_EMAIL = f'noreply@{os.environ.get("PA_USERNAME", "dzoko243")}.pythonanywhere.com'
    
    # CORS illimité pour PythonAnywhere - Accepter TOUTES les origines
    CORS_ORIGINS = ['*']
    CORS_ALLOW_CREDENTIALS = False
    CORS_ALLOW_HEADERS = ['*']
    CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'HEAD']
    CORS_MAX_AGE = 86400
    
    # Rate limiting adapté
    RATELIMIT_DEFAULT = "50/hour"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Désactiver CSRF pour faciliter les requêtes API
    CSRF_ENABLED = False

# Dictionnaire des configurations
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'pythonanywhere': PythonAnywhereConfig,
    'default': DevelopmentConfig
}

# Fonction utilitaire pour obtenir la configuration
def get_config():
    """Retourne la configuration appropriée basée sur l'environnement"""
    env = os.environ.get('FLASK_ENV', 'development')
    
    # Détection automatique de PythonAnywhere
    server_software = os.environ.get('SERVER_SOFTWARE', '')
    if 'pythonanywhere' in server_software.lower() or 'PYTHONANYWHERE' in os.environ:
        return PythonAnywhereConfig
    
    return config.get(env, DevelopmentConfig)

