"""
Seed data script for populating the database with sample data.

This script creates sample users, employees, and donations for testing.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import User, Employee, Donation
from app.auth import get_password_hash
from app.utils import normalize_cnic, extract_family_key
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker('en_PK')  # Pakistan locale


def create_sample_users(db: Session):
    """Create sample users."""
    # Create admin user
    admin = User(
        name="Admin User",
        email="admin@blessings.org",
        password_hash=get_password_hash("admin123"),
        role="admin",
        is_active=True
    )
    db.add(admin)

    # Create sample donors
    for i in range(10):
        donor = User(
            name=fake.name(),
            email=f"donor{i+1}@example.com",
            password_hash=get_password_hash("donor123"),
            role="donor",
            is_active=True
        )
        db.add(donor)

    db.commit()
    print("Created sample users")


def create_sample_employees(db: Session):
    """Create sample employees/beneficiaries."""
    # Get admin user
    admin = db.query(User).filter(User.role == "admin").first()

    # Create sample employees
    for i in range(200):
        cnic = fake.unique.random_number(digits=13, fix_len=True)
        normalized_cnic = normalize_cnic(str(cnic))
        family_key = extract_family_key(normalized_cnic)

        employee = Employee(
            user_id=admin.id,
            name=fake.name(),
            father_name=fake.name(),
            cnic=normalized_cnic,
            family_key=family_key,
            grade=random.choice(["1", "2", "3", "4", "5", "10", "15", "20"]),
            designation=fake.job(),
            mobile=f"03{random.randint(10, 99)}{random.randint(1000000, 9999999)}",
            address=fake.address(),
            family_size=random.randint(1, 8),
            latitude=33.6846 + random.uniform(-0.1, 0.1),
            longitude=73.0479 + random.uniform(-0.1, 0.1),
            is_eligible=random.choice([True, True, True, False]),  # 75% eligible
            eligibility_score=random.uniform(0.3, 0.9),
            fraud_flag=random.choice([False, False, False, False, True])  # 20% fraud flag
        )
        db.add(employee)

    db.commit()
    print("Created 200 sample employees")


def create_sample_donations(db: Session):
    """Create sample donations."""
    donors = db.query(User).filter(User.role == "donor").all()

    for i in range(500):
        donor = random.choice(donors)
        donation = Donation(
            donor_id=donor.id,
            donor_name=donor.name,
            donor_email=donor.email,
            donor_cnic=None,  # Optional
            amount=random.uniform(1000, 50000),
            donation_type=random.choice(["zakat", "sadaqah", "general"]),
            detected_amount=None,
            confidence=None,
            ocr_text=None,
            transaction_hash=f"hash_{i}",
            created_at=datetime.now() - timedelta(days=random.randint(0, 30))
        )
        db.add(donation)

    db.commit()
    print("Created 500 sample donations")


def main():
    """Main function to seed the database."""
    print("Seeding database with sample data...")

    db = SessionLocal()
    try:
        create_sample_users(db)
        create_sample_employees(db)
        create_sample_donations(db)
        print("Database seeded successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()