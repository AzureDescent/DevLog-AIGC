# data_sources/local_git.py
import logging
import os
from typing import List, Dict, Any, Optional

from .base import DataSource
from models import GitCommit
from context import RunContext
import git_utils  # 复用现有的 git_utils

logger = logging.getLogger(__name__)


class LocalGitDataSource(DataSource):
    """
    [V4.5] 本地 Git 数据源实现。
    通过调用 git 命令行工具分析本地仓库。
    """

    def __init__(self, context: RunContext):
        self.context = context

    def validate(self) -> bool:
        if not os.path.exists(self.context.repo_path):
            logger.error(f"❌ 路径不存在: {self.context.repo_path}")
            return False
        if not git_utils.is_git_repository(self.context.repo_path):
            logger.error(f"❌ 指定路径不是 Git 仓库: {self.context.repo_path}")
            return False
        return True

    def get_commits(self) -> List[GitCommit]:
        log_output = git_utils.get_git_log(self.context)
        if not log_output:
            return []
        return git_utils.parse_git_log(log_output)

    def get_stats(self) -> Dict[str, Any]:
        return git_utils.get_git_stats(self.context)

    def get_diff(self, commit_hash: str) -> Optional[str]:
        return git_utils.get_commit_diff(self.context, commit_hash)

    def get_readme(self) -> Optional[str]:
        readme_path = os.path.join(self.context.repo_path, "README.md")
        try:
            if os.path.exists(readme_path):
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read()
                logger.info(f"✅ [DataSource] 成功加载 README: {readme_path}")
                return content
            else:
                logger.warning(f"⚠️ [DataSource] 未找到 README.md")
                return None
        except Exception as e:
            logger.error(f"❌ [DataSource] 读取 README 失败: {e}")
            return None
