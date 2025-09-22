"""
FastAPI application entry point.

This module creates and configures the FastAPI app with all routes,
middleware, and dependencies.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .config import settings
import logging

# Import all route modules
from .routes import auth, employees, donations, admin, feedback, ocr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="API for Blessings Distribution System",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React apps
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1"]
)

# Include route modules
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(donations.router, prefix="/api/donations", tags=["Donations"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic info."""
    return """
    <html>
        <head><title>Blessings Distribution System</title></head>
        <body>
            <h1>Welcome to Blessings Distribution System API</h1>
            <p>API Documentation: <a href="/api/docs">/api/docs</a></p>
            <p>Health Check: <a href="/health">/health</a></p>
        </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)