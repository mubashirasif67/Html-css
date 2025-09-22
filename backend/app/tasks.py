"""
Celery tasks for the Blessings Donation System.

This module contains background tasks for OCR processing, email notifications,
data cleanup, and system maintenance.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import structlog

from .celery_app import celery_app
from .database import SessionLocal
from .config import settings
from .ocr.pipeline import OCRPipeline
from .donations.models import Donation, DonationReceipt, DonationStats
from .donations.services import DonationService, FraudDetectionService
from .auth.models import RefreshToken
from .auth.utils import cleanup_expired_tokens as cleanup_auth_tokens
from .notifications.email import EmailService
from .notifications.sms import SMSService

logger = structlog.get_logger(__name__)


def get_db_session():
    """Get database session for tasks."""
    return SessionLocal()


@celery_app.task(bind=True, max_retries=3)
def process_receipt_ocr(self, receipt_path: str, donation_id: int):
    """
    Process receipt image with OCR and update donation.
    
    Args:
        receipt_path: Path to the receipt image
        donation_id: ID of the donation to update
    """
    try:
        logger.info("Starting OCR processing", receipt_path=receipt_path, donation_id=donation_id)
        
        # Initialize OCR pipeline
        ocr_pipeline = OCRPipeline()
        
        # Process the image
        ocr_result = ocr_pipeline.process_image(receipt_path)
        
        # Update donation with OCR results
        db = get_db_session()
        try:
            donation = db.query(Donation).filter(Donation.id == donation_id).first()
            if not donation:
                raise ValueError(f"Donation {donation_id} not found")
            
            # Update donation fields
            donation.ocr_detected_amount = ocr_result.detected_amount
            donation.ocr_confidence = ocr_result.confidence
            donation.ocr_raw_text = ocr_result.raw_text
            donation.ocr_processed = True
            
            # If no amount was set and OCR detected one, use it
            if not donation.amount and ocr_result.detected_amount:
                donation.amount = ocr_result.detected_amount
            
            # Create receipt record
            receipt = DonationReceipt(
                donation_id=donation_id,
                original_filename=os.path.basename(receipt_path),
                file_path=receipt_path,
                file_size=os.path.getsize(receipt_path),
                mime_type="image/jpeg",  # Assume JPEG for now
                file_hash=_calculate_file_hash(receipt_path),
                ocr_text=ocr_result.raw_text,
                ocr_confidence=ocr_result.confidence,
                detected_amounts=str([ocr_result.detected_amount]) if ocr_result.detected_amount else "[]",
                best_amount=ocr_result.detected_amount,
                best_currency="PKR",
                text_boxes=str(ocr_result.text_boxes),
                processed=True,
                processing_time=ocr_result.processing_time
            )
            
            db.add(receipt)
            db.commit()
            
            logger.info(
                "OCR processing completed successfully",
                donation_id=donation_id,
                detected_amount=ocr_result.detected_amount,
                confidence=ocr_result.confidence
            )
            
            return {
                "donation_id": donation_id,
                "detected_amount": ocr_result.detected_amount,
                "confidence": ocr_result.confidence,
                "processing_time": ocr_result.processing_time
            }
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error("OCR processing failed", error=str(e), donation_id=donation_id)
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))  # Exponential backoff
        
        # Mark as failed in database
        db = get_db_session()
        try:
            donation = db.query(Donation).filter(Donation.id == donation_id).first()
            if donation:
                donation.ocr_processed = True  # Mark as processed even if failed
                donation.ocr_confidence = 0.0
                donation.ocr_raw_text = f"OCR processing failed: {str(e)}"
                db.commit()
        finally:
            db.close()
        
        raise


@celery_app.task(bind=True, max_retries=3)
def send_donation_receipt_email(self, donation_id: int):
    """
    Send donation receipt email to donor.
    
    Args:
        donation_id: ID of the donation
    """
    try:
        logger.info("Sending donation receipt email", donation_id=donation_id)
        
        db = get_db_session()
        try:
            donation = db.query(Donation).filter(Donation.id == donation_id).first()
            if not donation:
                raise ValueError(f"Donation {donation_id} not found")
            
            if not donation.donor_email:
                logger.warning("No email address for donation", donation_id=donation_id)
                return {"status": "skipped", "reason": "no_email"}
            
            # Initialize email service
            email_service = EmailService()
            
            # Send receipt email
            result = email_service.send_donation_receipt(
                to_email=donation.donor_email,
                donor_name=donation.donor_name,
                amount=donation.amount,
                currency=donation.currency,
                donation_type=donation.donation_type.value,
                receipt_number=donation.receipt_number,
                donation_date=donation.created_at
            )
            
            logger.info("Donation receipt email sent successfully", donation_id=donation_id)
            return result
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error("Failed to send donation receipt email", error=str(e), donation_id=donation_id)
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise


@celery_app.task(bind=True, max_retries=2)
def analyze_donation_fraud(self, donation_id: int):
    """
    Analyze donation for fraud indicators.
    
    Args:
        donation_id: ID of the donation to analyze
    """
    try:
        logger.info("Analyzing donation for fraud", donation_id=donation_id)
        
        db = get_db_session()
        try:
            donation = db.query(Donation).filter(Donation.id == donation_id).first()
            if not donation:
                raise ValueError(f"Donation {donation_id} not found")
            
            # Initialize fraud detection service
            fraud_service = FraudDetectionService(db)
            
            # Analyze donation
            fraud_analysis = fraud_service.analyze_donation(donation)
            
            # Update donation with results
            db.commit()
            
            logger.info(
                "Fraud analysis completed",
                donation_id=donation_id,
                fraud_score=fraud_analysis["fraud_score"],
                is_suspicious=fraud_analysis["is_suspicious"]
            )
            
            return fraud_analysis
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error("Fraud analysis failed", error=str(e), donation_id=donation_id)
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise


@celery_app.task
def cleanup_expired_tokens():
    """Clean up expired refresh tokens."""
    try:
        logger.info("Starting token cleanup")
        
        db = get_db_session()
        try:
            count = cleanup_auth_tokens(db)
            logger.info("Token cleanup completed", tokens_cleaned=count)
            return {"tokens_cleaned": count}
        finally:
            db.close()
    
    except Exception as e:
        logger.error("Token cleanup failed", error=str(e))
        raise


@celery_app.task
def generate_donation_stats():
    """Generate daily donation statistics."""
    try:
        logger.info("Generating donation statistics")
        
        db = get_db_session()
        try:
            # Get today's date
            today = datetime.utcnow().date()
            
            # Check if stats already exist for today
            existing_stats = db.query(DonationStats).filter(
                DonationStats.stat_date == today,
                DonationStats.period_type == "daily"
            ).first()
            
            if existing_stats:
                logger.info("Statistics already exist for today")
                return {"status": "skipped", "reason": "already_exists"}
            
            # Calculate statistics
            service = DonationService(db)
            stats = service.get_donation_statistics(
                date_from=datetime.combine(today, datetime.min.time()),
                date_to=datetime.combine(today, datetime.max.time())
            )
            
            # Create stats record
            daily_stats = DonationStats(
                stat_date=today,
                period_type="daily",
                total_donations=stats["total_donations"],
                total_amount=stats["total_amount"],
                average_amount=stats["average_amount"],
                zakat_count=stats["by_type"].get("zakat", {}).get("count", 0),
                zakat_amount=stats["by_type"].get("zakat", {}).get("amount", 0.0),
                sadaqah_count=stats["by_type"].get("sadaqah", {}).get("count", 0),
                sadaqah_amount=stats["by_type"].get("sadaqah", {}).get("amount", 0.0),
                general_count=stats["by_type"].get("general", {}).get("count", 0),
                general_amount=stats["by_type"].get("general", {}).get("amount", 0.0),
                pending_count=stats["by_status"].get("pending", 0),
                verified_count=stats["by_status"].get("verified", 0),
                processed_count=stats["by_status"].get("processed", 0),
                rejected_count=stats["by_status"].get("rejected", 0),
                ocr_processed_count=stats["ocr_stats"]["total_processed"],
                ocr_success_rate=stats["ocr_stats"]["success_rate"],
                suspicious_count=stats["fraud_stats"]["total_flagged"],
                fraud_detected_count=stats["fraud_stats"].get("confirmed_fraud", 0)
            )
            
            db.add(daily_stats)
            db.commit()
            
            logger.info("Daily statistics generated successfully")
            return {"status": "completed", "total_donations": stats["total_donations"]}
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error("Failed to generate donation statistics", error=str(e))
        raise


@celery_app.task
def send_weekly_reports():
    """Send weekly summary reports to administrators."""
    try:
        logger.info("Sending weekly reports")
        
        db = get_db_session()
        try:
            # Get weekly statistics
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            service = DonationService(db)
            stats = service.get_donation_statistics(date_from=week_ago)
            
            # Get admin users
            from .auth.models import User, UserRole
            admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
            
            if not admins:
                logger.warning("No admin users found for weekly reports")
                return {"status": "skipped", "reason": "no_admins"}
            
            # Initialize email service
            email_service = EmailService()
            
            # Send report to each admin
            sent_count = 0
            for admin in admins:
                if admin.donor_email:
                    try:
                        email_service.send_weekly_report(
                            to_email=admin.email,
                            admin_name=admin.name,
                            stats=stats,
                            period_start=week_ago,
                            period_end=datetime.utcnow()
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.error("Failed to send weekly report to admin", 
                                   admin_id=admin.id, error=str(e))
            
            logger.info("Weekly reports sent", sent_count=sent_count)
            return {"status": "completed", "reports_sent": sent_count}
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error("Failed to send weekly reports", error=str(e))
        raise


@celery_app.task
def cleanup_old_files():
    """Clean up old uploaded files and temporary files."""
    try:
        logger.info("Starting file cleanup")
        
        # Clean up files older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        cleaned_files = 0
        total_size = 0
        
        # Clean up receipt images for processed donations
        db = get_db_session()
        try:
            old_receipts = db.query(DonationReceipt).filter(
                DonationReceipt.created_at < cutoff_date,
                DonationReceipt.processed == True
            ).all()
            
            for receipt in old_receipts:
                if os.path.exists(receipt.file_path):
                    try:
                        file_size = os.path.getsize(receipt.file_path)
                        os.remove(receipt.file_path)
                        cleaned_files += 1
                        total_size += file_size
                        logger.debug("Cleaned up old receipt file", file_path=receipt.file_path)
                    except Exception as e:
                        logger.warning("Failed to delete file", file_path=receipt.file_path, error=str(e))
        
        finally:
            db.close()
        
        # Clean up temporary files
        temp_dirs = ["data/temp", "data/processed"]
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = datetime.utcnow() - datetime.fromtimestamp(os.path.getctime(file_path))
                        if file_age > timedelta(days=1):  # Clean files older than 1 day
                            try:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                cleaned_files += 1
                                total_size += file_size
                            except Exception as e:
                                logger.warning("Failed to delete temp file", file_path=file_path, error=str(e))
        
        logger.info("File cleanup completed", 
                   files_cleaned=cleaned_files, 
                   total_size_mb=total_size / (1024 * 1024))
        
        return {
            "status": "completed",
            "files_cleaned": cleaned_files,
            "total_size_bytes": total_size
        }
    
    except Exception as e:
        logger.error("File cleanup failed", error=str(e))
        raise


@celery_app.task
def health_check_services():
    """Perform health checks on external services."""
    try:
        logger.info("Performing service health checks")
        
        results = {}
        
        # Check database
        try:
            from .database import check_database_connection
            results["database"] = {
                "status": "healthy" if check_database_connection() else "unhealthy",
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            results["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
        
        # Check email service
        try:
            email_service = EmailService()
            results["email"] = {
                "status": "healthy" if email_service.test_connection() else "unhealthy",
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            results["email"] = {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
        
        # Check SMS service
        try:
            sms_service = SMSService()
            results["sms"] = {
                "status": "healthy" if sms_service.test_connection() else "unhealthy",
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            results["sms"] = {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
        
        # Log unhealthy services
        unhealthy_services = [name for name, status in results.items() 
                            if status["status"] == "unhealthy"]
        
        if unhealthy_services:
            logger.warning("Unhealthy services detected", services=unhealthy_services)
            
            # Send alert to admins for critical services
            if "database" in unhealthy_services:
                send_admin_alert.delay(
                    subject="Critical: Database Health Check Failed",
                    message="Database connectivity check failed. Immediate attention required.",
                    level="critical"
                )
        
        logger.info("Service health checks completed", 
                   healthy_count=len([s for s in results.values() if s["status"] == "healthy"]),
                   total_services=len(results))
        
        return results
    
    except Exception as e:
        logger.error("Service health check failed", error=str(e))
        raise


@celery_app.task(bind=True, max_retries=3)
def send_admin_alert(self, subject: str, message: str, level: str = "info"):
    """
    Send alert notification to administrators.
    
    Args:
        subject: Alert subject
        message: Alert message
        level: Alert level (info, warning, error, critical)
    """
    try:
        logger.info("Sending admin alert", subject=subject, level=level)
        
        db = get_db_session()
        try:
            # Get admin users
            from .auth.models import User, UserRole
            admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
            
            if not admins:
                logger.warning("No admin users found for alert")
                return {"status": "skipped", "reason": "no_admins"}
            
            # Initialize notification services
            email_service = EmailService()
            sms_service = SMSService()
            
            sent_emails = 0
            sent_sms = 0
            
            for admin in admins:
                # Send email alert
                if admin.email:
                    try:
                        email_service.send_admin_alert(
                            to_email=admin.email,
                            admin_name=admin.name,
                            subject=subject,
                            message=message,
                            level=level
                        )
                        sent_emails += 1
                    except Exception as e:
                        logger.error("Failed to send email alert to admin", 
                                   admin_id=admin.id, error=str(e))
                
                # Send SMS for critical alerts
                if level == "critical" and admin.phone and sms_service.is_configured():
                    try:
                        sms_service.send_admin_alert(
                            to_phone=admin.phone,
                            message=f"CRITICAL: {subject} - {message[:100]}"
                        )
                        sent_sms += 1
                    except Exception as e:
                        logger.error("Failed to send SMS alert to admin", 
                                   admin_id=admin.id, error=str(e))
            
            logger.info("Admin alerts sent", 
                       emails_sent=sent_emails, 
                       sms_sent=sent_sms)
            
            return {
                "status": "completed",
                "emails_sent": sent_emails,
                "sms_sent": sent_sms
            }
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error("Failed to send admin alert", error=str(e))
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise


def _calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    import hashlib
    
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()