"""
Pydantic models for authentication requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """Request model for user signup."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Response model for user information."""
    id: int
    email: str
    username: str
    tier: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Response model for JWT token."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: Optional[int] = None
    email: Optional[str] = None


class APIKeyCreate(BaseModel):
    """Request model for creating an API key."""
    name: str = Field(..., min_length=1, max_length=100, description="Friendly name for the API key")


class APIKeyOut(BaseModel):
    """Response model for API key information (without the actual key)."""
    id: int
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyOut):
    """
    Response model when creating a new API key.
    Includes the full key, which is only shown once.
    """
    key: str = Field(..., description="Full API key - save this, it won't be shown again")
