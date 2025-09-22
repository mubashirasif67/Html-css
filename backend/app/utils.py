"""
Utility functions for the application.

Includes CNIC validation/normalization, hash generation for transparency,
and other common helper functions.
"""
import re
import hashlib
from typing import Optional
from .models import EmployeeGrade


def normalize_cnic(cnic: str) -> str:
    """Normalize CNIC to standard format: XXXXX-XXXXXXX-X"""
    # Remove all non-digits
    digits = re.sub(r'\D', '', cnic)
    if len(digits) != 13:
        raise ValueError("CNIC must be exactly 13 digits")
    return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"


def extract_family_key(cnic: str) -> str:
    """Extract family key from CNIC (first 7 digits after normalization)."""
    normalized = normalize_cnic(cnic)
    return normalized.split('-')[1]  # XXXXX-XXXXXXX-X -> XXXXXXX


def validate_cnic(cnic: str) -> bool:
    """Validate CNIC format."""
    try:
        normalize_cnic(cnic)
        return True
    except ValueError:
        return False


def generate_transaction_hash(donation_data: dict) -> str:
    """Generate SHA256 hash for donation transparency."""
    # Create a string from relevant donation data
    hash_string = f"{donation_data['donor_name']}{donation_data['amount']}{donation_data['donation_type']}"
    return hashlib.sha256(hash_string.encode()).hexdigest()


def mask_cnic(cnic: str, visible_chars: int = 4) -> str:
    """Mask CNIC for privacy, showing only first and last visible_chars."""
    normalized = normalize_cnic(cnic)
    parts = normalized.split('-')
    masked = f"{parts[0][:visible_chars]}***-***{parts[2]}"
    return masked


def grade_to_int(grade: EmployeeGrade) -> int:
    """Convert grade enum to integer."""
    return int(grade.value)


def int_to_grade(grade_int: int) -> EmployeeGrade:
    """Convert integer to grade enum."""
    return EmployeeGrade(str(grade_int))