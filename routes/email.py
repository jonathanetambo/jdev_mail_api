# routes/email.py - Version complète et corrigée
from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Site, EmailLog, User, db
from services.email_service import EmailService
from services.encryption_service import EncryptionService
from extensions import limiter
import os
from datetime import datetime, timedelta
import logging
import traceback

email_bp = Blueprint('email', __name__)
encryption_service = EncryptionService()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_user_id():
    """Récupère l'ID de l'utilisateur courant de manière sécurisée"""
    try:
        identity = get_jwt_identity()
        if identity is None:
            return None
        return int(identity) if isinstance(identity, str) and identity.isdigit() else identity
    except Exception as e:
        logger.error(f"Error getting user identity: {str(e)}")
        return None


def add_cors_headers(response):
    """Ajoute les headers CORS à la réponse"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
    response.headers.add('Access-Control-Expose-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response


@email_bp.route('/api/send-email', methods=['OPTIONS', 'POST'])
@limiter.limit("50/hour")
def send_email_api():
    """Endpoint public pour envoyer des emails - Support CORS complet"""
    
    # Gestion de la requête OPTIONS (preflight CORS)
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200
    
    try:
        # Log de la requête
        logger.info(f"=== SEND EMAIL REQUEST ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Récupération des données
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        if not data:
            response = jsonify({'success': False, 'error': 'No data provided'})
            return add_cors_headers(response), 400
        
        # Validation des champs requis
        site_id = data.get('site_id')
        public_key = data.get('public_key')
        secret_key = data.get('secret_key')
        to_email = data.get('to')
        subject = data.get('subject')
        html_content = data.get('html_content')
        text_content = data.get('text_content')
        
        # Vérification des champs obligatoires
        missing_fields = []
        if not site_id: missing_fields.append('site_id')
        if not public_key: missing_fields.append('public_key')
        if not secret_key: missing_fields.append('secret_key')
        if not to_email: missing_fields.append('to')
        if not subject: missing_fields.append('subject')
        if not html_content: missing_fields.append('html_content')
        
        if missing_fields:
            response = jsonify({
                'success': False, 
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            })
            return add_cors_headers(response), 400
        
        # Authentification du site
        logger.info(f"Authenticating site: {site_id}")
        site = Site.query.filter_by(
            site_id=site_id,
            public_key=public_key,
            secret_key=secret_key,
            is_active=True
        ).first()
        
        if not site:
            logger.warning(f"Authentication failed for site_id: {site_id}")
            response = jsonify({'success': False, 'error': 'Invalid authentication credentials'})
            return add_cors_headers(response), 401
        
        logger.info(f"Site authenticated: {site.name} (ID: {site.id})")
        
        # Validation de l'email
        if not EmailService.validate_email(to_email):
            response = jsonify({'success': False, 'error': 'Invalid recipient email format'})
            return add_cors_headers(response), 400
        
        # Envoi de l'email
        logger.info(f"Sending email to: {to_email}")
        success, message = EmailService.send_email(
            to_email,
            subject,
            html_content,
            text_content
        )
        
        # Création du log en base de données
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
            logger.info(f"Email sent successfully to {to_email}")
        else:
            logger.error(f"Failed to send email to {to_email}: {message}")
        
        db.session.commit()
        
        # Création du log chiffré
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
        
        # Sauvegarde du log chiffré
        try:
            encrypted_log = encryption_service.encrypt_log(log_data)
            log_dir = 'logs/encrypted'
            os.makedirs(log_dir, exist_ok=True)
            log_file = f'{log_dir}/{site.site_id}.jdev'
            
            with open(log_file, 'ab') as f:
                f.write(encrypted_log + b'\n')
            logger.info(f"Encrypted log saved to {log_file}")
        except Exception as e:
            logger.error(f"Error saving encrypted log: {str(e)}")
        
        # Réponse de succès
        if success:
            response = jsonify({
                'success': True,
                'message': message,
                'log_id': email_log.id,
                'status': 'sent'
            })
            return add_cors_headers(response), 200
        else:
            response = jsonify({
                'success': False,
                'error': message,
                'log_id': email_log.id,
                'status': 'failed'
            })
            return add_cors_headers(response), 500
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error in send_email_api: {str(e)}")
        logger.error(traceback.format_exc())
        
        response = jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'type': type(e).__name__
        })
        return add_cors_headers(response), 500


@email_bp.route('/api/stats', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def get_stats():
    """Obtenir les statistiques globales de l'utilisateur"""
    
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200
    
    try:
        current_user_id = get_current_user_id()
        
        if not current_user_id:
            response = jsonify({'success': False, 'error': 'User not authenticated'})
            return add_cors_headers(response), 401
        
        user = User.query.get(current_user_id)
        if not user:
            response = jsonify({'success': False, 'error': 'User not found'})
            return add_cors_headers(response), 404
        
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
        
        response = jsonify({
            'success': True,
            'total_emails': total_emails,
            'total_sites': len(sites),
            'success_rate': f"{success_rate:.1f}",
            'avg_time': '120'
        })
        return add_cors_headers(response), 200
        
    except Exception as e:
        logger.error(f"Error in get_stats: {str(e)}")
        response = jsonify({'success': False, 'error': str(e)})
        return add_cors_headers(response), 500


@email_bp.route('/api/logs', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def get_logs():
    """Récupérer les logs de l'utilisateur"""
    
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200
    
    try:
        current_user_id = get_current_user_id()
        
        if not current_user_id:
            response = jsonify({'success': False, 'error': 'User not authenticated'})
            return add_cors_headers(response), 401
        
        site_id = request.args.get('site_id', type=int)
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        limit = request.args.get('limit', 100, type=int)
        
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
        
        logs = query.order_by(EmailLog.sent_at.desc()).limit(limit).all()
        
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
        
        response = jsonify({
            'success': True,
            'logs': logs_data,
            'total': len(logs_data)
        })
        return add_cors_headers(response), 200
        
    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}")
        response = jsonify({'success': False, 'error': str(e)})
        return add_cors_headers(response), 500


@email_bp.route('/api/logs/<int:log_id>', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def get_log_detail(log_id):
    """Récupérer un log spécifique"""
    
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200
    
    try:
        current_user_id = get_current_user_id()
        
        if not current_user_id:
            response = jsonify({'success': False, 'error': 'User not authenticated'})
            return add_cors_headers(response), 401
        
        log = EmailLog.query.join(Site).filter(
            EmailLog.id == log_id,
            Site.user_id == current_user_id
        ).first()
        
        if not log:
            response = jsonify({'success': False, 'error': 'Log not found'})
            return add_cors_headers(response), 404
        
        response = jsonify({
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
        })
        return add_cors_headers(response), 200
        
    except Exception as e:
        logger.error(f"Error in get_log_detail: {str(e)}")
        response = jsonify({'success': False, 'error': str(e)})
        return add_cors_headers(response), 500


@email_bp.route('/api/logs/<int:log_id>/decrypt', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def decrypt_log(log_id):
    """Déchiffrer un log spécifique"""
    
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200
    
    try:
        current_user_id = get_current_user_id()
        
        if not current_user_id:
            response = jsonify({'success': False, 'error': 'User not authenticated'})
            return add_cors_headers(response), 401
        
        log = EmailLog.query.join(Site).filter(
            EmailLog.id == log_id,
            Site.user_id == current_user_id
        ).first()
        
        if not log:
            response = jsonify({'success': False, 'error': 'Log not found'})
            return add_cors_headers(response), 404
        
        log_file = f'logs/encrypted/{log.site.site_id}.jdev'
        
        if not os.path.exists(log_file):
            response = jsonify({'success': False, 'error': 'Log file not found'})
            return add_cors_headers(response), 404
        
        with open(log_file, 'rb') as f:
            for line in f:
                if line.strip():
                    try:
                        decrypted = encryption_service.decrypt_log(line.strip())
                        if decrypted.get('id') == log_id:
                            response = jsonify({
                                'success': True,
                                'decrypted_log': decrypted
                            })
                            return add_cors_headers(response), 200
                    except Exception as e:
                        logger.error(f"Error decrypting line: {str(e)}")
                        continue
        
        response = jsonify({'success': False, 'error': 'Log entry not found in encrypted file'})
        return add_cors_headers(response), 404
        
    except Exception as e:
        logger.error(f"Error in decrypt_log: {str(e)}")
        response = jsonify({'success': False, 'error': str(e)})
        return add_cors_headers(response), 500


@email_bp.route('/api/logs/export', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def export_logs():
    """Exporter les logs au format JSON"""
    
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200
    
    try:
        current_user_id = get_current_user_id()
        
        if not current_user_id:
            response = jsonify({'success': False, 'error': 'User not authenticated'})
            return add_cors_headers(response), 401
        
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
        
        response = jsonify(export_data)
        return add_cors_headers(response), 200
        
    except Exception as e:
        logger.error(f"Error in export_logs: {str(e)}")
        response = jsonify({'success': False, 'error': str(e)})
        return add_cors_headers(response), 500


@email_bp.route('/api/stats/site/<int:site_id>', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def get_site_stats(site_id):
    """Obtenir les statistiques d'un site spécifique"""
    
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200
    
    try:
        current_user_id = get_current_user_id()
        
        if not current_user_id:
            response = jsonify({'success': False, 'error': 'User not authenticated'})
            return add_cors_headers(response), 401
        
        site = Site.query.filter_by(
            id=site_id,
            user_id=current_user_id
        ).first()
        
        if not site:
            response = jsonify({'success': False, 'error': 'Site not found'})
            return add_cors_headers(response), 404
        
        logs = EmailLog.query.filter_by(site_id=site_id).all()
        
        sent_count = sum(1 for log in logs if log.status == 'sent')
        failed_count = sum(1 for log in logs if log.status == 'failed')
        
        daily_stats = []
        for i in range(30):
            date = datetime.utcnow().date() - timedelta(days=i)
            day_logs = [log for log in logs if log.sent_at and log.sent_at.date() == date]
            daily_stats.append({
                'date': date.isoformat(),
                'count': len(day_logs),
                'sent': sum(1 for log in day_logs if log.status == 'sent'),
                'failed': sum(1 for log in day_logs if log.status == 'failed')
            })
        
        response = jsonify({
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
        })
        return add_cors_headers(response), 200
        
    except Exception as e:
        logger.error(f"Error in get_site_stats: {str(e)}")
        response = jsonify({'success': False, 'error': str(e)})
        return add_cors_headers(response), 500


# Endpoint de test CORS
@email_bp.route('/api/test', methods=['GET', 'OPTIONS'])
def test_endpoint():
    """Endpoint de test pour vérifier que l'API fonctionne"""
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response), 200
    
    response = jsonify({
        'success': True,
        'message': 'JDev Mail API is working!',
        'timestamp': datetime.utcnow().isoformat(),
        'cors_enabled': True
    })
    return add_cors_headers(response), 200