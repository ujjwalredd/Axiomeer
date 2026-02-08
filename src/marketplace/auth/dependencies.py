"""
FastAPI authentication dependencies for user authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from marketplace.storage.db import SessionLocal
from marketplace.storage.users import User, APIKey
from marketplace.auth.security import verify_token
from marketplace.auth.rate_limiter import check_rate_limit
from marketplace.settings import AUTH_ENABLED, API_KEY_HEADER


# HTTP Bearer security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


def get_db():
    """
    Database session dependency.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Header(None, alias=API_KEY_HEADER),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user if credentials are provided.
    Returns None if no credentials or invalid credentials (backward compatible).

    Supports two authentication methods:
    1. API Key via X-API-Key header
    2. JWT token via Authorization: Bearer <token> header

    Args:
        credentials: Optional HTTP Bearer credentials (JWT token)
        api_key: Optional API key from X-API-Key header
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not AUTH_ENABLED:
        return None

    # Try API key authentication first
    if api_key:
        key_hash = APIKey.hash_key(api_key)
        api_key_obj = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()

        if api_key_obj:
            # Update last_used timestamp
            api_key_obj.last_used = datetime.now(timezone.utc)
            db.commit()

            # Get the associated user
            user = db.query(User).filter(User.id == api_key_obj.user_id).first()
            if user and user.is_active:
                return user

    # Try JWT token authentication
    if credentials:
        payload = verify_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = db.query(User).filter(
                    User.id == int(user_id),
                    User.is_active == True
                ).first()
                if user:
                    # Update last_login
                    user.last_login = datetime.now(timezone.utc)
                    db.commit()
                    return user

    # No valid authentication found
    return None


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """
    Get the current authenticated user (required).
    Raises 401 if not authenticated when AUTH_ENABLED=true.
    Returns anonymous user when AUTH_ENABLED=false (backward compatible).

    Args:
        user: Optional user from get_current_user_optional

    Returns:
        User object

    Raises:
        HTTPException: 401 if not authenticated and AUTH_ENABLED=true
    """
    if not AUTH_ENABLED:
        # Backward compatibility: create anonymous user when auth disabled
        # This allows endpoints to work without authentication
        now = datetime.now(timezone.utc)
        return User(
            id=0,
            email="anonymous@axiomeer.local",
            username="anonymous",
            password_hash="",
            tier="free",
            is_active=True,
            is_verified=False,
            created_at=now,
            last_login=now
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please provide valid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current user and verify they're active.

    Args:
        current_user: Current authenticated user

    Returns:
        User object if active

    Raises:
        HTTPException: 400 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    return current_user


async def check_user_rate_limit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Check rate limits for the current user.
    Combines authentication and rate limiting in one dependency.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        User object if rate limit not exceeded

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    check_rate_limit(db, current_user)
    return current_user
