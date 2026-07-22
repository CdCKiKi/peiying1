"""
Tommy 模块 ORM 模型 - 文件归档 + 租务管理
"""
import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Column, String, DateTime, Date, Numeric, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.db.session import Base


def generate_id() -> str:
    return str(uuid.uuid4())


class ArchiveDocument(Base):
    """Tommy 文件归档表"""
    __tablename__ = "tommy_archive_documents"

    id = Column(String(36), primary_key=True, default=generate_id)
    original_file_id = Column(String(36), ForeignKey("files.id"), nullable=False, comment="原始文件 ID")
    original_filename = Column(String(255), nullable=False, comment="原始文件名")

    # AI/OCR 结果字段
    category = Column(String(50), nullable=True, comment="建议分类: 財務/人事/租務/教育局通告/會議/其他")
    suggested_name = Column(String(255), nullable=True, comment="建议新文件名")
    amount = Column(Numeric(12, 2), nullable=True, comment="提取金额")
    due_date = Column(Date, nullable=True, comment="到期日")
    ocr_text = Column(Text, nullable=True, comment="OCR 识别原文")
    ai_summary = Column(Text, nullable=True, comment="AI 摘要")
    confidence = Column(String(20), nullable=True, comment="AI 置信度: low/medium/high")
    source_file_id = Column(String(36), nullable=True, comment="来源文件 ID（归档后）")

    # 状态流转: pending → ocr_running → needs_review → confirmed → archived → exception
    status = Column(String(20), nullable=False, default="pending", comment="状态")

    # 审计字段
    last_reviewed_by = Column(String(36), nullable=True, comment="最后复核人")
    last_reviewed_at = Column(DateTime, nullable=True, comment="最后复核时间")
    created_by = Column(String(36), nullable=False, comment="创建者 ID")
    updated_by = Column(String(36), nullable=True, comment="更新者 ID")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    note = Column(Text, nullable=True, comment="备注")


class RentalUnit(Base):
    """Tommy 租务管理 - 租赁单位表"""
    __tablename__ = "tommy_rental_units"

    id = Column(String(36), primary_key=True, default=generate_id)
    property_name = Column(String(100), nullable=False, default="俊傑花園", comment="物业名称")
    unit_number = Column(String(50), nullable=False, comment="单位编号，如 A座8樓B室 / 车位01")
    unit_type = Column(String(20), nullable=False, comment="类型: 住宅/車位")
    tenant_name = Column(String(100), nullable=True, comment="当前租户名称")
    lease_start = Column(Date, nullable=True, comment="当前租约开始日期")
    lease_end = Column(Date, nullable=True, comment="当前租约结束日期")
    monthly_rent = Column(Numeric(12, 2), nullable=True, comment="当前月租金 (HK$)")
    is_occupied = Column(Boolean, default=True, comment="是否已出租")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/expiring/expired/vacant")
    notes = Column(Text, nullable=True, comment="备注")
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payments = relationship("RentalPayment", back_populates="unit", lazy="selectin")
    leases = relationship("RentalLease", back_populates="unit", lazy="selectin", order_by="RentalLease.lease_start.desc()")


class RentalLease(Base):
    """Tommy 租务管理 - 租约记录表"""
    __tablename__ = "tommy_rental_leases"

    id = Column(String(36), primary_key=True, default=generate_id)
    unit_id = Column(String(36), ForeignKey("tommy_rental_units.id"), nullable=False, comment="单位 ID")
    tenant_name = Column(String(100), nullable=False, comment="租户名称")
    lease_start = Column(Date, nullable=False, comment="租约开始日期")
    lease_end = Column(Date, nullable=False, comment="租约结束日期")
    monthly_rent = Column(Numeric(12, 2), nullable=False, comment="月租金 (HK$)")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/expired/terminated")
    notes = Column(Text, nullable=True, comment="备注")
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    unit = relationship("RentalUnit", back_populates="leases")


class RentalPayment(Base):
    """Tommy 租务管理 - 缴费记录表"""
    __tablename__ = "tommy_rental_payments"

    id = Column(String(36), primary_key=True, default=generate_id)
    unit_id = Column(String(36), ForeignKey("tommy_rental_units.id"), nullable=False, comment="单位 ID")
    amount = Column(Numeric(12, 2), nullable=False, comment="应缴金额 (HK$)")
    due_date = Column(Date, nullable=False, comment="缴费截止日")
    paid_date = Column(Date, nullable=True, comment="实际缴费日期")
    paid_amount = Column(Numeric(12, 2), nullable=True, comment="实际缴费金额")
    status = Column(String(20), nullable=False, default="pending", comment="状态: pending/paid/overdue/partial")
    reminder_sent = Column(Boolean, default=False, comment="是否已发送缴费提醒")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    unit = relationship("RentalUnit", back_populates="payments")
