"""
培英 AI 行政平台 - API 功能测试脚本
按测试指南顺序执行，覆盖 2.1~2.15 全部功能点
"""
import httpx
import time
import json
import sys
import os

BASE = "http://localhost:8000/api/v1"
TEST_DATA_DIR = r"c:\Users\27840\Desktop\Tommy\test_data"

# 测试结果记录
results = []
current_user = {}

def log(test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"test": test_name, "status": status, "detail": detail})
    mark = "✓" if passed else "✗"
    print(f"  [{mark}] {test_name}" + (f" — {detail}" if detail and not passed else ""))

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ===== 2.1 登入功能 =====
def test_login():
    section("2.1 登入功能")
    with httpx.Client(timeout=30) as c:
        # 正确密码登录
        r = c.post(f"{BASE}/accounts/login", json={"username": "tommy", "password": "tommy123"})
        log("登录（正确密码）", r.status_code == 200, f"status={r.status_code}")
        if r.status_code != 200:
            print(f"    响应: {r.text[:300]}")
            return None
        data = r.json()
        token = data.get("access_token")
        log("返回 access_token", bool(token))
        user = data.get("user", {})
        log("返回用户信息", bool(user.get("username")))
        log("用户角色存在", bool(user.get("roles")), str(user.get("roles")))

        # 错误密码登录
        r2 = c.post(f"{BASE}/accounts/login", json={"username": "tommy", "password": "wrong"})
        log("错误密码拒绝登录", r2.status_code in (400, 401), f"status={r2.status_code}")

        # admin 登录
        r3 = c.post(f"{BASE}/accounts/login", json={"username": "admin", "password": "admin123"})
        log("admin 账号登录", r3.status_code == 200, f"status={r3.status_code}")

        # 获取当前用户信息
        r4 = c.get(f"{BASE}/accounts/me", headers={"Authorization": f"Bearer {token}"})
        log("获取 /me 接口", r4.status_code == 200, f"status={r4.status_code}")

    return token

# ===== 2.2 文件上传与智能归档 =====
def test_upload_and_classify(token):
    section("2.2 文件上传与智能归档")
    headers = {"Authorization": f"Bearer {token}"}
    test_files = [
        ("test_01_rental_notice.pdf", "租務", "PDF"),
        ("test_02_receipt.pdf", "財務", "PDF"),
        ("test_03_edb_notice.pdf", "教育局通告", "PDF"),
        ("test_04_meeting.pdf", "會議", "PDF"),
        ("test_05_hr_contract.docx", "人事", "DOCX"),
        ("test_06_scan_image.png", "租務", "PNG"),
    ]
    doc_ids = []
    file_ids = []
    with httpx.Client(timeout=60, headers=headers) as c:
        for filename, expected_cat, ftype in test_files:
            filepath = os.path.join(TEST_DATA_DIR, filename)
            if not os.path.exists(filepath):
                log(f"上传 {filename}", False, "文件不存在")
                continue
            # 上传文件
            with open(filepath, "rb") as f:
                r = c.post(f"{BASE}/files/upload", files={"file": (filename, f)})
            log(f"上传 {filename}", r.status_code in (200, 201), f"status={r.status_code}")
            if r.status_code not in (200, 201):
                print(f"    响应: {r.text[:300]}")
                continue
            file_id = r.json().get("id")
            file_ids.append((file_id, filename))
            # 创建归档文档
            r2 = c.post(f"{BASE}/tommy/archive-documents", json={"original_file_id": file_id})
            log(f"创建归档 {filename}", r2.status_code in (200, 201), f"status={r2.status_code}")
            if r2.status_code not in (200, 201):
                print(f"    响应: {r2.text[:300]}")
                continue
            doc_id = r2.json().get("id")
            doc_ids.append((doc_id, filename, expected_cat))

        # 等待后台 OCR + AI 分类完成（最多等 90 秒）
        print("\n  等待后台 OCR + AI 分类完成...")
        max_wait = 90
        for doc_id, filename, expected_cat in doc_ids:
            waited = 0
            doc_data = None
            while waited < max_wait:
                r = c.get(f"{BASE}/tommy/archive-documents/{doc_id}")
                if r.status_code == 200:
                    doc_data = r.json()
                    status = doc_data.get("status")
                    if status in ("needs_review", "archived", "confirmed", "exception"):
                        break
                time.sleep(3)
                waited += 3
            if not doc_data:
                log(f"OCR+分类 {filename}", False, "超时未获取到文档")
                continue
            actual_status = doc_data.get("status")
            actual_cat = doc_data.get("category")
            ocr_text = doc_data.get("ocr_text", "")

            log(f"OCR 完成 {filename}", actual_status != "pending" and actual_status != "ocr_running",
                f"status={actual_status}")
            log(f"OCR 原文非空 {filename}", bool(ocr_text and len(ocr_text) > 10),
                f"len={len(ocr_text) if ocr_text else 0}")
            if actual_status == "exception":
                log(f"AI 分类 {filename}", False, f"异常状态: {ocr_text[:100] if ocr_text else 'no text'}")
            else:
                cat_match = actual_cat == expected_cat
                log(f"AI 分类 {filename} (期望={expected_cat}, 实际={actual_cat})",
                    cat_match, "" if cat_match else f"期望「{expected_cat}」，实际「{actual_cat}」")
                # 金额验证（仅 test_01）
                if filename == "test_01_rental_notice.pdf":
                    amount = doc_data.get("amount")
                    log(f"金额提取 {filename}", amount is not None and float(amount) == 18500,
                        f"amount={amount}")
                # 打印 AI 摘要
                summary = doc_data.get("ai_summary", "")
                if summary:
                    print(f"    AI摘要: {summary[:80]}")
    return doc_ids, file_ids, headers

# ===== 2.3 文件预览 =====
def test_file_preview(headers, file_ids):
    section("2.3 文件预览")
    with httpx.Client(timeout=30, headers=headers) as c:
        for file_id, filename in file_ids:
            # 获取文件信息
            r = c.get(f"{BASE}/files/{file_id}")
            log(f"获取文件信息 {filename}", r.status_code == 200, f"status={r.status_code}")

            # 获取文件内容（预览/下载）
            r2 = c.get(f"{BASE}/files/{file_id}/content")
            log(f"获取文件内容 {filename}", r2.status_code == 200, f"status={r2.status_code}")
            if r2.status_code == 200:
                content_type = r2.headers.get("content-type", "")
                content_disp = r2.headers.get("content-disposition", "")
                has_content = len(r2.content) > 0
                log(f"文件内容非空 {filename}", has_content, f"size={len(r2.content)}")
                log(f"Content-Type 存在 {filename}", bool(content_type), content_type)

                # PDF 应使用 application/pdf
                if filename.endswith(".pdf"):
                    log(f"PDF 类型正确 {filename}", "pdf" in content_type.lower(),
                        f"content-type={content_type}")
                # PNG 应使用 image/
                elif filename.endswith(".png"):
                    log(f"PNG 类型正确 {filename}", content_type.startswith("image/"),
                        f"content-type={content_type}")
                # DOCX 应使用 wordprocessingml
                elif filename.endswith(".docx"):
                    log(f"DOCX 类型正确 {filename}",
                        "wordprocessingml" in content_type.lower() or "octet-stream" in content_type.lower(),
                        f"content-type={content_type}")

# ===== 2.4 搜索与筛选 =====
def test_search_and_filter(headers, doc_ids):
    section("2.4 搜索与筛选功能")
    with httpx.Client(timeout=30, headers=headers) as c:
        # 关键词搜索
        r = c.get(f"{BASE}/tommy/archive-documents?search=租金")
        log("搜索「租金」", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            log("搜索返回结果", data.get("pagination", {}).get("total", 0) > 0,
                f"total={data.get('pagination', {}).get('total', 0)}")

        # 全文搜索（OCR 原文中的词）
        r = c.get(f"{BASE}/tommy/archive-documents?search=俊傑花園")
        log("全文搜索「俊傑花園」", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            log("全文搜索返回结果", data.get("pagination", {}).get("total", 0) > 0,
                f"total={data.get('pagination', {}).get('total', 0)}")

        # 按分类筛选
        r = c.get(f"{BASE}/tommy/archive-documents?category=租務")
        log("筛选分类=租務", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            all_match = all(d.get("category") == "租務" for d in items)
            log("筛选结果全为租務", all_match, f"count={len(items)}")

        # 按状态筛选
        r = c.get(f"{BASE}/tommy/archive-documents?status=needs_review")
        log("筛选状态=needs_review", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            all_match = all(d.get("status") == "needs_review" for d in items)
            log("筛选结果全为needs_review", all_match, f"count={len(items)}")

        # 日期范围筛选
        r = c.get(f"{BASE}/tommy/archive-documents?date_from=2026-01-01&date_to=2026-12-31")
        log("日期范围筛选", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            log("日期筛选返回结果", data.get("pagination", {}).get("total", 0) >= 0,
                f"total={data.get('pagination', {}).get('total', 0)}")

# ===== 2.5 分页 =====
def test_pagination(headers):
    section("2.5 分页导航")
    with httpx.Client(timeout=30, headers=headers) as c:
        # 第 1 页，每页 5 条
        r = c.get(f"{BASE}/tommy/archive-documents?page=1&page_size=5")
        log("分页 page=1 size=5", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            log("返回不超过 5 条", len(items) <= 5, f"count={len(items)}")
            pg = data.get("pagination", {})
            log("分页信息正确", pg.get("page") == 1 and pg.get("page_size") == 5,
                f"page={pg.get('page')} size={pg.get('page_size')} total={pg.get('total')}")

        # 每页 100 条
        r = c.get(f"{BASE}/tommy/archive-documents?page=1&page_size=100")
        log("分页 size=100", r.status_code == 200)

        # 测试 page=2
        r = c.get(f"{BASE}/tommy/archive-documents?page=2&page_size=5")
        log("分页 page=2", r.status_code == 200, f"status={r.status_code}")

# ===== 2.6 批量操作 =====
def test_batch_ops(headers, doc_ids):
    section("2.6 批量操作")
    with httpx.Client(timeout=60, headers=headers) as c:
        # 找出 needs_review 状态的文档
        review_ids = []
        for doc_id, filename, _ in doc_ids:
            r = c.get(f"{BASE}/tommy/archive-documents/{doc_id}")
            if r.status_code == 200 and r.json().get("status") == "needs_review":
                review_ids.append(doc_id)

        if len(review_ids) < 2:
            log("批量确认（前提不足）", False, f"只有 {len(review_ids)} 个 needs_review 文档")
        else:
            # 批量确认
            r = c.post(f"{BASE}/tommy/archive-documents/batch/confirm", json={"doc_ids": review_ids})
            log("批量确认", r.status_code == 200, f"status={r.status_code}")
            if r.status_code == 200:
                confirmed = r.json().get("confirmed", 0)
                log(f"确认了 {confirmed} 份", confirmed == len(review_ids))

            # 验证状态已变更
            all_confirmed = True
            for doc_id in review_ids:
                r = c.get(f"{BASE}/tommy/archive-documents/{doc_id}")
                if r.status_code != 200 or r.json().get("status") != "confirmed":
                    all_confirmed = False
                    break
            log("批量确认后状态为 confirmed", all_confirmed)

            # 批量归档
            r = c.post(f"{BASE}/tommy/archive-documents/batch/archive", json={"doc_ids": review_ids})
            log("批量归档", r.status_code == 200, f"status={r.status_code}")
            if r.status_code == 200:
                archived = r.json().get("archived", 0)
                log(f"归档了 {archived} 份", archived == len(review_ids))

# ===== 2.7 异常处理与重试 =====
def test_exception_retry(headers, doc_ids):
    section("2.7 异常处理与重试")
    with httpx.Client(timeout=60, headers=headers) as c:
        if not doc_ids:
            log("异常重试（无文档）", False, "没有可测试的文档")
            return

        # 选一个文档标记为异常
        target_id = doc_ids[0][0]
        r = c.post(f"{BASE}/tommy/archive-documents/{target_id}/flag-exception")
        log("标记文档为异常", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            log("状态变为 exception", r.json().get("status") == "exception",
                f"status={r.json().get('status')}")

        # 单文档重试
        r = c.post(f"{BASE}/tommy/archive-documents/{target_id}/retry")
        log("单文档重试", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            log("重试后状态非异常", r.json().get("status") != "exception",
                f"status={r.json().get('status')}")

        # 批量重试（再次标记异常后批量重试）
        r = c.post(f"{BASE}/tommy/archive-documents/{target_id}/flag-exception")
        if r.status_code == 200:
            r = c.post(f"{BASE}/tommy/archive-documents/batch/retry", json={"doc_ids": [target_id]})
            log("批量重试", r.status_code == 200, f"status={r.status_code}")
            if r.status_code == 200:
                retried = r.json().get("retried", 0)
                log(f"重试了 {retried} 份", retried == 1)

# ===== 2.8 撤销操作 =====
def test_undo(headers, doc_ids):
    section("2.8 撤销操作")
    with httpx.Client(timeout=30, headers=headers) as c:
        # 找一个 archived 的文档
        archived_id = None
        for doc_id, filename, _ in doc_ids:
            r = c.get(f"{BASE}/tommy/archive-documents/{doc_id}")
            if r.status_code == 200 and r.json().get("status") == "archived":
                archived_id = doc_id
                break
        if not archived_id:
            # 选一个 needs_review 文档，先确认再归档
            for doc_id, filename, _ in doc_ids:
                r = c.get(f"{BASE}/tommy/archive-documents/{doc_id}")
                if r.status_code == 200 and r.json().get("status") in ("needs_review", "confirmed"):
                    # 如果是 needs_review 先确认
                    if r.json().get("status") == "needs_review":
                        c.post(f"{BASE}/tommy/archive-documents/{doc_id}/confirm")
                    # 再归档
                    c.post(f"{BASE}/tommy/archive-documents/{doc_id}/archive")
                    archived_id = doc_id
                    break

        if not archived_id:
            log("撤销归档（前提不足）", False, "没有 archived 文档")
            return

        # 撤销归档 -> confirmed
        r = c.post(f"{BASE}/tommy/archive-documents/{archived_id}/undo-archive")
        log("撤销归档（archived→confirmed）", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            log("撤销后状态为 confirmed", r.json().get("status") == "confirmed",
                f"status={r.json().get('status')}")

        # 撤销确认 -> needs_review
        r = c.post(f"{BASE}/tommy/archive-documents/{archived_id}/undo-archive")
        log("撤销确认（confirmed→needs_review）", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            log("撤销后状态为 needs_review", r.json().get("status") == "needs_review",
                f"status={r.json().get('status')}")

        # 再次撤销应失败（needs_review 无法撤销）
        r = c.post(f"{BASE}/tommy/archive-documents/{archived_id}/undo-archive")
        log("needs_review 状态撤销被拒绝", r.status_code in (400, 422), f"status={r.status_code}")

# ===== 2.9-2.11 租务管理 =====
def test_rental(headers):
    section("2.9-2.11 租务管理")
    with httpx.Client(timeout=30, headers=headers) as c:
        # 单位列表
        r = c.get(f"{BASE}/tommy/rental-units")
        log("获取单位列表", r.status_code == 200, f"status={r.status_code}")
        units = []
        if r.status_code == 200:
            data = r.json()
            units = data.get("data", []) if isinstance(data, dict) else data
            residential = [u for u in units if u.get("unit_type") == "住宅"]
            parking = [u for u in units if u.get("unit_type") == "車位"]
            log("住宅单位数量", len(residential) >= 1, f"count={len(residential)}")
            log("车位数量", len(parking) >= 1, f"count={len(parking)}")

        # 逾期缴费列表
        r = c.get(f"{BASE}/tommy/rental-units/payments/overdue")
        log("获取逾期缴费列表", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            log("逾期列表返回 data 字段", "data" in data, f"total={data.get('total', 0)}")

        # 即将到期租约
        r = c.get(f"{BASE}/tommy/rental-units/expiring")
        log("获取即将到期租约", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            log("到期列表返回 data 字段", "data" in data, f"total={data.get('total', 0)}")

        # 租务统计
        r = c.get(f"{BASE}/tommy/rental-units/stats")
        log("获取租务统计", r.status_code == 200, f"status={r.status_code}")

        # 选一个有租户的单位测试
        target_unit = None
        for u in units:
            if u.get("tenant_name") and u.get("lease_start") and u.get("monthly_rent"):
                target_unit = u
                break

        if not target_unit:
            log("租务操作（无可用单位）", False, "没有有租户的单位")
            return

        unit_id = target_unit.get("id")
        # 单位详情
        r = c.get(f"{BASE}/tommy/rental-units/{unit_id}")
        log("获取单位详情", r.status_code == 200, f"status={r.status_code}")

        # 缴费记录列表
        r = c.get(f"{BASE}/tommy/rental-units/{unit_id}/payments")
        log("获取缴费记录", r.status_code == 200, f"status={r.status_code}")

        # 租约记录列表
        r = c.get(f"{BASE}/tommy/rental-units/{unit_id}/leases")
        log("获取租约记录", r.status_code == 200, f"status={r.status_code}")

        # 记录缴费
        r = c.post(f"{BASE}/tommy/rental-units/{unit_id}/payments", json={
            "amount": 1000, "due_date": "2026-08-31"
        })
        log("记录缴费", r.status_code in (200, 201), f"status={r.status_code}")
        payment_id = None
        if r.status_code in (200, 201):
            payment_id = r.json().get("id")

        # 标记已缴（使用 PATCH 接口）
        if payment_id:
            r = c.patch(f"{BASE}/tommy/rental-units/{unit_id}/payments/{payment_id}", json={
                "paid_amount": 1000, "paid_date": "2026-07-28", "status": "paid"
            })
            log("标记已缴", r.status_code == 200, f"status={r.status_code}")
            if r.status_code == 200:
                log("缴费状态为 paid", r.json().get("status") == "paid",
                    f"status={r.json().get('status')}")

                # 撤销缴费
                r = c.patch(f"{BASE}/tommy/rental-units/{unit_id}/payments/{payment_id}", json={
                    "status": "pending", "paid_date": None, "paid_amount": None
                })
                log("撤销缴费", r.status_code == 200, f"status={r.status_code}")

        # 发送缴费提醒（即使没有 SMTP 也应记录审计日志）
        r = c.post(f"{BASE}/tommy/rental-units/{unit_id}/send-reminder")
        log("发送缴费提醒", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            log("提醒接口返回 detail", bool(r.json().get("detail")),
                r.json().get("detail", "")[:80])

        # 2.12 生成租约文件
        r = c.post(f"{BASE}/tommy/rental-units/{unit_id}/generate-lease")
        log("生成租约文件", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            content_disp = r.headers.get("content-disposition", "")
            log("租约文件为 docx", "document" in content_type or "octet" in content_type,
                f"content-type={content_type}")
            log("Content-Disposition 存在", "attachment" in content_disp,
                f"disposition={content_disp[:80]}")
            log("租约文件内容非空", len(r.content) > 0, f"size={len(r.content)}")

        # 新增租约（续租）
        r = c.post(f"{BASE}/tommy/rental-units/{unit_id}/leases", json={
            "tenant_name": "測試續租租戶",
            "lease_start": "2027-07-01",
            "lease_end": "2029-06-30",
            "monthly_rent": 20000
        })
        log("新增租约（续租）", r.status_code in (200, 201), f"status={r.status_code}")
        if r.status_code in (200, 201):
            log("新租约状态为 active", r.json().get("status") == "active",
                f"status={r.json().get('status')}")
            new_lease_id = r.json().get("id")

            # 验证旧租约已标记为 expired
            r = c.get(f"{BASE}/tommy/rental-units/{unit_id}/leases")
            if r.status_code == 200:
                leases = r.json().get("data", [])
                expired_leases = [l for l in leases if l.get("status") == "expired"]
                log("旧租约已标记 expired", len(expired_leases) > 0,
                    f"expired_count={len(expired_leases)}")

# ===== 2.13 仪表板统计 =====
def test_dashboard(headers):
    section("2.13 仪表板统计")
    with httpx.Client(timeout=30, headers=headers) as c:
        r = c.get(f"{BASE}/tommy/archive-documents/stats")
        log("获取归档统计", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            stats = r.json()
            required_fields = ["total", "pending_review", "confirmed", "archived", "exception", "today_upload"]
            for field in required_fields:
                log(f"统计字段 {field}", field in stats, f"value={stats.get(field)}")
            log("分类分布字段存在", "category_breakdown" in stats)
            log("月度趋势字段存在", "monthly_trend" in stats)
            print(f"    统计: {json.dumps(stats, ensure_ascii=False)[:200]}")

# ===== 2.15 审计日志 =====
def test_audit_log(headers, doc_ids):
    section("2.15 审计日志")
    with httpx.Client(timeout=30, headers=headers) as c:
        # 查询所有审计日志
        r = c.get(f"{BASE}/audit/logs?page=1&page_size=10")
        log("查询审计日志列表", r.status_code == 200, f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            logs = data.get("data", [])
            log("审计日志非空", len(logs) > 0, f"count={len(logs)}")
            if logs:
                first = logs[0]
                log("审计日志有时间字段", "created_at" in first)
                log("审计日志有操作人字段", "user_name" in first)
                log("审计日志有操作内容字段", "detail" in first or "action" in first)
                print(f"    最新审计: {json.dumps(first, ensure_ascii=False)[:150]}")

        # 按模块筛选
        r = c.get(f"{BASE}/audit/logs?module=tommy")
        log("按模块筛选审计日志", r.status_code == 200, f"status={r.status_code}")

        # 按资源ID筛选
        if doc_ids:
            doc_id = doc_ids[0][0]
            r = c.get(f"{BASE}/audit/logs?resource_id={doc_id}")
            log("按资源ID查询审计日志", r.status_code == 200, f"status={r.status_code}")
            if r.status_code == 200:
                data = r.json()
                logs = data.get("data", [])
                log("资源审计日志非空", len(logs) > 0, f"count={len(logs)}")

# ===== 主流程 =====
def main():
    print("\n" + "="*60)
    print("  培英 AI 行政平台 - API 功能测试")
    print("="*60)

    token = test_login()
    if not token:
        print("\n登录失败，无法继续测试")
        print_summary()
        return

    doc_ids, file_ids, headers = test_upload_and_classify(token)
    test_file_preview(headers, file_ids)
    test_search_and_filter(headers, doc_ids)
    test_pagination(headers)
    test_batch_ops(headers, doc_ids)
    test_exception_retry(headers, doc_ids)
    test_undo(headers, doc_ids)
    test_rental(headers)
    test_dashboard(headers)
    test_audit_log(headers, doc_ids)

    print_summary()

def print_summary():
    section("测试结果汇总")
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)
    print(f"\n  总计: {total}  通过: {passed}  失败: {failed}")
    if failed:
        print(f"\n  失败项:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    ✗ {r['test']} — {r['detail']}")
    print()

if __name__ == "__main__":
    main()
