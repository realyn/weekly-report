from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    username: str
    real_name: str
    department: Optional[str] = "产品研发部"


class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.user


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    must_change_password: bool = False


class TokenData(BaseModel):
    username: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str
