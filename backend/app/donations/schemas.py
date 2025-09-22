"""
Donation schemas for the Blessings Donation System.

This module defines Pydantic schemas for donation requests and responses.
"""

from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .models import DonationType, DonationStatus, PaymentMethod


class DonationTypeEnum(str, Enum):
    """Donation type enumeration for API."""
    ZAKAT = "zakat"
    SADAQAH = "sadaqah"
    GENERAL = "general"
    EMERGENCY = "emergency"
    EDUCATION = "education"
    MEDICAL = "medical"


class DonationStatusEnum(str, Enum):
    """Donation status enumeration for API."""
    PENDING = "pending"
    VERIFIED = "verified"
    PROCESSED = "processed"
    REJECTED = "rejected"


class PaymentMethodEnum(str, Enum):
    """Payment method enumeration for API."""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    ONLINE = "online"
    MOBILE_WALLET = "mobile_wallet"
    CHEQUE = "cheque"
    OTHER = "other"


# Donation Creation Schemas
class DonationCreateRequest(BaseModel):
    """Schema for creating a new donation."""
    donor_name: str = Field(..., min_length=2, max_length=255, description="Donor full name")
    donor_email: Optional[EmailStr] = Field(None, description="Donor email address")
    donor_phone: Optional[str] = Field(None, max_length=20, description="Donor phone number")
    donor_cnic: Optional[str] = Field(None, max_length=15, description="Donor CNIC")
    donor_address: Optional[str] = Field(None, description="Donor address")
    
    amount: Optional[float] = Field(None, ge=1.0, description="Donation amount (required if no receipt)")
    currency: str = Field(default="PKR", max_length=3, description="Currency code")
    donation_type: DonationTypeEnum = Field(default=DonationTypeEnum.GENERAL, description="Donation type")
    payment_method: PaymentMethodEnum = Field(default=PaymentMethodEnum.CASH, description="Payment method")
    
    campaign: Optional[str] = Field(None, max_length=100, description="Campaign name")
    reference_number: Optional[str] = Field(None, max_length=100, description="Reference number")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @validator('donor_phone')
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v:
            clean_phone = ''.join(c for c in v if c.isdigit() or c == '+')
            if not clean_phone.replace('+', '').isdigit():
                raise ValueError('Phone number must contain only digits and optional + prefix')
            if len(clean_phone.replace('+', '')) < 10:
                raise ValueError('Phone number must be at least 10 digits')
        return v
    
    @validator('donor_cnic')
    def validate_cnic(cls, v):
        """Validate CNIC format."""
        if v:
            # Remove hyphens and spaces
            clean_cnic = v.replace('-', '').replace(' ', '')
            if not clean_cnic.isdigit() or len(clean_cnic) != 13:
                raise ValueError('CNIC must be 13 digits')
            # Format as XXXXX-XXXXXXX-X
            return f"{clean_cnic[:5]}-{clean_cnic[5:12]}-{clean_cnic[12]}"
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "donor_name": "Ahmed Khan",
                "donor_email": "ahmed.khan@example.com",
                "donor_phone": "+923001234567",
                "donor_cnic": "12345-1234567-1",
                "donor_address": "House 123, Street 45, Islamabad",
                "amount": 5000.0,
                "currency": "PKR",
                "donation_type": "zakat",
                "payment_method": "bank_transfer",
                "campaign": "Ramadan 2023",
                "notes": "Monthly zakat donation"
            }
        }


class DonationUpdateRequest(BaseModel):
    """Schema for updating donation information."""
    donor_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Donor full name")
    donor_email: Optional[EmailStr] = Field(None, description="Donor email address")
    donor_phone: Optional[str] = Field(None, max_length=20, description="Donor phone number")
    donor_address: Optional[str] = Field(None, description="Donor address")
    
    amount: Optional[float] = Field(None, ge=1.0, description="Donation amount")
    donation_type: Optional[DonationTypeEnum] = Field(None, description="Donation type")
    payment_method: Optional[PaymentMethodEnum] = Field(None, description="Payment method")
    
    status: Optional[DonationStatusEnum] = Field(None, description="Donation status")
    verification_notes: Optional[str] = Field(None, description="Verification notes")
    
    campaign: Optional[str] = Field(None, max_length=100, description="Campaign name")
    notes: Optional[str] = Field(None, description="Additional notes")


# OCR Schemas
class OCRResult(BaseModel):
    """Schema for OCR processing results."""
    detected_amount: Optional[float] = Field(None, description="Detected amount from receipt")
    currency: Optional[str] = Field(None, description="Detected currency")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score")
    raw_text: str = Field(..., description="Raw OCR text")
    processing_time: float = Field(..., description="Processing time in seconds")
    text_boxes: List[Dict[str, Any]] = Field(default=[], description="Text bounding boxes")
    
    class Config:
        schema_extra = {
            "example": {
                "detected_amount": 5000.0,
                "currency": "PKR",
                "confidence": 0.92,
                "raw_text": "BANK RECEIPT\nAmount: Rs 5,000\nDate: 01/12/2023",
                "processing_time": 2.35,
                "text_boxes": [
                    {"text": "Rs 5,000", "x": 120, "y": 45, "width": 80, "height": 20}
                ]
            }
        }


class ReceiptUploadResponse(BaseModel):
    """Schema for receipt upload response."""
    receipt_id: int = Field(..., description="Receipt ID")
    ocr_result: OCRResult = Field(..., description="OCR processing results")
    suggested_amount: Optional[float] = Field(None, description="Suggested donation amount")
    requires_manual_review: bool = Field(..., description="Whether manual review is required")
    
    class Config:
        schema_extra = {
            "example": {
                "receipt_id": 123,
                "ocr_result": {
                    "detected_amount": 5000.0,
                    "currency": "PKR",
                    "confidence": 0.92,
                    "raw_text": "BANK RECEIPT\nAmount: Rs 5,000\nDate: 01/12/2023",
                    "processing_time": 2.35,
                    "text_boxes": []
                },
                "suggested_amount": 5000.0,
                "requires_manual_review": False
            }
        }


# Response Schemas
class DonationResponse(BaseModel):
    """Schema for donation response."""
    id: int = Field(..., description="Donation ID")
    donor_name: str = Field(..., description="Donor name")
    donor_email: Optional[str] = Field(None, description="Donor email")
    donor_phone: Optional[str] = Field(None, description="Donor phone")
    masked_cnic: Optional[str] = Field(None, description="Masked CNIC")
    donor_address: Optional[str] = Field(None, description="Donor address")
    
    amount: float = Field(..., description="Donation amount")
    currency: str = Field(..., description="Currency")
    donation_type: str = Field(..., description="Donation type")
    payment_method: str = Field(..., description="Payment method")
    
    receipt_number: Optional[str] = Field(None, description="Receipt number")
    receipt_exists: bool = Field(..., description="Whether receipt image exists")
    
    ocr_detected_amount: Optional[float] = Field(None, description="OCR detected amount")
    ocr_confidence: Optional[float] = Field(None, description="OCR confidence")
    ocr_processed: bool = Field(..., description="Whether OCR was processed")
    
    status: str = Field(..., description="Donation status")
    verification_notes: Optional[str] = Field(None, description="Verification notes")
    
    fraud_score: Optional[float] = Field(None, description="Fraud detection score")
    is_suspicious: bool = Field(..., description="Whether flagged as suspicious")
    
    campaign: Optional[str] = Field(None, description="Campaign name")
    reference_number: Optional[str] = Field(None, description="Reference number")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "donor_name": "Ahmed Khan",
                "donor_email": "ahmed.khan@example.com",
                "donor_phone": "+923001234567",
                "masked_cnic": "12345-****567-1",
                "donor_address": "House 123, Street 45, Islamabad",
                "amount": 5000.0,
                "currency": "PKR",
                "donation_type": "zakat",
                "payment_method": "bank_transfer",
                "receipt_number": "BLS-20231201-1234",
                "receipt_exists": True,
                "ocr_detected_amount": 5000.0,
                "ocr_confidence": 0.92,
                "ocr_processed": True,
                "status": "verified",
                "verification_notes": "Amount confirmed from receipt",
                "fraud_score": 0.1,
                "is_suspicious": False,
                "campaign": "Ramadan 2023",
                "reference_number": "REF-001",
                "notes": "Monthly zakat donation",
                "created_at": "2023-12-01T10:30:00Z",
                "updated_at": "2023-12-01T11:00:00Z",
                "processed_at": "2023-12-01T11:00:00Z"
            }
        }


class DonationListResponse(BaseModel):
    """Schema for paginated donation list response."""
    donations: List[DonationResponse] = Field(..., description="List of donations")
    total: int = Field(..., description="Total number of donations")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Donations per page")
    pages: int = Field(..., description="Total number of pages")
    total_amount: float = Field(..., description="Total amount of all donations")
    
    class Config:
        schema_extra = {
            "example": {
                "donations": [],
                "total": 150,
                "page": 1,
                "per_page": 20,
                "pages": 8,
                "total_amount": 750000.0
            }
        }


# Statistics Schemas
class DonationStatsResponse(BaseModel):
    """Schema for donation statistics response."""
    total_donations: int = Field(..., description="Total number of donations")
    total_amount: float = Field(..., description="Total donation amount")
    average_amount: float = Field(..., description="Average donation amount")
    
    by_type: Dict[str, Dict[str, Any]] = Field(..., description="Statistics by donation type")
    by_status: Dict[str, int] = Field(..., description="Count by status")
    by_payment_method: Dict[str, int] = Field(..., description="Count by payment method")
    
    ocr_stats: Dict[str, Any] = Field(..., description="OCR processing statistics")
    fraud_stats: Dict[str, Any] = Field(..., description="Fraud detection statistics")
    
    recent_donations: List[DonationResponse] = Field(..., description="Recent donations")
    
    class Config:
        schema_extra = {
            "example": {
                "total_donations": 150,
                "total_amount": 750000.0,
                "average_amount": 5000.0,
                "by_type": {
                    "zakat": {"count": 80, "amount": 400000.0},
                    "sadaqah": {"count": 50, "amount": 250000.0},
                    "general": {"count": 20, "amount": 100000.0}
                },
                "by_status": {
                    "pending": 10,
                    "verified": 120,
                    "processed": 15,
                    "rejected": 5
                },
                "by_payment_method": {
                    "bank_transfer": 80,
                    "cash": 40,
                    "online": 30
                },
                "ocr_stats": {
                    "total_processed": 100,
                    "success_rate": 0.85,
                    "average_confidence": 0.78
                },
                "fraud_stats": {
                    "total_flagged": 5,
                    "confirmed_fraud": 2,
                    "false_positives": 3
                },
                "recent_donations": []
            }
        }


# Note Schemas
class DonationNoteCreate(BaseModel):
    """Schema for creating donation notes."""
    note: str = Field(..., min_length=1, description="Note content")
    note_type: str = Field(default="general", description="Note type")
    is_internal: bool = Field(default=True, description="Whether note is internal")


class DonationNoteResponse(BaseModel):
    """Schema for donation note response."""
    id: int = Field(..., description="Note ID")
    donation_id: int = Field(..., description="Donation ID")
    note: str = Field(..., description="Note content")
    note_type: str = Field(..., description="Note type")
    is_internal: bool = Field(..., description="Whether note is internal")
    created_by: int = Field(..., description="User ID who created the note")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


# Audit Schemas
class DonationAuditResponse(BaseModel):
    """Schema for donation audit response."""
    id: int = Field(..., description="Audit ID")
    donation_id: int = Field(..., description="Donation ID")
    field_name: str = Field(..., description="Changed field name")
    old_value: Optional[str] = Field(None, description="Old value")
    new_value: Optional[str] = Field(None, description="New value")
    change_type: str = Field(..., description="Change type")
    changed_by: int = Field(..., description="User ID who made the change")
    changed_at: datetime = Field(..., description="Change timestamp")
    reason: Optional[str] = Field(None, description="Reason for change")
    
    class Config:
        from_attributes = True


# Export/Report Schemas
class DonationExportRequest(BaseModel):
    """Schema for donation export request."""
    format: str = Field(default="csv", description="Export format (csv, xlsx, pdf)")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    donation_type: Optional[DonationTypeEnum] = Field(None, description="Donation type filter")
    status: Optional[DonationStatusEnum] = Field(None, description="Status filter")
    min_amount: Optional[float] = Field(None, ge=0, description="Minimum amount filter")
    max_amount: Optional[float] = Field(None, ge=0, description="Maximum amount filter")
    include_sensitive: bool = Field(default=False, description="Include sensitive data (admin only)")


class DonationExportResponse(BaseModel):
    """Schema for donation export response."""
    export_id: str = Field(..., description="Export job ID")
    download_url: str = Field(..., description="Download URL")
    expires_at: datetime = Field(..., description="URL expiration time")
    record_count: int = Field(..., description="Number of records exported")
    file_size: int = Field(..., description="File size in bytes")
    
    class Config:
        schema_extra = {
            "example": {
                "export_id": "exp_20231201_123456",
                "download_url": "/api/v1/donations/exports/exp_20231201_123456/download",
                "expires_at": "2023-12-02T10:30:00Z",
                "record_count": 150,
                "file_size": 25600
            }
        }


# API Response Schemas
class MessageResponse(BaseModel):
    """Generic message response schema."""
    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")