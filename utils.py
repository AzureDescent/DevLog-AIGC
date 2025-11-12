# utils.py
import logging
import sys
import os


# 将日志配置移到这里，作为一个可被调用的函数
def setup_logging():
    """配置全局日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def open_report_in_browser(filename: str):
    """在浏览器中打开报告"""
    logger = logging.getLogger(__name__)
    try:
        if os.name == "nt":  # Windows
            os.startfile(filename)
        elif os.name == "posix":  # macOS/Linux
            if sys.platform == "darwin":
                os.system(f'open "{filename}"')
            else:
                os.system(f'xdg-open "{filename}"')
        logger.info(f"🌐 已在浏览器中打开报告: {filename}")
    except Exception as e:
        logger.warning(f"无法自动打开报告，请手动打开: {filename}, 错误: {e}")
