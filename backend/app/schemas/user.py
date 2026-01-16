import re
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


def validate_password_strength(password: str) -> str:
    """验证密码强度：至少8位，包含字母和数字"""
    if len(password) < 8:
        raise ValueError("密码长度至少8位")
    if not re.search(r'[A-Za-z]', password):
        raise ValueError("密码必须包含字母")
    if not re.search(r'\d', password):
        raise ValueError("密码必须包含数字")
    return password


class UserBase(BaseModel):
    username: str
    real_name: str
    department: Optional[str] = "产品研发部"


class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.user

    @field_validator('password')
    @classmethod
    def check_password(cls, v):
        return validate_password_strength(v)


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

    @field_validator('new_password')
    @classmethod
    def check_new_password(cls, v):
        return validate_password_strength(v)
