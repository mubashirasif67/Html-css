"""
SMS notification service for the Blessings Donation System.

This module provides SMS functionality using Twilio API with fallback
to mock service when Twilio is not configured.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)

# Try to import Twilio, but handle gracefully if not available
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    logger.warning("Twilio not installed, using mock SMS service")
    TWILIO_AVAILABLE = False
    TwilioClient = None
    TwilioException = Exception


class SMSService:
    """SMS service for sending notifications via Twilio or mock service."""
    
    def __init__(self):
        self.twilio_sid = settings.twilio_sid
        self.twilio_auth_token = settings.twilio_auth_token
        self.twilio_from = settings.twilio_from
        
        # Initialize Twilio client if configured
        self.twilio_client = None
        self.use_mock = True
        
        if TWILIO_AVAILABLE and self.is_configured():
            try:
                self.twilio_client = TwilioClient(self.twilio_sid, self.twilio_auth_token)
                self.use_mock = False
                logger.info("Twilio SMS service initialized")
            except Exception as e:
                logger.error("Failed to initialize Twilio client", error=str(e))
                self.use_mock = True
        else:
            logger.info("Using mock SMS service")
    
    def is_configured(self) -> bool:
        """Check if Twilio SMS service is properly configured."""
        return bool(
            TWILIO_AVAILABLE and
            self.twilio_sid and
            self.twilio_auth_token and
            self.twilio_from
        )
    
    def test_connection(self) -> bool:
        """Test SMS service connection."""
        if self.use_mock:
            logger.info("Mock SMS service connection test - always successful")
            return True
        
        try:
            # Try to get account info to test connection
            account = self.twilio_client.api.accounts(self.twilio_sid).fetch()
            logger.info("Twilio connection test successful", account_status=account.status)
            return True
        except Exception as e:
            logger.error("Twilio connection test failed", error=str(e))
            return False
    
    def send_sms(
        self,
        to_phone: str,
        message: str,
        from_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS message.
        
        Args:
            to_phone: Recipient phone number
            message: SMS message content
            from_phone: Sender phone number (optional, uses default)
            
        Returns:
            Dictionary with send result
        """
        if self.use_mock:
            return self._send_mock_sms(to_phone, message)
        
        try:
            from_number = from_phone or self.twilio_from
            
            # Send SMS via Twilio
            twilio_message = self.twilio_client.messages.create(
                body=message,
                from_=from_number,
                to=to_phone
            )
            
            logger.info(
                "SMS sent successfully via Twilio",
                to_phone=to_phone,
                message_sid=twilio_message.sid,
                status=twilio_message.status
            )
            
            return {
                'success': True,
                'message': 'SMS sent successfully',
                'to_phone': to_phone,
                'message_sid': twilio_message.sid,
                'status': twilio_message.status,
                'sent_at': datetime.utcnow().isoformat(),
                'service': 'twilio'
            }
            
        except TwilioException as e:
            logger.error("Twilio SMS sending failed", error=str(e), to_phone=to_phone)
            return {
                'success': False,
                'error': str(e),
                'to_phone': to_phone,
                'service': 'twilio'
            }
        except Exception as e:
            logger.error("SMS sending failed", error=str(e), to_phone=to_phone)
            return {
                'success': False,
                'error': str(e),
                'to_phone': to_phone,
                'service': 'twilio'
            }
    
    def _send_mock_sms(self, to_phone: str, message: str) -> Dict[str, Any]:
        """
        Send mock SMS (for development/testing).
        
        Args:
            to_phone: Recipient phone number
            message: SMS message content
            
        Returns:
            Dictionary with mock send result
        """
        try:
            # Log the SMS for debugging
            logger.info(
                "Mock SMS sent",
                to_phone=to_phone,
                message=message[:100] + "..." if len(message) > 100 else message
            )
            
            # Store in mock SMS log (you could write to file or database)
            mock_message_id = f"mock_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(to_phone) % 10000}"
            
            return {
                'success': True,
                'message': 'Mock SMS sent successfully',
                'to_phone': to_phone,
                'message_sid': mock_message_id,
                'status': 'delivered',
                'sent_at': datetime.utcnow().isoformat(),
                'service': 'mock'
            }
            
        except Exception as e:
            logger.error("Mock SMS sending failed", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'to_phone': to_phone,
                'service': 'mock'
            }
    
    def send_pickup_notification_sms(
        self,
        to_phone: str,
        employee_name: str,
        pickup_date: str,
        pickup_time: str,
        location: str
    ) -> Dict[str, Any]:
        """
        Send pickup notification SMS.
        
        Args:
            to_phone: Employee phone number
            employee_name: Employee name
            pickup_date: Date of pickup
            pickup_time: Time slot for pickup
            location: Pickup location
            
        Returns:
            Dictionary with send result
        """
        message = f"""
Dear {employee_name},

Your ration package is ready for collection:

Date: {pickup_date}
Time: {pickup_time}
Location: {location}

Please bring your employee ID.

Blessings Donation System
""".strip()
        
        return self.send_sms(to_phone, message)
    
    def send_donation_confirmation_sms(
        self,
        to_phone: str,
        donor_name: str,
        amount: float,
        receipt_number: str
    ) -> Dict[str, Any]:
        """
        Send donation confirmation SMS.
        
        Args:
            to_phone: Donor phone number
            donor_name: Donor name
            amount: Donation amount
            receipt_number: Receipt number
            
        Returns:
            Dictionary with send result
        """
        message = f"""
Dear {donor_name},

Thank you for your donation of PKR {amount:,.2f}.

Receipt: {receipt_number}

May Allah reward your generosity.

Blessings Donation System
""".strip()
        
        return self.send_sms(to_phone, message)
    
    def send_admin_alert(
        self,
        to_phone: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send critical alert SMS to administrator.
        
        Args:
            to_phone: Admin phone number
            message: Alert message
            
        Returns:
            Dictionary with send result
        """
        alert_message = f"""
ALERT - Blessings System

{message}

Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Please check the system immediately.
""".strip()
        
        return self.send_sms(to_phone, alert_message)
    
    def send_verification_code(
        self,
        to_phone: str,
        verification_code: str
    ) -> Dict[str, Any]:
        """
        Send SMS verification code.
        
        Args:
            to_phone: Phone number to verify
            verification_code: Verification code
            
        Returns:
            Dictionary with send result
        """
        message = f"""
Your verification code for Blessings Donation System is: {verification_code}

This code will expire in 10 minutes.

Do not share this code with anyone.
""".strip()
        
        return self.send_sms(to_phone, message)
    
    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get status of a sent message.
        
        Args:
            message_sid: Message SID from Twilio
            
        Returns:
            Dictionary with message status
        """
        if self.use_mock:
            return {
                'message_sid': message_sid,
                'status': 'delivered',
                'error_code': None,
                'error_message': None,
                'service': 'mock'
            }
        
        try:
            message = self.twilio_client.messages(message_sid).fetch()
            
            return {
                'message_sid': message_sid,
                'status': message.status,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'date_sent': message.date_sent.isoformat() if message.date_sent else None,
                'date_updated': message.date_updated.isoformat() if message.date_updated else None,
                'service': 'twilio'
            }
            
        except TwilioException as e:
            logger.error("Failed to get message status", message_sid=message_sid, error=str(e))
            return {
                'message_sid': message_sid,
                'status': 'unknown',
                'error': str(e),
                'service': 'twilio'
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the SMS service configuration.
        
        Returns:
            Dictionary with service information
        """
        return {
            'service_type': 'mock' if self.use_mock else 'twilio',
            'configured': self.is_configured(),
            'twilio_available': TWILIO_AVAILABLE,
            'from_number': self.twilio_from if not self.use_mock else 'mock_number',
            'connection_test': self.test_connection()
        }


# Mock SMS storage for development
class MockSMSStorage:
    """Simple in-memory storage for mock SMS messages."""
    
    def __init__(self):
        self.messages = []
    
    def add_message(self, to_phone: str, message: str, status: str = 'delivered'):
        """Add a mock SMS message to storage."""
        message_data = {
            'id': len(self.messages) + 1,
            'to_phone': to_phone,
            'message': message,
            'status': status,
            'sent_at': datetime.utcnow().isoformat()
        }
        self.messages.append(message_data)
        return message_data
    
    def get_messages(self, limit: int = 50) -> list:
        """Get recent mock SMS messages."""
        return self.messages[-limit:]
    
    def clear_messages(self):
        """Clear all mock SMS messages."""
        self.messages.clear()


# Global mock SMS storage instance
mock_sms_storage = MockSMSStorage()