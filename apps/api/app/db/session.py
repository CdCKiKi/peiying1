"""
数据库会话管理 - 使用 SQLAlchemy async engine + Alembic 迁移
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

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


def _run_alembic_upgrade() -> None:
    """同步执行 Alembic 迁移到最新版本"""
    import os
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine, inspect, text

    # 使用绝对路径确保不受 CWD 影响
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "migrations")
    migrations_dir = os.path.abspath(migrations_dir)

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", migrations_dir)
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

    # 检查是否是已有数据库（表存在但无 alembic 版本记录）
    engine = create_engine(settings.DATABASE_URL_SYNC)
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        # 检查 alembic 版本表是否存在
        has_alembic = "alembic_version" in existing_tables
        if not has_alembic:
            # 已有表但无 alembic 记录 → 标记为当前版本，跳过建表
            logger.info("检测到已有数据库，标记 Alembic 版本为 head")
            command.stamp(alembic_cfg, "head")
            engine.dispose()
            return

    engine.dispose()
    command.upgrade(alembic_cfg, "head")


async def init_db() -> None:
    """初始化数据库 - 运行 Alembic 迁移 + FTS5 索引"""
    # 1. 在同步引擎上运行 Alembic 表结构迁移
    await asyncio.to_thread(_run_alembic_upgrade)

    # 2. 创建 FTS5 索引（Alembic 不管理虚拟表）
    if settings.DATABASE_URL.startswith("sqlite"):
        async with engine.begin() as conn:
            await _init_fts5(conn)

    logger.info("数据库初始化完成 (Alembic + FTS5)")


async def _init_fts5(conn) -> None:
    """创建 FTS5 全文搜索虚拟表与触发器"""
    try:
        await conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS archive_fts USING fts5(
                original_filename,
                category,
                suggested_name,
                ai_summary,
                ocr_text,
                content='tommy_archive_documents',
                content_rowid='rowid'
            )
        """))

        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS archive_fts_ai AFTER INSERT ON tommy_archive_documents BEGIN
                INSERT INTO archive_fts(rowid, original_filename, category, suggested_name, ai_summary, ocr_text)
                VALUES (new.rowid, new.original_filename, new.category, new.suggested_name, new.ai_summary, new.ocr_text);
            END
        """))

        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS archive_fts_ad AFTER DELETE ON tommy_archive_documents BEGIN
                INSERT INTO archive_fts(archive_fts, rowid, original_filename, category, suggested_name, ai_summary, ocr_text)
                VALUES ('delete', old.rowid, old.original_filename, old.category, old.suggested_name, old.ai_summary, old.ocr_text);
            END
        """))

        await conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS archive_fts_au AFTER UPDATE ON tommy_archive_documents BEGIN
                INSERT INTO archive_fts(archive_fts, rowid, original_filename, category, suggested_name, ai_summary, ocr_text)
                VALUES ('delete', old.rowid, old.original_filename, old.category, old.suggested_name, old.ai_summary, old.ocr_text);
                INSERT INTO archive_fts(rowid, original_filename, category, suggested_name, ai_summary, ocr_text)
                VALUES (new.rowid, new.original_filename, new.category, new.suggested_name, new.ai_summary, new.ocr_text);
            END
        """))

        await conn.execute(text("INSERT INTO archive_fts(archive_fts) VALUES('rebuild')"))

        logger.info("FTS5 全文搜索索引已初始化")
    except Exception as e:
        logger.warning(f"FTS5 初始化失败（可忽略）: {e}")


# ===== FTS5 搜索工具 =====

async def fts_search_archive(db: AsyncSession, keyword: str, limit: int = 200) -> list[str]:
    """
    使用 FTS5 全文搜索归档文档，返回匹配的文档 ID 列表
    失败时返回空列表（调用方回退到 ILIKE）
    """
    try:
        safe_keyword = keyword.replace('"', '""')
        result = await db.execute(
            text("""
                SELECT d.id FROM tommy_archive_documents d
                JOIN archive_fts fts ON d.rowid = fts.rowid
                WHERE archive_fts MATCH :query
                ORDER BY rank
                LIMIT :limit
            """),
            {"query": f'"{safe_keyword}"', "limit": limit}
        )
        return [row[0] for row in result.fetchall()]
    except Exception:
        return []  # 回退到 ILIKE
