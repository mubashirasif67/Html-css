"""
Employee management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from app.database import get_db
from app.auth import get_current_user, get_current_admin_user, validate_cnic
from app.models.user import User
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    EmployeeListResponse
)
from app.services.ml_service import MLService

logger = logging.getLogger(__name__)
router = APIRouter()
ml_service = MLService()


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new employee (Admin only)
    
    Request Body:
    ```json
    {
        "name": "Ali Ahmed",
        "cnic": "12345-1234567-1",
        "father_name": "Ahmed Khan",
        "grade": 15,
        "designation": "Assistant",
        "mobile": "+923001234567",
        "email": "ali@example.com",
        "address": "House 123, Street 45, Karachi",
        "family_size": 4,
        "income_estimate": 35000.0,
        "lat": 24.8607,
        "lon": 67.0011
    }
    ```
    """
    # Check if employee with same CNIC exists
    existing = db.query(Employee).filter(Employee.cnic == employee_data.cnic).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this CNIC already exists"
        )
    
    # Create employee
    employee = Employee(**employee_data.dict())
    
    # Calculate family key for deduplication
    employee.calculate_family_key()
    
    # Run initial eligibility check
    try:
        eligibility_result = await ml_service.check_eligibility(employee)
        employee.eligibility_score = eligibility_result["score"]
        employee.is_eligible = eligibility_result["eligible"]
    except Exception as e:
        logger.warning(f"Could not check eligibility: {e}")
        employee.eligibility_score = 0.5
        employee.is_eligible = True
    
    try:
        db.add(employee)
        db.commit()
        db.refresh(employee)
        
        logger.info(f"Employee created: {employee.id} by user {current_user.id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating employee: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating employee"
        )
    
    return EmployeeResponse.from_orm(employee)


@router.get("/", response_model=EmployeeListResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    grade: Optional[int] = Query(None, ge=1, le=22),
    is_eligible: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List employees with pagination and filters
    
    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - grade: Filter by grade (1-22)
    - is_eligible: Filter by eligibility status
    - search: Search by name or CNIC
    
    Example:
    GET /api/employees?grade=15&page=1&per_page=10
    """
    query = db.query(Employee)
    
    # Apply filters
    if grade:
        query = query.filter(Employee.grade == grade)
    
    if is_eligible is not None:
        query = query.filter(Employee.is_eligible == is_eligible)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Employee.name.like(search_term)) |
            (Employee.cnic.like(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    employees = query.offset(offset).limit(per_page).all()
    
    # Calculate pagination info
    pages = (total + per_page - 1) // per_page
    
    return EmployeeListResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        items=[EmployeeResponse.from_orm(emp) for emp in employees]
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get employee details by ID
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return EmployeeResponse.from_orm(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update employee details (Admin only)
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Update fields
    update_data = employee_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    # Recalculate family key if needed
    if "cnic" in update_data:
        employee.calculate_family_key()
    
    # Re-run eligibility check if relevant fields changed
    if any(field in update_data for field in ["grade", "family_size", "income_estimate"]):
        try:
            eligibility_result = await ml_service.check_eligibility(employee)
            employee.eligibility_score = eligibility_result["score"]
            employee.is_eligible = eligibility_result["eligible"]
        except Exception as e:
            logger.warning(f"Could not check eligibility: {e}")
    
    try:
        db.commit()
        db.refresh(employee)
        
        logger.info(f"Employee {employee_id} updated by user {current_user.id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating employee: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating employee"
        )
    
    return EmployeeResponse.from_orm(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete an employee (Admin only)
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    try:
        db.delete(employee)
        db.commit()
        
        logger.info(f"Employee {employee_id} deleted by user {current_user.id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting employee: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting employee"
        )
    
    return None