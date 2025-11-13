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


# --- (新增) V2.0 START ---
# 辅助函数，用于配置 GenAI，避免代码重复
def _configure_genai(config: GitReportConfig) -> Optional[genai.GenerativeModel]:  # type: ignore
    if not config.AI_API_KEY:
        logger.warning("❌ 未配置 GOOGLE_API_KEY 环境变量")
        return None
    try:
        genai.configure(api_key=config.AI_API_KEY)  # type: ignore
        model = genai.GenerativeModel("gemini-2.5-flash")  # type: ignore
        return model
    except Exception as e:
        logger.error(f"❌ GenAI 配置失败: {e}")
        return None


def get_single_diff_summary(
    config: GitReportConfig, diff_content: str
) -> Optional[str]:
    """
    (新增 "Map" 阶段)
    使用 AI 单独总结一个 diff 的核心逻辑变更。
    """
    logger.info("🤖 正在调用 AI 总结单个 Diff...")
    model = _configure_genai(config)
    if not model:
        return None

    # (方法一的补充：在发送前再次过滤超大 diff)
    # (gemini-2.5-flash 的上下文约为 1M tokens,
    # 但我们应设置一个更合理的业务上限，例如 100k 字符)
    if len(diff_content) > 100000:
        logger.warning(f"⚠️ Diff 内容过长 ({len(diff_content)} chars)，跳过 AI 总结。")
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
        response = model.generate_content(prompt)
        # 清理总结，确保是单行
        summary = response.text.strip().replace("\n", " ")
        logger.info(f"✅ 单个 Diff 总结成功: {summary}")
        return summary
    except Exception as e:
        logger.error(f"❌ 单个 Diff 总结失败: {e}")
        return None


# --- (新增) V2.0 END ---


def get_ai_summary(
    config: GitReportConfig,
    text_report: str,
    # (修改) V2.0: 接收 "Map" 阶段的结果
    diff_summaries: Optional[str] = None,
    previous_summary: Optional[str] = None,
) -> Optional[str]:
    """
    (修改 "Reduce" 阶段)
    使用 AI 生成最终的工作摘要。
    """
    logger.info("🤖 正在调用 AI 生成*最终*摘要...")

    model = _configure_genai(config)  # (使用辅助函数)
    if not model:
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
        response = model.generate_content(prompt)
        logger.info("✅ AI 最终摘要生成成功 (已包含历史上下文)")
        return response.text

    except Exception as e:
        logger.error(f"❌ AI 最终摘要生成失败: {e}")
        return None


# --- (新增) V2.2 START: 记忆蒸馏 ---
def distill_project_memory(config: GitReportConfig) -> Optional[str]:
    """
    (新增 "记忆蒸馏" 阶段)
    读取 *所有* 的历史日志，生成一个浓缩的、有权重的记忆文件。
    """
    logger.info("🧠 正在启动 AI '记忆蒸馏' 阶段...")

    # 1. 读取“地基”日志
    try:
        with open(config.PROJECT_LOG_FILE, "r", encoding="utf-8") as f:
            full_log = f.read()
    except FileNotFoundError:
        logger.info("ℹ️ 未找到项目日志 (project_log.jsonl)，将创建新记忆。")
        return None  # 没有历史，无需蒸馏

    if not full_log.strip():
        logger.info("ℹ️ 项目日志为空，无需蒸馏。")
        return None

    model = _configure_genai(config)
    if not model:
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
        * **过去 1-2 周**: 压缩相似的工作（例如 "修复了A, 修复了B" -> "完成了多项bug修复"），但要保留关键的功能点。
        * **更早 (2周前)**: 必须 *极度* 压缩。只保留里程碑式的成就（例如 "完成了V1.0重构", "上线了支付系统"）。

    2.  **变更权重 (Importance)**:
        * 使用 `additions` 和 `deletions` 作为“重要性”的参考。
        * 一个 `additions: 1000, deletions: 500` 的条目（即使在 1 个月前）可能是一个需要保留的“里程碑”。
        * 一个 `additions: 5, deletions: 5` 的条目（例如 "修复拼写错误"）如果超过 1 周，应 *立即丢弃*，不要在记忆中提及。

    3.  **连续性 (Continuity)**:
        * 你的输出必须是一个连贯的叙事。使用 Markdown 标题（例如 `## 近期进展` 和 `### 历史里程碑`）来组织结构。
        * 不要只是罗列，要体现“演进”。例如："在(里程碑)的基础上，团队近期专注于(近期进展)..."

    请立即开始生成这份压缩后的 "项目连续记忆" (project_memory.md)：
    """

    try:
        response = model.generate_content(prompt)
        logger.info("✅ AI '记忆蒸馏' 成功")
        return response.text
    except Exception as e:
        logger.error(f"❌ AI '记忆蒸馏' 失败: {e}")
        return None


# --- (新增) V2.2 END ---
