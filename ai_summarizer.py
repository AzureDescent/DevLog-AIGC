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


def get_ai_summary(config: GitReportConfig, text_report: str) -> Optional[str]:
    """使用 AI 生成工作摘要"""
    logger.info("🤖 正在调用 AI 生成摘要...")

    if not config.AI_API_KEY:
        logger.warning("❌ 未配置 GOOGLE_API_KEY 环境变量，跳过 AI 摘要")
        return None

    try:
        genai.configure(api_key=config.AI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        你是一名资深的技术团队主管。
        以下是今天团队的 Git 提交日志和代码变更统计（原始数据）：
        --- 原始数据开始 ---
        {text_report}
        --- 原始数据结束 ---
        请你基于以上原始数据，撰写一份结构清晰、重点突出、人类可读的工作日报摘要。
        要求：
        1.  **总体概览**: 简要总结今天的主要进展、提交总数和代码变更情况。
        2.  **按模块/功能/作者总结**: 不要只是罗列 commit，而是将相关的工作合并归类。
        3.  **高亮亮点**: 指出任何重大的功能上线、关键修复或需要注意的变更。
        4.  **输出格式**: 使用 Markdown 格式化，使其易于阅读。
        """

        response = model.generate_content(prompt)
        logger.info("✅ AI 摘要生成成功")
        return response.text

    except Exception as e:
        logger.error(f"❌ AI 摘要生成失败: {e}")
        return None
