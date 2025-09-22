"""
Authentication and authorization utilities
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload data to encode in the token
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token
    
    Args:
        data: Payload data to encode in the token
    
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token to decode
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token
    
    Args:
        token: JWT access token
        db: Database session
    
    Returns:
        Current user object
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        
        # Check token type
        if payload.get("type") != "access":
            raise credentials_exception
        
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except HTTPException:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current admin user
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Admin user object
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    
    return current_user


def validate_password_strength(password: str) -> bool:
    """
    Validate password strength
    
    Args:
        password: Password to validate
    
    Returns:
        True if password meets requirements
    
    Raises:
        ValueError: If password doesn't meet requirements
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        raise ValueError("Password must contain at least one special character")
    
    return True


def mask_cnic(cnic: str) -> str:
    """
    Mask CNIC for privacy (show only last 4 digits)
    
    Args:
        cnic: CNIC number to mask
    
    Returns:
        Masked CNIC string
    """
    if not cnic or len(cnic) < 4:
        return "****"
    
    # Remove any hyphens
    clean_cnic = cnic.replace("-", "")
    
    # Show format: *****-*******-1234
    if len(clean_cnic) >= 13:
        return f"*****-*******-{clean_cnic[-4:]}"
    else:
        return f"{'*' * (len(clean_cnic) - 4)}{clean_cnic[-4:]}"


def validate_cnic(cnic: str) -> str:
    """
    Validate and normalize CNIC format
    
    Args:
        cnic: CNIC number to validate
    
    Returns:
        Normalized CNIC in format: 12345-1234567-1
    
    Raises:
        ValueError: If CNIC format is invalid
    """
    # Remove any spaces or hyphens
    clean_cnic = cnic.replace("-", "").replace(" ", "")
    
    # Check if it's 13 digits
    if not clean_cnic.isdigit() or len(clean_cnic) != 13:
        raise ValueError("CNIC must be exactly 13 digits")
    
    # Format as: 12345-1234567-1
    formatted_cnic = f"{clean_cnic[:5]}-{clean_cnic[5:12]}-{clean_cnic[12]}"
    
    return formatted_cnic