"""
app/services/email_service.py
=============================
Wrapper for the Resend email service and Jinja2 templating.
"""

import os
import logging
import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Resend
resend.api_key = settings.RESEND_API_KEY

# Initialize Jinja2 environment
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "email")
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)


def render_template(template_name: str, context: dict) -> str:
    """
    Renders an HTML email template with the given context.
    """
    template = jinja_env.get_template(template_name)
    return template.render(**context)


def send_email(to: str, subject: str, template_name: str, context: dict) -> bool:
    """
    Sends an email using Resend and Jinja2 templates.
    Fails gracefully if the email cannot be sent.

    Args:
        to: Recipient email address
        subject: Email subject line
        template_name: HTML template file name in app/templates/email/
        context: Dictionary of variables for the Jinja2 template

    Returns:
        True if successful, False if failed.
    """
    # In development mode, if no API key is provided, log and return True
    if not settings.RESEND_API_KEY or settings.RESEND_API_KEY.startswith("re_placeholder_"):
        logger.warning(
            f"[EMAIL_SERVICE] Missing valid RESEND_API_KEY. Simulating email to {to}.\n"
            f"Subject: {subject}\n"
            f"Context: {context}"
        )
        return True

    try:
        html_content = render_template(template_name, context)

        params: resend.Emails.SendParams = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html_content,
        }

        response = resend.Emails.send(params)
        logger.info(f"[EMAIL_SERVICE] Successfully sent email to {to}. ID: {response.get('id')}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL_SERVICE] Failed to send email to {to}: {str(e)}")
        # Don't crash the application if email fails
        return False
