"""
Tests for donation endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, Donation
from app.auth import get_password_hash


def test_create_donation(client: TestClient, db_session: Session):
    """Test creating a donation."""
    # Create donor user
    donor = User(
        name="Donor",
        email="donor@test.com",
        password_hash=get_password_hash("donor123"),
        role="donor"
    )
    db_session.add(donor)
    db_session.commit()

    # Login as donor
    login_response = client.post(
        "/api/auth/login",
        data={"username": "donor@test.com", "password": "donor123"}
    )
    token = login_response.json()["access_token"]

    # Create donation
    response = client.post(
        "/api/donations/",
        data={
            "donor_name": "Test Donor",
            "donor_email": "donor@test.com",
            "amount": 5000,
            "donation_type": "zakat"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 5000
    assert data["donation_type"] == "zakat"
    assert "transaction_hash" in data


def test_list_donations(client: TestClient, db_session: Session):
    """Test listing donations for a user."""
    # Create donor user
    donor = User(
        name="Donor",
        email="donor@test.com",
        password_hash=get_password_hash("donor123"),
        role="donor"
    )
    db_session.add(donor)
    db_session.commit()

    # Create test donations
    for i in range(3):
        donation = Donation(
            donor_id=donor.id,
            donor_name="Test Donor",
            amount=1000 * (i + 1),
            donation_type="general"
        )
        db_session.add(donation)
    db_session.commit()

    # Login as donor
    login_response = client.post(
        "/api/auth/login",
        data={"username": "donor@test.com", "password": "donor123"}
    )
    token = login_response.json()["access_token"]

    # List donations
    response = client.get(
        "/api/donations/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_list_all_donations_admin_only(client: TestClient, db_session: Session):
    """Test that only admins can list all donations."""
    # Create regular user
    user = User(
        name="User",
        email="user@test.com",
        password_hash=get_password_hash("user123"),
        role="donor"
    )
    db_session.add(user)
    db_session.commit()

    # Login as regular user
    login_response = client.post(
        "/api/auth/login",
        data={"username": "user@test.com", "password": "user123"}
    )
    token = login_response.json()["access_token"]

    # Try to access all donations
    response = client.get(
        "/api/donations/all",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403