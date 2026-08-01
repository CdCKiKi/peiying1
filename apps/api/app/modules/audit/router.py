"""
审计日志 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.security import get_current_user
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogCreate, AuditLogRead
from app.common.pagination import PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/logs", response_model=AuditLogRead)
async def create_audit_log(request: AuditLogCreate, db: AsyncSession = Depends(get_db)):
    """创建审计日志"""
    log = AuditLog(
        module=request.module,
        action=request.action,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        user_id=request.user_id,
        user_name=request.user_name,
        detail=request.detail,
        extra_data=request.extra_data,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return AuditLogRead.model_validate(log)


@router.get("/logs", response_model=PaginatedResponse[AuditLogRead])
async def list_audit_logs(
    module: str = Query(None, description="按模块筛选"),
    resource_id: str = Query(None, description="按资源 ID 筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """查询审计日志列表"""
    query = select(AuditLog).order_by(AuditLog.created_at.desc())

    if module:
        query = query.where(AuditLog.module == module)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)

    # 总数
    count_query = select(func.count()).select_from(AuditLog)
    if module:
        count_query = count_query.where(AuditLog.module == module)
    if resource_id:
        count_query = count_query.where(AuditLog.resource_id == resource_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return PaginatedResponse(
        data=[AuditLogRead.model_validate(log) for log in logs],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )
