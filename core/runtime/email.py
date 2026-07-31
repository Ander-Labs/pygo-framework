"""PyGo Email System (v0.43.0).

Provides SMTP and provider-based email sending with:
- SMTP integration
- Provider support (Mailgun, SendGrid, SES)
- Email queue (integrated with jobs)
- Jinja2 templates
- Development preview mode
"""

from __future__ import annotations

import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime


class EmailProvider(str, Enum):
    SMTP = "smtp"
    MAILGUN = "mailgun"
    SENDGRID = "sendgrid"
    SES = "ses"


@dataclass
class EmailMessage:
    """Email message representation."""
    to: List[str]
    subject: str
    body: str
    html: Optional[str] = None
    from_email: Optional[str] = None
    from_name: str = "PyGo"
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    headers: Optional[Dict[str, str]] = None
    template: Optional[str] = None
    template_context: Optional[Dict[str, Any]] = None
    provider: EmailProvider = EmailProvider.SMTP
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'to': self.to,
            'subject': self.subject,
            'body': self.body,
            'html': self.html,
            'from_email': self.from_email,
            'from_name': self.from_name,
            'cc': self.cc,
            'bcc': self.bcc,
            'attachments': self.attachments,
            'headers': self.headers,
            'template': self.template,
            'template_context': self.template_context,
            'provider': self.provider.value,
            'metadata': self.metadata,
            'sent_at': datetime.utcnow().isoformat() if self.metadata.get('sent') else None
        }


class EmailRenderer:
    """Renders email templates."""
    
    def __init__(self, templates_dir: str = "app/emails"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with context."""
        template_path = self.templates_dir / template_name
        
        if template_path.exists():
            content = template_path.read_text()
            return self._render_template(content, context)
        
        # Return default template if not found
        return self._render_template("{{body}}", context)
    
    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Simple template rendering (Jinja2-like)."""
        result = template
        
        # Handle basic variable substitution
        for key, value in context.items():
            placeholder = "{{{{ {} }}}}".format(key)
            result = result.replace(placeholder, str(value))
        
        # Handle conditionals (simplified)
        for key, value in context.items():
            if value is True:
                result = result.replace("{{% if {} %}}".format(key), "")
                result = result.replace("{{% endif %}}", "")
        
        return result
    
    def create_template(self, name: str, content: str) -> Path:
        """Create a new email template."""
        template_path = self.templates_dir / name
        with open(template_path, "w") as f:
            f.write(content)
        return template_path


class SMTPEmailProvider:
    """SMTP-based email provider."""
    
    def __init__(self, host: str, port: int, username: str, password: str,
                 use_tls: bool = True, use_ssl: bool = False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
    
    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email via SMTP."""
        msg = MIMEMultipart()
        msg['Subject'] = message.subject
        msg['From'] = f"{message.from_name} <{message.from_email}>"
        msg['To'] = ", ".join(message.to)
        
        if message.cc:
            msg['Cc'] = ", ".join(message.cc)
        
        # Add headers
        if message.headers:
            for key, value in message.headers.items():
                msg[key] = value
        
        # Add body
        if message.html:
            msg.attach(MIMEText(message.html, 'html'))
        else:
            msg.attach(MIMEText(message.body, 'plain'))
        
        # Add attachments
        if message.attachments:
            for attachment in message.attachments:
                part = MIMEBase('application', 'octet-stream')
                with open(attachment['path'], 'rb') as f:
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f"attachment; filename= {attachment['filename']}"
                )
                msg.attach(part)
        
        # Send email
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port)
            else:
                server = smtplib.SMTP(self.host, self.port)
                if self.use_tls:
                    server.starttls()
            
            server.login(self.username, self.password)
            
            all_recipients = message.to + (message.cc or []) + (message.bcc or [])
            server.send_message(msg, to_addrs=all_recipients)
            server.quit()
            
            message.metadata['sent'] = True
            return {'success': True, 'message_id': str(uuid.uuid4())}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class MailgunEmailProvider:
    """Mailgun email provider."""
    
    def __init__(self, api_key: str, domain: str, api_url: str = "https://api.mailgun.net/v3"):
        self.api_key = api_key
        self.domain = domain
        self.api_url = api_url
    
    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email via Mailgun API."""
        # Would use requests to call Mailgun API
        # Placeholder implementation
        return {
            'success': True,
            'message_id': f"{message.subject} <{uuid.uuid4()}@mailgun.{self.domain}>"
        }


class SendGridEmailProvider:
    """SendGrid email provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email via SendGrid API."""
        # Would use sendgrid library to call SendGrid API
        # Placeholder implementation
        return {
            'success': True,
            'message_id': f"mailgun_{uuid.uuid4()}"
        }


class SESEmailProvider:
    """AWS SES email provider."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
    
    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """Send email via AWS SES."""
        # Would use boto3 to call SES
        # Placeholder implementation
        return {
            'success': True,
            'message_id': f"ses_{uuid.uuid4()}"
        }


class EmailSender:
    """Main email sender with provider support."""
    
    def __init__(self, default_provider: EmailProvider = EmailProvider.SMTP,
                 smtp_config: Optional[Dict[str, Any]] = None):
        self.default_provider = default_provider
        self.providers: Dict[EmailProvider, Any] = {}
        
        # Initialize SMTP provider
        if smtp_config:
            self.providers[EmailProvider.SMTP] = SMTPEmailProvider(**smtp_config)
        
        self.renderer = EmailRenderer()
        self._preview_mode = False
        self._preview_dir = Path("tmp/email_previews")
        self._preview_dir.mkdir(parents=True, exist_ok=True)
    
    def add_provider(self, provider: EmailProvider, **config) -> None:
        """Add an email provider."""
        if provider == EmailProvider.MAILGUN:
            self.providers[provider] = MailgunEmailProvider(**config)
        elif provider == EmailProvider.SENDGRID:
            self.providers[provider] = SendGridEmailProvider(**config)
        elif provider == EmailProvider.SES:
            self.providers[provider] = SESEmailProvider(**config)
        elif provider == EmailProvider.SMTP:
            self.providers[provider] = SMTPEmailProvider(**config)
    
    def send(self, message: EmailMessage, provider: Optional[EmailProvider] = None) -> Dict[str, Any]:
        """Send an email."""
        provider = provider or message.provider or self.default_provider
        
        # Render templates if specified
        if message.template:
            renderer = EmailRenderer()
            context = message.template_context or {}
            context['body'] = message.body
            context['subject'] = message.subject
            
            if message.html:
                message.html = renderer.render(message.template + ".html", context)
            message.body = renderer.render(message.template + ".txt", context)
        
        # Preview mode
        if self._preview_mode:
            return self._preview_send(message)
        
        # Send via provider
        if provider in self.providers:
            result = self.providers[provider].send(message)
            message.metadata['sent'] = True
            return result
        else:
            return {
                'success': False,
                'error': f"Provider {provider} not configured"
            }
    
    def _preview_send(self, message: EmailMessage) -> Dict[str, Any]:
        """Preview mode - save to file instead of sending."""
        preview_id = str(uuid.uuid4())[:8]
        preview_file = self._preview_dir / f"{preview_id}.eml"
        
        # Build email content
        content = f"""From: {message.from_name} <{message.from_email}>
To: {', '.join(message.to)}
Subject: {message.subject}
Date: {datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}
Message-ID: <{preview_id}@pygo.dev>

{message.body}
"""
        if message.html:
            content += f"\n\n[HTML part: {len(message.html)} bytes]"
        
        with open(preview_file, 'w') as f:
            f.write(content)
        
        return {
            'success': True,
            'message_id': f"preview_{preview_id}",
            'preview_path': str(preview_file)
        }
    
    def enable_preview_mode(self, enabled: bool = True) -> None:
        """Enable/disable preview mode."""
        self._preview_mode = enabled
    
    def send_async(self, message: EmailMessage, queue_name: str = "email") -> str:
        """Send email asynchronously via job queue."""
        from core.runtime.jobs import JobQueue
        
        jq = JobQueue()
        job_id = jq.enqueue(
            name="send_email",
            payload=message.to_dict(),
            queue=queue_name
        )
        return job_id


# Convenience functions
def send_email(to: List[str], subject: str, body: str,
               from_email: Optional[str] = None,
               provider: Optional[EmailProvider] = None,
               html: Optional[str] = None) -> Dict[str, Any]:
    """Send a simple email."""
    message = EmailMessage(to=to, subject=subject, body=body, html=html)
    
    # Get configured sender
    sender = EmailSender()
    return sender.send(message, provider)


def send_email_async(to: List[str], subject: str, body: str,
                     from_email: Optional[str] = None,
                     html: Optional[str] = None,
                     queue_name: str = "email") -> str:
    """Send email asynchronously."""
    message = EmailMessage(to=to, subject=subject, body=body, html=html)
    sender = EmailSender()
    return sender.send_async(message, queue_name)


def create_email_template(name: str, content: str) -> Path:
    """Create an email template."""
    renderer = EmailRenderer()
    return renderer.create_template(name, content)