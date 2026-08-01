"""
数据库种子数据 - 启动时自动初始化默认数据
"""
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.modules.accounts.models import User, Role, Permission, user_roles, role_permissions
from app.modules.files.models import File
from app.modules.tommy.models import ArchiveDocument, RentalUnit, RentalPayment, RentalLease
from app.modules.audit.models import AuditLog


async def seed_data(db: AsyncSession) -> None:
    """初始化种子数据 - 仅在数据库为空时执行"""

    # 检查是否已有用户
    existing = await db.execute(select(User).limit(1))
    if existing.scalar_one_or_none():
        return

    # ===== 角色 =====
    roles_data = [
        ("admin", "系統管理員"),
        ("tommy", "校務處書記"),
        ("apple", "獎學金管理"),
        ("danielle", "宿費管理"),
        ("steven", "採購管理"),
        ("wendy", "家長通告"),
        ("leung", "薪酬資訊"),
    ]
    role_map = {}
    for name, desc in roles_data:
        role = Role(name=name, description=desc)
        db.add(role)
        await db.flush()
        role_map[name] = role

    # ===== 用户 =====
    users_data = [
        ("tommy", "tommy123", "Tommy", "tommy@py.edu.hk", ["tommy"]),
        ("admin", "admin123", "Admin", "admin@py.edu.hk", ["admin"]),
    ]
    user_map = {}
    for username, password, full_name, email, role_names in users_data:
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        user_map[username] = user

        # 关联角色
        for rn in role_names:
            await db.execute(
                user_roles.insert().values(user_id=user.id, role_id=role_map[rn].id)
            )

    tommy_id = user_map["tommy"].id

    # ===== 俊杰花园 8 住宅 + 9 车位 =====
    residential_units = [
        ("A座8樓B室", "陳先生", Decimal("18500"), date(2027, 6, 30), "active", None),
        ("A座7樓A室", "李太太", Decimal("16500"), date(2026, 9, 30), "expiring", None),
        ("A座6樓C室", "張先生", Decimal("15000"), date(2027, 3, 31), "active", None),
        ("B座5樓D室", "王女士", Decimal("16000"), date(2027, 12, 31), "active", None),
        ("B座4樓A室", "劉先生", Decimal("14500"), date(2026, 8, 15), "expiring", None),
        ("B座3樓B室", None, Decimal("14000"), None, "vacant", None),
        ("C座2樓C室", "黃太太", Decimal("15500"), date(2027, 6, 30), "active", None),
        ("C座1樓D室", "趙先生", Decimal("13500"), date(2026, 10, 31), "expiring", None),
        # 测试单位（有电邮，可测试邮件发送功能）
        ("測試A座1樓A室", "測試租戶（可修改電郵）", Decimal("9999"), date(2027, 6, 30), "active", "test@example.com"),
    ]

    parking_units = [
        ("車位01", "陳先生", Decimal("2500"), date(2027, 6, 30), "active", None),
        ("車位02", "王女士", Decimal("2500"), date(2026, 8, 31), "expiring", None),
        ("車位03", "李太太", Decimal("2500"), date(2027, 3, 31), "active", None),
        ("車位04", "張先生", Decimal("2500"), date(2027, 12, 31), "active", None),
        ("車位05", None, Decimal("2500"), None, "vacant", None),
        ("車位06", "劉先生", Decimal("2500"), date(2027, 6, 30), "active", None),
        ("車位07", None, Decimal("2500"), None, "vacant", None),
        ("車位08", "黃太太", Decimal("2500"), date(2026, 9, 15), "expiring", None),
        ("車位09", "趙先生", Decimal("2500"), date(2027, 3, 31), "active", None),
    ]

    unit_map = {}
    for number, tenant, rent, lease_end, status, email in residential_units:
        unit = RentalUnit(
            property_name="俊傑花園",
            unit_number=number,
            unit_type="住宅",
            tenant_name=tenant,
            tenant_email=email,
            lease_start=date(2024, 7, 1) if lease_end else None,
            lease_end=lease_end,
            monthly_rent=rent,
            is_occupied=(tenant is not None),
            status=status,
            created_by=tommy_id,
        )
        db.add(unit)
        await db.flush()
        unit_map[number] = unit

    for number, tenant, rent, lease_end, status, email in parking_units:
        unit = RentalUnit(
            property_name="俊傑花園",
            unit_number=number,
            unit_type="車位",
            tenant_name=tenant,
            tenant_email=email,
            lease_start=date(2024, 7, 1) if lease_end else None,
            lease_end=lease_end,
            monthly_rent=rent,
            is_occupied=(tenant is not None),
            status=status,
            created_by=tommy_id,
        )
        db.add(unit)
        await db.flush()
        unit_map[number] = unit

    # ===== 租约记录 =====
    for number, unit in unit_map.items():
        if unit.is_occupied and unit.tenant_name and unit.lease_start and unit.lease_end and unit.monthly_rent:
            lease = RentalLease(
                unit_id=unit.id,
                tenant_name=unit.tenant_name,
                lease_start=unit.lease_start,
                lease_end=unit.lease_end,
                monthly_rent=unit.monthly_rent,
                status="active",
                created_by=tommy_id,
            )
            db.add(lease)

    # ===== 缴费记录（当前月） =====
    today = date.today()
    for number, unit in unit_map.items():
        if unit.is_occupied and unit.monthly_rent:
            # 当 today.day <= 28 时，截止日为当月 28 号；否则为下月 5 号。
            # 原实现用 today.replace(month=today.month % 12 + 1, day=5) 会在 12 月跨年时
            # 生成同年的非法日期（如 2026-13-05）。改用 timedelta 推算避免越界。
            if today.day <= 28:
                due_date = today.replace(day=28)
            else:
                # 下月 5 号：从当月 1 号起 +32 天再回到当月 5 号
                first_of_next_month = today.replace(day=1) + timedelta(days=32)
                due_date = first_of_next_month.replace(day=5)
            payment = RentalPayment(
                unit_id=unit.id,
                amount=unit.monthly_rent,
                due_date=due_date,
                status="paid" if "陳" in (unit.tenant_name or "") else "pending",
                paid_date=today - timedelta(days=3) if "陳" in (unit.tenant_name or "") else None,
                paid_amount=unit.monthly_rent if "陳" in (unit.tenant_name or "") else None,
            )
            db.add(payment)

    # 确保上传目录存在
    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)

    # ===== 示例归档文档 =====
    sample_docs = [
        ("scan_20260715_001.pdf", "租務", "2026-07-15_租務_俊傑花園租金通知.pdf", Decimal("18500"), date(2026, 7, 31), "needs_review", "medium"),
        ("receipt_property_072.pdf", "財務", "2026-07-14_財務_維修費收據.pdf", Decimal("2300"), None, "confirmed", "high"),
        ("edb_notice_0713.pdf", "教育局通告", "2026-07-13_教育局通告_暑期安全指引.pdf", None, date(2026, 7, 25), "archived", "high"),
    ]

    for filename, category, suggested, amount, due, status, confidence in sample_docs:
        # 创建虚拟文件记录 + 写入一个简单的占位文件
        file_id = f"seed_file_{filename.split('.')[0]}"
        stored_filename = f"{file_id}.pdf"
        file_path = os.path.join(upload_dir, stored_filename)

        # 写入一个最小的占位 PDF（使得预览/下载不会 404）
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF")

        file_record = File(
            id=file_id,
            original_filename=filename,
            stored_filename=stored_filename,
            file_path=file_path,
            mime_type="application/pdf",
            file_size=os.path.getsize(file_path),
            uploaded_by=tommy_id,
        )
        db.add(file_record)

        ocr_texts = {
            "scan_20260715_001.pdf": "俊傑花園租金通知\n單位：A座 8樓 B室\n租戶：陳先生\n月份：2026年7月\n租金：HK$ 18,500\n繳付限期：2026年7月31日",
            "receipt_property_072.pdf": "維修費收據\n項目：冷氣維修\n金額：HK$ 2,300",
            "edb_notice_0713.pdf": "教育局通告\n主旨：暑期安全指引\n敬請各校注意暑期校園安全",
        }
        summaries = {
            "scan_20260715_001.pdf": "俊傑花園 A座 8樓 B室 2026年7月租金通知，租金 HK$ 18,500",
            "receipt_property_072.pdf": "維修費收據 HK$ 2,300",
            "edb_notice_0713.pdf": "教育局暑期安全指引通告",
        }

        doc = ArchiveDocument(
            original_file_id=file_id,
            original_filename=filename,
            category=category,
            suggested_name=suggested,
            amount=amount,
            due_date=due,
            ocr_text=ocr_texts.get(filename, ""),
            ai_summary=summaries.get(filename, ""),
            confidence=confidence,
            status=status,
            created_by=tommy_id,
            last_reviewed_by=tommy_id if status in ("confirmed", "archived") else None,
            last_reviewed_at=datetime.utcnow() if status in ("confirmed", "archived") else None,
        )
        db.add(doc)

    # ===== 审计日志 =====
    audit_entries = [
        ("tommy", "upload", "archive_document", "seed_doc_1", "Tommy 上傳文件 scan_20260715_001.pdf"),
        ("tommy", "ocr_complete", "archive_document", "seed_doc_1", "OCR Worker 完成文字識別"),
        ("tommy", "ai_classify", "archive_document", "seed_doc_1", "AI 建議分類為「租務」"),
        ("tommy", "confirm", "archive_document", "seed_doc_2", "人工確認 AI 結果"),
        ("tommy", "archive", "archive_document", "seed_doc_3", "文件已歸檔到「教育局通告」目錄"),
    ]
    for module, action, rtype, rid, detail in audit_entries:
        log = AuditLog(
            module=module,
            action=action,
            resource_type=rtype,
            resource_id=rid,
            user_id=tommy_id,
            user_name="Tommy",
            detail=detail,
        )
        db.add(log)

    await db.commit()
    print("[Seed] 种子数据初始化完成：2 用户, 7 角色, 17 租賃單位, 3 歸檔文檔")
