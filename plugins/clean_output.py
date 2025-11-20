# plugins/clean_output.py
import re
from hooks.base import BasePlugin
from context import RunContext


class CleanOutputPlugin(BasePlugin):
    """
    [插件] 输出清洗器
    去除 LLM 可能输出的 markdown 代码块包裹标记 (```markdown ... ```)
    """

    name = "CleanMarkdownOutput"

    def on_ai_summary_generated(self, context: RunContext, summary: str) -> str:
        if not summary:
            return summary

        cleaned = summary.strip()

        # 1. 去除开头的 ```markdown 或 ```
        # 使用正则匹配：行首的 ``` 后跟可选的 markdown，然后是换行
        pattern_start = r"^```(markdown)?\s*\n"
        if re.match(pattern_start, cleaned, re.IGNORECASE):
            cleaned = re.sub(pattern_start, "", cleaned)

        # 2. 去除结尾的 ```
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        # 3. 再次去除可能残留的首尾空白
        cleaned = cleaned.strip()

        if cleaned != summary:
            print(f"🧹 [CleanOutput] 已去除 AI 回复中的 Markdown 代码块包裹。")

        return cleaned
