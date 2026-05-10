# services/email_service.py - Version professionnelle
import smtplib
import socket
import dns.resolver
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import re
import logging

logger = logging.getLogger(__name__)

class EmailService:
    
    @staticmethod
    def validate_email(email):
        """Validation basique d'email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def get_mx_record(domain):
        """Récupérer l'enregistrement MX du domaine"""
        try:
            records = dns.resolver.resolve(domain, 'MX')
            # Trier par priorité
            mx_records = sorted([(r.preference, str(r.exchange)) for r in records])
            return mx_records[0][1] if mx_records else None
        except Exception as e:
            logger.error(f"Error getting MX record for {domain}: {str(e)}")
            return None
    
    @staticmethod
    def send_email_direct(to_email, subject, html_content, text_content=None, from_domain=None):
        """
        Envoi d'email direct via MX record
        Méthode professionnelle sans dépendre de Gmail
        """
        try:
            # Extraire le domaine du destinataire
            recipient_domain = to_email.split('@')[1]
            
            # Récupérer le serveur MX
            mx_server = EmailService.get_mx_record(recipient_domain)
            
            if not mx_server:
                return False, f"Impossible de trouver le serveur mail pour {recipient_domain}"
            
            # Configuration
            from_email = f"noreply@{from_domain}" if from_domain else "noreply@jdevmail.com"
            
            # Création du message
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Message-ID'] = EmailService.generate_message_id()
            msg['Date'] = EmailService.get_current_date()
            
            # Contenu texte
            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            
            # Contenu HTML
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Connexion directe au serveur MX
            server = smtplib.SMTP(mx_server, 25, timeout=30)
            server.ehlo()
            
            # Envoi
            server.sendmail(from_email, [to_email], msg.as_string())
            server.quit()
            
            logger.info(f"Email sent directly to {to_email} via {mx_server}")
            return True, "Email envoyé avec succès"
            
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipient refused: {str(e)}")
            return False, "Adresse email invalide"
        except smtplib.SMTPConnectError as e:
            logger.error(f"Connection error: {str(e)}")
            return False, "Impossible de se connecter au serveur mail"
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False, f"Erreur d'envoi: {str(e)}"
    
    @staticmethod
    def send_email_via_relay(to_email, subject, html_content, text_content=None):
        """
        Envoi d'email via un serveur SMTP relais (Postfix, Sendmail, etc.)
        """
        try:
            smtp_server = current_app.config.get('SMTP_SERVER', 'localhost')
            smtp_port = current_app.config.get('SMTP_PORT', 25)
            from_email = current_app.config.get('DEFAULT_FROM_EMAIL', 'noreply@jdevmail.com')
            
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Connexion au serveur SMTP local
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.ehlo()
            
            # Authentification si nécessaire
            if current_app.config.get('SMTP_USERNAME'):
                server.starttls()
                server.ehlo()
                server.login(
                    current_app.config['SMTP_USERNAME'],
                    current_app.config['SMTP_PASSWORD']
                )
            
            server.sendmail(from_email, [to_email], msg.as_string())
            server.quit()
            
            return True, "Email envoyé avec succès"
            
        except Exception as e:
            logger.error(f"Relay error: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def generate_message_id():
        """Générer un Message-ID unique"""
        import uuid
        import time
        return f"<{uuid.uuid4()}@{time.strftime('%Y%m%d%H%M%S')}.jdevmail.com>"
    
    @staticmethod
    def get_current_date():
        """Retourner la date formatée pour l'email"""
        import email.utils
        return email.utils.formatdate()
    
    @staticmethod
    def send_email(to_email, subject, html_content, text_content=None):
        """
        Méthode principale d'envoi d'email
        Essaie d'abord l'envoi direct, puis le relais
        """
        # Validation email
        if not EmailService.validate_email(to_email):
            return False, "Format d'email invalide"
        
        # Essayer l'envoi direct
        success, message = EmailService.send_email_direct(
            to_email, subject, html_content, text_content
        )
        
        if success:
            return True, message
        
        # Si l'envoi direct échoue, essayer via relais
        logger.warning(f"Direct send failed: {message}, trying relay...")
        return EmailService.send_email_via_relay(
            to_email, subject, html_content, text_content
        )