"""
Tommy 模块 API 路由 - 文件归档 + 租务管理
"""
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.db.session import get_db, async_session, fts_search_archive
from app.core.security import get_current_user
from app.core.config import settings
from app.core.xfyun_ocr_client import xfyun_ocr_client
from app.core.ai_classifier import ai_classifier
from app.core.emailer import emailer
from app.core.lease_generator import lease_generator
from app.common.errors import not_found, forbidden, validation_error
from app.common.pagination import PaginatedResponse, PaginationMeta
from app.modules.tommy.models import ArchiveDocument, RentalUnit, RentalPayment, RentalLease
from app.modules.tommy.schemas import (
    ArchiveDocumentCreate, ArchiveDocumentUpdate, ArchiveDocumentRead,
    RentalUnitCreate, RentalUnitUpdate, RentalUnitRead,
    RentalPaymentCreate, RentalPaymentUpdate, RentalPaymentRead,
    RentalLeaseCreate, RentalLeaseUpdate, RentalLeaseRead,
    BatchOperationRequest,
)
from app.modules.files.models import File as FileModel
from app.modules.audit.models import AuditLog

router = APIRouter(prefix="/tommy", tags=["tommy"])


async def _log_audit(db: AsyncSession, current_user: dict, module: str, action: str, resource_type: str, resource_id: str, detail: str = None):
    """写入审计日志"""
    log = AuditLog(
        module=module,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=current_user["sub"],
        user_name=current_user.get("username", ""),
        detail=detail,
    )
    db.add(log)


async def _run_ocr_and_classify(db: AsyncSession, doc: ArchiveDocument) -> None:
    """对单个文档执行 OCR + AI 分类"""
    doc.status = "ocr_running"
    await db.commit()

    ocr_text = ""
    confidence = "medium"

    # 获取文件记录
    file_result = await db.execute(select(FileModel).where(FileModel.id == doc.original_file_id))
    file_record = file_result.scalar_one_or_none()

    if settings.OCR_BACKEND == "xfyun" and file_record:
        try:
            file_full_path = os.path.join(settings.UPLOAD_DIR, file_record.stored_filename)
            if os.path.exists(file_full_path):
                ocr_text, confidence = await xfyun_ocr_client.recognize(file_full_path)
            else:
                ocr_text = f"（文件不存在: {file_full_path}）"
        except Exception as e:
            ocr_text = f"（OCR識別失敗: {str(e)}）"
            confidence = "low"
            doc.status = "exception"
            doc.ocr_text = ocr_text
            await db.commit()
            return
    else:
        ocr_text = "（Mock OCR）俊傑花園租金通知\n單位：A座 8樓 B室\n租戶：陳先生\n月份：2026年7月\n租金：HK$ 18,500\n繳付限期：2026年7月31日"

    doc.ocr_text = ocr_text

    # AI 分类
    # 注意：原代码 `doc.original_filename or file_record.original_filename if file_record else ""`
    # 解析为 `(doc.original_filename or file_record.original_filename) if file_record else ""`，
    # 当 file_record 为 None 但 doc.original_filename 有值时会错误返回空串。这里显式加括号。
    filename_for_classify = doc.original_filename or (file_record.original_filename if file_record else "")
    category, suggested_name, ai_summary, amount, due_date, classify_confidence = await ai_classifier.classify(
        ocr_text, filename_for_classify
    )

    doc.status = "needs_review"
    doc.category = category
    doc.suggested_name = suggested_name
    doc.amount = amount if amount > 0 else None
    # LLM/关键词匹配返回的 due_date 可能是字符串（如 "2026-08-31"），
    # SQLite Date 列只接受 Python date 对象，需要转换
    if due_date and isinstance(due_date, str):
        try:
            doc.due_date = date.fromisoformat(due_date[:10])
        except ValueError:
            doc.due_date = None
    elif isinstance(due_date, date):
        doc.due_date = due_date
    else:
        doc.due_date = None
    doc.ai_summary = ai_summary
    doc.confidence = classify_confidence if classify_confidence else confidence

    # 递增重试计数
    current_count = int(doc.retry_count or "0")
    doc.retry_count = str(current_count + 1)

    await db.commit()


async def _background_ocr_classify(doc_id: str) -> None:
    """后台异步执行 OCR + AI 分类（拥有独立 DB 会话）"""
    async with async_session() as db:
        try:
            result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
            doc = result.scalar_one_or_none()
            if not doc:
                return
            await _run_ocr_and_classify(db, doc)
            await db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"后台 OCR 失败 {doc_id}: {e}")


# ===== 文件归档 =====

archive_router = APIRouter(prefix="/archive-documents", tags=["tommy-archive"])


@archive_router.get("/stats")
async def get_archive_stats(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """获取归档统计（含图表数据）"""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    total = (await db.execute(select(func.count()).select_from(ArchiveDocument))).scalar() or 0
    pending_review = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.status == "needs_review"))).scalar() or 0
    confirmed = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.status == "confirmed"))).scalar() or 0
    archived = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.status == "archived"))).scalar() or 0
    exception = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.status == "exception"))).scalar() or 0
    today_upload = (await db.execute(select(func.count()).select_from(ArchiveDocument).where(ArchiveDocument.created_at >= today_start))).scalar() or 0

    # 分类分布（饼图数据）
    cat_result = await db.execute(
        select(ArchiveDocument.category, func.count())
        .where(ArchiveDocument.category != None)
        .group_by(ArchiveDocument.category)
    )
    category_breakdown = [{"category": row[0], "count": row[1]} for row in cat_result.all()]

    # 近 6 个月上传趋势（柱状图数据）
    monthly_trend = []
    for i in range(5, -1, -1):
        month_start = datetime(today.year, today.month, 1) - timedelta(days=30 * i)
        month_start = month_start.replace(day=1)
        if i == 0:
            month_end = today_start + timedelta(days=1)
        else:
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1)
        count = (await db.execute(
            select(func.count()).select_from(ArchiveDocument)
            .where(ArchiveDocument.created_at >= month_start, ArchiveDocument.created_at < month_end)
        )).scalar() or 0
        monthly_trend.append({"month": month_start.strftime("%Y-%m"), "count": count})

    return {
        "total": total,
        "pending_review": pending_review,
        "confirmed": confirmed,
        "archived": archived,
        "exception": exception,
        "today_upload": today_upload,
        "category_breakdown": category_breakdown,
        "monthly_trend": monthly_trend,
    }


@archive_router.get("", response_model=PaginatedResponse[ArchiveDocumentRead])
async def list_archive_documents(
    category: str = Query(None, description="按分类筛选"),
    status: str = Query(None, description="按状态筛选"),
    search: str = Query(None, description="搜索文件名、分类、金额、日期或 OCR 原文"),
    date_from: str = Query(None, description="创建日期起始 (YYYY-MM-DD)"),
    date_to: str = Query(None, description="创建日期截止 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出归档文档（FTS5 全文搜索 + 日期范围筛选）"""
    query = select(ArchiveDocument).order_by(ArchiveDocument.created_at.desc())
    count_query = select(func.count()).select_from(ArchiveDocument)

    if category:
        query = query.where(ArchiveDocument.category == category)
        count_query = count_query.where(ArchiveDocument.category == category)
    if status:
        query = query.where(ArchiveDocument.status == status)
        count_query = count_query.where(ArchiveDocument.status == status)

    # 日期范围筛选
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.where(ArchiveDocument.created_at >= dt_from)
            count_query = count_query.where(ArchiveDocument.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(ArchiveDocument.created_at < dt_to)
            count_query = count_query.where(ArchiveDocument.created_at < dt_to)
        except ValueError:
            pass

    # 搜索：优先使用 FTS5，失败回退到 ILIKE
    if search:
        fts_ids = await fts_search_archive(db, search)
        if fts_ids:
            query = query.where(ArchiveDocument.id.in_(fts_ids))
            count_query = count_query.where(ArchiveDocument.id.in_(fts_ids))
        else:
            # ILIKE 回退
            search_filter = or_(
                ArchiveDocument.original_filename.ilike(f"%{search}%"),
                ArchiveDocument.category.ilike(f"%{search}%"),
                ArchiveDocument.suggested_name.ilike(f"%{search}%"),
                ArchiveDocument.ai_summary.ilike(f"%{search}%"),
                ArchiveDocument.ocr_text.ilike(f"%{search}%"),
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
async def create_archive_document(request: ArchiveDocumentCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
        created_by=current_user["sub"],
        note=request.note,
    )
    db.add(doc)
    await db.flush()

    await _log_audit(db, current_user, "tommy", "upload", "archive_document", doc.id, f"上傳文件 {doc.original_filename}")
    await db.commit()
    await db.refresh(doc)

    # 后台执行 OCR + AI 分类（不阻塞响应）
    # 使用 FastAPI BackgroundTasks 而非 asyncio.create_task，
    # 后者脱离请求生命周期，任务可能在事件循环清理时被取消。
    background_tasks.add_task(_background_ocr_classify, doc.id)

    return ArchiveDocumentRead.model_validate(doc)


# ===== 批量操作 =====
# 注意：这些路由必须在 /{doc_id} 系列路由之前注册，
# 否则 /batch/confirm 会被 /{doc_id}/confirm 匹配（doc_id="batch"）。

@archive_router.post("/batch/confirm")
async def batch_confirm(request: BatchOperationRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """批量确认 AI 结果"""
    confirmed_count = 0
    errors = []

    for doc_id in request.doc_ids:
        result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            errors.append(f"{doc_id}: 文档不存在")
            continue
        if doc.status != "needs_review":
            errors.append(f"{doc.original_filename}: 状态不是待確認")
            continue

        doc.status = "confirmed"
        doc.last_reviewed_by = current_user["sub"]
        doc.last_reviewed_at = datetime.utcnow()
        await _log_audit(db, current_user, "tommy", "batch_confirm", "archive_document", doc.id, "批量確認 AI 結果")
        confirmed_count += 1

    await db.commit()
    return {"confirmed": confirmed_count, "errors": errors}


@archive_router.post("/batch/archive")
async def batch_archive(request: BatchOperationRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """批量归档"""
    archived_count = 0
    errors = []

    for doc_id in request.doc_ids:
        result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            errors.append(f"{doc_id}: 文档不存在")
            continue
        if doc.status not in ("confirmed", "needs_review"):
            errors.append(f"{doc.original_filename}: 状态不可归档")
            continue

        if doc.status == "needs_review":
            await _log_audit(db, current_user, "tommy", "batch_confirm", "archive_document", doc.id, "批量歸檔時自動確認 AI 結果")
        doc.status = "archived"
        doc.last_reviewed_by = current_user["sub"]
        doc.last_reviewed_at = datetime.utcnow()
        await _log_audit(db, current_user, "tommy", "batch_archive", "archive_document", doc.id, f"批量歸檔到「{doc.category or '其他'}」目錄")
        archived_count += 1

    await db.commit()
    return {"archived": archived_count, "errors": errors}


@archive_router.post("/batch/retry")
async def batch_retry(request: BatchOperationRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """批量重试异常文档"""
    retried_count = 0
    errors = []

    for doc_id in request.doc_ids:
        result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            errors.append(f"{doc_id}: 文档不存在")
            continue
        if doc.status not in ("exception", "needs_review"):
            errors.append(f"{doc.original_filename}: 状态不支持重試")
            continue

        await _run_ocr_and_classify(db, doc)
        await _log_audit(db, current_user, "tommy", "batch_retry", "archive_document", doc.id, f"批量重試 OCR 和 AI 分類 (第 {doc.retry_count} 次)")
        retried_count += 1

    await db.commit()
    return {"retried": retried_count, "errors": errors}


# ===== 单文档操作 =====

@archive_router.get("/{doc_id}", response_model=ArchiveDocumentRead)
async def get_archive_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """获取归档文档详情"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")
    return ArchiveDocumentRead.model_validate(doc)


@archive_router.patch("/{doc_id}", response_model=ArchiveDocumentRead)
async def update_archive_document(doc_id: str, request: ArchiveDocumentUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """更新归档文档（人工修改 AI 结果）"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doc, key, value)

    doc.last_reviewed_by = current_user["sub"]
    doc.last_reviewed_at = datetime.utcnow()

    await _log_audit(db, current_user, "tommy", "edit", "archive_document", doc.id, "人工修改 AI 結果")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.delete("/{doc_id}")
async def delete_archive_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """删除归档文档"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    await _log_audit(db, current_user, "tommy", "delete", "archive_document", doc.id, f"刪除文件 {doc.original_filename}")
    await db.delete(doc)
    await db.commit()
    return {"message": "已刪除", "id": doc_id}


@archive_router.post("/{doc_id}/run-ocr", response_model=ArchiveDocumentRead)
async def run_ocr(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """触发 OCR 识别"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    await _run_ocr_and_classify(db, doc)

    await _log_audit(db, current_user, "tommy", "run_ocr", "archive_document", doc.id, "重新運行 OCR")
    await _log_audit(db, current_user, "tommy", "ai_classify", "archive_document", doc.id, f"AI 重新分類為「{doc.category}」")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/retry", response_model=ArchiveDocumentRead)
async def retry_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """重试失败的文档（重新 OCR + AI 分类）"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    if doc.status not in ("exception", "needs_review"):
        raise validation_error("只有異常或待復核狀態的文檔才能重試")

    await _run_ocr_and_classify(db, doc)

    await _log_audit(db, current_user, "tommy", "retry", "archive_document", doc.id, f"重試 OCR 和 AI 分類 (第 {doc.retry_count} 次)")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/classify", response_model=ArchiveDocumentRead)
async def classify_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
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

    await _log_audit(db, current_user, "tommy", "ai_classify", "archive_document", doc.id, f"AI 重新分類為「{doc.category}」")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/confirm", response_model=ArchiveDocumentRead)
async def confirm_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """人工确认 AI 结果"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    doc.status = "confirmed"
    doc.last_reviewed_by = current_user["sub"]
    doc.last_reviewed_at = datetime.utcnow()

    await _log_audit(db, current_user, "tommy", "confirm", "archive_document", doc.id, "人工確認 AI 結果")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/archive", response_model=ArchiveDocumentRead)
async def archive_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """确认归档"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    doc.status = "archived"
    doc.last_reviewed_by = current_user["sub"]
    doc.last_reviewed_at = datetime.utcnow()

    await _log_audit(db, current_user, "tommy", "archive", "archive_document", doc.id, f"文件已歸檔到「{doc.category or '其他'}」目錄")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/undo-archive", response_model=ArchiveDocumentRead)
async def undo_archive_document(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """撤销归档或复核操作"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    if doc.status == "archived":
        doc.status = "confirmed"
        await _log_audit(db, current_user, "tommy", "undo_archive", "archive_document", doc.id, "撤銷歸檔，狀態回退為已確認")
    elif doc.status == "confirmed":
        doc.status = "needs_review"
        await _log_audit(db, current_user, "tommy", "undo_confirm", "archive_document", doc.id, "撤銷確認，狀態回退為待復核")
    else:
        raise validation_error("当前状态无法撤销")

    doc.last_reviewed_by = current_user["sub"]
    doc.last_reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


@archive_router.post("/{doc_id}/flag-exception", response_model=ArchiveDocumentRead)
async def flag_exception(doc_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """标记异常"""
    result = await db.execute(select(ArchiveDocument).where(ArchiveDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise not_found("归档文档不存在")

    doc.status = "exception"
    doc.last_reviewed_by = current_user["sub"]
    doc.last_reviewed_at = datetime.utcnow()

    await _log_audit(db, current_user, "tommy", "flag_exception", "archive_document", doc.id, "標記為異常，等待人工處理")
    await db.commit()
    await db.refresh(doc)

    return ArchiveDocumentRead.model_validate(doc)


# ===== 租务管理 =====

rental_router = APIRouter(prefix="/rental-units", tags=["tommy-rental"])


@rental_router.delete("/{unit_id}")
async def delete_rental_unit(unit_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """删除租赁单位及其关联的租约和缴费记录"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    unit_number = unit.unit_number

    # 删除关联的缴费记录
    payments = (await db.execute(select(RentalPayment).where(RentalPayment.unit_id == unit_id))).scalars().all()
    for p in payments:
        await db.delete(p)

    # 删除关联的租约记录
    leases = (await db.execute(select(RentalLease).where(RentalLease.unit_id == unit_id))).scalars().all()
    for l in leases:
        await db.delete(l)

    await db.delete(unit)
    await _log_audit(db, current_user, "tommy", "delete_unit", "rental_unit", unit_id, f"刪除租賃單位 {unit_number} 及 {len(leases)} 條租約、{len(payments)} 條繳費記錄")
    await db.commit()

    return {"message": "已刪除", "unit_id": unit_id}


@rental_router.get("/stats")
async def get_rental_stats(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
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


def _refresh_unit_status(unit: RentalUnit) -> None:
    """根据 lease_end 自动刷新单位状态"""
    if not unit.lease_end:
        return
    today = date.today()
    remaining = (unit.lease_end - today).days
    if remaining < 0:
        unit.status = "expired"
    elif remaining <= 15:
        unit.status = "expiring"
    elif unit.is_occupied:
        unit.status = "active"


@rental_router.get("", response_model=PaginatedResponse[RentalUnitRead])
async def list_rental_units(
    unit_type: str = Query(None, description="按类型筛选: 住宅/車位"),
    status: str = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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

    # 自动刷新状态并持久化
    for u in units:
        _refresh_unit_status(u)
    if units:
        await db.commit()

    return PaginatedResponse(
        data=[RentalUnitRead.model_validate(u) for u in units],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@rental_router.post("", response_model=RentalUnitRead)
async def create_rental_unit(request: RentalUnitCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """创建租赁单位（同时创建初始租约）"""
    unit = RentalUnit(
        unit_number=request.unit_number,
        unit_type=request.unit_type,
        tenant_name=request.tenant_name,
        tenant_email=request.tenant_email,
        lease_start=request.lease_start,
        lease_end=request.lease_end,
        monthly_rent=request.monthly_rent,
        is_occupied=request.is_occupied,
        notes=request.notes,
        created_by=current_user["sub"],
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
            created_by=current_user["sub"],
        )
        db.add(lease)
        await db.flush()
        await _log_audit(db, current_user, "tommy", "create_lease", "rental_lease", lease.id, f"為單位 {request.unit_number} 創建初始租約，租戶: {request.tenant_name}")

        # 新增租約同時創建一條待繳的繳費記錄
        first_payment = RentalPayment(
            unit_id=unit.id,
            amount=request.monthly_rent,
            due_date=request.lease_start,
            status="pending",
        )
        db.add(first_payment)
        await db.flush()
        await _log_audit(db, current_user, "tommy", "create_payment", "rental_payment", first_payment.id, f"新租約自動生成繳費 {request.unit_number} HK${request.monthly_rent}")

    await _log_audit(db, current_user, "tommy", "create_unit", "rental_unit", unit.id, f"新增租賃單位 {request.unit_number}")
    await db.commit()
    await db.refresh(unit)
    return RentalUnitRead.model_validate(unit)


@rental_router.get("/expiring")
async def list_expiring_leases(
    days: int = Query(90, description="未來 N 天內到期"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出即将到期和已过期的租约单位"""
    today = date.today()
    cutoff = today + timedelta(days=days)

    result = await db.execute(
        select(RentalUnit)
        .where(
            RentalUnit.lease_end <= cutoff,
            RentalUnit.is_occupied == True,
        )
        .order_by(RentalUnit.lease_end)
    )
    units = result.scalars().all()

    # 计算剩余天数并分类
    expiring_list = []
    for u in units:
        remaining = (u.lease_end - today).days if u.lease_end else 0
        if remaining < 0:
            severity = "expired"
        elif remaining <= 15:
            severity = "danger"
        elif remaining <= 30:
            severity = "warning"
        else:
            severity = "info"
        pending_payment = (await db.execute(
            select(RentalPayment)
            .where(RentalPayment.unit_id == u.id, RentalPayment.status == "pending")
            .order_by(RentalPayment.due_date.asc())
            .limit(1)
        )).scalar_one_or_none()

        expiring_list.append({
            "id": u.id,
            "unit_number": u.unit_number,
            "unit_type": u.unit_type,
            "tenant_name": u.tenant_name,
            "tenant_email": u.tenant_email,
            "lease_end": str(u.lease_end) if u.lease_end else None,
            "monthly_rent": float(u.monthly_rent) if u.monthly_rent else None,
            "remaining_days": remaining,
            "severity": severity,
            "has_pending_payment": pending_payment is not None,
        })

    return {"data": expiring_list, "total": len(expiring_list)}


@rental_router.get("/{unit_id}", response_model=RentalUnitRead)
async def get_rental_unit(unit_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """获取租赁单位详情"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")
    _refresh_unit_status(unit)
    await db.commit()
    return RentalUnitRead.model_validate(unit)


@rental_router.post("/{unit_id}/vacate")
async def vacate_rental_unit(unit_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """将已到期单位转为空置"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    unit.is_occupied = False
    unit.tenant_name = None
    unit.tenant_email = None
    unit.lease_start = None
    unit.lease_end = None
    unit.monthly_rent = None
    unit.status = "vacant"

    await _log_audit(db, current_user, "tommy", "vacate_unit", "rental_unit", unit_id, f"單位 {unit.unit_number} 已轉為空置")
    await db.commit()
    await db.refresh(unit)
    return {"message": "已轉為空置", "unit_id": unit_id}


@rental_router.patch("/{unit_id}", response_model=RentalUnitRead)
async def update_rental_unit(unit_id: str, request: RentalUnitUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """更新租赁单位"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(unit, key, value)

    await _log_audit(db, current_user, "tommy", "update_unit", "rental_unit", unit_id, f"更新租賃單位 {unit.unit_number}")
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
    current_user: dict = Depends(get_current_user),
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
async def create_rental_payment(unit_id: str, request: RentalPaymentCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """创建缴费记录"""
    import logging as _lg
    _log = _lg.getLogger(__name__)
    try:
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
        await db.flush()  # 确保 payment.id 已生成，否则 _log_audit 收到 None
        await _log_audit(db, current_user, "tommy", "create_payment", "rental_payment", payment.id, f"新增繳費記錄 {unit.unit_number} HK${request.amount}")
        await db.commit()
        await db.refresh(payment)
        return RentalPaymentRead.model_validate(payment)
    except Exception as e:
        _log.error(f"create_rental_payment 异常: {type(e).__name__}: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"创建缴费记录失败: {type(e).__name__}: {e}")


@rental_router.patch("/{unit_id}/payments/{payment_id}", response_model=RentalPaymentRead)
async def update_rental_payment(
    unit_id: str,
    payment_id: str,
    request: RentalPaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新缴费记录（记录收款）"""
    result = await db.execute(select(RentalPayment).where(RentalPayment.id == payment_id, RentalPayment.unit_id == unit_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise not_found("缴费记录不存在")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(payment, key, value)

    await _log_audit(db, current_user, "tommy", "update_payment", "rental_payment", payment_id, f"更新繳費記錄，狀態: {payment.status}")
    await db.commit()
    await db.refresh(payment)
    return RentalPaymentRead.model_validate(payment)


@rental_router.post("/{unit_id}/send-reminder")
async def send_reminder(unit_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """发送缴费提醒（真实发送邮件）"""
    result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise not_found("租赁单位不存在")

    # 查找待缴费记录（单位可能有多条 pending 记录，取最早到期的一条）
    pending_payment = (await db.execute(
        select(RentalPayment)
        .where(RentalPayment.unit_id == unit_id, RentalPayment.status == "pending")
        .order_by(RentalPayment.due_date.asc())
        .limit(1)
    )).scalar_one_or_none()

    email_sent = False
    if unit.tenant_email and pending_payment:
        email_sent = await emailer.send_rental_reminder(
            to_email=unit.tenant_email,
            tenant_name=unit.tenant_name or "租戶",
            unit_number=unit.unit_number,
            amount=float(pending_payment.amount),
            due_date=str(pending_payment.due_date),
        )

    if email_sent:
        detail = f"已向 {unit.tenant_name} ({unit.tenant_email}) 發送繳費提醒郵件"
    elif unit.tenant_email:
        detail = f"郵件發送失敗，已記錄提醒（{unit.tenant_name}）"
    else:
        detail = f"已記錄繳費提醒（未設定租戶電郵，無法發送）"

    await _log_audit(db, current_user, "tommy", "send_reminder", "rental_unit", unit_id, detail)
    await db.commit()

    return {
        "message": "繳費提醒已處理",
        "unit_id": unit_id,
        "tenant": unit.tenant_name,
        "email_sent": email_sent,
        "detail": detail,
    }


@rental_router.get("/payments/overdue")
async def list_overdue_payments(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出所有逾期和7天内即将到期的缴费记录"""
    today = date.today()
    cutoff = today + timedelta(days=7)

    # 查所有 pending/overdue 的缴费记录，且 due_date <= today+7
    result = await db.execute(
        select(RentalPayment, RentalUnit)
        .join(RentalUnit, RentalPayment.unit_id == RentalUnit.id)
        .where(RentalPayment.status.in_(["pending", "overdue"]))
        .where(RentalPayment.due_date <= cutoff)
        .order_by(RentalPayment.due_date)
    )
    rows = result.all()

    overdue_list = []
    for payment, unit in rows:
        overdue_days = (today - payment.due_date).days if payment.due_date < today else 0
        remaining_days = max(0, (payment.due_date - today).days)  # 剩余天数
        # 不在此处持久化状态：GET 不应有副作用。
        # 已逾期但 DB 仍为 pending 的记录在响应中按 overdue 展示；
        # 实际落库应由独立的批量更新接口或定时任务负责。
        display_status = "overdue" if overdue_days > 0 else payment.status

        overdue_list.append({
            "payment_id": payment.id,
            "unit_id": unit.id,
            "unit_number": unit.unit_number,
            "unit_type": unit.unit_type,
            "tenant_name": unit.tenant_name,
            "tenant_email": unit.tenant_email,
            "amount": float(payment.amount),
            "due_date": str(payment.due_date),
            "overdue_days": max(0, overdue_days),
            "remaining_days": remaining_days,
            "status": display_status,
            "paid_date": str(payment.paid_date) if payment.paid_date else None,
            "paid_amount": float(payment.paid_amount) if payment.paid_amount else None,
        })

    return {"data": overdue_list, "total": len(overdue_list)}


@rental_router.post("/{unit_id}/generate-lease")
async def generate_lease(unit_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """生成租约文件（返回下载）"""
    import logging as _lg
    _log = _lg.getLogger(__name__)
    try:
        result = await db.execute(select(RentalUnit).where(RentalUnit.id == unit_id))
        unit = result.scalar_one_or_none()
        if not unit:
            raise not_found("租赁单位不存在")

        if not unit.tenant_name or not unit.lease_start or not unit.lease_end or not unit.monthly_rent:
            raise validation_error("租戶資訊不完整，無法生成租約")

        buffer, filename = lease_generator.generate(
            unit_number=unit.unit_number,
            tenant_name=unit.tenant_name,
            lease_start=unit.lease_start,
            lease_end=unit.lease_end,
            monthly_rent=unit.monthly_rent,
        )

        await _log_audit(db, current_user, "tommy", "generate_lease", "rental_unit", unit_id, f"生成租約文件 {filename}")
        await db.commit()

        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if filename.endswith(".docx") else "text/plain; charset=utf-8"

        return StreamingResponse(
            buffer,
            media_type=content_type,
            headers={"Content-Disposition": _encode_content_disposition(filename)},
        )
    except Exception as e:
        _log.error(f"generate_lease 异常: {type(e).__name__}: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"生成租约失败: {type(e).__name__}: {e}")


def _encode_content_disposition(filename: str) -> str:
    """构造 Content-Disposition 头，兼容中文文件名（RFC 5987）。

    HTTP 头只能用 latin-1 编码，含非 ASCII 字符的文件名必须用
    `filename*=UTF-8''<percent-encoded>` 形式传递，否则会触发
    UnicodeEncodeError。这里同时给出 ASCII fallback 提高兼容性。
    """
    from urllib.parse import quote
    try:
        filename.encode("latin-1")
        # 纯 ASCII，可直接用 filename="..."
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        ascii_fallback = "lease.docx"
        encoded = quote(filename, safe="")
        return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


@rental_router.post("/{unit_id}/leases", response_model=RentalLeaseRead)
async def create_rental_lease(unit_id: str, request: RentalLeaseCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
        await _log_audit(db, current_user, "tommy", "expire_lease", "rental_lease", old_lease.id, f"租約已到期，租戶: {old_lease.tenant_name}")

    lease = RentalLease(
        unit_id=unit_id,
        tenant_name=request.tenant_name,
        lease_start=request.lease_start,
        lease_end=request.lease_end,
        monthly_rent=request.monthly_rent,
        status="active",
        notes=request.notes,
        created_by=current_user["sub"],
    )
    db.add(lease)
    await db.flush()

    unit.tenant_name = request.tenant_name
    unit.lease_start = request.lease_start
    unit.lease_end = request.lease_end
    unit.monthly_rent = request.monthly_rent
    unit.is_occupied = True
    unit.status = "active"

    # 續租同時創建一條待繳的繳費記錄
    renewal_payment = RentalPayment(
        unit_id=unit_id,
        amount=request.monthly_rent,
        due_date=request.lease_start,
        status="pending",
    )
    db.add(renewal_payment)
    await db.flush()
    await _log_audit(db, current_user, "tommy", "create_payment", "rental_payment", renewal_payment.id, f"續租自動生成繳費 {unit.unit_number} HK${request.monthly_rent}")

    await _log_audit(db, current_user, "tommy", "create_lease", "rental_lease", lease.id, f"為單位 {unit.unit_number} 新增租約，租戶: {request.tenant_name}")
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
    current_user: dict = Depends(get_current_user),
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
async def update_rental_lease(unit_id: str, lease_id: str, request: RentalLeaseUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
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

    await _log_audit(db, current_user, "tommy", "update_lease", "rental_lease", lease_id, f"更新租約記錄，租戶: {lease.tenant_name}")
    await db.commit()
    await db.refresh(lease)

    return RentalLeaseRead.model_validate(lease)


# 注册子路由到 Tommy 主路由
router.include_router(archive_router)
router.include_router(rental_router)
