from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.models import RoleEnum

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: RoleEnum = RoleEnum.associate

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
