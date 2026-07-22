"""
Tommy 模块 API 路由 - 文件归档 + 租务管理
"""
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.db.session import get_db
from app.common.errors import not_found, forbidden, validation_error
from app.common.pagination import PaginatedResponse, PaginationMeta
from app.modules.tommy.models import ArchiveDocument, RentalUnit, RentalPayment, RentalLease
from app.modules.tommy.schemas import (
    ArchiveDocumentCreate, ArchiveDocumentUpdate, ArchiveDocumentRead,
    RentalUnitCreate, RentalUnitUpdate, RentalUnitRead,
    RentalPaymentCreate, RentalPaymentUpdate, RentalPaymentRead,
    RentalLeaseCreate, RentalLeaseUpdate, RentalLeaseRead,
)
from app.modules.files.models import File as FileModel
from app.modules.audit.models import AuditLog
from app.core.config import settings
from app.core.xfyun_ocr_client import xfyun_ocr_client
from app.core.ai_classifier import ai_classifier

router = APIRouter(prefix="/tommy", tags=["tommy"])

CURRENT_USER_ID = "seed_user_tommy"
CURRENT_USER_NAME = "Tommy"


async def _log_audit(db: AsyncSession, module: str, action: str, resource_type: str, resource_id: str, detail: str = None):
    """写入审计日志"""
    log = AuditLog(
        module=module,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=CURRENT_USER_ID,
        user_name=CURRENT_USER_NAME,
        detail=detail,
    )
    db.add(log)


# ===== 文件归档 =====

archive_router = APIRouter(prefix="/archive-documents", tags=["tommy-archive"])


@archive_router.get("/stats")
async def get_archive_stats(db: AsyncSession = Depends(get_db)):
    """获取归档统计"""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    total = (await db.execute(select(func.count()).select_from(ArchiveDocument))).scalar() or 0
    pending_review = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.status == "needs_review"))).scalar() or 0
    confirmed = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.status == "confirmed"))).scalar() or 0
    archived = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.status == "archived"))).scalar() or 0
    exception = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.status == "exception"))).scalar() or 0
    today_upload = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.created_at >= today_start))).scalar() or 0

    return {
        "total": total,
        "pending_review": pending_review,
        "confirmed": confirmed,
        "archived": archived,
        "exception": exception,
        "today_upload": today_upload,
    }


@archive_router.get("", response_model=PaginatedResponse[ArchiveDocumentRead])
async def list_archive_documents(
    category: str = Query(None, description="按分类筛选"),
    status: str = Query(None, description="按状态筛选"),
    search: str = Query(None, description="搜索文件名、分类、金额或日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """列出归档文档"""
    query = select(ArchiveDocument).order_by(ArchiveDocument.created_at.desc())
    count_query = select(func.count()).select_from(ArchiveDocument)

    if category:
        query = query.where(ArchiveDocument.category == category)
        count_query = count_query.where(ArchiveDocument.category == category)
    if status:
        query = query.where(ArchiveDocument.status == status)
        count_query = count_query.where(ArchiveDocument.status == status)
    if search:
        search_filter = or_(
            ArchiveDocument.original_filename.ilike(f"%{search}%"),
            ArchiveDocument.category.ilike(f"%{search}%"),
            ArchiveDocument.suggested_name.ilike(f"%{search}%"),
            ArchiveDocument.ai_summary.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    docs = result.scalars().all()

    return PaginatedResponse(
        data=[ArchiveDocumentRead.model_validate(doc) for doc in docs],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@archive_router.post("", response_model=ArchiveDocumentRead)
async def create_archive_document(request: ArchiveDocumentCreate, db: AsyncSession = Depends(get_db)):
    """创建归档文档（上传后触发 OCR）"""
    # 从 files 表读取真实文件名
    file_result = await db.execute(select(FileModel).where(FileModel.id == request.original_file_id))
    file_record = file_result.scalar_one_or_none()
    if not file_record:
        raise validation_error("文件不存在，请先上传文件")

    doc = ArchiveDocument(
        original_file_id=request.original_file_id,
        original_filename=file_record.original_filename,
        status="pending",
        created_by=CURRENT_USER_ID,
        note=request.note,
    )
    db.add(doc)
    await db.flush()

    await _log_audit(db, "tommy", "upload", "archive_document", doc.id, f"上傳文件 {doc.original_filename}")
    await db.commit()
    await db.refresh(doc)

    doc.status = "ocr_running"
    await db.commit()

    ocr_text = ""
    confidence = "medium"

    if settings.OCR_BACKEND == "xfyun":
        try:
            file_full_path = os.path.join(settings.UPLOAD_DIR, file_record.stored_filename)
            if os.path.exists(file_full_path):
                ocr_text, confidence = await xfyun_ocr_client.recognize(file_full_path)
            else:
                ocr_text = f"（文件不存在: {file_full_path}）"
        except Exception as e:
            ocr_text = f"（OCR識別失敗: {str(e)}）"
            confidence = "low"
    else:
        ocr_text = "（Mock OCR）俊傑花園租金通知\n單位：A座 8樓 B室\n租戶：陳先生\n月份：2026年7月\n租金：HK$ 18,500\n繳付限期：2026年7月31日"

    doc.ocr_text = ocr_text

    category, suggested_name, ai_summary, amount, due_date, classify_confidence = await ai_classifier.classify(
        ocr_text, file_record.original_filename
    )

    doc.status = "needs_review"
    doc.category = category
    doc.suggested_name = suggested_name
    doc.amount = amount if amount > 0 else None
    doc.due_date = due_date
    doc.ai_summary = ai_summary
    doc.confidence = classify_confidence if classify_confidence else confidence

    await _log_audit(db, "tommy", "ocr_complete", "archive_document", doc.id, "OCR Worker 完成文字識別")
    await _log_audit(db, "tommy", "ai_classify", "archive_document", doc.id, f"AI 建議分類為「{doc.category}」")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.get("/{doc_id}", response_model=ArchiveDocumentRead)
async def get_archive_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """获取归档文档详情"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")
    return ArchiveDocumentRead.model_validate(doc)


@archive_router.patch("/{doc_id}", response_model=ArchiveDocumentRead)
async def update_archive_document(doc_id: str, request: ArchiveDocumentUpdate, db: AsyncSession = Depends(get_db)):
    """更新归档文档（人工修改 AI 结果）"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doc, key, value)

    doc.last_reviewed_by = CURRENT_USER_ID
    doc.last_reviewed_at = datetime.utcnow()

    await _log_audit(db, "tommy", "edit", "archive_document", doc.id, "人工修改 AI 結果")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.delete("/{doc_id}")
async def delete_archive_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """删除归档文档"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    await _log_audit(db, "tommy", "delete", "archive_document", doc.id, f"刪除文件 {doc.original_filename}")
    await db.delete(doc)
    await db.commit()
    return {"message": "已刪除", "id": doc_id}


@archive_router.post("/{doc_id}/run-ocr", response_model=ArchiveDocumentRead)
async def run_ocr(doc_id: str, db: AsyncSession = Depends(get_db)):
    """触发 OCR 识别"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    doc.status = "ocr_running"
    await db.commit()

    ocr_text = ""
    confidence = "medium"

    if settings.OCR_BACKEND == "xfyun":
        try:
            file_result = await db.execute(select(FileModel).where(FileModel.id == doc.original_file_id))
            file_record = file_result.scalar_one_or_none()
            if file_record:
                file_full_path = os.path.join(settings.UPLOAD_DIR, file_record.stored_filename)
                if os.path.exists(file_full_path):
                    ocr_text, confidence = await xfyun_ocr_client.recognize(file_full_path)
                else:
                    ocr_text = f"（文件不存在: {file_full_path}）"
            else:
                ocr_text = "（原始文件不存在）"
        except Exception as e:
            ocr_text = f"（OCR識別失敗: {str(e)}）"
            confidence = "low"
    else:
        ocr_text = "（Mock OCR 重新識別完成）"

    doc.ocr_text = ocr_text

    category, suggested_name, ai_summary, amount, due_date, classify_confidence = await ai_classifier.classify(
        ocr_text, doc.original_filename
    )

    doc.status = "needs_review"
    doc.category = category
    doc.suggested_name = suggested_name
    doc.amount = amount if amount > 0 else None
    doc.due_date = due_date
    doc.ai_summary = ai_summary
    doc.confidence = classify_confidence if classify_confidence else confidence

    await _log_audit(db, "tommy", "run_ocr", "archive_document", doc.id, "重新運行 OCR")
    await _log_audit(db, "tommy", "ai_classify", "archive_document", doc.id, f"AI 重新分類為「{doc.category}」")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/classify", response_model=ArchiveDocumentRead)
async def classify_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """触发 AI 分类"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    ocr_text = doc.ocr_text or ""
    category, suggested_name, ai_summary, amount, due_date, classify_confidence = await ai_classifier.classify(
        ocr_text, doc.original_filename
    )

    doc.category = category
    doc.suggested_name = suggested_name
    doc.amount = amount if amount > 0 else None
    doc.due_date = due_date
    doc.ai_summary = ai_summary
    doc.confidence = classify_confidence
    doc.status = "needs_review"

    await _log_audit(db, "tommy", "ai_classify", "archive_document", doc.id, f"AI 重新分類為「{doc.category}」")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/confirm", response_model=ArchiveDocumentRead)
async def confirm_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """人工确认 AI 结果"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    doc.status = "confirmed"
    doc.last_reviewed_by = CURRENT_USER_ID
    doc.last_reviewed_at = datetime.utcnow()

    await _log_audit(db, "tommy", "confirm", "archive_document", doc.id, "人工確認 AI 結果")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/archive", response_model=ArchiveDocumentRead)
async def archive_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """确认归档"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    doc.status = "archived"
    doc.last_reviewed_by = CURRENT_USER_ID
    doc.last_reviewed_at = datetime.utcnow()

    await _log_audit(db, "tommy", "archive", "archive_document", doc.id, f"文件已歸檔到「{doc.category or '其他'}」目錄")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/undo-archive", response_model=ArchiveDocumentRead)
async def undo_archive_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """撤销归档或复核操作"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    if doc.status == "archived":
        doc.status = "confirmed"
        await _log_audit(db, "tommy", "undo_archive", "archive_document", doc.id, "撤銷歸檔，狀態回退為已確認")
    elif doc.status == "confirmed":
        doc.status = "needs_review"
        await _log_audit(db, "tommy", "undo_confirm", "archive_document", doc.id, "撤銷確認，狀態回退為待復核")
    else:
        raise ValueError("当前状态无法撤销")

    doc.last_reviewed_by = CURRENT_USER_ID
    doc.last_reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/flag-exception", response_model=ArchiveDocumentRead)
async def flag_exception(doc_id: str, db: AsyncSession = Depends(get_db)):
    """标记异常"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    doc.status = "exception"
    doc.last_reviewed_by = CURRENT_USER_ID
    doc.last_reviewed_at = datetime.utcnow()

    await _log_audit(db, "tommy", "flag_exception", "archive_document", doc.id, "標記為異常，等待人工處理")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


# ===== 租务管理 =====

rental_router = APIRouter(prefix="/rental-units", tags=["tommy-rental"])


@rental_router.get("/stats")
async def get_rental_stats(db: AsyncSession = Depends(get_db)):
    """获取租务统计"""
    total_units = (await db.execute(select(func.count()).select_from(RentalUnit).where(RentalUnit.unit_type == "住宅"))).scalar() or 0
    total_parking = (await db.execute(select(func.count()).select_from(RentalUnit).where(RentalUnit.unit_type == "車位"))).scalar() or 0

    today = date.today()
    expiring_soon = (await db.execute(
        select(func.count()).select_from(RentalUnit).where(
            RentalUnit.lease_end <= today + timedelta(days=90),
            RentalUnit.lease_end >= today,
            RentalUnit.is_occupied == True,
        )
    )).scalar() or 0

    vacant = (await db.execute(select(func.count()).select_from(RentalUnit).where(RentalUnit.is_occupied == False))).scalar() or 0

    total_rent_result = await db.execute(
        select(func.coalesce(func.sum(RentalUnit.monthly_rent), 0)).where(RentalUnit.is_occupied == True)
    )
    total_rent = float(total_rent_result.scalar() or 0)

    pending_payments = (await db.execute(
        select(func.count()).select_from(RentalPayment).where(RentalPayment.status == "pending")
    )).scalar() or 0

    return {
        "residential_count": total_units,
        "parking_count": total_parking,
        "expiring_soon": expiring_soon,
        "vacant": vacant,
        "total_monthly_rent": total_rent,
        "pending_payments": pending_payments,
    }


@rental_router.get("", response_model=PaginatedResponse[RentalUnitRead])
async def list_rental_units(
    unit_type: str = Query(None, description="按类型筛选: 住宅/車位"),
    status: str = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """列出租赁单位"""
    query = select(RentalUnit).order_by(RentalUnit.unit_number)
    count_query = select(func.count()).select_from(RentalUnit)

    if unit_type:
        query = query.where(RentalUnit.unit_type == unit_type)
        count_query = count_query.where(RentalUnit.unit_type == unit_type)
    if status:
        query = query.where(RentalUnit.status == status)
        count_query = count_query.where(RentalUnit.status == status)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    units = result.scalars().all()

    return PaginatedResponse(
        data=[RentalUnitRead.model_validate(u) for u in units],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@rental_router.post("", response_model=RentalUnitRead)
async def create_rental_unit(request: RentalUnitCreate, db: AsyncSession = Depends(get_db)):
    """创建租赁单位（同时创建初始租约）"""
    unit = RentalUnit(
        unit_number=request.unit_number,
        unit_type=request.unit_type,
        tenant_name=request.tenant_name,
        lease_start=request.lease_start,
        lease_end=request.lease_end,
        monthly_rent=request.monthly_rent,
        is_occupied=request.is_occupied,
        notes=request.notes,
        created_by=CURRENT_USER_ID,
    )
    db.add(unit)
    await db.flush()

    if request.tenant_name and request.lease_start and request.lease_end and request.monthly_rent:
        lease = RentalLease(
            unit_id=unit.id,
            tenant_name=request.tenant_name,
            lease_start=request.lease_start,
            lease_end=request.lease_end,
            monthly_rent=request.monthly_rent,
            status="active",
            notes=request.notes,
            created_by=CURRENT_USER_ID,
        )
        db.add(lease)
        await _log_audit(db, "tommy", "create_lease", "rental_lease", lease.id, f"為單位 {request.unit_number} 創建初始租約，租戶: {request.tenant_name}")

    await _log_audit(db, "tommy", "create_unit", "rental_unit", unit.id, f"新增租賃單位 {request.unit_number}")
    await db.commit()
    await db.refresh(unit)
    return RentalUnitRead.model_validate(unit)


@rental_router.get("/{unit_id}", response_model=RentalUnitRead)
async def get_rental_unit(unit_id: str, db: AsyncSession = Depends(get_db)):
    """获取租赁单位详情"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")
    return RentalUnitRead.model_validate(unit)


@rental_router.patch("/{unit_id}", response_model=RentalUnitRead)
async def update_rental_unit(unit_id: str, request: RentalUnitUpdate, db: AsyncSession = Depends(get_db)):
    """更新租赁单位"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(unit, key, value)

    await _log_audit(db, "tommy", "update_unit", "rental_unit", unit_id, f"更新租賃單位 {unit.unit_number}")
    await db.commit()
    await db.refresh(unit)
    return RentalUnitRead.model_validate(unit)


@rental_router.get("/{unit_id}/payments", response_model=PaginatedResponse[RentalPaymentRead])
async def list_rental_payments(
    unit_id: str,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """列出缴费记录"""
    query = select(RentalPayment).where(RentalPayment.unit_id == unit_id).order_by(RentalPayment.due_date.desc())
    count_query = select(func.count()).select_from(RentalPayment).where(RentalPayment.unit_id == unit_id)

    if status:
        query = query.where(RentalPayment.status == status)
        count_query = count_query.where(RentalPayment.status == status)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    payments = result.scalars().all()

    return PaginatedResponse(
        data=[RentalPaymentRead.model_validate(p) for p in payments],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@rental_router.post("/{unit_id}/payments", response_model=RentalPaymentRead)
async def create_rental_payment(unit_id: str, request: RentalPaymentCreate, db: AsyncSession = Depends(get_db)):
    """创建缴费记录"""
    # 检查单位是否存在
    unit_result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = unit_result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    payment = RentalPayment(
        unit_id=unit_id,
        amount=request.amount,
        due_date=request.due_date,
        status="pending",
    )
    db.add(payment)
    await _log_audit(db, "tommy", "create_payment", "rental_payment", payment.id, f"新增繳費記錄 {unit.unit_number} HK${request.amount}")
    await db.commit()
    await db.refresh(payment)
    return RentalPaymentRead.model_validate(payment)


@rental_router.patch("/{unit_id}/payments/{payment_id}", response_model=RentalPaymentRead)
async def update_rental_payment(
    unit_id: str,
    payment_id: str,
    request: RentalPaymentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新缴费记录（记录收款）"""
    result = await db.execute(select(RentalPayment).where(RentalPayment.id == payment_id, RentalPayment.unit_id == unit_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise not_found("缴费记录不存在")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(payment, key, value)

    await _log_audit(db, "tommy", "update_payment", "rental_payment", payment_id, f"更新繳費記錄，狀態: {payment.status}")
    await db.commit()
    await db.refresh(payment)
    return RentalPaymentRead.model_validate(payment)


@rental_router.post("/{unit_id}/send-reminder")
async def send_reminder(unit_id: str, db: AsyncSession = Depends(get_db)):
    """发送缴费提醒"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    await _log_audit(db, "tommy", "send_reminder", "rental_unit", unit_id, f"向 {unit.tenant_name} 發送繳費提醒")
    await db.commit()

    return {"message": "繳費提醒已發送", "unit_id": unit_id, "tenant": unit.tenant_name}


@rental_router.post("/{unit_id}/generate-lease")
async def generate_lease(unit_id: str, db: AsyncSession = Depends(get_db)):
    """生成租约文件"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    await _log_audit(db, "tommy", "generate_lease", "rental_unit", unit_id, f"生成租約文件 {unit.unit_number}")
    await db.commit()

    return {"message": "租約文件已生成", "unit_id": unit_id, "unit_number": unit.unit_number}


@rental_router.post("/{unit_id}/leases", response_model=RentalLeaseRead)
async def create_rental_lease(unit_id: str, request: RentalLeaseCreate, db: AsyncSession = Depends(get_db)):
    """为单位新增租约（续租），旧租约自动标记为已到期"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    old_lease_result = await db.execute(
        select(RentalLease).where(RentalLease.unit_id == unit_id, RentalLease.status == "active")
    )
    old_lease = old_lease_result.scalar_one_or_none()
    if old_lease:
        old_lease.status = "expired"
        await _log_audit(db, "tommy", "expire_lease", "rental_lease", old_lease.id, f"租約已到期，租戶: {old_lease.tenant_name}")

    lease = RentalLease(
        unit_id=unit_id,
        tenant_name=request.tenant_name,
        lease_start=request.lease_start,
        lease_end=request.lease_end,
        monthly_rent=request.monthly_rent,
        status="active",
        notes=request.notes,
        created_by=CURRENT_USER_ID,
    )
    db.add(lease)
    await db.flush()

    unit.tenant_name = request.tenant_name
    unit.lease_start = request.lease_start
    unit.lease_end = request.lease_end
    unit.monthly_rent = request.monthly_rent
    unit.is_occupied = True
    unit.status = "active"

    await _log_audit(db, "tommy", "create_lease", "rental_lease", lease.id, f"為單位 {unit.unit_number} 新增租約，租戶: {request.tenant_name}")
    await db.commit()
    await db.refresh(lease)

    return RentalLeaseRead.model_validate(lease)


@rental_router.get("/{unit_id}/leases", response_model=PaginatedResponse[RentalLeaseRead])
async def list_rental_leases(
    unit_id: str,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """列出单位的所有租约记录"""
    query = select(RentalLease).where(RentalLease.unit_id == unit_id).order_by(RentalLease.lease_start.desc())
    count_query = select(func.count()).select_from(RentalLease).where(RentalLease.unit_id == unit_id)

    if status:
        query = query.where(RentalLease.status == status)
        count_query = count_query.where(RentalLease.status == status)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    leases = result.scalars().all()

    return PaginatedResponse(
        data=[RentalLeaseRead.model_validate(l) for l in leases],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@rental_router.put("/{unit_id}/leases/{lease_id}", response_model=RentalLeaseRead)
async def update_rental_lease(unit_id: str, lease_id: str, request: RentalLeaseUpdate, db: AsyncSession = Depends(get_db)):
    """更新租约记录"""
    result = await db.execute(select(RentalLease).where(RentalLease.id == lease_id, RentalLease.unit_id == unit_id))
    lease = result.scalar_one_or_none()
    if not lease:
        raise not_found("租约记录不存在")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lease, key, value)

    if lease.status == "active":
        unit_result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
        unit = unit_result.scalar_one_or_none()
        if unit:
            if request.tenant_name:
                unit.tenant_name = request.tenant_name
            if request.lease_start:
                unit.lease_start = request.lease_start
            if request.lease_end:
                unit.lease_end = request.lease_end
            if request.monthly_rent:
                unit.monthly_rent = request.monthly_rent

    await _log_audit(db, "tommy", "update_lease", "rental_lease", lease_id, f"更新租約記錄，租戶: {lease.tenant_name}")
    await db.commit()
    await db.refresh(lease)

    return RentalLeaseRead.model_validate(lease)


# 注册子路由到 Tommy 主路由
router.include_router(archive_router)
router.include_router(rental_router)
