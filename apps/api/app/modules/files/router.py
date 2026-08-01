"""
文件模块 API 路由 - 统一文件上传 + 文件访问
"""
import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.common.errors import validation_error, not_found
from app.modules.files.models import File as FileModel
from app.modules.files.schemas import FileUploadResponse, FileRead

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    description: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """统一文件上传接口 - 支持本地存储"""
    # 检查文件大小
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise validation_error(f"文件大小超過限制 ({settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB)")

    # 生成存储文件名
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    stored_filename = f"{file_id}{ext}"

    # 确保上传目录存在
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    # 保存文件到本地
    file_path = os.path.join(upload_dir, stored_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建数据库记录
    db_file = FileModel(
        id=file_id,
        original_filename=file.filename or "unknown",
        stored_filename=stored_filename,
        file_path=file_path,
        mime_type=file.content_type,
        file_size=len(content),
        uploaded_by=current_user["sub"],
        description=description,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    return FileUploadResponse(
        id=db_file.id,
        original_filename=db_file.original_filename,
        file_path=db_file.file_path,
        mime_type=db_file.mime_type,
        file_size=db_file.file_size,
        uploaded_by=db_file.uploaded_by,
        created_at=db_file.created_at,
    )


@router.get("/{file_id}", response_model=FileRead)
async def get_file_info(file_id: str, db: AsyncSession = Depends(get_db)):
    """获取文件信息"""
    result = await db.execute(select(FileModel).where(FileModel.id == file_id))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise not_found("文件不存在")
    return FileRead.model_validate(file_record)


@router.get("/{file_id}/content")
async def get_file_content(file_id: str, db: AsyncSession = Depends(get_db)):
    """获取文件内容（用于预览/下载）"""
    result = await db.execute(select(FileModel).where(FileModel.id == file_id))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise not_found("文件不存在")

    if not os.path.exists(file_record.file_path):
        raise not_found("文件已被删除或不存在")

    return FileResponse(
        path=file_record.file_path,
        filename=file_record.original_filename,
        media_type=file_record.mime_type or "application/octet-stream",
    )
