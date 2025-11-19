# hooks/base.py
from abc import ABC
from typing import List, Dict, Any, Optional
from context import RunContext


class BasePlugin(ABC):
    """
    [V4.6] 插件基类
    定义所有生命周期钩子。用户自定义插件应继承此类。
    """

    # 插件名称 (建议子类覆盖)
    name: str = "BasePlugin"

    def on_start(self, context: RunContext):
        """
        [钩子] 流程开始时调用。
        可用于初始化资源或打印日志。
        """
        pass

    def on_data_fetched(self, context: RunContext, commits: List, stats: Dict):
        """
        [钩子] 数据源获取 Git 数据后调用。
        可用于检查数据完整性或统计自定义指标。
        """
        pass

    def on_ai_summary_generated(self, context: RunContext, summary: str) -> str:
        """
        [Filter 钩子] AI 摘要生成后调用。
        **必须返回字符串**。可用于敏感词过滤、追加内容或格式调整。

        :param summary: 原始 AI 摘要
        :return: 修改后的摘要 (若不修改请直接返回 summary)
        """
        return summary

    def on_html_generated(self, context: RunContext, html_content: str) -> str:
        """
        [Filter 钩子] HTML 生成后，保存前调用。
        可用于注入自定义 script 标签或 footer。
        """
        return html_content

    def on_finish(self, context: RunContext):
        """
        [钩子] 流程结束时调用（无论成功与否，只要未崩溃）。
        可用于清理资源。
        """
        pass
