# llm/provider_abc.py
"""
[V3.4] 所有 LLM 供应商的抽象基类 (ABC)。
该模块定义了策略模式的 "Strategy" 接口
任何新的 LLM 供应商都必须继承自 LLMProvider 并实现 generate_summary 方法。
"""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    LLM 供应商的抽象接口
    """

    @abstractmethod
    def generate_summary(
        self, system_prompt: str, user_prompt: str, model_name: str | None = None
    ) -> str:
        """
        根据系统提示和用户提示生成摘要。

        参数:
            system_prompt: AI 的指令或上下文 (V3.4 暂定传入空值，由 user_prompt 完整承载 V3.3 模板).
            user_prompt: 用户的输入 (在 V3.4 中，我们将传入 V3.3 完整的、已格式化的提示).
            model_name: (可选) 要使用的具体模型 (例如 "gemini-1.5-pro").
                          如果为 None，将使用供应商的默认模型.
        返回:
            包含生成摘要的字符串。

        抛出:
            Exception: 如果 API 调用失败。
        """
        pass
