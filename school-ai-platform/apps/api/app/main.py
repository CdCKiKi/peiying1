"""
培英 AI 行政平台 - FastAPI 后端主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="培英中學 AI 數智化行政平台後端 API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS 配置 - 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库 + 种子数据"""
    from app.db.session import init_db, async_session
    from app.db.seed import seed_data

    await init_db()

    # 初始化种子数据
    async with async_session() as db:
        await seed_data(db)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "version": settings.VERSION}


# 注册路由
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
