# git_utils.py
import subprocess
import re
import logging
import fnmatch
from typing import Optional, List, Dict, Any
from config import GitReportConfig
from models import GitCommit, FileStat

logger = logging.getLogger(__name__)


def run_git_command(cmd: str, context: str = "执行Git命令") -> Optional[str]:
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


# --- (新增) V2.0 START ---
def get_commit_diff(config: GitReportConfig, commit_hash: str) -> Optional[str]:
    """获取单个commit的diff内容"""
    cmd = config.GIT_COMMIT_DIFF_FORMAT.format(commit_hash=commit_hash)
    return run_git_command(cmd, f"获取 {commit_hash} 的Diff")


# --- (新增) V2.0 END ---


def is_git_repository() -> bool:
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


def get_git_log(config: GitReportConfig) -> Optional[str]:
    """获取Git提交历史"""
    cmd = config.GIT_LOG_FORMAT.format(time_range=config.TIME_RANGE)
    return run_git_command(cmd, "获取Git提交历史")


def parse_single_commit(line: str) -> Optional[GitCommit]:
    """解析单行提交记录"""
    try:
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


def parse_git_log(log_output: str) -> List[GitCommit]:
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
        commit = parse_single_commit(line)
        if commit:
            commits.append(commit)
    logger.info(f"成功解析 {len(commits)} 个提交")
    return commits


def get_git_stats(config: GitReportConfig) -> Dict[str, Any]:
    """获取Git统计信息和文件变更详情（已实现智能过滤）"""  # <-- (注释更新)
    stats = {
        "additions": 0,
        "deletions": 0,
        "files_changed": 0,
        "file_stats": [],
    }
    output = run_git_command(
        config.GIT_STATS_FORMAT.format(time_range=config.TIME_RANGE),
        "获取Git统计信息",
    )
    if not output:
        return stats

    file_changes: Dict[str, FileStat] = {}

    # =================================================================
    # 新增：获取过滤模式
    # =================================================================
    patterns = config.FILTER_FILE_PATTERNS

    try:
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) == 3:
                    add = int(parts[0]) if parts[0].isdigit() else 0
                    delete = int(parts[1]) if parts[1].isdigit() else 0
                    filename = parts[2].strip()

                    # =================================================================
                    # 新增：执行过滤检查
                    # =================================================================
                    is_filtered = False
                    for pattern in patterns:
                        if fnmatch.fnmatch(filename, pattern):
                            is_filtered = True
                            break

                    if is_filtered:
                        logger.info(f"智能过滤: 已跳过文件 {filename}")
                        continue  # 跳过此文件，不计入统计
                    # =================================================================

                    stats["additions"] += add
                    stats["deletions"] += delete
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
