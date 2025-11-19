# orchestrator.py
"""
[V4.4] 业务逻辑编排器
- 集成 Context/Orchestrator 模式
- [V4.3] 集成多渠道通知系统 (Notifiers)，移除 email_sender 强依赖
"""
import logging
import sys
import os
import json
from datetime import datetime
from typing import Optional

# V4.0 导入
from context import RunContext
from config import GlobalConfig

# V4.0 导入服务
from ai_summarizer import AIService
import git_utils
import report_builder

# import email_sender  <-- [已移除] 旧的邮件发送模块
import pdf_converter
import utils

logger = logging.getLogger(__name__)


class ReportOrchestrator:
    """
    (V4.0) 负责执行报告生成的核心业务逻辑。
    完全由 RunContext 驱动。
    """

    def __init__(self, context: RunContext):
        """
        初始化编排器，接收所有运行时配置。
        """
        self.context = context
        self.global_config = context.global_config
        logger.info("✅ (V4.0) ReportOrchestrator 已初始化")

    def run(self):
        """
        (V4.0) 执行核心业务流程。
        """

        # --- 1. AI 实例创建 ---
        ai_service: Optional[AIService] = None
        if not self.context.no_ai:
            try:
                ai_service = AIService(self.context)
            except (ValueError, ImportError) as e:
                logger.error(f"❌ (V3.4) AI 服务初始化失败: {e}")
                logger.error("   请检查您的 .env 文件是否已正确配置。")
                logger.error("   将以 --no-ai 模式继续...")
                self.context.no_ai = True

        # --- 2. 读取 README ---
        project_readme = None
        readme_path = os.path.join(self.context.repo_path, "README.md")
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                project_readme = f.read()
            logger.info(f"✅ 成功加载目标仓库 README: {readme_path}")
        except FileNotFoundError:
            logger.warning(f"❌ 未在目标仓库找到 README.md，跳过加载。 ({readme_path})")
        except Exception as e:
            logger.error(f"❌ 读取 README.md 失败 ({readme_path}): {e}")

        # --- 3. 读取“压缩记忆” ---
        previous_summary = None
        memory_file_path = os.path.join(
            self.context.project_data_path, self.global_config.PROJECT_MEMORY_FILE
        )
        if not self.context.no_ai:
            try:
                with open(memory_file_path, "r", encoding="utf-8") as f:
                    previous_summary = f.read()
                if previous_summary:
                    logger.info(f"✅ 成功加载压缩记忆: {memory_file_path}")
            except FileNotFoundError:
                logger.info(f"ℹ️ 未找到压缩记忆 ({memory_file_path})，将从头开始。")
            except Exception as e:
                logger.error(f"❌ 加载压缩记忆失败 ({memory_file_path}): {e}")

        # --- 4. 检查 Git 环境 ---
        if not git_utils.is_git_repository(self.context.repo_path):
            logger.error(f"❌ 指定路径不是Git仓库: {self.context.repo_path}")
            return

        # --- 5. 获取 Git 数据 ---
        log_output = git_utils.get_git_log(self.context)
        if not log_output:
            logger.error("❌ 未获取到Git提交记录")
            print(f"💡 提示: 在 '{self.context.time_range_desc}' 范围内可能没有提交。")
            return

        commits = git_utils.parse_git_log(log_output)
        stats = git_utils.get_git_stats(self.context)
        stats["total_commits"] = len(commits)

        # --- 6. 生成文本报告 (基础数据) ---
        text_report = report_builder.generate_text_report(commits, stats)

        # --- 7. AI "Map" 阶段 (Diff 分析) ---
        ai_diff_summary = None
        if not self.context.no_ai and ai_service:
            logger.info("🤖 正在启动 AI 'Map' 阶段 (逐条总结 Diff)...")
            diff_summaries_list = []
            for commit in commits:
                if commit.is_merge_commit:
                    continue
                diff_content = git_utils.get_commit_diff(self.context, commit.hash)
                if diff_content:
                    single_summary = ai_service.get_single_diff_summary(diff_content)
                    if single_summary:
                        diff_summaries_list.append(
                            f"* {commit.hash} ({commit.author}): {single_summary}"
                        )
            if diff_summaries_list:
                ai_diff_summary = "\n".join(diff_summaries_list)
                logger.info("✅ AI 'Map' 阶段完成")

        # --- 8. AI "Reduce" 阶段 (日报汇总) ---
        ai_summary = None
        if not self.context.no_ai and ai_service:
            ai_summary = ai_service.get_ai_summary(
                text_report, ai_diff_summary, previous_summary
            )

        # --- 9. 生成并保存 HTML 报告 ---
        html_content = report_builder.generate_html_report(
            commits, stats, ai_summary, self.global_config
        )
        html_filename_full_path = report_builder.save_html_report(
            html_content, self.context
        )

        if not html_filename_full_path:
            logger.error("❌ HTML 报告文件生成失败，中止后续操作。")
            return

        # --- 10. 更新“记忆”系统 ---
        if ai_summary and ai_service:
            log_file_path = os.path.join(
                self.context.project_data_path, self.global_config.PROJECT_LOG_FILE
            )
            try:
                log_entry = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "additions": stats.get("additions", 0),
                    "deletions": stats.get("deletions", 0),
                    "summary": ai_summary,
                }
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

                new_compressed_memory = ai_service.distill_project_memory()
                if new_compressed_memory:
                    memory_write_path = os.path.join(
                        self.context.project_data_path,
                        self.global_config.PROJECT_MEMORY_FILE,
                    )
                    with open(memory_write_path, "w", encoding="utf-8") as f:
                        f.write(new_compressed_memory)
                    logger.info(f"✅ 成功重写压缩记忆 ({memory_write_path})")
            except Exception as e:
                logger.error(f"❌ 更新记忆系统失败: {e}")

        # --- 11. 风格转换 (Markdown 文章) ---
        article_full_path = None
        # 只要 style 不是默认，或者需要 PDF 附件，就生成文章
        needs_article = (self.context.style != "default") or (
            self.context.attach_format == "pdf"
        )

        if needs_article:
            if (
                ai_summary
                and previous_summary
                and not self.context.no_ai
                and ai_service
            ):
                logger.info(f"🤖 启动风格转换 (Style: {self.context.style})...")
                public_article = ai_service.generate_public_article(
                    ai_summary,
                    previous_summary,
                    project_readme,
                    style=self.context.style,
                )
                if public_article:
                    article_filename = f"PublicArticle_{self.context.style}_{datetime.now().strftime('%Y%m%d')}.md"
                    article_full_path = os.path.join(
                        self.context.project_data_path, article_filename
                    )
                    try:
                        with open(article_full_path, "w", encoding="utf-8") as f:
                            f.write(public_article)
                        logger.info(
                            f"✅ 公众号文章 (Markdown) 已保存: {article_full_path}"
                        )

                        # 仅当不发送邮件时才在控制台打印预览
                        if not self.context.email_list:
                            print("\n" + "=" * 50)
                            print(f"📰 文章预览 ({self.context.style}):")
                            print("=" * 50)
                            print(public_article)
                    except Exception as e:
                        logger.error(f"❌ 保存公众号文章失败: {e}")
                        article_full_path = None

        # --- 12. 打印摘要到控制台 (仅当不发邮件时) ---
        if not self.context.email_list:
            print("\n" + "=" * 50)
            if ai_summary:
                print(f"🤖 AI 工作摘要 (由 {self.context.llm_id} 生成):")
                print("=" * 50)
                print(ai_summary)
            else:
                print("📄 原始文本报告 (AI未运行或生成失败):")
                print(text_report)

        # --- 13. 打印统计 ---
        if not self.context.email_list:
            print(
                f"\n📊 新增: {stats['additions']} 行, 删除: {stats['deletions']} 行, 文件: {stats['files_changed']}"
            )

        # --- 14. 打开浏览器 ---
        if not self.context.no_browser:
            utils.open_report_in_browser(html_filename_full_path)

        # =================================================================
        # --- 15. [V4.3 重构] 多渠道通知分发 ---
        # =================================================================

        # 15.1 准备通知内容
        notification_subject = f"Git工作日报 - {datetime.now().strftime('%Y-%m-%d')}"
        # 优先使用 AI 摘要作为正文，如果没有则回退到文本报告
        notification_content = ai_summary if ai_summary else text_report

        # 15.2 准备附件 (PDF or HTML)
        attachment_to_send = None

        if self.context.attach_format == "pdf":
            if article_full_path:
                logger.info(f"🤖 正在启动 PDF 转换 (用于附件发送)...")
                pdf_full_path = pdf_converter.convert_md_to_pdf(
                    article_full_path, self.context
                )
                if pdf_full_path:
                    attachment_to_send = pdf_full_path
                else:
                    logger.warning("⚠️ PDF 转换失败，回退使用 HTML 附件。")
                    attachment_to_send = html_filename_full_path
            else:
                logger.warning("⚠️ 指定了 PDF 格式但未生成文章，回退使用 HTML 附件。")
                attachment_to_send = html_filename_full_path
        else:
            # 默认 HTML
            attachment_to_send = html_filename_full_path

        # 15.3 加载并执行所有激活的通知器
        try:
            # [V4.3] 动态导入工厂，避免顶层 import 错误
            from notifiers.factory import get_active_notifiers

            active_notifiers = get_active_notifiers(self.context)

            if not active_notifiers:
                logger.info("ℹ️ 没有激活任何通知渠道 (未配置邮箱或 Webhook)，跳过发送。")
            else:
                logger.info(f"🚀 开始通过 {len(active_notifiers)} 个渠道推送报告...")
                for notifier in active_notifiers:
                    logger.info(f"   >> 正在调用: {notifier.name}")
                    success = notifier.send(
                        subject=notification_subject,
                        content=notification_content,
                        attachment_path=attachment_to_send,
                    )
                    status_icon = "✅" if success else "❌"
                    print(
                        f"[{status_icon} 推送结果] {notifier.name}: {'成功' if success else '失败'}"
                    )

        except ImportError:
            logger.error(
                "❌ 无法导入 notifiers.factory。请确保 notifiers 目录存在且包含 __init__.py (或作为 namespace package)。"
            )
        except Exception as e:
            logger.error(f"❌ 通知分发过程发生异常: {e}", exc_info=True)
