"""
文件 ORM 模型
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Text

from app.db.session import Base


def generate_id() -> str:
    return str(uuid.uuid4())


class File(Base):
    """文件表 - 存储上传文件信息"""
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=generate_id)
    original_filename = Column(String(255), nullable=False, comment="原始文件名")
    stored_filename = Column(String(255), nullable=False, comment="存储文件名")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    mime_type = Column(String(100), nullable=True, comment="MIME 类型")
    file_size = Column(Integer, nullable=True, comment="文件大小 (bytes)")
    uploaded_by = Column(String(36), nullable=False, comment="上传者 ID")
    description = Column(Text, nullable=True, comment="文件描述")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
