"""
Celery tasks for background processing
"""

from celery import Task
from app.celery_app import celery_app
import logging
from typing import Dict, Any
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.process_donation_receipt")
def process_donation_receipt(self: Task, donation_id: int) -> Dict[str, Any]:
    """
    Process donation receipt - send email and SMS notifications
    
    Args:
        donation_id: ID of the donation
    
    Returns:
        Status dictionary
    """
    logger.info(f"Processing receipt for donation {donation_id}")
    
    try:
        from app.database import SessionLocal
        from app.models.donation import Donation, DonationReceipt
        from app.services.notification_service import NotificationService
        
        db = SessionLocal()
        notification_service = NotificationService()
        
        # Get donation
        donation = db.query(Donation).filter(Donation.id == donation_id).first()
        if not donation:
            logger.error(f"Donation {donation_id} not found")
            return {"status": "error", "message": "Donation not found"}
        
        # Send email receipt
        if donation.donor_email:
            email_sent = notification_service.send_donation_receipt_email(
                donation.donor_email,
                donation.donor_name,
                donation.amount,
                donation.transaction_id
            )
            
            # Update receipt status
            receipt = db.query(DonationReceipt).filter(
                DonationReceipt.donation_id == donation_id
            ).first()
            if receipt:
                receipt.email_sent = email_sent
                receipt.email_sent_at = datetime.utcnow() if email_sent else None
        
        # Send SMS if phone number available
        if donation.donor_phone:
            sms_sent = notification_service.send_donation_receipt_sms(
                donation.donor_phone,
                donation.amount,
                donation.transaction_id
            )
            
            if receipt:
                receipt.sms_sent = sms_sent
                receipt.sms_sent_at = datetime.utcnow() if sms_sent else None
        
        db.commit()
        db.close()
        
        logger.info(f"Receipt processed for donation {donation_id}")
        return {
            "status": "success",
            "donation_id": donation_id,
            "email_sent": email_sent if donation.donor_email else False,
            "sms_sent": sms_sent if donation.donor_phone else False
        }
        
    except Exception as e:
        logger.error(f"Error processing receipt: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="app.tasks.send_pickup_notifications")
def send_pickup_notifications(self: Task, distribution_id: int) -> Dict[str, Any]:
    """
    Send pickup notifications to beneficiaries
    
    Args:
        distribution_id: ID of the distribution
    
    Returns:
        Status dictionary
    """
    logger.info(f"Sending pickup notifications for distribution {distribution_id}")
    
    try:
        from app.database import SessionLocal
        from app.models.distribution import Distribution, DistributionBeneficiary, PickupSchedule
        from app.models.employee import Employee
        from app.services.notification_service import NotificationService
        
        db = SessionLocal()
        notification_service = NotificationService()
        
        # Get distribution beneficiaries with schedules
        beneficiaries = db.query(DistributionBeneficiary).join(
            Employee
        ).filter(
            DistributionBeneficiary.distribution_id == distribution_id,
            DistributionBeneficiary.pickup_schedule_id.isnot(None)
        ).all()
        
        sent_count = 0
        failed_count = 0
        
        for ben in beneficiaries:
            try:
                # Get schedule details
                schedule = db.query(PickupSchedule).filter(
                    PickupSchedule.id == ben.pickup_schedule_id
                ).first()
                
                if not schedule:
                    continue
                
                # Send notification
                if ben.employee.mobile:
                    sent = notification_service.send_pickup_notification(
                        ben.employee.mobile,
                        ben.employee.name,
                        schedule.pickup_date,
                        schedule.start_time,
                        schedule.location
                    )
                    
                    if sent:
                        sent_count += 1
                    else:
                        failed_count += 1
                        
            except Exception as e:
                logger.error(f"Error sending notification to beneficiary {ben.id}: {e}")
                failed_count += 1
        
        # Update distribution status
        distribution = db.query(Distribution).filter(
            Distribution.id == distribution_id
        ).first()
        if distribution:
            distribution.status = "in_progress"
            distribution.started_at = datetime.utcnow()
        
        db.commit()
        db.close()
        
        logger.info(f"Pickup notifications sent: {sent_count} success, {failed_count} failed")
        
        return {
            "status": "success",
            "distribution_id": distribution_id,
            "sent": sent_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"Error sending pickup notifications: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="app.tasks.process_ocr")
def process_ocr(self: Task, image_path: str) -> Dict[str, Any]:
    """
    Process image with OCR in background
    
    Args:
        image_path: Path to the image file
    
    Returns:
        OCR results
    """
    logger.info(f"Processing OCR for image: {image_path}")
    
    try:
        from app.services.ocr_service import OCRService
        
        ocr_service = OCRService()
        result = ocr_service.process_receipt(image_path)
        
        logger.info(f"OCR completed: Amount={result.get('detected_amount')}")
        return result
        
    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "detected_amount": None,
            "confidence": 0.0
        }


@celery_app.task(bind=True, name="app.tasks.retrain_models")
def retrain_models(self: Task) -> Dict[str, Any]:
    """
    Retrain ML models with latest data
    
    Returns:
        Training status
    """
    logger.info("Starting model retraining...")
    
    try:
        import subprocess
        import sys
        
        # Run training scripts
        scripts = [
            "/app/app/ml/train_eligibility.py",
            "/app/app/ml/train_fraud.py"
        ]
        
        results = {}
        
        for script in scripts:
            logger.info(f"Running {script}")
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True
            )
            
            model_name = os.path.basename(script).replace("train_", "").replace(".py", "")
            results[model_name] = {
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr
            }
            
            if result.returncode != 0:
                logger.error(f"Training failed for {model_name}: {result.stderr}")
        
        logger.info("Model retraining completed")
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "models": results
        }
        
    except Exception as e:
        logger.error(f"Error retraining models: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@celery_app.task(bind=True, name="app.tasks.cleanup_old_files")
def cleanup_old_files(self: Task, days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old temporary files
    
    Args:
        days_old: Delete files older than this many days
    
    Returns:
        Cleanup status
    """
    logger.info(f"Cleaning up files older than {days_old} days")
    
    try:
        upload_dir = "/app/uploads"
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        deleted_count = 0
        
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            
            # Skip if not a file
            if not os.path.isfile(filepath):
                continue
            
            # Check file age
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_time < cutoff_date:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"Deleted old file: {filename}")
                except Exception as e:
                    logger.error(f"Error deleting {filename}: {e}")
        
        logger.info(f"Cleanup completed: {deleted_count} files deleted")
        
        return {
            "status": "success",
            "deleted": deleted_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@celery_app.task(bind=True, name="app.tasks.send_email")
def send_email(self: Task, to: str, subject: str, body: str) -> bool:
    """
    Send email notification
    
    Args:
        to: Recipient email
        subject: Email subject
        body: Email body
    
    Returns:
        Success status
    """
    from app.services.notification_service import NotificationService
    
    notification_service = NotificationService()
    return notification_service.send_email(to, subject, body)


@celery_app.task(bind=True, name="app.tasks.send_sms")
def send_sms(self: Task, to: str, message: str) -> bool:
    """
    Send SMS notification
    
    Args:
        to: Recipient phone number
        message: SMS message
    
    Returns:
        Success status
    """
    from app.services.notification_service import NotificationService
    
    notification_service = NotificationService()
    return notification_service.send_sms(to, message)