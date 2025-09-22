"""
Donation models for the Blessings Donation System.

This module defines donation-related database models.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, Text, LargeBinary
from sqlalchemy.sql import func
import enum
from datetime import datetime
from typing import Optional

from ..database import Base


class DonationType(str, enum.Enum):
    """Donation type enumeration."""
    ZAKAT = "zakat"
    SADAQAH = "sadaqah"
    GENERAL = "general"
    EMERGENCY = "emergency"
    EDUCATION = "education"
    MEDICAL = "medical"


class DonationStatus(str, enum.Enum):
    """Donation status enumeration."""
    PENDING = "pending"
    VERIFIED = "verified"
    PROCESSED = "processed"
    REJECTED = "rejected"


class PaymentMethod(str, enum.Enum):
    """Payment method enumeration."""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    ONLINE = "online"
    MOBILE_WALLET = "mobile_wallet"
    CHEQUE = "cheque"
    OTHER = "other"


class Donation(Base):
    """
    Donation model to store donation information.
    
    This model captures all donation details including donor information,
    amount, type, and processing status.
    """
    
    __tablename__ = "donations"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Donor information
    donor_name = Column(String(255), nullable=False, index=True)
    donor_email = Column(String(255), nullable=True, index=True)
    donor_phone = Column(String(20), nullable=True)
    donor_cnic = Column(String(15), nullable=True, index=True)  # Encrypted/masked
    donor_address = Column(Text, nullable=True)
    
    # Donation details
    amount = Column(Float, nullable=False, index=True)
    currency = Column(String(3), default="PKR", nullable=False)
    donation_type = Column(Enum(DonationType), default=DonationType.GENERAL, nullable=False)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH, nullable=False)
    
    # Receipt information
    receipt_number = Column(String(50), unique=True, nullable=True, index=True)
    receipt_image_path = Column(String(500), nullable=True)
    receipt_hash = Column(String(64), nullable=True)  # SHA256 for integrity
    
    # OCR information
    ocr_detected_amount = Column(Float, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    ocr_raw_text = Column(Text, nullable=True)
    ocr_processed = Column(Boolean, default=False, nullable=False)
    
    # Status and processing
    status = Column(Enum(DonationStatus), default=DonationStatus.PENDING, nullable=False)
    verified_by = Column(Integer, nullable=True)  # User ID who verified
    verification_notes = Column(Text, nullable=True)
    
    # Fraud detection
    fraud_score = Column(Float, nullable=True)
    fraud_flags = Column(Text, nullable=True)  # JSON string of flags
    is_suspicious = Column(Boolean, default=False, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional metadata
    source = Column(String(50), default="web", nullable=False)  # web, mobile, api
    campaign = Column(String(100), nullable=True)
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Geolocation (optional)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_name = Column(String(200), nullable=True)
    
    def __repr__(self) -> str:
        return f"<Donation(id={self.id}, donor='{self.donor_name}', amount={self.amount}, status='{self.status}')>"
    
    @property
    def is_verified(self) -> bool:
        """Check if donation is verified."""
        return self.status == DonationStatus.VERIFIED
    
    @property
    def is_processed(self) -> bool:
        """Check if donation is processed."""
        return self.status == DonationStatus.PROCESSED
    
    @property
    def masked_cnic(self) -> Optional[str]:
        """Get masked CNIC for display."""
        if not self.donor_cnic:
            return None
        # Mask middle digits: 12345-1234567-1 -> 12345-****567-1
        if len(self.donor_cnic) >= 13:
            return f"{self.donor_cnic[:5]}-****{self.donor_cnic[-3:]}"
        return "****"
    
    @property
    def receipt_exists(self) -> bool:
        """Check if receipt image exists."""
        return bool(self.receipt_image_path)
    
    def generate_receipt_number(self) -> str:
        """Generate a unique receipt number."""
        from datetime import datetime
        import random
        
        timestamp = datetime.now().strftime("%Y%m%d")
        random_part = f"{random.randint(1000, 9999)}"
        return f"BLS-{timestamp}-{random_part}"


class DonationReceipt(Base):
    """
    Model to store receipt images and OCR data.
    
    This model stores the actual receipt images and OCR processing results.
    """
    
    __tablename__ = "donation_receipts"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to donation
    donation_id = Column(Integer, index=True, nullable=False)
    
    # File information
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA256
    
    # Image metadata
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    image_format = Column(String(10), nullable=True)
    
    # OCR results
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    ocr_language = Column(String(10), default="eng", nullable=False)
    ocr_processing_time = Column(Float, nullable=True)  # seconds
    
    # Detected amounts and currencies
    detected_amounts = Column(Text, nullable=True)  # JSON array
    detected_currencies = Column(Text, nullable=True)  # JSON array
    best_amount = Column(Float, nullable=True)
    best_currency = Column(String(3), nullable=True)
    
    # Bounding boxes for detected text
    text_boxes = Column(Text, nullable=True)  # JSON array of bounding boxes
    
    # Processing status
    processed = Column(Boolean, default=False, nullable=False)
    processing_error = Column(Text, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<DonationReceipt(id={self.id}, donation_id={self.donation_id}, processed={self.processed})>"


class DonationNote(Base):
    """
    Model to store notes and comments on donations.
    
    This allows staff to add notes during verification and processing.
    """
    
    __tablename__ = "donation_notes"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to donation
    donation_id = Column(Integer, index=True, nullable=False)
    
    # Note details
    note = Column(Text, nullable=False)
    note_type = Column(String(50), default="general", nullable=False)  # general, verification, fraud, etc.
    
    # Author information
    created_by = Column(Integer, nullable=False)  # User ID
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Visibility
    is_internal = Column(Boolean, default=True, nullable=False)  # Internal staff notes vs public
    
    def __repr__(self) -> str:
        return f"<DonationNote(id={self.id}, donation_id={self.donation_id}, type='{self.note_type}')>"


class DonationAudit(Base):
    """
    Model to track all changes to donations for audit purposes.
    
    This provides a complete audit trail of donation modifications.
    """
    
    __tablename__ = "donation_audit"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to donation
    donation_id = Column(Integer, index=True, nullable=False)
    
    # Change information
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_type = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    
    # User information
    changed_by = Column(Integer, nullable=False)  # User ID
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Additional context
    reason = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    def __repr__(self) -> str:
        return f"<DonationAudit(id={self.id}, donation_id={self.donation_id}, field='{self.field_name}')>"


class DonationStats(Base):
    """
    Model to store aggregated donation statistics.
    
    This table is populated by periodic tasks for performance.
    """
    
    __tablename__ = "donation_stats"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Time period
    stat_date = Column(DateTime(timezone=True), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, yearly
    
    # Aggregated values
    total_donations = Column(Integer, default=0, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    average_amount = Column(Float, default=0.0, nullable=False)
    
    # By donation type
    zakat_count = Column(Integer, default=0, nullable=False)
    zakat_amount = Column(Float, default=0.0, nullable=False)
    sadaqah_count = Column(Integer, default=0, nullable=False)
    sadaqah_amount = Column(Float, default=0.0, nullable=False)
    general_count = Column(Integer, default=0, nullable=False)
    general_amount = Column(Float, default=0.0, nullable=False)
    
    # By status
    pending_count = Column(Integer, default=0, nullable=False)
    verified_count = Column(Integer, default=0, nullable=False)
    processed_count = Column(Integer, default=0, nullable=False)
    rejected_count = Column(Integer, default=0, nullable=False)
    
    # OCR statistics
    ocr_processed_count = Column(Integer, default=0, nullable=False)
    ocr_success_rate = Column(Float, default=0.0, nullable=False)
    
    # Fraud statistics
    suspicious_count = Column(Integer, default=0, nullable=False)
    fraud_detected_count = Column(Integer, default=0, nullable=False)
    
    # Audit fields
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<DonationStats(date='{self.stat_date}', period='{self.period_type}', total={self.total_donations})>"