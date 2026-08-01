"""
培英 AI 行政平台 - FastAPI 后端主入口
"""
import logging
import os
import time
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging

# 初始化日志系统（最先执行）
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="培英中學 AI 數智化行政平台後端 API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 全局异常处理器（捕获未处理异常，记录完整堆栈）=====
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(f"未处理异常 {request.method} {request.url.path}: {exc}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__, "traceback": tb},
    )


# ===== 请求日志中间件 =====

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有 API 请求的方法、路径、状态码和耗时"""
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        # 捕获未处理异常，记录完整堆栈，返回 500
        import traceback
        logger.error(f"未处理异常 {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": type(exc).__name__},
        )

    elapsed = time.perf_counter() - start_time
    status = response.status_code

    # 日志级别：4xx/5xx 用 warning/error，正常用 info
    log_msg = f"{request.method:6s} {request.url.path} → {status} ({elapsed:.3f}s)"

    if status >= 500:
        logger.error(log_msg)
    elif status >= 400:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    return response


# ===== 启动事件 =====

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库 + 种子数据"""
    from app.db.session import init_db, async_session
    from app.db.seed import seed_data

    # 确保上传目录和日志目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "logs"), exist_ok=True)

    await init_db()

    async with async_session() as db:
        await seed_data(db)

    logger.info(f"培英 AI 平台已啟動 (v{settings.VERSION})")
    logger.info(f"OCR 後端: {settings.OCR_BACKEND}, LLM 後端: {settings.LLM_BACKEND}")
    logger.info(f"郵件服務: {'已配置' if settings.SMTP_HOST else '未配置'}")


# ===== 健康检查 =====

@app.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "ok", "version": settings.VERSION, "timestamp": time.time()}


@app.get("/health/detailed")
async def health_check_detailed():
    """详细健康检查（含 DB 连接测试）"""
    from app.db.session import async_session
    from sqlalchemy import text
    from app.core.monitor import get_system_status

    db_ok = False
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        db_ok = False

    status = await get_system_status()
    status["database"]["connected"] = db_ok

    if not db_ok:
        status["status"] = "degraded"
        status["warnings"].append("数据库连接失败")

    return status


# ===== 管理接口 =====

@app.get(f"{settings.API_V1_STR}/admin/status")
async def admin_status():
    """系统状态面板（含磁盘、数据库、错误统计）"""
    from app.core.monitor import get_system_status
    return await get_system_status()


# ===== 注册路由 =====
from app.modules.accounts.router import router as accounts_router
from app.modules.files.router import router as files_router
from app.modules.ocr.router import router as ocr_router
from app.modules.ai.router import router as ai_router
from app.modules.tommy.router import router as tommy_router
from app.modules.audit.router import router as audit_router

app.include_router(accounts_router, prefix=settings.API_V1_STR)
app.include_router(files_router, prefix=settings.API_V1_STR)
app.include_router(ocr_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(tommy_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
