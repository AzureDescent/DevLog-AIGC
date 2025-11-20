# data_sources/github_api.py
import logging
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

# 第三方库
try:
    from github import Github, GithubException
    from github.Repository import Repository
    from github.Commit import Commit
except ImportError:
    Github = None

from .base import DataSource
from models import GitCommit, FileStat
from context import RunContext
from config import GlobalConfig

logger = logging.getLogger(__name__)


class GitHubAPIDataSource(DataSource):
    """
    [V4.8] GitHub 远程数据源实现
    使用 PyGithub 直接访问远程仓库，无需本地 git clone。
    """

    def __init__(self, context: RunContext):
        self.context = context
        self.global_config = context.global_config
        self.repo: Optional[Repository] = None

        if not Github:
            raise ImportError(
                "请安装 PyGithub 库以使用远程仓库功能: pip install PyGithub"
            )

        # 初始化 GitHub 客户端
        token = self.global_config.GITHUB_TOKEN
        if not token:
            logger.warning(
                "⚠️ 未配置 GITHUB_TOKEN，API 请求可能会受到严格限制 (60次/小时)。建议在 .env 中配置。"
            )
            self.client = Github()  # 匿名访问
        else:
            self.client = Github(token)

    def _parse_repo_name(self, url: str) -> Optional[str]:
        """从 URL 中解析 owner/repo"""
        # 支持 https://github.com/owner/repo 和 git@github.com:owner/repo.git
        try:
            if url.startswith("git@"):
                # git@github.com:owner/repo.git -> owner/repo
                return url.split(":")[1].replace(".git", "")

            parsed = urlparse(url)
            path = parsed.path.strip("/")
            if path.endswith(".git"):
                path = path[:-4]
            return path
        except Exception:
            return None

    def _parse_since_arg(self, arg: str) -> datetime:
        """
        将 git log 的 --since 参数解析为 datetime 对象。
        目前支持简单的 'N day/hour ago' 格式。
        """
        # 默认回退：昨天
        default_since = datetime.now() - timedelta(days=1)

        if not arg:
            return default_since

        # 尝试提取数字和单位
        # 这里的 arg 通常是 '--since="1 day ago"' 这样的字符串
        match = re.search(
            r"(\d+)\s+(day|hour|week|month|year)s?\s+ago", arg, re.IGNORECASE
        )
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()

            delta = timedelta(days=1)
            if "hour" in unit:
                delta = timedelta(hours=num)
            elif "day" in unit:
                delta = timedelta(days=num)
            elif "week" in unit:
                delta = timedelta(weeks=num)
            elif "month" in unit:
                delta = timedelta(days=num * 30)
            elif "year" in unit:
                delta = timedelta(days=num * 365)

            return datetime.now() - delta

        return default_since

    def validate(self) -> bool:
        repo_name = self._parse_repo_name(self.context.repo_path)
        if not repo_name:
            logger.error(f"❌ 无法从 URL 解析仓库名称: {self.context.repo_path}")
            return False

        try:
            logger.info(f"🌐 正在连接 GitHub API: {repo_name} ...")
            self.repo = self.client.get_repo(repo_name)
            logger.info(
                f"✅ 成功连接远程仓库: {self.repo.full_name} ({self.repo.stargazers_count} stars)"
            )
            return True
        except GithubException as e:
            logger.error(
                f"❌ 无法访问 GitHub 仓库: {e.status} {e.data.get('message', '')}"
            )
            return False
        except Exception as e:
            logger.error(f"❌ GitHub 连接发生未知错误: {e}")
            return False

    def get_commits(self) -> List[GitCommit]:
        if not self.repo:
            return []

        # 1. 解析时间范围
        # context.commit_range_arg 类似于 '--since="1 day ago"'
        since_date = self._parse_since_arg(self.context.commit_range_arg)
        logger.info(
            f"📅 获取提交记录 (Since: {since_date.strftime('%Y-%m-%d %H:%M')})..."
        )

        # 2. 调用 API
        try:
            gh_commits = self.repo.get_commits(since=since_date)

            parsed_commits = []
            # 注意：GitHub API 是分页的，迭代会自动翻页
            # 我们设置一个安全上限，防止 API 耗尽
            max_limit = 100
            count = 0

            for c in gh_commits:
                if count >= max_limit:
                    logger.warning(f"⚠️ 达到 API 单次获取上限 ({max_limit})，停止获取。")
                    break

                # 转换模型
                # GitCommit(graph, hash, branch, message, time, author)
                # 远程模式下 graph 无法构建，branch 暂不追踪
                git_commit = GitCommit(
                    graph="*",
                    hash=c.sha[:7],
                    branch="",  # API 获取特定 commit 的 branch 比较昂贵，暂留空
                    message=c.commit.message.split("\n")[0],  # 只取首行
                    time=c.commit.author.date.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),  # 使用 commit time
                    author=c.commit.author.name,
                )
                parsed_commits.append(git_commit)
                count += 1

            return parsed_commits
        except Exception as e:
            logger.error(f"❌ 获取提交列表失败: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        # 注意：GitHub API 获取 commits 列表时，默认不包含 stats (additions/deletions)
        # 必须对每个 commit 再调用一次 get_commit(sha) 才能拿到 stats。
        # 这会消耗大量 API 额度。
        # 优化策略：我们只在 get_diff 时获取详情，或者在这里为了 stats 必须牺牲一下速度。

        # 为了节省额度，我们这里先返回空，改为在 Orchestrator 处理流程中，
        # 实际我们需要遍历 commits 来累加。
        # 由于架构设计，get_stats 是独立调用的。我们不得不重新遍历或者复用。
        # 鉴于 API 限制，我们这里做一个简化：
        # 真正的 stats 统计将在 get_diff (AI Map阶段) 中顺便完成，
        # 或者我们在这里只做简单的计数。

        # 为了保持兼容性，我们这里只能再次获取（但因为会有缓存，或者我们只获取最近几个）
        # 实际上，更好的做法是在 get_commits 里就顺便把 stats 拿了（但这需要 1+N 次请求）。

        # **折中方案**：
        # 仅返回一个占位符，具体的 diff 内容留给 get_diff 获取。
        # 真实的 add/del 统计在纯 API 模式下比较昂贵，我们暂时返回 0 或估计值。

        return {
            "additions": 0,  # 暂不支持批量获取，太慢
            "deletions": 0,
            "files_changed": 0,
            "file_stats": [],
        }

    def get_diff(self, commit_hash: str) -> Optional[str]:
        """
        获取单个 Commit 的 Diff。
        PyGithub 的 commit.files 提供了 patch 字段，这就是 diff。
        """
        if not self.repo:
            return None

        try:
            # 这里会消耗 1 次 API 请求
            full_commit = self.repo.get_commit(commit_hash)

            diff_text = []
            # 顺便我们可以统计 stats (但这无法回填给 get_stats 了)

            for f in full_commit.files:
                header = f"diff --git a/{f.filename} b/{f.filename}\n"
                header += f"--- a/{f.filename}\n+++ b/{f.filename}\n"
                patch = f.patch if f.patch else "(Binary file or too large)"
                diff_text.append(header + patch)

            return "\n".join(diff_text)

        except Exception as e:
            logger.error(f"❌ 获取 Diff 失败 ({commit_hash}): {e}")
            return None

    def get_readme(self) -> Optional[str]:
        if not self.repo:
            return None
        try:
            content_file = self.repo.get_readme()
            return content_file.decoded_content.decode("utf-8")
        except Exception as e:
            logger.warning(f"⚠️ 无法获取远程 README: {e}")
            return None
