# pdf_converter.py
"""
[V3.7] PDF 转换器模块
- 负责将 V3.6 生成的 Markdown 文章转换为 PDF
- 使用 markdown 库转为 HTML
- (V3.7-Subprocess 修正版) 使用 subprocess 调用 PrinceXML 可执行文件
"""

import logging
import os
import markdown
import subprocess  # <--- [V3.7 修正] 导入 subprocess
from typing import Optional

# (V4.0) 导入 RunContext
from context import RunContext

logger = logging.getLogger(__name__)


def convert_md_to_pdf(article_md_path: str, context: RunContext) -> Optional[str]:
    """
    (V4.0 重构) 将 Markdown 文件转换为 PDF。
    - 接收 RunContext
    """

    try:
        # 1. 定义路径
        # (V4.0) 从 global_config 获取 SCRIPT_BASE_PATH
        css_path = os.path.join(
            context.global_config.SCRIPT_BASE_PATH, "templates", "pdf_style.css"
        )
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

        # 5. 构建完整的 HTML 文档 (用于 Prince 的 stdin)
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

        # 6. [V3.7 修正] 调用 PrinceXML CLI

        # 构建命令：
        # "prince" - 可执行文件
        # "-" - 从 stdin 读取 HTML
        # "-o <path>" - 指定输出文件
        # "--style <path>" - 应用 CSS
        command = ["prince", "-", "-o", pdf_output_path, "--style", css_path]

        logger.info(f"    (Prince CLI) 正在执行命令...")
        # (为日志隐藏完整命令，因为它可能很长，但保留关键部分)
        logger.info(f"    (Prince CLI) -> prince -o {pdf_output_path} --style ...")

        # 启动子进程
        p = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # 将 HTML 字符串 (编码为 utf-8) 发送到进程的 stdin
        # Popen.communicate 会发送数据、关闭 stdin、等待进程结束
        outs, errs = p.communicate(full_html_doc.encode("utf-8"))

        # 7. 检查结果
        if p.returncode != 0:
            # PrinceXML 执行失败
            logger.error(
                f"❌ (V3.7) PrinceXML CLI 失败 (Return Code: {p.returncode})。"
            )
            # Stderr 包含了 Prince 的错误信息
            logger.error(f"   Stderr: {errs.decode('utf-8')}")
            return None

        # 8. 检查输出文件
        if os.path.exists(pdf_output_path):
            logger.info(f"   (Prince CLI) Stdout: {outs.decode('utf-8')}")
            return pdf_output_path
        else:
            logger.error(
                f"❌ (V3.7) PrinceXML 运行成功，但输出文件未找到: {pdf_output_path}"
            )
            return None

    except FileNotFoundError:
        # 这是最关键的错误：如果 "prince" 命令找不到
        logger.error("❌ (V3.7) 'prince' command not found.")
        logger.error("   请确保 PrinceXML 已正确安装，并且 'prince' (或 'prince.exe')")
        logger.error("   位于您系统的 PATH 环境变量中。")
        return None
    except Exception as e:
        logger.error(
            f"❌ (V3.7) PDF 转换 (subprocess) 时发生未知错误: {e}", exc_info=True
        )
        return None
