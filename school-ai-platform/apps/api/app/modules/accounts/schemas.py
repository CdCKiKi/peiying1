"""
用户模块 Pydantic schemas
"""
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserCreate(BaseModel):
    """创建用户"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = None
    role_names: List[str] = Field(default_factory=list, description="角色名称列表")


class UserRead(BaseModel):
    """读取用户"""
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    roles: List[str] = Field(default_factory=list, description="角色名称列表")
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """更新用户"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_names: Optional[List[str]] = None


TokenResponse.model_rebuild()
