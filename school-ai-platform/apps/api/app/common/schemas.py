"""
通用 Pydantic schemas - 所有模块共享
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BaseSchema(BaseModel):
    """基础 schema"""
    class Config:
        from_attributes = True


class IDSchema(BaseSchema):
    """包含 ID 的 schema"""
    id: str = Field(..., description="记录 ID")


class TimestampSchema(BaseSchema):
    """包含时间戳的 schema"""
    created_at: datetime
    updated_at: Optional[datetime] = None


class CreatedBySchema(BaseSchema):
    """包含创建者信息的 schema"""
    created_by: str
    updated_by: Optional[str] = None
