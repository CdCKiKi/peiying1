"""
分页工具
"""
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页请求参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class PaginationMeta(BaseModel):
    """分页元信息"""
    page: int
    page_size: int
    total: int


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    data: List[T]
    pagination: PaginationMeta
