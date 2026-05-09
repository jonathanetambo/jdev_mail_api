# models/__init__.py
from datetime import datetime
import secrets
import hashlib
from extensions import db
from flask_bcrypt import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add these new fields
    last_login = db.Column(db.DateTime, nullable=True)
    reset_token = db.Column(db.String(128), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(128), nullable=True)
    
    sites = db.relationship('Site', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def increment_login_attempts(self):
        self.login_attempts += 1
        db.session.commit()
    
    def reset_login_attempts(self):
        self.login_attempts = 0
        self.locked_until = None
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

class Site(db.Model):
    __tablename__ = 'sites'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    public_key = db.Column(db.String(64), unique=True, nullable=False)
    secret_key = db.Column(db.String(128), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    emails_sent = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    email_logs = db.relationship('EmailLog', backref='site', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.site_id:
            self.site_id = secrets.token_hex(16)
        if not self.public_key:
            self.public_key = secrets.token_urlsafe(32)
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(64)
    
    def to_dict(self, include_keys=False):
        data = {
            'id': self.id,
            'site_id': self.site_id,
            'name': self.name,
            'domain': self.domain,
            'is_active': self.is_active,
            'emails_sent': self.emails_sent,
            'created_at': self.created_at.isoformat()
        }
        if include_keys:
            data['public_key'] = self.public_key
            data['secret_key'] = self.secret_key
        return data

class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # sent, failed, spam
    error_message = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(255), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'recipient': self.recipient,
            'subject': self.subject,
            'status': self.status,
            'sent_at': self.sent_at.isoformat()
        }