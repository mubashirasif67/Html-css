"""
Employee-related Pydantic schemas
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import datetime


class EmployeeBase(BaseModel):
    """Base employee schema"""
    name: str = Field(..., min_length=1, max_length=255)
    cnic: str = Field(..., max_length=20)
    father_name: Optional[str] = Field(None, max_length=255)
    grade: int = Field(..., ge=1, le=22)
    designation: Optional[str] = Field(None, max_length=255)
    mobile: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    family_size: int = Field(1, ge=1, le=20)
    
    @validator('cnic')
    def validate_cnic(cls, v):
        """Validate CNIC format"""
        clean = v.replace('-', '').replace(' ', '')
        if not clean.isdigit() or len(clean) != 13:
            raise ValueError('CNIC must be 13 digits')
        # Format as 12345-1234567-1
        return f"{clean[:5]}-{clean[5:12]}-{clean[12]}"


class EmployeeCreate(EmployeeBase):
    """Schema for creating a new employee"""
    income_estimate: Optional[float] = Field(0.0, ge=0)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    father_name: Optional[str] = Field(None, max_length=255)
    grade: Optional[int] = Field(None, ge=1, le=22)
    designation: Optional[str] = Field(None, max_length=255)
    mobile: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    family_size: Optional[int] = Field(None, ge=1, le=20)
    income_estimate: Optional[float] = Field(None, ge=0)
    is_eligible: Optional[bool] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)


class EmployeeResponse(BaseModel):
    """Schema for employee response"""
    id: int
    name: str
    cnic: str  # Will be masked in response
    father_name: Optional[str]
    grade: int
    designation: Optional[str]
    mobile: Optional[str]
    email: Optional[str]
    address: Optional[str]
    family_size: int
    family_key: Optional[str]
    is_eligible: bool
    eligibility_score: float
    fraud_flag: bool
    previous_aid_count: int
    created_at: datetime
    last_distribution_date: Optional[datetime]
    
    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    """Schema for paginated employee list response"""
    total: int
    page: int
    per_page: int
    pages: int
    items: List[EmployeeResponse]


class EmployeeEligibilityCheck(BaseModel):
    """Schema for eligibility check request"""
    employee_id: int
    force_check: bool = False


class EmployeeEligibilityResponse(BaseModel):
    """Schema for eligibility check response"""
    employee_id: int
    is_eligible: bool
    eligibility_score: float = Field(..., ge=0, le=1)
    fraud_flag: bool
    fraud_score: float = Field(..., ge=0, le=1)
    reasons: List[str]
    recommendation: str