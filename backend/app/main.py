"""
Main FastAPI application for the Blessings Donation System.

This module initializes the FastAPI app, configures middleware,
includes all routers, and sets up application lifecycle events.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog
import time
import os

from .config import settings
from .database import engine, check_database_connection, health_check
from .auth.routes import router as auth_router
from .donations.routes import router as donations_router
from .employees.routes import router as employees_router
from .admin.routes import router as admin_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Blessings Donation System", version=settings.app_version)
    
    # Check database connection
    if not check_database_connection():
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")
    
    # Create upload directories
    os.makedirs(settings.upload_folder, exist_ok=True)
    os.makedirs(settings.receipt_folder, exist_ok=True)
    os.makedirs("app/ml/models", exist_ok=True)
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Blessings Donation System")
    engine.dispose()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive donation management system with OCR capabilities and ML-powered eligibility assessment",
    docs_url="/docs" if settings.show_docs else None,
    redoc_url="/redoc" if settings.show_docs else None,
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*"] if settings.debug else ["localhost"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=round(process_time, 4)
        )
        
        return response
    
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "Request failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            process_time=round(process_time, 4)
        )
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
    )
    
    if settings.debug:
        # In debug mode, show detailed error
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        # In production, hide error details
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging."""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


# Health check endpoint
@app.get("/health")
async def health_check_endpoint():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Application health status
    """
    db_health = health_check()
    
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
        "timestamp": time.time(),
        "version": settings.app_version,
        "environment": settings.environment,
        "database": db_health
    }


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with basic application information.
    
    Returns:
        dict: Application information
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/docs" if settings.show_docs else None,
        "api_prefix": f"/api/{settings.api_version}"
    }


# API version info
@app.get(f"/api/{settings.api_version}")
async def api_info():
    """
    API version information.
    
    Returns:
        dict: API version details
    """
    return {
        "api_version": settings.api_version,
        "app_version": settings.app_version,
        "endpoints": {
            "auth": f"/api/{settings.api_version}/auth",
            "donations": f"/api/{settings.api_version}/donations",
            "employees": f"/api/{settings.api_version}/employees",
            "admin": f"/api/{settings.api_version}/admin"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


# Include routers
app.include_router(
    auth_router,
    prefix=f"/api/{settings.api_version}/auth",
    tags=["Authentication"]
)

app.include_router(
    donations_router,
    prefix=f"/api/{settings.api_version}/donations",
    tags=["Donations"]
)

app.include_router(
    employees_router,
    prefix=f"/api/{settings.api_version}/employees",
    tags=["Employees"]
)

app.include_router(
    admin_router,
    prefix=f"/api/{settings.api_version}/admin",
    tags=["Administration"]
)


# Mount static files (if directory exists)
if os.path.exists(settings.static_folder):
    app.mount("/static", StaticFiles(directory=settings.static_folder), name="static")


# Development endpoints (only in debug mode)
if settings.debug:
    
    @app.get("/debug/config")
    async def debug_config():
        """Debug endpoint to view configuration (sensitive values hidden)."""
        config_dict = settings.dict()
        
        # Hide sensitive values
        sensitive_keys = [
            'secret_key', 'jwt_secret', 'database_url', 'smtp_pass',
            'twilio_auth_token', 'stripe_secret_key', 'sentry_dsn'
        ]
        
        for key in sensitive_keys:
            if key in config_dict and config_dict[key]:
                config_dict[key] = "***hidden***"
        
        return config_dict
    
    @app.get("/debug/database")
    async def debug_database():
        """Debug endpoint for database information."""
        from .database import DatabaseManager
        
        try:
            stats = DatabaseManager.get_database_stats()
            return {
                "connection_status": "connected",
                "statistics": stats
            }
        except Exception as e:
            return {
                "connection_status": "error",
                "error": str(e)
            }


# Startup message
@app.on_event("startup")
async def startup_message():
    """Log startup message with configuration."""
    logger.info(
        "FastAPI application started",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
        database_configured=bool(settings.database_url),
        redis_configured=bool(settings.redis_url),
        smtp_configured=bool(settings.smtp_user),
        twilio_configured=settings.twilio_enabled,
        cors_origins=settings.cors_origins
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.reload_on_change,
        log_level=settings.log_level.lower()
    )