"""
权限校验 - RBAC 权限系统
"""
from typing import List, Optional


# 权限格式: {module}:{resource}:{action}
# 例如: tommy:archive_documents:read

class PermissionChecker:
    """权限校验器"""

    # 预定义角色与权限映射
    ROLE_PERMISSIONS = {
        "admin": [
            # admin 有所有权限
            "*:*:*",
        ],
        "tommy": [
            "tommy:archive_documents:read",
            "tommy:archive_documents:write",
            "tommy:archive_documents:confirm",
            "tommy:archive_documents:archive",
            "tommy:archive_documents:delete",
            "tommy:rental_units:read",
            "tommy:rental_units:write",
            "tommy:rental_units:send_reminder",
            "tommy:rental_units:generate_lease",
            "files:upload",
            "ocr:jobs:create",
            "ocr:jobs:read",
            "ai:generate:create",
            "ai:generate:read",
            "audit:logs:read",
        ],
        "apple": [
            "apple:awards:read",
            "apple:awards:write",
            "apple:finance:read",
            "apple:finance:write",
            "files:upload",
            "ocr:jobs:create",
            "ocr:jobs:read",
        ],
        "danielle": [
            "danielle:hostel_payments:read",
            "danielle:hostel_payments:write",
            "danielle:hostel_payments:approve",
            "files:upload",
            "ocr:jobs:create",
            "ocr:jobs:read",
        ],
        "steven": [
            "steven:bids:read",
            "steven:bids:write",
            "steven:inventory:read",
            "steven:inventory:write",
            "files:upload",
            "ocr:jobs:create",
            "ocr:jobs:read",
        ],
        "wendy": [
            "wendy:notices:read",
            "wendy:notices:write",
            "wendy:substitute_arrangements:read",
            "wendy:substitute_arrangements:write",
            "files:upload",
            "ocr:jobs:create",
            "ocr:jobs:read",
        ],
        "leung": [
            "leung:payroll:read",
            "leung:payroll:write",
            "leung:payroll:export",
            "leung:information_summary:read",
            "leung:information_summary:write",
            "leung:task_assignment:read",
            "leung:task_assignment:write",
            "files:upload",
            "ocr:jobs:create",
            "ocr:jobs:read",
        ],
    }

    @classmethod
    def has_permission(cls, role: str, required_permission: str) -> bool:
        """检查角色是否拥有指定权限"""
        permissions = cls.ROLE_PERMISSIONS.get(role, [])
        if "*:*:*" in permissions:
            return True

        # 精确匹配
        if required_permission in permissions:
            return True

        # 通配符匹配 (例如 tommy:*:read)
        module, resource, action = required_permission.split(":")
        for perm in permissions:
            p_module, p_resource, p_action = perm.split(":")
            if (
                (p_module == module or p_module == "*")
                and (p_resource == resource or p_resource == "*")
                and (p_action == action or p_action == "*")
            ):
                return True

        return False

    @classmethod
    def get_user_permissions(cls, role: str) -> List[str]:
        """获取角色的所有权限"""
        return cls.ROLE_PERMISSIONS.get(role, [])

    @classmethod
    def can_access_module(cls, role: str, module: str) -> bool:
        """检查角色是否可以访问指定模块"""
        return cls.has_permission(role, f"{module}:*:read")
