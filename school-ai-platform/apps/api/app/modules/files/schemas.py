"""
文件模块 schemas
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    id: str
    original_filename: str
    file_path: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class FileRead(BaseModel):
    """读取文件"""
    id: str
    original_filename: str
    stored_filename: str
    file_path: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
