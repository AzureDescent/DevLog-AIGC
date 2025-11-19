# llm/mock_provider.py
"""
[测试样例] 一个模拟的 LLM 供应商
用于验证 V4.1 的动态注册机制 (Registry Pattern)。
"""
import logging
from typing import Optional
from llm.provider_abc import LLMProvider, register_provider
from config import GlobalConfig

logger = logging.getLogger(__name__)


# 核心测试点：使用装饰器注册 ID 为 "mock"
@register_provider("mock")
class MockProvider(LLMProvider):
    """
    模拟的 Provider，不进行任何实际 API 调用，仅返回固定字符串。
    """

    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config
        logger.info("✅ MockProvider 已初始化 (无需 API Key)")

    def summarize_diff(self, diff_content: str) -> Optional[str]:
        return f"[Mock] Diff 摘要: {diff_content[:20]}..."

    def summarize_report(
        self,
        text_report: str,
        diff_summaries: Optional[str] = None,
        previous_summary: Optional[str] = None,
    ) -> Optional[str]:
        return (
            "# [Mock] AI 日报摘要\n\n"
            "## 🧪 测试运行\n"
            "这是一个由 MockProvider 生成的测试摘要，证明动态注册机制工作正常。\n\n"
            "### 原始数据\n"
            f"- 报告长度: {len(text_report)} 字符\n"
            f"- Diff 摘要存在: {'是' if diff_summaries else '否'}"
        )

    def distill_memory(self, full_log: str) -> Optional[str]:
        return "# [Mock] 项目记忆\n\n这是一个测试记忆。"

    def generate_article(
        self,
        today_technical_summary: str,
        project_historical_memory: str,
        project_readme: Optional[str] = None,
        style: str = "default",
    ) -> Optional[str]:
        return (
            f"# [Mock] 风格文章 ({style})\n\n"
            "这是一篇测试文章。如果能在浏览器中看到这个，说明 V4.1 架构运行完美！"
        )
