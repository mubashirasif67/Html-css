"""
Configuration settings for the application
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Blessings FYP System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "jwt-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "mysql+pymysql://blessings_user:blessings_pass@localhost:3306/blessings"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "Blessings Foundation <noreply@blessings.org>")
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    
    # SMS (Twilio)
    TWILIO_ENABLED: bool = os.getenv("TWILIO_ENABLED", "false").lower() == "true"
    TWILIO_SID: str = os.getenv("TWILIO_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM: str = os.getenv("TWILIO_FROM", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    
    # OCR
    OCR_CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.8"))
    OCR_MAX_FILE_SIZE_MB: int = int(os.getenv("OCR_MAX_FILE_SIZE_MB", "10"))
    
    # ML Models
    ML_MODEL_PATH: str = os.getenv("ML_MODEL_PATH", "/app/app/ml/models")
    ELIGIBILITY_MODEL_FILE: str = os.getenv("ELIGIBILITY_MODEL_FILE", "eligibility_model.joblib")
    FRAUD_MODEL_FILE: str = os.getenv("FRAUD_MODEL_FILE", "fraud_model.joblib")
    
    # File Upload
    UPLOAD_PATH: str = os.getenv("UPLOAD_PATH", "/app/uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf"]
    
    # CORS
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:8080,http://localhost:80"
    ).split(",")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Distribution
    MIN_BENEFICIARIES_PER_DISTRIBUTION: int = int(
        os.getenv("MIN_BENEFICIARIES_PER_DISTRIBUTION", "10")
    )
    MAX_PICKUP_SLOT_SIZE: int = int(os.getenv("MAX_PICKUP_SLOT_SIZE", "20"))
    PICKUP_SLOT_DURATION_MINUTES: int = int(os.getenv("PICKUP_SLOT_DURATION_MINUTES", "30"))
    
    # Feature Flags
    ENABLE_BLOCKCHAIN_RECEIPTS: bool = os.getenv(
        "ENABLE_BLOCKCHAIN_RECEIPTS", "false"
    ).lower() == "true"
    ENABLE_PAYMENT_GATEWAY: bool = os.getenv(
        "ENABLE_PAYMENT_GATEWAY", "false"
    ).lower() == "true"
    ENABLE_ADVANCED_FRAUD_DETECTION: bool = os.getenv(
        "ENABLE_ADVANCED_FRAUD_DETECTION", "true"
    ).lower() == "true"
    ENABLE_FAMILY_DEDUPLICATION: bool = os.getenv(
        "ENABLE_FAMILY_DEDUPLICATION", "true"
    ).lower() == "true"
    
    # Admin
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@blessings.org")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin@123456")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()