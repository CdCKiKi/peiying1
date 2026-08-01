"""
OCR 模块 API 路由
"""
import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import get_current_user
from app.common.errors import not_found
from app.modules.ocr.models import OcrJob
from app.modules.ocr.schemas import OcrJobCreate, OcrJobRead
from app.modules.files.models import File as FileModel
from app.core.config import settings
from app.core.xfyun_ocr_client import xfyun_ocr_client

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/jobs", response_model=OcrJobRead)
async def create_ocr_job(request: OcrJobCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """创建 OCR 任务"""
    job = OcrJob(
        job_type=request.job_type,
        module=request.module,
        source_file_id=request.source_file_id,
        status="pending",
        created_by=current_user["sub"],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    job.status = "running"
    await db.commit()

    ocr_text = ""
    confidence = "medium"

    if settings.OCR_BACKEND == "xfyun":
        try:
            file_result = await db.execute(select(FileModel).where(FileModel.id == request.source_file_id))
            file_record = file_result.scalar_one_or_none()
            if file_record:
                file_full_path = os.path.join(settings.UPLOAD_DIR, file_record.stored_filename)
                if os.path.exists(file_full_path):
                    ocr_text, confidence = await xfyun_ocr_client.recognize(file_full_path)
                else:
                    ocr_text = f"（文件不存在: {file_full_path}）"
            else:
                ocr_text = "（原始文件不存在）"
        except Exception as e:
            ocr_text = f"（OCR識別失敗: {str(e)}）"
            confidence = "low"
            job.status = "failed"
            job.error_message = str(e)
    else:
        ocr_text = "（Mock OCR 文本 - 后续接入真实 OCR 后替换）"

    if job.status != "failed":
        job.status = "succeeded"
    job.ocr_text = ocr_text
    job.confidence = confidence
    job.duration_seconds = 18
    await db.commit()
    await db.refresh(job)

    return OcrJobRead.model_validate(job)


@router.get("/jobs/{job_id}", response_model=OcrJobRead)
async def get_ocr_job(job_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """查询 OCR 任务状态"""
    result = await db.execute(select(OcrJob).where(OcrJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise not_found("OCR 任务不存在")
    return OcrJobRead.model_validate(job)
