"""
Notification and communication models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class NotificationType(str, enum.Enum):
    """Notification type enumeration"""
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"


class NotificationStatus(str, enum.Enum):
    """Notification status enumeration"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class NotificationCategory(str, enum.Enum):
    """Notification category enumeration"""
    DONATION_RECEIPT = "donation_receipt"
    PICKUP_SCHEDULE = "pickup_schedule"
    DISTRIBUTION_ALERT = "distribution_alert"
    ACCOUNT = "account"
    SYSTEM = "system"


class Notification(Base):
    """
    Notification model for tracking all communications
    
    Attributes:
        id: Primary key
        user_id: Recipient user ID
        type: Type of notification (email, sms, etc.)
        category: Category of notification
        status: Current status
        subject: Subject line (for emails)
        content: Message content
        metadata: Additional data (JSON)
    """
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Recipient
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    recipient_email = Column(String(255))
    recipient_phone = Column(String(20))
    recipient_name = Column(String(255))
    
    # Notification details
    type = Column(Enum(NotificationType), nullable=False, index=True)
    category = Column(Enum(NotificationCategory), nullable=False, index=True)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)
    
    # Content
    subject = Column(String(500))
    content = Column(Text, nullable=False)
    template_id = Column(String(50))  # Template identifier
    
    # Metadata
    metadata = Column(Text)  # JSON data
    priority = Column(Integer, default=5)  # 1-10, 1 being highest
    
    # Tracking
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # External tracking
    external_id = Column(String(255))  # Twilio message SID, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    scheduled_for = Column(DateTime(timezone=True))  # For scheduled notifications
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    logs = relationship("NotificationLog", back_populates="notification", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, status={self.status})>"
    
    def to_dict(self):
        """Convert notification to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value if self.type else None,
            "category": self.category.value if self.category else None,
            "status": self.status.value if self.status else None,
            "subject": self.subject,
            "recipient_email": self.recipient_email,
            "recipient_phone": self.recipient_phone,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NotificationLog(Base):
    """
    Detailed log of notification attempts
    """
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)
    
    # Log details
    action = Column(String(50))  # "send_attempt", "delivered", "failed", etc.
    status_code = Column(Integer)  # HTTP status code or similar
    response = Column(Text)  # Full response from service
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    notification = relationship("Notification", back_populates="logs")
    
    def __repr__(self):
        return f"<NotificationLog(id={self.id}, notification={self.notification_id}, action={self.action})>"