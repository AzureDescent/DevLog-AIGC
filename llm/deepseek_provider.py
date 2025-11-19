# llm/deepseek_provider.py
"""
[V3.5] LLMProvider 针对 DeepSeek 的具体实现。
[V4.1] 使用 @register_provider 进行自动注册。
"""
import logging
from typing import Optional, Dict
import os

try:
    from openai import OpenAI
except ImportError:
    pass

# (V4.1) 导入注册装饰器
from llm.provider_abc import LLMProvider, register_provider

# (V4.0) 导入 GlobalConfig
from config import GlobalConfig

logger = logging.getLogger(__name__)


@register_provider("deepseek")  # <--- [V4.1] 注册 DeepSeek
class DeepSeekProvider(LLMProvider):
    """
    (V3.5) DeepSeek 策略实现 (OpenAI 兼容)。
    """

    def __init__(self, global_config: GlobalConfig):
        """
        (V4.0) 初始化 DeepSeek 客户端并加载 DeepSeek 专用提示词。
        - 接收 GlobalConfig
        """
        self.global_config = global_config  # (V4.0)
        if not self.global_config.DEEPSEEK_API_KEY:  # (V4.0)
            logger.error("❌ (V3.4) DEEPSEEK_API_KEY 未设置。请检查您的 .env 文件。")
            raise ValueError("DEEPSEEK_API_KEY 未设置。")

        try:
            self.client = OpenAI(
                api_key=self.global_config.DEEPSEEK_API_KEY,  # (V4.0)
                base_url=self.global_config.DEEPSEEK_BASE_URL,  # (V4.0)
            )
            self.default_model = self.global_config.DEFAULT_MODEL_DEEPSEEK  # (V4.0)

            # (V3.6) 加载 DeepSeek 专用提示词
            self.prompts = self._load_prompts_from_dir(
                os.path.join(
                    self.global_config.SCRIPT_BASE_PATH, "prompts", "deepseek"
                )  # (V4.0)
            )

            # (V3.5) DeepSeek 需要一个 System Prompt
            self.system_prompt = self.prompts.get("system", "你是一个有用的助手。")

            logger.info(
                f"✅ (V3.6) DeepSeekProvider 初始化成功 (已加载 {len(self.prompts)} 个提示)"
            )
        except Exception as e:
            logger.error(f"❌ (V3.4) DeepSeek (OpenAI) 客户端初始化失败: {e}")
            raise ValueError(f"DeepSeek (OpenAI) 客户端初始化失败: {e}")

    def _load_prompts_from_dir(self, prompt_dir: str) -> Dict[str, str]:
        # ... (保留原有逻辑，省略以节省篇幅) ...
        prompts = {}
        try:
            for root, _, files in os.walk(prompt_dir):
                for filename in files:
                    if filename.endswith(".txt"):
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, prompt_dir)
                        key = os.path.splitext(relative_path)[0]
                        key = key.replace(os.path.sep, "/")
                        with open(file_path, "r", encoding="utf-8") as f:
                            prompts[key] = f.read()
            return prompts
        except Exception:
            return {}

    def _generate(
        self, user_prompt_key: str, format_kwargs: dict, model_name: str | None = None
    ) -> Optional[str]:
        # ... (保留原有逻辑，省略以节省篇幅) ...
        user_prompt_template = self.prompts.get(user_prompt_key)
        if not user_prompt_template:
            logger.error(
                f"❌ [DeepSeekProvider] 未找到 User 提示词: '{user_prompt_key}'"
            )
            return None
        try:
            user_prompt = user_prompt_template.format(**format_kwargs)
            model_to_use = model_name or self.default_model
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = self.client.chat.completions.create(
                model=model_to_use, messages=messages
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                raise Exception("未从 DeepSeek API 收到内容")
        except Exception as e:
            logger.error(f"❌ [DeepSeekProvider 错误] 生成内容失败: {e}")
            raise

    # --- (V3.5) 实现 ABC 接口 ---
    # ... (实现与原文件一致，只是类被装饰器包裹了) ...

    def summarize_diff(self, diff_content: str) -> Optional[str]:
        return self._generate("diff_map", {"diff_content": diff_content})

    def summarize_report(
        self,
        text_report: str,
        diff_summaries: Optional[str] = None,
        previous_summary: Optional[str] = None,
    ) -> Optional[str]:
        history_block = (
            f"---\n历史上下文:\n{previous_summary}\n---" if previous_summary else ""
        )
        diff_block = (
            f"---\n逐条 Diff 总结:\n{diff_summaries}\n---" if diff_summaries else ""
        )
        return self._generate(
            "summary_reduce",
            {
                "history_block": history_block,
                "text_report": text_report,
                "diff_block": diff_block,
            },
        )

    def distill_memory(self, full_log: str) -> Optional[str]:
        return self._generate("memory_distill", {"full_log": full_log})

    def generate_article(
        self,
        today_technical_summary: str,
        project_historical_memory: str,
        project_readme: Optional[str] = None,
        style: str = "default",
    ) -> Optional[str]:
        readme_block = (
            f"---\n项目 README:\n{project_readme}\n---" if project_readme else ""
        )
        prompt_key = f"articles/{style}"
        if prompt_key not in self.prompts:
            prompt_key = "articles/default"
        return self._generate(
            prompt_key,
            {
                "project_historical_memory": project_historical_memory,
                "today_technical_summary": today_technical_summary,
                "readme_block": readme_block,
            },
        )
