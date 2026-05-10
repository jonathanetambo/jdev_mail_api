# services/sendmail_service.py
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class SendmailService:
    @staticmethod
    def send_email(to_email, subject, html_content, text_content=None):
        """Utiliser sendmail directement"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = 'noreply@jdevmail.com'
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Envoyer via sendmail
            process = subprocess.Popen(
                ['/usr/sbin/sendmail', '-t', '-i'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(msg.as_string().encode('utf-8'))
            
            if process.returncode == 0:
                return True, "Email envoyé"
            else:
                return False, stderr.decode()
                
        except Exception as e:
            return False, str(e)