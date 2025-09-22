"""
Employee models for the Blessings Donation System.

This module defines employee-related database models for ration distribution.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, Text
from sqlalchemy.sql import func
import enum
from datetime import datetime
from typing import Optional

from ..database import Base


class EmploymentStatus(str, enum.Enum):
    """Employment status enumeration."""
    PERMANENT = "permanent"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    RETIRED = "retired"
    SUSPENDED = "suspended"


class HousingStatus(str, enum.Enum):
    """Housing status enumeration."""
    OWNED = "owned"
    RENTED = "rented"
    FAMILY = "family"
    QUARTERS = "quarters"


class Employee(Base):
    """
    Employee model for ration distribution eligibility.
    
    This model stores employee information used for eligibility assessment
    and ration distribution management.
    """
    
    __tablename__ = "employees"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Employee identification
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    cnic = Column(String(15), unique=True, nullable=False, index=True)
    
    # Personal information
    name = Column(String(255), nullable=False, index=True)
    father_name = Column(String(255), nullable=False)
    date_of_birth = Column(DateTime(timezone=True), nullable=True)
    
    # Contact information
    mobile = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    
    # Employment details
    grade = Column(Integer, nullable=False, index=True)  # 1-20 scale
    designation = Column(String(100), nullable=False)
    department = Column(String(100), nullable=True)
    employment_status = Column(Enum(EmploymentStatus), default=EmploymentStatus.PERMANENT)
    joining_date = Column(DateTime(timezone=True), nullable=True)
    
    # Family information
    family_size = Column(Integer, default=1, nullable=False)
    dependents = Column(Integer, default=0, nullable=False)
    spouse_name = Column(String(255), nullable=True)
    
    # Financial information
    basic_salary = Column(Float, nullable=True)
    total_income = Column(Float, nullable=True)
    medical_expenses = Column(Float, default=0.0)
    education_expenses = Column(Float, default=0.0)
    
    # Housing information
    housing_status = Column(Enum(HousingStatus), default=HousingStatus.RENTED)
    housing_allowance = Column(Float, default=0.0)
    
    # Eligibility tracking
    previous_aid_count = Column(Integer, default=0, nullable=False)
    last_aid_date = Column(DateTime(timezone=True), nullable=True)
    is_eligible = Column(Boolean, default=True, nullable=False)
    eligibility_score = Column(Float, nullable=True)
    
    # Location information (for clustering)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    area = Column(String(100), nullable=True)
    
    # Verification status
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(Integer, nullable=True)  # User ID
    verification_date = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, nullable=True)  # User ID
    
    # Additional notes
    notes = Column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, employee_id='{self.employee_id}', name='{self.name}')>"
    
    @property
    def masked_cnic(self) -> str:
        """Get masked CNIC for display."""
        if not self.cnic:
            return "****"
        # Mask middle digits: 12345-1234567-1 -> 12345-****567-1
        if len(self.cnic) >= 13:
            return f"{self.cnic[:5]}-****{self.cnic[-3:]}"
        return "****"
    
    @property
    def years_of_service(self) -> float:
        """Calculate years of service."""
        if not self.joining_date:
            return 0.0
        
        delta = datetime.utcnow() - self.joining_date
        return delta.days / 365.25
    
    @property
    def family_key(self) -> str:
        """Generate family key for deduplication (first 7 digits of CNIC)."""
        if not self.cnic:
            return ""
        
        clean_cnic = self.cnic.replace('-', '').replace(' ', '')
        return clean_cnic[:7] if len(clean_cnic) >= 7 else clean_cnic
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.area:
            parts.append(self.area)
        return ", ".join(parts) if parts else ""
    
    @property
    def is_high_priority(self) -> bool:
        """Check if employee is high priority for aid."""
        return (
            self.grade >= 15 and  # Lower grades (higher numbers)
            self.family_size >= 4 and
            self.previous_aid_count <= 2
        )
    
    def calculate_need_score(self) -> float:
        """Calculate need score based on various factors."""
        score = 0.0
        
        # Grade-based scoring (higher grade = higher need)
        if self.grade >= 15:
            score += 0.3
        elif self.grade >= 10:
            score += 0.2
        elif self.grade >= 5:
            score += 0.1
        
        # Family size scoring
        if self.family_size >= 6:
            score += 0.25
        elif self.family_size >= 4:
            score += 0.15
        elif self.family_size >= 2:
            score += 0.05
        
        # Income-based scoring
        if self.total_income:
            if self.total_income <= 25000:
                score += 0.3
            elif self.total_income <= 40000:
                score += 0.2
            elif self.total_income <= 60000:
                score += 0.1
        
        # Previous aid consideration
        if self.previous_aid_count == 0:
            score += 0.1
        elif self.previous_aid_count <= 2:
            score += 0.05
        else:
            score -= 0.05
        
        # Housing status
        if self.housing_status == HousingStatus.RENTED:
            score += 0.05
        elif self.housing_status == HousingStatus.FAMILY:
            score += 0.03
        
        # Medical expenses
        if self.medical_expenses >= 5000:
            score += 0.1
        elif self.medical_expenses >= 2000:
            score += 0.05
        
        return min(score, 1.0)


class DistributionRun(Base):
    """
    Model to track ration distribution runs.
    
    This model stores information about each distribution cycle
    including eligible employees and scheduling.
    """
    
    __tablename__ = "distribution_runs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Run details
    run_date = Column(DateTime(timezone=True), nullable=False, index=True)
    run_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), default="pending", nullable=False)  # pending, approved, completed
    
    # Statistics
    total_eligible = Column(Integer, default=0)
    total_approved = Column(Integer, default=0)
    total_distributed = Column(Integer, default=0)
    
    # Approval information
    approved_by = Column(Integer, nullable=True)  # User ID
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_by = Column(Integer, nullable=False)  # User ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<DistributionRun(id={self.id}, run_date='{self.run_date}', status='{self.status}')>"


class DistributionEntry(Base):
    """
    Model to track individual employee entries in distribution runs.
    
    This model links employees to specific distribution runs with
    eligibility scores and pickup scheduling.
    """
    
    __tablename__ = "distribution_entries"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    distribution_run_id = Column(Integer, nullable=False, index=True)
    employee_id = Column(Integer, nullable=False, index=True)
    
    # Eligibility assessment
    eligibility_score = Column(Float, nullable=False)
    ml_prediction = Column(Float, nullable=True)  # ML model prediction
    manual_override = Column(Boolean, default=False)
    
    # Fraud detection
    fraud_score = Column(Float, nullable=True)
    fraud_flags = Column(Text, nullable=True)  # JSON string
    is_flagged = Column(Boolean, default=False)
    
    # Family deduplication
    family_key = Column(String(20), nullable=False, index=True)
    is_family_head = Column(Boolean, default=True)  # Primary family member
    duplicate_of = Column(Integer, nullable=True)  # Reference to family head entry
    
    # Pickup scheduling
    pickup_date = Column(DateTime(timezone=True), nullable=True)
    pickup_time_slot = Column(String(20), nullable=True)  # e.g., "09:00-09:30"
    pickup_location = Column(String(255), nullable=True)
    cluster_id = Column(Integer, nullable=True)  # For geographic clustering
    
    # Distribution status
    status = Column(String(50), default="eligible", nullable=False)  # eligible, approved, collected, rejected
    collected_at = Column(DateTime(timezone=True), nullable=True)
    collected_by = Column(String(255), nullable=True)  # Who collected
    
    # Items distributed
    items_json = Column(Text, nullable=True)  # JSON string of items
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<DistributionEntry(id={self.id}, employee_id={self.employee_id}, status='{self.status}')>"
    
    @property
    def is_collected(self) -> bool:
        """Check if ration has been collected."""
        return self.status == "collected" and self.collected_at is not None