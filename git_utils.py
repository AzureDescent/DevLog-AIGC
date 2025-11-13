# git_utils.py
import subprocess
import re
import logging
import fnmatch
from typing import Optional, List, Dict, Any
from config import GitReportConfig
from models import GitCommit, FileStat

logger = logging.getLogger(__name__)


def run_git_command(
    cmd: str, repo_path: str, context: str = "执行Git命令"
) -> Optional[str]:
    """
    (V3.0 修改) 统一的Git命令执行函数
    - 增加了 repo_path 参数
    - 使用 cwd 参数在指定仓库路径下执行
    """
    try:
        logger.info(f"在 {repo_path} 中执行命令: {cmd}")
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            cwd=repo_path,  # --- (V3.0) 核心修改 ---
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
    # --- (V3.0) 修改: 传入 config.REPO_PATH ---
    return run_git_command(cmd, config.REPO_PATH, f"获取 {commit_hash} 的Diff")


# --- (新增) V2.0 END ---


def is_git_repository(repo_path: str) -> bool:
    """
    (V3.0 修改) 检查指定路径是否为Git仓库
    - 增加了 repo_path 参数
    - 使用 cwd 参数
    """
    try:
        result = subprocess.run(
            "git rev-parse --is-inside-work-tree",
            shell=True,
            capture_output=True,
            text=True,
            cwd=repo_path,  # --- (V3.0) 核心修改 ---
        )
        return result.returncode == 0
    except Exception:
        return False


def get_git_log(config: GitReportConfig) -> Optional[str]:
    """获取Git提交历史"""
    cmd = config.GIT_LOG_FORMAT.format(time_range=config.TIME_RANGE)
    # --- (V3.0) 修改: 传入 config.REPO_PATH ---
    return run_git_command(cmd, config.REPO_PATH, "获取Git提交历史")


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
    """获取Git统计信息和文件变更详情（已实现智能过滤）"""
    stats = {
        "additions": 0,
        "deletions": 0,
        "files_changed": 0,
        "file_stats": [],
    }
    # --- (V3.0) 修改: 传入 config.REPO_PATH ---
    output = run_git_command(
        config.GIT_STATS_FORMAT.format(time_range=config.TIME_RANGE),
        config.REPO_PATH,
        "获取Git统计信息",
    )
    if not output:
        return stats

    file_changes: Dict[str, FileStat] = {}
    patterns = config.FILTER_FILE_PATTERNS

    try:
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) == 3:
                    add = int(parts[0]) if parts[0].isdigit() else 0
                    delete = int(parts[1]) if parts[1].isdigit() else 0
                    filename = parts[2].strip()

                    is_filtered = False
                    for pattern in patterns:
                        if fnmatch.fnmatch(filename, pattern):
                            is_filtered = True
                            break

                    if is_filtered:
                        logger.info(f"智能过滤: 已跳过文件 {filename}")
                        continue

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
