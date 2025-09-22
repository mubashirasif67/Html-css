"""
Authentication routes for the Blessings Donation System.

This module provides API endpoints for user authentication,
registration, and user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from ..database import get_db
from ..config import settings
from .schemas import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    UserCreateRequest, UserUpdateRequest, UserResponse, UserListResponse,
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest,
    MessageResponse, ErrorResponse, SecurityStatsResponse
)
from .models import User, UserRole, UserStatus
from .utils import (
    authenticate_user, create_access_token, create_refresh_token,
    store_refresh_token, verify_refresh_token, revoke_refresh_token,
    hash_password, verify_password, get_current_user_from_token,
    require_permission, get_login_stats, AuthenticationError, AuthorizationError
)

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        user = get_current_user_from_token(db, credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        logger.error("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Require admin user for protected endpoints.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Register a new user (Admin only).
    
    Args:
        user_data: User creation data
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        UserResponse: Created user information
        
    Raises:
        HTTPException: If email already exists or validation fails
    """
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if employee_id already exists
        if user_data.employee_id:
            existing_employee = db.query(User).filter(
                User.employee_id == user_data.employee_id
            ).first()
            if existing_employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee ID already exists"
                )
        
        # Create new user
        hashed_password = hash_password(user_data.password)
        
        new_user = User(
            name=user_data.name,
            email=user_data.email,
            password_hash=hashed_password,
            phone=user_data.phone,
            role=UserRole(user_data.role.value),
            status=UserStatus.ACTIVE,  # Auto-activate admin-created users
            department=user_data.department,
            employee_id=user_data.employee_id,
            notes=user_data.notes,
            is_verified=True,  # Auto-verify admin-created users
            created_by=current_user.id
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(
            "User registered successfully",
            user_id=new_user.id,
            email=new_user.email,
            created_by=current_user.id
        )
        
        return UserResponse.from_orm(new_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User registration failed", error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    
    Args:
        login_data: Login credentials
        request: HTTP request object
        db: Database session
        
    Returns:
        LoginResponse: JWT tokens and user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Get client IP address
        client_ip = request.client.host if request.client else None
        
        # Authenticate user
        user = authenticate_user(
            db=db,
            email=login_data.email,
            password=login_data.password,
            ip_address=client_ip
        )
        
        # Create tokens
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        refresh_token = create_refresh_token(user_id=user.id)
        
        # Store refresh token
        device_info = request.headers.get("User-Agent", "Unknown")
        store_refresh_token(
            db=db,
            user_id=user.id,
            token=refresh_token,
            device_info=device_info,
            ip_address=client_ip
        )
        
        logger.info("User logged in successfully", user_id=user.id, email=user.email)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60,
            user=UserResponse.from_orm(user)
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token data
        db: Database session
        
    Returns:
        RefreshTokenResponse: New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Verify refresh token
        user = verify_refresh_token(db, refresh_data.refresh_token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new access token
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        
        logger.info("Token refreshed successfully", user_id=user.id)
        
        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout user by revoking refresh token.
    
    Args:
        refresh_data: Refresh token data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        MessageResponse: Logout confirmation
    """
    try:
        # Revoke refresh token
        revoked = revoke_refresh_token(db, refresh_data.refresh_token)
        
        if revoked:
            logger.info("User logged out successfully", user_id=current_user.id)
            return MessageResponse(message="Logged out successfully")
        else:
            return MessageResponse(message="Token already expired or invalid")
            
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user information (limited fields).
    
    Args:
        user_data: User update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Updated user information
    """
    try:
        # Users can only update their own basic information
        if user_data.name is not None:
            current_user.name = user_data.name
        if user_data.phone is not None:
            current_user.phone = user_data.phone
        
        # Only admins can change role and status
        if current_user.is_admin:
            if user_data.role is not None:
                current_user.role = UserRole(user_data.role.value)
            if user_data.status is not None:
                current_user.status = UserStatus(user_data.status.value)
            if user_data.department is not None:
                current_user.department = user_data.department
            if user_data.employee_id is not None:
                current_user.employee_id = user_data.employee_id
            if user_data.notes is not None:
                current_user.notes = user_data.notes
        
        db.commit()
        db.refresh(current_user)
        
        logger.info("User updated successfully", user_id=current_user.id)
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        logger.error("User update failed", error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change current user's password.
    
    Args:
        password_data: Password change data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        MessageResponse: Password change confirmation
    """
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.password_hash = hash_password(password_data.new_password)
        current_user.password_changed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info("Password changed successfully", user_id=current_user.id)
        return MessageResponse(message="Password changed successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change failed", error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    per_page: int = 20,
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    List all users with pagination and filtering (Admin only).
    
    Args:
        page: Page number
        per_page: Users per page
        role: Filter by role
        status: Filter by status
        search: Search by name or email
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        UserListResponse: Paginated list of users
    """
    try:
        query = db.query(User)
        
        # Apply filters
        if role:
            query = query.filter(User.role == UserRole(role))
        if status:
            query = query.filter(User.status == UserStatus(status))
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.name.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.employee_id.ilike(search_term))
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        users = query.offset(offset).limit(per_page).all()
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page
        
        return UserListResponse(
            users=[UserResponse.from_orm(user) for user in users],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        logger.error("User list failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Get user by ID (Admin only).
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        UserResponse: User information
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Update user by ID (Admin only).
    
    Args:
        user_id: User ID
        user_data: User update data
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        UserResponse: Updated user information
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        if user_data.name is not None:
            user.name = user_data.name
        if user_data.phone is not None:
            user.phone = user_data.phone
        if user_data.role is not None:
            user.role = UserRole(user_data.role.value)
        if user_data.status is not None:
            user.status = UserStatus(user_data.status.value)
        if user_data.department is not None:
            user.department = user_data.department
        if user_data.employee_id is not None:
            user.employee_id = user_data.employee_id
        if user_data.notes is not None:
            user.notes = user_data.notes
        
        db.commit()
        db.refresh(user)
        
        logger.info("User updated by admin", user_id=user.id, admin_id=current_user.id)
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User update failed", error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Delete user by ID (Admin only).
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        MessageResponse: Deletion confirmation
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent self-deletion
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        db.delete(user)
        db.commit()
        
        logger.info("User deleted by admin", user_id=user.id, admin_id=current_user.id)
        return MessageResponse(message="User deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User deletion failed", error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User deletion failed"
        )


@router.get("/security/stats", response_model=SecurityStatsResponse)
async def get_security_stats(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Get security statistics (Admin only).
    
    Args:
        days: Number of days to analyze
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        SecurityStatsResponse: Security statistics
    """
    try:
        stats = get_login_stats(db, days)
        
        # Get user counts
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.status == UserStatus.ACTIVE).count()
        
        # Get recent attempts
        from datetime import datetime, timedelta
        from .models import LoginAttempt
        
        recent_attempts = db.query(LoginAttempt).filter(
            LoginAttempt.attempted_at >= datetime.utcnow() - timedelta(days=1)
        ).order_by(LoginAttempt.attempted_at.desc()).limit(10).all()
        
        return SecurityStatsResponse(
            total_users=total_users,
            active_users=active_users,
            failed_logins_today=stats["failed_attempts"],
            successful_logins_today=stats["successful_attempts"],
            suspicious_activities=len(stats["suspicious_ips"]),
            recent_attempts=[
                {
                    "id": attempt.id,
                    "email": attempt.email,
                    "ip_address": attempt.ip_address,
                    "success": attempt.success,
                    "failure_reason": attempt.failure_reason,
                    "attempted_at": attempt.attempted_at,
                    "country": attempt.country,
                    "city": attempt.city
                }
                for attempt in recent_attempts
            ]
        )
        
    except Exception as e:
        logger.error("Security stats failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security statistics"
        )


# Import datetime for password change endpoint
from datetime import datetime