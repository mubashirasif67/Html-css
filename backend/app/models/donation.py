"""
Donation and receipt models
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import hashlib
import json

from app.database import Base


class DonationType(str, enum.Enum):
    """Donation type enumeration"""
    ZAKAT = "zakat"
    SADAQAH = "sadaqah"
    GENERAL = "general"
    FITRANA = "fitrana"
    QURBANI = "qurbani"


class PaymentMethod(str, enum.Enum):
    """Payment method enumeration"""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    ONLINE = "online"
    CHEQUE = "cheque"


class Donation(Base):
    """
    Donation model for tracking contributions
    
    Attributes:
        id: Primary key
        donor_id: Foreign key to user (optional for anonymous)
        donor_name: Name of donor
        donor_email: Email of donor
        donor_cnic: CNIC of donor (optional)
        donation_type: Type of donation (Zakat, Sadaqah, etc.)
        amount: Donation amount
        currency: Currency code (default PKR)
        payment_method: How the payment was made
        receipt_image_path: Path to uploaded receipt image
        ocr_detected_amount: Amount detected by OCR
        ocr_confidence: OCR detection confidence
        is_verified: Whether donation is verified
        blockchain_hash: Optional blockchain receipt hash
        notes: Additional notes
    """
    __tablename__ = "donations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Donor information
    donor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    donor_name = Column(String(255), nullable=False)
    donor_email = Column(String(255), index=True)
    donor_phone = Column(String(20))
    donor_cnic = Column(String(20))
    is_anonymous = Column(Boolean, default=False)
    
    # Donation details
    donation_type = Column(Enum(DonationType), default=DonationType.GENERAL, nullable=False)
    amount = Column(Float, nullable=False, index=True)
    currency = Column(String(3), default="PKR")
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    transaction_id = Column(String(100), unique=True, index=True)
    
    # Receipt and OCR
    receipt_image_path = Column(String(500))
    ocr_detected_amount = Column(Float)
    ocr_confidence = Column(Float)
    ocr_raw_text = Column(Text)
    
    # Verification and security
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_date = Column(DateTime(timezone=True))
    blockchain_hash = Column(String(64), unique=True)  # SHA256 hash
    
    # Additional information
    notes = Column(Text)
    campaign_id = Column(String(50))  # For specific campaigns
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    donor = relationship("User", foreign_keys=[donor_id], back_populates="donations")
    verifier = relationship("User", foreign_keys=[verified_by])
    receipt = relationship("DonationReceipt", back_populates="donation", uselist=False)
    
    def __repr__(self):
        return f"<Donation(id={self.id}, amount={self.amount}, type={self.donation_type})>"
    
    def generate_blockchain_hash(self):
        """
        Generate a blockchain-style hash for the donation
        Used for transparency and audit trail
        """
        data = {
            "id": self.id,
            "donor_name": self.donor_name,
            "amount": self.amount,
            "type": self.donation_type.value if self.donation_type else "general",
            "timestamp": self.created_at.isoformat() if self.created_at else "",
        }
        
        json_str = json.dumps(data, sort_keys=True)
        self.blockchain_hash = hashlib.sha256(json_str.encode()).hexdigest()
        return self.blockchain_hash
    
    def to_dict(self, include_donor_info=False):
        """
        Convert donation to dictionary
        
        Args:
            include_donor_info: Whether to include donor information
        
        Returns:
            Dictionary representation
        """
        data = {
            "id": self.id,
            "donation_type": self.donation_type.value if self.donation_type else None,
            "amount": self.amount,
            "currency": self.currency,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "is_verified": self.is_verified,
            "blockchain_hash": self.blockchain_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_donor_info and not self.is_anonymous:
            data.update({
                "donor_name": self.donor_name,
                "donor_email": self.donor_email,
                "donor_phone": self.donor_phone,
            })
        elif self.is_anonymous:
            data["donor_name"] = "Anonymous"
        
        if self.ocr_detected_amount:
            data["ocr_detected_amount"] = self.ocr_detected_amount
            data["ocr_confidence"] = round(self.ocr_confidence, 2) if self.ocr_confidence else 0
        
        return data


class DonationReceipt(Base):
    """
    Donation receipt details
    """
    __tablename__ = "donation_receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("donations.id"), unique=True, nullable=False)
    
    # Receipt details
    receipt_number = Column(String(50), unique=True, index=True)
    issued_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Email/SMS status
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True))
    sms_sent = Column(Boolean, default=False)
    sms_sent_at = Column(DateTime(timezone=True))
    
    # PDF generation
    pdf_path = Column(String(500))
    pdf_generated_at = Column(DateTime(timezone=True))
    
    # Relationship
    donation = relationship("Donation", back_populates="receipt")
    
    def generate_receipt_number(self):
        """Generate unique receipt number"""
        if self.donation_id:
            timestamp = self.issued_date.strftime("%Y%m%d%H%M%S") if self.issued_date else "00000000000000"
            self.receipt_number = f"RCP-{timestamp}-{self.donation_id:06d}"
        return self.receipt_number