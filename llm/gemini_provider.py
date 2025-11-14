# llm/gemini_provider.py
"""
[V3.5] LLMProvider 针对 Google Gemini 的具体实现。
- 实现了 V3.5 的业务接口。
- 从 'prompts/gemini/' 目录加载自己的提示词。
"""
import logging
from typing import Optional, Dict
import os

try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    # 错误将在 AIService 工厂函数中被捕获
    pass

from llm.provider_abc import LLMProvider
from config import GitReportConfig

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    (V3.5) Gemini 策略实现。
    """

    def __init__(self, config: GitReportConfig):
        """
        (V3.5) 初始化 Gemini 客户端 (genai.Client) 并加载 Gemini 专用提示词。
        """
        self.config = config
        if not self.config.GEMINI_API_KEY:
            logger.error("❌ (V3.4) GEMINI_API_KEY 未设置。请检查您的 .env 文件。")
            raise ValueError("GEMINI_API_KEY 未设置。")

        try:
            self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)
            self.default_model = self.config.DEFAULT_MODEL_GEMINI

            # (V3.5) 加载 Gemini 专用提示词
            self.prompts = self._load_prompts_from_dir(
                os.path.join(self.config.SCRIPT_BASE_PATH, "prompts", "gemini")
            )

            logger.info(
                f"✅ (V3.5) GeminiProvider (genai.Client 模式) 初始化成功 (已加载 {len(self.prompts)} 个提示)"
            )
        except Exception as e:
            logger.error(f"❌ (V3.4) Gemini (genai.Client) 客户端初始化失败: {e}")
            raise ValueError(f"Gemini (genai.Client) 客户端初始化失败: {e}")

    def _load_prompts_from_dir(self, prompt_dir: str) -> Dict[str, str]:
        """(V3.5) 辅助函数：从此 Provider 的目录加载所有 .txt 模板"""
        prompts = {}
        try:
            for filename in os.listdir(prompt_dir):
                if filename.endswith(".txt"):
                    # 'diff_map.txt' -> 'diff_map'
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
        self, prompt_key: str, format_kwargs: dict, model_name: str | None = None
    ) -> Optional[str]:
        """(V3.5) 内部辅助函数，用于格式化和调用 Gemini"""

        prompt_template = self.prompts.get(prompt_key)
        if not prompt_template:
            logger.error(f"❌ [GeminiProvider] 未找到提示词: '{prompt_key}'")
            return None

        try:
            # Gemini 需要一个完整的提示词
            full_prompt = prompt_template.format(**format_kwargs)
        except KeyError as e:
            logger.error(
                f"❌ [GeminiProvider] 格式化提示 '{prompt_key}' 失败: 缺少键 {e}"
            )
            return None

        try:
            model_to_use = model_name or self.default_model
            client_model_name = f"models/{model_to_use}"

            response = self.client.models.generate_content(
                model=client_model_name, contents=full_prompt
            )

            if not response or not response.text:
                logger.error("❌ [GeminiProvider 错误] API 调用成功，但回复内容为空")
                raise Exception("API 调用成功，但回复内容为空")

            return response.text

        except APIError as e:
            logger.error(f"❌ [GeminiProvider API 错误]: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [GeminiProvider 错误] 生成内容失败: {e}")
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
