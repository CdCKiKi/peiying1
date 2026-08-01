"""
AI 模块 API 路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.common.errors import not_found
from app.modules.ai.models import AiJob
from app.modules.ai.schemas import AiJobCreate, AiJobRead

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate", response_model=AiJobRead)
async def create_ai_job(request: AiJobCreate, db: AsyncSession = Depends(get_db)):
    """创建 AI 生成/分类任务"""
    job = AiJob(
        job_type=request.job_type,
        module=request.module,
        source_file_id=request.source_file_id,
        source_ocr_job_id=request.source_ocr_job_id,
        prompt_key=request.prompt_key,
        status="pending",
        created_by="current_user",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Mock: 直接返回预设 AI 结果
    job.status = "succeeded"
    job.result = {
        "category": "租務",
        "suggested_name": "2026-07-15_租務_俊傑花園租金通知.pdf",
        "amount": 18500,
        "due_date": "2026-07-31",
        "summary": "俊傑花園 A座 8樓 B室 2026年7月租金通知",
        "confidence": "medium",
        "warnings": [],
    }
    job.confidence = "medium"
    job.warnings = []
    await db.commit()
    await db.refresh(job)

    return AiJobRead.model_validate(job)


@router.get("/generate/{job_id}", response_model=AiJobRead)
async def get_ai_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """查询 AI 任务状态"""
    result = await db.execute(select(AiJob).where(AiJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise not_found("AI 任务不存在")
    return AiJobRead.model_validate(job)
