"""
Donation routes for the Blessings Donation System.

This module provides API endpoints for donation management,
OCR receipt processing, and donation analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog
import os
import aiofiles
from datetime import datetime, timedelta
import io
import csv

from ..database import get_db
from ..auth.routes import get_current_user, get_admin_user
from ..auth.models import User
from .schemas import (
    DonationCreateRequest, DonationUpdateRequest, DonationResponse,
    DonationListResponse, DonationStatsResponse, ReceiptUploadResponse,
    DonationNoteCreate, DonationNoteResponse, DonationAuditResponse,
    DonationExportRequest, DonationExportResponse, MessageResponse, ErrorResponse
)
from .models import Donation, DonationStatus, DonationType
from .services import DonationService, FraudDetectionService
from ..ocr.pipeline import OCRPipeline
from ..tasks import process_receipt_ocr, send_donation_receipt_email

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
async def create_donation(
    donation_data: DonationCreateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = None  # Optional for public donations
):
    """
    Create a new donation.
    
    This endpoint accepts donations from both authenticated users and anonymous donors.
    For anonymous donations, no authentication is required.
    """
    try:
        service = DonationService(db)
        
        # Validate that either amount is provided or receipt will be uploaded
        if not donation_data.amount and not donation_data.donor_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either donation amount or email for receipt processing is required"
            )
        
        # Create donation
        donation = service.create_donation(
            donation_data=donation_data,
            created_by=current_user.id if current_user else None
        )
        
        # Run fraud detection
        fraud_service = FraudDetectionService(db)
        fraud_analysis = fraud_service.analyze_donation(donation)
        
        # Update donation with fraud analysis
        db.commit()
        db.refresh(donation)
        
        # Send receipt email if email provided
        if donation.donor_email:
            send_donation_receipt_email.delay(donation.id)
        
        logger.info(
            "Donation created successfully",
            donation_id=donation.id,
            amount=donation.amount,
            fraud_score=donation.fraud_score
        )
        
        # Convert to response model
        response = DonationResponse.from_orm(donation)
        response.masked_cnic = donation.masked_cnic
        response.receipt_exists = donation.receipt_exists
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create donation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create donation"
        )


@router.post("/upload_receipt", response_model=ReceiptUploadResponse)
async def upload_receipt(
    file: UploadFile = File(...),
    donation_id: Optional[int] = Form(None),
    donor_name: Optional[str] = Form(None),
    donor_email: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload and process a donation receipt using OCR.
    
    This endpoint can either:
    1. Add a receipt to an existing donation (provide donation_id)
    2. Create a new donation from the receipt (provide donor details)
    """
    try:
        # Validate file type and size
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed"
            )
        
        # Read file content
        file_content = await file.read()
        
        if len(file_content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size too large. Maximum 10MB allowed."
            )
        
        # Save uploaded file
        upload_dir = "data/receipts"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        import uuid
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # Process with OCR
        ocr_pipeline = OCRPipeline()
        ocr_result = ocr_pipeline.process_image(file_path)
        
        # Handle existing donation or create new one
        service = DonationService(db)
        
        if donation_id:
            # Add receipt to existing donation
            donation = service.get_donation(donation_id)
            if not donation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Donation not found"
                )
            
            # Update donation with OCR results
            if ocr_result.detected_amount and not donation.amount:
                donation.amount = ocr_result.detected_amount
            
            donation.receipt_image_path = file_path
            donation.ocr_detected_amount = ocr_result.detected_amount
            donation.ocr_confidence = ocr_result.confidence
            donation.ocr_raw_text = ocr_result.raw_text
            donation.ocr_processed = True
            
        else:
            # Create new donation from receipt
            if not donor_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Donor name is required for new donations"
                )
            
            from .schemas import DonationCreateRequest
            donation_data = DonationCreateRequest(
                donor_name=donor_name,
                donor_email=donor_email,
                amount=ocr_result.detected_amount or 0.0
            )
            
            donation = service.create_donation(donation_data)
            donation.receipt_image_path = file_path
            donation.ocr_detected_amount = ocr_result.detected_amount
            donation.ocr_confidence = ocr_result.confidence
            donation.ocr_raw_text = ocr_result.raw_text
            donation.ocr_processed = True
        
        db.commit()
        db.refresh(donation)
        
        # Determine if manual review is required
        requires_manual_review = (
            ocr_result.confidence < 0.8 or
            not ocr_result.detected_amount or
            donation.is_suspicious
        )
        
        logger.info(
            "Receipt processed successfully",
            donation_id=donation.id,
            ocr_confidence=ocr_result.confidence,
            detected_amount=ocr_result.detected_amount,
            requires_review=requires_manual_review
        )
        
        return ReceiptUploadResponse(
            receipt_id=donation.id,
            ocr_result=ocr_result,
            suggested_amount=ocr_result.detected_amount,
            requires_manual_review=requires_manual_review
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Receipt upload failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process receipt"
        )


@router.get("/", response_model=DonationListResponse)
async def list_donations(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    donation_type: Optional[str] = Query(None, description="Filter by donation type"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    search: Optional[str] = Query(None, description="Search by donor name, email, or receipt number"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum amount filter"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum amount filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List donations with filtering and pagination.
    
    Requires authentication. Users can see all donations based on their role.
    """
    try:
        service = DonationService(db)
        
        donations, total_count, total_amount = service.list_donations(
            page=page,
            per_page=per_page,
            status=status,
            donation_type=donation_type,
            date_from=date_from,
            date_to=date_to,
            search=search,
            min_amount=min_amount,
            max_amount=max_amount
        )
        
        # Convert to response models
        donation_responses = []
        for donation in donations:
            response = DonationResponse.from_orm(donation)
            response.masked_cnic = donation.masked_cnic
            response.receipt_exists = donation.receipt_exists
            donation_responses.append(response)
        
        # Calculate pages
        pages = (total_count + per_page - 1) // per_page
        
        return DonationListResponse(
            donations=donation_responses,
            total=total_count,
            page=page,
            per_page=per_page,
            pages=pages,
            total_amount=total_amount
        )
        
    except Exception as e:
        logger.error("Failed to list donations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve donations"
        )


@router.get("/{donation_id}", response_model=DonationResponse)
async def get_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get donation by ID."""
    try:
        service = DonationService(db)
        donation = service.get_donation(donation_id)
        
        if not donation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )
        
        # Convert to response model
        response = DonationResponse.from_orm(donation)
        response.masked_cnic = donation.masked_cnic
        response.receipt_exists = donation.receipt_exists
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get donation", donation_id=donation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve donation"
        )


@router.put("/{donation_id}", response_model=DonationResponse)
async def update_donation(
    donation_id: int,
    donation_data: DonationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update donation by ID (Staff and Admin only)."""
    try:
        # Check permissions
        if not current_user.has_permission("donations:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DonationService(db)
        donation = service.update_donation(
            donation_id=donation_id,
            donation_data=donation_data,
            updated_by=current_user.id
        )
        
        if not donation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )
        
        # Convert to response model
        response = DonationResponse.from_orm(donation)
        response.masked_cnic = donation.masked_cnic
        response.receipt_exists = donation.receipt_exists
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update donation", donation_id=donation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update donation"
        )


@router.post("/{donation_id}/verify", response_model=DonationResponse)
async def verify_donation(
    donation_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify a donation (Staff and Admin only)."""
    try:
        # Check permissions
        if not current_user.has_permission("donations:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DonationService(db)
        donation = service.verify_donation(
            donation_id=donation_id,
            verified_by=current_user.id,
            notes=notes
        )
        
        if not donation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )
        
        # Convert to response model
        response = DonationResponse.from_orm(donation)
        response.masked_cnic = donation.masked_cnic
        response.receipt_exists = donation.receipt_exists
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to verify donation", donation_id=donation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify donation"
        )


@router.post("/{donation_id}/process", response_model=DonationResponse)
async def process_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process a donation (Admin only)."""
    try:
        # Check permissions
        if not current_user.has_permission("donations:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DonationService(db)
        donation = service.process_donation(
            donation_id=donation_id,
            processed_by=current_user.id
        )
        
        if not donation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )
        
        # Convert to response model
        response = DonationResponse.from_orm(donation)
        response.masked_cnic = donation.masked_cnic
        response.receipt_exists = donation.receipt_exists
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process donation", donation_id=donation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process donation"
        )


@router.get("/{donation_id}/receipt")
async def download_receipt(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download receipt image for a donation."""
    try:
        service = DonationService(db)
        donation = service.get_donation(donation_id)
        
        if not donation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )
        
        if not donation.receipt_image_path or not os.path.exists(donation.receipt_image_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receipt image not found"
            )
        
        return FileResponse(
            path=donation.receipt_image_path,
            filename=f"receipt_{donation_id}{os.path.splitext(donation.receipt_image_path)[1]}",
            media_type="image/jpeg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download receipt", donation_id=donation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download receipt"
        )


@router.post("/{donation_id}/notes", response_model=DonationNoteResponse)
async def add_donation_note(
    donation_id: int,
    note_data: DonationNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a note to a donation."""
    try:
        service = DonationService(db)
        
        # Check if donation exists
        donation = service.get_donation(donation_id)
        if not donation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )
        
        note = service.add_donation_note(
            donation_id=donation_id,
            note=note_data.note,
            note_type=note_data.note_type,
            is_internal=note_data.is_internal,
            created_by=current_user.id
        )
        
        return DonationNoteResponse.from_orm(note)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add donation note", donation_id=donation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add note"
        )


@router.get("/{donation_id}/notes", response_model=List[DonationNoteResponse])
async def get_donation_notes(
    donation_id: int,
    include_internal: bool = Query(True, description="Include internal notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notes for a donation."""
    try:
        service = DonationService(db)
        
        # Non-admin users can't see internal notes
        if not current_user.is_admin and include_internal:
            include_internal = False
        
        notes = service.get_donation_notes(donation_id, include_internal)
        return [DonationNoteResponse.from_orm(note) for note in notes]
        
    except Exception as e:
        logger.error("Failed to get donation notes", donation_id=donation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notes"
        )


@router.get("/{donation_id}/audit", response_model=List[DonationAuditResponse])
async def get_donation_audit(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)  # Admin only
):
    """Get audit trail for a donation (Admin only)."""
    try:
        service = DonationService(db)
        audit_records = service.get_donation_audit(donation_id)
        return [DonationAuditResponse.from_orm(record) for record in audit_records]
        
    except Exception as e:
        logger.error("Failed to get donation audit", donation_id=donation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit trail"
        )


@router.get("/stats/overview", response_model=DonationStatsResponse)
async def get_donation_stats(
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get donation statistics."""
    try:
        service = DonationService(db)
        stats = service.get_donation_statistics(date_from, date_to)
        
        # Convert recent donations to response models
        recent_donations = []
        for donation in stats["recent_donations"]:
            response = DonationResponse.from_orm(donation)
            response.masked_cnic = donation.masked_cnic
            response.receipt_exists = donation.receipt_exists
            recent_donations.append(response)
        
        return DonationStatsResponse(
            total_donations=stats["total_donations"],
            total_amount=stats["total_amount"],
            average_amount=stats["average_amount"],
            by_type=stats["by_type"],
            by_status=stats["by_status"],
            by_payment_method=stats["by_payment_method"],
            ocr_stats=stats["ocr_stats"],
            fraud_stats=stats["fraud_stats"],
            recent_donations=recent_donations
        )
        
    except Exception as e:
        logger.error("Failed to get donation statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get("/export/csv")
async def export_donations_csv(
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    donation_type: Optional[str] = Query(None, description="Type filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export donations to CSV format."""
    try:
        # Check permissions
        if not current_user.has_permission("reports:export"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DonationService(db)
        donations, _, _ = service.list_donations(
            page=1,
            per_page=10000,  # Large number to get all records
            status=status,
            donation_type=donation_type,
            date_from=date_from,
            date_to=date_to
        )
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        headers = [
            'ID', 'Donor Name', 'Email', 'Phone', 'Amount', 'Currency',
            'Type', 'Payment Method', 'Status', 'Receipt Number',
            'Created At', 'Processed At'
        ]
        writer.writerow(headers)
        
        # Write data
        for donation in donations:
            writer.writerow([
                donation.id,
                donation.donor_name,
                donation.donor_email or '',
                donation.donor_phone or '',
                donation.amount,
                donation.currency,
                donation.donation_type.value,
                donation.payment_method.value,
                donation.status.value,
                donation.receipt_number or '',
                donation.created_at.isoformat(),
                donation.processed_at.isoformat() if donation.processed_at else ''
            ])
        
        output.seek(0)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=donations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export donations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export donations"
        )