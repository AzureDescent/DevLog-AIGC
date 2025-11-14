# llm/gemini_provider.py
"""
[V3.4] LLMProvider 针对 Google Gemini 的具体实现 。
"""
import logging
from typing import Optional
import google.generativeai as genai
from llm.provider_abc import LLMProvider
from config import GitReportConfig  # 假设 config.py 中有 GitReportConfig

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    用于与 Google Gemini API 交互的具体策略类
    """

    def __init__(self, config: GitReportConfig):
        """
        初始化 Gemini 客户端。

        抛出:
            ValueError: 如果 config 中未设置 GEMINI_API_KEY。
        """
        self.config = config
        if not self.config.GEMINI_API_KEY:
            logger.error("❌ (V3.4) GEMINI_API_KEY 未设置。请检查您的 .env 文件。")
            raise ValueError("GEMINI_API_KEY 未设置。请检查您的.env 文件。")

        try:
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            self.default_model = self.config.DEFAULT_MODEL_GEMINI

            # (V3.4.1 修复) 预热模型实例
            self.model_instance = genai.GenerativeModel(self.default_model)

            # (V3.4.1 修复) 存储预热模型的名称，以备比较
            self.default_model_name_cached = self.model_instance.model_name

            logger.info(
                f"✅ (V3.4) GeminiProvider 初始化成功 (默认模型: {self.default_model})"
            )
        except Exception as e:
            logger.error(f"❌ (V3.4) Gemini GenAI 配置失败: {e}")
            raise ValueError(f"Gemini GenAI 配置失败: {e}")

    def generate_summary(
        self, system_prompt: str, user_prompt: str, model_name: str | None = None
    ) -> str:
        """
        使用 Gemini API 生成摘要。
        Gemini 的基础 API 会合并系统和用户提示
        """
        try:
            # V3.4 简化：我们假定 V3.3 的完整提示在 user_prompt 中。
            # V3.5 将改进此处的提示词差异化 。
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            # (V3.4) 选择模型：使用指定的 model_name 或默认模型
            model_to_use = model_name or self.default_model

            if model_to_use == self.default_model:
                model_instance = self.model_instance  # 使用预热的实例
            else:
                # 仅当 V3.5 传入 --model 且不是默认值时
                logger.warning(f"(V3.4) 切换 Gemini 模型至: {model_to_use}")
                model_instance = genai.GenerativeModel(model_to_use)

            response = model_instance.generate_content(
                full_prompt
            )  # <--- 卡住的真正位置
            return response.text

        except Exception as e:
            logger.error(f"❌ [GeminiProvider 错误] 生成内容失败: {e}")
            raise
