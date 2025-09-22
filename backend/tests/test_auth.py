"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User
from app.auth import get_password_hash


def test_register_user(client: TestClient, db_session: Session):
    """Test user registration."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpass123",
            "role": "donor"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data

    # Verify user was created in database
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    assert user is not None
    assert user.name == "Test User"


def test_register_duplicate_email(client: TestClient, db_session: Session):
    """Test registration with duplicate email."""
    # Create user first
    db_session.add(User(
        name="Existing User",
        email="existing@example.com",
        password_hash=get_password_hash("pass123"),
        role="donor"
    ))
    db_session.commit()

    response = client.post(
        "/api/auth/register",
        json={
            "name": "New User",
            "email": "existing@example.com",
            "password": "newpass123",
            "role": "donor"
        }
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client: TestClient, db_session: Session):
    """Test successful login."""
    # Create user
    hashed_password = get_password_hash("testpass123")
    db_session.add(User(
        name="Login Test",
        email="login@example.com",
        password_hash=hashed_password,
        role="donor",
        is_active=True
    ))
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        data={
            "username": "login@example.com",
            "password": "testpass123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_login_invalid_credentials(client: TestClient, db_session: Session):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "wrongpass"
        }
    )

    assert response.status_code == 401


def test_login_inactive_user(client: TestClient, db_session: Session):
    """Test login with inactive user."""
    hashed_password = get_password_hash("testpass123")
    db_session.add(User(
        name="Inactive User",
        email="inactive@example.com",
        password_hash=hashed_password,
        role="donor",
        is_active=False
    ))
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        data={
            "username": "inactive@example.com",
            "password": "testpass123"
        }
    )

    assert response.status_code == 400