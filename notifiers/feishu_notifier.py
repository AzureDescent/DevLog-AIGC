# notifiers/feishu_notifier.py
import logging
import os
import time
import requests
from typing import Optional, Dict, Any
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class FeishuNotifier(BaseNotifier):
    """
    [V4.4] 飞书通知实现
    - 模式 A (高级): 使用 App ID/Secret 上传文件并点对点发送 (需企业自建应用权限)。
    - 模式 B (基础): 使用 Webhook 发送文本摘要 (无需特殊权限)。
    """

    @property
    def name(self) -> str:
        return "Feishu (Lark)"

    def is_enabled(self) -> bool:
        # 只要配置了 App ID 或 Webhook 任意一种，即视为启用
        has_app = bool(
            self.global_config.FEISHU_APP_ID and self.global_config.FEISHU_APP_SECRET
        )
        has_webhook = bool(self.global_config.FEISHU_WEBHOOK)
        return has_app or has_webhook

    def send(
        self, subject: str, content: str, attachment_path: Optional[str] = None
    ) -> bool:
        """
        执行发送逻辑。优先尝试 App 模式发送文件，失败或未配置则回退到 Webhook。
        """
        use_app_mode = bool(
            self.global_config.FEISHU_APP_ID and self.global_config.FEISHU_APP_SECRET
        )

        if use_app_mode:
            return self._send_via_app(subject, content, attachment_path)
        else:
            return self._send_via_webhook(subject, content)

    # --- 模式 A: 自建应用 (App ID + Secret) ---

    def _send_via_app(
        self, subject: str, content: str, attachment_path: Optional[str]
    ) -> bool:
        """
        完整流程：获取 Token -> (上传文件) -> 遍历邮箱 -> 发送消息
        """
        try:
            # 1. 获取 Tenant Access Token
            token = self._get_tenant_access_token()
            if not token:
                return False

            # 2. 上传文件 (如果有)
            file_key = None
            if attachment_path and os.path.exists(attachment_path):
                logger.info(
                    f"📤 [Feishu] 正在上传附件: {os.path.basename(attachment_path)}"
                )
                file_key = self._upload_file(token, attachment_path)
                if not file_key:
                    logger.warning("⚠️ [Feishu] 文件上传失败，将仅发送文本消息。")

            # 3. 遍历收件人 (通过邮箱匹配)
            success_count = 0
            recipients = self.context.email_list

            if not recipients:
                logger.warning("⚠️ [Feishu] 未配置接收邮箱 (email_list)，无法定向发送。")
                return False

            for email in recipients:
                # 发送文本/Markdown 摘要
                msg_sent = self._send_app_message(
                    token, email, "text", f"{subject}\n\n{content}"
                )

                # 发送文件 (如果有)
                file_sent = True
                if file_key:
                    # 飞书仅 PDF 支持以 "file" 类型发送预览，其他通常也是 "file"
                    # 注意: 这里的 file_key 是通过 im/v1/files 接口获取的
                    file_sent = self._send_app_message(token, email, "file", file_key)

                if msg_sent:
                    success_count += 1

            logger.info(
                f"✅ [Feishu] 已向 {success_count}/{len(recipients)} 个用户发送消息。"
            )
            return success_count > 0

        except Exception as e:
            logger.error(f"❌ [Feishu] App 模式发送异常: {e}", exc_info=True)
            return False

    def _get_tenant_access_token(self) -> Optional[str]:
        """获取飞书自建应用鉴权 Token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.global_config.FEISHU_APP_ID,
            "app_secret": self.global_config.FEISHU_APP_SECRET,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("tenant_access_token")
            else:
                logger.error(f"❌ [Feishu] 获取 Token 失败: {data.get('msg')}")
                return None
        except Exception as e:
            logger.error(f"❌ [Feishu] 获取 Token 网络错误: {e}")
            return None

    def _upload_file(self, token: str, file_path: str) -> Optional[str]:
        """
        上传文件到飞书，获取 file_key。
        API: POST /open-apis/im/v1/files
        """
        url = "https://open.feishu.cn/open-apis/im/v1/files"
        headers = {"Authorization": f"Bearer {token}"}

        file_name = os.path.basename(file_path)
        file_type = "pdf" if file_name.lower().endswith(".pdf") else "stream"

        try:
            with open(file_path, "rb") as f:
                # 使用 multipart/form-data 上传
                files = {
                    "file_name": (None, file_name),
                    "file_type": (None, file_type),
                    "file": (file_name, f),
                }
                resp = requests.post(url, headers=headers, files=files, timeout=60)
                data = resp.json()

                if data.get("code") == 0:
                    return data["data"]["file_key"]
                else:
                    logger.error(f"❌ [Feishu] 文件上传 API 错误: {data}")
                    return None
        except Exception as e:
            logger.error(f"❌ [Feishu] 文件上传 IO 错误: {e}")
            return None

    def _send_app_message(
        self, token: str, email: str, msg_type: str, content_or_key: str
    ) -> bool:
        """
        通过邮箱发送消息 (利用 receive_id_type=email)
        """
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": "email"}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # 构造消息体
        content_obj = {}
        if msg_type == "text":
            content_obj = {"text": content_or_key}
        elif msg_type == "file":
            content_obj = {"file_key": content_or_key}

        payload = {
            "receive_id": email,
            "msg_type": msg_type,
            "content": json.dumps(content_obj),  # 飞书要求 content 是 JSON 字符串
        }

        try:
            resp = requests.post(
                url, params=params, headers=headers, json=payload, timeout=10
            )
            data = resp.json()
            if data.get("code") == 0:
                return True
            else:
                logger.error(f"❌ [Feishu] 发送消息失败 ({email}): {data.get('msg')}")
                return False
        except Exception as e:
            logger.error(f"❌ [Feishu] 发送消息请求错误: {e}")
            return False

    # --- 模式 B: 群 Webhook (降级) ---

    def _send_via_webhook(self, subject: str, content: str) -> bool:
        """简单发送文本到群 Webhook"""
        url = self.global_config.FEISHU_WEBHOOK
        if not url:
            return False

        logger.info("ℹ️ [Feishu] 使用 Webhook 模式发送 (仅文本)...")

        # 简单构造富文本或普通文本
        payload = {
            "msg_type": "text",
            "content": {
                "text": f"【{subject}】\n\n{content}\n\n(注: 详细附件请查看邮件或联系管理员)"
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                logger.info("✅ [Feishu] Webhook 推送成功。")
                return True
            else:
                logger.error(f"❌ [Feishu] Webhook 错误: {data}")
                return False
        except Exception as e:
            logger.error(f"❌ [Feishu] Webhook 网络错误: {e}")
            return False


# 为了在 _send_app_message 中使用 json.dumps
import json
