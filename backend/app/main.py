from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, async_session
from app.routers import auth_router, reports_router, summary_router, admin_router
from app.tasks.scheduler import setup_scheduler
from app.models.user import User, UserRole
from app.utils.security import get_password_hash
from app.config import get_settings
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # 启动时初始化数据库
    await init_db()
    # 创建默认管理员（仅当配置了密码时）
    if settings.ADMIN_PASSWORD:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.username == "admin"))
            if not result.scalar_one_or_none():
                admin = User(
                    username="admin",
                    password=get_password_hash(settings.ADMIN_PASSWORD),
                    real_name="管理员",
                    role=UserRole.admin
                )
                db.add(admin)
                await db.commit()

    # 启动定时任务
    scheduler = setup_scheduler()
    scheduler.start()

    yield

    # 关闭定时任务
    scheduler.shutdown()


app = FastAPI(
    title="周报管理系统",
    description="企业周报在线填写、汇总与文档生成系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(reports_router)
app.include_router(summary_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "周报管理系统 API", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
