"""
User model for authentication and authorization
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    STAFF = "staff"
    DONOR = "donor"
    BENEFICIARY = "beneficiary"


class User(Base):
    """
    User model for authentication
    
    Attributes:
        id: Primary key
        email: Unique email address
        name: Full name
        password_hash: Bcrypt hashed password
        role: User role (admin, staff, donor, beneficiary)
        is_active: Whether the user account is active
        created_at: Timestamp of user creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.DONOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Additional fields
    phone = Column(String(20))
    cnic = Column(String(20), index=True)  # Encrypted/hashed in production
    address = Column(String(500))
    
    # Relationships
    donations = relationship("Donation", back_populates="donor", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def to_dict(self, include_sensitive=False):
        """
        Convert user object to dictionary
        
        Args:
            include_sensitive: Whether to include sensitive information
        
        Returns:
            Dictionary representation of user
        """
        data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value if self.role else None,
            "is_active": self.is_active,
            "phone": self.phone,
            "address": self.address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data["cnic"] = self.cnic
        else:
            # Mask CNIC for privacy
            if self.cnic:
                data["cnic"] = f"*****-*******-{self.cnic[-4:]}" if len(self.cnic) >= 4 else "****"
        
        return data