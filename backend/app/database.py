"""
Database configuration and session management
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Configure session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    Yields database session and ensures it's closed after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables
    This is called on application startup
    """
    try:
        # Import all models to ensure they're registered
        from app.models import user, employee, donation, distribution, notification
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is working
    Used for health checks
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


# Event listener for connection checkout
@event.listens_for(engine, "connect")
def set_mysql_pragma(dbapi_connection, connection_record):
    """
    Set MySQL session variables for better performance
    """
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET sql_mode = 'TRADITIONAL'")
        cursor.execute("SET time_zone = '+00:00'")


# Event listener for handling disconnections
@event.listens_for(engine, "engine_connect")
def ping_connection(connection, branch):
    """
    Handle database disconnections gracefully
    """
    if branch:
        return
    
    try:
        connection.scalar("SELECT 1")
    except Exception:
        connection.invalidate()
        raise