# data_sources/factory.py
import logging
from context import RunContext
from .base import DataSource
from .local_git import LocalGitDataSource
from .github_api import GitHubAPIDataSource  # <--- 导入新类

logger = logging.getLogger(__name__)


def get_data_source(context: RunContext) -> DataSource:
    """
    [V4.5] 数据源工厂
    [V4.8] 支持 GitHub URL 自动识别
    """
    path = context.repo_path.lower()

    # 判断是否为远程 URL
    if (
        path.startswith("http://")
        or path.startswith("https://")
        or path.startswith("git@")
    ):
        logger.info("🔌 [Factory] 检测到远程 URL，初始化数据源: GitHub API")
        return GitHubAPIDataSource(context)

    logger.info("🔌 [Factory] 初始化数据源: Local Git")
    return LocalGitDataSource(context)
