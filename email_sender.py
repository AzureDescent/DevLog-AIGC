# email_sender.py
import logging
import sys
import os
from datetime import datetime
from typing import List  # [V3.9] 导入 List

# (V4.0) 导入 RunContext
from context import RunContext

try:
    import yagmail
except ImportError:
    print("错误: yagmail 库未安装。请运行: pip install yagmail")
    sys.exit(1)

logger = logging.getLogger(__name__)


def send_email_report(
    context: RunContext,  # (V4.0) 接收 RunContext
    recipient_emails: List[str],  # [V3.9] 签名从 str 变为 List[str]
    ai_summary: str,
    attachment_path: str,
) -> bool:
    """(V4.0) 使用 yagmail 发送邮件 (支持多收件人)"""

    # [V3.9] 更新日志以显示所有收件人
    recipient_str = ", ".join(recipient_emails)
    logger.info(f"📬 正在准备发送邮件至: {recipient_str} (使用 yagmail)")

    try:
        # (V4.0) 从 context.global_config 获取 SMTP 设置
        yag = yagmail.SMTP(
            user=context.global_config.SMTP_USER,
            password=context.global_config.SMTP_PASSWORD,
            host=context.global_config.SMTP_SERVER,
            port=context.global_config.SMTP_PORT,
        )

        subject = f"Git 工作日报 - {datetime.now().strftime('%Y-%m-%d')}"
        attachment_filename = os.path.basename(attachment_path)

        html_body = f"""
        <html>
        <body>
            <p>你好,</p>
            <p>以下是今日的 Git 工作 AI 摘要：</p>
            <hr>
            <pre style="font-family: monospace; white-space: pre-wrap; padding: 10px; background: #f4f4f4; border-radius: 5px;">{ai_summary}</pre>
            <hr>
            <p>详细的可视化报告 ({attachment_filename}) 已作为附件添加，请查收。</p>
        </body>
        </html>
        """

        yag.send(
            to=recipient_emails,  # [V3.9] yagmail 原生支持列表
            subject=subject,
            contents=html_body,
            attachments=attachment_path,
        )
        logger.info(
            f"✅ 邮件已成功发送至 {recipient_str} (附件: {attachment_filename})"
        )
        return True

    except Exception as e:
        logger.error(f"❌ (yagmail) 发送邮件失败: {e}")
        return False
