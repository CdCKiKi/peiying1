"""
邮件发送服务
支持 SMTP 发送缴费提醒、租约到期通知等
"""
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)


class Emailer:
    """邮件发送客户端"""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM
        self.use_tls = settings.SMTP_USE_TLS

    @property
    def is_configured(self) -> bool:
        """检查邮件服务是否已配置"""
        return bool(self.host and self.user and self.password)

    async def send_rental_reminder(
        self,
        to_email: str,
        tenant_name: str,
        unit_number: str,
        amount: float,
        due_date: str,
    ) -> bool:
        """发送缴费提醒邮件"""
        subject = f"【培英中學】繳費提醒 - {unit_number}"
        body = f"""
親愛的 {tenant_name} 先生/女士：

您好！這是由培英中學校務處發出的繳費提醒。

單位：俊傑花園 {unit_number}
應繳金額：HK$ {amount:,.2f}
繳付限期：{due_date}

請於限期前完成繳費。如有任何疑問，請聯絡校務處 Tommy。

此致
培英中學校務處
        """.strip()

        return await self._send(to_email, subject, body)

    async def send_lease_expiry_reminder(
        self,
        to_email: str,
        tenant_name: str,
        unit_number: str,
        lease_end: str,
    ) -> bool:
        """发送租约到期提醒"""
        subject = f"【培英中學】租約到期提醒 - {unit_number}"
        body = f"""
親愛的 {tenant_name} 先生/女士：

您好！您租用的以下單位租約即將到期：

單位：俊傑花園 {unit_number}
租約到期日：{lease_end}

如需續租，請盡快與校務處 Tommy 聯絡辦理續租手續。

此致
培英中學校務處
        """.strip()

        return await self._send(to_email, subject, body)

    async def send_document(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[tuple]] = None,
    ) -> bool:
        """发送带附件的邮件

        attachments: [(filename, file_bytes, mime_type), ...]
        """
        return await self._send(to_email, subject, body, attachments)

    async def _send(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[tuple]] = None,
    ) -> bool:
        """底层 SMTP 发送（在线程池中运行以避免阻塞）"""
        if not self.is_configured:
            logger.warning("邮件服务未配置，跳過發送")
            return False

        try:
            await asyncio.to_thread(
                self._send_sync, to_email, subject, body, attachments
            )
            logger.info(f"郵件已發送至 {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"郵件發送失敗 ({to_email}): {str(e)}")
            return False

    def _send_sync(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[tuple]] = None,
    ) -> None:
        """同步 SMTP 发送"""
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if attachments:
            for filename, file_bytes, mime_type in attachments:
                part = MIMEBase(*mime_type.split("/", 1), Name=filename)
                part.set_payload(file_bytes)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"',
                )
                msg.attach(part)

        if self.use_tls:
            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=30)

        try:
            server.login(self.user, self.password)
            server.sendmail(self.from_addr, to_email, msg.as_string())
        finally:
            server.quit()


emailer = Emailer()
