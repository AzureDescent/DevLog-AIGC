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

from dotenv import load_dotenv

load_dotenv()

import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

try:
    import google.generativeai as genai
except ImportError:
    print("错误: google-generativeai 库未安装。请运行: pip install google-generativeai")
    sys.exit(1)

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

    # --- V1.0+ MOD: 优先从 .env 读取配置 ---

    # AI 配置
    # (这行保持不变，它会自动读取 .env)
    AI_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")

    # 邮件(SMTP)配置
    # os.getenv("SMTP_SERVER", "...") 的意思是:
    # 尝试读取 "SMTP_SERVER" 变量，如果找不到，就使用 "smtp.example.com"
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = 587  # (通常不需要在 .env 中配置)
    SMTP_USER: str = os.getenv("SMTP_USER", "your-email@example.com")

    # 密码只从环境变量读取，绝不硬编码
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASS")
    # --- V1.0+ END MOD ---


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
    ) -> tuple[Optional[str], str]:  # 修复：使用 tuple 类型
        """生成并保存报告文件，并返回报告路径和文本内容"""

        # --- V1.0 MOD: 生成文本报告，但不打印 ---
        text_report = self.generate_text_report(commits, stats)
        # print("\n" + "=" * 50)
        # print("📄 文本报告:")
        # print("=" * 50)
        # print(text_report)
        # --- V1.0 END MOD ---

        # 生成并保存HTML报告
        html_report = self.generate_html_report(commits, stats)
        filename = f"{self.config.OUTPUT_FILENAME_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_report)
            logger.info(f"✅ HTML报告已保存: {filename}")

            # --- V1.0 MOD: 返回文件名和文本报告 ---
            return filename, text_report
            # --- V1.0 END MOD ---

        except Exception as e:
            logger.error(f"❌ 保存HTML报告失败: {e}")
            # --- V1.0 MOD: 返回 None 和 文本报告 ---
            return None, text_report
            # --- V1.0 END MOD ---

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

    def main(self, args: argparse.Namespace):  # --- V1.0 MOD: 接受 args 参数 ---
        """主执行函数"""

        # --- V1.0 MOD: 从 args 设置时间范围 ---
        self.config.TIME_RANGE = args.time
        logger.info(f"🚀 正在生成Git工作报告... 时间范围: {self.config.TIME_RANGE}")
        print("=" * 50)
        # --- V1.0 END MOD ---

        # (删除旧的 sys.argv 检查)

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

        # --- V1.0 START: 重构报告生成和 AI 调用流程 ---

        # 生成并保存报告
        html_filename, text_report = self.generate_and_save_reports(commits, stats)
        if not html_filename:
            logger.error("❌ HTML 报告文件生成失败，中止后续操作。")
            return

        # 生成 AI 摘要
        ai_summary = None
        if not args.no_ai:
            ai_summary = self.get_ai_summary(text_report)

        # 打印 AI 摘要或原始报告
        print("\n" + "=" * 50)
        if ai_summary:
            print("🤖 AI 工作摘要:")
            print("=" * 50)
            print(ai_summary)
        else:
            print("📄 原始文本报告 (AI未运行或生成失败):")
            print("=" * 50)
            print(text_report)
        print("=" * 50)

        # --- V1.0 END ---

        # 显示统计信息
        print("\n📊 代码变更统计:")
        print(f"   📈 新增行数: {stats['additions']}")
        print(f"   📉 删除行数: {stats['deletions']}")
        print(f"   📁 修改文件: {stats['files_changed']} (详情已包含在报告中)")
        print(f"   👥 参与作者: {len(set(commit.author for commit in commits))}")

        # 在默认浏览器中打开报告
        if not args.no_browser:  # V1.0 MOD: 增加浏览器打开控制
            self.open_report_in_browser(html_filename)

        # --- V1.0 START: 邮件发送逻辑 ---
        if args.email:
            logger.info("准备发送邮件...")
            # 优先使用 AI 摘要，如果失败则使用原始文本报告作为邮件正文
            email_body_content = ai_summary if ai_summary else text_report

            # (注意: 如果使用原始文本，邮件可读性会差，AI 摘要是最好的)
            if not ai_summary:
                logger.warning("AI 摘要不可用，将使用原始文本报告作为邮件正文。")

            self.send_email_report(args.email, email_body_content, html_filename)
        # --- V1.0 END ---

    # --- V1.0 START: 新增 AI 摘要方法 ---
    def get_ai_summary(self, text_report: str) -> Optional[str]:
        """使用 AI 生成工作摘要"""
        logger.info("🤖 正在调用 AI 生成摘要...")

        if not self.config.AI_API_KEY:
            logger.warning("❌ 未配置 GOOGLE_API_KEY 环境变量，跳过 AI 摘要")
            return None

        try:
            genai.configure(api_key=self.config.AI_API_KEY)
            model = genai.GenerativeModel(
                "gemini-2.5-flash"
            )  # 使用 Flash 模型，速度快成本低

            prompt = f"""
            你是一名资深的技术团队主管。
            以下是今天团队的 Git 提交日志和代码变更统计（原始数据）：

            --- 原始数据开始 ---
            {text_report}
            --- 原始数据结束 ---

            请你基于以上原始数据，撰写一份结构清晰、重点突出、人类可读的工作日报摘要。
            要求：
            1.  **总体概览**: 简要总结今天的主要进展、提交总数和代码变更情况。
            2.  **按模块/功能/作者总结**: 不要只是罗列 commit，而是将相关的工作（如 "用户登录模块"、"修复了 XXX bug"）合并归类。
            3.  **高亮亮点**: 指出任何重大的功能上线、关键修复或需要注意的变更。
            4.  **输出格式**: 使用 Markdown 格式化，使其易于阅读。
            """

            response = model.generate_content(prompt)

            logger.info("✅ AI 摘要生成成功")
            return response.text

        except Exception as e:
            logger.error(f"❌ AI 摘要生成失败: {e}")
            return None

    # --- V1.0 END ---

    # --- V1.0 START: 新增邮件发送方法 ---
    def send_email_report(
        self, recipient_email: str, ai_summary: str, html_report_path: str
    ):
        """发送包含 AI 摘要和 HTML 附件的邮件"""
        logger.info(f"📬 正在准备发送邮件至: {recipient_email}")

        if (
            not self.config.SMTP_SERVER
            or not self.config.SMTP_USER
            or not self.config.SMTP_PASSWORD
        ):
            logger.error(
                "❌ 邮件(SMTP)配置不完整 (服务器, 用户, 或密码未设置)，无法发送邮件。"
            )
            logger.error("💡 请检查 GitReportConfig 或 SMTP_PASS 环境变量。")
            return

        try:
            # 构造邮件
            msg = MIMEMultipart()
            msg["From"] = self.config.SMTP_USER
            msg["To"] = recipient_email
            msg["Subject"] = f"Git 工作日报 - {datetime.now().strftime('%Y-%m-%d')}"

            # 邮件正文 (使用 AI 摘要)
            # 我们使用 HTML 格式发送正文，以便 Markdown 换行生效
            html_body = f"""
            <html>
            <head></head>
            <body>
                <p>你好,</p>
                <p>以下是今日的 Git 工作 AI 摘要：</p>
                <hr>
                <pre style="font-family: monospace; white-space: pre-wrap; padding: 10px; background: #f4f4f4; border-radius: 5px;">
{ai_summary}
                </pre>
                <hr>
                <p>详细的 HTML 可视化报告已作为附件添加，请查收。</p>
                <p>-- 自动化报告系统</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            # 添加 HTML 报告作为附件
            with open(html_report_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(html_report_path)}",
            )
            msg.attach(part)

            # 发送邮件
            with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.starttls()  # 启用安全连接
                server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
                server.sendmail(self.config.SMTP_USER, recipient_email, msg.as_string())

            logger.info(f"✅ 邮件已成功发送至 {recipient_email}")

        except Exception as e:
            logger.error(f"❌ 发送邮件失败: {e}")

    # --- V1.0 END ---


def main():
    """主函数入口 (V1.0 重构：使用 argparse)"""

    # --- V1.0 START: 设置命令行参数 ---
    parser = argparse.ArgumentParser(description="Git 工作日报 AI 摘要生成器")

    parser.add_argument(
        "-t",
        "--time",
        type=str,
        default="1 day ago",
        help="Git log 的时间范围 (例如 '1 day ago', '2 weeks ago', '2025-10-01')",
    )

    parser.add_argument(
        "-e", "--email", type=str, help="[可选] 报告接收者的电子邮件地址"
    )

    parser.add_argument("--no-ai", action="store_true", help="[可选] 禁用 AI 摘要功能")

    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="[可选] 禁用自动在浏览器中打开 HTML 报告",
    )

    args = parser.parse_args()
    # --- V1.0 END ---

    reporter = GitReporter()

    # --- V1.0 MOD: 将解析后的参数传递给 main 方法 ---
    reporter.main(args)
    # --- V1.0 END ---


if __name__ == "__main__":
    main()
