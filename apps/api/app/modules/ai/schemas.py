"""
AI 模块 schemas
"""
from typing import Optional, Any, List
from datetime import datetime

from pydantic import BaseModel, Field


class AiJobCreate(BaseModel):
    """创建 AI 任务"""
    job_type: str = Field(..., description="任务类型")
    module: str = Field(..., description="所属模块")
    source_file_id: Optional[str] = None
    source_ocr_job_id: Optional[str] = None
    prompt_key: Optional[str] = None


class AiJobRead(BaseModel):
    """读取 AI 任务"""
    id: str
    job_type: str
    module: str
    source_file_id: Optional[str] = None
    source_ocr_job_id: Optional[str] = None
    prompt_key: Optional[str] = None
    status: str
    result: Optional[Any] = None
    raw_response: Optional[str] = None
    confidence: Optional[str] = None
    warnings: Optional[List[str]] = None
    error_message: Optional[str] = None
    created_by: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
