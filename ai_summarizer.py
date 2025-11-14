# ai_summarizer.py
import logging
import sys
from typing import Optional
from config import GitReportConfig
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


# --- (V3.4) 工厂函数 (V3.5 保持不变) ---
def get_llm_provider(provider_id: str, config: GitReportConfig) -> LLMProvider:
    """
    (V3.4) 工厂函数，根据 provider_id 选择并实例化正确的 LLM 供应商。
    """
    logger.info(f"ℹ️ (V3.4) 正在尝试初始化 LLM 供应商: {provider_id}")

    if not config.is_provider_configured(provider_id):
        logger.error(f"❌ (V3.4) 供应商 '{provider_id}' 未配置。")
        raise ValueError(
            f"供应商 '{provider_id}' 未配置。 "
            f"请在您的 .env 文件中设置相应的 API 密钥。"
        )
    try:
        if provider_id == "gemini":
            return GeminiProvider(config)
        elif provider_id == "deepseek":
            return DeepSeekProvider(config)

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


# --- (V3.5) AIService (上下文) ---
class AIService:
    """
    (V3.5 重构) 封装所有对 LLM 的调用。
    - 提示词加载逻辑已移至 Provider。
    - AIService 只负责传递*原始数据*。
    """

    def __init__(self, config: GitReportConfig, provider_id: str):
        """
        (V3.4) 初始化 AI 服务
        """
        self.config = config
        self.provider: LLMProvider = get_llm_provider(provider_id, config)
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
        (V3.5 重构) 委托 Provider 蒸馏记忆。
        """
        logger.info("🧠 正在启动 AI '记忆蒸馏' 阶段...")

        log_file_path = os.path.join(
            self.config.PROJECT_DATA_PATH, self.config.PROJECT_LOG_FILE
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
    ) -> Optional[str]:
        """
        (V3.5 重构) 委托 Provider 生成公众号文章。
        """
        logger.info("✍️ 正在启动 AI '风格转换' 阶段 (生成公众号文章)...")
        try:
            # (V3.5) 纯委托
            return self.provider.generate_article(
                today_technical_summary, project_historical_memory, project_readme
            )
        except Exception as e:
            logger.error(f"❌ (V3.5) generate_public_article 失败: {e}")
            return None
