# cli.py
"""
[V4.0] 命令行界面 (Interface) 层
[V4.1] 更新：移除 --llm 的 choices 限制，支持动态注册的供应商。
"""
import argparse
import logging
import sys
import os
from typing import Dict, Any, Optional, List

# V4.0 导入
import config_manager
from config import GlobalConfig
from context import RunContext
from orchestrator import ReportOrchestrator

logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    """
    (V4.0) 负责所有 argparse 的定义。
    """
    parser = argparse.ArgumentParser(
        description="Git 工作日报生成器 (V4.0+)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # --- [V3.8/V3.9] 新增/修改的参数 ---
    parser.add_argument(
        "--configure",
        action="store_true",
        help="[V3.8] 运行交互式配置向导。\n" "   (需要 -r 指定要配置的仓库路径)",
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="[V3.9] 运行交互式项目清理向导。\n" "   (需要 -p 或 -r 指定清理目标)",
    )

    parser.add_argument(
        "-p",
        "--project",
        type=str,
        help="[V3.8] 使用已配置的项目别名运行报告。\n" "   (与 -r 互斥)",
    )
    parser.add_argument(
        "-r",
        "--repo-path",
        type=str,
        default=None,
        help="[V3.0] 指定要分析的 Git 仓库的根目录路径。\n"
        "   (用于 --configure, --cleanup 或直接运行未配置的项目)",
    )

    # --- (V3.2) 互斥参数组 ---
    range_group = parser.add_mutually_exclusive_group()
    range_group.add_argument(
        "-t",
        "--time",
        type=str,
        help="指定Git日志的时间范围 (例如 '1 day ago').\n(默认: '1 day ago')",
    )
    range_group.add_argument(
        "-n",
        "--number",
        type=int,
        help="[V3.2] 指定最近 N 次提交 (例如 5)。\n(与 -t 互斥)",
    )

    # --- [V3.8] 覆盖参数 ---

    # [V4.1 修改] 移除了 choices=["gemini", "deepseek"]，支持动态供应商
    parser.add_argument(
        "--llm",
        type=str,
        default=None,
        help="[V3.4] (覆盖) 指定要使用的 LLM 供应商 (例如 'gemini', 'deepseek', 'mock' 等)。\n"
        "(默认: 使用项目 config.json 或全局 config.py 中的设置)",
    )

    parser.add_argument(
        "--style",
        type=str,
        default=None,
        help="[V3.6] (覆盖) 指定公众号文章的风格。\n"
        "例如: 'default', 'novel', 'anime'。 \n"
        "(默认: 使用项目 config.json 中的设置)",
    )

    parser.add_argument(
        "--attach-format",
        type=str,
        choices=["html", "pdf"],
        default=None,
        help="[V3.7] (覆盖) (与 -e 连用) 指定邮件的附件格式。\n"
        "'html': 发送 GitReport_....html\n"
        "'pdf': (实验性) 将风格文章转为 PDF (需安装 PrinceXML) \n"
        "(默认: 使用项目 config.json 中的设置)",
    )

    parser.add_argument(
        "-e",
        "--email",
        type=str,
        default=None,
        help="[V3.9] (覆盖) 接收邮箱 (多个请用逗号,分隔)。\n"
        "(默认: 使用项目 config.json 中的设置)",
    )

    # --- 标志 (Flags) ---
    parser.add_argument("--no-ai", action="store_true", help="禁用 AI 摘要功能")
    parser.add_argument(
        "--no-browser", action="store_true", help="不自动在浏览器中打开报告"
    )

    return parser


def run_cli():
    """
    (V4.0) 新的主入口点。
    """

    # 1. 解析 Args
    parser = setup_parser()
    args = parser.parse_args()

    # 2. 加载 GlobalConfig 和 Data Root
    global_config = GlobalConfig()
    data_root_path = os.path.join(
        global_config.SCRIPT_BASE_PATH, global_config.DATA_ROOT_DIR_NAME
    )
    os.makedirs(data_root_path, exist_ok=True)

    # 3. 处理特殊模式：--configure
    if args.configure:
        if not args.repo_path:
            logger.error("❌ --configure 标志需要 -r / --repo-path 指定目标仓库路径。")
            sys.exit(1)

        logger.info(f"⚙️ (V3.8) 启动交互式配置向导: {args.repo_path}")
        repo_path_abs = os.path.abspath(args.repo_path)
        config_manager.run_interactive_config_wizard(data_root_path, repo_path_abs)
        sys.exit(0)

    # 4. 确定路径并加载项目配置
    project_config: Dict[str, Any] = {}
    alias: Optional[str] = None
    repo_path: Optional[str] = None
    project_data_path: Optional[str] = None

    if args.project and args.repo_path:
        logger.error("❌ (V3.8) 不能同时使用 -p (别名) 和 -r (路径)。请只选其一。")
        sys.exit(1)

    if args.project:
        # (V3.8) 别名模式
        alias = args.project
        repo_path_from_alias = config_manager.get_path_from_alias(data_root_path, alias)
        if not repo_path_from_alias:
            logger.error(f"❌ (V3.8) 别名 '{alias}' 未在 projects.json 中找到。")
            logger.error(f"   请先使用 --configure -r ... 来配置它。")
            sys.exit(1)
        repo_path = repo_path_from_alias
        project_data_path = config_manager.get_project_data_path(
            data_root_path, repo_path
        )
        project_config = config_manager.load_project_config(project_data_path)
        logger.info(f"ℹ️ (V3.8) 使用别名 '{alias}' (路径: {repo_path})")

    elif args.repo_path:
        # (V3.8) 直接路径模式
        # [V4.8 修复] 如果是远程 URL，保持原样；否则转为绝对路径
        if args.repo_path.startswith(("http://", "https://", "git@")):
            repo_path = args.repo_path
            logger.info(f"ℹ️ (V4.8) 检测到远程仓库 URL: {repo_path}")
        else:
            repo_path = os.path.abspath(args.repo_path)
            logger.info(f"ℹ️ (V3.8) 使用直接路径 {repo_path}")

        project_data_path = config_manager.get_project_data_path(
            data_root_path, repo_path
        )
        project_config = config_manager.load_project_config(project_data_path)

    else:
        logger.error(
            "❌ (V3.8) 必须提供 -p (项目别名) 或 -r (仓库路径) 之一来运行报告。"
        )
        sys.exit(1)

    # 确保项目数据目录存在
    os.makedirs(project_data_path, exist_ok=True)

    # 5. 处理特殊模式：--cleanup
    if args.cleanup:
        logger.info(f"🧹 (V3.9) 启动清理向导: {repo_path}")
        config_manager.run_interactive_cleanup_wizard(
            data_root_path, project_data_path, repo_path, alias
        )
        sys.exit(0)

    # 6. [V4.0] 组装 RunContext
    logger.info("⚙️ (V4.0) 正在合并配置并组装 RunContext...")

    # Git 范围参数
    number = args.number
    time_str_input = args.time

    # AI 与报告参数
    llm_id = args.llm or project_config.get("default_llm") or global_config.DEFAULT_LLM
    style = args.style or project_config.get("default_style") or "default"
    attach_format = (
        args.attach_format or project_config.get("default_attach_format") or "html"
    )

    # 邮件参数
    email_list: List[str] = []
    if args.email:
        email_list = [e.strip() for e in args.email.split(",") if e.strip()]
    elif project_config.get("default_email"):
        email_list = project_config.get("default_email", [])

    # 标志参数
    no_ai = args.no_ai
    no_browser = args.no_browser

    # 设置范围
    commit_range_arg: str
    time_range_desc: str
    if number:
        commit_range_arg = f"-n {number}"
        time_range_desc = f"最近 {number} 次提交"
    else:
        time_str_default = "1 day ago"
        time_str = time_str_input if time_str_input else time_str_default
        commit_range_arg = f'--since="{time_str}"'
        time_range_desc = time_str

    # 日志
    email_log_str = ", ".join(email_list) if email_list else "未设置"

    logger.info("=" * 50)
    logger.info(f"🚀 (V4.0) DevLog-AIGC 启动...")
    logger.info(f"   [目标仓库]: {repo_path}")
    logger.info(f"   [LLM 供应商]: {llm_id}")
    logger.info(f"   [文章风格]: {style}")
    logger.info(f"   [邮件目标]: {email_log_str}")
    logger.info("=" * 50)

    # 实例化 Context
    try:
        run_context = RunContext(
            repo_path=repo_path,
            project_data_path=project_data_path,
            llm_id=llm_id,
            style=style,
            email_list=email_list,
            attach_format=attach_format,
            commit_range_arg=commit_range_arg,
            time_range_desc=time_range_desc,
            no_ai=no_ai,
            no_browser=no_browser,
            global_config=global_config,
        )
    except Exception as e:
        logger.error(f"❌ (V4.0) 实例化 RunContext 失败: {e}", exc_info=True)
        sys.exit(1)

    # 7. 运行 Orchestrator
    logger.info("🚀 (V4.0) 正在移交给 Orchestrator...")
    orchestrator = ReportOrchestrator(run_context)
    orchestrator.run()
    logger.info("✅ (V4.0) Orchestrator 运行完毕。")
