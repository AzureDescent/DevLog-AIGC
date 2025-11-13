# config.py
import os
from dotenv import load_dotenv


# --- (新增) V3.0: 定义脚本的基础路径 ---
# 无论从哪里运行，SCRIPT_BASE_PATH 都是 config.py 所在的目录

SCRIPT_BASE_PATH = os.path.abspath(os.path.dirname(__file__))

# 从脚本的基础路径加载 .env 文件
# 这使得 .env 文件可以和脚本放在一起，而不是放在目标仓库
env_path = os.path.join(SCRIPT_BASE_PATH, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ (V3.0) 已从脚本目录加载 .env: {env_path}")
else:
    # 尝试从 CWD 加载（保留旧的兼容性，但 V3.0 推荐 .env 随脚本）
    load_dotenv()
    print("⚠️ (V3.0) 未在脚本目录找到 .env，尝试从 CWD 加载。")


class GitReportConfig:
    """Git报告配置参数类"""

    # --- (新增) V3.0: 路径配置 ---
    # 1. 脚本的数据存储根目录
    SCRIPT_BASE_PATH: str = SCRIPT_BASE_PATH
    # 2. 要分析的目标 Git 仓库路径 (默认: CWD, 将被 argparse 覆盖)
    REPO_PATH: str = "."

    # --- (新增) V3.1: 隔离的数据路径 ---
    # 这是所有项目数据存储的根目录名 (相对于 SCRIPT_BASE_PATH)
    DATA_ROOT_DIR_NAME: str = "data"
    # 这是 *当前* 项目的专属数据路径 (将在 GitReport.py 中被设置)
    # 例如: /path/to/script/data/Project-A
    PROJECT_DATA_PATH: str = ""
    # --- (V3.1 结束) ---

    # 原始配置
    TIME_RANGE: str = "1 day ago"
    GIT_LOG_FORMAT = 'git log --since="{time_range}" --graph --pretty=format:"%h|%d|%s|%cr|%an" --abbrev-commit'
    GIT_STATS_FORMAT = 'git log --since="{time_range}" --numstat --pretty=format:""'
    GIT_COMMIT_DIFF_FORMAT = 'git show {commit_hash} --pretty="" --no-color'

    # V2.2 记忆文件 (文件名保持相对，我们将用 SCRIPT_BASE_PATH 组合)
    PROJECT_LOG_FILE: str = "project_log.jsonl"
    PROJECT_MEMORY_FILE: str = "project_memory.md"
    OUTPUT_FILENAME_PREFIX = "GitReport"

    # --- (新增) V2.1 START ---
    # 定义 AI 摘要的缓存文件名
    AI_CACHE_FILENAME: str = ".ai_summary_cache.md"
    # --- (新增) V2.1 END ---

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
