"""
Distribution-related Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


class DistributionStatus(str, Enum):
    """Distribution status enumeration"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DistributionCreate(BaseModel):
    """Schema for creating a new distribution"""
    distribution_date: date
    notes: Optional[str] = None
    config: Optional[Dict[str, Any]] = None  # Distribution rules configuration


class DistributionApprove(BaseModel):
    """Schema for approving a distribution"""
    distribution_run_id: int
    notes: Optional[str] = None
    send_notifications: bool = True


class DistributionResponse(BaseModel):
    """Schema for distribution response"""
    id: int
    distribution_date: date
    status: str
    total_beneficiaries: int
    total_families: int
    total_amount: float
    created_at: datetime
    created_by: int
    approved_at: Optional[datetime]
    approved_by: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    
    class Config:
        from_attributes = True


class BeneficiaryResponse(BaseModel):
    """Schema for distribution beneficiary response"""
    id: int
    employee_id: int
    employee_name: str
    employee_cnic: str  # Masked
    grade: int
    family_key: str
    family_size: int
    eligibility_score: float = Field(..., ge=0, le=1)
    fraud_flag: bool
    priority_rank: int
    amount_allocated: float
    items_allocated: Optional[List[str]]
    pickup_schedule_id: Optional[int]
    pickup_completed: bool
    
    class Config:
        from_attributes = True


class DistributionRunResponse(BaseModel):
    """Schema for distribution run result"""
    distribution_id: int
    distribution_date: date
    status: str
    total_beneficiaries: int
    total_families: int
    beneficiaries: List[BeneficiaryResponse]
    excluded_due_to_deduplication: int
    excluded_due_to_eligibility: int
    excluded_due_to_fraud: int


class PickupScheduleCreate(BaseModel):
    """Schema for creating pickup schedule"""
    distribution_id: int
    pickup_date: date
    location: str
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lon: Optional[float] = Field(None, ge=-180, le=180)
    slots_per_day: int = Field(10, ge=1, le=50)
    minutes_per_slot: int = Field(30, ge=10, le=120)


class PickupScheduleResponse(BaseModel):
    """Schema for pickup schedule response"""
    id: int
    distribution_id: int
    pickup_date: date
    start_time: datetime
    end_time: datetime
    slot_number: int
    location: str
    location_lat: Optional[float]
    location_lon: Optional[float]
    max_beneficiaries: int
    current_beneficiaries: int
    is_full: bool
    beneficiaries: Optional[List[BeneficiaryResponse]]
    
    class Config:
        from_attributes = True


class DistributionReport(BaseModel):
    """Schema for distribution report"""
    distribution_id: int
    report_type: str  # "summary", "detailed", "beneficiaries"
    format: str = "pdf"  # "pdf", "csv", "xlsx"
    include_photos: bool = False


class DistributionStatistics(BaseModel):
    """Schema for distribution statistics"""
    total_distributions: int
    total_beneficiaries_served: int
    total_amount_distributed: float
    average_per_beneficiary: float
    distributions_by_month: Dict[str, int]
    beneficiaries_by_grade: Dict[int, int]
    coverage_by_area: Dict[str, int]
    deduplication_stats: Dict[str, int]
    ml_model_performance: Dict[str, float]