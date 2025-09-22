"""
Donation management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging
import os
import uuid
from datetime import datetime, timedelta

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.donation import Donation, DonationReceipt
from app.schemas.donation import (
    DonationCreate, DonationResponse, DonationListResponse,
    OCRResponse
)
from app.services.ocr_service import OCRService
from app.config import settings
from app.tasks import process_donation_receipt

logger = logging.getLogger(__name__)
router = APIRouter()
ocr_service = OCRService()


@router.post("/", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
async def create_donation(
    donation_data: DonationCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = None
):
    """
    Create a new donation
    
    Request Body:
    ```json
    {
        "donor_name": "Muhammad Ali",
        "donor_email": "ali@example.com",
        "donor_phone": "+923001234567",
        "donor_cnic": "12345-1234567-1",
        "donation_type": "zakat",
        "amount": 10000.0,
        "currency": "PKR",
        "payment_method": "bank_transfer",
        "is_anonymous": false,
        "notes": "For Ramadan distribution"
    }
    ```
    """
    # Create donation
    donation = Donation(**donation_data.dict())
    
    # Link to user if authenticated
    if current_user:
        donation.donor_id = current_user.id
    
    # Generate transaction ID
    donation.transaction_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    try:
        db.add(donation)
        db.commit()
        
        # Generate blockchain hash
        donation.generate_blockchain_hash()
        db.commit()
        
        db.refresh(donation)
        
        # Create receipt
        receipt = DonationReceipt(donation_id=donation.id)
        receipt.generate_receipt_number()
        db.add(receipt)
        db.commit()
        
        # Queue receipt processing (email/SMS)
        process_donation_receipt.delay(donation.id)
        
        logger.info(f"Donation created: {donation.id} - Amount: {donation.amount}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating donation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating donation"
        )
    
    return DonationResponse.from_orm(donation)


@router.post("/upload_receipt", response_model=OCRResponse)
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a donation receipt using OCR
    
    Request:
    - Form-data with 'file' field containing image (jpg, jpeg, png)
    - Max file size: 10MB
    
    Returns:
    ```json
    {
        "detected_amount": 5000.0,
        "confidence": 0.92,
        "currency": "PKR",
        "raw_text": "Receipt\\nAmount: Rs 5,000",
        "boxes": [...],
        "processing_time": 1.23,
        "requires_manual_verification": false
    }
    ```
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Check file size
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > settings.OCR_MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds {settings.OCR_MAX_FILE_SIZE_MB}MB limit"
        )
    
    # Save file temporarily
    temp_filename = f"{uuid.uuid4().hex}_{file.filename}"
    temp_path = os.path.join(settings.UPLOAD_PATH, temp_filename)
    
    try:
        os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(contents)
        
        # Process with OCR
        result = await ocr_service.process_receipt(temp_path)
        
        # Determine if manual verification is needed
        result["requires_manual_verification"] = (
            result["confidence"] < settings.OCR_CONFIDENCE_THRESHOLD
        )
        
        logger.info(f"OCR processed receipt: Amount={result.get('detected_amount')}, Confidence={result.get('confidence')}")
        
        return OCRResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing receipt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing receipt"
        )
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/", response_model=DonationListResponse)
async def list_donations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    donation_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    is_verified: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List donations with filters and pagination
    
    Query Parameters:
    - page: Page number
    - per_page: Items per page
    - donation_type: Filter by type (zakat, sadaqah, general)
    - from_date: Start date filter
    - to_date: End date filter
    - min_amount: Minimum amount filter
    - max_amount: Maximum amount filter
    - is_verified: Verification status filter
    """
    query = db.query(Donation)
    
    # Apply filters
    if donation_type:
        query = query.filter(Donation.donation_type == donation_type)
    
    if from_date:
        query = query.filter(Donation.created_at >= from_date)
    
    if to_date:
        query = query.filter(Donation.created_at <= to_date)
    
    if min_amount is not None:
        query = query.filter(Donation.amount >= min_amount)
    
    if max_amount is not None:
        query = query.filter(Donation.amount <= max_amount)
    
    if is_verified is not None:
        query = query.filter(Donation.is_verified == is_verified)
    
    # Get total count and sum
    total = query.count()
    total_amount = query.with_entities(db.func.sum(Donation.amount)).scalar() or 0.0
    
    # Apply pagination
    offset = (page - 1) * per_page
    donations = query.order_by(Donation.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Calculate pagination info
    pages = (total + per_page - 1) // per_page
    
    return DonationListResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        total_amount=total_amount,
        items=[DonationResponse.from_orm(d) for d in donations]
    )


@router.get("/{donation_id}", response_model=DonationResponse)
async def get_donation(
    donation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get donation details by ID
    """
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )
    
    return DonationResponse.from_orm(donation)


@router.post("/{donation_id}/verify", response_model=DonationResponse)
async def verify_donation(
    donation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify a donation (Staff/Admin only)
    """
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to verify donations"
        )
    
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )
    
    donation.is_verified = True
    donation.verified_by = current_user.id
    donation.verification_date = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(donation)
        
        logger.info(f"Donation {donation_id} verified by user {current_user.id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error verifying donation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying donation"
        )
    
    return DonationResponse.from_orm(donation)