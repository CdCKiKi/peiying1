"""
AI 文档分类服务
根据OCR识别的文本内容进行智能分类
支持多种分类策略：LLM API、关键词匹配、外部API调用
"""
import json
import re
import os
from datetime import date
from typing import Tuple, Optional, Dict, Any
from decimal import Decimal

import httpx

from app.core.config import settings


# 加载 prompt 模板
def _load_prompt_template() -> str:
    """加载文档分类 prompt 模板"""
    prompt_paths = [
        os.path.join(os.path.dirname(__file__), "..", "modules", "tommy", "prompts", "document_classify_zh_hk.md"),
        os.path.join(os.path.dirname(__file__), "..", "..", "modules", "tommy", "prompts", "document_classify_zh_hk.md"),
    ]
    for p in prompt_paths:
        abs_path = os.path.abspath(p)
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                return f.read()
    return ""


class AiClassifier:
    """智能文档分类器"""

    CATEGORIES = ["租務", "財務", "人事", "教育局通告", "會議", "其他"]

    KEYWORDS = {
        "租務": [
            "租金", "租約", "租戶", "單位", "樓", "室", "座",
            "繳費通知", "月租", "押金", "租金通知", "租賃", "合約"
        ],
        "財務": [
            "發票", "收據", "銀行", "付款", "繳費", "金額",
            "費用", "帳單", "支付", "轉帳", "支票", "報銷", "預算"
        ],
        "人事": [
            "員工", "招聘", "合同", "離職", "薪金", "假期",
            "考勤", "福利", "保險", "面試", "入职", "員工手冊"
        ],
        "教育局通告": [
            "教育局", "通告", "學校", "課程", "學費",
            "考試", "學生", "教師", "校長", "學期", "教育"
        ],
        "會議": [
            "會議", "議程", "記錄", "決議", "討論",
            "報告", "出席", "主持", "會議室", "備忘錄"
        ],
    }

    def __init__(self):
        self.backend = settings.CLASSIFICATION_BACKEND or "keyword"

    async def classify(self, ocr_text: str, filename: str = "") -> Tuple[str, str, str, Decimal, Optional[str], str]:
        """
        对文档进行分类

        返回：(category, suggested_name, summary, amount, due_date, confidence)
        """
        if self.backend == "api" and settings.CLASSIFICATION_API_URL:
            return await self._classify_via_api(ocr_text, filename)
        elif self.backend == "llm" and settings.LLM_API_KEY:
            return await self._classify_via_llm(ocr_text, filename)
        else:
            return self._classify_via_keywords(ocr_text, filename)

    # ===== LLM API 分类 =====

    async def _classify_via_llm(self, ocr_text: str, filename: str = "") -> Tuple[str, str, str, Decimal, Optional[str], str]:
        """通过 LLM API 进行智能分类"""
        prompt_template = _load_prompt_template()

        # 构建用户消息
        user_message = f"文件名：{filename}\n\nOCR 文本：\n{ocr_text}"

        system_prompt = prompt_template if prompt_template else (
            "你是香港中學校務處文件歸檔助手。請根據 OCR 文本判斷文件類別（財務/人事/租務/教育局通告/會議/其他），"
            "並提取金額、日期、摘要等結構化欄位。輸出必須是合法 JSON。"
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{settings.LLM_API_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        "max_tokens": settings.LLM_MAX_TOKENS,
                        "temperature": settings.LLM_TEMPERATURE,
                    },
                )

                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                    # 尝试从响应中提取 JSON
                    result = self._parse_llm_json(content)
                    if result:
                        return (
                            result.get("category", "其他"),
                            result.get("suggested_name", f"{date.today().isoformat()}_其他_{filename}"),
                            result.get("summary", ""),
                            Decimal(str(result.get("amount", 0))) if result.get("amount") else Decimal("0"),
                            result.get("due_date"),
                            result.get("confidence", "medium"),
                        )
                    else:
                        # JSON 解析失败，回退到关键词
                        return self._classify_via_keywords(ocr_text, filename)
                else:
                    # API 调用失败，回退到关键词
                    return self._classify_via_keywords(ocr_text, filename)

        except Exception:
            # 网络等异常，回退到关键词
            return self._classify_via_keywords(ocr_text, filename)

    def _parse_llm_json(self, content: str) -> Optional[Dict[str, Any]]:
        """从 LLM 返回内容中提取 JSON"""
        if not content:
            return None

        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试查找第一个 { 到最后一个 }
        first_brace = content.find("{")
        last_brace = content.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(content[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass

        return None

    # ===== 外部 API 分类 =====

    async def _classify_via_api(self, ocr_text: str, filename: str = "") -> Tuple[str, str, str, Decimal, Optional[str], str]:
        """通过外部API进行分类"""
        payload = {
            "ocr_text": ocr_text,
            "filename": filename,
            "categories": self.CATEGORIES,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    settings.CLASSIFICATION_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    result = resp.json()
                    return (
                        result.get("category", "其他"),
                        result.get("suggested_name", f"{date.today().isoformat()}_其他_{filename}"),
                        result.get("summary", ""),
                        Decimal(str(result.get("amount", 0))),
                        result.get("due_date"),
                        result.get("confidence", "medium"),
                    )
                else:
                    return self._classify_via_keywords(ocr_text, filename)
        except Exception:
            return self._classify_via_keywords(ocr_text, filename)

    # ===== 关键词分类（回退方案） =====

    def _classify_via_keywords(self, ocr_text: str, filename: str = "") -> Tuple[str, str, str, Decimal, Optional[str], str]:
        """基于关键词匹配的分类方法"""
        ocr_text_lower = ocr_text.lower()
        filename_lower = filename.lower()

        scores = {}
        for category, keywords in self.KEYWORDS.items():
            score = 0
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in ocr_text_lower:
                    score += 2
                if keyword_lower in filename_lower:
                    score += 1
            scores[category] = score

        max_score = max(scores.values())
        if max_score == 0:
            category = "其他"
        else:
            category = max(scores, key=scores.get)

        summary = self._extract_summary(ocr_text, category)
        amount = self._extract_amount(ocr_text)
        due_date = self._extract_due_date(ocr_text)
        suggested_name = self._generate_suggested_name(category, filename, due_date)

        confidence = self._calculate_confidence(max_score, ocr_text)

        return category, suggested_name, summary, amount, due_date, confidence

    # ===== 公共工具方法 =====

    def _extract_summary(self, ocr_text: str, category: str) -> str:
        """提取文档摘要"""
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        if not lines:
            return f"已分类为「{category}」"

        if category == "租務":
            unit_match = re.search(r'(?:單位|房|室|座|樓)\s*[:：]\s*([^\n]+)', ocr_text)
            amount_match = re.search(r'(?:租金|月租|金額)\s*[:：]\s*HK\$\s*([\d,]+)', ocr_text)
            parts = []
            if unit_match:
                parts.append(unit_match.group(1).strip())
            if amount_match:
                parts.append(f"租金 HK$ {amount_match.group(1)}")
            if parts:
                return f"{'，'.join(parts)}"

        if category == "財務":
            amount_match = re.search(r'(?:金額|費用|總計)\s*[:：]\s*HK\$\s*([\d,]+)', ocr_text)
            if amount_match:
                return f"財務文件，金額 HK$ {amount_match.group(1)}"

        if category == "人事":
            name_match = re.search(r'(?:員工|姓名)\s*[:：]\s*([^\n]+)', ocr_text)
            if name_match:
                return f"{category}文件，涉及員工 {name_match.group(1).strip()}"

        if category == "教育局通告":
            title_match = re.search(r'(?:通告|通知|標題)\s*[:：]\s*([^\n]+)', ocr_text)
            if title_match:
                return f"教育局通告：{title_match.group(1).strip()}"

        if category == "會議":
            title_match = re.search(r'(?:會議|議程)\s*[:：]\s*([^\n]+)', ocr_text)
            if title_match:
                return f"會議記錄：{title_match.group(1).strip()}"

        return f"已分类为「{category}」"

    def _extract_amount(self, ocr_text: str) -> Decimal:
        """从文本中提取金额"""
        patterns = [
            r'HK\$\s*([\d,]+(?:\.\d+)?)',
            r'(?:租金|金額|費用|應繳)\s*[:：]\s*([\d,]+(?:\.\d+)?)',
            # 兜底模式：要求至少含一个千位分隔符（逗号），
            # 避免误匹配年份/日期等无逗号的纯数字（如 2026、20260715）
            r'(\d{1,3}(?:,\d{3})+(?:\.\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, ocr_text)
            if match:
                try:
                    return Decimal(match.group(1).replace(',', ''))
                except Exception:
                    continue

        return Decimal("0")

    def _extract_due_date(self, ocr_text: str) -> Optional[str]:
        """从文本中提取到期日"""
        date_patterns = [
            r'(?:繳付限期|到期日|截止日期|截止)\s*[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
            r'(?:繳付限期|到期日|截止日期|截止)\s*[:：]\s*(\d{1,2}[-/月]\d{1,2}[-/年]\d{4})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, ocr_text)
            if match:
                date_str = match.group(1)
                date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                try:
                    if len(date_str) == 8 and date_str.isdigit():
                        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    return date_str
                except Exception:
                    continue

        return None

    def _generate_suggested_name(self, category: str, filename: str, due_date: Optional[str]) -> str:
        """生成建议文件名"""
        today = date.today().isoformat()

        if due_date:
            date_part = due_date[:10]
        else:
            date_part = today

        name_parts = [date_part, category]

        if filename:
            base_name = filename.rsplit('.', 1)[0]
            if len(base_name) > 30:
                base_name = base_name[:30]
            name_parts.append(base_name)

        return '_'.join(name_parts)

    def _calculate_confidence(self, score: int, ocr_text: str) -> str:
        """计算置信度"""
        if score >= 6:
            return "high"
        elif score >= 3:
            return "medium"
        elif score >= 1:
            return "low"
        else:
            return "low"


ai_classifier = AiClassifier()
