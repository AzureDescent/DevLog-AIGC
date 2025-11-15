# config_manager.py
"""
[V3.8] 配置管理器
- 负责处理全局项目别名 (projects.json)
- 负责处理项目级默认配置 (config.json)
- 包含一个交互式向导 (run_interactive_config_wizard)
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# 导入配置以获取基础路径
from config import GitReportConfig

logger = logging.getLogger(__name__)

PROJECTS_JSON_FILE = "projects.json"
CONFIG_JSON_FILE = "config.json"


def _get_data_root_path() -> str:
    """(V3.8) 辅助函数：获取 data 根目录的路径"""
    cfg = GitReportConfig()
    return os.path.join(cfg.SCRIPT_BASE_PATH, cfg.DATA_ROOT_DIR_NAME)


def load_project_aliases(data_root_path: str) -> Dict[str, str]:
    """(V3.8) 加载全局别名文件 (data/projects.json)"""
    aliases_path = os.path.join(data_root_path, PROJECTS_JSON_FILE)
    if not os.path.exists(aliases_path):
        return {}
    try:
        with open(aliases_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ (V3.8) 加载别名文件 {aliases_path} 失败: {e}")
        return {}


def save_project_aliases(data_root_path: str, aliases: Dict[str, str]):
    """(V3.8) 保存全局别名文件 (data/projects.json)"""
    aliases_path = os.path.join(data_root_path, PROJECTS_JSON_FILE)
    try:
        os.makedirs(data_root_path, exist_ok=True)
        with open(aliases_path, "w", encoding="utf-8") as f:
            json.dump(aliases, f, indent=4)
    except Exception as e:
        logger.error(f"❌ (V3.8) 保存别名文件 {aliases_path} 失败: {e}")


def get_path_from_alias(data_root_path: str, alias: str) -> Optional[str]:
    """(V3.8) 通过别名获取仓库的绝对路径"""
    aliases = load_project_aliases(data_root_path)
    return aliases.get(alias)


def load_project_config(project_data_path: str) -> Dict[str, Any]:
    """(V3.8) 加载特定项目的配置文件 (data/<Project>/config.json)"""
    config_path = os.path.join(project_data_path, CONFIG_JSON_FILE)
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ (V3.8) 加载项目配置 {config_path} 失败: {e}")
        return {}


def save_project_config(project_data_path: str, config_data: Dict[str, Any]):
    """(V3.8) 保存特定项目的配置文件 (data/<Project>/config.json)"""
    config_path = os.path.join(project_data_path, CONFIG_JSON_FILE)
    try:
        os.makedirs(project_data_path, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        logger.error(f"❌ (V3.8) 保存项目配置 {config_path} 失败: {e}")


def get_project_data_path(data_root_path: str, repo_path: str) -> str:
    """(V3.8) 辅助函数：根据仓库路径获取其数据存储路径"""
    repo_path_abs = os.path.abspath(repo_path)
    if os.path.basename(repo_path_abs) == ".":
        project_name = "current_dir_project"
    else:
        project_name = os.path.basename(repo_path_abs)
    return os.path.join(data_root_path, project_name)


def _input_with_default(prompt: str, default: str) -> str:
    """(V3.8) 辅助函数：获取带默认值的用户输入"""
    return input(f"{prompt} [{default}]: ") or default


def run_interactive_config_wizard(data_root_path: str, repo_path: str):
    """
    (V3.8) 运行交互式配置向导
    """
    logger.info("--- 🚀 欢迎使用 DevLog-AIGC V3.8 配置向导 ---")
    repo_path_abs = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path_abs):
        logger.error(f"路径 {repo_path_abs} 不是一个有效的目录。")
        return

    project_data_path = get_project_data_path(data_root_path, repo_path_abs)
    project_name_default = os.path.basename(project_data_path)

    logger.info(f"  [目标仓库]: {repo_path_abs}")
    logger.info(f"  [数据目录]: {project_data_path}")

    # 1. 加载现有配置
    aliases = load_project_aliases(data_root_path)
    current_config = load_project_config(project_data_path)

    # 2. 配置别名 (Alias)
    print("\n--- 1. 项目别名配置 ---")
    current_alias = next(
        (alias for alias, path in aliases.items() if path == repo_path_abs),
        project_name_default,
    )
    alias = _input_with_default(f"  设置一个简短的别名 (用于 -p ...)", current_alias)
    aliases[alias] = repo_path_abs
    save_project_aliases(data_root_path, aliases)
    logger.info(f"✅ 别名 '{alias}' 已保存至 {PROJECTS_JSON_FILE}")

    # 3. 配置项目默认值 (Config)
    print("\n--- 2. 项目默认值配置 ---")
    print("  (提示：保留默认值或直接按 Enter 键跳过)")
    config_data = {}
    config_data["default_llm"] = _input_with_default(
        "  默认 LLM (gemini, deepseek)", current_config.get("default_llm", "gemini")
    )
    config_data["default_style"] = _input_with_default(
        "  默认文章风格 (default, novel, anime, etc.)",
        current_config.get("default_style", "default"),
    )
    config_data["default_email"] = _input_with_default(
        "  默认接收邮箱 (留空=不发送)", current_config.get("default_email", "")
    )
    config_data["default_attach_format"] = _input_with_default(
        "  默认附件格式 (html, pdf)",
        current_config.get("default_attach_format", "html"),
    )

    save_project_config(project_data_path, config_data)
    logger.info(f"✅ 项目配置已保存至 {project_data_path}/{CONFIG_JSON_FILE}")

    print("\n--- ✅ 配置完成！ ---")
    print(f"  现在你可以使用 'python GitReport.py -p {alias}' 来运行报告。")
