"""
生产级日志配置 - 文件按天滚动 + 控制台输出
"""
import logging
import os
import time
from collections import deque
from logging.handlers import TimedRotatingFileHandler

from app.core.config import settings

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")

# 错误计数器（供监控面板使用）
# 用 deque 记录最近窗口内的错误时间戳，避免历史累计导致监控误报
ERROR_WINDOW_SECONDS = 300  # 5 分钟窗口
_error_timestamps: deque = deque()
_error_counts: dict = {
    "recent": 0,
    "last_message": "",
    "last_time": "",
}


def _prune_old_errors() -> None:
    """剔除超出时间窗口的错误时间戳"""
    cutoff = time.time() - ERROR_WINDOW_SECONDS
    while _error_timestamps and _error_timestamps[0] < cutoff:
        _error_timestamps.popleft()
    _error_counts["recent"] = len(_error_timestamps)


def get_error_counts() -> dict:
    _prune_old_errors()
    return dict(_error_counts)


class ErrorCountingHandler(logging.Handler):
    """统计最近错误数量的 Handler"""
    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            _error_timestamps.append(time.time())
            _error_counts["last_message"] = self.format(record)[:500]
            _error_counts["last_time"] = record.asctime if hasattr(record, "asctime") else ""
            _prune_old_errors()


def setup_logging() -> None:
    """配置应用日志：文件按天滚动 + 控制台"""

    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)

    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # 日志格式
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # === 全量日志：按天滚动，保留 60 天 ===
    app_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "app.log"),
        when="midnight",
        interval=1,
        backupCount=60,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(file_fmt)
    root_logger.addHandler(app_handler)

    # === 错误日志：按天滚动，保留 180 天 ===
    error_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "error.log"),
        when="midnight",
        interval=1,
        backupCount=180,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_fmt)
    root_logger.addHandler(error_handler)

    # === 控制台输出 ===
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    console.setFormatter(console_fmt)
    root_logger.addHandler(console)

    # === 错误计数器 ===
    error_counter = ErrorCountingHandler()
    error_counter.setLevel(logging.ERROR)
    root_logger.addHandler(error_counter)

    # 减少第三方库日志噪音
    for lib in ("httpx", "httpcore", "urllib3", "asyncio", "sqlalchemy.engine"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("日志系统初始化完成（每日滚动，保留 60 天）")


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger"""
    return logging.getLogger(name)
