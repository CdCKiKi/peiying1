"""
用户/角色/权限 ORM 模型
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


def generate_id() -> str:
    return str(uuid.uuid4())


# 角色-权限关联表（多对多）
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("id", String(36), primary_key=True, default=generate_id),
    Column("role_id", String(36), ForeignKey("roles.id"), nullable=False),
    Column("permission_id", String(36), ForeignKey("permissions.id"), nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# 用户-角色关联表（多对多）
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("id", String(36), primary_key=True, default=generate_id),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("role_id", String(36), ForeignKey("roles.id"), nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_id)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = relationship("Role", secondary=user_roles, back_populates="users")


class Role(Base):
    """角色表"""
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=generate_id)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    """权限表 - 格式: {module}:{resource}:{action}"""
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=generate_id)
    code = Column(String(100), unique=True, nullable=False, index=True)  # e.g. "tommy:archive_documents:read"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class UserRole(Base):
    """用户-角色关联（用于直接查询）"""
    __tablename__ = "user_roles_view"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    role_id = Column(String(36), ForeignKey("roles.id"))
    created_at = Column(DateTime)


class RolePermission(Base):
    """角色-权限关联（用于直接查询）"""
    __tablename__ = "role_permissions_view"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.id"))
    permission_id = Column(String(36), ForeignKey("permissions.id"))
    created_at = Column(DateTime)
