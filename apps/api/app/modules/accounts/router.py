"""
用户模块 API 路由
"""
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.core.config import settings
from app.core.security import verify_password, create_access_token, decode_access_token, get_password_hash, get_current_user
from app.common.errors import unauthorized, forbidden, not_found
from app.modules.accounts.schemas import LoginRequest, TokenResponse, UserRead, ChangePasswordRequest
from app.modules.accounts.models import User

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(
        select(User).where(User.username == request.username).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise unauthorized("用戶名或密碼錯誤")

    if not user.is_active:
        raise forbidden("用戶已被禁用")

    role_names = [role.name for role in user.roles]

    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "roles": role_names},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(
        access_token=access_token,
        user=UserRead(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=role_names,
            created_at=user.created_at,
        ),
    )


@router.get("/me", response_model=UserRead)
async def get_me(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    result = await db.execute(
        select(User).where(User.id == current_user["sub"]).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise not_found("用戶不存在")

    role_names = [role.name for role in user.roles]

    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=role_names,
        created_at=user.created_at,
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """修改当前用户密码"""
    result = await db.execute(select(User).where(User.id == current_user["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise not_found("用戶不存在")

    if not verify_password(request.old_password, user.hashed_password):
        raise unauthorized("目前密碼不正確")

    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    return {"message": "密碼修改成功"}
