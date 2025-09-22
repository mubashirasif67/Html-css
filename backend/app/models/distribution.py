"""
Distribution and pickup scheduling models
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class DistributionStatus(str, enum.Enum):
    """Distribution status enumeration"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Distribution(Base):
    """
    Distribution run model for managing ration distributions
    
    Attributes:
        id: Primary key
        distribution_date: Date of distribution
        status: Current status of distribution
        total_beneficiaries: Total number of beneficiaries
        total_amount: Total amount/value distributed
        created_by: User who created the distribution
        approved_by: User who approved the distribution
        notes: Additional notes
    """
    __tablename__ = "distributions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Distribution details
    distribution_date = Column(Date, nullable=False, index=True)
    status = Column(Enum(DistributionStatus), default=DistributionStatus.DRAFT, nullable=False)
    
    # Statistics
    total_beneficiaries = Column(Integer, default=0)
    total_families = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    
    # Approval workflow
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    
    # Completion tracking
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Additional information
    notes = Column(Text)
    config = Column(Text)  # JSON configuration for distribution rules
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    beneficiaries = relationship("DistributionBeneficiary", back_populates="distribution", cascade="all, delete-orphan")
    schedules = relationship("PickupSchedule", back_populates="distribution", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Distribution(id={self.id}, date={self.distribution_date}, status={self.status})>"
    
    def to_dict(self):
        """Convert distribution to dictionary"""
        return {
            "id": self.id,
            "distribution_date": self.distribution_date.isoformat() if self.distribution_date else None,
            "status": self.status.value if self.status else None,
            "total_beneficiaries": self.total_beneficiaries,
            "total_families": self.total_families,
            "total_amount": self.total_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "notes": self.notes,
        }


class DistributionBeneficiary(Base):
    """
    Beneficiaries selected for a distribution
    """
    __tablename__ = "distribution_beneficiaries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    distribution_id = Column(Integer, ForeignKey("distributions.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    
    # Selection details
    family_key = Column(String(10), index=True)
    eligibility_score = Column(Float)
    fraud_flag = Column(Boolean, default=False)
    priority_rank = Column(Integer)  # Ordering within distribution
    
    # Distribution details
    amount_allocated = Column(Float)
    items_allocated = Column(Text)  # JSON list of items
    
    # Pickup information
    pickup_schedule_id = Column(Integer, ForeignKey("pickup_schedules.id"))
    pickup_completed = Column(Boolean, default=False)
    pickup_completed_at = Column(DateTime(timezone=True))
    
    # Verification
    verified_by_cnic = Column(Boolean, default=False)
    verification_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    distribution = relationship("Distribution", back_populates="beneficiaries")
    employee = relationship("Employee", back_populates="distributions")
    pickup_schedule = relationship("PickupSchedule", back_populates="beneficiaries")
    
    def __repr__(self):
        return f"<DistributionBeneficiary(dist={self.distribution_id}, emp={self.employee_id})>"


class PickupSchedule(Base):
    """
    Pickup scheduling for distributions
    """
    __tablename__ = "pickup_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    distribution_id = Column(Integer, ForeignKey("distributions.id"), nullable=False, index=True)
    
    # Schedule details
    pickup_date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    slot_number = Column(Integer)  # Slot identifier (1, 2, 3, etc.)
    
    # Location
    location = Column(String(500))
    location_lat = Column(Float)
    location_lon = Column(Float)
    
    # Capacity
    max_beneficiaries = Column(Integer, default=20)
    current_beneficiaries = Column(Integer, default=0)
    
    # Cluster information (for grouped scheduling)
    cluster_id = Column(Integer)
    cluster_center_lat = Column(Float)
    cluster_center_lon = Column(Float)
    
    # Status
    is_full = Column(Boolean, default=False)
    notifications_sent = Column(Boolean, default=False)
    notifications_sent_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    distribution = relationship("Distribution", back_populates="schedules")
    beneficiaries = relationship("DistributionBeneficiary", back_populates="pickup_schedule")
    
    def __repr__(self):
        return f"<PickupSchedule(id={self.id}, date={self.pickup_date}, slot={self.slot_number})>"
    
    def to_dict(self):
        """Convert schedule to dictionary"""
        return {
            "id": self.id,
            "pickup_date": self.pickup_date.isoformat() if self.pickup_date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "slot_number": self.slot_number,
            "location": self.location,
            "max_beneficiaries": self.max_beneficiaries,
            "current_beneficiaries": self.current_beneficiaries,
            "is_full": self.is_full,
        }