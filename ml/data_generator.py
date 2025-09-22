"""
Synthetic data generator for ML training and testing.

This module generates realistic synthetic data for employees,
donations, and receipt images for OCR testing.
"""
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import os
from PIL import Image, ImageDraw, ImageFont
import cv2

fake = Faker('en_PK')


def generate_employee_data(n_employees: int = 1000) -> pd.DataFrame:
    """Generate synthetic employee data."""
    data = []

    for i in range(n_employees):
        # Generate CNIC
        cnic_digits = fake.unique.random_number(digits=13, fix_len=True)
        cnic = f"{cnic_digits"05d"}-{cnic_digits"07d"}-{cnic_digits % 10}"

        # Generate family key (first 7 digits after normalization)
        family_key = str(cnic_digits)[:7]

        employee = {
            'id': i + 1,
            'cnic': cnic,
            'name': fake.name(),
            'father_name': fake.name(),
            'grade': random.choice([1, 2, 3, 4, 5, 10, 15, 20]),
            'designation': fake.job(),
            'mobile': f"03{random.randint(10, 99)}{random.randint(1000000, 9999999)}",
            'address': fake.address(),
            'family_key': family_key,
            'family_size': random.randint(1, 8),
            'latitude': 33.6846 + random.uniform(-0.1, 0.1),  # Islamabad area
            'longitude': 73.0479 + random.uniform(-0.1, 0.1),
            'income_estimate': random.randint(15000, 80000),
            'previous_aid_count': random.randint(0, 10),
            'is_eligible': random.choice([True, False]),
            'eligibility_score': random.uniform(0.1, 1.0),
            'fraud_flag': random.choice([False, False, False, False, True])  # 20% fraud
        }
        data.append(employee)

    df = pd.DataFrame(data)

    # Add some realistic correlations
    # Lower grades tend to have lower income and higher eligibility
    df.loc[df['grade'] <= 5, 'income_estimate'] = df.loc[df['grade'] <= 5, 'income_estimate'] * 0.5
    df.loc[df['grade'] <= 5, 'is_eligible'] = True
    df.loc[df['grade'] <= 5, 'eligibility_score'] = df.loc[df['grade'] <= 5, 'eligibility_score'] * 1.2

    # Larger families tend to have lower income per person
    df['income_per_person'] = df['income_estimate'] / df['family_size']
    df.loc[df['income_per_person'] > 20000, 'is_eligible'] = False
    df.loc[df['income_per_person'] > 20000, 'eligibility_score'] = df.loc[df['income_per_person'] > 20000, 'eligibility_score'] * 0.5

    # Clean up
    df = df.drop('income_per_person', axis=1)
    df['is_eligible'] = df['is_eligible'].astype(bool)

    return df


def generate_donation_data(n_donations: int = 2000) -> pd.DataFrame:
    """Generate synthetic donation data."""
    data = []

    for i in range(n_donations):
        donation = {
            'id': i + 1,
            'donor_name': fake.name(),
            'donor_email': fake.email(),
            'donor_cnic': f"{fake.random_number(digits=5)"05d"}-{fake.random_number(digits=7)"07d"}-{fake.random_number(digits=1)}" if random.choice([True, False]) else None,
            'amount': random.choice([1000, 2000, 5000, 10000, 20000, 50000, 100000]),
            'donation_type': random.choice(['zakat', 'sadaqah', 'general']),
            'created_at': fake.date_time_between(start_date='-1y', end_date='now'),
            'fraud_flag': random.choice([False, False, False, False, True])  # 20% fraud
        }
        data.append(donation)

    df = pd.DataFrame(data)

    # Add fraud patterns
    fraud_donations = df[df['fraud_flag']]
    if not fraud_donations.empty:
        # Fraudulent donations tend to be from same donors
        fraud_donors = fraud_donations['donor_name'].unique()[:5]
        df.loc[df['donor_name'].isin(fraud_donors), 'fraud_flag'] = True

    return df


def generate_receipt_images(n_images: int = 100, output_dir: str = "/app/ml/synthetic_data/receipts"):
    """Generate synthetic receipt images for OCR testing."""
    os.makedirs(output_dir, exist_ok=True)

    # Sample amounts for receipts
    amounts = [1000, 2500, 5000, 7500, 10000, 15000, 20000, 25000, 50000, 100000]

    for i in range(n_images):
        # Create blank receipt image
        img = Image.new('RGB', (400, 600), color='white')
        draw = ImageDraw.Draw(img)

        # Add some noise/texture
        for _ in range(100):
            x, y = random.randint(0, 400), random.randint(0, 600)
            draw.point((x, y), fill=(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)))

        # Add receipt content
        y_pos = 50

        # Header
        draw.text((50, y_pos), "BLESSINGS DISTRIBUTION CENTER", fill=(0, 0, 0))
        y_pos += 40

        draw.text((50, y_pos), "Receipt No: " + str(random.randint(10000, 99999)), fill=(0, 0, 0))
        y_pos += 30

        draw.text((50, y_pos), "Date: " + fake.date(), fill=(0, 0, 0))
        y_pos += 40

        # Donor info
        draw.text((50, y_pos), "Donor: " + fake.name(), fill=(0, 0, 0))
        y_pos += 30

        draw.text((50, y_pos), "Amount: Rs " + str(random.choice(amounts)), fill=(0, 0, 0))
        y_pos += 40

        # Add some random text
        for _ in range(5):
            draw.text((50, y_pos), fake.sentence(nb_words=3), fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)))
            y_pos += 20

        # Add some distortion and noise
        img_array = np.array(img)

        # Add Gaussian noise
        noise = np.random.normal(0, 5, img_array.shape).astype(np.uint8)
        img_array = cv2.add(img_array, noise)

        # Slight rotation
        angle = random.uniform(-1, 1)
        M = cv2.getRotationMatrix2D((200, 300), angle, 1)
        img_array = cv2.warpAffine(img_array, M, (400, 600))

        # Save image
        filename = f"{output_dir}/receipt_{i+1"03d"}.png"
        cv2.imwrite(filename, img_array)

        print(f"Generated {filename}")


def generate_fraud_data(n_records: int = 500) -> pd.DataFrame:
    """Generate synthetic data for fraud detection training."""
    data = []

    for i in range(n_records):
        # Base features
        amount = random.uniform(1000, 100000)
        frequency = random.randint(1, 20)
        amount_variance = random.uniform(0, 1)
        time_since_last = random.uniform(0, 90)

        # Fraud patterns
        is_fraud = random.choice([False, False, False, False, True])  # 20% fraud

        # Add fraud-specific patterns
        if is_fraud:
            # Fraudulent records tend to have unusual patterns
            if random.choice([True, False]):
                amount = random.choice([999, 1001, 5001, 9999])  # Just over/under thresholds
            if random.choice([True, False]):
                frequency = random.choice([1, 20])  # Very low or very high frequency
            if random.choice([True, False]):
                time_since_last = random.choice([0, 90])  # Very recent or very old

        record = {
            'id': i + 1,
            'amount': amount,
            'frequency': frequency,
            'amount_variance': amount_variance,
            'time_since_last': time_since_last,
            'is_fraud': is_fraud
        }
        data.append(record)

    return pd.DataFrame(data)


def main():
    """Generate all synthetic datasets."""
    print("Generating synthetic datasets...")

    # Generate employee data
    employees_df = generate_employee_data(1000)
    employees_df.to_csv("/app/ml/synthetic_data/employees.csv", index=False)
    print("Generated employees.csv")

    # Generate donation data
    donations_df = generate_donation_data(2000)
    donations_df.to_csv("/app/ml/synthetic_data/donations.csv", index=False)
    print("Generated donations.csv")

    # Generate receipt images
    generate_receipt_images(100)
    print("Generated 100 synthetic receipt images")

    # Generate fraud data
    fraud_df = generate_fraud_data(500)
    fraud_df.to_csv("/app/ml/synthetic_data/fraud.csv", index=False)
    print("Generated fraud.csv")

    print("All synthetic data generated successfully!")


if __name__ == "__main__":
    main()