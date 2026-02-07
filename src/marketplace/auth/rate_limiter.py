"""
Rate limiting functionality for API endpoints.
"""

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from marketplace.storage.users import User, RateLimit
from marketplace.settings import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_FREE_TIER_PER_HOUR,
    RATE_LIMIT_STARTER_TIER_PER_HOUR,
    RATE_LIMIT_PRO_TIER_PER_HOUR,
)


# Tier-based rate limits (requests per hour)
TIER_LIMITS = {
    "free": RATE_LIMIT_FREE_TIER_PER_HOUR,
    "starter": RATE_LIMIT_STARTER_TIER_PER_HOUR,
    "pro": RATE_LIMIT_PRO_TIER_PER_HOUR,
    "enterprise": 100000,  # Very high limit for enterprise
}


def check_rate_limit(
    db: Session,
    user: User,
    endpoint: str = "global",
    window_minutes: int = 60
) -> None:
    """
    Check if user is within their rate limit for the given endpoint.
    Raises HTTPException 429 if rate limit is exceeded.

    Args:
        db: Database session
        user: User to check rate limit for
        endpoint: Endpoint being accessed (default: "global" for all endpoints)
        window_minutes: Rate limit window in minutes (default: 60 for hourly)

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    if not RATE_LIMIT_ENABLED:
        return

    # Get tier-based limit
    limit = TIER_LIMITS.get(user.tier, RATE_LIMIT_FREE_TIER_PER_HOUR)

    # Calculate window start time
    window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    # Create identifier for this user
    identifier = f"user_{user.id}"

    # Find existing rate limit record within current window
    rate_record = db.query(RateLimit).filter(
        RateLimit.identifier == identifier,
        RateLimit.identifier_type == "user",
        RateLimit.endpoint == endpoint,
        RateLimit.window_start >= window_start
    ).first()

    if not rate_record:
        # Create new rate limit window
        rate_record = RateLimit(
            identifier=identifier,
            identifier_type="user",
            endpoint=endpoint,
            window_start=datetime.now(timezone.utc),
            request_count=1
        )
        db.add(rate_record)
        db.commit()
        return

    # Check if limit exceeded
    if rate_record.request_count >= limit:
        # Calculate time until window resets
        time_until_reset = (rate_record.window_start + timedelta(minutes=window_minutes)) - datetime.now(timezone.utc)
        reset_seconds = int(time_until_reset.total_seconds())

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Tier: {user.tier}, Limit: {limit} requests per hour. Try again in {reset_seconds} seconds.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_seconds),
                "Retry-After": str(reset_seconds)
            }
        )

    # Increment request count
    rate_record.request_count += 1
    db.commit()


def get_rate_limit_status(db: Session, user: User, endpoint: str = "global") -> dict:
    """
    Get current rate limit status for a user.

    Args:
        db: Database session
        user: User to check
        endpoint: Endpoint to check (default: "global")

    Returns:
        Dictionary with rate limit information
    """
    if not RATE_LIMIT_ENABLED:
        return {
            "enabled": False,
            "limit": None,
            "remaining": None,
            "reset_at": None
        }

    limit = TIER_LIMITS.get(user.tier, RATE_LIMIT_FREE_TIER_PER_HOUR)
    identifier = f"user_{user.id}"
    window_start = datetime.now(timezone.utc) - timedelta(hours=1)

    rate_record = db.query(RateLimit).filter(
        RateLimit.identifier == identifier,
        RateLimit.identifier_type == "user",
        RateLimit.endpoint == endpoint,
        RateLimit.window_start >= window_start
    ).first()

    if not rate_record:
        return {
            "enabled": True,
            "tier": user.tier,
            "limit": limit,
            "remaining": limit,
            "reset_at": None,
            "current_count": 0
        }

    remaining = max(0, limit - rate_record.request_count)
    reset_at = rate_record.window_start + timedelta(hours=1)

    return {
        "enabled": True,
        "tier": user.tier,
        "limit": limit,
        "remaining": remaining,
        "reset_at": reset_at.isoformat(),
        "current_count": rate_record.request_count
    }
