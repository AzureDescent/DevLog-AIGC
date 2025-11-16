# context.py
"""
[V4.0] 运行时配置的数据模型
"""
from dataclasses import dataclass
from typing import List, Optional
from config import GlobalConfig  # V4.0


@dataclass
class RunContext:
    """
    (V4.0) 封装一次运行所需的所有配置和状态。
    这是从 CLI 传递到 Orchestrator 的唯一对象。
    """

    # --- 核心路径 ---
    repo_path: str
    project_data_path: str

    # --- AI 与报告参数 ---
    llm_id: str
    style: str
    attach_format: str

    # --- 范围参数 ---
    commit_range_arg: str
    time_range_desc: str

    # --- 邮件参数 ---
    email_list: List[str]

    # --- 标志 ---
    no_ai: bool
    no_browser: bool

    # --- 全局配置 ---
    # 包含所有 API 密钥、常量和 .env 加载的数据
    global_config: GlobalConfig
