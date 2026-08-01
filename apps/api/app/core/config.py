"""
应用配置 - 从 .env 文件和环境变量读取，提供默认值
"""
import os
from pathlib import Path
from typing import List


def _load_dotenv() -> None:
    """加载 .env 文件到环境变量（不覆盖已存在的环境变量）"""
    # 查找项目根目录的 .env
    env_path = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"
    if not env_path.exists():
        # 尝试 backend 目录
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


class Settings:
    """应用全局配置"""

    # 项目信息
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "培英 AI 行政平台")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")

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
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 小时

    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000"
    ).split(",")

    # 文件存储
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))  # 50MB

    # OCR 后端
    OCR_BACKEND: str = os.getenv("OCR_BACKEND", "xfyun")  # mock | xfyun

    # 讯飞 OCR 配置
    XFYUN_APPID: str = os.getenv("XFYUN_APPID", "")
    XFYUN_API_SECRET: str = os.getenv("XFYUN_API_SECRET", "")
    XFYUN_API_KEY: str = os.getenv("XFYUN_API_KEY", "")
    XFYUN_OCR_URL: str = os.getenv("XFYUN_OCR_URL", "https://cbm01.cn-huabei-1.xf-yun.com/v1/private/se75ocrbm")

    # AI / LLM 配置
    LLM_BACKEND: str = os.getenv("LLM_BACKEND", "openai")  # mock | openai
    LLM_API_URL: str = os.getenv("LLM_API_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    # 文档分类策略
    CLASSIFICATION_BACKEND: str = os.getenv("CLASSIFICATION_BACKEND", "llm")  # keyword | llm | api
    CLASSIFICATION_API_URL: str = os.getenv("CLASSIFICATION_API_URL", "")

    # 邮件配置 (SMTP)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@py.edu.hk")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    # 日志
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
