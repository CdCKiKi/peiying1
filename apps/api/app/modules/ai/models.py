"""
AI 任务 ORM 模型
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, JSON

from app.db.session import Base


def generate_id() -> str:
    return str(uuid.uuid4())


class AiJob(Base):
    """AI 生成/分类任务表"""
    __tablename__ = "ai_jobs"

    id = Column(String(36), primary_key=True, default=generate_id)
    job_type = Column(String(100), nullable=False, comment="任务类型，如 ai.classify_document")
    module = Column(String(50), nullable=False, comment="所属模块")
    source_file_id = Column(String(36), nullable=True, comment="源文件 ID")
    source_ocr_job_id = Column(String(36), nullable=True, comment="源 OCR 任务 ID")
    prompt_key = Column(String(100), nullable=True, comment="使用的 prompt 标识")
    status = Column(String(20), nullable=False, default="pending")
    result = Column(JSON, nullable=True, comment="AI 结构化结果")
    raw_response = Column(Text, nullable=True, comment="AI 原始响应")
    confidence = Column(String(20), nullable=True, comment="置信度")
    warnings = Column(JSON, nullable=True, comment="警告列表")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
