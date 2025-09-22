"""
Admin API endpoints for distribution management and reporting
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime, timedelta
import logging
import io
import csv
import json

from app.database import get_db
from app.auth import get_current_admin_user
from app.models.user import User
from app.models.employee import Employee
from app.models.donation import Donation
from app.models.distribution import Distribution, DistributionBeneficiary, PickupSchedule
from app.schemas.distribution import (
    DistributionCreate, DistributionApprove, DistributionResponse,
    DistributionRunResponse, BeneficiaryResponse
)
from app.services.distribution_service import DistributionService
from app.tasks import send_pickup_notifications

logger = logging.getLogger(__name__)
router = APIRouter()
distribution_service = DistributionService()


@router.get("/distribution/run", response_model=DistributionRunResponse)
async def run_distribution(
    distribution_date: date = Query(..., description="Date for distribution (YYYY-MM-DD)"),
    max_beneficiaries: int = Query(100, ge=10, le=1000),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Run distribution algorithm to generate provisional list
    
    Query Parameters:
    - distribution_date: Date for the distribution (YYYY-MM-DD)
    - max_beneficiaries: Maximum number of beneficiaries to select
    
    Returns provisional distribution list with:
    - family_key: For family deduplication
    - eligibility_score: ML-based eligibility score
    - fraud_flag: Whether flagged by fraud detection
    
    Example:
    GET /api/admin/distribution/run?date=2024-01-15&max_beneficiaries=200
    """
    try:
        # Run distribution service
        result = await distribution_service.generate_distribution(
            db=db,
            distribution_date=distribution_date,
            max_beneficiaries=max_beneficiaries,
            created_by=current_user.id
        )
        
        logger.info(f"Distribution run completed: {result['distribution_id']} with {result['total_beneficiaries']} beneficiaries")
        
        return DistributionRunResponse(**result)
        
    except Exception as e:
        logger.error(f"Error running distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating distribution: {str(e)}"
        )


@router.post("/distribution/approve", response_model=DistributionResponse)
async def approve_distribution(
    approval_data: DistributionApprove,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Approve a distribution and trigger pickup scheduling
    
    Request Body:
    ```json
    {
        "distribution_run_id": 123,
        "notes": "Approved for January distribution",
        "send_notifications": true
    }
    ```
    
    This will:
    1. Mark distribution as approved
    2. Generate pickup schedules
    3. Send notifications to beneficiaries
    """
    # Get distribution
    distribution = db.query(Distribution).filter(
        Distribution.id == approval_data.distribution_run_id
    ).first()
    
    if not distribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Distribution not found"
        )
    
    if distribution.status != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Distribution is {distribution.status}, cannot approve"
        )
    
    try:
        # Approve distribution
        distribution.status = "approved"
        distribution.approved_by = current_user.id
        distribution.approved_at = datetime.utcnow()
        
        if approval_data.notes:
            distribution.notes = (distribution.notes or "") + f"\nApproval: {approval_data.notes}"
        
        # Generate pickup schedules
        schedules = await distribution_service.generate_pickup_schedules(
            db=db,
            distribution_id=distribution.id
        )
        
        db.commit()
        
        # Send notifications asynchronously
        if approval_data.send_notifications:
            send_pickup_notifications.delay(distribution.id)
        
        logger.info(f"Distribution {distribution.id} approved by {current_user.id}")
        
        return DistributionResponse.from_orm(distribution)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error approving distribution"
        )


@router.get("/reports/donations")
async def generate_donation_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    format: str = Query("csv", regex="^(csv|json)$"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Generate donation report in CSV or JSON format
    
    Query Parameters:
    - from_date: Start date (optional)
    - to_date: End date (optional)
    - format: Output format (csv or json)
    
    Example:
    GET /api/admin/reports/donations?from=2024-01-01&to=2024-01-31&format=csv
    """
    query = db.query(Donation)
    
    if from_date:
        query = query.filter(Donation.created_at >= from_date)
    
    if to_date:
        query = query.filter(Donation.created_at <= to_date + timedelta(days=1))
    
    donations = query.all()
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "ID", "Date", "Donor Name", "Email", "Type", 
                "Amount", "Currency", "Payment Method", "Verified", 
                "Blockchain Hash"
            ]
        )
        writer.writeheader()
        
        for donation in donations:
            writer.writerow({
                "ID": donation.id,
                "Date": donation.created_at.isoformat() if donation.created_at else "",
                "Donor Name": donation.donor_name if not donation.is_anonymous else "Anonymous",
                "Email": donation.donor_email or "",
                "Type": donation.donation_type.value if donation.donation_type else "",
                "Amount": donation.amount,
                "Currency": donation.currency,
                "Payment Method": donation.payment_method.value if donation.payment_method else "",
                "Verified": "Yes" if donation.is_verified else "No",
                "Blockchain Hash": donation.blockchain_hash or ""
            })
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=donations_report_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    
    else:  # JSON format
        data = []
        for donation in donations:
            data.append({
                "id": donation.id,
                "date": donation.created_at.isoformat() if donation.created_at else None,
                "donor_name": donation.donor_name if not donation.is_anonymous else "Anonymous",
                "email": donation.donor_email,
                "type": donation.donation_type.value if donation.donation_type else None,
                "amount": donation.amount,
                "currency": donation.currency,
                "payment_method": donation.payment_method.value if donation.payment_method else None,
                "verified": donation.is_verified,
                "blockchain_hash": donation.blockchain_hash
            })
        
        return {
            "report_date": datetime.now().isoformat(),
            "from_date": from_date.isoformat() if from_date else None,
            "to_date": to_date.isoformat() if to_date else None,
            "total_donations": len(data),
            "total_amount": sum(d["amount"] for d in data),
            "donations": data
        }


@router.get("/reports/beneficiaries")
async def generate_beneficiary_report(
    distribution_id: Optional[int] = None,
    format: str = Query("csv", regex="^(csv|json)$"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Generate beneficiary report for a distribution
    
    Query Parameters:
    - distribution_id: ID of the distribution (optional)
    - format: Output format (csv or json)
    """
    query = db.query(DistributionBeneficiary).join(Employee)
    
    if distribution_id:
        query = query.filter(DistributionBeneficiary.distribution_id == distribution_id)
    
    beneficiaries = query.all()
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Distribution ID", "Employee Name", "CNIC", "Grade",
                "Family Size", "Family Key", "Eligibility Score",
                "Fraud Flag", "Amount Allocated", "Pickup Completed"
            ]
        )
        writer.writeheader()
        
        for ben in beneficiaries:
            writer.writerow({
                "Distribution ID": ben.distribution_id,
                "Employee Name": ben.employee.name,
                "CNIC": f"*****-*******-{ben.employee.cnic[-4:]}",  # Masked
                "Grade": ben.employee.grade,
                "Family Size": ben.employee.family_size,
                "Family Key": ben.family_key,
                "Eligibility Score": round(ben.eligibility_score, 2) if ben.eligibility_score else 0,
                "Fraud Flag": "Yes" if ben.fraud_flag else "No",
                "Amount Allocated": ben.amount_allocated,
                "Pickup Completed": "Yes" if ben.pickup_completed else "No"
            })
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=beneficiaries_report_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    
    else:  # JSON format
        data = []
        for ben in beneficiaries:
            data.append({
                "distribution_id": ben.distribution_id,
                "employee_id": ben.employee_id,
                "employee_name": ben.employee.name,
                "cnic_masked": f"*****-*******-{ben.employee.cnic[-4:]}",
                "grade": ben.employee.grade,
                "family_size": ben.employee.family_size,
                "family_key": ben.family_key,
                "eligibility_score": round(ben.eligibility_score, 2) if ben.eligibility_score else 0,
                "fraud_flag": ben.fraud_flag,
                "amount_allocated": ben.amount_allocated,
                "pickup_completed": ben.pickup_completed
            })
        
        return {
            "report_date": datetime.now().isoformat(),
            "distribution_id": distribution_id,
            "total_beneficiaries": len(data),
            "total_amount": sum(d["amount_allocated"] for d in data if d["amount_allocated"]),
            "beneficiaries": data
        }


@router.get("/statistics/dashboard")
async def get_dashboard_statistics(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for admin panel
    """
    # Calculate date ranges
    today = datetime.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Donation statistics
    total_donations = db.query(Donation).count()
    monthly_donations = db.query(Donation).filter(
        Donation.created_at >= month_start
    ).count()
    
    total_amount = db.query(db.func.sum(Donation.amount)).scalar() or 0
    monthly_amount = db.query(db.func.sum(Donation.amount)).filter(
        Donation.created_at >= month_start
    ).scalar() or 0
    
    # Employee statistics
    total_employees = db.query(Employee).count()
    eligible_employees = db.query(Employee).filter(
        Employee.is_eligible == True
    ).count()
    
    # Distribution statistics
    total_distributions = db.query(Distribution).count()
    pending_distributions = db.query(Distribution).filter(
        Distribution.status == "pending_approval"
    ).count()
    
    # Recent donations
    recent_donations = db.query(Donation).order_by(
        Donation.created_at.desc()
    ).limit(10).all()
    
    return {
        "donations": {
            "total": total_donations,
            "monthly": monthly_donations,
            "total_amount": total_amount,
            "monthly_amount": monthly_amount
        },
        "employees": {
            "total": total_employees,
            "eligible": eligible_employees,
            "ineligible": total_employees - eligible_employees
        },
        "distributions": {
            "total": total_distributions,
            "pending": pending_distributions
        },
        "recent_donations": [
            {
                "id": d.id,
                "donor": d.donor_name if not d.is_anonymous else "Anonymous",
                "amount": d.amount,
                "type": d.donation_type.value if d.donation_type else None,
                "date": d.created_at.isoformat() if d.created_at else None
            }
            for d in recent_donations
        ]
    }