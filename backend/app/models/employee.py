"""
Employee model for beneficiary management
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Employee(Base):
    """
    Employee model representing potential beneficiaries
    
    Attributes:
        id: Primary key
        cnic: National ID (unique, validated format)
        name: Full name
        father_name: Father's name (for deduplication)
        grade: Employee grade (1-20)
        designation: Job title
        mobile: Contact number
        address: Physical address
        family_size: Number of family members
        income_estimate: Estimated monthly income
        lat: Latitude for location clustering
        lon: Longitude for location clustering
        is_eligible: Whether eligible for current distribution
        eligibility_score: ML model eligibility score
        fraud_flag: Whether flagged by fraud detection
        family_key: First 7 digits of CNIC for family deduplication
    """
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    cnic = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    father_name = Column(String(255), index=True)
    grade = Column(Integer, nullable=False, index=True)
    designation = Column(String(255))
    mobile = Column(String(20))
    email = Column(String(255))
    address = Column(String(500))
    
    # Family and financial information
    family_size = Column(Integer, default=1)
    income_estimate = Column(Float, default=0.0)
    previous_aid_count = Column(Integer, default=0)
    
    # Location for clustering
    lat = Column(Float)
    lon = Column(Float)
    
    # Eligibility and ML flags
    is_eligible = Column(Boolean, default=True)
    eligibility_score = Column(Float, default=0.5)
    fraud_flag = Column(Boolean, default=False)
    fraud_score = Column(Float, default=0.0)
    
    # Family deduplication
    family_key = Column(String(10), index=True)  # First 7 digits of CNIC
    is_family_head = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_distribution_date = Column(DateTime(timezone=True))
    
    # User account link (optional)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="employee_profile")
    
    # Relationships
    distributions = relationship("DistributionBeneficiary", back_populates="employee")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_grade_eligible', 'grade', 'is_eligible'),
        Index('idx_family_dedup', 'family_key', 'father_name'),
    )
    
    def __repr__(self):
        return f"<Employee(id={self.id}, cnic={self.cnic}, name={self.name}, grade={self.grade})>"
    
    def calculate_family_key(self):
        """
        Calculate family key from CNIC (first 7 digits)
        """
        if self.cnic:
            clean_cnic = self.cnic.replace("-", "")
            self.family_key = clean_cnic[:7] if len(clean_cnic) >= 7 else clean_cnic
        return self.family_key
    
    def to_dict(self, include_sensitive=False):
        """
        Convert employee to dictionary
        
        Args:
            include_sensitive: Whether to include sensitive information
        
        Returns:
            Dictionary representation
        """
        data = {
            "id": self.id,
            "name": self.name,
            "father_name": self.father_name,
            "grade": self.grade,
            "designation": self.designation,
            "mobile": self.mobile,
            "email": self.email,
            "address": self.address,
            "family_size": self.family_size,
            "is_eligible": self.is_eligible,
            "eligibility_score": round(self.eligibility_score, 2) if self.eligibility_score else 0,
            "fraud_flag": self.fraud_flag,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_sensitive:
            data["cnic"] = self.cnic
            data["income_estimate"] = self.income_estimate
            data["lat"] = self.lat
            data["lon"] = self.lon
        else:
            # Mask CNIC
            if self.cnic:
                data["cnic"] = f"*****-*******-{self.cnic[-4:]}" if len(self.cnic) >= 4 else "****"
        
        return data