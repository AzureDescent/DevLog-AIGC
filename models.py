# models.py
from dataclasses import dataclass


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
