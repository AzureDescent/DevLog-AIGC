# notifiers/email_notifier.py
import logging
import os
from typing import Optional
from .base import BaseNotifier

try:
    import yagmail
except ImportError:
    yagmail = None

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """
    [V4.3] 邮件通知实现 (封装 yagmail)
    """

    @property
    def name(self) -> str:
        return "Email (SMTP)"

    def is_enabled(self) -> bool:
        # 只有当上下文中有收件人列表时，才启用邮件通知
        return bool(self.context.email_list)

    def send(
        self, subject: str, content: str, attachment_path: Optional[str] = None
    ) -> bool:
        if not yagmail:
            logger.error(
                "❌ 无法发送邮件：未安装 yagmail 库。请运行: pip install yagmail"
            )
            return False

        recipients = self.context.email_list
        recipient_str = ", ".join(recipients)
        logger.info(f"📬 [Email] 正在准备发送至: {recipient_str}")

        try:
            # 从 global_config 获取 SMTP 设置
            yag = yagmail.SMTP(
                user=self.global_config.SMTP_USER,
                password=self.global_config.SMTP_PASSWORD,
                host=self.global_config.SMTP_SERVER,
                port=self.global_config.SMTP_PORT,
            )

            # 简单的 HTML 包装 (如果 content 已经是完整 HTML，这层包装也是安全的)
            if "<html>" not in content:
                html_body = f"""
                <html>
                <body>
                    <p>你好,</p>
                    <p>以下是今日的 Git 工作汇报：</p>
                    <hr>
                    {content}
                    <hr>
                    <p>详细报告已作为附件添加。</p>
                </body>
                </html>
                """
            else:
                html_body = content

            # 如果有附件，获取文件名用于日志
            attachment_filename = (
                os.path.basename(attachment_path) if attachment_path else "无"
            )

            yag.send(
                to=recipients,
                subject=subject,
                contents=html_body,
                attachments=attachment_path,
            )
            logger.info(f"✅ [Email] 发送成功 (附件: {attachment_filename})")
            return True

        except Exception as e:
            logger.error(f"❌ [Email] 发送失败: {e}")
            return False
