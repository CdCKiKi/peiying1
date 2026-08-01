"""
AI 模块 API 路由
"""
import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.ai_classifier import ai_classifier
from app.common.errors import not_found
from app.modules.ai.models import AiJob
from app.modules.ai.schemas import AiJobCreate, AiJobRead
from app.modules.files.models import File as FileModel
from app.modules.ocr.models import OcrJob

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate", response_model=AiJobRead)
async def create_ai_job(request: AiJobCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """创建 AI 生成/分类任务"""
    job = AiJob(
        job_type=request.job_type,
        module=request.module,
        source_file_id=request.source_file_id,
        source_ocr_job_id=request.source_ocr_job_id,
        prompt_key=request.prompt_key,
        status="pending",
        created_by=current_user["sub"],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 获取 OCR 文本
    ocr_text = ""
    filename = ""

    if request.source_ocr_job_id:
        ocr_result = await db.execute(select(OcrJob).where(OcrJob.id == request.source_ocr_job_id))
        ocr_job = ocr_result.scalar_one_or_none()
        if ocr_job:
            ocr_text = ocr_job.ocr_text or ""

    if request.source_file_id:
        file_result = await db.execute(select(FileModel).where(FileModel.id == request.source_file_id))
        file_record = file_result.scalar_one_or_none()
        if file_record:
            filename = file_record.original_filename

    if not ocr_text:
        job.status = "failed"
        job.error_message = "OCR 文本为空，无法分类"
        await db.commit()
        await db.refresh(job)
        return AiJobRead.model_validate(job)

    # 调用真实 AI 分类器
    category, suggested_name, summary, amount, due_date, confidence = await ai_classifier.classify(ocr_text, filename)

    job.status = "succeeded"
    job.result = {
        "category": category,
        "suggested_name": suggested_name,
        "amount": float(amount) if amount else 0,
        "due_date": due_date,
        "summary": summary,
        "confidence": confidence,
        "warnings": [],
    }
    job.confidence = confidence
    job.warnings = []
    await db.commit()
    await db.refresh(job)

    return AiJobRead.model_validate(job)


@router.get("/generate/{job_id}", response_model=AiJobRead)
async def get_ai_job(job_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """查询 AI 任务状态"""
    result = await db.execute(select(AiJob).where(AiJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise not_found("AI 任务不存在")
    return AiJobRead.model_validate(job)
