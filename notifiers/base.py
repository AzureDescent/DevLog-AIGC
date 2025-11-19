# notifiers/base.py
from abc import ABC, abstractmethod
from typing import Optional
from context import RunContext
import logging

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """
    [V4.3] 通知渠道抽象基类
    所有具体的通知方式（Email, Feishu, Slack...）都必须继承此类。
    """

    def __init__(self, context: RunContext):
        """
        初始化通知器，接收运行时上下文。
        """
        self.context = context
        self.global_config = context.global_config

    @property
    @abstractmethod
    def name(self) -> str:
        """返回通知渠道的名称 (日志显示用)"""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """
        判断此通知器是否应该激活。
        例如：EmailNotifier 检查 context.email_list 是否为空；
              FeishuNotifier 检查 config.FEISHU_WEBHOOK 是否存在。
        """
        pass

    @abstractmethod
    def send(
        self, subject: str, content: str, attachment_path: Optional[str] = None
    ) -> bool:
        """
        执行发送逻辑。
        :param subject: 消息标题
        :param content: 消息正文 (通常是 HTML 或 Markdown)
        :param attachment_path: (可选) 附件文件的绝对路径
        :return: 是否发送成功
        """
        pass
