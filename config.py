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
    OUTPUT_FILENAME_PREFIX = "GitReport"

    # AI 配置
    AI_API_KEY: str = os.getenv("GOOGLE_API_KEY")

    # 邮件(SMTP)配置
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = 587
    SMTP_USER: str = os.getenv("SMTP_USER", "your-email@example.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASS")
