# ai_summarizer.py
import logging
import sys
from typing import Optional

# (V4.0) 导入 GlobalConfig 和 RunContext
from config import GlobalConfig
from context import RunContext
import os

# (V3.4) 导入抽象层和具体策略
from llm.provider_abc import LLMProvider
from llm.gemini_provider import GeminiProvider
from llm.deepseek_provider import DeepSeekProvider

# (V3.4) 保留导入
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    pass

logger = logging.getLogger(__name__)


# --- (V3.4) 工厂函数 (V4.0 重构) ---
def get_llm_provider(provider_id: str, global_config: GlobalConfig) -> LLMProvider:
    """
    (V4.0) 工厂函数，根据 provider_id 选择并实例化正确的 LLM 供应商。
    现在接收 GlobalConfig。
    """
    logger.info(f"ℹ️ (V3.4) 正在尝试初始化 LLM 供应商: {provider_id}")

    # (V4.0) 使用 global_config
    if not global_config.is_provider_configured(provider_id):
        logger.error(f"❌ (V3.4) 供应商 '{provider_id}' 未配置。")
        raise ValueError(
            f"供应商 '{provider_id}' 未配置。 "
            f"请在您的 .env 文件中设置相应的 API 密钥。"
        )
    try:
        # (V4.0) 将 global_config 传递给 Provider
        if provider_id == "gemini":
            return GeminiProvider(global_config)
        elif provider_id == "deepseek":
            return DeepSeekProvider(global_config)

        logger.error(f"❌ (V3.4) 未知的 LLM 供应商: {provider_id}")
        raise ValueError(f"未知的 LLM 供应商: {provider_id}")
    except ImportError as e:
        logger.error(f"❌ (V3.4) 导入供应商 '{provider_id}' 失败。")
        logger.error(
            f"   请确保已安装所有必需的依赖 (例如 'pip install google-generativeai openai')。"
        )
        raise ImportError(f"供应商 '{provider_id}' 依赖缺失: {e}")
    except Exception as e:
        logger.error(f"❌ (V3.4) 实例化供应商 '{provider_id}' 失败: {e}")
        raise


# --- (V3.5) AIService (V4.0 重构) ---
class AIService:
    """
    (V4.0 重构) 封装所有对 LLM 的调用。
    - 由 RunContext 初始化。
    - 将 GlobalConfig 传递给 LLMProvider。
    """

    def __init__(self, context: RunContext):
        """
        (V4.0) 初始化 AI 服务
        - 接收 RunContext
        """
        self.context = context
        self.global_config = context.global_config
        # (V4.0) 从 context 获取 llm_id，并将 global_config 传递给工厂
        self.provider: LLMProvider = get_llm_provider(
            context.llm_id, self.global_config
        )
        logger.info(
            f"✅ 🤖 AI 服务已成功初始化 (Provider: {self.provider.__class__.__name__})"
        )

    # --- (V3.5) Prompt 加载器 (已移除) ---
    # _load_prompt_template 和 _generate_content 已被移除。

    # --- (V3.5) 重构所有 AI 调用方法 (纯委托) ---

    def get_single_diff_summary(self, diff_content: str) -> Optional[str]:
        """
        (V3.5 重构) 委托 Provider 总结 diff。
        """
        if len(diff_content) > 100000:
            logger.warning(
                f"⚠️ Diff 内容过长 ({len(diff_content)} chars)，跳过 AI 总结。"
            )
            return "(Diff 内容过长，已跳过总结)"

        try:
            # (V3.5) 纯委托
            summary = self.provider.summarize_diff(diff_content)
            if summary:
                # (V3.3) 的特定后处理仍然保留
                return summary.strip().replace("\n", " ")
            return None
        except Exception as e:
            logger.error(f"❌ (V3.5) get_single_diff_summary 失败: {e}")
            return None

    def get_ai_summary(
        self,
        text_report: str,
        diff_summaries: Optional[str] = None,
        previous_summary: Optional[str] = None,
    ) -> Optional[str]:
        """
        (V3.5 重构) 委托 Provider 生成最终摘要。
        """
        try:
            # (V3.5) 纯委托
            return self.provider.summarize_report(
                text_report, diff_summaries, previous_summary
            )
        except Exception as e:
            logger.error(f"❌ (V3.5) get_ai_summary 失败: {e}")
            return None

    def distill_project_memory(self) -> Optional[str]:
        """
        (V4.0 重构) 委托 Provider 蒸馏记忆。
        - (V4.0) 使用 context 和 global_config 获取路径
        """
        logger.info("🧠 正在启动 AI '记忆蒸馏' 阶段...")

        # (V4.0) 使用 context.project_data_path 和 global_config.PROJECT_LOG_FILE
        log_file_path = os.path.join(
            self.context.project_data_path, self.global_config.PROJECT_LOG_FILE
        )
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                full_log = f.read()
        except FileNotFoundError:
            logger.info(f"ℹ️ 未找到项目日志 ({log_file_path})，将创建新记忆。")
            return None
        except Exception as e:
            logger.error(f"❌ 读取项目日志失败 ({log_file_path}): {e}")
            return None

        if not full_log.strip():
            logger.info("ℹ️ 项目日志为空，无需蒸馏。")
            return None

        try:
            # (V3.5) 纯委托
            return self.provider.distill_memory(full_log)
        except Exception as e:
            logger.error(f"❌ (V3.5) distill_project_memory 失败: {e}")
            return None

    def generate_public_article(
        self,
        today_technical_summary: str,
        project_historical_memory: str,
        project_readme: Optional[str] = None,
        style: str = "default",  # (V3.6) 接收来自 Orchestrator 的 style
    ) -> Optional[str]:
        """
        (V3.6 重构) 委托 Provider 生成公众号文章。
        """
        logger.info(f"✍️ 正在启动 AI '风格转换' 阶段 (Style: {style})...")  # (V3.6)
        try:
            # (V3.6) 将 style 透传给 provider
            return self.provider.generate_article(
                today_technical_summary,
                project_historical_memory,
                project_readme,
                style=style,
            )
        except Exception as e:
            logger.error(f"❌ (V3.6) generate_public_article (style={style}) 失败: {e}")
            return None
