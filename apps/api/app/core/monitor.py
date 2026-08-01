"""
系统监控模块 - 健康检查、资源统计、错误追踪
"""
import os
import time
import shutil
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.logging import get_error_counts

# 服务启动时间
_start_time: float = time.time()


def get_uptime_seconds() -> float:
    """返回服务已运行秒数"""
    return time.time() - _start_time


def get_disk_usage(path: str) -> Optional[dict]:
    """获取磁盘使用情况"""
    try:
        total, used, free = shutil.disk_usage(path or settings.UPLOAD_DIR)
        return {
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "percent_used": round(used / total * 100, 1),
        }
    except Exception:
        return None


def get_directory_size_mb(path: str) -> float:
    """计算目录总大小（MB）"""
    if not os.path.isdir(path):
        return 0.0
    total = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except Exception:
        pass
    return round(total / (1024 ** 2), 2)


def get_file_size_mb(path: str) -> float:
    """获取单个文件大小（MB）"""
    try:
        return round(os.path.getsize(path) / (1024 ** 2), 2)
    except OSError:
        return 0.0


def count_files_in_dir(path: str) -> int:
    """统计目录中文件数量"""
    if not os.path.isdir(path):
        return 0
    count = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            count += len(filenames)
    except Exception:
        pass
    return count


def get_db_path() -> Optional[str]:
    """从 DATABASE_URL 推断 SQLite 数据库文件路径"""
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        # sqlite+aiosqlite:///./school_ai_dev.db → ./school_ai_dev.db
        for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
            if url.startswith(prefix):
                return url[len(prefix):]
    return None


async def get_system_status(db_session=None) -> dict:
    """获取完整系统状态（供 /admin/status API）"""
    error_info = get_error_counts()

    # 数据库信息
    db_path = get_db_path()
    db_size = get_file_size_mb(db_path) if db_path else None

    # 上传文件信息
    upload_dir = settings.UPLOAD_DIR
    upload_count = count_files_in_dir(upload_dir)
    upload_size = get_directory_size_mb(upload_dir)

    # 日志信息
    log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    log_count = count_files_in_dir(log_dir)
    log_size = get_directory_size_mb(log_dir)

    # 磁盘
    disk = get_disk_usage(upload_dir)

    # 判断健康状态
    is_healthy = True
    warnings = []

    if disk and disk["free_gb"] < 1:
        is_healthy = False
        warnings.append(f"磁盘空间不足：仅剩 {disk['free_gb']} GB")
    elif disk and disk["free_gb"] < 5:
        warnings.append(f"磁盘空间偏低：剩 {disk['free_gb']} GB")

    if error_info.get("recent", 0) > 10:
        warnings.append(f"最近错误较多：{error_info['recent']} 次")

    uptime = get_uptime_seconds()
    days, rem = divmod(int(uptime), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_str = f"{days}天 {hours}时 {minutes}分" if days else f"{hours}时 {minutes}分"

    return {
        "status": "healthy" if is_healthy else "degraded",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": int(uptime),
        "uptime_display": uptime_str,
        "disk": disk,
        "database": {
            "type": "sqlite" if db_path else "postgresql",
            "size_mb": db_size,
        },
        "uploads": {
            "count": upload_count,
            "size_mb": upload_size,
        },
        "logs": {
            "count": log_count,
            "size_mb": log_size,
        },
        "errors": {
            "recent_count": error_info.get("recent", 0),
            "last_message": error_info.get("last_message"),
        },
        "warnings": warnings,
    }
