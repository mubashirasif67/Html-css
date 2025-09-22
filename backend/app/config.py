"""
Configuration settings for the Blessings Donation System.

This module handles all configuration settings using Pydantic BaseSettings
for type validation and environment variable loading.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation and environment variable loading."""
    
    # Application Settings
    app_name: str = "Blessings Donation System"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    api_version: str = "v1"
    
    # Security Settings
    secret_key: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    csrf_secret_key: str = ""
    
    # Database Settings
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis Settings
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Email Settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    email_from: str = ""
    
    # SMS Settings (Optional)
    twilio_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from: Optional[str] = None
    
    # Payment Settings (Optional)
    stripe_public_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # File Upload Settings
    max_upload_size: int = 10485760  # 10MB
    upload_folder: str = "data/uploads"
    static_folder: str = "data/static"
    receipt_folder: str = "data/receipts"
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:80"]
    
    # OCR Settings
    tesseract_config: str = "--oem 3 --psm 6"
    ocr_confidence_threshold: float = 0.8
    ocr_supported_formats: List[str] = ["jpg", "jpeg", "png", "pdf", "tiff"]
    
    # ML Model Settings
    eligibility_model_path: str = "app/ml/models/eligibility_model.joblib"
    fraud_model_path: str = "app/ml/models/fraud_model.joblib"
    model_confidence_threshold: float = 0.7
    fraud_detection_threshold: float = 0.3
    
    # Rate Limiting
    rate_limit_donations: str = "10/minute"
    rate_limit_uploads: str = "5/minute"
    rate_limit_auth: str = "5/minute"
    
    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security Headers
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:80"]
    
    # Monitoring (Optional)
    sentry_dsn: Optional[str] = None
    prometheus_enabled: bool = False
    
    # Development Settings
    reload_on_change: bool = True
    show_docs: bool = True
    enable_profiling: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator('allowed_origins', 'cors_origins', pre=True)
    def parse_origins(cls, v):
        """Parse comma-separated origins into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('ocr_supported_formats', pre=True)
    def parse_formats(cls, v):
        """Parse comma-separated formats into a list."""
        if isinstance(v, str):
            return [fmt.strip().lower() for fmt in v.split(',')]
        return v
    
    @validator('email_from')
    def set_email_from_default(cls, v, values):
        """Set default email_from if not provided."""
        if not v and 'smtp_user' in values:
            return f"Blessings Donation System <{values['smtp_user']}>"
        return v
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        return self.database_url.replace('+pymysql', '')
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def twilio_enabled(self) -> bool:
        """Check if Twilio SMS is configured."""
        return bool(self.twilio_sid and self.twilio_auth_token)
    
    @property
    def stripe_enabled(self) -> bool:
        """Check if Stripe payment is configured."""
        return bool(self.stripe_public_key and self.stripe_secret_key)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()


# Logging configuration
import logging
import structlog

def configure_logging():
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Initialize logging
configure_logging()
logger = structlog.get_logger(__name__)