"""
数据库基础模型导入 - 确保 create_all 能找到所有模型
"""
# 共用基础表
from app.modules.accounts.models import User, Role, UserRole, Permission, RolePermission
from app.modules.files.models import File
from app.modules.ocr.models import OcrJob
from app.modules.audit.models import AuditLog

# Tommy 模块表
from app.modules.tommy.models import ArchiveDocument, RentalUnit, RentalPayment
