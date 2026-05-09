# services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import re

class EmailService:
    @staticmethod
    def validate_email(email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_domain(domain, allowed_domain):
        return domain == allowed_domain or domain.endswith(f'.{allowed_domain}')
    
    @staticmethod
    def send_email(to_email, subject, html_content, text_content=None, from_email=None):
        try:
            if not EmailService.validate_email(to_email):
                return False, "Invalid email address"
            
            from_email = from_email or current_app.config['DEFAULT_FROM_EMAIL']
            
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            server = smtplib.SMTP(
                current_app.config['SMTP_SERVER'],
                current_app.config['SMTP_PORT']
            )
            server.starttls()
            server.login(
                current_app.config['SMTP_USERNAME'],
                current_app.config['SMTP_PASSWORD']
            )
            server.send_message(msg)
            server.quit()
            
            return True, "Email sent successfully"
        except Exception as e:
            return False, str(e)