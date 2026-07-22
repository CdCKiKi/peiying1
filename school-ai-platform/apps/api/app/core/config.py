"""
应用配置 - 从环境变量读取，提供默认值
"""
import os
from typing import List


class Settings:
    """应用全局配置"""

    # 项目信息
    PROJECT_NAME: str = "培英 AI 行政平台"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # 数据库 - 开发模式默认使用 SQLite，生产环境使用 PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./school_ai_dev.db"
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC",
        "sqlite:///./school_ai_dev.db"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT 认证
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # 文件存储
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    # OCR/AI Worker
    OCR_BACKEND: str = os.getenv("OCR_BACKEND", "xfyun")  # mock | tesseract | xfyun
    LLM_BACKEND: str = os.getenv("LLM_BACKEND", "mock")  # mock | openai | local
    CLASSIFICATION_BACKEND: str = os.getenv("CLASSIFICATION_BACKEND", "keyword")  # keyword | api
    CLASSIFICATION_API_URL: str = os.getenv("CLASSIFICATION_API_URL", "")

    # 讯飞 OCR 配置
    XFYUN_APPID: str = os.getenv("XFYUN_APPID", "5fac6468")
    XFYUN_API_SECRET: str = os.getenv("XFYUN_API_SECRET", "Y2M1YTQ2YThjN2JkMmFjZmFhNWE2NDM1")
    XFYUN_API_KEY: str = os.getenv("XFYUN_API_KEY", "55146bdddb5b7b75757b5348faa867d2")
    XFYUN_OCR_URL: str = os.getenv("XFYUN_OCR_URL", "https://cbm01.cn-huabei-1.xf-yun.com/v1/private/se75ocrbm")

    # 日志
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
