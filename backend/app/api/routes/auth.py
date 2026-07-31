from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import SessionDep
from app.core import security
from app.core.config import settings
from app.db.models import User
from app.schemas.token import Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    session: SessionDep, form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

from app.schemas.user import UserCreate, UserResponse

@router.post("/register", response_model=UserResponse)
async def register_user(
    session: SessionDep, user_in: UserCreate
) -> Any:
    """
    Register a new user
    """
    result = await session.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()
    if user:
        raise HTTPException(status_code=400, detail="User already registered")
        
    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

from app.api.deps import CurrentUser

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: CurrentUser
) -> Any:
    """
    Get current user profile.
    """
    return current_user


