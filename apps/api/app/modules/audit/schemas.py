"""
审计日志 schemas
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    """创建审计日志"""
    module: str = Field(..., description="所属模块")
    action: str = Field(..., description="操作类型")
    resource_type: str = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源 ID")
    user_id: str = Field(..., description="操作者 ID")
    user_name: Optional[str] = None
    detail: Optional[str] = None
    extra_data: Optional[Any] = None


class AuditLogRead(BaseModel):
    """读取审计日志"""
    id: str
    module: str
    action: str
    resource_type: str
    resource_id: str
    user_id: str
    user_name: Optional[str] = None
    detail: Optional[str] = None
    extra_data: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True
