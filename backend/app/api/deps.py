from typing import AsyncGenerator, Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.core import security
from app.db.models import User, RoleEnum

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_db)]
TokenDep = Annotated[Optional[str], Depends(oauth2_scheme)]

async def get_current_user(session: SessionDep, token: TokenDep = None) -> User:
    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is not None:
                result = await session.execute(select(User).where(User.id == int(user_id)))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
        except JWTError:
            pass

    # Fallback to guest user when token is missing or invalid
    guest_email = "guest@example.com"
    result = await session.execute(select(User).where(User.email == guest_email))
    guest_user = result.scalar_one_or_none()
    if not guest_user:
        guest_user = User(
            email=guest_email,
            hashed_password=security.get_password_hash("guest-password-never-used"),
            full_name="Guest Counsel",
            role=RoleEnum.associate,
            is_active=True
        )
        session.add(guest_user)
        await session.commit()
        await session.refresh(guest_user)
    return guest_user

CurrentUser = Annotated[User, Depends(get_current_user)]

def get_current_active_superuser(current_user: CurrentUser) -> User:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

SuperUserDep = Annotated[User, Depends(get_current_active_superuser)]
