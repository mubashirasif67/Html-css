"""
Main FastAPI application
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import sys

from app.config import settings
from app.database import init_db, check_db_connection
from app.api import auth, employees, donations, admin, feedback

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Comprehensive charity management system with OCR and ML capabilities",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "body": exc.body if settings.DEBUG else None
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": type(exc).__name__
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting up Blessings FYP System...")
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
        
        # Check database connection
        if not check_db_connection():
            logger.error("Database connection check failed")
            sys.exit(1)
        
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        sys.exit(1)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Blessings FYP System...")


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Status of the application and its dependencies
    """
    db_status = check_db_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_status else "disconnected",
        "features": {
            "ocr": True,
            "ml": settings.ENABLE_ADVANCED_FRAUD_DETECTION,
            "blockchain": settings.ENABLE_BLOCKCHAIN_RECEIPTS,
            "payment_gateway": settings.ENABLE_PAYMENT_GATEWAY,
            "email": settings.EMAIL_ENABLED,
            "sms": settings.TWILIO_ENABLED,
        }
    }


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint
    
    Returns:
        Welcome message and API information
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "documentation": "/docs",
        "api_spec": "/openapi.json",
        "health": "/health"
    }


# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(donations.router, prefix="/api/donations", tags=["Donations"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])


# API documentation customization
@app.get("/api", tags=["System"])
async def api_info():
    """
    API information endpoint
    
    Returns:
        Available API endpoints and their descriptions
    """
    return {
        "version": "1.0.0",
        "endpoints": {
            "/api/auth": "Authentication endpoints (register, login, refresh)",
            "/api/employees": "Employee management endpoints",
            "/api/donations": "Donation management and OCR processing",
            "/api/admin": "Administrative functions (distributions, reports)",
            "/api/feedback": "Feedback and sentiment analysis"
        },
        "documentation": {
            "interactive": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )