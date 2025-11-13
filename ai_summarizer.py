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
def _configure_genai(config: GitReportConfig) -> Optional[genai.GenerativeModel]:
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
) -> Optional[str]:
    """
    (修改 "Reduce" 阶段)
    使用 AI 生成最终的工作摘要。
    """
    logger.info("🤖 正在调用 AI 生成*最终*摘要...")

    model = _configure_genai(config)  # (使用辅助函数)
    if not model:
        return None

    # (修改) V2.0: 更新 Prompt 以包含 diff 摘要
    prompt = f"""
    你是一名资深的技术团队主管。
    以下是今天团队的 Git 提交日志、代码变更统计（原始数据），
    以及（可选的）AI 对每条代码变更的逐条总结：

    --- 原始数据（Git 日志）开始 ---
    {text_report}
    --- 原始数据结束 ---

    {f'''
    --- AI 生成的逐条代码变更总结 ---
    {diff_summaries}
    --- 代码变更总结结束 ---
    ''' if diff_summaries and diff_summaries.strip() else ''}

    请你基于以上**所有信息**，撰写一份结构清晰、重点突出、人类可读的工作日报摘要。
    要求：
    1.  **总体概览**: 简要总结今天的主要进展、提交总数和代码变更情况。
    2.  **按模块/功能/作者总结**: 不要只是罗列 commit。
        (如果提供了 'AI 逐条总结'，请优先使用该信息来理解变更的 *真实内容*，而不是只看 commit message。)
    3.  **高亮亮点**: 指出任何重大的功能上线、关键修复或需要注意的变更。
    4.  **输出格式**: 使用 Markdown 格式化，使其易于阅读。
    """

    try:
        response = model.generate_content(prompt)
        logger.info("✅ AI 最终摘要生成成功")
        return response.text

    except Exception as e:
        logger.error(f"❌ AI 最终摘要生成失败: {e}")
        return None
