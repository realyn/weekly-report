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

    # LLM API 配置
    LLM_PROVIDER: str = "qwen"  # qwen, deepseek, openai
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://gpta.realyn.com"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DASHSCOPE_API_KEY: str = ""

    # 项目数据文件路径
    PROJECTS_DATA_PATH: str = "./data/projects.json"

    # Embedding 模型配置
    EMBEDDING_MODEL: str = "text-embedding-v3"  # text-embedding-v4 或 text-embedding-v3
    EMBEDDING_DIMENSION: int = 1024  # 向量维度，v4支持64-2048，v3固定1024

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
