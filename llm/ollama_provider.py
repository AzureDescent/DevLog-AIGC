# llm/ollama_provider.py
import logging
import os
from typing import Optional, Dict

# 复用 openai 库，因为 Ollama 完美兼容 OpenAI 的接口格式
try:
    from openai import OpenAI
except ImportError:
    pass

from llm.provider_abc import LLMProvider, register_provider
from config import GlobalConfig

logger = logging.getLogger(__name__)

@register_provider("ollama")
class OllamaProvider(LLMProvider):
    """
    [V4.7] Ollama 本地大模型策略实现。
    通过 OpenAI 兼容接口连接本地 Ollama 服务。
    """

    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config

        # 获取 Base URL，Docker 内部访问宿主机需要特殊地址
        # 默认为 http://host.docker.internal:11434/v1
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
        self.model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

        try:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key="ollama",  # Ollama 不需要真实 Key，但库要求必填
            )

            # 加载 DeepSeek 的提示词作为通用提示词 (结构相似)
            # 或者你可以复制一份 prompts/deepseek 重命名为 prompts/ollama
            self.prompts = self._load_prompts_from_dir(
                os.path.join(self.global_config.SCRIPT_BASE_PATH, "prompts", "deepseek")
            )

            # 设置 System Prompt
            self.system_prompt = self.prompts.get("system", "你是一个有用的助手。")

            logger.info(f"✅ OllamaProvider 初始化成功 (模型: {self.model_name}, 地址: {self.base_url})")
        except Exception as e:
            logger.error(f"❌ Ollama 客户端初始化失败: {e}")
            raise ValueError(f"Ollama 客户端初始化失败: {e}")

    def _load_prompts_from_dir(self, prompt_dir: str) -> Dict[str, str]:
        # 复用简单的加载逻辑
        prompts = {}
        try:
            for root, _, files in os.walk(prompt_dir):
                for filename in files:
                    if filename.endswith(".txt"):
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, prompt_dir)
                        key = os.path.splitext(relative_path)[0].replace(os.path.sep, "/")
                        with open(file_path, "r", encoding="utf-8") as f:
                            prompts[key] = f.read()
            return prompts
        except Exception:
            return {}

    def _generate(self, user_prompt_key: str, format_kwargs: dict, style: str = "default") -> Optional[str]:
        prompt_template = self.prompts.get(user_prompt_key)
        if not prompt_template:
            # 尝试回退到 default
            if "articles/" in user_prompt_key:
                prompt_template = self.prompts.get("articles/default")

            if not prompt_template:
                logger.error(f"❌ [Ollama] 未找到提示词: {user_prompt_key}")
                return None

        try:
            user_prompt = prompt_template.format(**format_kwargs)

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
            )

            if response.choices:
                return response.choices[0].message.content.strip()
            return None
        except Exception as e:
            logger.error(f"❌ [Ollama] 生成失败: {e}")
            return None

    # --- 实现接口 ---
    def summarize_diff(self, diff_content: str) -> Optional[str]:
        return self._generate("diff_map", {"diff_content": diff_content})

    def summarize_report(self, text_report: str, diff_summaries: str = None, previous_summary: str = None) -> Optional[str]:
        history_block = f"---\n历史上下文:\n{previous_summary}\n---" if previous_summary else ""
        diff_block = f"---\n逐条 Diff 总结:\n{diff_summaries}\n---" if diff_summaries else ""
        return self._generate("summary_reduce", {
            "history_block": history_block, "text_report": text_report, "diff_block": diff_block
        })

    def distill_memory(self, full_log: str) -> Optional[str]:
        return self._generate("memory_distill", {"full_log": full_log})

    def generate_article(self, today_summary: str, history: str, readme: str = None, style: str = "default") -> Optional[str]:
        readme_block = f"---\n项目 README:\n{readme}\n---" if readme else ""
        # 注意：这里复用了 deepseek 的提示词路径结构
        prompt_key = f"articles/{style}"
        return self._generate(prompt_key, {
            "project_historical_memory": history,
            "today_technical_summary": today_summary,
            "readme_block": readme_block
        }, style)