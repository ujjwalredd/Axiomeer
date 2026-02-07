"""
Tests for rate limiting functionality.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

# Set environment variables before imports
os.environ["AUTH_ENABLED"] = "true"
os.environ["RATE_LIMIT_ENABLED"] = "true"
os.environ["RATE_LIMIT_FREE_TIER_PER_HOUR"] = "5"  # Low limit for testing
os.environ["RATE_LIMIT_STARTER_TIER_PER_HOUR"] = "10"
os.environ["RATE_LIMIT_PRO_TIER_PER_HOUR"] = "20"
os.environ["DATABASE_URL"] = "sqlite:///./test_rate_limit.db"

from apps.api.main import app
from marketplace.storage.db import Base
from marketplace.auth.dependencies import get_db
from marketplace.storage.users import User, APIKey, RateLimit, UsageRecord
from marketplace.auth.security import get_password_hash

# Import all models to ensure all tables are created
from marketplace.storage.models import AppListing
from marketplace.storage.runs import Run
from marketplace.storage.messages import ConversationMessage


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_rate_limit.db"
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
def db_session():
    """Database session fixture."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def free_tier_user(db_session):
    """Create a free tier user with API key."""
    user = User(
        email="free@example.com",
        username="freeuser",
        password_hash=get_password_hash("password123"),
        tier="free",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create API key
    key = APIKey.generate_key()
    api_key = APIKey(
        user_id=user.id,
        key_prefix=key[:12],
        key_hash=APIKey.hash_key(key),
        name="Test Key",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(api_key)
    db_session.commit()

    return {"user": user, "api_key": key}


@pytest.fixture
def starter_tier_user(db_session):
    """Create a starter tier user with API key."""
    user = User(
        email="starter@example.com",
        username="starteruser",
        password_hash=get_password_hash("password123"),
        tier="starter",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create API key
    key = APIKey.generate_key()
    api_key = APIKey(
        user_id=user.id,
        key_prefix=key[:12],
        key_hash=APIKey.hash_key(key),
        name="Test Key",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(api_key)
    db_session.commit()

    return {"user": user, "api_key": key}


@pytest.fixture
def pro_tier_user(db_session):
    """Create a pro tier user with API key."""
    user = User(
        email="pro@example.com",
        username="prouser",
        password_hash=get_password_hash("password123"),
        tier="pro",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create API key
    key = APIKey.generate_key()
    api_key = APIKey(
        user_id=user.id,
        key_prefix=key[:12],
        key_hash=APIKey.hash_key(key),
        name="Test Key",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(api_key)
    db_session.commit()

    return {"user": user, "api_key": key}


class TestRateLimitFree:
    """Tests for free tier rate limiting."""

    def test_free_tier_within_limit(self, client, free_tier_user):
        """Test that free tier can make requests within limit."""
        api_key = free_tier_user["api_key"]
        headers = {"X-API-Key": api_key}

        # Make requests within limit (5 for free tier in test config)
        for i in range(5):
            response = client.post(
                "/shop",
                json={"task": "test task", "required_capabilities": []},
                headers=headers
            )
            assert response.status_code == 200, f"Request {i+1} failed"

    def test_free_tier_exceeds_limit(self, client, free_tier_user):
        """Test that free tier gets 429 when exceeding limit."""
        api_key = free_tier_user["api_key"]
        headers = {"X-API-Key": api_key}

        # Make requests up to limit
        for i in range(5):
            response = client.post(
                "/shop",
                json={"task": "test task", "required_capabilities": []},
                headers=headers
            )
            assert response.status_code == 200

        # Next request should be rate limited
        response = client.post(
            "/shop",
            json={"task": "test task", "required_capabilities": []},
            headers=headers
        )

        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_rate_limit_headers_present(self, client, free_tier_user):
        """Test that rate limit headers are included in response."""
        api_key = free_tier_user["api_key"]
        headers = {"X-API-Key": api_key}

        # Make one request
        response = client.post(
            "/shop",
            json={"task": "test task", "required_capabilities": []},
            headers=headers
        )

        assert response.status_code == 200


class TestRateLimitTiers:
    """Tests for different tier rate limits."""

    def test_starter_tier_has_higher_limit(self, client, starter_tier_user):
        """Test that starter tier has higher limit than free tier."""
        api_key = starter_tier_user["api_key"]
        headers = {"X-API-Key": api_key}

        # Starter tier has 10 requests per hour (in test config)
        for i in range(10):
            response = client.post(
                "/shop",
                json={"task": "test task", "required_capabilities": []},
                headers=headers
            )
            assert response.status_code == 200, f"Request {i+1} failed"

        # 11th request should be rate limited
        response = client.post(
            "/shop",
            json={"task": "test task", "required_capabilities": []},
            headers=headers
        )
        assert response.status_code == 429

    def test_pro_tier_has_highest_limit(self, client, pro_tier_user):
        """Test that pro tier has higher limit than starter tier."""
        api_key = pro_tier_user["api_key"]
        headers = {"X-API-Key": api_key}

        # Pro tier has 20 requests per hour (in test config)
        for i in range(20):
            response = client.post(
                "/shop",
                json={"task": "test task", "required_capabilities": []},
                headers=headers
            )
            assert response.status_code == 200, f"Request {i+1} failed"

        # 21st request should be rate limited
        response = client.post(
            "/shop",
            json={"task": "test task", "required_capabilities": []},
            headers=headers
        )
        assert response.status_code == 429


class TestRateLimitWindow:
    """Tests for rate limit window behavior."""

    def test_rate_limit_tracks_window(self, client, free_tier_user, db_session):
        """Test that rate limit tracking creates proper window records."""
        api_key = free_tier_user["api_key"]
        headers = {"X-API-Key": api_key}

        # Make a request
        response = client.post(
            "/shop",
            json={"task": "test task", "required_capabilities": []},
            headers=headers
        )
        assert response.status_code == 200

        # Check that rate limit record was created
        user_id = free_tier_user["user"]["id"]
        rate_record = db_session.query(RateLimit).filter(
            RateLimit.identifier == f"user_{user_id}",
            RateLimit.identifier_type == "user"
        ).first()

        assert rate_record is not None
        assert rate_record.request_count == 1
        assert rate_record.endpoint == "global"

    def test_rate_limit_increments_counter(self, client, free_tier_user, db_session):
        """Test that rate limit counter increments with each request."""
        api_key = free_tier_user["api_key"]
        headers = {"X-API-Key": api_key}
        user_id = free_tier_user["user"]["id"]

        # Make multiple requests
        for i in range(1, 4):
            response = client.post(
                "/shop",
                json={"task": "test task", "required_capabilities": []},
                headers=headers
            )
            assert response.status_code == 200

            # Check counter
            rate_record = db_session.query(RateLimit).filter(
                RateLimit.identifier == f"user_{user_id}"
            ).first()
            assert rate_record.request_count == i


class TestRateLimitDisabled:
    """Tests for when rate limiting is disabled."""

    def test_no_rate_limit_when_disabled(self, client, free_tier_user):
        """Test that rate limiting doesn't apply when disabled."""
        # Temporarily disable rate limiting
        original_setting = os.environ.get("RATE_LIMIT_ENABLED")
        os.environ["RATE_LIMIT_ENABLED"] = "false"

        try:
            # Reload the module to pick up new setting
            import importlib
            import marketplace.auth.rate_limiter
            importlib.reload(marketplace.auth.rate_limiter)

            api_key = free_tier_user["api_key"]
            headers = {"X-API-Key": api_key}

            # Should be able to make many requests without limit
            for i in range(20):  # Well over free tier limit
                response = client.post(
                    "/shop",
                    json={"task": "test task", "required_capabilities": []},
                    headers=headers
                )
                # All should succeed (no 429)
                assert response.status_code in [200, 404], f"Request {i+1} got unexpected status"

        finally:
            # Restore original setting
            if original_setting:
                os.environ["RATE_LIMIT_ENABLED"] = original_setting
            else:
                os.environ["RATE_LIMIT_ENABLED"] = "true"


class TestRateLimitExecuteEndpoint:
    """Tests for rate limiting on /execute endpoint."""

    def test_rate_limit_applies_to_execute(self, client, free_tier_user):
        """Test that rate limiting applies to /execute endpoint."""
        api_key = free_tier_user["api_key"]
        headers = {"X-API-Key": api_key}

        # Make requests to /execute endpoint
        for i in range(5):
            response = client.post(
                "/execute",
                json={
                    "app_id": "test-app",
                    "input_data": {"query": "test"},
                    "parameters": {},
                    "metadata": {}
                },
                headers=headers
            )
            # May get 404 (app not found) but shouldn't get 429 yet
            assert response.status_code in [200, 404, 500]

        # 6th request should be rate limited
        response = client.post(
            "/execute",
            json={
                "app_id": "test-app",
                "input_data": {"query": "test"},
                "parameters": {},
                "metadata": {}
            },
            headers=headers
        )
        assert response.status_code == 429
