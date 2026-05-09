from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Site, db
import re
import secrets
import logging

sites_bp = Blueprint('sites', __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_user_id():
    identity = get_jwt_identity()
    if identity is None:
        return None
    return int(identity)


@sites_bp.route('/sites', methods=['GET'])
@jwt_required()
def get_sites():
    try:
        user_id = get_current_user_id()
        logger.info(f"Getting sites for user {user_id}")

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        sites = Site.query.filter_by(user_id=user_id).all()

        return jsonify({
            'success': True,
            'sites': [site.to_dict() for site in sites]
        }), 200

    except Exception as e:
        logger.error(f"Error getting sites: {str(e)}")
        return jsonify({'error': str(e)}), 500


@sites_bp.route('/sites', methods=['POST'])
@jwt_required()
def create_site():
    try:
        user_id = get_current_user_id()
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        name = data.get('name', '').strip()
        domain = data.get('domain', '').strip()

        if not name or not domain:
            return jsonify({'error': 'Missing name or domain'}), 400

        if len(name) < 3:
            return jsonify({'error': 'Site name must be at least 3 characters'}), 400

        if len(name) > 100:
            return jsonify({'error': 'Site name must be less than 100 characters'}), 400

        domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(domain_pattern, domain):
            return jsonify({'error': 'Invalid domain format. Example: example.com'}), 400

        existing_site = Site.query.filter_by(user_id=user_id, name=name).first()
        if existing_site:
            return jsonify({'error': 'You already have a site with this name'}), 409

        site = Site(
            name=name,
            domain=domain,
            user_id=user_id
        )

        db.session.add(site)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Site created successfully',
            'site': site.to_dict(include_keys=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating site: {str(e)}")
        return jsonify({'error': str(e)}), 500


@sites_bp.route('/sites/<int:site_id>/keys', methods=['GET'])
@jwt_required()
def get_site_keys(site_id):
    try:
        user_id = get_current_user_id()

        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            return jsonify({'error': 'Site not found'}), 404

        return jsonify({
            'success': True,
            'site_id': site.site_id,
            'public_key': site.public_key,
            'secret_key': site.secret_key
        }), 200

    except Exception as e:
        logger.error(f"Error getting site keys: {str(e)}")
        return jsonify({'error': str(e)}), 500


@sites_bp.route('/sites/<int:site_id>/regenerate-keys', methods=['POST'])
@jwt_required()
def regenerate_keys(site_id):
    try:
        user_id = get_current_user_id()

        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            return jsonify({'error': 'Site not found'}), 404

        site.public_key = secrets.token_urlsafe(32)
        site.secret_key = secrets.token_urlsafe(64)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Keys regenerated successfully. Old keys are now invalid.',
            'site': site.to_dict(include_keys=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error regenerating keys: {str(e)}")
        return jsonify({'error': str(e)}), 500


@sites_bp.route('/sites/<int:site_id>', methods=['DELETE'])
@jwt_required()
def delete_site(site_id):
    try:
        user_id = get_current_user_id()

        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            return jsonify({'error': 'Site not found'}), 404

        site_name = site.name

        db.session.delete(site)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Site "{site_name}" deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting site: {str(e)}")
        return jsonify({'error': str(e)}), 500


@sites_bp.route('/sites/<int:site_id>/stats', methods=['GET'])
@jwt_required()
def get_site_stats(site_id):
    try:
        user_id = get_current_user_id()

        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            return jsonify({'error': 'Site not found'}), 404

        from models import EmailLog

        sent_count = EmailLog.query.filter_by(site_id=site_id, status='sent').count()
        failed_count = EmailLog.query.filter_by(site_id=site_id, status='failed').count()
        total = sent_count + failed_count

        return jsonify({
            'success': True,
            'site': {
                'id': site.id,
                'name': site.name,
                'site_id': site.site_id,
                'domain': site.domain,
                'emails_sent': site.emails_sent,
                'created_at': site.created_at.isoformat(),
                'stats': {
                    'sent': sent_count,
                    'failed': failed_count,
                    'total': total,
                    'success_rate': (sent_count / total * 100) if total > 0 else 0
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting site stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


@sites_bp.route('/sites/<int:site_id>/toggle-status', methods=['POST'])
@jwt_required()
def toggle_site_status(site_id):
    try:
        user_id = get_current_user_id()

        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            return jsonify({'error': 'Site not found'}), 404

        site.is_active = not site.is_active
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Site status updated successfully',
            'is_active': site.is_active
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling site status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@sites_bp.route('/sites/<int:site_id>', methods=['PUT'])
@jwt_required()
def update_site(site_id):
    try:
        user_id = get_current_user_id()
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            return jsonify({'error': 'Site not found'}), 404

        if data.get('name'):
            name = data.get('name').strip()

            if len(name) < 3:
                return jsonify({'error': 'Site name must be at least 3 characters'}), 400

            if len(name) > 100:
                return jsonify({'error': 'Site name must be less than 100 characters'}), 400

            site.name = name

        if data.get('domain'):
            domain = data.get('domain').strip()
            domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

            if not re.match(domain_pattern, domain):
                return jsonify({'error': 'Invalid domain format'}), 400

            site.domain = domain

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Site updated successfully',
            'site': site.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating site: {str(e)}")
        return jsonify({'error': str(e)}), 500