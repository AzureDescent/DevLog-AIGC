# plugins/sensitive_filter.py
from hooks.base import BasePlugin
from context import RunContext


class SensitiveWordFilterPlugin(BasePlugin):
    """
    示例插件：敏感词过滤
    """

    name = "SensitiveWordFilter"

    # 定义要过滤的词汇
    SENSITIVE_WORDS = ["绝对机密", "内部IP", "password"]

    def on_ai_summary_generated(self, context: RunContext, summary: str) -> str:
        if not summary:
            return summary

        filtered_summary = summary
        count = 0
        for word in self.SENSITIVE_WORDS:
            if word in filtered_summary:
                filtered_summary = filtered_summary.replace(word, "***")
                count += 1

        if count > 0:
            print(f"🛡️ [SensitiveWordFilter] 已过滤 {count} 个敏感词。")

        return filtered_summary

    def on_html_generated(self, context: RunContext, html_content: str) -> str:
        # 示例：在 HTML 底部注入一个自定义的 footer
        custom_footer = "<p style='text-align: center; color: #999; font-size: 10px;'>Powered by Plugin System</p>"
        return html_content.replace("</body>", f"{custom_footer}</body>")
