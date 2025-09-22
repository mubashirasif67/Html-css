"""
Tests for employee endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, Employee
from app.auth import get_password_hash


def test_create_employee(client: TestClient, db_session: Session):
    """Test creating an employee."""
    # Create admin user first
    admin = User(
        name="Admin",
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

    # Create employee
    response = client.post(
        "/api/employees/",
        json={
            "name": "John Doe",
            "father_name": "Jane Doe",
            "cnic": "12345-1234567-1",
            "grade": "5",
            "designation": "Teacher",
            "mobile": "03123456789",
            "family_size": 4,
            "address": "Test Address"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["cnic"] == "12345-1234567-1"
    assert data["family_key"] == "1234567"


def test_create_employee_invalid_cnic(client: TestClient, db_session: Session):
    """Test creating employee with invalid CNIC."""
    # Create admin user first
    admin = User(
        name="Admin",
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

    # Create employee with invalid CNIC
    response = client.post(
        "/api/employees/",
        json={
            "name": "John Doe",
            "father_name": "Jane Doe",
            "cnic": "invalid-cnic",
            "grade": "5",
            "mobile": "03123456789",
            "family_size": 4
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400


def test_list_employees(client: TestClient, db_session: Session):
    """Test listing employees."""
    # Create admin user
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        role="admin"
    )
    db_session.add(admin)
    db_session.commit()

    # Create test employees
    for i in range(3):
        employee = Employee(
            user_id=admin.id,
            name=f"Employee {i}",
            father_name=f"Father {i}",
            cnic=f"12345-123456{i}-1",
            family_key=f"123456{i}",
            grade="5",
            mobile=f"0312345678{i}",
            is_eligible=True,
            eligibility_score=0.8
        )
        db_session.add(employee)
    db_session.commit()

    # Login as admin
    login_response = client.post(
        "/api/auth/login",
        data={"username": "admin@test.com", "password": "admin123"}
    )
    token = login_response.json()["access_token"]

    # List employees
    response = client.get(
        "/api/employees/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "Employee 0"