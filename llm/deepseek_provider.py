# llm/deepseek_provider.py
"""
[V3.5] LLMProvider 针对 DeepSeek 的具体实现。
- 实现了 V3.5 的业务接口。
- 从 'prompts/deepseek/' 目录加载自己的提示词。
- 使用 System + User 角色。
"""
import logging
from typing import Optional, Dict
import os

try:
    from openai import OpenAI
except ImportError:
    # 错误将在 AIService 工厂函数中被捕获
    pass

from llm.provider_abc import LLMProvider
from config import GitReportConfig

logger = logging.getLogger(__name__)


class DeepSeekProvider(LLMProvider):
    """
    (V3.5) DeepSeek 策略实现 (OpenAI 兼容)。
    """

    def __init__(self, config: GitReportConfig):
        """
        (V3.5) 初始化 DeepSeek 客户端并加载 DeepSeek 专用提示词。
        """
        self.config = config
        if not self.config.DEEPSEEK_API_KEY:
            logger.error("❌ (V3.4) DEEPSEEK_API_KEY 未设置。请检查您的 .env 文件。")
            raise ValueError("DEEPSEEK_API_KEY 未设置。")

        try:
            self.client = OpenAI(
                api_key=self.config.DEEPSEEK_API_KEY,
                base_url=self.config.DEEPSEEK_BASE_URL,
            )
            self.default_model = self.config.DEFAULT_MODEL_DEEPSEEK

            # (V3.5) 加载 DeepSeek 专用提示词
            self.prompts = self._load_prompts_from_dir(
                os.path.join(self.config.SCRIPT_BASE_PATH, "prompts", "deepseek")
            )

            # (V3.5) DeepSeek 需要一个 System Prompt
            self.system_prompt = self.prompts.get("system", "你是一个有用的助手。")

            logger.info(
                f"✅ (V3.5) DeepSeekProvider 初始化成功 (已加载 {len(self.prompts)} 个提示)"
            )
        except Exception as e:
            logger.error(f"❌ (V3.4) DeepSeek (OpenAI) 客户端初始化失败: {e}")
            raise ValueError(f"DeepSeek (OpenAI) 客户端初始化失败: {e}")

    def _load_prompts_from_dir(self, prompt_dir: str) -> Dict[str, str]:
        """(V3.5) 辅助函数：从此 Provider 的目录加载所有 .txt 模板"""
        prompts = {}
        try:
            for filename in os.listdir(prompt_dir):
                if filename.endswith(".txt"):
                    name = filename.split(".")[0]
                    prompt_path = os.path.join(prompt_dir, filename)
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        prompts[name] = f.read()
            if not prompts:
                logger.warning(
                    f"⚠️ (V3.5) 在 {prompt_dir} 中未找到任何 .txt 提示词文件。"
                )
            return prompts
        except FileNotFoundError:
            logger.error(f"❌ (V3.5) 提示词目录未找到: {prompt_dir}")
            return {}
        except Exception as e:
            logger.error(f"❌ (V3.5) 加载提示词失败 ({prompt_dir}): {e}")
            return {}

    def _generate(
        self, user_prompt_key: str, format_kwargs: dict, model_name: str | None = None
    ) -> Optional[str]:
        """(V3.5) 内部辅助函数，用于格式化和调用 DeepSeek (OpenAI 兼容)"""

        user_prompt_template = self.prompts.get(user_prompt_key)
        if not user_prompt_template:
            logger.error(
                f"❌ [DeepSeekProvider] 未找到 User 提示词: '{user_prompt_key}'"
            )
            return None

        try:
            # DeepSeek 只需要 User 部分的提示
            user_prompt = user_prompt_template.format(**format_kwargs)
        except KeyError as e:
            logger.error(
                f"❌ [DeepSeekProvider] 格式化提示 '{user_prompt_key}' 失败: 缺少键 {e}"
            )
            return None

        try:
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
    ) -> Optional[str]:

        readme_block = (
            f"---\n项目 README:\n{project_readme}\n---" if project_readme else ""
        )

        return self._generate(
            "public_article",
            {
                "project_historical_memory": project_historical_memory,
                "today_technical_summary": today_technical_summary,
                "readme_block": readme_block,
            },
        )
