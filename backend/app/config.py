"""
Configuration settings for the Blessings Distribution System.

This module loads environment variables and provides configuration
objects for the application, database, and external services.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    secret_key: str = Field(..., description="Secret key for JWT and general crypto")
    jwt_secret: str = Field(..., description="JWT signing secret")
    database_url: str = Field(..., description="Database connection URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    redis_url: str = Field(default="redis://localhost:6379/1", description="Redis URL for caching")
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_pass: str = Field(default="", description="SMTP password")
    twilio_sid: str = Field(default="", description="Twilio SID (optional)")
    twilio_auth_token: str = Field(default="", description="Twilio auth token (optional)")
    twilio_from: str = Field(default="", description="Twilio phone number (optional)")
    app_name: str = Field(default="Blessings Distribution System", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()