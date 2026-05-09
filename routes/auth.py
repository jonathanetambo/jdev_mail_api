# routes/auth.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from datetime import datetime, timedelta
from models import User, db
from extensions import limiter
import re
import secrets
import time

auth_bp = Blueprint('auth', __name__)


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def current_user_id():
    identity = get_jwt_identity()
    return int(identity) if identity is not None else None


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5/hour")
def register():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400

    if len(username) > 50:
        return jsonify({'error': 'Username must be less than 50 characters'}), 400

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    if not re.search(r'[A-Za-z]', password):
        return jsonify({'error': 'Password must contain at least one letter'}), 400

    if not re.search(r'[0-9]', password):
        return jsonify({'error': 'Password must contain at least one number'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    try:
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10/minute")
def login():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username_or_email = data.get('username', '').strip()
    password = data.get('password', '')
    remember = data.get('remember', False)

    if not username_or_email or not password:
        return jsonify({'error': 'Missing username/email or password'}), 400

    user = User.query.filter(
        (User.username == username_or_email) |
        (User.email == username_or_email.lower())
    ).first()

    if not user:
        time.sleep(0.5)
        return jsonify({'error': 'Invalid credentials'}), 401

    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        return jsonify({'error': f'Account locked. Try again in {remaining} minutes'}), 403

    if not user.check_password(password):
        user.increment_login_attempts()

        if user.login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            db.session.commit()
            return jsonify({'error': 'Too many failed attempts. Account locked for 15 minutes'}), 403

        db.session.commit()
        return jsonify({'error': 'Invalid credentials'}), 401

    user.reset_login_attempts()

    expires_delta = timedelta(days=30) if remember else timedelta(hours=24)

    # CORRECTION IMPORTANTE :
    # identity doit être une chaîne, pas un entier.
    access_token = create_access_token(
        identity=str(user.id),
        expires_delta=expires_delta
    )

    refresh_token = create_refresh_token(
        identity=str(user.id)
    )

    user.last_login = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
        'expires_in': expires_delta.total_seconds()
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = current_user_id()

    new_access_token = create_access_token(
        identity=str(user_id),
        expires_delta=timedelta(hours=24)
    )

    return jsonify({
        'success': True,
        'access_token': new_access_token
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = current_user_id()

    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = current_user_id()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({'error': 'Missing passwords'}), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not user.check_password(old_password):
        return jsonify({'error': 'Current password is incorrect'}), 401

    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters'}), 400

    if not re.search(r'[A-Za-z]', new_password):
        return jsonify({'error': 'New password must contain at least one letter'}), 400

    if not re.search(r'[0-9]', new_password):
        return jsonify({'error': 'New password must contain at least one number'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Password changed successfully'
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("3/hour")
def forgot_password():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    user = User.query.filter_by(email=email).first()

    if user:
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        print(f"Reset token for {email}: {reset_token}")
        print(f"Reset link: http://localhost:5000/reset-password?token={reset_token}")

    return jsonify({
        'success': True,
        'message': 'If an account exists with this email, you will receive a password reset link.'
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
@limiter.limit("3/hour")
def reset_password():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({'error': 'Missing token or password'}), 400

    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired reset token'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    if not re.search(r'[A-Za-z]', new_password):
        return jsonify({'error': 'Password must contain at least one letter'}), 400

    if not re.search(r'[0-9]', new_password):
        return jsonify({'error': 'Password must contain at least one number'}), 400

    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Password reset successfully'
    }), 200