"""
数据库会话管理 - 使用 SQLAlchemy async engine
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# SQLite 需要特殊配置
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


async def get_db() -> AsyncSession:
    """获取数据库会话 - 用于 FastAPI 依赖注入"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库 - 创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
