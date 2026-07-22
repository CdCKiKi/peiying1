"""
OCR 任务 ORM 模型
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Integer

from app.db.session import Base


def generate_id() -> str:
    return str(uuid.uuid4())


class OcrJob(Base):
    """OCR 任务表"""
    __tablename__ = "ocr_jobs"

    id = Column(String(36), primary_key=True, default=generate_id)
    job_type = Column(String(100), nullable=False, comment="任务类型，如 ocr.extract_receipt")
    module = Column(String(50), nullable=False, comment="所属模块，如 tommy")
    source_file_id = Column(String(36), nullable=False, comment="源文件 ID")
    status = Column(String(20), nullable=False, default="pending", comment="状态: pending/running/succeeded/failed/needs_review")
    ocr_text = Column(Text, nullable=True, comment="OCR 识别原文")
    confidence = Column(String(20), nullable=True, comment="置信度: low/medium/high")
    error_message = Column(Text, nullable=True, comment="错误信息")
    duration_seconds = Column(Integer, nullable=True, comment="处理耗时（秒）")
    created_by = Column(String(36), nullable=False, comment="创建者 ID")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
