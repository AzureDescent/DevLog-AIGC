"""Git工作日报生成器
本脚本用于生成Git仓库的工作日报，包含提交历史和代码变更统计信息。
生成的报告包括文本格式和HTML可视化格式，支持按作者分组显示提交记录。
"""
"""下一步计划:
1. 增加AI分析功能，自动生成提交摘要和代码变更亮点。
2. 增加深色模式支持，提升视觉体验。
3. 增加邮件发送功能，自动将报告发送给相关人员。
4. 增加命令行参数支持，允许用户自定义时间范围和输出格式。
5. 增加图形化界面，提升用户交互体验。
6. 增加实时监控功能，自动生成每日或每周报告。"""

import subprocess
import re
from datetime import datetime
import os
import sys
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class GitReportConfig:
    """Git报告配置参数类"""

    TIME_RANGE: str = "1 day ago"
    GIT_LOG_FORMAT = 'git log --since="{time_range}" --graph --pretty=format:"%h|%d|%s|%cr|%an" --abbrev-commit'
    # 使用 --numstat 可以获取增删行数和文件名
    GIT_STATS_FORMAT = 'git log --since="{time_range}" --numstat --pretty=format:""'
    OUTPUT_FILENAME_PREFIX = "GitReport"


@dataclass
class GitCommit:
    """Git提交数据模型"""

    graph: str
    hash: str
    branch: str
    message: str
    time: str
    author: str

    @property
    def has_branch(self) -> bool:
        return bool(self.branch.strip())

    @property
    def is_merge_commit(self) -> bool:
        return self.message.lower().startswith("merge")


@dataclass
class FileStat:
    """文件变更统计数据模型"""

    additions: int
    deletions: int
    filename: str


class GitReporter:
    """Git工作报告生成器"""

    def __init__(self, time_range: Optional[str] = None):
        self.config = GitReportConfig()
        if time_range:
            self.config.TIME_RANGE = time_range
            logger.info(f"设置报告时间范围为: {self.config.TIME_RANGE}")

    def run_git_command(self, cmd: str, context: str = "执行Git命令") -> Optional[str]:
        """统一的Git命令执行函数"""
        try:
            logger.info(f"执行命令: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"{context}失败: {result.stderr}")
                return None

            logger.info(f"{context}成功，输出 {len(result.stdout.splitlines())} 行")
            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"{context}超时")
            return None
        except Exception as e:
            logger.error(f"{context}出错: {e}")
            return None

    def is_git_repository(self) -> bool:
        """检查当前目录是否为Git仓库"""
        try:
            result = subprocess.run(
                "git rev-parse --is-inside-work-tree",
                shell=True,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_git_log(self) -> Optional[str]:
        """获取Git提交历史"""
        cmd = self.config.GIT_LOG_FORMAT.format(time_range=self.config.TIME_RANGE)
        return self.run_git_command(cmd, "获取Git提交历史")

    def parse_single_commit(self, line: str) -> Optional[GitCommit]:
        """解析单行提交记录"""
        try:
            # 使用更精确的正则清理
            clean_line = re.sub(r"^[\*\|\\\/\s]+", "", line).strip()

            parts = [part.strip() for part in clean_line.split("|")]

            if len(parts) < 5:
                logger.warning(f"提交格式异常: {line}")
                return None

            return GitCommit(
                graph=line[0] if line and not line[0].isalnum() else "*",
                hash=parts[0],
                branch=parts[1],
                message=parts[2],
                time=parts[3],
                author=parts[4],
            )

        except Exception as e:
            logger.error(f"解析提交行失败 '{line}': {e}")
            return None

    def parse_git_log(self, log_output: str) -> List[GitCommit]:
        """解析Git日志输出"""
        commits = []

        if not log_output or not log_output.strip():
            logger.warning("Git日志输出为空")
            return commits

        lines = [
            line.strip()
            for line in log_output.split("\n")
            if line.strip() and line.strip() != "*"
        ]
        logger.info(f"解析 {len(lines)} 行有效日志")

        for line in lines:
            commit = self.parse_single_commit(line)
            if commit:
                commits.append(commit)

        logger.info(f"成功解析 {len(commits)} 个提交")
        return commits

    # --- START: 新增/修改 get_git_stats 逻辑以捕获文件变更详情 ---
    def get_git_stats(self) -> Dict[str, Any]:
        """获取Git统计信息和文件变更详情"""
        stats = {
            "additions": 0,
            "deletions": 0,
            "files_changed": 0,
            "file_stats": [],  # 新增：存储 FileStat 对象的列表
        }

        output = self.run_git_command(
            self.config.GIT_STATS_FORMAT.format(time_range=self.config.TIME_RANGE),
            "获取Git统计信息",
        )

        if not output:
            return stats

        # 使用字典来合并同一文件的多次变更，确保唯一性
        file_changes: Dict[str, FileStat] = {}

        try:
            for line in output.strip().split("\n"):
                if line.strip():
                    parts = line.split("\t")
                    # --numstat 的输出格式是: <additions>\t<deletions>\t<file>
                    if len(parts) == 3:
                        add = int(parts[0]) if parts[0].isdigit() else 0
                        delete = int(parts[1]) if parts[1].isdigit() else 0
                        filename = parts[2].strip()

                        # 累加总数
                        stats["additions"] += add
                        stats["deletions"] += delete

                        # 合并文件变更统计
                        if filename not in file_changes:
                            file_changes[filename] = FileStat(
                                additions=add, deletions=delete, filename=filename
                            )
                        else:
                            file_changes[filename].additions += add
                            file_changes[filename].deletions += delete

            stats["file_stats"] = list(file_changes.values())
            stats["files_changed"] = len(stats["file_stats"])

        except ValueError as e:
            logger.error(f"解析统计信息时出现数值错误: {e}")

        return stats

    # --- END: get_git_stats 逻辑修改 ---

    def generate_text_report(
        self, commits: List[GitCommit], stats: Dict[str, Any]
    ) -> str:
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
            # 按作者分组显示
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

        # --- 新增：文本报告中的文件变更列表 ---
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
        # --- 结束：文本报告文件变更列表 ---

        lines.append("=" * 80)
        return "\n".join(lines)

    # --- START: 修改 get_css_styles 添加文件列表样式 ---
    def get_css_styles(self) -> str:
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

    # --- END: 修改 get_css_styles ---

    def generate_html_header(self) -> str:
        """生成HTML头部"""
        return f"""
            <div class="header">
                <h1 style="color: #2c3e50; margin-bottom: 10px;">📊 Git工作日报</h1>
                <p style="color: #7f8c8d; font-size: 1.1em;">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """

    def generate_html_stats(
        self, commits: List[GitCommit], stats: Dict[str, Any]
    ) -> str:
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

    def generate_html_commits(self, commits: List[GitCommit]) -> str:
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

    def generate_html_report(
        self, commits: List[GitCommit], stats: Dict[str, Any]
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
                {stats_section}
                {commits_section}
            </div>
        </body>
        </html>
        """

        return html_template.format(
            title=f"Git工作日报 - {datetime.now().strftime('%Y-%m-%d')}",
            css=self.get_css_styles(),
            header=self.generate_html_header(),
            stats_section=self.generate_html_stats(commits, stats),
            commits_section=self.generate_html_commits(commits),
        )

    def generate_and_save_reports(
        self, commits: List[GitCommit], stats: Dict[str, Any]
    ) -> Optional[str]:
        """生成并保存报告文件"""
        # 传递 stats 字典给 generate_text_report
        text_report = self.generate_text_report(commits, stats)
        print("\n" + "=" * 50)
        print("📄 文本报告:")
        print("=" * 50)
        print(text_report)

        # 生成并保存HTML报告
        html_report = self.generate_html_report(commits, stats)
        filename = f"{self.config.OUTPUT_FILENAME_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_report)
            logger.info(f"✅ HTML报告已保存: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ 保存HTML报告失败: {e}")
            return None

    def open_report_in_browser(self, filename: str):
        """在浏览器中打开报告"""
        try:
            if os.name == "nt":  # Windows
                os.startfile(filename)
            elif os.name == "posix":  # macOS/Linux
                if sys.platform == "darwin":
                    os.system(f'open "{filename}"')
                else:
                    os.system(f'xdg-open "{filename}"')
            logger.info("🌐 已在浏览器中打开报告")
        except Exception as e:
            logger.warning(f"无法自动打开报告，请手动打开: {filename}, 错误: {e}")

    def main(self):
        """主执行函数"""
        logger.info("🚀 正在生成Git工作可视化报告...")
        print("=" * 50)

        # --- 新增：命令行参数解析，实现动态时间范围 (可选的额外改进) ---
        if len(sys.argv) > 1:
            self.__init__(time_range=" ".join(sys.argv[1:]))
        # -------------------------------------------------------------

        # 检查当前目录是否为Git仓库
        if not self.is_git_repository():
            logger.error("❌ 当前目录不是Git仓库")
            print("💡 请确保在Git仓库目录中运行此脚本")
            return

        # 获取并解析Git日志
        log_output = self.get_git_log()

        if not log_output:
            logger.error("❌ 未获取到Git提交记录")
            print("💡 可能的原因:")
            print("   - 今天没有提交")
            print("   - Git命令执行环境问题")
            return

        commits = self.parse_git_log(log_output)
        # 获取包含文件详情的统计信息
        stats = self.get_git_stats()
        stats["total_commits"] = len(commits)

        # 生成并保存报告
        filename = self.generate_and_save_reports(commits, stats)
        if not filename:
            return

        # 显示统计信息
        print("\n📊 代码变更统计:")
        print(f"   📈 新增行数: {stats['additions']}")
        print(f"   📉 删除行数: {stats['deletions']}")
        print(f"   📁 修改文件: {stats['files_changed']} (详情已包含在报告中)")
        print(f"   👥 参与作者: {len(set(commit.author for commit in commits))}")

        # 在默认浏览器中打开报告
        self.open_report_in_browser(filename)


def main():
    """主函数入口"""
    reporter = GitReporter()
    reporter.main()


if __name__ == "__main__":
    main()
