"""
Donation services for the Blessings Donation System.

This module provides business logic for donation processing,
OCR integration, and fraud detection.
"""

import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import structlog

from ..config import settings
from .models import (
    Donation, DonationReceipt, DonationNote, DonationAudit,
    DonationType, DonationStatus, PaymentMethod
)
from .schemas import DonationCreateRequest, DonationUpdateRequest, OCRResult

logger = structlog.get_logger(__name__)


class DonationService:
    """Service class for donation-related operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_donation(
        self,
        donation_data: DonationCreateRequest,
        created_by: Optional[int] = None
    ) -> Donation:
        """
        Create a new donation record.
        
        Args:
            donation_data: Donation creation data
            created_by: User ID who created the donation
            
        Returns:
            Donation: Created donation record
        """
        try:
            # Create donation record
            donation = Donation(
                donor_name=donation_data.donor_name,
                donor_email=donation_data.donor_email,
                donor_phone=donation_data.donor_phone,
                donor_cnic=self._encrypt_cnic(donation_data.donor_cnic) if donation_data.donor_cnic else None,
                donor_address=donation_data.donor_address,
                amount=donation_data.amount or 0.0,
                currency=donation_data.currency,
                donation_type=DonationType(donation_data.donation_type.value),
                payment_method=PaymentMethod(donation_data.payment_method.value),
                campaign=donation_data.campaign,
                reference_number=donation_data.reference_number,
                notes=donation_data.notes,
                status=DonationStatus.PENDING
            )
            
            # Generate receipt number
            donation.receipt_number = donation.generate_receipt_number()
            
            # Calculate receipt hash for integrity
            if donation_data.amount:
                donation.receipt_hash = self._calculate_donation_hash(donation)
            
            self.db.add(donation)
            self.db.flush()  # Get the ID without committing
            
            # Create audit record
            self._create_audit_record(
                donation_id=donation.id,
                field_name="created",
                new_value="donation_created",
                change_type="INSERT",
                changed_by=created_by or 0
            )
            
            self.db.commit()
            self.db.refresh(donation)
            
            logger.info(
                "Donation created successfully",
                donation_id=donation.id,
                donor_name=donation.donor_name,
                amount=donation.amount,
                created_by=created_by
            )
            
            return donation
            
        except Exception as e:
            logger.error("Failed to create donation", error=str(e))
            self.db.rollback()
            raise
    
    def update_donation(
        self,
        donation_id: int,
        donation_data: DonationUpdateRequest,
        updated_by: int
    ) -> Optional[Donation]:
        """
        Update an existing donation.
        
        Args:
            donation_id: Donation ID
            donation_data: Update data
            updated_by: User ID who updated the donation
            
        Returns:
            Donation: Updated donation record or None if not found
        """
        try:
            donation = self.db.query(Donation).filter(Donation.id == donation_id).first()
            if not donation:
                return None
            
            # Track changes for audit
            changes = []
            
            # Update fields and track changes
            if donation_data.donor_name is not None and donation_data.donor_name != donation.donor_name:
                changes.append(("donor_name", donation.donor_name, donation_data.donor_name))
                donation.donor_name = donation_data.donor_name
            
            if donation_data.donor_email is not None and donation_data.donor_email != donation.donor_email:
                changes.append(("donor_email", donation.donor_email, donation_data.donor_email))
                donation.donor_email = donation_data.donor_email
            
            if donation_data.donor_phone is not None and donation_data.donor_phone != donation.donor_phone:
                changes.append(("donor_phone", donation.donor_phone, donation_data.donor_phone))
                donation.donor_phone = donation_data.donor_phone
            
            if donation_data.amount is not None and donation_data.amount != donation.amount:
                changes.append(("amount", str(donation.amount), str(donation_data.amount)))
                donation.amount = donation_data.amount
            
            if donation_data.donation_type is not None:
                new_type = DonationType(donation_data.donation_type.value)
                if new_type != donation.donation_type:
                    changes.append(("donation_type", donation.donation_type.value, new_type.value))
                    donation.donation_type = new_type
            
            if donation_data.payment_method is not None:
                new_method = PaymentMethod(donation_data.payment_method.value)
                if new_method != donation.payment_method:
                    changes.append(("payment_method", donation.payment_method.value, new_method.value))
                    donation.payment_method = new_method
            
            if donation_data.status is not None:
                new_status = DonationStatus(donation_data.status.value)
                if new_status != donation.status:
                    changes.append(("status", donation.status.value, new_status.value))
                    donation.status = new_status
                    
                    # Update processed timestamp if status changed to processed
                    if new_status == DonationStatus.PROCESSED:
                        donation.processed_at = datetime.utcnow()
            
            if donation_data.verification_notes is not None:
                changes.append(("verification_notes", donation.verification_notes, donation_data.verification_notes))
                donation.verification_notes = donation_data.verification_notes
            
            # Create audit records for changes
            for field_name, old_value, new_value in changes:
                self._create_audit_record(
                    donation_id=donation.id,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                    change_type="UPDATE",
                    changed_by=updated_by
                )
            
            self.db.commit()
            self.db.refresh(donation)
            
            logger.info(
                "Donation updated successfully",
                donation_id=donation.id,
                changes_count=len(changes),
                updated_by=updated_by
            )
            
            return donation
            
        except Exception as e:
            logger.error("Failed to update donation", donation_id=donation_id, error=str(e))
            self.db.rollback()
            raise
    
    def get_donation(self, donation_id: int) -> Optional[Donation]:
        """Get donation by ID."""
        return self.db.query(Donation).filter(Donation.id == donation_id).first()
    
    def list_donations(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        donation_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None
    ) -> Tuple[List[Donation], int, float]:
        """
        List donations with filtering and pagination.
        
        Returns:
            Tuple of (donations, total_count, total_amount)
        """
        try:
            query = self.db.query(Donation)
            
            # Apply filters
            if status:
                query = query.filter(Donation.status == DonationStatus(status))
            
            if donation_type:
                query = query.filter(Donation.donation_type == DonationType(donation_type))
            
            if date_from:
                query = query.filter(Donation.created_at >= date_from)
            
            if date_to:
                query = query.filter(Donation.created_at <= date_to)
            
            if min_amount is not None:
                query = query.filter(Donation.amount >= min_amount)
            
            if max_amount is not None:
                query = query.filter(Donation.amount <= max_amount)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Donation.donor_name.ilike(search_term),
                        Donation.donor_email.ilike(search_term),
                        Donation.receipt_number.ilike(search_term),
                        Donation.reference_number.ilike(search_term)
                    )
                )
            
            # Get total count and amount before pagination
            total_count = query.count()
            total_amount = query.with_entities(func.sum(Donation.amount)).scalar() or 0.0
            
            # Apply pagination
            offset = (page - 1) * per_page
            donations = query.order_by(Donation.created_at.desc()).offset(offset).limit(per_page).all()
            
            return donations, total_count, total_amount
            
        except Exception as e:
            logger.error("Failed to list donations", error=str(e))
            raise
    
    def get_donation_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get donation statistics.
        
        Args:
            date_from: Start date filter
            date_to: End date filter
            
        Returns:
            dict: Statistics data
        """
        try:
            query = self.db.query(Donation)
            
            if date_from:
                query = query.filter(Donation.created_at >= date_from)
            if date_to:
                query = query.filter(Donation.created_at <= date_to)
            
            # Basic statistics
            total_donations = query.count()
            total_amount = query.with_entities(func.sum(Donation.amount)).scalar() or 0.0
            average_amount = total_amount / total_donations if total_donations > 0 else 0.0
            
            # Statistics by type
            by_type = {}
            for donation_type in DonationType:
                type_query = query.filter(Donation.donation_type == donation_type)
                count = type_query.count()
                amount = type_query.with_entities(func.sum(Donation.amount)).scalar() or 0.0
                by_type[donation_type.value] = {"count": count, "amount": amount}
            
            # Statistics by status
            by_status = {}
            for status in DonationStatus:
                count = query.filter(Donation.status == status).count()
                by_status[status.value] = count
            
            # Statistics by payment method
            by_payment_method = {}
            for method in PaymentMethod:
                count = query.filter(Donation.payment_method == method).count()
                by_payment_method[method.value] = count
            
            # OCR statistics
            ocr_processed = query.filter(Donation.ocr_processed == True).count()
            ocr_success = query.filter(
                and_(
                    Donation.ocr_processed == True,
                    Donation.ocr_confidence >= settings.ocr_confidence_threshold
                )
            ).count()
            
            ocr_stats = {
                "total_processed": ocr_processed,
                "success_rate": ocr_success / ocr_processed if ocr_processed > 0 else 0.0,
                "average_confidence": query.filter(
                    Donation.ocr_confidence.isnot(None)
                ).with_entities(func.avg(Donation.ocr_confidence)).scalar() or 0.0
            }
            
            # Fraud statistics
            suspicious_count = query.filter(Donation.is_suspicious == True).count()
            high_fraud_score = query.filter(
                Donation.fraud_score >= settings.fraud_detection_threshold
            ).count()
            
            fraud_stats = {
                "total_flagged": suspicious_count,
                "high_risk_count": high_fraud_score,
                "fraud_rate": suspicious_count / total_donations if total_donations > 0 else 0.0
            }
            
            # Recent donations
            recent_donations = query.order_by(Donation.created_at.desc()).limit(10).all()
            
            return {
                "total_donations": total_donations,
                "total_amount": total_amount,
                "average_amount": average_amount,
                "by_type": by_type,
                "by_status": by_status,
                "by_payment_method": by_payment_method,
                "ocr_stats": ocr_stats,
                "fraud_stats": fraud_stats,
                "recent_donations": recent_donations
            }
            
        except Exception as e:
            logger.error("Failed to get donation statistics", error=str(e))
            raise
    
    def add_donation_note(
        self,
        donation_id: int,
        note: str,
        note_type: str = "general",
        is_internal: bool = True,
        created_by: int = 0
    ) -> DonationNote:
        """Add a note to a donation."""
        try:
            donation_note = DonationNote(
                donation_id=donation_id,
                note=note,
                note_type=note_type,
                is_internal=is_internal,
                created_by=created_by
            )
            
            self.db.add(donation_note)
            self.db.commit()
            self.db.refresh(donation_note)
            
            logger.info("Donation note added", donation_id=donation_id, note_type=note_type)
            return donation_note
            
        except Exception as e:
            logger.error("Failed to add donation note", error=str(e))
            self.db.rollback()
            raise
    
    def get_donation_notes(self, donation_id: int, include_internal: bool = True) -> List[DonationNote]:
        """Get notes for a donation."""
        query = self.db.query(DonationNote).filter(DonationNote.donation_id == donation_id)
        
        if not include_internal:
            query = query.filter(DonationNote.is_internal == False)
        
        return query.order_by(DonationNote.created_at.desc()).all()
    
    def get_donation_audit(self, donation_id: int) -> List[DonationAudit]:
        """Get audit trail for a donation."""
        return self.db.query(DonationAudit).filter(
            DonationAudit.donation_id == donation_id
        ).order_by(DonationAudit.changed_at.desc()).all()
    
    def verify_donation(
        self,
        donation_id: int,
        verified_by: int,
        notes: Optional[str] = None
    ) -> Optional[Donation]:
        """Mark a donation as verified."""
        try:
            donation = self.db.query(Donation).filter(Donation.id == donation_id).first()
            if not donation:
                return None
            
            old_status = donation.status.value
            donation.status = DonationStatus.VERIFIED
            donation.verified_by = verified_by
            if notes:
                donation.verification_notes = notes
            
            # Create audit record
            self._create_audit_record(
                donation_id=donation.id,
                field_name="status",
                old_value=old_status,
                new_value="verified",
                change_type="UPDATE",
                changed_by=verified_by,
                reason="Manual verification"
            )
            
            self.db.commit()
            self.db.refresh(donation)
            
            logger.info("Donation verified", donation_id=donation_id, verified_by=verified_by)
            return donation
            
        except Exception as e:
            logger.error("Failed to verify donation", error=str(e))
            self.db.rollback()
            raise
    
    def process_donation(
        self,
        donation_id: int,
        processed_by: int
    ) -> Optional[Donation]:
        """Mark a donation as processed."""
        try:
            donation = self.db.query(Donation).filter(Donation.id == donation_id).first()
            if not donation:
                return None
            
            old_status = donation.status.value
            donation.status = DonationStatus.PROCESSED
            donation.processed_at = datetime.utcnow()
            
            # Create audit record
            self._create_audit_record(
                donation_id=donation.id,
                field_name="status",
                old_value=old_status,
                new_value="processed",
                change_type="UPDATE",
                changed_by=processed_by,
                reason="Donation processing completed"
            )
            
            self.db.commit()
            self.db.refresh(donation)
            
            logger.info("Donation processed", donation_id=donation_id, processed_by=processed_by)
            return donation
            
        except Exception as e:
            logger.error("Failed to process donation", error=str(e))
            self.db.rollback()
            raise
    
    def _encrypt_cnic(self, cnic: str) -> str:
        """Encrypt CNIC for secure storage."""
        # In production, use proper encryption
        # For now, just hash it
        return hashlib.sha256(cnic.encode()).hexdigest()
    
    def _calculate_donation_hash(self, donation: Donation) -> str:
        """Calculate integrity hash for donation."""
        data = f"{donation.donor_name}{donation.amount}{donation.currency}{donation.donation_type.value}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _create_audit_record(
        self,
        donation_id: int,
        field_name: str,
        new_value: str,
        change_type: str,
        changed_by: int,
        old_value: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """Create an audit record for donation changes."""
        audit = DonationAudit(
            donation_id=donation_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type,
            changed_by=changed_by,
            reason=reason
        )
        self.db.add(audit)


class FraudDetectionService:
    """Service for fraud detection in donations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_donation(self, donation: Donation) -> Dict[str, Any]:
        """
        Analyze donation for potential fraud indicators.
        
        Args:
            donation: Donation to analyze
            
        Returns:
            dict: Fraud analysis results
        """
        try:
            flags = []
            score = 0.0
            
            # Check for duplicate donations
            if self._check_duplicate_donation(donation):
                flags.append("duplicate_donation")
                score += 0.3
            
            # Check for suspicious amounts
            if self._check_suspicious_amount(donation):
                flags.append("suspicious_amount")
                score += 0.2
            
            # Check for rapid submissions
            if self._check_rapid_submissions(donation):
                flags.append("rapid_submissions")
                score += 0.4
            
            # Check CNIC patterns
            if self._check_cnic_patterns(donation):
                flags.append("suspicious_cnic")
                score += 0.3
            
            # Check email patterns
            if self._check_email_patterns(donation):
                flags.append("suspicious_email")
                score += 0.2
            
            # Update donation with fraud analysis
            donation.fraud_score = min(score, 1.0)
            donation.fraud_flags = json.dumps(flags)
            donation.is_suspicious = score >= settings.fraud_detection_threshold
            
            logger.info(
                "Fraud analysis completed",
                donation_id=donation.id,
                fraud_score=donation.fraud_score,
                flags_count=len(flags),
                is_suspicious=donation.is_suspicious
            )
            
            return {
                "fraud_score": donation.fraud_score,
                "flags": flags,
                "is_suspicious": donation.is_suspicious,
                "recommendation": self._get_recommendation(score)
            }
            
        except Exception as e:
            logger.error("Fraud analysis failed", donation_id=donation.id, error=str(e))
            return {
                "fraud_score": 0.0,
                "flags": [],
                "is_suspicious": False,
                "recommendation": "manual_review"
            }
    
    def _check_duplicate_donation(self, donation: Donation) -> bool:
        """Check for potential duplicate donations."""
        # Look for similar donations in the last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        
        similar = self.db.query(Donation).filter(
            and_(
                Donation.id != donation.id,
                Donation.donor_name == donation.donor_name,
                Donation.amount == donation.amount,
                Donation.created_at >= since
            )
        ).first()
        
        return similar is not None
    
    def _check_suspicious_amount(self, donation: Donation) -> bool:
        """Check for suspicious donation amounts."""
        # Check for round numbers that might be fake
        if donation.amount % 1000 == 0 and donation.amount >= 10000:
            return True
        
        # Check for amounts that are unusually high for the donor type
        avg_amount = self.db.query(func.avg(Donation.amount)).filter(
            Donation.donation_type == donation.donation_type
        ).scalar()
        
        if avg_amount and donation.amount > avg_amount * 10:
            return True
        
        return False
    
    def _check_rapid_submissions(self, donation: Donation) -> bool:
        """Check for rapid successive submissions."""
        # Look for multiple donations from same email in last hour
        if not donation.donor_email:
            return False
        
        since = datetime.utcnow() - timedelta(hours=1)
        count = self.db.query(Donation).filter(
            and_(
                Donation.id != donation.id,
                Donation.donor_email == donation.donor_email,
                Donation.created_at >= since
            )
        ).count()
        
        return count >= 3
    
    def _check_cnic_patterns(self, donation: Donation) -> bool:
        """Check for suspicious CNIC patterns."""
        if not donation.donor_cnic:
            return False
        
        # Check for obviously fake CNICs (repeated digits, etc.)
        clean_cnic = donation.donor_cnic.replace('-', '')
        
        # Check for repeated digits
        if len(set(clean_cnic)) <= 3:
            return True
        
        # Check for sequential numbers
        if clean_cnic in ['1234567890123', '0123456789012']:
            return True
        
        return False
    
    def _check_email_patterns(self, donation: Donation) -> bool:
        """Check for suspicious email patterns."""
        if not donation.donor_email:
            return False
        
        # Check for temporary email domains
        temp_domains = ['10minutemail.com', 'guerrillamail.com', 'tempmail.org']
        domain = donation.donor_email.split('@')[-1].lower()
        
        return domain in temp_domains
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on fraud score."""
        if score >= 0.7:
            return "reject"
        elif score >= 0.3:
            return "manual_review"
        else:
            return "approve"