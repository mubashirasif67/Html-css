"""
Donation management routes.

Handles donation creation, listing, and receipt processing.
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import io
from ..database import get_db
from ..models import Donation, User
from ..schemas import DonationCreate, DonationResponse
from ..utils import generate_transaction_hash
from ..dependencies import get_current_user
from ..services.notification_service import notification_service
from ..tasks import process_ocr_task, send_donation_notification
from ..auth import create_access_token
import pandas as pd
import csv

router = APIRouter()


@router.post("/", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
def create_donation(
    donor_name: str = Form(...),
    donor_email: Optional[str] = Form(None),
    donor_cnic: Optional[str] = Form(None),
    amount: float = Form(...),
    donation_type: str = Form(...),
    receipt_image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new donation."""
    # Process receipt image if provided
    detected_amount = None
    confidence = None
    ocr_text = None

    if receipt_image:
        # Read image bytes
        image_bytes = receipt_image.file.read()

        # Run OCR task asynchronously
        ocr_result = process_ocr_task.delay(image_bytes)

        # For now, we'll process synchronously for simplicity
        # In production, you'd wait for the async result
        from ..services.ocr_service import ocr_service
        result = ocr_service.process_receipt(image_bytes)

        detected_amount = result.detected_amount
        confidence = result.confidence
        ocr_text = result.raw_text

        # If confidence is low, use detected amount as suggestion
        if confidence and confidence < 0.8:
            # In a real app, you'd prompt the user
            pass

    # Use detected amount if available and confidence is high
    final_amount = amount
    if detected_amount and confidence and confidence > 0.8:
        final_amount = detected_amount

    # Generate transaction hash for transparency
    donation_data = {
        "donor_name": donor_name,
        "amount": final_amount,
        "donation_type": donation_type
    }
    transaction_hash = generate_transaction_hash(donation_data)

    # Create donation
    new_donation = Donation(
        donor_id=current_user.id,
        donor_name=donor_name,
        donor_email=donor_email,
        donor_cnic=donor_cnic,
        amount=final_amount,
        donation_type=donation_type,
        detected_amount=detected_amount,
        confidence=confidence,
        ocr_text=ocr_text,
        transaction_hash=transaction_hash
    )

    db.add(new_donation)
    db.commit()
    db.refresh(new_donation)

    # Send notification asynchronously
    if donor_email:
        send_donation_notification.delay(new_donation.id)

    return DonationResponse.model_validate(new_donation)


@router.get("/", response_model=List[DonationResponse])
def list_donations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List donations for the current user."""
    donations = db.query(Donation).filter(Donation.donor_id == current_user.id).offset(skip).limit(limit).all()
    return [DonationResponse.model_validate(d) for d in donations]


@router.get("/all", response_model=List[DonationResponse])
def list_all_donations(
    current_user: User = Depends(get_current_user),  # Should be admin
    db: Session = Depends(get_db)
):
    """List all donations (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    donations = db.query(Donation).all()
    return [DonationResponse.model_validate(d) for d in donations]


@router.get("/export")
def export_donations(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export donations as CSV."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    query = db.query(Donation)

    if from_date:
        query = query.filter(Donation.created_at >= from_date)
    if to_date:
        query = query.filter(Donation.created_at <= to_date)

    donations = query.all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['ID', 'Donor Name', 'Donor Email', 'Amount', 'Type', 'Date', 'Transaction Hash'])
    for donation in donations:
        writer.writerow([
            donation.id,
            donation.donor_name,
            donation.donor_email or '',
            donation.amount,
            donation.donation_type.value,
            donation.created_at.isoformat(),
            donation.transaction_hash or ''
        ])

    output.seek(0)
    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=donations.csv"}
    )