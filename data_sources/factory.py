# data_sources/factory.py
import logging
from context import RunContext
from .base import DataSource
from .local_git import LocalGitDataSource

logger = logging.getLogger(__name__)


def get_data_source(context: RunContext) -> DataSource:
    """
    [V4.5] 数据源工厂
    根据 RunContext 中的配置决定实例化哪种 DataSource。
    目前默认返回 LocalGitDataSource。
    """
    # 未来扩展点：
    # if context.repo_path.startswith("https://github.com/"):
    #     return GitHubAPIDataSource(context)

    logger.info("🔌 [Factory] 初始化数据源: Local Git")
    return LocalGitDataSource(context)
