#!/usr/bin/env python
"""
Seed database with sample data for testing
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime, timedelta
import random
import logging
from faker import Faker

from app.database import SessionLocal, init_db
from app.models.user import User, UserRole
from app.models.employee import Employee
from app.models.donation import Donation, DonationType, PaymentMethod
from app.auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()


def generate_cnic():
    """Generate a valid-looking CNIC"""
    part1 = str(random.randint(10000, 99999))
    part2 = str(random.randint(1000000, 9999999))
    part3 = str(random.randint(1, 9))
    return f"{part1}-{part2}-{part3}"


def seed_users(db):
    """Seed users table"""
    logger.info("Seeding users...")
    
    users_data = [
        {
            "email": "admin@blessings.org",
            "name": "Admin User",
            "password": "Admin@123456",
            "role": UserRole.ADMIN,
            "phone": "+923001234567"
        },
        {
            "email": "staff@blessings.org",
            "name": "Staff Member",
            "password": "Staff@123456",
            "role": UserRole.STAFF,
            "phone": "+923012345678"
        },
        {
            "email": "donor1@example.com",
            "name": "Ali Ahmed",
            "password": "Donor@123456",
            "role": UserRole.DONOR,
            "phone": "+923023456789"
        },
        {
            "email": "donor2@example.com",
            "name": "Sara Khan",
            "password": "Donor@123456",
            "role": UserRole.DONOR,
            "phone": "+923034567890"
        }
    ]
    
    for user_data in users_data:
        # Check if user exists
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
            user = User(
                email=user_data["email"],
                name=user_data["name"],
                password_hash=get_password_hash(user_data["password"]),
                role=user_data["role"],
                phone=user_data.get("phone"),
                cnic=generate_cnic(),
                is_active=True
            )
            db.add(user)
    
    db.commit()
    logger.info(f"Seeded {len(users_data)} users")


def seed_employees(db, count=200):
    """Seed employees table"""
    logger.info(f"Seeding {count} employees...")
    
    # Pakistani names for realism
    first_names = ["Muhammad", "Ali", "Ahmed", "Hassan", "Fatima", "Ayesha", "Sara", "Zainab", 
                   "Usman", "Omar", "Ibrahim", "Maryam", "Khadija", "Bilal", "Hamza"]
    last_names = ["Khan", "Ahmed", "Ali", "Shah", "Malik", "Hussain", "Iqbal", "Rahman", 
                  "Siddiqui", "Qureshi", "Bukhari", "Mirza", "Raza", "Haider", "Javed"]
    
    # Generate campus-like location clusters
    location_clusters = [
        {"lat": 24.8607, "lon": 67.0011, "name": "Karachi Central"},
        {"lat": 24.9056, "lon": 67.0822, "name": "Karachi East"},
        {"lat": 24.8103, "lon": 67.0225, "name": "Karachi West"},
        {"lat": 31.5204, "lon": 74.3587, "name": "Lahore"},
        {"lat": 33.6844, "lon": 73.0479, "name": "Islamabad"},
    ]
    
    employees = []
    family_keys_used = set()
    
    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        father_first = random.choice(first_names)
        
        cnic = generate_cnic()
        family_key = cnic[:7]
        
        # Create family groups (20% chance of same family)
        if random.random() < 0.2 and family_keys_used:
            family_key = random.choice(list(family_keys_used))
        
        family_keys_used.add(family_key)
        
        # Select location cluster
        cluster = random.choice(location_clusters)
        lat = cluster["lat"] + random.uniform(-0.05, 0.05)
        lon = cluster["lon"] + random.uniform(-0.05, 0.05)
        
        employee = Employee(
            cnic=cnic,
            name=f"{first_name} {last_name}",
            father_name=f"{father_first} {last_name}",
            grade=random.randint(1, 22),
            designation=random.choice(["Assistant", "Clerk", "Officer", "Senior Officer", "Manager"]),
            mobile=f"+9230{random.randint(10000000, 99999999)}",
            email=f"{first_name.lower()}.{last_name.lower()}{i}@example.com",
            address=f"House {random.randint(1, 999)}, Street {random.randint(1, 50)}, {cluster['name']}",
            family_size=random.randint(1, 8),
            income_estimate=random.randint(15000, 150000),
            previous_aid_count=random.randint(0, 5),
            lat=lat,
            lon=lon,
            is_eligible=random.random() > 0.2,  # 80% eligible
            eligibility_score=random.uniform(0.3, 0.9),
            fraud_flag=random.random() < 0.05,  # 5% fraud flagged
            family_key=family_key,
            is_family_head=random.random() > 0.3
        )
        
        employees.append(employee)
    
    # Bulk insert
    db.bulk_save_objects(employees)
    db.commit()
    
    logger.info(f"Seeded {count} employees")


def seed_donations(db, count=500):
    """Seed donations table"""
    logger.info(f"Seeding {count} donations...")
    
    # Get donor users
    donors = db.query(User).filter(User.role == UserRole.DONOR).all()
    
    donations = []
    
    for i in range(count):
        # Random donation data
        is_anonymous = random.random() < 0.1  # 10% anonymous
        
        donation = Donation(
            donor_id=random.choice(donors).id if donors and not is_anonymous else None,
            donor_name=fake.name() if not is_anonymous else "Anonymous",
            donor_email=fake.email() if not is_anonymous else None,
            donor_phone=f"+9230{random.randint(10000000, 99999999)}" if not is_anonymous else None,
            donor_cnic=generate_cnic() if not is_anonymous and random.random() > 0.5 else None,
            donation_type=random.choice(list(DonationType)),
            amount=random.choice([500, 1000, 2000, 5000, 10000, 25000, 50000, 100000]),
            currency="PKR",
            payment_method=random.choice(list(PaymentMethod)),
            transaction_id=f"TXN-{datetime.now().strftime('%Y%m%d')}-{i:06d}",
            is_anonymous=is_anonymous,
            is_verified=random.random() > 0.3,  # 70% verified
            notes=fake.sentence() if random.random() > 0.7 else None,
            created_at=datetime.now() - timedelta(days=random.randint(0, 365))
        )
        
        # Generate blockchain hash
        donations.append(donation)
    
    # Bulk insert
    db.bulk_save_objects(donations)
    db.commit()
    
    # Generate blockchain hashes
    all_donations = db.query(Donation).all()
    for donation in all_donations:
        if not donation.blockchain_hash:
            donation.generate_blockchain_hash()
    
    db.commit()
    
    logger.info(f"Seeded {count} donations")


def main():
    """Main seeding function"""
    logger.info("Starting database seeding...")
    
    # Initialize database
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Seed data
        seed_users(db)
        seed_employees(db, count=200)
        seed_donations(db, count=500)
        
        logger.info("Database seeding completed successfully!")
        
        # Print summary
        user_count = db.query(User).count()
        employee_count = db.query(Employee).count()
        donation_count = db.query(Donation).count()
        
        print("\n" + "="*50)
        print("DATABASE SEEDING SUMMARY")
        print("="*50)
        print(f"Users: {user_count}")
        print(f"Employees: {employee_count}")
        print(f"Donations: {donation_count}")
        print("="*50)
        print("\nDefault Admin Credentials:")
        print("Email: admin@blessings.org")
        print("Password: Admin@123456")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()