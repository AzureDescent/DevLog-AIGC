# llm/deepseek_provider.py
"""
[V3.4] LLMProvider 针对 DeepSeek 的具体实现
该供应商使用 DeepSeek 提供的 OpenAI 兼容 API。
它利用了 'openai' Python 库
"""
import logging
from typing import Optional
from openai import OpenAI  # 关键：导入 OpenAI
from llm.provider_abc import LLMProvider
from config import GitReportConfig

logger = logging.getLogger(__name__)


class DeepSeekProvider(LLMProvider):
    """
    用于与 DeepSeek API (OpenAI 兼容) 交互的具体策略类
    """

    def __init__(self, config: GitReportConfig):
        """
        初始化 OpenAI 客户端，使其指向 DeepSeek API 端点。

        抛出:
            ValueError: 如果 config 中未设置 DEEPSEEK_API_KEY。
        """
        self.config = config
        if not self.config.DEEPSEEK_API_KEY:
            logger.error("❌ (V3.4) DEEPSEEK_API_KEY 未设置。请检查您的 .env 文件。")
            raise ValueError("DEEPSEEK_API_KEY 未设置。请检查您的.env 文件。")
        try:
            # 这是来自指导文件的关键发现：
            # 我们使用 OpenAI 客户端，但使用 DeepSeek 的
            # base_url 和 api_key 对其进行配置
            self.client = OpenAI(
                api_key=self.config.DEEPSEEK_API_KEY,
                base_url=self.config.DEEPSEEK_BASE_URL,
            )
            self.default_model = self.config.DEFAULT_MODEL_DEEPSEEK
            logger.info(
                f"✅ (V3.4) DeepSeekProvider 初始化成功 (默认模型: {self.default_model})"
            )
        except Exception as e:
            logger.error(f"❌ (V3.4) DeepSeek (OpenAI) 客户端初始化失败: {e}")
            raise ValueError(f"DeepSeek (OpenAI) 客户端初始化失败: {e}")

    def generate_summary(
        self, system_prompt: str, user_prompt: str, model_name: str | None = None
    ) -> str:
        """
        使用 DeepSeek (OpenAI 兼容) 聊天 API 生成摘要
        """
        try:
            # (V3.4) 选择模型：使用指定的 model_name 或默认模型
            model_to_use = model_name or self.default_model

            # (V3.4) OpenAI 兼容 API 使用结构化的 'messages' 列表
            # V3.4 简化：我们假定 V3.3 的完整提示在 user_prompt 中。
            # system_prompt 暂时为空，V3.5 再进行提示词分离 。
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self.client.chat.completions.create(
                model=model_to_use, messages=messages
            )

            # (V3.4) 从响应中提取内容
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                raise Exception("未从 DeepSeek API 收到内容")

        except Exception as e:
            logger.error(f"❌ [DeepSeekProvider 错误] 生成内容失败: {e}")
            raise
