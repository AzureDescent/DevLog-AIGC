# data_sources/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from models import GitCommit


class DataSource(ABC):
    """
    [V4.5] 数据源抽象基类
    定义了获取项目变更数据的标准接口，屏蔽了底层是本地 Git 还是远程 API 的差异。
    """

    @abstractmethod
    def validate(self) -> bool:
        """
        验证数据源是否可用。
        例如：本地路径是否存在且为 Git 仓库，或者 API Key 是否有效。
        """
        pass

    @abstractmethod
    def get_commits(self) -> List[GitCommit]:
        """
        获取指定范围内的提交列表。
        返回解析后的 GitCommit 对象列表。
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取变更统计信息。
        返回包含 additions, deletions, file_stats 等信息的字典。
        """
        pass

    @abstractmethod
    def get_diff(self, commit_hash: str) -> Optional[str]:
        """
        获取指定提交的 Diff 内容 (用于 AI 分析)。
        """
        pass

    @abstractmethod
    def get_readme(self) -> Optional[str]:
        """
        获取项目的 README 内容 (作为项目上下文)。
        """
        pass
