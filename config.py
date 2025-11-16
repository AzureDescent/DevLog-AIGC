# config.py
import os
from dotenv import load_dotenv


# --- (V3.0) 脚本基础路径 (V3.3 保持不变) ---
SCRIPT_BASE_PATH = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(SCRIPT_BASE_PATH, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ (V3.0) 已从脚本目录加载 .env: {env_path}")
else:
    load_dotenv()
    print("⚠️ (V3.0) 未在脚本目录找到 .env，尝试从 CWD 加载。")


class GlobalConfig:
    """
    (V4.0) Git报告的全局应用配置。
    只包含从 .env 加载的密钥和应用级常量。
    不包含任何运行时状态。
    """

    # --- (V3.0 & V3.1) 路径配置 (V4.0 重构) ---
    SCRIPT_BASE_PATH: str = SCRIPT_BASE_PATH
    DATA_ROOT_DIR_NAME: str = "data"
    # 移除了: REPO_PATH, PROJECT_DATA_PATH (现在在 RunContext 中)

    # --- (V3.2) 范围参数 (V4.0 重构) ---
    # 移除了: TIME_RANGE_DESCRIPTION, COMMIT_RANGE_ARG (现在在 RunContext 中)
    # 保留了: Git 命令格式字符串 (作为常量)
    GIT_LOG_FORMAT = 'git log {commit_range_arg} --graph --pretty=format:"%h|%d|%s|%cr|%an" --abbrev-commit'
    GIT_STATS_FORMAT = 'git log {commit_range_arg} --numstat --pretty=format:""'
    GIT_COMMIT_DIFF_FORMAT = 'git show {commit_hash} --pretty="" --no-color'

    # V2.2 记忆文件 (V4.0 保持不变)
    PROJECT_LOG_FILE: str = "project_log.jsonl"
    PROJECT_MEMORY_FILE: str = "project_memory.md"
    OUTPUT_FILENAME_PREFIX = "GitReport"
    AI_CACHE_FILENAME: str = ".ai_summary_cache.md"

    # --- V3.3 智能过滤 (V4.0 保持不变) ---
    FILTER_FILE_PATTERNS: list[str] = [
        "*.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pdm.lock",
        "uv.lock",
        "dist/*",
        "build/*",
        "*.min.js",
        "*.pyc",
        "*.so",
        "*.o",
        "__pycache__/*",
        ".pytest_cache/*",
        ".mypy_cache/*",
        ".ruff_cache/*",
        ".vscode/*",
        ".idea/*",
        ".env",
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

    # =================================================================
    # --- (V3.4) AI 供应商配置 (V4.0 保持不变) ---
    # =================================================================

    # 1. 供应商 API 密钥
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

    # 2. 供应商特定配置
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # 3. 应用程序默认值
    DEFAULT_LLM: str = os.getenv("DEFAULT_LLM", "gemini").lower()

    # 4. 供应商的默认模型
    DEFAULT_MODEL_GEMINI: str = "gemini-2.5-flash"
    DEFAULT_MODEL_DEEPSEEK: str = "deepseek-chat"

    # 5. (V3.4 新增) 供应商配置验证辅助函数
    def is_provider_configured(self, provider: str) -> bool:
        """
        检查特定供应商是否已在环境中设置其 API 密钥。
        """
        if provider == "gemini":
            return bool(self.GEMINI_API_KEY)
        if provider == "deepseek":
            return bool(self.DEEPSEEK_API_KEY)
        return False

    # =================================================================
    # --- (V3.3 保持不变) 邮件(SMTP)配置 ---
    # =================================================================
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = 465
    SMTP_USER: str = os.getenv("SMTP_USER", "your-email@example.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASS", "")
