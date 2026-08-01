"""
审计日志 ORM 模型
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, JSON

from app.db.session import Base


def generate_id() -> str:
    return str(uuid.uuid4())


class AuditLog(Base):
    """审计日志表 - 记录所有重要操作"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_id)
    module = Column(String(50), nullable=False, comment="所属模块")
    action = Column(String(100), nullable=False, comment="操作类型，如 confirm/archive/delete")
    resource_type = Column(String(100), nullable=False, comment="资源类型，如 archive_document")
    resource_id = Column(String(36), nullable=False, comment="资源 ID")
    user_id = Column(String(36), nullable=False, comment="操作者 ID")
    user_name = Column(String(100), nullable=True, comment="操作者名称")
    detail = Column(Text, nullable=True, comment="操作详情")
    extra_data = Column(JSON, nullable=True, comment="额外数据")
    created_at = Column(DateTime, default=datetime.utcnow)
