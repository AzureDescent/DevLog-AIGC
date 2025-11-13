"""
Git工作日报生成器 (V3.2)
本脚本用于协调 Git 报告的生成、AI 分析和分发。
- V3.2: 增加 -n/--number 参数，与 -t 互斥。
"""

import argparse
import logging
import sys
import os
import json
from datetime import datetime

# 导入所有重构后的模块
from config import GitReportConfig
import utils
import git_utils
import report_builder
from ai_summarizer import AIService
import email_sender

# 1. 初始化日志
utils.setup_logging()
logger = logging.getLogger(__name__)


def main_flow(args: argparse.Namespace):
    """
    主执行流程
    (V3.2 重构)
    """

    # 1. 加载配置
    cfg = GitReportConfig()

    # --- (V3.0) 设置 REPO_PATH ---
    cfg.REPO_PATH = os.path.abspath(args.repo_path)

    # --- (新增) V3.2: 根据互斥参数设置范围 ---
    # args.number 存在 (用户使用了 -n 5)
    if args.number:
        cfg.COMMIT_RANGE_ARG = f"-n {args.number}"
        cfg.TIME_RANGE_DESCRIPTION = f"最近 {args.number} 次提交"
    # 默认或用户使用了 -t '...'
    else:
        # 如果用户 -t 和 -n 都没指定，args.time 会是 None，我们设置默认值
        time_str = args.time if args.time else "1 day ago"
        cfg.COMMIT_RANGE_ARG = f'--since="{time_str}"'
        cfg.TIME_RANGE_DESCRIPTION = time_str
    # --- (V3.2 结束) ---

    # --- (V3.1) 构建项目专属数据路径 ---
    try:
        if os.path.basename(cfg.REPO_PATH) == ".":
            project_name = "current_dir_project"
        else:
            project_name = os.path.basename(cfg.REPO_PATH)
        data_root_path = os.path.join(cfg.SCRIPT_BASE_PATH, cfg.DATA_ROOT_DIR_NAME)
        cfg.PROJECT_DATA_PATH = os.path.join(data_root_path, project_name)
        os.makedirs(cfg.PROJECT_DATA_PATH, exist_ok=True)
    except Exception as e:
        logger.error(f"❌ (V3.1) 创建项目数据目录失败: {e}")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info(f"🚀 (V3.2) DevLog-AIGC 启动...")
    logger.info(f"   [目标仓库 (REPO_PATH)]: {cfg.REPO_PATH}")
    logger.info(f"   [数据存储 (DATA_PATH)]: {cfg.PROJECT_DATA_PATH}")
    # --- (V3.2) 修改: 使用 TIME_RANGE_DESCRIPTION ---
    logger.info(f"   [分析范围]: {cfg.TIME_RANGE_DESCRIPTION}")
    logger.info("=" * 50)

    # (V2.4) 创建 AI 实例
    ai_service = AIService(cfg)

    # --- (V3.0) 读取 README ---
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

    # --- (V3.1) 读取“压缩记忆” ---
    previous_summary = None
    memory_file_path = os.path.join(cfg.PROJECT_DATA_PATH, cfg.PROJECT_MEMORY_FILE)
    if not args.no_ai:
        try:
            with open(memory_file_path, "r", encoding="utf-8") as f:
                previous_summary = f.read()
            if previous_summary:
                logger.info(f"✅ 成功加载压缩记忆: {memory_file_path}")
        except FileNotFoundError:
            logger.info(f"ℹ️ 未找到压缩记忆 ({memory_file_path})，将从头开始。")
        except Exception as e:
            logger.error(f"❌ 加载压缩记忆失败 ({memory_file_path}): {e}")

    # 2. 检查环境 (V3.0 不变)
    if not git_utils.is_git_repository(cfg.REPO_PATH):
        logger.error(f"❌ 指定路径不是Git仓库: {cfg.REPO_PATH}")
        return

    # 3. 获取和解析 Git 数据 (V3.2: 内部已适配)
    log_output = git_utils.get_git_log(cfg)
    if not log_output:
        logger.error("❌ 未获取到Git提交记录")
        print(f"💡 提示: 在 '{cfg.TIME_RANGE_DESCRIPTION}' 范围内可能没有提交。")
        return

    commits = git_utils.parse_git_log(log_output)
    stats = git_utils.get_git_stats(cfg)
    stats["total_commits"] = len(commits)

    # 4. 生成报告
    text_report = report_builder.generate_text_report(commits, stats)

    # 5. "Map" 阶段
    ai_diff_summary = None
    if not args.no_ai:
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

    # 6. "Reduce" 阶段
    ai_summary = None
    if not args.no_ai:
        ai_summary = ai_service.get_ai_summary(
            text_report, ai_diff_summary, previous_summary
        )

    # 7. 生成 HTML 报告
    html_content = report_builder.generate_html_report(commits, stats, ai_summary)
    html_filename_full_path = report_builder.save_html_report(html_content, cfg)

    # 8. 更新“记忆”系统
    if ai_summary:
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

    # 9. 风格转换
    public_article = None
    if ai_summary and previous_summary and not args.no_ai:
        logger.info("🤖 启动 V2.3 风格转换...")
        public_article = ai_service.generate_public_article(
            ai_summary,
            previous_summary,
            project_readme,
        )
        if public_article:
            article_filename = f"PublicArticle_{datetime.now().strftime('%Y%m%d')}.md"
            article_full_path = os.path.join(cfg.PROJECT_DATA_PATH, article_filename)
            try:
                with open(article_full_path, "w", encoding="utf-8") as f:
                    f.write(public_article)
                logger.info(f"✅ 公众号文章已保存: {article_full_path}")
                print("\n" + "=" * 50)
                print(f"📰 AI 生成的公众号文章预览 (已保存至 {article_full_path}):")
                print("=" * 50)
                print(public_article)
            except Exception as e:
                logger.error(f"❌ 保存公众号文章失败: {e}")

    # 10. 打印摘要到控制台
    print("\n" + "=" * 50)
    if ai_summary:
        print("🤖 AI 工作摘要:")
        print("=" * 50)
        print(ai_summary)
    else:
        print("📄 原始文本报告 (AI未运行或生成失败):")
        print("=" * 50)
        print(text_report)
    print("=" * 50)

    # 11. 打印统计
    print("\n📊 代码变更统计:")
    print(f"   📈 新增行数: {stats['additions']}")
    print(f"   📉 删除行数: {stats['deletions']}")
    print(f"   📁 修改文件: {stats['files_changed']} (详情已包含在报告中)")
    print(f"   👥 参与作者: {len(set(commit.author for commit in commits))}")

    # 12. (可选) 打开浏览器
    if not args.no_browser:
        utils.open_report_in_browser(html_filename_full_path)

    # 13. (可选) 发送邮件
    if args.email:
        logger.info("准备发送邮件...")
        email_body_content = ai_summary if ai_summary else text_report
        if not ai_summary:
            logger.warning("AI 摘要不可用，将使用原始文本报告作为邮件正文。")
        email_success = email_sender.send_email_report(
            cfg,
            args.email,
            email_body_content,
            html_filename_full_path,
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
        description="Git 工作日报生成器 (V3.2)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # --- (V3.0) repo-path 参数 ---
    parser.add_argument(
        "-r",
        "--repo-path",
        type=str,
        default=".",
        help="[V3.0] 指定要分析的 Git 仓库的根目录路径。\n(默认: '.')",
    )

    # --- (新增) V3.2: 创建互斥参数组 ---
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
    # --- (V3.2 结束) ---

    parser.add_argument("--no-ai", action="store_true", help="禁用 AI 摘要功能")
    parser.add_argument(
        "--no-browser", action="store_true", help="不自动在浏览器中打开报告"
    )
    parser.add_argument("-e", "--email", type=str, help="报告生成后发送邮件到指定地址")

    # 2. 解析参数
    try:
        args = parser.parse_args()
        # 3. 调用主流程
        main_flow(args)
    except Exception as e:
        logger.error(f"❌ 发生未处理的全局异常: {e}", exc_info=True)
        sys.exit(1)
