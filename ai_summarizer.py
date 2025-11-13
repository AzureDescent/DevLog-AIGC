# ai_summarizer.py
import logging
import sys
from typing import Optional
from config import GitReportConfig

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
            logger.info("🤖 AI 服务已成功初始化 (Gemini a 1-Flash)")
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

    def get_single_diff_summary(self, diff_content: str) -> Optional[str]:
        """
        (V2.4 重构: 转换为方法)
        (新增 "Map" 阶段)
        使用 AI 单独总结一个 diff 的核心逻辑变更。
        """
        # (V2.4 重构: 不再调用 _configure_genai，而是检查 self.model)
        if not self.model:
            return None

        logger.info("🤖 正在调用 AI 总结单个 Diff...")

        # (方法一的补充：在发送前再次过滤超大 diff)
        # (gemini-2.5-flash 的上下文约为 1M tokens,
        # 但我们应设置一个更合理的业务上限，例如 100k 字符)
        if len(diff_content) > 100000:
            logger.warning(
                f"⚠️ Diff 内容过长 ({len(diff_content)} chars)，跳过 AI 总结。"
            )
            return "(Diff 内容过长，已跳过总结)"

        prompt = f"""
        你是一名资深的程序员，擅长 Code Review。
        以下是一个 Git Commit 的 diff 内容。请用一句话（不要超过50个字）总结这个 diff 的核心代码逻辑变更。
        重点关注 *逻辑* 变更，忽略纯粹的格式化、重命名或依赖文件更新 (如 package-lock.json)。

        --- Diff 内容开始 ---
        {diff_content}
        --- Diff 内容结束 ---

        核心逻辑总结：
        """

        try:
            # (V2.4 重构: 使用 self.model)
            response = self.model.generate_content(prompt)
            # 清理总结，确保是单行
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
        (V2.4 重构: 转换为方法)
        (修改 "Reduce" 阶段)
        使用 AI 生成最终的工作摘要。
        """
        logger.info("🤖 正在调用 AI 生成*最终*摘要...")

        # (V2.4 重构: 不再调用 _configure_genai，而是检查 self.model)
        if not self.model:
            return None

        # (修改) V2.1: 更新 Prompt 以包含 previous_summary
        prompt = f"""
        你是一名资深的技术团队主管，你正在撰写一份连续的工作日报。

        {f'''
        --- 这是你昨天的工作摘要（历史上下文） ---
        {previous_summary}
        --- 历史上下文结束 ---
        ''' if previous_summary and previous_summary.strip() else ''}

        现在，这是今天团队的 Git 提交日志、代码变更统计，以及（可选的）AI 对每条代码变更的逐条总结：

        --- 今天的原始数据（Git 日志） ---
        {text_report}
        --- 原始数据结束 ---

        {f'''
        --- 今天 AI 生成的逐条代码变更总结 (Diffs) ---
        {diff_summaries}
        --- 代码变更总结结束 ---
        ''' if diff_summaries and diff_summaries.strip() else ''}

        请你基于**历史上下文**（如果提供了）和**今天的全部新数据**，撰写一份结构清晰、重点突出、人类可读的*今日*工作日报摘要。
        要求：
        1.  **体现连续性**: 在"总体概览"部分，请*务必*将今天的工作与昨天的摘要（如果提供了）联系起来。
            例如："在昨天完成了XX模块重构的基础上，今天团队..."
            或："今天的工作主要在修复昨天引入的XX问题..."
            或："延续昨天的开发，今天XX功能已完成..."
        2.  **按模块/功能/作者总结**: 合并归类今天的工作。优先使用 'AI 逐条总结' 来理解真实变更。
        3.  **高亮亮点**: 指出今天任何重大的功能上线、关键修复或需要注意的变更。
        4.  **输出格式**: 使用 Markdown 格式化，使其易于阅读。
        """

        try:
            # (V2.4 重构: 使用 self.model)
            response = self.model.generate_content(prompt)
            logger.info("✅ AI 最终摘要生成成功 (已包含历史上下文)")
            return response.text

        except Exception as e:
            logger.error(f"❌ AI 最终摘要生成失败: {e}")
            return None

    def distill_project_memory(self) -> Optional[str]:
        """
        (V2.4 重构: 转换为方法)
        (新增 "记忆蒸馏" 阶段)
        读取 *所有* 的历史日志，生成一个浓缩的、有权重的记忆文件。
        """
        logger.info("🧠 正在启动 AI '记忆蒸馏' 阶段...")

        # 1. 读取“地基”日志
        try:
            # (V2.4 重构: 使用 self.config)
            with open(self.config.PROJECT_LOG_FILE, "r", encoding="utf-8") as f:
                full_log = f.read()
        except FileNotFoundError:
            logger.info(
                f"ℹ️ 未找到项目日志 ({self.config.PROJECT_LOG_FILE})，将创建新记忆。"
            )
            return None  # 没有历史，无需蒸馏

        if not full_log.strip():
            logger.info("ℹ️ 项目日志为空，无需蒸馏。")
            return None

        # (V2.4 重构: 不再调用 _configure_genai，而是检查 self.model)
        if not self.model:
            return None

        # 2. 构造蒸馏 Prompt
        prompt = f"""
        你是一名项目历史学家和信息压缩专家。
        以下是本软件项目 *从开始到今天* 所有的 AI 生成的每日工作摘要日志 (JSONL 格式)。
        每条日志包含：日期(date), 新增行数(additions), 删除行数(deletions), 和当日AI摘要(summary)。

        --- 完整日志开始 ---
        {full_log}
        --- 完整日志结束 ---

        你的任务是：阅读 *所有* 日志，生成一份单一的、压缩后的 "项目连续记忆" (Markdown 格式)。
        这份“记忆”的*唯一*目标是为明天的 AI 提供最高效、最节省上下文的历史背景。

        请严格遵守以下 "加权压缩" 规则：

        1.  **时间权重 (Recency)**:
            * **最近的 3-5 天**: 必须保留 *完整* 的 `summary` 细节，这是最高优先级的。
            * **过去 1-2 周**: 压缩相似的工作（例如 "修复了A, ...
        ... (Prompt 其余部分不变) ...

        请立即开始生成这份压缩后的 "项目连续记忆" (project_memory.md)：
        """

        try:
            # (V2.4 重构: 使用 self.model)
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
        (V2.4 重构: 转换为方法)
        (V2.4 升级)
        将技术摘要和项目历史，转换为面向公众的公众号文章，并利用 README 文件。
        """
        logger.info("✍️ 正在启动 AI '风格转换' 阶段 (生成公众号文章)...")

        # (V2.4 重构: 不再调用 _configure_genai，而是检查 self.model)
        if not self.model:
            return None

        # 构造 Prompt
        prompt = f"""
        你是一名资深的技术市场运营专家 (Tech Marketer) 和内容创作者。
        你的任务是为我们的项目撰写一篇面向用户和社区的“开发日志”或“公众号更新”。
        文章风格必须是：通俗易懂、充满热情、强调用户价值，而不是罗列技术术语。

        {f'''
        --- 项目背景与目标 (来自 README.md) ---
        这份文件定义了项目的使命、主要功能和市场定位。
        请确保你的文章风格和重点与其吻合。
        {project_readme}
        --- 项目背景结束 ---
        ''' if project_readme and project_readme.strip() else ''}

        为了帮助你写作，我将提供两份材料：

        1.  **项目历史与记忆 (浓缩版)**:
            ...
        2.  **今天的技术工作摘要**:
            ...

        请基于以上**所有材料**，撰写这篇公众号文章 (Markdown 格式)：
        ... (其余要求保持不变) ...
        """

        try:
            # (V2.4 重构: 使用 self.model)
            response = self.model.generate_content(prompt)
            logger.info("✅ AI '风格转换' 成功 (已包含项目背景)")
            return response.text
        except Exception as e:
            logger.error(f"❌ AI '风格转换' 失败: {e}")
            return None
