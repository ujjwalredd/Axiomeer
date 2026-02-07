"""
Authentication API endpoints for user signup, login, and API key management.
"""

from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from marketplace.auth.dependencies import get_db, get_current_user
from marketplace.auth.security import verify_password, get_password_hash, create_access_token
from marketplace.auth.models import (
    UserCreate,
    UserLogin,
    UserOut,
    Token,
    APIKeyCreate,
    APIKeyOut,
    APIKeyCreateResponse
)
from marketplace.storage.users import User, APIKey
from marketplace.settings import JWT_ACCESS_TOKEN_EXPIRE_MINUTES


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Args:
        user_data: User registration data (email, username, password)
        db: Database session

    Returns:
        Created user information (without password)

    Raises:
        HTTPException: 400 if email or username already exists
    """
    # Check if user with email or username already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()

    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        tier="free",
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access token.

    Args:
        user_data: User login credentials (email, password)
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: 401 if credentials are invalid or account is disabled
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is disabled"
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Create JWT access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from dependency

    Returns:
        Current user information
    """
    return current_user


@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new API key for the current user.

    Args:
        key_data: API key creation data (name)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created API key information INCLUDING the full key (shown only once)

    Note:
        The full API key is only returned once during creation.
        Store it securely as it cannot be retrieved later.
    """
    # Generate new API key
    key = APIKey.generate_key()
    key_hash = APIKey.hash_key(key)
    key_prefix = key[:12]  # axm_<8 chars> for display

    # Create API key record
    new_api_key = APIKey(
        user_id=current_user.id,
        key_prefix=key_prefix,
        key_hash=key_hash,
        name=key_data.name,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_api_key)
    db.commit()
    db.refresh(new_api_key)

    # Return response with full key (only shown once)
    return APIKeyCreateResponse(
        id=new_api_key.id,
        name=new_api_key.name,
        key_prefix=new_api_key.key_prefix,
        is_active=new_api_key.is_active,
        created_at=new_api_key.created_at,
        last_used=new_api_key.last_used,
        expires_at=new_api_key.expires_at,
        key=key  # Full key only shown once
    )


@router.get("/api-keys", response_model=list[APIKeyOut])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of user's API keys (without the actual key values)
    """
    api_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).order_by(APIKey.created_at.desc()).all()

    return api_keys


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke (deactivate) an API key.

    Args:
        key_id: ID of the API key to revoke
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: 404 if API key not found or doesn't belong to user
    """
    # Find API key belonging to current user
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Deactivate the key (don't delete for audit trail)
    api_key.is_active = False
    db.commit()

    return None
