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
from app.core.security import verify_password, create_access_token, decode_access_token
from app.common.errors import unauthorized, forbidden, not_found
from app.modules.accounts.schemas import LoginRequest, TokenResponse, UserRead
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
