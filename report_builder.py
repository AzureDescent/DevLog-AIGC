# report_builder.py
"""
[V4.2] 报告生成器 - Jinja2 模板引擎重构版
负责准备数据上下文，并调用 Jinja2 模板渲染 HTML。
"""
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models import GitCommit
from config import GlobalConfig
from context import RunContext

logger = logging.getLogger(__name__)


def generate_text_report(commits: List[GitCommit], stats: Dict[str, Any]) -> str:
    """
    生成纯文本格式的报告 (用于终端输出或邮件正文回退)。
    (保留 V3.3 逻辑，未改动)
    """
    lines = [
        "=" * 80,
        "                            Git工作汇总",
        "=" * 80,
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"提交数量: {len(commits)}",
        f"代码变更: +{stats['additions']} -{stats['deletions']} (修改文件: {stats['files_changed']})",
        "",
    ]
    if not commits:
        lines.append("⚠️  未找到提交记录")
    else:
        authors_commits = {}
        for commit in commits:
            authors_commits.setdefault(commit.author, []).append(commit)
        for author, author_commits in authors_commits.items():
            lines.append(f"作者: {author} ({len(author_commits)} 个提交)")
            lines.append("-" * 40)
            for commit in author_commits:
                branch_info = f" ({commit.branch})" if commit.has_branch else ""
                line = f"{commit.graph} {commit.hash}{branch_info} - {commit.message} ({commit.time})"
                lines.append(line)
            lines.append("")
    if stats["file_stats"]:
        lines.append("=" * 80)
        lines.append("                文件变更详情 (按文件合并统计)")
        lines.append("=" * 80)
        lines.append(f" {'新增':<6} | {'删除':<6} | 文件名")
        lines.append("-" * 80)
        for file_stat in stats["file_stats"]:
            lines.append(
                f" +{file_stat.additions:<5} | -{file_stat.deletions:<5} | {file_stat.filename}"
            )
        lines.append("-" * 80)
    lines.append("=" * 80)
    return "\n".join(lines)


def _get_css_styles(global_config: GlobalConfig) -> str:
    """读取 CSS 文件内容"""
    css_path = os.path.join(global_config.SCRIPT_BASE_PATH, "templates", "styles.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"❌ CSS 模板文件未找到: {css_path}")
        return "/* CSS 模板文件未找到 */"
    except Exception as e:
        logger.error(f"❌ 加载 CSS 模板失败: {e}")
        return f"/* 加载 CSS 模板失败: {e} */"


def generate_html_report(
    commits: List[GitCommit],
    stats: Dict[str, Any],
    ai_summary: Optional[str],
    global_config: GlobalConfig,
) -> str:
    """
    (V4.2 重构) 使用 Jinja2 模板引擎生成 HTML 报告。
    """
    # 1. 准备模板环境
    templates_dir = os.path.join(global_config.SCRIPT_BASE_PATH, "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # 2. 准备数据上下文 (Context)
    # 2.1 预处理 Markdown AI 摘要
    ai_summary_html = ""
    if ai_summary:
        ai_summary_html = markdown.markdown(
            ai_summary, extensions=["fenced_code", "tables", "sane_lists", "nl2br"]
        )

    # 2.2 按作者分组提交 (方便模板遍历)
    authors_commits = {}
    for commit in commits:
        authors_commits.setdefault(commit.author, []).append(commit)

    # 2.3 获取参与作者列表
    authors = list(authors_commits.keys())

    # 2.4 组装完整上下文
    template_context = {
        "title": f"Git工作日报 - {datetime.now().strftime('%Y-%m-%d')}",
        "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "css_content": _get_css_styles(global_config),
        "ai_summary_html": ai_summary_html,
        "total_commits": len(commits),
        "authors": authors,
        "stats": stats,
        "authors_commits": authors_commits,
        # 将 FileStat 等对象直接传给模板，模板可以直接访问其属性
    }

    # 3. 加载并渲染模板
    try:
        # 默认使用 report.html.j2，如果想更灵活，可以放入 config 中配置
        template_name = "report.html.j2"
        template = env.get_template(template_name)

        logger.info(f"🎨 正在渲染 Jinja2 模板: {template_name}")
        return template.render(**template_context)

    except Exception as e:
        logger.error(f"❌ Jinja2 模板渲染失败: {e}", exc_info=True)
        return f"<h1>错误：模板渲染失败</h1><pre>{e}</pre>"


def save_html_report(html_content: str, context: RunContext) -> Optional[str]:
    """保存HTML报告到文件 (保持 V4.0 逻辑)"""
    filename = f"{context.global_config.OUTPUT_FILENAME_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    full_path = os.path.join(context.project_data_path, filename)

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"✅ HTML报告已保存: {full_path}")
        return full_path
    except Exception as e:
        logger.error(f"❌ 保存HTML报告失败 ({full_path}): {e}")
        return None
