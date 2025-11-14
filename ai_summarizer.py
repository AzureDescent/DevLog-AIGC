# ai_summarizer.py
import logging
import sys
from typing import Optional
from config import GitReportConfig
import os

# --- (V3.4) 导入抽象层和具体策略 ---
from llm.provider_abc import LLMProvider
from llm.gemini_provider import GeminiProvider
from llm.deepseek_provider import DeepSeekProvider

# --- (V3.4) 结束 ---


try:
    import google.generativeai as genai
except ImportError:
    print("错误: google-generativeai 库未安装。请运行: pip install google-generativeai")
    pass

logger = logging.getLogger(__name__)


# --- (V3.4) 工厂函数 ---
def get_llm_provider(provider_id: str, config: GitReportConfig) -> LLMProvider:
    """
    (V3.4) 工厂函数，根据 provider_id 选择并实例化正确的 LLM 供应商
    这是策略模式选择的核心。
    """
    logger.info(f"ℹ️ (V3.4) 正在尝试初始化 LLM 供应商: {provider_id}")

    # (V3.4) 验证所选供应商是否已设置其密钥
    if not config.is_provider_configured(provider_id):
        logger.error(f"❌ (V3.4) 供应商 '{provider_id}' 未配置。")
        raise ValueError(
            f"供应商 '{provider_id}' 未配置。 "
            f"请在您的 .env 文件中设置相应的 API 密钥。"
        )

    # (V3.4) 策略选择
    try:
        if provider_id == "gemini":
            return GeminiProvider(config)
        elif provider_id == "deepseek":
            return DeepSeekProvider(config)

        # (V3.4) 未知供应商的回退
        logger.error(f"❌ (V3.4) 未知的 LLM 供应商: {provider_id}")
        raise ValueError(f"未知的 LLM 供应商: {provider_id}")
    except ImportError as e:
        logger.error(f"❌ (V3.4) 导入供应商 '{provider_id}' 失败。")
        logger.error(
            f"   请确保已安装所有必需的依赖 (例如 'pip install google-generativeai openai')。"
        )
        raise ImportError(f"供应商 '{provider_id}' 依赖缺失: {e}")
    except Exception as e:
        # 捕获 Gemini/DeepSeek __init__ 中的其他异常
        logger.error(f"❌ (V3.4) 实例化供应商 '{provider_id}' 失败: {e}")
        raise


# (V2.4 重构: 整个文件被重构为 AIService 类)
class AIService:
    """
    (V3.4 重构) 封装所有对 LLM 的调用。
    在初始化时配置一次供应商 (策略)。
    """

    def __init__(self, config: GitReportConfig, provider_id: str):
        """
        (V3.4 修改) 初始化 AI 服务
        - provider_id: [V3.4] 用户选择的供应商 ID (例如 "gemini") 。
        """
        self.config = config

        # (V3.4) AIService 持有一个对 "Strategy" (LLMProvider) 的引用
        # 它从工厂获取这个供应商 。
        # 如果 provider_id 无效或未配置，工厂将引发 ValueError。
        self.provider: LLMProvider = get_llm_provider(provider_id, config)

        logger.info(
            f"✅ 🤖 AI 服务已成功初始化 (Provider: {self.provider.__class__.__name__})"
        )

    # (V3.4) 移除: _configure_genai(self)
    # 此逻辑现已移至 llm/gemini_provider.py

    # --- (V3.3) Prompt 加载器 (V3.4 保持不变) ---
    def _load_prompt_template(self, template_name: str) -> Optional[str]:
        """(V3.3) 辅助函数：从 prompts/ 目录加载模板"""
        prompt_path = os.path.join(
            self.config.SCRIPT_BASE_PATH, "prompts", template_name
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"❌ (V3.3) Prompt 模板文件未找到: {prompt_path}")
            return None
        except Exception as e:
            logger.error(f"❌ (V3.3) 加载 Prompt 模板失败 ({prompt_path}): {e}")
            return None

    # --- (V3.4) 重构所有 AI 调用方法 ---

    def _generate_content(
        self, prompt_template_name: str, format_kwargs: dict
    ) -> Optional[str]:
        """
        (V3.4 新增) 内部辅助函数，用于统一调用 self.provider。
        """
        if not self.provider:
            logger.error("❌ (V3.4) AI Provider 未初始化。")
            return None

        # (V3.3) 加载 Prompt
        prompt_template = self._load_prompt_template(prompt_template_name)
        if not prompt_template:
            return None

        # (V3.3) 格式化 Prompt
        try:
            user_prompt = prompt_template.format(**format_kwargs)
        except KeyError as e:
            logger.error(
                f"❌ (V3.4) 格式化 Prompt '{prompt_template_name}' 失败: 缺少键 {e}"
            )
            return None

        logger.info(f"🤖 正在调用 AI Provider: {self.provider.__class__.__name__}...")

        try:
            # (V3.4) 将工作委托给选定的供应商
            # 我们将 V3.3 完整的、已格式化的提示作为 'user_prompt' 传递。
            # 'system_prompt' 暂时为空。
            # V3.5 将通过修改此处的逻辑来实现提示词差异化 。
            system_prompt = ""

            response_text = self.provider.generate_summary(
                system_prompt=system_prompt, user_prompt=user_prompt
            )

            logger.info(f"✅ AI Provider 调用成功 ({prompt_template_name})")
            return response_text

        except Exception as e:
            logger.error(
                f"❌ AI Provider 调用失败 ({self.provider.__class__.__name__}): {e}"
            )
            return None

    def get_single_diff_summary(self, diff_content: str) -> Optional[str]:
        """
        (V3.4 重构) 使用 AI 单独总结一个 diff 的核心逻辑变更。
        """
        if len(diff_content) > 100000:
            logger.warning(
                f"⚠️ Diff 内容过长 ({len(diff_content)} chars)，跳过 AI 总结。"
            )
            return "(Diff 内容过长，已跳过总结)"

        summary = self._generate_content("diff_map.txt", {"diff_content": diff_content})

        # (V3.3) V3.3 的特定后处理
        if summary:
            return summary.strip().replace("\n", " ")
        return None

    def get_ai_summary(
        self,
        text_report: str,
        diff_summaries: Optional[str] = None,
        previous_summary: Optional[str] = None,
    ) -> Optional[str]:
        """
        (V3.4 重构) 使用 AI 生成最终的工作摘要。
        """
        # (V3.3) 准备用于模板的动态内容块
        history_block = (
            f"""
        --- 这是你昨天的工作摘要（历史上下文） ---
        {previous_summary}
        --- 历史上下文结束 ---
        """
            if previous_summary and previous_summary.strip()
            else ""
        )

        diff_block = (
            f"""
        --- 今天 AI 生成的逐条代码变更总结 (Diffs) ---
        {diff_summaries}
        --- 代码变更总结结束 ---
        """
            if diff_summaries and diff_summaries.strip()
            else ""
        )

        return self._generate_content(
            "summary_reduce.txt",
            {
                "history_block": history_block,
                "text_report": text_report,
                "diff_block": diff_block,
            },
        )

    def distill_project_memory(self) -> Optional[str]:
        """
        (V3.4 重构) (记忆蒸馏) 读取历史日志，生成浓缩记忆。
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

        return self._generate_content("memory_distill.txt", {"full_log": full_log})

    def generate_public_article(
        self,
        today_technical_summary: str,
        project_historical_memory: str,
        project_readme: Optional[str] = None,
    ) -> Optional[str]:
        """
        (V3.4 重构) 转换为面向公众的公众号文章。
        """
        logger.info("✍️ 正在启动 AI '风格转换' 阶段 (生成公众号文章)...")

        # (V3.3) 准备用于模板的动态内容块
        readme_block = (
            f"""
        3.  **项目 README (使命与愿景)**:
            (这能让你理解项目的核心价值和目标用户)
            ---
            {project_readme}
            ---
        """
            if project_readme
            else ""
        )

        return self._generate_content(
            "public_article.txt",
            {
                "project_historical_memory": project_historical_memory,
                "today_technical_summary": today_technical_summary,
                "readme_block": readme_block,
            },
        )
