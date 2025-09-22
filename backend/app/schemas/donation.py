"""
Donation-related Pydantic schemas
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DonationType(str, Enum):
    """Donation type enumeration"""
    ZAKAT = "zakat"
    SADAQAH = "sadaqah"
    GENERAL = "general"
    FITRANA = "fitrana"
    QURBANI = "qurbani"


class PaymentMethod(str, Enum):
    """Payment method enumeration"""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    ONLINE = "online"
    CHEQUE = "cheque"


class DonationBase(BaseModel):
    """Base donation schema"""
    donor_name: str = Field(..., min_length=1, max_length=255)
    donor_email: Optional[EmailStr] = None
    donor_phone: Optional[str] = Field(None, max_length=20)
    donor_cnic: Optional[str] = Field(None, max_length=20)
    donation_type: DonationType = DonationType.GENERAL
    amount: Optional[float] = Field(None, gt=0)
    currency: str = Field("PKR", max_length=3)
    payment_method: PaymentMethod = PaymentMethod.CASH
    is_anonymous: bool = False
    notes: Optional[str] = None
    
    @validator('donor_cnic')
    def validate_cnic(cls, v):
        """Validate CNIC format if provided"""
        if v:
            clean = v.replace('-', '').replace(' ', '')
            if not clean.isdigit() or len(clean) != 13:
                raise ValueError('CNIC must be 13 digits')
            return f"{clean[:5]}-{clean[5:12]}-{clean[12]}"
        return v


class DonationCreate(DonationBase):
    """Schema for creating a new donation"""
    campaign_id: Optional[str] = Field(None, max_length=50)


class DonationUpdate(BaseModel):
    """Schema for updating a donation"""
    amount: Optional[float] = Field(None, gt=0)
    is_verified: Optional[bool] = None
    notes: Optional[str] = None


class DonationResponse(BaseModel):
    """Schema for donation response"""
    id: int
    donor_name: str
    donor_email: Optional[str]
    donor_phone: Optional[str]
    donation_type: str
    amount: float
    currency: str
    payment_method: str
    transaction_id: Optional[str]
    is_anonymous: bool
    is_verified: bool
    blockchain_hash: Optional[str]
    receipt_image_path: Optional[str]
    ocr_detected_amount: Optional[float]
    ocr_confidence: Optional[float]
    created_at: datetime
    verified_at: Optional[datetime] = Field(None, alias="verification_date")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class DonationListResponse(BaseModel):
    """Schema for paginated donation list response"""
    total: int
    page: int
    per_page: int
    pages: int
    total_amount: float
    items: List[DonationResponse]


class OCRRequest(BaseModel):
    """Schema for OCR processing request"""
    image_base64: Optional[str] = None  # Base64 encoded image
    confidence_threshold: float = Field(0.8, ge=0, le=1)


class OCRResponse(BaseModel):
    """Schema for OCR processing response"""
    detected_amount: Optional[float]
    confidence: float = Field(..., ge=0, le=1)
    currency: str = "PKR"
    raw_text: str
    boxes: List[Dict[str, Any]] = []  # Bounding boxes for detected text
    processing_time: float  # Time in seconds
    requires_manual_verification: bool


class DonationReceiptRequest(BaseModel):
    """Schema for donation receipt generation request"""
    donation_id: int
    send_email: bool = True
    send_sms: bool = False


class DonationReceiptResponse(BaseModel):
    """Schema for donation receipt response"""
    receipt_number: str
    pdf_url: Optional[str]
    email_sent: bool
    sms_sent: bool
    issued_date: datetime


class DonationStatistics(BaseModel):
    """Schema for donation statistics"""
    total_donations: int
    total_amount: float
    average_donation: float
    donations_by_type: Dict[str, float]
    donations_by_month: Dict[str, float]
    top_donors: List[Dict[str, Any]]
    recent_donations: List[DonationResponse]