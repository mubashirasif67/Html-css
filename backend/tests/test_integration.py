"""
Integration tests for the complete system
"""

import pytest
from fastapi.testclient import TestClient
import time
from app.main import app
from app.database import SessionLocal, init_db

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_database():
    """Setup test database"""
    init_db()
    yield
    # Cleanup if needed


def test_complete_donation_flow(setup_database):
    """Test complete donation flow from submission to receipt"""
    
    # 1. Submit a donation
    donation_data = {
        "donor_name": "Integration Test Donor",
        "donor_email": "test@integration.com",
        "donor_phone": "+923001234567",
        "donation_type": "zakat",
        "amount": 10000.0,
        "payment_method": "bank_transfer",
        "is_anonymous": False
    }
    
    response = client.post("/api/donations", json=donation_data)
    assert response.status_code == 201
    
    donation = response.json()
    assert donation["id"] > 0
    assert donation["amount"] == 10000.0
    assert donation["blockchain_hash"] is not None
    
    # 2. Verify the donation was created
    get_response = client.get(f"/api/donations/{donation['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == donation["id"]


def test_employee_registration_and_eligibility(setup_database):
    """Test employee registration and eligibility check"""
    
    # First, login as admin
    login_response = client.post(
        "/api/auth/login/json",
        json={
            "email": "admin@blessings.org",
            "password": "Admin@123456"
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Register an employee
        employee_data = {
            "name": "Test Employee",
            "cnic": "12345-1234567-1",
            "father_name": "Test Father",
            "grade": 10,
            "designation": "Test Position",
            "mobile": "+923001234567",
            "email": "test.employee@example.com",
            "address": "Test Address",
            "family_size": 4,
            "income_estimate": 30000.0
        }
        
        response = client.post(
            "/api/employees",
            json=employee_data,
            headers=headers
        )
        
        if response.status_code == 201:
            employee = response.json()
            assert employee["id"] > 0
            assert employee["eligibility_score"] >= 0
            assert employee["family_key"] is not None


def test_ocr_receipt_upload(setup_database):
    """Test OCR receipt upload"""
    
    # Create a simple test image
    from PIL import Image
    import io
    
    img = Image.new('RGB', (200, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    files = {"file": ("test_receipt.png", img_bytes, "image/png")}
    
    response = client.post("/api/donations/upload_receipt", files=files)
    
    assert response.status_code == 200
    result = response.json()
    assert "confidence" in result
    assert "currency" in result
    assert "processing_time" in result


def test_distribution_generation(setup_database):
    """Test distribution generation"""
    
    # Login as admin
    login_response = client.post(
        "/api/auth/login/json",
        json={
            "email": "admin@blessings.org",
            "password": "Admin@123456"
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Generate distribution
        response = client.get(
            "/api/admin/distribution/run",
            params={
                "distribution_date": "2024-01-15",
                "max_beneficiaries": 50
            },
            headers=headers
        )
        
        if response.status_code == 200:
            distribution = response.json()
            assert "distribution_id" in distribution
            assert "total_beneficiaries" in distribution
            assert "beneficiaries" in distribution


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    
    health = response.json()
    assert health["status"] in ["healthy", "unhealthy"]
    assert "version" in health
    assert "features" in health


def test_api_documentation():
    """Test API documentation availability"""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    openapi = response.json()
    assert "openapi" in openapi
    assert "paths" in openapi