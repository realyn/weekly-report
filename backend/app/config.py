from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "周报管理系统"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/weekly_report.db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时

    # 管理员初始密码
    ADMIN_PASSWORD: str = ""

    # 文档存储路径
    DOCUMENTS_PATH: str = "./data/documents"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
