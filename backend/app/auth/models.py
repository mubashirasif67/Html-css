"""
Authentication models for the Blessings Donation System.

This module defines the User model and related authentication entities.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from typing import Optional

from ..database import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    STAFF = "staff"
    VOLUNTEER = "volunteer"
    VIEWER = "viewer"


class UserStatus(str, enum.Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(Base):
    """
    User model for authentication and authorization.
    
    This model stores user credentials, profile information,
    and access control data.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Profile fields
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Authorization fields
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Security fields
    is_verified = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(Integer, nullable=True)  # User ID who created this user
    
    # Additional profile fields
    department = Column(String(100), nullable=True)
    employee_id = Column(String(50), unique=True, nullable=True)
    notes = Column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_staff(self) -> bool:
        """Check if user has staff role or higher."""
        return self.role in [UserRole.ADMIN, UserRole.STAFF]
    
    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE
    
    @property
    def can_login(self) -> bool:
        """Check if user can login."""
        return (
            self.status == UserStatus.ACTIVE and
            self.is_verified and
            self.failed_login_attempts < 5
        )
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            permission: Permission string to check
            
        Returns:
            bool: True if user has permission
        """
        role_permissions = {
            UserRole.ADMIN: [
                "users:create", "users:read", "users:update", "users:delete",
                "employees:create", "employees:read", "employees:update", "employees:delete",
                "donations:create", "donations:read", "donations:update", "donations:delete",
                "distributions:create", "distributions:read", "distributions:update", "distributions:approve",
                "reports:read", "reports:export",
                "system:configure", "system:backup"
            ],
            UserRole.STAFF: [
                "employees:create", "employees:read", "employees:update",
                "donations:create", "donations:read", "donations:update",
                "distributions:create", "distributions:read", "distributions:update",
                "reports:read"
            ],
            UserRole.VOLUNTEER: [
                "employees:read",
                "donations:create", "donations:read",
                "distributions:read"
            ],
            UserRole.VIEWER: [
                "employees:read",
                "donations:read",
                "distributions:read"
            ]
        }
        
        user_permissions = role_permissions.get(self.role, [])
        return permission in user_permissions


class LoginAttempt(Base):
    """
    Model to track login attempts for security monitoring.
    
    This helps detect brute force attacks and suspicious activity.
    """
    
    __tablename__ = "login_attempts"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Attempt details
    email = Column(String(255), index=True, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    
    # Result
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100), nullable=True)
    
    # Timing
    attempted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Geolocation (optional)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    def __repr__(self) -> str:
        return f"<LoginAttempt(email='{self.email}', success={self.success}, ip='{self.ip_address}')>"


class RefreshToken(Base):
    """
    Model to store refresh tokens for JWT authentication.
    
    This allows for secure token refresh without re-authentication.
    """
    
    __tablename__ = "refresh_tokens"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Token details
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    
    # Metadata
    device_info = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id}, expires_at='{self.expires_at}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        return not self.is_expired and not self.is_revoked


class PasswordReset(Base):
    """
    Model to handle password reset requests.
    
    This stores temporary tokens for secure password reset functionality.
    """
    
    __tablename__ = "password_resets"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Reset details
    email = Column(String(255), index=True, nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    
    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Status
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<PasswordReset(email='{self.email}', used={self.used})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if reset token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if reset token is valid."""
        return not self.is_expired and not self.used