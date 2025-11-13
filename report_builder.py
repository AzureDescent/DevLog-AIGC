# report_builder.py
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from models import GitCommit
import markdown
import os

# (V3.3) 导入 SCRIPT_BASE_PATH 用于定位模板
from config import GitReportConfig, SCRIPT_BASE_PATH

logger = logging.getLogger(__name__)


def generate_text_report(commits: List[GitCommit], stats: Dict[str, Any]) -> str:
    """生成文本格式的报告"""
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


def get_css_styles() -> str:
    """
    (V3.3 修改)
    返回CSS样式 - 从 templates/styles.css 文件读取
    """
    css_path = os.path.join(SCRIPT_BASE_PATH, "templates", "styles.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"❌ (V3.3) CSS 模板文件未找到: {css_path}")
        return "/* CSS 模板文件未找到 */"
    except Exception as e:
        logger.error(f"❌ (V3.3) 加载 CSS 模板失败: {e}")
        return f"/* 加载 CSS 模板失败: {e} */"


def generate_html_header() -> str:
    """生成HTML头部"""
    return f"""
        <div class="header">
            <h1 style="color: #2c3e50; margin-bottom: 10px;">📊 Git工作日报</h1>
            <p style="color: #7f8c8d; font-size: 1.1em;">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    """


def generate_html_stats(commits: List[GitCommit], stats: Dict[str, Any]) -> str:
    """生成HTML统计部分和文件变更列表"""
    authors = set(commit.author for commit in commits) if commits else set()

    # 文件变更列表 HTML
    file_list_html = ""
    if stats.get("file_stats"):
        file_list_html = """
        <div class="file-list">
            <h3 style="color: #667eea; margin-top: 0;">📁 文件变更详情 (合并统计)</h3>
            <table class="file-table">
                <thead>
                    <tr>
                        <th>文件名</th>
                        <th>新增行数</th>
                        <th>删除行数</th>
                    </tr>
                </thead>
                <tbody>
        """
        for file_stat in stats["file_stats"]:
            file_list_html += f"""
                    <tr>
                        <td>{file_stat.filename}</td>
                        <td class="file-add">+{file_stat.additions}</td>
                        <td class="file-del">-{file_stat.deletions}</td>
                    </tr>
            """
        file_list_html += """
                </tbody>
            </table>
        </div>
        """

    # 总统计信息 HTML
    stats_html = f"""
        <div class="stats">
            <h2 style="margin: 0; color: white;">📈 统计信息</h2>
            <p style="font-size: 1.2em; margin: 10px 0;">
                今日提交数量: <strong style="font-size: 1.4em;">{len(commits)}</strong>
            </p>
            <p style="margin: 5px 0;">
                涉及作者: <strong>{', '.join(authors) if authors else '无'}</strong>
            </p>
            <p style="margin: 5px 0;">
                代码变更: <strong>+{stats['additions']} -{stats['deletions']}</strong> (修改文件: {stats['files_changed']})
            </p>
        </div>
    """

    # 将统计信息和文件列表合并返回
    return stats_html + file_list_html


def generate_html_commits(commits: List[GitCommit]) -> str:
    """生成HTML提交列表"""
    if not commits:
        return """
            <div class="empty-state">
                <h3>📭 没有找到提交记录</h3>
                <p>可能是以下原因：</p>
                <ul style="text-align: left; display: inline-block;">
                    <li>今天没有提交</li>
                    <li>Git仓库路径不正确</li>
                    <li>时间范围设置问题</li>
                </ul>
            </div>
        """

    # 按作者分组
    authors_commits = {}
    for commit in commits:
        authors_commits.setdefault(commit.author, []).append(commit)

    commits_html = '<h3 style="color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px;">📝 提交历史</h3>'

    for author, author_commits in authors_commits.items():
        commits_html += f"""
            <div class="author-section">
                <div class="author-header">👤 {author} ({len(author_commits)} 个提交)</div>
        """

        for i, commit in enumerate(author_commits, 1):
            commits_html += f"""
                <div class="commit">
                    <span class="commit-number">{i}</span>
                    <span class="graph">{commit.graph}</span>
                    <span class="hash">{commit.hash}</span>
                    <div class="message">{commit.message}</div>
                    <div>
                        <span class="time">🕒 {commit.time}</span>
                        {f'| <span class="branch">🌿 {commit.branch}</span>' if commit.has_branch else ''}
                    </div>
                </div>
            """

        commits_html += "</div>"

    return commits_html


def generate_html_ai_summary(ai_summary: Optional[str]) -> str:
    """生成 AI 摘要的 HTML 块 (Markdown 渲染)"""
    if not ai_summary:
        return ""

    html_summary = markdown.markdown(ai_summary, extensions=["fenced_code", "tables"])

    return f"""
        <div class="ai-summary">
            <h2 style="margin-top: 0; color: #667eea;">🤖 AI 工作摘要</h2>

            <div class="markdown-body">
                {html_summary}
            </div>
        </div>
    """


def generate_html_report(
    commits: List[GitCommit],
    stats: Dict[str, Any],
    ai_summary: Optional[str],
) -> str:
    """
    (V3.3 修改)
    生成HTML格式的可视化报告 - 从 templates/report.html.tpl 加载骨架
    """

    # (V3.3) 从文件加载 HTML 模板
    tpl_path = os.path.join(SCRIPT_BASE_PATH, "templates", "report.html.tpl")
    try:
        with open(tpl_path, "r", encoding="utf-8") as f:
            html_template = f.read()
    except FileNotFoundError:
        logger.error(f"❌ (V3.3) HTML 模板文件未找到: {tpl_path}")
        return f"<h1>错误：HTML 模板文件未找到 ({tpl_path})</h1>"
    except Exception as e:
        logger.error(f"❌ (V3.3) 加载 HTML 模板失败: {e}")
        return f"<h1>错误：加载 HTML 模板失败: {e}</h1>"

    # (V3.3) 注入内容到模板
    return html_template.format(
        title=f"Git工作日报 - {datetime.now().strftime('%Y-%m-%d')}",
        css=get_css_styles(),
        header=generate_html_header(),
        ai_summary_section=generate_html_ai_summary(ai_summary),
        stats_section=generate_html_stats(commits, stats),
        commits_section=generate_html_commits(commits),
    )


def save_html_report(html_content: str, config: GitReportConfig) -> Optional[str]:
    """
    (V3.1 修改) 保存HTML报告到文件
    - 使用 config.PROJECT_DATA_PATH 组合完整路径
    """
    filename = f"{config.OUTPUT_FILENAME_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    # --- (V3.1) 核心修改 ---
    # 使用项目专属路径，而不是 V3.0 的脚本根路径
    full_path = os.path.join(config.PROJECT_DATA_PATH, filename)

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"✅ HTML报告已保存: {full_path}")
        return full_path
    except Exception as e:
        logger.error(f"❌ 保存HTML报告失败 ({full_path}): {e}")
        return None
