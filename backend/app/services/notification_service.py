"""
Notification service for email and SMS.

This module provides email sending via SMTP and SMS via Twilio,
with mock implementations when external services are not configured.
"""
import logging
from typing import Optional, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from flask import Flask
from twilio.rest import Client
from ..config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via email and SMS."""

    def __init__(self):
        self.smtp_configured = bool(settings.smtp_user and settings.smtp_pass)
        self.twilio_configured = bool(settings.twilio_sid and settings.twilio_auth_token)

        if not self.twilio_configured:
            logger.info("Twilio not configured, using mock SMS service")

        if not self.smtp_configured:
            logger.info("SMTP not configured, using mock email service")

    def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send email notification."""
        if not self.smtp_configured:
            return self._mock_send_email(to_email, subject, body)

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = settings.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject

            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def _mock_send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Mock email service for testing."""
        logger.info(f"[MOCK EMAIL] To: {to_email}")
        logger.info(f"[MOCK EMAIL] Subject: {subject}")
        logger.info(f"[MOCK EMAIL] Body: {body}")
        return True

    def send_sms(self, to_phone: str, message: str) -> bool:
        """Send SMS notification."""
        if not self.twilio_configured:
            return self._mock_send_sms(to_phone, message)

        try:
            client = Client(settings.twilio_sid, settings.twilio_auth_token)
            message = client.messages.create(
                body=message,
                from_=settings.twilio_from,
                to=to_phone
            )
            logger.info(f"SMS sent to {to_phone}, SID: {message.sid}")
            return True

        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False

    def _mock_send_sms(self, to_phone: str, message: str) -> bool:
        """Mock SMS service for testing."""
        logger.info(f"[MOCK SMS] To: {to_phone}")
        logger.info(f"[MOCK SMS] Message: {message}")
        return True

    def send_donation_receipt(self, donation_data: Dict) -> bool:
        """Send donation receipt email."""
        subject = "Donation Receipt - Blessings Distribution System"
        body = f"""
Thank you for your generous donation!

Donation Details:
- Donor: {donation_data['donor_name']}
- Amount: {donation_data['amount']} {donation_data.get('currency', 'PKR')}
- Type: {donation_data['donation_type']}
- Transaction ID: {donation_data.get('id', 'N/A')}
- Date: {donation_data.get('created_at', 'N/A')}

Your support helps us provide essential aid to those in need.
For transparency, your transaction hash is: {donation_data.get('transaction_hash', 'N/A')}

Best regards,
Blessings Distribution System
"""

        return self.send_email(donation_data['donor_email'], subject, body)

    def send_pickup_notification(self, employee_data: Dict, pickup_slot: str) -> bool:
        """Send pickup notification to employee."""
        subject = "Ration Pickup Notification"
        body = f"""
Dear {employee_data['name']},

Your ration distribution has been scheduled.

Pickup Details:
- Date & Time: {pickup_slot}
- Location: Main Distribution Center
- Amount: {employee_data.get('amount', 'N/A')} PKR

Please bring your CNIC and arrive on time.
If you cannot make it, please contact us in advance.

Best regards,
Blessings Distribution System
"""

        # Send email if available
        email_sent = False
        if employee_data.get('user') and employee_data['user'].email:
            email_sent = self.send_email(employee_data['user'].email, subject, body)

        # Send SMS to mobile
        sms_sent = self.send_sms(employee_data['mobile'], f"Pickup scheduled: {pickup_slot}. Amount: {employee_data.get('amount', 'N/A')} PKR")

        return email_sent or sms_sent


# Global service instance
notification_service = NotificationService()