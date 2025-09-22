"""
Smoke tests for the entire system.

These tests verify that the system starts up correctly and
basic functionality works end-to-end.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User
from app.auth import get_password_hash


def test_health_check(client: TestClient):
    """Test that the health check endpoint works."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client: TestClient):
    """Test that the root endpoint returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to Blessings Distribution System" in response.text


def test_full_user_flow(client: TestClient, db_session: Session):
    """Test a complete user flow from registration to login."""
    # Register user
    register_response = client.post(
        "/api/auth/register",
        json={
            "name": "Smoke Test User",
            "email": "smoke@test.com",
            "password": "smokepass123",
            "role": "donor"
        }
    )

    assert register_response.status_code == 201
    register_data = register_response.json()
    assert "access_token" in register_data

    # Login
    login_response = client.post(
        "/api/auth/login",
        data={
            "username": "smoke@test.com",
            "password": "smokepass123"
        }
    )

    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data

    # Use token to access protected endpoint
    token = login_data["access_token"]
    protected_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert protected_response.status_code == 200
    user_data = protected_response.json()
    assert user_data["name"] == "Smoke Test User"
    assert user_data["email"] == "smoke@test.com"


def test_admin_functionality(client: TestClient, db_session: Session):
    """Test basic admin functionality."""
    # Create admin user
    admin = User(
        name="Admin User",
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        role="admin"
    )
    db_session.add(admin)
    db_session.commit()

    # Login as admin
    login_response = client.post(
        "/api/auth/login",
        data={"username": "admin@test.com", "password": "admin123"}
    )
    token = login_response.json()["access_token"]

    # Create employee (admin functionality)
    employee_response = client.post(
        "/api/employees/",
        json={
            "name": "Test Employee",
            "father_name": "Test Father",
            "cnic": "12345-1234567-1",
            "grade": "5",
            "mobile": "03123456789",
            "family_size": 3
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert employee_response.status_code == 201
    employee_data = employee_response.json()
    assert employee_data["name"] == "Test Employee"