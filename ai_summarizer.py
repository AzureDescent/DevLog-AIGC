# ai_summarizer.py
import logging
import sys
from typing import Optional
from config import GitReportConfig
import os

try:
    import google.generativeai as genai
except ImportError:
    print("错误: google-generativeai 库未安装。请运行: pip install google-generativeai")
    sys.exit(1)

logger = logging.getLogger(__name__)


# (V2.4 重构: 整个文件被重构为 AIService 类)


class AIService:
    """
    封装所有对 Google Gemini AI 的调用。
    在初始化时配置一次模型，供所有方法使用。
    """

    def __init__(self, config: GitReportConfig):
        """
        初始化 AI 服务，加载配置并配置一次 GenAI 模型。
        """
        self.config = config
        # (V2.4 重构: 在初始化时调用一次，并存储模型实例)
        self.model = self._configure_genai()
        if self.model:
            logger.info("🤖 AI 服务已成功初始化 (Gemini 2.5 Flash)")
        else:
            logger.error("❌ AI 服务初始化失败，后续 AI 功能将不可用。")

    def _configure_genai(self) -> Optional[genai.GenerativeModel]:  # type: ignore
        """
        (V2.4 重构: 转换为私有方法)
        辅助函数，用于配置 GenAI，避免代码重复。
        """
        # (V2.4 重构: 使用 self.config)
        if not self.config.AI_API_KEY:
            logger.warning("❌ 未配置 GOOGLE_API_KEY 环境变量")
            return None
        try:
            # (V2.4 重构: 使用 self.config)
            genai.configure(api_key=self.config.AI_API_KEY)  # type: ignore
            model = genai.GenerativeModel("gemini-2.5-flash")  # type: ignore
            return model
        except Exception as e:
            logger.error(f"❌ GenAI 配置失败: {e}")
            return None

    # --- (V3.3) 新增: Prompt 加载器 ---
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

    # --- (V3.3) 结束 ---

    def get_single_diff_summary(self, diff_content: str) -> Optional[str]:
        """
        (V2.4 重构: 转换为方法)
        (V3.3 修改: 从 prompts/diff_map.txt 加载 Prompt)
        (新增 "Map" 阶段)
        使用 AI 单独总结一个 diff 的核心逻辑变更。
        """
        if not self.model:
            return None

        # (V3.3) 加载 Prompt
        prompt_template = self._load_prompt_template("diff_map.txt")
        if not prompt_template:
            return None

        logger.info("🤖 正在调用 AI 总结单个 Diff...")

        if len(diff_content) > 100000:
            logger.warning(
                f"⚠️ Diff 内容过长 ({len(diff_content)} chars)，跳过 AI 总结。"
            )
            return "(Diff 内容过长，已跳过总结)"

        # (V3.3) 格式化 Prompt
        prompt = prompt_template.format(diff_content=diff_content)

        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip().replace("\n", " ")
            logger.info(f"✅ 单个 Diff 总结成功: {summary}")
            return summary
        except Exception as e:
            logger.error(f"❌ 单个 Diff 总结失败: {e}")
            return None

    def get_ai_summary(
        self,
        text_report: str,
        diff_summaries: Optional[str] = None,
        previous_summary: Optional[str] = None,
    ) -> Optional[str]:
        """
        (V3.3 修改: 从 prompts/summary_reduce.txt 加载 Prompt)
        使用 AI 生成最终的工作摘要。
        """
        logger.info("🤖 正在调用 AI 生成*最终*摘要...")

        if not self.model:
            return None

        # (V3.3) 加载 Prompt
        prompt_template = self._load_prompt_template("summary_reduce.txt")
        if not prompt_template:
            return None

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

        # (V3.3) 格式化 Prompt
        prompt = prompt_template.format(
            history_block=history_block, text_report=text_report, diff_block=diff_block
        )

        try:
            response = self.model.generate_content(prompt)
            logger.info("✅ AI 最终摘要生成成功 (已包含历史上下文)")
            return response.text

        except Exception as e:
            logger.error(f"❌ AI 最终摘要生成失败: {e}")
            return None

    def distill_project_memory(self) -> Optional[str]:
        """
        (V3.1 修改)
        (V3.3 修改: 从 prompts/memory_distill.txt 加载 Prompt)
        (记忆蒸馏) 读取 *所有* 的历史日志，生成一个浓缩的、有权重的记忆文件。
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

        if not self.model:
            return None

        # (V3.3) 加载 Prompt
        prompt_template = self._load_prompt_template("memory_distill.txt")
        if not prompt_template:
            return None

        # (V3.3) 格式化 Prompt
        prompt = prompt_template.format(full_log=full_log)

        try:
            response = self.model.generate_content(prompt)
            logger.info("✅ AI '记忆蒸馏' 成功")
            return response.text
        except Exception as e:
            logger.error(f"❌ AI '记忆蒸馏' 失败: {e}")
            return None

    def generate_public_article(
        self,
        today_technical_summary: str,
        project_historical_memory: str,
        project_readme: Optional[str] = None,
    ) -> Optional[str]:
        """
        (V3.3 修改: 从 prompts/public_article.txt 加载 Prompt)
        将技术摘要和项目历史，转换为面向公众的公众号文章，并利用 README 文件。
        """
        logger.info("✍️ 正在启动 AI '风格转换' 阶段 (生成公众号文章)...")

        if not self.model:
            return None

        # (V3.3) 加载 Prompt
        prompt_template = self._load_prompt_template("public_article.txt")
        if not prompt_template:
            return None

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

        # (V3.3) 格式化 Prompt
        prompt = prompt_template.format(
            project_historical_memory=project_historical_memory,
            today_technical_summary=today_technical_summary,
            readme_block=readme_block,
        )

        try:
            response = self.model.generate_content(prompt)
            logger.info("✅ AI '风格转换' 成功 (已包含项目背景)")
            return response.text
        except Exception as e:
            logger.error(f"❌ AI '风格转换' 失败: {e}")
            return None
