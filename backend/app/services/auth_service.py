from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.security import get_password_hash, verify_password, create_access_token


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password):
        return None
    return user


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        password=hashed_password,
        real_name=user_data.real_name,
        department=user_data.department,
        role=user_data.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def create_user_token(user: User) -> dict:
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "must_change_password": user.must_change_password
    }
