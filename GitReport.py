"""
Git工作日报生成器 (V3.9)
- [V3.9] 增加 --cleanup 模式，用于项目清理
- [V3.9] 邮件参数 (-e) 和配置 (default_email) 现在支持群发
- [V3.8] 增加 --configure 模式和 -p 别名模式，引入 config_manager
- [V3.7] 增加 --attach-format [html|pdf] 参数，支持 PDF 附件
- [V3.4] 增加 --llm 参数，用于选择 AI 供应商
"""

import argparse
import logging
import sys
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any  # [V3.9] 确保导入 List

# 导入所有重构后的模块
from config import GitReportConfig
import utils
import git_utils
import report_builder
from ai_summarizer import AIService  # (V3.4) 此模块内部已重构
import email_sender
import pdf_converter  # (V3.7)
import config_manager  # (V3.8) 导入配置管理器

# 1. 初始化日志
utils.setup_logging()
logger = logging.getLogger(__name__)


def main_flow(args: argparse.Namespace):
    """
    主执行流程
    (V3.9 重构)
    """

    # 1. 加载基础配置
    cfg = GitReportConfig()
    data_root_path = os.path.join(cfg.SCRIPT_BASE_PATH, cfg.DATA_ROOT_DIR_NAME)
    os.makedirs(data_root_path, exist_ok=True)

    # --- [V3.8] 检查是否为配置模式 ---
    if args.configure:
        if not args.repo_path:
            logger.error("❌ --configure 标志需要 -r / --repo-path 指定目标仓库路径。")
            logger.error("   示例: python GitReport.py --configure -r /path/to/my/repo")
            sys.exit(1)

        logger.info(f"⚙️ (V3.8) 启动交互式配置向导: {args.repo_path}")
        repo_path_abs = os.path.abspath(args.repo_path)
        config_manager.run_interactive_config_wizard(data_root_path, repo_path_abs)
        sys.exit(0)  # 配置完成后退出

    # --- [V3.8] 确定路径并加载项目配置 ---
    project_config: Dict[str, Any] = {}
    alias: Optional[str] = None

    if args.project and args.repo_path:
        logger.error("❌ (V3.8) 不能同时使用 -p (别名) 和 -r (路径)。请只选其一。")
        sys.exit(1)

    if args.project:
        # (V3.8) 别名模式
        alias = args.project
        repo_path_from_alias = config_manager.get_path_from_alias(data_root_path, alias)
        if not repo_path_from_alias:
            logger.error(
                f"❌ (V3.8) 别名 '{alias}' 未在 {data_root_path}/{config_manager.PROJECTS_JSON_FILE} 中找到。"
            )
            logger.error(f"   请先使用 --configure -r ... 来配置它。")
            sys.exit(1)
        cfg.REPO_PATH = repo_path_from_alias
        cfg.PROJECT_DATA_PATH = config_manager.get_project_data_path(
            data_root_path, cfg.REPO_PATH
        )
        project_config = config_manager.load_project_config(cfg.PROJECT_DATA_PATH)
        logger.info(f"ℹ️ (V3.8) 使用别名 '{alias}' (路径: {cfg.REPO_PATH})")

    elif args.repo_path:
        # (V3.8) 直接路径模式 (V3.0 兼容)
        cfg.REPO_PATH = os.path.abspath(args.repo_path)
        cfg.PROJECT_DATA_PATH = config_manager.get_project_data_path(
            data_root_path, cfg.REPO_PATH
        )
        project_config = config_manager.load_project_config(cfg.PROJECT_DATA_PATH)
        if project_config:
            logger.info(f"ℹ️ (V3.8) 使用直接路径 {cfg.REPO_PATH} (已加载项目配置)")
        else:
            logger.info(f"ℹ️ (V3.8) 使用直接路径 {cfg.REPO_PATH} (无项目配置)")

    else:
        logger.error(
            "❌ (V3.8) 必须提供 -p (项目别名) 或 -r (仓库路径) 之一来运行报告。"
        )
        logger.error(
            "   提示: 首次运行请使用 'python GitReport.py --configure -r /path/to/repo'"
        )
        sys.exit(1)

    # 确保项目数据目录存在 (V3.1 逻辑保留)
    os.makedirs(cfg.PROJECT_DATA_PATH, exist_ok=True)

    # --- [V3.9] 检查是否为清理模式 ---
    if args.cleanup:
        logger.info(f"🧹 (V3.9) 启动清理向导: {cfg.REPO_PATH}")
        config_manager.run_interactive_cleanup_wizard(
            data_root_path, cfg.PROJECT_DATA_PATH, cfg.REPO_PATH, alias
        )
        sys.exit(0)  # 清理完成后退出

    # --- [V3.9] 合并配置与命令行参数 (邮件群发更新) ---
    # 优先级: 命令行Args > 项目config.json > 全局config.py

    # Git 范围参数 (无配置)
    number = args.number
    time_str_input = args.time

    # AI 与报告参数 (有配置)
    llm = args.llm or project_config.get("default_llm") or cfg.DEFAULT_LLM
    style = args.style or project_config.get("default_style") or "default"
    attach_format = (
        args.attach_format or project_config.get("default_attach_format") or "html"
    )

    # [V3.9] 邮件群发逻辑
    email_list: List[str] = []
    if args.email:  # 1. 优先使用 CLI (逗号分隔的字符串)
        email_list = [e.strip() for e in args.email.split(",") if e.strip()]
    elif project_config.get("default_email"):  # 2. 其次使用 config.json (已经是列表)
        email_list = project_config.get("default_email", [])  # 确保是列表

    email = email_list if email_list else None  # 传递给后续步骤的变量

    # 标志参数 (无配置)
    no_ai = args.no_ai
    no_browser = args.no_browser

    # --- (V3.2) 根据互斥参数设置范围 ---
    if number:
        cfg.COMMIT_RANGE_ARG = f"-n {number}"
        cfg.TIME_RANGE_DESCRIPTION = f"最近 {number} 次提交"
    else:
        time_str_default = "1 day ago"
        time_str = time_str_input if time_str_input else time_str_default
        cfg.COMMIT_RANGE_ARG = f'--since="{time_str}"'
        cfg.TIME_RANGE_DESCRIPTION = time_str

    # --- (V3.4) LLM 供应商选择 ---
    provider_id = llm
    # --- (V3.4) 结束 ---

    # [V3.9] 更新日志
    email_log_str = ", ".join(email) if email else "未设置"

    logger.info("=" * 50)
    logger.info(f"🚀 (V3.9) DevLog-AIGC 启动...")
    logger.info(f"   [目标仓库 (REPO_PATH)]: {cfg.REPO_PATH}")
    logger.info(f"   [数据存储 (DATA_PATH)]: {cfg.PROJECT_DATA_PATH}")
    logger.info(f"   [分析范围]: {cfg.TIME_RANGE_DESCRIPTION}")
    logger.info(
        f"   [LLM 供应商 (Provider)]: {provider_id} {'(来自命令行)' if args.llm else '(来自配置)'}"
    )
    logger.info(
        f"   [文章风格 (Style)]: {style} {'(来自命令行)' if args.style else '(来自配置)'}"
    )
    logger.info(
        f"   [邮件目标 (Email)]: {email_log_str} {'(来自命令行)' if args.email else '(来自配置)'}"
    )
    logger.info(
        f"   [附件格式 (Attach)]: {attach_format} {'(来自命令行)' if args.attach_format and args.attach_format != 'html' else '(来自配置)'}"
    )
    logger.info("=" * 50)

    # --- (V3.4) AI 实例创建 (核心修改) ---
    ai_service = None
    if not no_ai:
        try:
            ai_service = AIService(cfg, provider_id=provider_id)
        except (ValueError, ImportError) as e:
            logger.error(f"❌ (V3.4) AI 服务初始化失败: {e}")
            logger.error("   请检查您的 .env 文件是否已正确配置。")
            logger.error("   将以 --no-ai 模式继续...")
            no_ai = True  # 强制进入 no-ai 模式

    # --- (V3.0) 读取 README (V3.3 保持不变) ---
    project_readme = None
    readme_path = os.path.join(cfg.REPO_PATH, "README.md")
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            project_readme = f.read()
        logger.info(f"✅ 成功加载目标仓库 README: {readme_path}")
    except FileNotFoundError:
        logger.warning(f"❌ 未在目标仓库找到 README.md，跳过加载。 ({readme_path})")
    except Exception as e:
        logger.error(f"❌ 读取 README.md 失败 ({readme_path}): {e}")

    # --- (V3.1) 读取“压缩记忆” (V3.3 保持不变) ---
    previous_summary = None
    memory_file_path = os.path.join(cfg.PROJECT_DATA_PATH, cfg.PROJECT_MEMORY_FILE)
    if not no_ai:
        try:
            with open(memory_file_path, "r", encoding="utf-8") as f:
                previous_summary = f.read()
            if previous_summary:
                logger.info(f"✅ 成功加载压缩记忆: {memory_file_path}")
        except FileNotFoundError:
            logger.info(f"ℹ️ 未找到压缩记忆 ({memory_file_path})，将从头开始。")
        except Exception as e:
            logger.error(f"❌ 加载压缩记忆失败 ({memory_file_path}): {e}")

    # 2. 检查环境 (V3.3 保持不变)
    if not git_utils.is_git_repository(cfg.REPO_PATH):
        logger.error(f"❌ 指定路径不是Git仓库: {cfg.REPO_PATH}")
        return

    # 3. 获取和解析 Git 数据 (V3.3 保持不变)
    log_output = git_utils.get_git_log(cfg)
    if not log_output:
        logger.error("❌ 未获取到Git提交记录")
        print(f"💡 提示: 在 '{cfg.TIME_RANGE_DESCRIPTION}' 范围内可能没有提交。")
        return

    commits = git_utils.parse_git_log(log_output)
    stats = git_utils.get_git_stats(cfg)
    stats["total_commits"] = len(commits)

    # 4. 生成报告 (V3.3 保持不变)
    text_report = report_builder.generate_text_report(commits, stats)

    # 5. "Map" 阶段 (V3.3 保持不变, ai_service 内部已重构)
    ai_diff_summary = None
    if not no_ai and ai_service:
        logger.info("🤖 正在启动 AI 'Map' 阶段 (逐条总结 Diff)...")
        diff_summaries_list = []
        for commit in commits:
            if commit.is_merge_commit:
                logger.info(f"    (跳过 Merge Commit: {commit.hash})")
                continue
            diff_content = git_utils.get_commit_diff(cfg, commit.hash)
            if diff_content:
                single_summary = ai_service.get_single_diff_summary(diff_content)
                if single_summary:
                    diff_summaries_list.append(
                        f"* {commit.hash} ({commit.author}): {single_summary}"
                    )
            else:
                logger.warning(f"    (未能获取 {commit.hash} 的 Diff 内容)")
        if diff_summaries_list:
            ai_diff_summary = "\n".join(diff_summaries_list)
            logger.info("✅ AI 'Map' 阶段完成")
        else:
            logger.info("ℹ️ AI 'Map' 阶段未生成任何 Diff 摘要")

    # 6. "Reduce" 阶段 (V3.3 保持不变, ai_service 内部已重构)
    ai_summary = None
    if not no_ai and ai_service:
        ai_summary = ai_service.get_ai_summary(
            text_report, ai_diff_summary, previous_summary
        )

    # 7. 生成 HTML 报告 (V3.3 保持不变)
    html_content = report_builder.generate_html_report(commits, stats, ai_summary)
    html_filename_full_path = report_builder.save_html_report(html_content, cfg)

    # 8. 更新“记忆”系统 (V3.3 保持不变, ai_service 内部已重构)
    if ai_summary and ai_service:
        log_file_path = os.path.join(cfg.PROJECT_DATA_PATH, cfg.PROJECT_LOG_FILE)
        try:
            log_entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "additions": stats.get("additions", 0),
                "deletions": stats.get("deletions", 0),
                "summary": ai_summary,
            }
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            logger.info(f"✅ 成功追加到项目日志 ({log_file_path})")

            new_compressed_memory = ai_service.distill_project_memory()
            if new_compressed_memory:
                memory_write_path = os.path.join(
                    cfg.PROJECT_DATA_PATH, cfg.PROJECT_MEMORY_FILE
                )
                with open(memory_write_path, "w", encoding="utf-8") as f:
                    f.write(new_compressed_memory)
                logger.info(f"✅ 成功重写压缩记忆 ({memory_write_path})")
        except Exception as e:
            logger.error(f"❌ 更新记忆系统失败: {e}")

    if not html_filename_full_path:
        logger.error("❌ HTML 报告文件生成失败，中止后续操作。")
        return

    # --- (V3.7-MD) 在步骤 9 之前初始化变量 ---
    public_article = None
    article_full_path = None
    # --- (V3.7-MD) 结束 ---

    # 9. 风格转换 (V3.9 使用合并后的 'style' 和 'email' 变量)
    public_article = None
    needs_article = email and attach_format == "pdf"

    if (needs_article) or (not email and style != "default"):
        if ai_summary and previous_summary and not no_ai and ai_service:
            logger.info(f"🤖 启动 V3.6 风格转换 (Style: {style})...")
            public_article = ai_service.generate_public_article(
                ai_summary,
                previous_summary,
                project_readme,
                style=style,
            )
            if public_article:
                article_filename = (
                    f"PublicArticle_{style}_{datetime.now().strftime('%Y%m%d')}.md"
                )
                article_full_path = os.path.join(
                    cfg.PROJECT_DATA_PATH, article_filename
                )
                try:
                    with open(article_full_path, "w", encoding="utf-8") as f:
                        f.write(public_article)
                    logger.info(f"✅ 公众号文章 (Markdown) 已保存: {article_full_path}")

                    if not email:
                        print("\n" + "=" * 50)
                        print(
                            f"📰 AI 生成的公众号文章 (风格: {style}) 预览 (已保存至 {article_full_path}):"
                        )
                        print("=" * 50)
                        print(public_article)
                except Exception as e:
                    logger.error(f"❌ 保存公众号文章失败: {e}")
                    article_full_path = None
        else:
            logger.warning(f"ℹ️ 无法生成风格文章 (缺少 AI 摘要或历史记忆)。")

    # 10. 打印摘要到控制台 (V3.9 使用合并后的 'email' 变量)
    if not email:
        print("\n" + "=" * 50)
        if ai_summary:
            print(f"🤖 AI 工作摘要 (由 {provider_id} 生成):")
            print("=" * 50)
            print(ai_summary)
        else:
            print("📄 原始文本报告 (AI未运行或生成失败):")
            print("=" * 50)
            print(text_report)
        print("=" * 50)

    # 11. 打印统计 (V3.9 使用合并后的 'email' 变量)
    if not email:
        print("\n📊 代码变更统计:")
        print(f"   📈 新增行数: {stats['additions']}")
        print(f"   📉 删除行数: {stats['deletions']}")
        print(f"   📁 修改文件: {stats['files_changed']} (详情已包含在报告中)")
        print(f"   👥 参与作者: {len(set(commit.author for commit in commits))}")

    # 12. (可选) 打开浏览器 (V3.9 使用合并后的 'no_browser' 变量)
    if not no_browser:
        utils.open_report_in_browser(html_filename_full_path)

    # 13. (可选) 发送邮件 (V3.9 使用合并后的 'email', 'attach_format' 变量)
    if email:  # [V3.9] email 现在是一个列表
        logger.info("准备发送邮件...")
        email_body_content = ai_summary if ai_summary else text_report
        if not ai_summary:
            logger.warning("AI 摘要不可用，将使用原始文本报告作为邮件正文。")

        # --- [V3.7-PDF] 核心修改：根据 attach_format 选择附件路径 ---
        attachment_to_send = None
        pdf_full_path = None

        if attach_format == "pdf":
            logger.info(f"💌 附件格式: 'pdf'。")
            if article_full_path:
                logger.info(f"🤖 正在启动 V3.7 PDF 转换 (PrinceXML)...")
                try:
                    pdf_full_path = pdf_converter.convert_md_to_pdf(
                        article_full_path, cfg
                    )
                    if pdf_full_path:
                        attachment_to_send = pdf_full_path
                        logger.info(f"✅ PDF 转换成功: {attachment_to_send}")
                    else:
                        raise Exception("PDF 转换函数返回 None")
                except Exception as e:
                    logger.error(f"❌ PDF 转换失败: {e}")
                    logger.warning(
                        f"   将回退发送 HTML 报告: {html_filename_full_path}"
                    )
                    attachment_to_send = html_filename_full_path
            else:
                logger.warning(f"⚠️ 附件格式: 'pdf'，但风格文章未生成。")
                logger.warning(f"   将回退发送 HTML 报告: {html_filename_full_path}")
                attachment_to_send = html_filename_full_path
        else:
            # 默认 (html)
            attachment_to_send = html_filename_full_path
            logger.info(f"💌 附件格式: 'html'。将发送: {attachment_to_send}")
        # --- [V3.7-PDF] 逻辑结束 ---

        if not attachment_to_send:
            logger.error("❌ 邮件发送失败：找不到任何附件文件 (HTML or PDF)。")
            email_success = False
        else:
            # [V3.9] 调用更新后的 email_sender 函数
            email_success = email_sender.send_email_report(
                cfg,
                email,  # [V3.9] email 是一个列表
                email_body_content,
                attachment_to_send,
            )

        if email_success:
            print("\n[📢 邮件检测: 发送请求成功，请检查收件箱 (包括垃圾邮件)]")
        else:
            print("\n[❌ 邮件检测: 发送失败，请检查终端日志中的详细错误信息和配置]")


# -------------------------------------------------------------------
# 主程序入口
# -------------------------------------------------------------------
if __name__ == "__main__":
    # 1. 设置命令行参数解析
    parser = argparse.ArgumentParser(
        description="Git 工作日报生成器 (V3.9)",  # [V3.9 修改]
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # --- [V3.8/V3.9] 新增/修改的参数 ---
    parser.add_argument(
        "--configure",
        action="store_true",
        help="[V3.8] 运行交互式配置向导。\n" "   (需要 -r 指定要配置的仓库路径)",
    )

    # [V3.9] 新增 cleanup 标志
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

    # --- (V3.2) 互斥参数组 (V3.3 保持不变) ---
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

    # --- [V3.8] 以下参数现在作为 "覆盖" ---

    parser.add_argument(
        "--llm",
        type=str,
        choices=["gemini", "deepseek"],
        default=None,
        help="[V3.4] (覆盖) 指定要使用的 LLM 供应商。\n"
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

    # 2. 解析参数
    try:
        args = parser.parse_args()
        # 3. 调用主流程
        main_flow(args)
    except Exception as e:
        logger.error(f"❌ 发生未处理的全局异常: {e}", exc_info=True)
        sys.exit(1)
