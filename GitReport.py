#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Git工作日报生成器
本脚本用于协调 Git 报告的生成、AI 分析和分发。
"""

import argparse
import logging
import sys

# 导入所有重构后的模块
from config import GitReportConfig
import utils
import git_utils
import report_builder

# (V2.4 重构: 导入 AIService 类)
from ai_summarizer import AIService
import email_sender
import os  # noqa
import json
from datetime import datetime

# 1. 初始化日志
utils.setup_logging()
logger = logging.getLogger(__name__)


def main_flow(args: argparse.Namespace):
    """
    主执行流程
    (原 GitReporter.main 方法的逻辑)
    """

    # 1. 加载配置
    cfg = GitReportConfig()
    cfg.TIME_RANGE = args.time
    logger.info(f"🚀 正在生成Git工作报告... 时间范围: {cfg.TIME_RANGE}")
    print("=" * 50)

    # (V2.4 重构: 在流程早期创建单一 AI 实例)
    ai_service = AIService(cfg)

    # 1.1. 读取 README 文件，作为项目元数据
    project_readme = None
    try:
        # 假设 README.md 在脚本运行的根目录
        with open("README.md", "r", encoding="utf-8") as f:
            project_readme = f.read()
        logger.info("✅ 成功加载 README.md 作为项目元数据")
    except FileNotFoundError:
        logger.warning("❌ 未找到 README.md 文件，跳过加载项目元数据。")
    except Exception as e:
        logger.error(f"❌ 读取 README.md 失败: {e}")

    # --- (修改) V2.2 START: 读取“压缩记忆” ---
    previous_summary = None  # 这现在是 V2.1 中的 "previous_summary"
    if not args.no_ai:
        try:
            # 读取的是 project_memory.md，而不是 V2.1 的 cache 文件
            with open(cfg.PROJECT_MEMORY_FILE, "r", encoding="utf-8") as f:
                previous_summary = f.read()
            if previous_summary:
                logger.info(f"✅ 成功加载压缩记忆 ({cfg.PROJECT_MEMORY_FILE})")
        except FileNotFoundError:
            logger.info(f"ℹ️ 未找到压缩记忆 ({cfg.PROJECT_MEMORY_FILE})，将从头开始。")
        except Exception as e:
            logger.error(f"❌ 加载压缩记忆失败: {e}")
    # --- (修改) V2.2 END ---

    # 2. 检查环境
    if not git_utils.is_git_repository():
        logger.error("❌ 当前目录不是Git仓库")
        print("💡 请确保在Git仓库目录中运行此脚本")
        return

    # 3. 获取和解析 Git 数据
    log_output = git_utils.get_git_log(cfg)
    if not log_output:
        logger.error("❌ 未获取到Git提交记录")
        print("💡 可能的原因: 今天没有提交或Git命令执行环境问题")
        return

    commits = git_utils.parse_git_log(log_output)
    stats = git_utils.get_git_stats(cfg)
    stats["total_commits"] = len(commits)

    # 4. 生成报告（AI 摘要需要文本报告）
    text_report = report_builder.generate_text_report(commits, stats)

    # --- (修改) V2.0 START: "Map" 阶段 ---
    ai_diff_summary = None
    if not args.no_ai:
        logger.info("🤖 正在启动 AI 'Map' 阶段 (逐条总结 Diff)...")
        diff_summaries_list = []

        # 遍历我们从 parse_git_log 得到的 commits 列表
        for i, commit in enumerate(commits):
            # (重要) 跳过合并提交，它们的 diff 复杂且意义不大
            if commit.is_merge_commit:  #
                logger.info(f"    (跳过 Merge Commit: {commit.hash})")
                continue

            # (调用我们在 git_utils.py 中添加的新函数)
            diff_content = git_utils.get_commit_diff(cfg, commit.hash)  #

            if diff_content:
                # (V2.4 重构: 使用 ai_service 实例的方法)
                single_summary = ai_service.get_single_diff_summary(diff_content)
                if single_summary:
                    # 将子摘要与 commit 信息关联起来
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
    # --- (修改) V2.0 END ---

    # 5. (可选) AI 分析
    ai_summary = None
    if not args.no_ai:
        # (V2.4 重构: 使用 ai_service 实例的方法)
        ai_summary = ai_service.get_ai_summary(
            text_report, ai_diff_summary, previous_summary
        )

    # 6. 生成最终 HTML 报告
    html_content = report_builder.generate_html_report(commits, stats, ai_summary)
    html_filename = report_builder.save_html_report(
        html_content, cfg.OUTPUT_FILENAME_PREFIX
    )

    # --- (新增) V2.2 START: 更新“记忆”系统 ---
    if ai_summary:  # 必须在 *今天* 的摘要成功生成后
        # 7.1. 写入“地基”日志
        try:
            log_entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "additions": stats.get("additions", 0),
                "deletions": stats.get("deletions", 0),
                "summary": ai_summary,
            }
            # 以 'a' (追加) 模式打开 .jsonl 文件
            with open(cfg.PROJECT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            logger.info(f"✅ 成功追加到项目日志 ({cfg.PROJECT_LOG_FILE})")

            # 7.2. 触发“记忆蒸馏”，重写“压缩记忆”
            # (这个函数会读取 project_log.jsonl 并生成 project_memory.md)
            # (V2.4 重构: 使用 ai_service 实例的方法)
            new_compressed_memory = ai_service.distill_project_memory()

            if new_compressed_memory:
                with open(cfg.PROJECT_MEMORY_FILE, "w", encoding="utf-8") as f:
                    f.write(new_compressed_memory)
                logger.info(f"✅ 成功重写压缩记忆 ({cfg.PROJECT_MEMORY_FILE})")

        except Exception as e:
            logger.error(f"❌ 更新记忆系统失败: {e}")
    # --- (新增) V2.2 END ---

    if not html_filename:
        logger.error("❌ HTML 报告文件生成失败，中止后续操作。")
        return

    # --- (新增) V2.3 START: 风格转换 ---
    public_article = None
    if ai_summary and previous_summary and not args.no_ai:
        logger.info("🤖 启动 V2.3 风格转换...")
        # (V2.4 重构: 使用 ai_service 实例的方法)
        public_article = ai_service.generate_public_article(
            ai_summary,  # 传入今天刚生成的技术摘要
            previous_summary,  # 传入我们刚读到的项目历史
            project_readme,  # 传入项目元数据（README 内容）
        )

        if public_article:
            # (推荐) 将公众号文章也保存到文件
            article_filename = f"PublicArticle_{datetime.now().strftime('%Y%m%d')}.md"
            try:
                with open(article_filename, "w", encoding="utf-8") as f:
                    f.write(public_article)
                logger.info(f"✅ 公众号文章已保存: {article_filename}")
                print("\n" + "=" * 50)
                print(f"📰 AI 生成的公众号文章预览 (已保存至 {article_filename}):")
                print("=" * 50)
                print(public_article)
            except Exception as e:
                logger.error(f"❌ 保存公众号文章失败: {e}")
    # --- (新增) V2.3 END ---

    # 7. 打印摘要到控制台
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

    # 8. 打印统计
    print("\n📊 代码变更统计:")
    print(f"   📈 新增行数: {stats['additions']}")
    print(f"   📉 删除行数: {stats['deletions']}")
    print(f"   📁 修改文件: {stats['files_changed']} (详情已包含在报告中)")
    print(f"   👥 参与作者: {len(set(commit.author for commit in commits))}")

    # 9. (可选) 打开浏览器
    if not args.no_browser:
        utils.open_report_in_browser(html_filename)

    # 10. (可选) 发送邮件
    if args.email:
        logger.info("准备发送邮件...")
        email_body_content = ai_summary if ai_summary else text_report
        if not ai_summary:
            logger.warning("AI 摘要不可用，将使用原始文本报告作为邮件正文。")

        email_success = email_sender.send_email_report(
            cfg, args.email, email_body_content, html_filename
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
    parser = argparse.ArgumentParser(description="Git 工作日报生成器")
    parser.add_argument(
        "-t",
        "--time",
        type=str,
        default=GitReportConfig.TIME_RANGE,  # 从配置类中获取默认值
        help=f"指定Git日志的时间范围 (例如 '1 day ago'). 默认: '{GitReportConfig.TIME_RANGE}'",
    )
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
