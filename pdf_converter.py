# pdf_converter.py
"""
[V3.7] PDF 转换器模块
- 负责将 V3.6 生成的 Markdown 文章转换为 PDF
- 使用 markdown 库转为 HTML
- 使用 prince 库调用 PrinceXML 进行最终转换
"""

import logging
import os
import markdown
from typing import Optional

try:
    import prince
except ImportError:
    print("错误: prince 库未安装。请运行: pip install prince")
    prince = None

# (V3.7) 导入 SCRIPT_BASE_PATH 用于定位 CSS
from config import GitReportConfig, SCRIPT_BASE_PATH

logger = logging.getLogger(__name__)


def convert_md_to_pdf(article_md_path: str, config: GitReportConfig) -> Optional[str]:
    """
    将 Markdown 文件转换为 PDF。

    Args:
        article_md_path (str): V3.6 生成的 PublicArticle_*.md 文件的完整路径。
        config (GitReportConfig): 配置对象 (未使用，但为未来扩展保留)。

    Returns:
        Optional[str]: 成功则返回 PDF 文件的路径，失败则返回 None。
    """
    if not prince:
        logger.error("❌ (V3.7) Prince 库未加载。无法执行 PDF 转换。")
        return None

    try:
        # 1. 定义路径
        css_path = os.path.join(SCRIPT_BASE_PATH, "templates", "pdf_style.css")
        pdf_output_path = article_md_path.replace(".md", ".pdf")

        # 2. 检查 CSS
        if not os.path.exists(css_path):
            logger.error(f"❌ (V3.7) PDF CSS 文件未找到: {css_path}")
            return None

        # 3. 读取 MD 内容
        with open(article_md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 4. MD -> HTML 片段
        html_fragment = markdown.markdown(
            md_content, extensions=["fenced_code", "tables"]
        )

        # 5. 构建完整的 HTML 文档
        #    (PrinceXML 需要完整的 HTML，<head> 中链接 CSS 是不可靠的，
        #     使用 Prince 的 style_sheets 参数是最佳实践)
        full_html_doc = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Git Report Article</title>
        </head>
        <body>
            <div class="markdown-body">
                {html_fragment}
            </div>
        </body>
        </html>
        """

        # 6. 调用 PrinceXML
        logger.info(f"    (PrinceXML) 正在使用 CSS: {css_path}")
        logger.info(f"    (PrinceXML) 正在生成 PDF: {pdf_output_path}")

        p = prince.Prince(style_sheets=[css_path])
        success = p.convert_string_to_file(full_html_doc, pdf_output_path)

        if not success:
            logger.error("❌ (V3.7) Prince.convert_string_to_file 失败。")
            return None

        # 7. 检查输出
        if os.path.exists(pdf_output_path):
            return pdf_output_path
        else:
            logger.error(f"❌ (V3.7) Prince 调用成功，但 PDF 文件未在预期位置找到。")
            return None

    except FileNotFoundError as e:
        logger.error(f"❌ (V3.7) PDF 转换失败: 文件未找到 {e}")
        return None
    except Exception as e:
        logger.error(f"❌ (V3.7) PDF 转换时发生未知错误: {e}", exc_info=True)
        return None
