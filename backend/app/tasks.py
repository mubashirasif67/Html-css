"""
Celery tasks for background processing.

This module defines tasks for OCR processing, sending notifications,
training ML models, and other heavy operations.
"""
from celery import shared_task
from sqlalchemy.orm import Session
from .database import SessionLocal
from .services.ocr_service import ocr_service
from .services.notification_service import notification_service
from .services.distribution_service import DistributionService
from .services.eligibility_service import eligibility_service
from .services.fraud_service import fraud_service
from .models import Donation, DistributionRun, Employee, User
from .utils import generate_transaction_hash
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task
def process_ocr_task(image_bytes: bytes) -> dict:
    """Task to process OCR on receipt image."""
    try:
        result = ocr_service.process_receipt(image_bytes)
        return result.dict()
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        return {"error": str(e)}


@shared_task
def send_donation_notification(donation_id: int) -> bool:
    """Task to send donation receipt notification."""
    db = SessionLocal()
    try:
        donation = db.query(Donation).filter(Donation.id == donation_id).first()
        if donation and donation.donor_email:
            success = notification_service.send_donation_receipt({
                "id": donation.id,
                "donor_name": donation.donor_name,
                "donor_email": donation.donor_email,
                "amount": donation.amount,
                "currency": donation.currency,
                "donation_type": donation.donation_type.value,
                "transaction_hash": donation.transaction_hash,
                "created_at": donation.created_at.isoformat()
            })
            return success
        return False
    except Exception as e:
        logger.error(f"Error sending donation notification: {e}")
        return False
    finally:
        db.close()


@shared_task
def send_pickup_notifications(run_id: int) -> bool:
    """Task to send pickup notifications for a distribution run."""
    db = SessionLocal()
    try:
        run = db.query(DistributionRun).filter(DistributionRun.id == run_id).first()
        if not run:
            return False

        distributions = db.query(Distribution).filter(Distribution.run_id == run_id).all()
        success_count = 0

        for distribution in distributions:
            employee = db.query(Employee).filter(Employee.id == distribution.employee_id).first()
            if employee:
                success = notification_service.send_pickup_notification({
                    "name": employee.name,
                    "mobile": employee.mobile,
                    "amount": distribution.amount,
                    "user": employee.user
                }, distribution.pickup_slot)

                if success:
                    distribution.notification_sent = True
                    success_count += 1

        db.commit()
        logger.info(f"Sent {success_count}/{len(distributions)} pickup notifications")
        return success_count > 0

    except Exception as e:
        logger.error(f"Error sending pickup notifications: {e}")
        return False
    finally:
        db.close()


@shared_task
def train_eligibility_model() -> bool:
    """Task to retrain the eligibility model with latest data."""
    try:
        from ml.train_eligibility import train_and_save_model
        train_and_save_model()
        # Reload the model in the service
        eligibility_service.load_model()
        logger.info("Eligibility model retrained successfully")
        return True
    except Exception as e:
        logger.error(f"Error training eligibility model: {e}")
        return False


@shared_task
def train_fraud_model() -> bool:
    """Task to retrain the fraud detection model."""
    try:
        from ml.train_fraud import train_and_save_model
        train_and_save_model()
        # Reload the model in the service
        fraud_service.load_model()
        logger.info("Fraud model retrained successfully")
        return True
    except Exception as e:
        logger.error(f"Error training fraud model: {e}")
        return False


@shared_task
def generate_monthly_report(month: int, year: int) -> str:
    """Task to generate monthly donation report."""
    db = SessionLocal()
    try:
        from datetime import datetime
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import os

        start_date = datetime(year, month, 1)
        end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

        donations = db.query(Donation).filter(
            Donation.created_at >= start_date,
            Donation.created_at < end_date
        ).all()

        # Generate PDF report
        filename = f"monthly_report_{year}_{month:02d}.pdf"
        filepath = f"/tmp/{filename}"

        c = canvas.Canvas(filepath, pagesize=letter)
        c.drawString(100, 750, f"Monthly Donation Report - {month}/{year}")
        c.drawString(100, 730, f"Total Donations: {len(donations)}")

        y = 700
        for donation in donations[:50]:  # Limit to first 50 for readability
            c.drawString(100, y, f"{donation.donor_name}: {donation.amount} {donation.currency}")
            y -= 20

        c.save()

        logger.info(f"Generated monthly report: {filename}")
        return filename

    except Exception as e:
        logger.error(f"Error generating monthly report: {e}")
        return ""
    finally:
        db.close()