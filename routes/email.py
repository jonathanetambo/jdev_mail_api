from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Site, EmailLog, User, db
from services.email_service import EmailService
from services.encryption_service import EncryptionService
from extensions import limiter
import os
from datetime import datetime, timedelta
import logging

email_bp = Blueprint('email', __name__)
encryption_service = EncryptionService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_user_id():
    identity = get_jwt_identity()
    if identity is None:
        return None
    return int(identity)


@email_bp.route('/api/send-email', methods=['POST'])
@limiter.limit("50/hour")
def send_email_api():
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        site_id = data.get('site_id')
        public_key = data.get('public_key')
        secret_key = data.get('secret_key')
        to_email = data.get('to')
        subject = data.get('subject')
        html_content = data.get('html_content')
        text_content = data.get('text_content')

        if not all([site_id, public_key, secret_key, to_email, subject, html_content]):
            return jsonify({'error': 'Missing required fields'}), 400

        site = Site.query.filter_by(
            site_id=site_id,
            public_key=public_key,
            secret_key=secret_key,
            is_active=True
        ).first()

        if not site:
            return jsonify({'error': 'Invalid authentication credentials'}), 401

        if not EmailService.validate_email(to_email):
            return jsonify({'error': 'Invalid recipient email'}), 400

        success, message = EmailService.send_email(
            to_email,
            subject,
            html_content,
            text_content
        )

        email_log = EmailLog(
            recipient=to_email,
            subject=subject,
            status='sent' if success else 'failed',
            error_message=message if not success else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            site_id=site.id
        )

        db.session.add(email_log)

        if success:
            site.emails_sent += 1

        db.session.commit()

        log_data = {
            'id': email_log.id,
            'site_id': site.site_id,
            'site_name': site.name,
            'recipient': to_email,
            'subject': subject,
            'status': 'sent' if success else 'failed',
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }

        encrypted_log = encryption_service.encrypt_log(log_data)

        log_dir = 'logs/encrypted'
        os.makedirs(log_dir, exist_ok=True)

        log_file = f'{log_dir}/{site.site_id}.jdev'

        with open(log_file, 'ab') as f:
            f.write(encrypted_log + b'\n')

        if success:
            return jsonify({
                'success': True,
                'message': message,
                'log_id': email_log.id
            }), 200

        return jsonify({
            'success': False,
            'error': message
        }), 500

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in send_email_api: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/api/stats', methods=['GET'])
@jwt_required()
def get_stats():
    try:
        current_user_id = get_current_user_id()

        if not current_user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        sites = Site.query.filter_by(user_id=current_user_id).all()

        total_emails = sum(site.emails_sent for site in sites)

        total_logs = EmailLog.query.join(Site).filter(
            Site.user_id == current_user_id
        ).count()

        successful_logs = EmailLog.query.join(Site).filter(
            Site.user_id == current_user_id,
            EmailLog.status == 'sent'
        ).count()

        success_rate = (successful_logs / total_logs * 100) if total_logs > 0 else 100

        return jsonify({
            'success': True,
            'total_emails': total_emails,
            'total_sites': len(sites),
            'success_rate': f"{success_rate:.1f}",
            'avg_time': '120'
        }), 200

    except Exception as e:
        logger.error(f"Error in get_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/api/logs', methods=['GET'])
@jwt_required()
def get_logs():
    try:
        current_user_id = get_current_user_id()

        site_id = request.args.get('site_id', type=int)
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        query = EmailLog.query.join(Site).filter(
            Site.user_id == current_user_id
        )

        if site_id:
            query = query.filter(EmailLog.site_id == site_id)

        if status:
            query = query.filter(EmailLog.status == status)

        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from)
                query = query.filter(EmailLog.sent_at >= from_date)
            except Exception:
                pass

        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to)
                query = query.filter(EmailLog.sent_at <= to_date)
            except Exception:
                pass

        logs = query.order_by(EmailLog.sent_at.desc()).limit(100).all()

        logs_data = []

        for log in logs:
            logs_data.append({
                'id': log.id,
                'site_id': log.site.site_id,
                'site_name': log.site.name,
                'recipient': log.recipient,
                'subject': log.subject,
                'status': log.status,
                'sent_at': log.sent_at.isoformat(),
                'ip_address': log.ip_address,
                'error_message': log.error_message
            })

        return jsonify({
            'success': True,
            'logs': logs_data,
            'total': len(logs_data)
        }), 200

    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/api/logs/<int:log_id>', methods=['GET'])
@jwt_required()
def get_log_detail(log_id):
    try:
        current_user_id = get_current_user_id()

        log = EmailLog.query.join(Site).filter(
            EmailLog.id == log_id,
            Site.user_id == current_user_id
        ).first()

        if not log:
            return jsonify({'error': 'Log not found'}), 404

        return jsonify({
            'success': True,
            'id': log.id,
            'recipient': log.recipient,
            'subject': log.subject,
            'status': log.status,
            'sent_at': log.sent_at.isoformat(),
            'ip_address': log.ip_address,
            'error_message': log.error_message,
            'user_agent': log.user_agent,
            'site_name': log.site.name,
            'site_id': log.site.site_id
        }), 200

    except Exception as e:
        logger.error(f"Error in get_log_detail: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/api/logs/<int:log_id>/decrypt', methods=['GET'])
@jwt_required()
def decrypt_log(log_id):
    try:
        current_user_id = get_current_user_id()

        log = EmailLog.query.join(Site).filter(
            EmailLog.id == log_id,
            Site.user_id == current_user_id
        ).first()

        if not log:
            return jsonify({'error': 'Log not found'}), 404

        log_file = f'logs/encrypted/{log.site.site_id}.jdev'

        if not os.path.exists(log_file):
            return jsonify({'error': 'Log file not found'}), 404

        with open(log_file, 'rb') as f:
            for line in f:
                if line.strip():
                    try:
                        decrypted = encryption_service.decrypt_log(line.strip())

                        if decrypted.get('id') == log_id:
                            return jsonify({
                                'success': True,
                                'decrypted_log': decrypted
                            }), 200

                    except Exception as e:
                        logger.error(f"Error decrypting line: {str(e)}")

        return jsonify({'error': 'Log entry not found in encrypted file'}), 404

    except Exception as e:
        logger.error(f"Error in decrypt_log: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/api/logs/export', methods=['GET'])
@jwt_required()
def export_logs():
    try:
        current_user_id = get_current_user_id()

        logs = EmailLog.query.join(Site).filter(
            Site.user_id == current_user_id
        ).order_by(EmailLog.sent_at.desc()).all()

        export_data = {
            'success': True,
            'export_date': datetime.utcnow().isoformat(),
            'user_id': current_user_id,
            'total_logs': len(logs),
            'logs': []
        }

        for log in logs:
            export_data['logs'].append({
                'id': log.id,
                'site_name': log.site.name,
                'recipient': log.recipient,
                'subject': log.subject,
                'status': log.status,
                'sent_at': log.sent_at.isoformat(),
                'ip_address': log.ip_address,
                'error_message': log.error_message
            })

        return jsonify(export_data), 200

    except Exception as e:
        logger.error(f"Error in export_logs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@email_bp.route('/api/stats/site/<int:site_id>', methods=['GET'])
@jwt_required()
def get_site_stats(site_id):
    try:
        current_user_id = get_current_user_id()

        site = Site.query.filter_by(
            id=site_id,
            user_id=current_user_id
        ).first()

        if not site:
            return jsonify({'error': 'Site not found'}), 404

        logs = EmailLog.query.filter_by(site_id=site_id).all()

        sent_count = sum(1 for log in logs if log.status == 'sent')
        failed_count = sum(1 for log in logs if log.status == 'failed')

        daily_stats = []

        for i in range(30):
            date = datetime.utcnow().date() - timedelta(days=i)

            day_logs = [
                log for log in logs
                if log.sent_at and log.sent_at.date() == date
            ]

            daily_stats.append({
                'date': date.isoformat(),
                'count': len(day_logs),
                'sent': sum(1 for log in day_logs if log.status == 'sent'),
                'failed': sum(1 for log in day_logs if log.status == 'failed')
            })

        return jsonify({
            'success': True,
            'site': {
                'id': site.id,
                'name': site.name,
                'site_id': site.site_id,
                'domain': site.domain,
                'emails_sent': site.emails_sent,
                'created_at': site.created_at.isoformat()
            },
            'stats': {
                'total': len(logs),
                'sent': sent_count,
                'failed': failed_count,
                'success_rate': (sent_count / len(logs) * 100) if logs else 0
            },
            'daily_stats': daily_stats
        }), 200

    except Exception as e:
        logger.error(f"Error in get_site_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500