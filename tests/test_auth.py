"""
Tests for authentication endpoints and functionality.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

# Set environment variables before imports
os.environ["AUTH_ENABLED"] = "true"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # Disable rate limiting for auth tests
os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"

from apps.api.main import app
from marketplace.storage.db import Base, SessionLocal
from marketplace.auth.dependencies import get_db
from marketplace.storage.users import User, APIKey
from marketplace.auth.security import get_password_hash, create_access_token

# Import all models to ensure all tables are created
from marketplace.storage.models import AppListing
from marketplace.storage.runs import Run
from marketplace.storage.messages import ConversationMessage
from marketplace.storage.users import RateLimit, UsageRecord


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123"
    }


@pytest.fixture
def authenticated_user(client, test_user_data):
    """Create a user and return authentication token."""
    # Signup
    response = client.post("/auth/signup", json=test_user_data)
    assert response.status_code == 201

    # Login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"token": token, "user_data": test_user_data}


class TestSignup:
    """Tests for user signup endpoint."""

    def test_signup_success(self, client, test_user_data):
        """Test successful user signup."""
        response = client.post("/auth/signup", json=test_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["tier"] == "free"
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "password" not in data
        assert "password_hash" not in data

    def test_signup_duplicate_email(self, client, test_user_data):
        """Test signup with duplicate email."""
        # First signup
        response = client.post("/auth/signup", json=test_user_data)
        assert response.status_code == 201

        # Duplicate email
        duplicate_data = test_user_data.copy()
        duplicate_data["username"] = "differentuser"
        response = client.post("/auth/signup", json=duplicate_data)

        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_signup_duplicate_username(self, client, test_user_data):
        """Test signup with duplicate username."""
        # First signup
        response = client.post("/auth/signup", json=test_user_data)
        assert response.status_code == 201

        # Duplicate username
        duplicate_data = test_user_data.copy()
        duplicate_data["email"] = "different@example.com"
        response = client.post("/auth/signup", json=duplicate_data)

        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()

    def test_signup_invalid_email(self, client, test_user_data):
        """Test signup with invalid email."""
        invalid_data = test_user_data.copy()
        invalid_data["email"] = "invalid-email"

        response = client.post("/auth/signup", json=invalid_data)
        assert response.status_code == 422

    def test_signup_short_password(self, client, test_user_data):
        """Test signup with password too short."""
        invalid_data = test_user_data.copy()
        invalid_data["password"] = "short"

        response = client.post("/auth/signup", json=invalid_data)
        assert response.status_code == 422

    def test_signup_invalid_username(self, client, test_user_data):
        """Test signup with invalid username (special characters)."""
        invalid_data = test_user_data.copy()
        invalid_data["username"] = "test@user!"

        response = client.post("/auth/signup", json=invalid_data)
        assert response.status_code == 422


class TestLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client, test_user_data):
        """Test successful login."""
        # Signup first
        client.post("/auth/signup", json=test_user_data)

        # Login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user_data):
        """Test login with wrong password."""
        # Signup first
        client.post("/auth/signup", json=test_user_data)

        # Wrong password
        login_data = {
            "email": test_user_data["email"],
            "password": "wrongpassword"
        }
        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "email or password" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "somepassword"
        }
        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401


class TestGetCurrentUser:
    """Tests for get current user endpoint."""

    def test_get_current_user_with_jwt(self, client, authenticated_user):
        """Test getting current user info with JWT token."""
        token = authenticated_user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Use a fresh test client to avoid state issues
        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == authenticated_user["user_data"]["email"]
        assert data["username"] == authenticated_user["user_data"]["username"]

    def test_get_current_user_without_auth(self, client):
        """Test getting current user without authentication."""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}

        response = client.get("/auth/me")

        assert response.status_code == 401


class TestAPIKeys:
    """Tests for API key management endpoints."""

    def test_create_api_key(self, client, authenticated_user):
        """Test creating an API key."""
        token = authenticated_user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        key_data = {"name": "Test API Key"}
        response = client.post("/auth/api-keys", json=key_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test API Key"
        assert "key" in data  # Full key shown only once
        assert data["key"].startswith("axm_")
        assert data["key_prefix"] == data["key"][:12]
        assert data["is_active"] is True

    def test_list_api_keys(self, client, authenticated_user):
        """Test listing user's API keys."""
        token = authenticated_user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create two API keys
        client.post("/auth/api-keys", json={"name": "Key 1"}, headers=headers)
        client.post("/auth/api-keys", json={"name": "Key 2"}, headers=headers)

        # List keys
        response = client.get("/auth/api-keys", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert "key" not in data[0]  # Full key not shown in list
        assert data[0]["name"] in ["Key 1", "Key 2"]

    def test_revoke_api_key(self, client, authenticated_user):
        """Test revoking an API key."""
        token = authenticated_user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create API key
        response = client.post("/auth/api-keys", json={"name": "Test Key"}, headers=headers)
        key_id = response.json()["id"]

        # Revoke key
        response = client.delete(f"/auth/api-keys/{key_id}", headers=headers)

        assert response.status_code == 204

        # Verify key is revoked
        response = client.get("/auth/api-keys", headers=headers)
        keys = response.json()
        revoked_key = next(k for k in keys if k["id"] == key_id)
        assert revoked_key["is_active"] is False

    def test_revoke_nonexistent_key(self, client, authenticated_user):
        """Test revoking non-existent API key."""
        token = authenticated_user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete("/auth/api-keys/99999", headers=headers)

        assert response.status_code == 404


class TestAPIKeyAuthentication:
    """Tests for authenticating with API keys."""

    def test_create_and_authenticate_with_api_key(self, client, authenticated_user):
        """Test creating and using API key for authentication."""
        token = authenticated_user["token"]
        jwt_headers = {"Authorization": f"Bearer {token}"}

        # Create API key
        response = client.post("/auth/api-keys", json={"name": "Test Key"}, headers=jwt_headers)
        assert response.status_code == 201
        api_key = response.json()["key"]

        # Verify key was created (using JWT auth)
        response = client.get("/auth/api-keys", headers=jwt_headers)
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_authenticate_with_invalid_api_key(self, client):
        """Test authentication with invalid API key."""
        headers = {"X-API-Key": "axm_invalid_key"}

        response = client.get("/auth/me", headers=headers)

        assert response.status_code == 401

    def test_revoked_api_key_not_listed_as_active(self, client, authenticated_user):
        """Test that revoked API key is marked as inactive."""
        token = authenticated_user["token"]
        jwt_headers = {"Authorization": f"Bearer {token}"}

        # Create and revoke API key
        response = client.post("/auth/api-keys", json={"name": "Test Key"}, headers=jwt_headers)
        key_id = response.json()["id"]

        client.delete(f"/auth/api-keys/{key_id}", headers=jwt_headers)

        # Verify key is marked inactive
        response = client.get("/auth/api-keys", headers=jwt_headers)
        keys = response.json()
        revoked_key = next(k for k in keys if k["id"] == key_id)
        assert revoked_key["is_active"] is False


class TestBackwardCompatibility:
    """Tests for backward compatibility with AUTH_ENABLED=false."""

    def test_health_works_without_auth(self, client):
        """Test that health endpoint works when auth is disabled."""
        # Temporarily disable auth
        original_auth = os.environ.get("AUTH_ENABLED")
        os.environ["AUTH_ENABLED"] = "false"

        try:
            # Health should work without authentication
            response = client.get("/health")
            assert response.status_code == 200
        finally:
            # Restore original setting
            if original_auth:
                os.environ["AUTH_ENABLED"] = original_auth
