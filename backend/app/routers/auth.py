from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.user import Token, UserResponse, PasswordChange
from app.services.auth_service import authenticate_user, create_user_token
from app.utils.security import get_current_user, get_password_hash, verify_password
from app.utils.rate_limiter import check_rate_limit, record_failed_attempt, clear_failed_attempts
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # 使用 IP + 用户名 作为限制标识
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{form_data.username}"

    # 检查是否被锁定
    allowed, remaining_seconds = check_rate_limit(identifier)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录尝试次数过多，请 {remaining_seconds // 60 + 1} 分钟后再试",
        )

    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        record_failed_attempt(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 登录成功，清除失败记录
    clear_failed_attempts(identifier)
    return create_user_token(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(status_code=400, detail="原密码错误")

    current_user.password = get_password_hash(password_data.new_password)
    current_user.must_change_password = False  # 重置首次登录标记
    await db.commit()
    return {"message": "密码修改成功"}
