"""
Authentication utilities for the Blessings Donation System.

This module provides password hashing, JWT token management,
and authentication helper functions.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
import secrets
import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import structlog

from ..config import settings
from .models import User, RefreshToken, LoginAttempt

logger = structlog.get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class AuthorizationError(Exception):
    """Custom exception for authorization errors."""
    pass


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        dict: Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        return None


def create_access_token(user_id: int, email: str, role: str) -> str:
    """
    Create an access token for a user.
    
    Args:
        user_id: User ID
        email: User email
        role: User role
        
    Returns:
        str: Access token
    """
    data = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access"
    }
    
    return generate_token(data, timedelta(minutes=settings.jwt_expire_minutes))


def create_refresh_token(user_id: int) -> str:
    """
    Create a refresh token for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        str: Refresh token
    """
    data = {
        "sub": str(user_id),
        "type": "refresh"
    }
    
    return generate_token(data, timedelta(days=30))  # 30 days expiry


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.
    
    Args:
        token: Token to hash
        
    Returns:
        str: Hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_reset_token() -> str:
    """
    Generate a secure random token for password reset.
    
    Returns:
        str: Random token
    """
    return secrets.token_urlsafe(32)


def authenticate_user(db: Session, email: str, password: str, ip_address: str = None) -> Optional[User]:
    """
    Authenticate a user with email and password.
    
    Args:
        db: Database session
        email: User email
        password: User password
        ip_address: Client IP address
        
    Returns:
        User: Authenticated user or None
        
    Raises:
        AuthenticationError: If authentication fails
    """
    # Log login attempt
    attempt = LoginAttempt(
        email=email,
        ip_address=ip_address,
        success=False,
        attempted_at=datetime.utcnow()
    )
    
    try:
        # Get user by email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            attempt.failure_reason = "User not found"
            db.add(attempt)
            db.commit()
            raise AuthenticationError("Invalid email or password")
        
        # Check if user can login
        if not user.can_login:
            if user.failed_login_attempts >= 5:
                attempt.failure_reason = "Account locked"
            elif not user.is_verified:
                attempt.failure_reason = "Account not verified"
            elif not user.is_active:
                attempt.failure_reason = "Account inactive"
            else:
                attempt.failure_reason = "Login not allowed"
            
            db.add(attempt)
            db.commit()
            raise AuthenticationError("Account access denied")
        
        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            attempt.failure_reason = "Invalid password"
            db.add(attempt)
            db.commit()
            raise AuthenticationError("Invalid email or password")
        
        # Successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        attempt.success = True
        
        db.add(attempt)
        db.commit()
        
        logger.info("User authenticated successfully", user_id=user.id, email=email)
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        attempt.failure_reason = "System error"
        db.add(attempt)
        db.commit()
        raise AuthenticationError("Authentication failed")


def store_refresh_token(
    db: Session,
    user_id: int,
    token: str,
    device_info: str = None,
    ip_address: str = None
) -> RefreshToken:
    """
    Store a refresh token in the database.
    
    Args:
        db: Database session
        user_id: User ID
        token: Refresh token
        device_info: Device information
        ip_address: Client IP address
        
    Returns:
        RefreshToken: Stored refresh token record
    """
    token_hash = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    refresh_token = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at
    )
    
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return refresh_token


def revoke_refresh_token(db: Session, token: str) -> bool:
    """
    Revoke a refresh token.
    
    Args:
        db: Database session
        token: Refresh token to revoke
        
    Returns:
        bool: True if token was revoked
    """
    token_hash = hash_token(token)
    
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_revoked == False
    ).first()
    
    if refresh_token:
        refresh_token.is_revoked = True
        refresh_token.revoked_at = datetime.utcnow()
        db.commit()
        return True
    
    return False


def verify_refresh_token(db: Session, token: str) -> Optional[User]:
    """
    Verify a refresh token and return the associated user.
    
    Args:
        db: Database session
        token: Refresh token
        
    Returns:
        User: Associated user if token is valid
    """
    token_hash = hash_token(token)
    
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()
    
    if not refresh_token or not refresh_token.is_valid:
        return None
    
    # Update last used timestamp
    refresh_token.last_used = datetime.utcnow()
    db.commit()
    
    # Get associated user
    user = db.query(User).filter(User.id == refresh_token.user_id).first()
    
    return user if user and user.can_login else None


def cleanup_expired_tokens(db: Session) -> int:
    """
    Clean up expired refresh tokens.
    
    Args:
        db: Database session
        
    Returns:
        int: Number of tokens cleaned up
    """
    expired_tokens = db.query(RefreshToken).filter(
        RefreshToken.expires_at < datetime.utcnow()
    ).all()
    
    count = len(expired_tokens)
    
    for token in expired_tokens:
        db.delete(token)
    
    db.commit()
    
    logger.info("Cleaned up expired tokens", count=count)
    return count


def get_current_user_from_token(db: Session, token: str) -> Optional[User]:
    """
    Get current user from access token.
    
    Args:
        db: Database session
        token: Access token
        
    Returns:
        User: Current user if token is valid
    """
    payload = verify_token(token)
    
    if not payload or payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    try:
        user_id = int(user_id)
        user = db.query(User).filter(User.id == user_id).first()
        return user if user and user.can_login else None
    except (ValueError, TypeError):
        return None


def check_permission(user: User, permission: str) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user: User object
        permission: Permission string
        
    Returns:
        bool: True if user has permission
    """
    return user.has_permission(permission)


def require_permission(user: User, permission: str) -> None:
    """
    Require a specific permission, raise exception if not authorized.
    
    Args:
        user: User object
        permission: Required permission
        
    Raises:
        AuthorizationError: If user doesn't have permission
    """
    if not check_permission(user, permission):
        raise AuthorizationError(f"Permission required: {permission}")


def get_login_stats(db: Session, days: int = 7) -> Dict[str, Any]:
    """
    Get login statistics for the specified number of days.
    
    Args:
        db: Database session
        days: Number of days to analyze
        
    Returns:
        dict: Login statistics
    """
    from sqlalchemy import func, and_
    
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Total attempts
    total_attempts = db.query(LoginAttempt).filter(
        LoginAttempt.attempted_at >= since_date
    ).count()
    
    # Successful attempts
    successful_attempts = db.query(LoginAttempt).filter(
        and_(
            LoginAttempt.attempted_at >= since_date,
            LoginAttempt.success == True
        )
    ).count()
    
    # Failed attempts
    failed_attempts = total_attempts - successful_attempts
    
    # Unique users
    unique_users = db.query(LoginAttempt.email).filter(
        and_(
            LoginAttempt.attempted_at >= since_date,
            LoginAttempt.success == True
        )
    ).distinct().count()
    
    # Recent failed attempts by IP
    recent_failures = db.query(
        LoginAttempt.ip_address,
        func.count(LoginAttempt.id).label('count')
    ).filter(
        and_(
            LoginAttempt.attempted_at >= since_date,
            LoginAttempt.success == False,
            LoginAttempt.ip_address.isnot(None)
        )
    ).group_by(LoginAttempt.ip_address).order_by(
        func.count(LoginAttempt.id).desc()
    ).limit(10).all()
    
    return {
        "period_days": days,
        "total_attempts": total_attempts,
        "successful_attempts": successful_attempts,
        "failed_attempts": failed_attempts,
        "success_rate": round(successful_attempts / total_attempts * 100, 2) if total_attempts > 0 else 0,
        "unique_users": unique_users,
        "suspicious_ips": [
            {"ip": ip, "failed_attempts": count}
            for ip, count in recent_failures
            if count >= 5
        ]
    }