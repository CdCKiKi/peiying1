"""
Alembic 迁移环境配置
动态读取 app.core.config 中的数据库 URL，自动发现所有 ORM 模型
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.db.session import Base

# 导入所有模型，确保 Base.metadata 包含全部表
from app.modules.accounts import models as _accounts_models      # noqa: F401
from app.modules.files import models as _files_models            # noqa: F401
from app.modules.ocr import models as _ocr_models                # noqa: F401
from app.modules.ai import models as _ai_models                  # noqa: F401
from app.modules.tommy import models as _tommy_models            # noqa: F401
from app.modules.audit import models as _audit_models            # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置 Alembic 使用的数据库 URL（同步版本）
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：仅生成 SQL 脚本"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直接连接数据库执行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
