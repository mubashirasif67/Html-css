"""
Pydantic schemas for API request/response validation.

Defines input and output models for all API endpoints to ensure
data consistency and provide OpenAPI documentation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from .models import UserRole, DonationType, EmployeeGrade


class UserBase(BaseModel):
    """Base schema for user data."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: UserRole = UserRole.DONOR


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    """Schema for user response (excluding password)."""
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT tokens."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr
    password: str


class EmployeeBase(BaseModel):
    """Base schema for employee data."""
    name: str = Field(..., min_length=1, max_length=100)
    father_name: str = Field(..., min_length=1, max_length=100)
    cnic: str = Field(..., regex=r"^\d{5}-\d{7}-\d{1}$")  # CNIC format
    grade: EmployeeGrade
    designation: Optional[str] = None
    mobile: str = Field(..., regex=r"^\d{10,15}$")
    address: Optional[str] = None
    family_size: int = Field(default=1, ge=1)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class EmployeeCreate(EmployeeBase):
    """Schema for creating an employee."""
    pass


class EmployeeResponse(EmployeeBase):
    """Schema for employee response."""
    id: int
    user_id: Optional[int]
    family_key: str
    is_eligible: bool
    eligibility_score: float
    fraud_flag: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DonationBase(BaseModel):
    """Base schema for donation data."""
    donor_name: str = Field(..., min_length=1, max_length=100)
    donor_email: Optional[EmailStr] = None
    donor_cnic: Optional[str] = Field(None, regex=r"^\d{5}-\d{7}-\d{1}$")
    amount: float = Field(..., gt=0)
    donation_type: DonationType
    receipt_image: Optional[str] = None  # Base64 or URL for upload


class DonationCreate(DonationBase):
    """Schema for creating a donation."""
    pass


class DonationResponse(DonationBase):
    """Schema for donation response."""
    id: int
    donor_id: Optional[int]
    detected_amount: Optional[float]
    confidence: Optional[float]
    ocr_text: Optional[str]
    transaction_hash: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class OCRResult(BaseModel):
    """Schema for OCR processing result."""
    detected_amount: Optional[float]
    currency: str = "PKR"
    confidence: float
    raw_text: str
    boxes: Optional[List[dict]] = None  # Bounding boxes for detected text


class DistributionRunCreate(BaseModel):
    """Schema for creating a distribution run."""
    run_date: datetime


class DistributionRunResponse(BaseModel):
    """Schema for distribution run response."""
    id: int
    admin_id: int
    run_date: datetime
    status: str
    total_beneficiaries: int
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True


class DistributionResponse(BaseModel):
    """Schema for distribution response."""
    id: int
    employee_id: int
    run_id: int
    amount: float
    pickup_slot: Optional[str]
    notification_sent: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    feedback_text: str = Field(..., min_length=1, max_length=1000)


class FeedbackResponse(FeedbackCreate):
    """Schema for feedback response."""
    id: int
    user_id: int
    sentiment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True