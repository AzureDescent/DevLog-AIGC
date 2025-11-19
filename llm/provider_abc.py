# llm/provider_abc.py
"""
[V3.5] 所有 LLM 供应商的抽象基类 (ABC)。
[V4.1] 新增 Registry Pattern 支持，允许动态注册供应商。
"""
from abc import ABC, abstractmethod
from typing import Optional, Type, Dict

# --- [V4.1] 注册表机制 START ---
# 全局注册表，存储 "provider_id" -> Provider Class 的映射
PROVIDER_REGISTRY: Dict[str, Type["LLMProvider"]] = {}


def register_provider(provider_id: str):
    """
    类装饰器：用于将具体的 Provider 实现类注册到全局注册表中。

    使用示例:
        @register_provider("gemini")
        class GeminiProvider(LLMProvider):
            ...
    """

    def decorator(cls):
        if provider_id in PROVIDER_REGISTRY:
            raise ValueError(
                f"Provider id '{provider_id}' 已经被注册过 ({PROVIDER_REGISTRY[provider_id].__name__})"
            )
        PROVIDER_REGISTRY[provider_id] = cls
        return cls

    return decorator


# --- [V4.1] 注册表机制 END ---


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
        style: str = "default",  # (V3.6) 新增 style 参数
    ) -> Optional[str]:
        """(V3.6) 生成公众号文章 (支持多风格)"""
        pass
