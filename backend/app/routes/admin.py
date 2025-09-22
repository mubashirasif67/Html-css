"""
Admin routes for system management.

Handles distribution generation, approval, reporting, and system administration.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import io
import csv
from ..database import get_db
from ..models import DistributionRun, Donation, Employee, User
from ..schemas import DistributionRunCreate, DistributionRunResponse
from ..dependencies import get_admin_user
from ..services.distribution_service import DistributionService
from ..services.notification_service import notification_service
from ..tasks import send_pickup_notifications

router = APIRouter()


@router.post("/distribution/run", response_model=DistributionRunResponse)
def generate_distribution(
    run_date: datetime = Query(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Generate a provisional distribution list."""
    try:
        # Calculate total budget from recent donations
        total_budget = db.query(Donation).filter(
            Donation.created_at >= datetime.now().replace(day=1)
        ).sum(Donation.amount) or 1000000  # Default if no donations

        distribution_service = DistributionService(db)
        distribution_run = distribution_service.generate_provisional_distribution(run_date, total_budget)

        return DistributionRunResponse.model_validate(distribution_run)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/distribution/runs", response_model=List[DistributionRunResponse])
def list_distribution_runs(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all distribution runs."""
    runs = db.query(DistributionRun).all()
    return [DistributionRunResponse.model_validate(run) for run in runs]


@router.post("/distribution/approve")
def approve_distribution(
    run_id: int = Query(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Approve a distribution run and send notifications."""
    run = db.query(DistributionRun).filter(DistributionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Distribution run not found")

    if run.status != "pending":
        raise HTTPException(status_code=400, detail="Run already processed")

    # Update status
    run.status = "approved"
    run.admin_id = current_user.id
    db.commit()

    # Send notifications asynchronously
    send_pickup_notifications.delay(run_id)

    return {"message": "Distribution approved and notifications sent"}


@router.get("/reports/donations")
def get_donations_report(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Generate donations report."""
    query = db.query(Donation)

    if from_date:
        query = query.filter(Donation.created_at >= from_date)
    if to_date:
        query = query.filter(Donation.created_at <= to_date)

    donations = query.all()

    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['ID', 'Donor Name', 'Email', 'Amount', 'Type', 'Date', 'Hash'])
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
            headers={"Content-Disposition": f"attachment; filename=donations_report_{from_date}_{to_date}.csv"}
        )

    # For Excel format, you'd use openpyxl
    return {"message": "Excel format not implemented yet"}


@router.get("/dashboard/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get dashboard summary statistics."""
    total_donations = db.query(Donation).count()
    total_amount = db.query(Donation).sum(Donation.amount) or 0
    total_employees = db.query(Employee).count()
    eligible_employees = db.query(Employee).filter(Employee.is_eligible == True).count()
    pending_distributions = db.query(DistributionRun).filter(DistributionRun.status == "pending").count()

    return {
        "total_donations": total_donations,
        "total_amount": total_amount,
        "total_employees": total_employees,
        "eligible_employees": eligible_employees,
        "pending_distributions": pending_distributions
    }