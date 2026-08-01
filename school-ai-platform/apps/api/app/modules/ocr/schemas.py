"""
OCR 模块 schemas
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class OcrJobCreate(BaseModel):
    """创建 OCR 任务"""
    job_type: str = Field(..., description="任务类型，如 ocr.extract_receipt")
    module: str = Field(..., description="所属模块")
    source_file_id: str = Field(..., description="源文件 ID")


class OcrJobRead(BaseModel):
    """读取 OCR 任务"""
    id: str
    job_type: str
    module: str
    source_file_id: str
    status: str
    ocr_text: Optional[str] = None
    confidence: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[int] = None
    created_by: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
