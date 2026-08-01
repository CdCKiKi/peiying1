"""
Tommy 模块 schemas - 文件归档 + 租务管理
"""
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, Field


# ===== 文件归档 =====

class ArchiveDocumentCreate(BaseModel):
    """创建归档文档"""
    original_file_id: str = Field(..., description="原始文件 ID")
    note: Optional[str] = None


class ArchiveDocumentUpdate(BaseModel):
    """更新归档文档 - 人工修改 AI 结果"""
    category: Optional[str] = None
    suggested_name: Optional[str] = None
    amount: Optional[Decimal] = None
    due_date: Optional[date] = None
    ai_summary: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None


class ArchiveDocumentRead(BaseModel):
    """读取归档文档"""
    id: str
    original_file_id: str
    original_filename: str
    category: Optional[str] = None
    suggested_name: Optional[str] = None
    amount: Optional[Decimal] = None
    due_date: Optional[date] = None
    ocr_text: Optional[str] = None
    ai_summary: Optional[str] = None
    confidence: Optional[str] = None
    status: str
    last_reviewed_by: Optional[str] = None
    last_reviewed_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True


# ===== 租务管理 =====

class RentalUnitCreate(BaseModel):
    """创建租赁单位"""
    unit_number: str = Field(..., description="单位编号")
    unit_type: str = Field(..., description="类型: 住宅/車位")
    tenant_name: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    monthly_rent: Optional[Decimal] = None
    is_occupied: bool = True
    notes: Optional[str] = None


class RentalUnitUpdate(BaseModel):
    """更新租赁单位"""
    tenant_name: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    monthly_rent: Optional[Decimal] = None
    is_occupied: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class RentalLeaseCreate(BaseModel):
    """创建租约记录"""
    tenant_name: str = Field(..., description="租户名称")
    lease_start: date = Field(..., description="租约开始日期")
    lease_end: date = Field(..., description="租约结束日期")
    monthly_rent: Decimal = Field(..., description="月租金")
    notes: Optional[str] = None


class RentalLeaseUpdate(BaseModel):
    """更新租约记录"""
    tenant_name: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    monthly_rent: Optional[Decimal] = None
    notes: Optional[str] = None


class RentalLeaseRead(BaseModel):
    """读取租约记录"""
    id: str
    unit_id: str
    tenant_name: str
    lease_start: date
    lease_end: date
    monthly_rent: Decimal
    status: str
    notes: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RentalUnitRead(BaseModel):
    """读取租赁单位"""
    id: str
    property_name: str
    unit_number: str
    unit_type: str
    tenant_name: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    monthly_rent: Optional[Decimal] = None
    is_occupied: bool
    status: str
    notes: Optional[str] = None
    created_by: str
    created_at: datetime
    payments: List["RentalPaymentRead"] = Field(default_factory=list)
    leases: List["RentalLeaseRead"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class RentalPaymentCreate(BaseModel):
    """创建缴费记录"""
    amount: Decimal = Field(..., description="应缴金额")
    due_date: date = Field(..., description="缴费截止日")


class RentalPaymentUpdate(BaseModel):
    """更新缴费记录"""
    paid_date: Optional[date] = None
    paid_amount: Optional[Decimal] = None
    status: Optional[str] = None


class RentalPaymentRead(BaseModel):
    """读取缴费记录"""
    id: str
    unit_id: str
    amount: Decimal
    due_date: date
    paid_date: Optional[date] = None
    paid_amount: Optional[Decimal] = None
    status: str
    reminder_sent: bool
    created_at: datetime

    class Config:
        from_attributes = True


RentalUnitRead.model_rebuild()
