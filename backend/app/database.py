"""
Database configuration and session management for the Blessings Donation System.

This module sets up SQLAlchemy with MySQL, provides session management,
and includes database utilities.
"""

from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool
from typing import Generator
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

# SQLAlchemy engine configuration
engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,   # Recycle connections every hour
    echo=settings.debug  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


@event.listens_for(Pool, "connect")
def set_mysql_pragma(dbapi_connection, connection_record):
    """Set MySQL connection parameters for optimal performance."""
    with dbapi_connection.cursor() as cursor:
        # Set timezone to UTC
        cursor.execute("SET time_zone = '+00:00'")
        # Set SQL mode for strict data validation
        cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
        # Set charset to utf8mb4 for full Unicode support
        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        @app.get("/items/")
        async def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error("Database transaction failed", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables")
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (use with caution)."""
    logger.warning("Dropping all database tables")
    Base.metadata.drop_all(bind=engine)


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False


class DatabaseManager:
    """Database management utilities."""
    
    @staticmethod
    def get_table_info(table_name: str) -> dict:
        """Get information about a database table."""
        with engine.connect() as connection:
            result = connection.execute(f"DESCRIBE {table_name}")
            columns = result.fetchall()
            return {
                "table": table_name,
                "columns": [
                    {
                        "name": col[0],
                        "type": col[1],
                        "null": col[2] == "YES",
                        "key": col[3],
                        "default": col[4],
                        "extra": col[5]
                    }
                    for col in columns
                ]
            }
    
    @staticmethod
    def get_table_count(table_name: str) -> int:
        """Get row count for a table."""
        with engine.connect() as connection:
            result = connection.execute(f"SELECT COUNT(*) FROM {table_name}")
            return result.scalar()
    
    @staticmethod
    def backup_table(table_name: str, backup_name: str = None) -> str:
        """Create a backup of a table."""
        if not backup_name:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{table_name}_backup_{timestamp}"
        
        with engine.connect() as connection:
            connection.execute(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}")
        
        logger.info("Table backed up", original=table_name, backup=backup_name)
        return backup_name
    
    @staticmethod
    def get_database_stats() -> dict:
        """Get database statistics."""
        with engine.connect() as connection:
            # Get table sizes
            tables_query = """
            SELECT 
                TABLE_NAME,
                TABLE_ROWS,
                ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'SIZE_MB'
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC
            """
            
            result = connection.execute(tables_query)
            tables = result.fetchall()
            
            # Get database size
            db_size_query = """
            SELECT 
                ROUND(SUM((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'DB_SIZE_MB'
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            """
            
            db_size_result = connection.execute(db_size_query)
            db_size = db_size_result.scalar()
            
            return {
                "database_size_mb": db_size,
                "tables": [
                    {
                        "name": table[0],
                        "rows": table[1],
                        "size_mb": table[2]
                    }
                    for table in tables
                ]
            }


# Database health check for monitoring
def health_check() -> dict:
    """
    Perform database health check.
    
    Returns:
        dict: Health check results
    """
    try:
        start_time = time.time()
        
        with engine.connect() as connection:
            # Test basic connectivity
            connection.execute("SELECT 1")
            
            # Test write capability
            connection.execute("SELECT 1 INTO @test_var")
            
            # Get connection count
            result = connection.execute("SHOW STATUS LIKE 'Threads_connected'")
            connections = result.fetchone()[1]
            
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "connections": int(connections),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Import required modules for health check
import time
from datetime import datetime