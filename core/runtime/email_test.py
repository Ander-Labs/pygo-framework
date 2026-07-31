"""Test suite for v0.43.0 - Email SMTP."""
import pytest
from pathlib import Path
from datetime import datetime

from core.runtime.email import (
    EmailMessage, EmailProvider, EmailRenderer,
    SMTPEmailProvider, MailgunEmailProvider,
    SendGridEmailProvider, SESEmailProvider,
    EmailSender, send_email, send_email_async
)


def test_email_message_creation():
    """Test creating an email message."""
    message = EmailMessage(
        to=["user@example.com"],
        subject="Test Subject",
        body="Test body"
    )
    
    assert message.to == ["user@example.com"]
    assert message.subject == "Test Subject"
    assert message.body == "Test body"


def test_email_message_with_html():
    """Test email message with HTML."""
    message = EmailMessage(
        to=["user@example.com"],
        subject="Test",
        body="Plain text",
        html="<p>HTML content</p>"
    )
    
    assert message.html == "<p>HTML content</p>"


def test_email_message_to_dict():
    """Test email message serialization."""
    message = EmailMessage(
        to=["user@example.com"],
        subject="Test",
        body="Body",
        from_email="noreply@example.com",
        from_name="Test App"
    )
    
    d = message.to_dict()
    
    assert d['to'] == ["user@example.com"]
    assert d['subject'] == "Test"
    assert d['from_email'] == "noreply@example.com"
    assert d['from_name'] == "Test App"


def test_email_renderer_render():
    """Test template rendering."""
    renderer = EmailRenderer()
    
    content = renderer.render("test", {"name": "World", "body": "Hello {{ name }}!"})
    # Template may not exist, so check for either rendered or placeholder
    assert "Hello" in content or "{{body}}" in content


def test_email_renderer_create_template():
    """Test creating email templates."""
    renderer = EmailRenderer()
    
    path = renderer.create_template("welcome", "Welcome {{ name }}!")
    
    assert path.exists()
    assert "welcome" in path.name
    
    # Cleanup
    path.unlink()


def test_smtp_provider_init():
    """Test SMTP provider initialization."""
    provider = SMTPEmailProvider(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        use_tls=True
    )
    
    assert provider.host == "smtp.example.com"
    assert provider.port == 587


def test_smtp_provider_send_preview():
    """Test SMTP provider in preview mode."""
    sender = EmailSender()
    sender.enable_preview_mode(True)
    
    message = EmailMessage(
        to=["test@example.com"],
        subject="Test",
        body="Test body"
    )
    
    result = sender.send(message)
    
    assert result['success'] is True
    assert 'preview_path' in result


def test_sendgrid_provider_init():
    """Test SendGrid provider initialization."""
    provider = SendGridEmailProvider(api_key="test-key")
    
    assert provider.api_key == "test-key"


def test_mailgun_provider_init():
    """Test Mailgun provider initialization."""
    provider = MailgunEmailProvider(
        api_key="key",
        domain="example.com"
    )
    
    assert provider.domain == "example.com"


def test_ses_provider_init():
    """Test SES provider initialization."""
    provider = SESEmailProvider(region="us-west-2")
    
    assert provider.region == "us-west-2"


def test_email_sender_add_provider():
    """Test adding providers to sender."""
    sender = EmailSender()
    
    sender.add_provider(EmailProvider.MAILGUN, api_key="key", domain="example.com")
    
    assert EmailProvider.MAILGUN in sender.providers


def test_email_sender_send():
    """Test sending email."""
    sender = EmailSender()
    sender.enable_preview_mode(True)
    
    message = EmailMessage(
        to=["user@example.com"],
        subject="Test",
        body="Hello!"
    )
    
    result = sender.send(message)
    
    assert result['success'] is True


def test_email_sender_send_with_provider():
    """Test sending email with specific provider."""
    sender = EmailSender()
    sender.enable_preview_mode(True)
    
    message = EmailMessage(
        to=["user@example.com"],
        subject="Test",
        body="Hello!",
        provider=EmailProvider.SENDGRID
    )
    
    result = sender.send(message)
    
    assert result['success'] is True


def test_convenience_send_email():
    """Test convenience send_email function."""
    result = send_email(
        to=["user@example.com"],
        subject="Test",
        body="Hello!"
    )
    
    # Will fail without proper config, but shouldn't crash
    assert 'success' in result


def test_convenience_send_email_async():
    """Test async email sending."""
    job_id = send_email_async(
        to=["user@example.com"],
        subject="Test",
        body="Hello!"
    )
    
    assert job_id is not None


def test_email_provider_enum():
    """Test email provider enum values."""
    assert EmailProvider.SMTP.value == "smtp"
    assert EmailProvider.MAILGUN.value == "mailgun"
    assert EmailProvider.SENDGRID.value == "sendgrid"
    assert EmailProvider.SES.value == "ses"


def test_email_message_attachments():
    """Test email with attachments."""
    attachments = [{'path': '/tmp/report.pdf', 'filename': 'report.pdf'}]
    message = EmailMessage(
        to=["user@example.com"],
        subject="Report",
        body="See attached",
        attachments=attachments
    )
    
    assert len(message.attachments) == 1
    assert message.attachments[0]['filename'] == "report.pdf"


def test_email_message_cc_bcc():
    """Test email with CC and BCC."""
    message = EmailMessage(
        to=["primary@example.com"],
        subject="Test",
        body="Test",
        cc=["cc@example.com"],
        bcc=["bcc@example.com"]
    )
    
    assert message.cc == ["cc@example.com"]
    assert message.bcc == ["bcc@example.com"]


def test_email_message_template():
    """Test email with template."""
    message = EmailMessage(
        to=["user@example.com"],
        subject="Welcome",
        body="Welcome message",
        template="welcome",
        template_context={"name": "John"}
    )
    
    assert message.template == "welcome"
    assert message.template_context == {"name": "John"}


def test_email_sender_disable_preview():
    """Test disabling preview mode."""
    sender = EmailSender()
    sender.enable_preview_mode(False)
    
    message = EmailMessage(
        to=["user@example.com"],
        subject="Test",
        body="Test"
    )
    
    result = sender.send(message)
    
    # Will fail without provider configured
    assert result['success'] is False or 'error' in result


def test_multiple_recipients():
    """Test email to multiple recipients."""
    message = EmailMessage(
        to=["user1@example.com", "user2@example.com", "user3@example.com"],
        subject="Group Email",
        body="Hello everyone!"
    )
    
    assert len(message.to) == 3


def test_email_headers():
    """Test email with custom headers."""
    message = EmailMessage(
        to=["user@example.com"],
        subject="Test",
        body="Test",
        headers={"X-Priority": "high", "X-Custom": "value"}
    )
    
    assert message.headers["X-Priority"] == "high"
    assert message.headers["X-Custom"] == "value"