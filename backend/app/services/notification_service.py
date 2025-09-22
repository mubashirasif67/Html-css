"""
Notification Service for email and SMS
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import logging
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via email and SMS"""
    
    def __init__(self):
        """Initialize notification service"""
        self.email_enabled = settings.EMAIL_ENABLED
        self.sms_enabled = settings.TWILIO_ENABLED
        
        # Initialize Twilio client if enabled
        if self.sms_enabled:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(
                    settings.TWILIO_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("Twilio client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio: {e}")
                self.sms_enabled = False
                self.twilio_client = None
        else:
            self.twilio_client = None
    
    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        """
        Send email notification
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            html: Whether body is HTML
        
        Returns:
            True if sent successfully
        """
        if not self.email_enabled:
            logger.info(f"[MOCK EMAIL] To: {to}, Subject: {subject}")
            logger.info(f"[MOCK EMAIL] Body: {body[:200]}...")
            return True
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = settings.SMTP_FROM
            msg['To'] = to
            msg['Subject'] = subject
            
            # Add body
            part = MIMEText(body, 'html' if html else 'plain')
            msg.attach(part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASS:
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False
    
    def send_sms(self, to: str, message: str) -> bool:
        """
        Send SMS notification
        
        Args:
            to: Recipient phone number
            message: SMS message
        
        Returns:
            True if sent successfully
        """
        if not self.sms_enabled or not self.twilio_client:
            logger.info(f"[MOCK SMS] To: {to}")
            logger.info(f"[MOCK SMS] Message: {message}")
            return True
        
        try:
            # Send SMS via Twilio
            message = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_FROM,
                to=to
            )
            
            logger.info(f"SMS sent to {to}: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {e}")
            return False
    
    def send_whatsapp(self, to: str, message: str) -> bool:
        """
        Send WhatsApp message
        
        Args:
            to: Recipient phone number
            message: Message text
        
        Returns:
            True if sent successfully
        """
        if not self.sms_enabled or not self.twilio_client:
            logger.info(f"[MOCK WHATSAPP] To: {to}")
            logger.info(f"[MOCK WHATSAPP] Message: {message}")
            return True
        
        try:
            # Format number for WhatsApp
            whatsapp_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
            
            message = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_WHATSAPP_FROM,
                to=whatsapp_to
            )
            
            logger.info(f"WhatsApp sent to {to}: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp to {to}: {e}")
            return False
    
    def send_donation_receipt_email(
        self, 
        to: str, 
        donor_name: str, 
        amount: float, 
        transaction_id: str
    ) -> bool:
        """
        Send donation receipt via email
        
        Args:
            to: Recipient email
            donor_name: Name of donor
            amount: Donation amount
            transaction_id: Transaction ID
        
        Returns:
            Success status
        """
        subject = "Thank You for Your Donation - Blessings Foundation"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Thank You for Your Generosity!</h2>
                
                <p>Dear {donor_name},</p>
                
                <p>We have received your donation of <strong>PKR {amount:,.2f}</strong>.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Receipt Details:</h3>
                    <p><strong>Transaction ID:</strong> {transaction_id}</p>
                    <p><strong>Amount:</strong> PKR {amount:,.2f}</p>
                    <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                </div>
                
                <p>Your contribution will help us provide essential support to families in need. 
                We are committed to transparency and will ensure your donation reaches those who need it most.</p>
                
                <p>If you have any questions, please don't hesitate to contact us.</p>
                
                <p>With gratitude,<br>
                <strong>Blessings Foundation Team</strong></p>
                
                <hr style="margin-top: 30px;">
                <p style="font-size: 12px; color: #666;">
                    This is an automated receipt. Please keep it for your records.
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to, subject, body, html=True)
    
    def send_donation_receipt_sms(
        self, 
        to: str, 
        amount: float, 
        transaction_id: str
    ) -> bool:
        """
        Send donation receipt via SMS
        
        Args:
            to: Recipient phone number
            amount: Donation amount
            transaction_id: Transaction ID
        
        Returns:
            Success status
        """
        message = (
            f"Blessings Foundation: Thank you for your donation of PKR {amount:,.0f}. "
            f"Transaction ID: {transaction_id}. "
            f"Your generosity makes a difference!"
        )
        
        return self.send_sms(to, message)
    
    def send_pickup_notification(
        self,
        to: str,
        beneficiary_name: str,
        pickup_date: datetime,
        pickup_time: datetime,
        location: str
    ) -> bool:
        """
        Send pickup schedule notification
        
        Args:
            to: Recipient phone number
            beneficiary_name: Name of beneficiary
            pickup_date: Date of pickup
            pickup_time: Time of pickup
            location: Pickup location
        
        Returns:
            Success status
        """
        message = (
            f"Dear {beneficiary_name}, your ration pickup is scheduled for "
            f"{pickup_date.strftime('%B %d')} at {pickup_time.strftime('%I:%M %p')}. "
            f"Location: {location}. Please bring your CNIC for verification."
        )
        
        return self.send_sms(to, message)
    
    def send_bulk_notifications(
        self,
        recipients: List[dict],
        template: str,
        channel: str = "sms"
    ) -> dict:
        """
        Send bulk notifications
        
        Args:
            recipients: List of recipient dictionaries
            template: Message template
            channel: Notification channel (sms, email, whatsapp)
        
        Returns:
            Summary of sent notifications
        """
        sent = 0
        failed = 0
        
        for recipient in recipients:
            try:
                message = template.format(**recipient)
                
                if channel == "email":
                    success = self.send_email(
                        recipient.get("email"),
                        recipient.get("subject", "Notification"),
                        message
                    )
                elif channel == "whatsapp":
                    success = self.send_whatsapp(
                        recipient.get("phone"),
                        message
                    )
                else:  # SMS
                    success = self.send_sms(
                        recipient.get("phone"),
                        message
                    )
                
                if success:
                    sent += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error sending to {recipient}: {e}")
                failed += 1
        
        return {
            "sent": sent,
            "failed": failed,
            "total": len(recipients)
        }