# llm/gemini_provider.py
"""
[V3.4 修正 3.0] LLMProvider 针对 Google Gemini 的具体实现。
- 修正 import 语句 (使用 'from google import genai' 匹配 test.py)
"""
import logging
from typing import Optional

# --- (V3.4 修正 3.0) 核心修改 ---
# 匹配 test.py 的工作方式
try:
    from google import genai
except ImportError:
    logger.error("❌ 'google.genai' 导入失败。")
    logger.error("   请确保 'google-generativeai' 库已正确安装。")
    raise
# ---------------------------------

from google.genai.errors import APIError
from llm.provider_abc import LLMProvider
from config import GitReportConfig

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    (V3.4 修正)
    用于与 Google Gemini API 交互的具体策略类。
    使用 genai.Client() 实例模式。
    """

    def __init__(self, config: GitReportConfig):
        """
        初始化 Gemini 客户端 (genai.Client)。

        抛出:
            ValueError: 如果 config 中未设置 GEMINI_API_KEY。
        """
        self.config = config
        if not self.config.GEMINI_API_KEY:
            logger.error("❌ (V3.4) GEMINI_API_KEY 未设置。请检查您的 .env 文件。")
            raise ValueError("GEMINI_API_KEY 未设置。")

        try:
            # (V3.4 修正) 匹配 test.py，使用 genai.Client()
            # 'genai' 现在来自 'from google import genai'
            self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)
            self.default_model = self.config.DEFAULT_MODEL_GEMINI
            logger.info(
                f"✅ (V3.4) GeminiProvider (genai.Client 模式) 初始化成功 (默认模型: {self.default_model})"
            )
        except Exception as e:
            logger.error(f"❌ (V3.4) Gemini (genai.Client) 客户端初始化失败: {e}")
            raise ValueError(f"Gemini (genai.Client) 客户端初始化失败: {e}")

    def generate_summary(
        self, system_prompt: str, user_prompt: str, model_name: str | None = None
    ) -> str:
        """
        (V3.4 修正) 使用 Gemini (genai.Client) API 生成摘要。
        """
        try:
            # (V3.4) 选择模型：使用指定的 model_name 或默认模型
            model_to_use = model_name or self.default_model

            # (V3.4 修正) 匹配 test.py，模型名称需要 "models/" 前缀
            client_model_name = f"models/{model_to_use}"

            # V3.4 简化：我们假定 V3.3 的完整提示在 user_prompt 中。
            # system_prompt 暂时为空。
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            # (V3.4 修正) 匹配 test.py，使用 client.models.generate_content()
            response = self.client.models.generate_content(
                model=client_model_name, contents=full_prompt
            )

            # (V3.4 修正) 确保回复有效
            if not response or not response.text:
                logger.error("❌ [GeminiProvider 错误] API 调用成功，但回复内容为空")
                raise Exception("API 调用成功，但回复内容为空")

            return response.text

        except APIError as e:
            # (V3.4 修正) 更明确的 API 错误
            logger.error(f"❌ [GeminiProvider API 错误]: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [GeminiProvider 错误] 生成内容失败: {e}")
            raise
