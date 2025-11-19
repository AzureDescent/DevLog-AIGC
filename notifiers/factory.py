# notifiers/factory.py
from typing import List
import logging
from context import RunContext
from .base import BaseNotifier
from .email_notifier import EmailNotifier
from .feishu_notifier import FeishuNotifier

# --- 在这里注册新的通知渠道 ---
AVAILABLE_NOTIFIERS_CLASSES = [
    EmailNotifier,
    FeishuNotifier,
    # SlackNotifier,
]

logger = logging.getLogger(__name__)


def get_active_notifiers(context: RunContext) -> List[BaseNotifier]:
    """
    工厂方法：实例化并返回所有适用于当前上下文的 active notifiers。
    """
    active_list = []
    for notifier_cls in AVAILABLE_NOTIFIERS_CLASSES:
        try:
            notifier = notifier_cls(context)
            if notifier.is_enabled():
                active_list.append(notifier)
                logger.info(f"🔌 已激活通知渠道: {notifier.name}")
        except Exception as e:
            logger.error(f"⚠️ 初始化通知渠道 {notifier_cls.__name__} 失败: {e}")

    return active_list
