# pdf_converter.py
import logging
import os
import markdown
import subprocess
from typing import Optional
from context import RunContext

logger = logging.getLogger(__name__)


def convert_md_to_pdf(article_md_path: str, context: RunContext) -> Optional[str]:
    """
    [V4.7 优化版] 将 Markdown 转换为 PDF (PrinceXML)
    - 增强 Markdown 渲染扩展
    - 修复 CSS 路径问题
    """
    try:
        # 1. 准备路径
        css_path = os.path.join(
            context.global_config.SCRIPT_BASE_PATH, "templates", "pdf_style.css"
        )
        pdf_output_path = article_md_path.replace(".md", ".pdf")
        # [调试用] 保存一份中间 HTML 文件，方便检查渲染效果
        html_debug_path = article_md_path.replace(".md", ".html")

        if not os.path.exists(css_path):
            logger.error(f"❌ CSS 文件未找到: {css_path}")
            return None

        # 2. 读取 Markdown
        with open(article_md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 3. Markdown -> HTML (增强版)
        # 增加 'extra' (包含表格、脚注等), 'codehilite' (代码高亮), 'nl2br' (换行)
        html_fragment = markdown.markdown(
            md_content, extensions=["extra", "codehilite", "sane_lists", "nl2br"]
        )

        # 4. 读取 CSS 内容并直接嵌入 HTML
        # (PrinceXML 有时对外部 CSS 文件路径解析有问题，嵌入最稳妥)
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        # 5. 构建完整的 HTML 文档
        full_html_doc = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>DevLog Article</title>
            <style>
                {css_content}
            </style>
        </head>
        <body>
            <div class="markdown-body">
                {html_fragment}
            </div>
        </body>
        </html>
        """

        # [调试] 保存 HTML 文件到磁盘
        with open(html_debug_path, "w", encoding="utf-8") as f:
            f.write(full_html_doc)
        logger.info(f"📄 [调试] 中间 HTML 已保存: {html_debug_path}")

        # 6. 调用 PrinceXML
        # 注意：这里不再通过 --style 传 CSS，因为已经内嵌了
        command = ["prince", html_debug_path, "-o", pdf_output_path]

        logger.info(f"🖨️ 正在调用 PrinceXML 生成 PDF...")

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"❌ PrinceXML 失败: {result.stderr}")
            return None

        if os.path.exists(pdf_output_path):
            logger.info(f"✅ PDF 已生成: {pdf_output_path}")
            return pdf_output_path
        else:
            logger.error(f"❌ PDF 文件未生成 (未知错误)")
            return None

    except FileNotFoundError:
        logger.error(
            "❌ 系统未找到 'prince' 命令，请检查 Dockerfile 是否已正确安装 PrinceXML。"
        )
        return None
    except Exception as e:
        logger.error(f"❌ PDF 转换异常: {e}", exc_info=True)
        return None
