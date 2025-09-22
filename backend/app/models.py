"""
SQLAlchemy models for the Blessings Distribution System.

Defines database tables for users, employees, donations, distributions,
and related entities with appropriate relationships and constraints.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


class UserRole(str, enum.Enum):
    """Enum for user roles."""
    ADMIN = "admin"
    DONOR = "donor"
    EMPLOYEE = "employee"


class DonationType(str, enum.Enum):
    """Enum for donation types."""
    ZAKAT = "zakat"
    SADAQAH = "sadaqah"
    GENERAL = "general"


class EmployeeGrade(str, enum.Enum):
    """Enum for employee grades (1-20)."""
    GRADE_1 = "1"
    GRADE_2 = "2"
    GRADE_3 = "3"
    GRADE_4 = "4"
    GRADE_5 = "5"
    GRADE_6 = "6"
    GRADE_7 = "7"
    GRADE_8 = "8"
    GRADE_9 = "9"
    GRADE_10 = "10"
    GRADE_11 = "11"
    GRADE_12 = "12"
    GRADE_13 = "13"
    GRADE_14 = "14"
    GRADE_15 = "15"
    GRADE_16 = "16"
    GRADE_17 = "17"
    GRADE_18 = "18"
    GRADE_19 = "19"
    GRADE_20 = "20"


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.DONOR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    donations = relationship("Donation", back_populates="donor")
    employees = relationship("Employee", back_populates="user")
    distribution_runs = relationship("DistributionRun", back_populates="admin")


class Employee(Base):
    """Employee model representing beneficiaries."""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    cnic = Column(String(15), unique=True, index=True, nullable=False)  # Normalized CNIC
    name = Column(String(100), nullable=False)
    father_name = Column(String(100), nullable=False)
    grade = Column(Enum(EmployeeGrade), nullable=False)
    designation = Column(String(100))
    mobile = Column(String(15), nullable=False)
    address = Column(Text)
    family_key = Column(String(10), index=True)  # First 7 digits of CNIC for family grouping
    family_size = Column(Integer, default=1)
    latitude = Column(Float)  # For clustering
    longitude = Column(Float)  # For clustering
    is_eligible = Column(Boolean, default=True)
    eligibility_score = Column(Float, default=0.5)
    fraud_flag = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="employees")
    distributions = relationship("Distribution", back_populates="employee")


class Donation(Base):
    """Donation model."""
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    donor_name = Column(String(100), nullable=False)
    donor_email = Column(String(100))
    donor_cnic = Column(String(15))  # Optional CNIC
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="PKR")
    donation_type = Column(Enum(DonationType), nullable=False)
    receipt_image_path = Column(String(255))  # Path to uploaded receipt
    detected_amount = Column(Float)  # OCR detected amount
    confidence = Column(Float)  # OCR confidence
    ocr_text = Column(Text)  # Full OCR text
    transaction_hash = Column(String(64), index=True)  # SHA256 for transparency
    created_at = Column(DateTime, default=func.now())

    # Relationships
    donor = relationship("User", back_populates="donations")


class DistributionRun(Base):
    """Model for distribution run attempts."""
    __tablename__ = "distribution_runs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    run_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, completed
    total_beneficiaries = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    admin = relationship("User", back_populates="distribution_runs")
    distributions = relationship("Distribution", back_populates="run")


class Distribution(Base):
    """Model for individual distributions to employees."""
    __tablename__ = "distributions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("distribution_runs.id"), nullable=False)
    amount = Column(Float, nullable=False)
    pickup_slot = Column(String(50))  # e.g., "2024-01-15 10:00-10:30"
    notification_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    employee = relationship("Employee", back_populates="distributions")
    run = relationship("DistributionRun", back_populates="distributions")


class Feedback(Base):
    """Model for user feedback."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feedback_text = Column(Text, nullable=False)
    sentiment = Column(String(20))  # positive, negative, neutral
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User")