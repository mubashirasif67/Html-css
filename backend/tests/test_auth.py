"""
Tests for authentication endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal
from app.models.user import User
from app.auth import get_password_hash

client = TestClient(app)


def test_register_user():
    """Test user registration"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "TestPass123!",
            "role": "donor",
            "phone": "+923001234567"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "test@example.com"


def test_login():
    """Test user login"""
    # First create a user
    db = SessionLocal()
    user = User(
        email="login_test@example.com",
        name="Login Test",
        password_hash=get_password_hash("TestPass123!"),
        role="donor"
    )
    db.add(user)
    db.commit()
    db.close()
    
    # Test login
    response = client.post(
        "/api/auth/login/json",
        json={
            "email": "login_test@example.com",
            "password": "TestPass123!"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_invalid_login():
    """Test login with invalid credentials"""
    response = client.post(
        "/api/auth/login/json",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPass123!"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_refresh_token():
    """Test token refresh"""
    # First login to get tokens
    db = SessionLocal()
    user = User(
        email="refresh_test@example.com",
        name="Refresh Test",
        password_hash=get_password_hash("TestPass123!"),
        role="donor"
    )
    db.add(user)
    db.commit()
    db.close()
    
    login_response = client.post(
        "/api/auth/login/json",
        json={
            "email": "refresh_test@example.com",
            "password": "TestPass123!"
        }
    )
    
    refresh_token = login_response.json()["refresh_token"]
    
    # Test refresh
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data