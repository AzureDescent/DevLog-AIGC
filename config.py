# config.py
import os
from dotenv import load_dotenv

# 优先加载 .env 文件，以便 os.getenv 能立即读取
load_dotenv()


class GitReportConfig:
    """Git报告配置参数类"""

    TIME_RANGE: str = "1 day ago"
    GIT_LOG_FORMAT = 'git log --since="{time_range}" --graph --pretty=format:"%h|%d|%s|%cr|%an" --abbrev-commit'
    GIT_STATS_FORMAT = 'git log --since="{time_range}" --numstat --pretty=format:""'

    # --- (新增) V2.0 START ---
    # 用于获取单个 commit diff 的命令。
    # --pretty="" 确保我们只获取 diff 内容，没有 commit message 等额外信息
    # --no-color 移除 ANSI 颜色代码
    GIT_COMMIT_DIFF_FORMAT = 'git show {commit_hash} --pretty="" --no-color'
    # --- (新增) V2.0 END ---

    OUTPUT_FILENAME_PREFIX = "GitReport"

    # =================================================================
    # 新增：智能过滤 (Sieving) 模式
    # 使用 fnmatch 语法 (https://docs.python.org/3/library/fnmatch.html)
    # =================================================================
    FILTER_FILE_PATTERNS: list[str] = [
        # 锁定文件 (通常包含大量自动生成的变更)
        "*.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pdm.lock",
        "uv.lock",
        # 编译和构建产物
        "dist/*",
        "build/*",
        "*.min.js",
        "*.pyc",
        "*.so",
        "*.o",
        # 缓存和临时文件
        "__pycache__/*",
        ".pytest_cache/*",
        ".mypy_cache/*",
        ".ruff_cache/*",
        # IDE 和环境配置 (通常不应提交，但万一提交了)
        ".vscode/*",
        ".idea/*",
        ".env",
        # 常见的二进制/资源文件 (diff 无意义)
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.svg",
        "*.ico",
        "*.pdf",
        "*.woff",
        "*.woff2",
        "*.eot",
        "*.ttf",
        "*.otf",
        "*.zip",
        "*.tar.gz",
    ]

    # AI 配置
    AI_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # 邮件(SMTP)配置
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = 465
    SMTP_USER: str = os.getenv("SMTP_USER", "your-email@example.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASS", "")
