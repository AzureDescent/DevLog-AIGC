# report_builder.py
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from models import GitCommit

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
    """返回CSS样式"""
    return """
        body {
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        /* --- V1.1 START: 增加 AI 摘要区域样式 --- */
        .ai-summary {
            background: #fdfdfd;
            border: 1px solid #eee;
            border-left: 5px solid #667eea;
            padding: 20px 25px;
            margin-bottom: 30px;
            border-radius: 8px;
            font-family: 'Arial', sans-serif; /* AI 摘要使用更易读的非等宽字体 */
            line-height: 1.6;
            color: #333;
        }
        /* --- V1.1 END --- */

        .commit {
            padding: 15px;
            margin: 10px 0;
            border-left: 5px solid #667eea;
            background: #f8f9fa;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        .commit:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .hash {
            color: #e74c3c;
            font-weight: bold;
            font-family: monospace;
        }
        .message {
            color: #2c3e50;
            font-size: 1.1em;
            margin: 5px 0;
        }
        .time {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        .author {
            color: #3498db;
            font-weight: bold;
        }
        .branch {
            color: #27ae60;
            font-style: italic;
        }
        .graph {
            color: #95a5a6;
            font-family: monospace;
            margin-right: 10px;
        }
        .stats {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 25px 0;
            text-align: center;
        }
        .commit-number {
            background: #e74c3c;
            color: white;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-right: 10px;
            font-weight: bold;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
            font-size: 1.2em;
        }
        .author-section {
            margin-bottom: 30px;
        }
        .author-header {
            background: #ecf0f1;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-weight: bold;
            color: #2c3e50;
        }
        /* 新增文件变更列表样式 */
        .file-list {
            text-align: left;
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fff;
        }
        .file-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95em;
        }
        .file-table th, .file-table td {
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
            text-align: left;
        }
        .file-table th {
            background: #f1f1f1;
            font-weight: bold;
            color: #333;
        }
        .file-add {
            color: #27ae60; /* 绿色 */
            font-weight: bold;
        }
        .file-del {
            color: #e74c3c; /* 红色 */
            font-weight: bold;
        }
        """


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
    """生成 AI 摘要的 HTML 块"""
    if not ai_summary:
        return ""
    return f"""
        <div class="ai-summary">
            <h2 style="margin-top: 0; color: #667eea;">🤖 AI 工作摘要</h2>
            <pre style="white-space: pre-wrap; font-family: inherit; font-size: 1.05em; background: #f9f9f9; padding: 15px; border-radius: 5px; border: 1px solid #eee;">{ai_summary}</pre>
        </div>
    """


def generate_html_report(
    commits: List[GitCommit],
    stats: Dict[str, Any],
    ai_summary: Optional[str],
) -> str:
    """生成HTML格式的可视化报告"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <meta charset="utf-8">
        <style>{css}</style>
    </head>
    <body>
        <div class="container">
            {header}
            {ai_summary_section}
            {stats_section}
            {commits_section}
        </div>
    </body>
    </html>
    """
    return html_template.format(
        title=f"Git工作日报 - {datetime.now().strftime('%Y-%m-%d')}",
        css=get_css_styles(),
        header=generate_html_header(),
        ai_summary_section=generate_html_ai_summary(ai_summary),
        stats_section=generate_html_stats(commits, stats),
        commits_section=generate_html_commits(commits),
    )


def save_html_report(html_content: str, filename_prefix: str) -> Optional[str]:
    """保存HTML报告到文件"""
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"✅ HTML报告已保存: {filename}")
        return filename
    except Exception as e:
        logger.error(f"❌ 保存HTML报告失败: {e}")
        return None
