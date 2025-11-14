# email_sender.py
import logging
import sys
import os  # (V3.7) 导入 os 以获取文件名
from datetime import datetime
from config import GitReportConfig

try:
    import yagmail
except ImportError:
    print("错误: yagmail 库未安装。请运行: pip install yagmail")
    sys.exit(1)

logger = logging.getLogger(__name__)


def send_email_report(
    config: GitReportConfig,
    recipient_email: str,
    ai_summary: str,
    attachment_path: str,  # (V3.7) 重命名此参数
) -> bool:
    """(V1.2) 使用 yagmail 发送邮件"""
    logger.info(f"📬 正在准备发送邮件至: {recipient_email} (使用 yagmail)")

    try:
        yag = yagmail.SMTP(
            user=config.SMTP_USER,
            password=config.SMTP_PASSWORD,
            host=config.SMTP_SERVER,
            port=config.SMTP_PORT,
        )

        subject = f"Git 工作日报 - {datetime.now().strftime('%Y-%m-%d')}"

        # (V3.7) 动态获取附件名，使邮件正文更准确
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
            to=recipient_email,
            subject=subject,
            contents=html_body,
            attachments=attachment_path,  # (V2.7) 使用重命名后的参数
        )
        logger.info(
            f"✅ 邮件已成功发送至 {recipient_email} (附件: {attachment_filename})"
        )
        return True

    except Exception as e:
        logger.error(f"❌ (yagmail) 发送邮件失败: {e}")
        return False
