"""
Authentication and user management database models.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from marketplace.storage.db import Base
import secrets
import hashlib


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Tier (free, starter, pro, enterprise)
    tier: Mapped[str] = mapped_column(String, default="free", nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord",
        back_populates="user"
    )


class APIKey(Base):
    """API key model for programmatic access."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Key details
    key_prefix: Mapped[str] = mapped_column(String, nullable=False, index=True)  # First 12 chars for display
    key_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)  # User-friendly name

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    @staticmethod
    def generate_key() -> str:
        """Generate a secure API key: axm_<32 random chars>."""
        return f"axm_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()


class UsageRecord(Base):
    """Track API usage for billing and analytics."""
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Usage details
    endpoint: Mapped[str] = mapped_column(String, nullable=False)  # /shop, /execute, etc.
    method: Mapped[str] = mapped_column(String, nullable=False)  # GET, POST

    # Cost tracking (for future billing)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_records")


class RateLimit(Base):
    """Track rate limits per user/API key."""
    __tablename__ = "rate_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifier (user_id or API key hash)
    identifier: Mapped[str] = mapped_column(String, nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String, nullable=False)  # "user" or "api_key"

    # Rate limit window
    endpoint: Mapped[str] = mapped_column(String, nullable=False)  # /shop, /execute, or "global"
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
