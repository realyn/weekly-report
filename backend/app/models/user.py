from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    real_name = Column(String(50), nullable=False)
    department = Column(String(100), default="产品研发部")
    role = Column(SQLEnum(UserRole), default=UserRole.user)
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=True)  # 首次登录需修改密码
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    reports = relationship("Report", back_populates="user")
