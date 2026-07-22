"""
统一错误处理
"""
from typing import Any, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    """统一错误响应格式"""
    error: ErrorDetail
    meta: dict = {"request_id": ""}


class AppException(HTTPException):
    """应用自定义异常"""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Any] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code
        self.message = message
        self.details = details


# 常用错误快捷方法
def not_found(message: str = "资源不存在") -> AppException:
    return AppException(status.HTTP_404_NOT_FOUND, "NOT_FOUND", message)


def forbidden(message: str = "权限不足") -> AppException:
    return AppException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def unauthorized(message: str = "未认证") -> AppException:
    return AppException(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


def validation_error(message: str = "请检查输入内容", details=None) -> AppException:
    return AppException(status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR", message, details)


def conflict(message: str = "资源冲突") -> AppException:
    return AppException(status.HTTP_409_CONFLICT, "CONFLICT", message)
