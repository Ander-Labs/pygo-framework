"""PyGo Email System (v0.31.0).

Provides SMTP integration, templates, and email queue.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from dataclasses import dataclass
from io import StringIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import base64


@dataclass
class Email:
    """Represents an email message."""
    to: str
    subject: str
    body: str
    html: Optional[str] = None
    from_email: Optional[str] = None
    attachments: list = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class EmailTemplate:
    """Email template with Jinja2-like syntax."""
    
    def __init__(self, template: str):
        self.template = template
    
    def render(self, context: Dict[str, Any]) -> str:
        """Render template with context."""
        result = self.template
        
        # Simple variable substitution {{ var }}
        for key, value in context.items():
            result = result.replace("{{ " + key + " }}", str(value))
            result = result.replace("{{" + key + "}}", str(value))
        
        return result


class EmailSender:
    """Sends emails via SMTP."""
    
    def __init__(self, host: str = "localhost", port: int = 25,
                 username: Optional[str] = None, password: Optional[str] = None,
                 use_tls: bool = False, use_ssl: bool = False):
        self.host = host
        self.port = port
        self.username = username or os.environ.get("PYGO_SMTP_USER", "")
        self.password = password or os.environ.get("PYGO_SMTP_PASS", "")
        self.use_tls = use_tls
        self.use_ssl = use_ssl
    
    def send(self, email: Email) -> bool:
        """Send an email."""
        msg = MIMEMultipart()
        msg["From"] = email.from_email or "noreply@localhost"
        msg["To"] = email.to
        msg["Subject"] = email.subject
        
        if email.html:
            msg.attach(MIMEText(email.body, "plain"))
            msg.attach(MIMEText(email.html, "html"))
        else:
            msg.attach(MIMEText(email.body, "plain"))
        
        for attachment in email.attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment["content"])
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {attachment['filename']}"
            )
            msg.attach(part)
        
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port)
            else:
                server = smtplib.SMTP(self.host, self.port)
            
            if self.use_tls:
                server.starttls()
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Email send failed: {e}")
            return False


class EmailQueue:
    """Queue for sending emails asynchronously."""
    
    def __init__(self, sender: Optional[EmailSender] = None):
        self.sender = sender or EmailSender()
        self._queue = []
    
    def enqueue(self, email: Email) -> int:
        """Add email to queue."""
        self._queue.append(email)
        return len(self._queue) - 1
    
    def send_all(self) -> Dict[str, int]:
        """Send all emails in queue."""
        results = {"sent": 0, "failed": 0}
        
        for email in self._queue:
            if self.sender.send(email):
                results["sent"] += 1
            else:
                results["failed"] += 1
        
        self._queue.clear()
        return results


# Convenience functions
def send_email(to: str, subject: str, body: str, 
               html: Optional[str] = None,
               from_email: Optional[str] = None) -> bool:
    """Send an email immediately."""
    email = Email(to=to, subject=subject, body=body, html=html, from_email=from_email)
    sender = EmailSender()
    return sender.send(email)


def render_template(template: str, context: Dict[str, Any]) -> str:
    """Render an email template."""
    t = EmailTemplate(template)
    return t.render(context)


def queue_email(email: Email) -> int:
    """Add email to queue."""
    return EmailQueue().enqueue(email)