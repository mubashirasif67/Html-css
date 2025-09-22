"""
Authentication schemas for the Blessings Donation System.

This module defines Pydantic schemas for authentication requests and responses.
"""

from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from .models import UserRole, UserStatus


class UserRoleEnum(str, Enum):
    """User role enumeration for API."""
    ADMIN = "admin"
    STAFF = "staff"
    VOLUNTEER = "volunteer"
    VIEWER = "viewer"


class UserStatusEnum(str, Enum):
    """User status enumeration for API."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


# Authentication Schemas
class LoginRequest(BaseModel):
    """Schema for user login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "admin@blessings.org",
                "password": "admin123"
            }
        }


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: 'UserResponse' = Field(..., description="User information")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "def50200e3b0c44298fc1c149afbf4c8996fb...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "email": "admin@blessings.org",
                    "name": "System Administrator",
                    "role": "admin",
                    "status": "active"
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


# User Management Schemas
class UserCreateRequest(BaseModel):
    """Schema for creating a new user."""
    name: str = Field(..., min_length=2, max_length=255, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    role: UserRoleEnum = Field(default=UserRoleEnum.VIEWER, description="User role")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    employee_id: Optional[str] = Field(None, max_length=50, description="Employee ID")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v:
            # Remove common separators
            clean_phone = ''.join(c for c in v if c.isdigit() or c == '+')
            if not clean_phone.replace('+', '').isdigit():
                raise ValueError('Phone number must contain only digits and optional + prefix')
            if len(clean_phone.replace('+', '')) < 10:
                raise ValueError('Phone number must be at least 10 digits')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@blessings.org",
                "password": "SecurePass123",
                "phone": "+923001234567",
                "role": "staff",
                "department": "Operations",
                "employee_id": "EMP001",
                "notes": "New staff member"
            }
        }


class UserUpdateRequest(BaseModel):
    """Schema for updating user information."""
    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Full name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    role: Optional[UserRoleEnum] = Field(None, description="User role")
    status: Optional[UserStatusEnum] = Field(None, description="User status")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    employee_id: Optional[str] = Field(None, max_length=50, description="Employee ID")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v:
            clean_phone = ''.join(c for c in v if c.isdigit() or c == '+')
            if not clean_phone.replace('+', '').isdigit():
                raise ValueError('Phone number must contain only digits and optional + prefix')
            if len(clean_phone.replace('+', '')) < 10:
                raise ValueError('Phone number must be at least 10 digits')
        return v


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int = Field(..., description="User ID")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    role: str = Field(..., description="User role")
    status: str = Field(..., description="User status")
    department: Optional[str] = Field(None, description="Department")
    employee_id: Optional[str] = Field(None, description="Employee ID")
    is_verified: bool = Field(..., description="Email verification status")
    last_login: Optional[datetime] = Field(None, description="Last login time")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "email": "john.doe@blessings.org",
                "phone": "+923001234567",
                "role": "staff",
                "status": "active",
                "department": "Operations",
                "employee_id": "EMP001",
                "is_verified": True,
                "last_login": "2023-12-01T10:30:00Z",
                "created_at": "2023-11-01T09:00:00Z",
                "updated_at": "2023-12-01T10:30:00Z"
            }
        }


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Users per page")
    pages: int = Field(..., description="Total number of pages")


# Password Management Schemas
class ChangePasswordRequest(BaseModel):
    """Schema for password change request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""
    email: EmailStr = Field(..., description="Email address")


class ResetPasswordRequest(BaseModel):
    """Schema for password reset request."""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Security Schemas
class LoginAttemptResponse(BaseModel):
    """Schema for login attempt response."""
    id: int
    email: str
    ip_address: Optional[str]
    success: bool
    failure_reason: Optional[str]
    attempted_at: datetime
    country: Optional[str]
    city: Optional[str]
    
    class Config:
        from_attributes = True


class SecurityStatsResponse(BaseModel):
    """Schema for security statistics response."""
    total_users: int
    active_users: int
    failed_logins_today: int
    successful_logins_today: int
    suspicious_activities: int
    recent_attempts: List[LoginAttemptResponse]


# API Response Schemas
class MessageResponse(BaseModel):
    """Generic message response schema."""
    message: str = Field(..., description="Response message")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Operation completed successfully"
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Authentication failed",
                "detail": "Invalid email or password"
            }
        }


# Update forward references
LoginResponse.model_rebuild()