"""
Employee management routes.

Handles CRUD operations for employees/beneficiaries.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import Employee, User
from ..schemas import EmployeeCreate, EmployeeResponse
from ..utils import normalize_cnic, extract_family_key
from ..dependencies import get_admin_user

router = APIRouter()


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_data: EmployeeCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new employee."""
    # Validate and normalize CNIC
    try:
        normalized_cnic = normalize_cnic(employee_data.cnic)
        family_key = extract_family_key(normalized_cnic)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if CNIC already exists
    existing = db.query(Employee).filter(Employee.cnic == normalized_cnic).first()
    if existing:
        raise HTTPException(status_code=400, detail="CNIC already registered")

    # Create employee
    new_employee = Employee(
        user_id=current_user.id,
        name=employee_data.name,
        father_name=employee_data.father_name,
        cnic=normalized_cnic,
        family_key=family_key,
        grade=employee_data.grade,
        designation=employee_data.designation,
        mobile=employee_data.mobile,
        address=employee_data.address,
        family_size=employee_data.family_size,
        latitude=employee_data.latitude,
        longitude=employee_data.longitude,
        is_eligible=True  # Default to eligible
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return EmployeeResponse.model_validate(new_employee)


@router.get("/", response_model=List[EmployeeResponse])
def list_employees(
    grade: Optional[str] = Query(None),
    family_key: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List employees with optional filtering."""
    query = db.query(Employee)

    if grade:
        query = query.filter(Employee.grade == grade)

    if family_key:
        query = query.filter(Employee.family_key == family_key)

    employees = query.offset(skip).limit(limit).all()
    return [EmployeeResponse.model_validate(emp) for emp in employees]


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get employee by ID."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return EmployeeResponse.model_validate(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    employee_data: EmployeeCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update employee information."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Update fields
    for field in ['name', 'father_name', 'grade', 'designation', 'mobile', 'address', 'family_size', 'latitude', 'longitude']:
        if hasattr(employee_data, field):
            setattr(employee, field, getattr(employee_data, field))

    # Update CNIC if changed
    if employee_data.cnic != employee.cnic:
        try:
            normalized_cnic = normalize_cnic(employee_data.cnic)
            employee.cnic = normalized_cnic
            employee.family_key = extract_family_key(normalized_cnic)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    db.refresh(employee)

    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete employee."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.delete(employee)
    db.commit()