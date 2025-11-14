# llm/provider_abc.py
"""
[V3.5] 所有 LLM 供应商的抽象基类 (ABC)。
- 接口已从 V3.4 的 'generate_summary' 更改为特定的业务方法。
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class LLMProvider(ABC):
    """
    (V3.5 接口) LLM 供应商的抽象接口。
    """

    @abstractmethod
    def summarize_diff(self, diff_content: str) -> Optional[str]:
        """(V3.5) 总结单个 diff"""
        pass

    @abstractmethod
    def summarize_report(
        self,
        text_report: str,
        diff_summaries: Optional[str] = None,
        previous_summary: Optional[str] = None,
    ) -> Optional[str]:
        """(V3.5) 总结完整的报告 (Reduce 阶段)"""
        pass

    @abstractmethod
    def distill_memory(self, full_log: str) -> Optional[str]:
        """(V3.5) 蒸馏项目记忆"""
        pass

    @abstractmethod
    def generate_article(
        self,
        today_technical_summary: str,
        project_historical_memory: str,
        project_readme: Optional[str] = None,
    ) -> Optional[str]:
        """(V3.5) 生成公众号文章"""
        pass
