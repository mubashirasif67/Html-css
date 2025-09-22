"""
Email notification service for the Blessings Donation System.

This module provides email functionality including SMTP configuration,
template rendering, and various notification types.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import structlog
from jinja2 import Environment, FileSystemLoader, Template

from ..config import settings

logger = structlog.get_logger(__name__)


class EmailService:
    """Email service for sending various types of notifications."""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_pass = settings.smtp_pass
        self.email_from = settings.email_from or f"Blessings Donation System <{settings.smtp_user}>"
        
        # Set up Jinja2 environment for templates
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        if os.path.exists(template_dir):
            self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.jinja_env = None
            logger.warning("Email template directory not found", path=template_dir)
    
    def test_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
            logger.info("SMTP connection test successful")
            return True
        except Exception as e:
            logger.error("SMTP connection test failed", error=str(e))
            return False
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            attachments: List of attachment dictionaries (optional)
            
        Returns:
            Dictionary with send result
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text part
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.info("Email sent successfully", to_email=to_email, subject=subject)
            
            return {
                'success': True,
                'message': 'Email sent successfully',
                'to_email': to_email,
                'subject': subject,
                'sent_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to send email", error=str(e), to_email=to_email)
            return {
                'success': False,
                'error': str(e),
                'to_email': to_email,
                'subject': subject
            }
    
    def send_donation_receipt(
        self,
        to_email: str,
        donor_name: str,
        amount: float,
        currency: str,
        donation_type: str,
        receipt_number: str,
        donation_date: datetime
    ) -> Dict[str, Any]:
        """
        Send donation receipt email.
        
        Args:
            to_email: Donor email address
            donor_name: Donor name
            amount: Donation amount
            currency: Currency code
            donation_type: Type of donation
            receipt_number: Receipt number
            donation_date: Date of donation
            
        Returns:
            Dictionary with send result
        """
        try:
            # Prepare template context
            context = {
                'donor_name': donor_name,
                'amount': f"{amount:,.2f}",
                'currency': currency,
                'donation_type': donation_type.title(),
                'receipt_number': receipt_number,
                'donation_date': donation_date.strftime('%B %d, %Y'),
                'year': datetime.now().year
            }
            
            # Render template
            html_body = self._render_template('donation_receipt.html', context)
            text_body = self._render_text_receipt(context)
            
            subject = f"Donation Receipt - {receipt_number}"
            
            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error("Failed to send donation receipt", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'to_email': to_email
            }
    
    def send_pickup_notification(
        self,
        to_email: str,
        employee_name: str,
        pickup_date: datetime,
        pickup_time: str,
        location: str,
        items: List[str]
    ) -> Dict[str, Any]:
        """
        Send pickup notification email.
        
        Args:
            to_email: Employee email address
            employee_name: Employee name
            pickup_date: Date of pickup
            pickup_time: Time slot for pickup
            location: Pickup location
            items: List of items to collect
            
        Returns:
            Dictionary with send result
        """
        try:
            context = {
                'employee_name': employee_name,
                'pickup_date': pickup_date.strftime('%B %d, %Y'),
                'pickup_time': pickup_time,
                'location': location,
                'items': items,
                'year': datetime.now().year
            }
            
            html_body = self._render_template('pickup_notification.html', context)
            text_body = self._render_text_pickup(context)
            
            subject = f"Ration Collection Schedule - {pickup_date.strftime('%B %d, %Y')}"
            
            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error("Failed to send pickup notification", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'to_email': to_email
            }
    
    def send_weekly_report(
        self,
        to_email: str,
        admin_name: str,
        stats: Dict[str, Any],
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Send weekly summary report to administrators.
        
        Args:
            to_email: Admin email address
            admin_name: Admin name
            stats: Statistics dictionary
            period_start: Report period start date
            period_end: Report period end date
            
        Returns:
            Dictionary with send result
        """
        try:
            context = {
                'admin_name': admin_name,
                'period_start': period_start.strftime('%B %d, %Y'),
                'period_end': period_end.strftime('%B %d, %Y'),
                'total_donations': stats.get('total_donations', 0),
                'total_amount': f"{stats.get('total_amount', 0):,.2f}",
                'average_amount': f"{stats.get('average_amount', 0):,.2f}",
                'by_type': stats.get('by_type', {}),
                'by_status': stats.get('by_status', {}),
                'ocr_stats': stats.get('ocr_stats', {}),
                'fraud_stats': stats.get('fraud_stats', {}),
                'year': datetime.now().year
            }
            
            html_body = self._render_template('weekly_report.html', context)
            text_body = self._render_text_report(context)
            
            subject = f"Weekly Report - {period_start.strftime('%B %d')} to {period_end.strftime('%B %d, %Y')}"
            
            return self.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error("Failed to send weekly report", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'to_email': to_email
            }
    
    def send_admin_alert(
        self,
        to_email: str,
        admin_name: str,
        subject: str,
        message: str,
        level: str = 'info'
    ) -> Dict[str, Any]:
        """
        Send alert notification to administrator.
        
        Args:
            to_email: Admin email address
            admin_name: Admin name
            subject: Alert subject
            message: Alert message
            level: Alert level (info, warning, error, critical)
            
        Returns:
            Dictionary with send result
        """
        try:
            context = {
                'admin_name': admin_name,
                'alert_subject': subject,
                'alert_message': message,
                'alert_level': level,
                'alert_time': datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC'),
                'year': datetime.now().year
            }
            
            html_body = self._render_template('admin_alert.html', context)
            text_body = f"""
Alert Notification

Dear {admin_name},

Alert Level: {level.upper()}
Subject: {subject}
Message: {message}
Time: {context['alert_time']}

Please take appropriate action if required.

Best regards,
Blessings Donation System
"""
            
            email_subject = f"[{level.upper()}] {subject}"
            
            return self.send_email(
                to_email=to_email,
                subject=email_subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error("Failed to send admin alert", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'to_email': to_email
            }
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render HTML template.
        
        Args:
            template_name: Template file name
            context: Template context variables
            
        Returns:
            Rendered HTML string
        """
        try:
            if self.jinja_env:
                template = self.jinja_env.get_template(template_name)
                return template.render(**context)
            else:
                # Fallback to basic HTML template
                return self._get_basic_html_template(template_name, context)
        except Exception as e:
            logger.error("Template rendering failed", template=template_name, error=str(e))
            return self._get_basic_html_template(template_name, context)
    
    def _get_basic_html_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Get basic HTML template when Jinja2 templates are not available."""
        if template_name == 'donation_receipt.html':
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Donation Receipt</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .receipt-details {{ background-color: #e9ecef; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Blessings Donation System</h1>
        <h2>Donation Receipt</h2>
    </div>
    <div class="content">
        <p>Dear {context.get('donor_name', 'Donor')},</p>
        <p>Thank you for your generous donation. This email serves as your official receipt.</p>
        
        <div class="receipt-details">
            <h3>Donation Details</h3>
            <p><strong>Receipt Number:</strong> {context.get('receipt_number', 'N/A')}</p>
            <p><strong>Amount:</strong> {context.get('currency', 'PKR')} {context.get('amount', '0.00')}</p>
            <p><strong>Type:</strong> {context.get('donation_type', 'General')}</p>
            <p><strong>Date:</strong> {context.get('donation_date', 'N/A')}</p>
        </div>
        
        <p>Your donation will help us serve those in need. May Allah reward you for your generosity.</p>
    </div>
    <div class="footer">
        <p>© {context.get('year', datetime.now().year)} Blessings Donation System</p>
    </div>
</body>
</html>
"""
        elif template_name == 'pickup_notification.html':
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Pickup Notification</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .pickup-details {{ background-color: #e9ecef; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Blessings Donation System</h1>
        <h2>Ration Collection Schedule</h2>
    </div>
    <div class="content">
        <p>Dear {context.get('employee_name', 'Employee')},</p>
        <p>Your ration package is ready for collection. Please find the details below:</p>
        
        <div class="pickup-details">
            <h3>Collection Details</h3>
            <p><strong>Date:</strong> {context.get('pickup_date', 'N/A')}</p>
            <p><strong>Time:</strong> {context.get('pickup_time', 'N/A')}</p>
            <p><strong>Location:</strong> {context.get('location', 'N/A')}</p>
            <p><strong>Items:</strong> {', '.join(context.get('items', []))}</p>
        </div>
        
        <p>Please bring your employee ID for verification. Thank you.</p>
    </div>
    <div class="footer">
        <p>© {context.get('year', datetime.now().year)} Blessings Donation System</p>
    </div>
</body>
</html>
"""
        else:
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Notification</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .content {{ padding: 20px; }}
    </style>
</head>
<body>
    <div class="content">
        <h2>Blessings Donation System</h2>
        <p>This is a notification from the Blessings Donation System.</p>
        <p>Template: {template_name}</p>
    </div>
</body>
</html>
"""
    
    def _render_text_receipt(self, context: Dict[str, Any]) -> str:
        """Render plain text donation receipt."""
        return f"""
BLESSINGS DONATION SYSTEM
Donation Receipt

Dear {context.get('donor_name', 'Donor')},

Thank you for your generous donation. This email serves as your official receipt.

DONATION DETAILS:
Receipt Number: {context.get('receipt_number', 'N/A')}
Amount: {context.get('currency', 'PKR')} {context.get('amount', '0.00')}
Type: {context.get('donation_type', 'General')}
Date: {context.get('donation_date', 'N/A')}

Your donation will help us serve those in need. May Allah reward you for your generosity.

Best regards,
Blessings Donation System
© {context.get('year', datetime.now().year)}
"""
    
    def _render_text_pickup(self, context: Dict[str, Any]) -> str:
        """Render plain text pickup notification."""
        return f"""
BLESSINGS DONATION SYSTEM
Ration Collection Schedule

Dear {context.get('employee_name', 'Employee')},

Your ration package is ready for collection. Please find the details below:

COLLECTION DETAILS:
Date: {context.get('pickup_date', 'N/A')}
Time: {context.get('pickup_time', 'N/A')}
Location: {context.get('location', 'N/A')}
Items: {', '.join(context.get('items', []))}

Please bring your employee ID for verification. Thank you.

Best regards,
Blessings Donation System
© {context.get('year', datetime.now().year)}
"""
    
    def _render_text_report(self, context: Dict[str, Any]) -> str:
        """Render plain text weekly report."""
        return f"""
BLESSINGS DONATION SYSTEM
Weekly Report

Dear {context.get('admin_name', 'Administrator')},

Report Period: {context.get('period_start', 'N/A')} to {context.get('period_end', 'N/A')}

SUMMARY:
Total Donations: {context.get('total_donations', 0)}
Total Amount: PKR {context.get('total_amount', '0.00')}
Average Amount: PKR {context.get('average_amount', '0.00')}

This report contains detailed statistics about donation activities during the specified period.

Best regards,
Blessings Donation System
© {context.get('year', datetime.now().year)}
"""
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message."""
        try:
            filename = attachment['filename']
            content = attachment['content']
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(part)
            
        except Exception as e:
            logger.error("Failed to add email attachment", error=str(e))
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(
            self.smtp_host and
            self.smtp_port and
            self.smtp_user and
            self.smtp_pass
        )