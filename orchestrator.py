# orchestrator.py
"""
[V4.0] 业务逻辑编排器
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
import email_sender
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
        这是从 V3.9 的 main_flow() 迁移而来的逻辑。
        """

        # --- (V3.4) AI 实例创建 (V4.0 重构) ---
        ai_service: Optional[AIService] = None
        if not self.context.no_ai:
            try:
                # (V4.0) AIService 现在接收 RunContext
                ai_service = AIService(self.context)
            except (ValueError, ImportError) as e:
                logger.error(f"❌ (V3.4) AI 服务初始化失败: {e}")
                logger.error("   请检查您的 .env 文件是否已正确配置。")
                logger.error("   将以 --no-ai 模式继续...")
                self.context.no_ai = True  # (V4.0) 更新上下文状态

        # --- (V3.0) 读取 README (V4.0 重构) ---
        project_readme = None
        # (V4.0) 使用 context.repo_path
        readme_path = os.path.join(self.context.repo_path, "README.md")
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                project_readme = f.read()
            logger.info(f"✅ 成功加载目标仓库 README: {readme_path}")
        except FileNotFoundError:
            logger.warning(f"❌ 未在目标仓库找到 README.md，跳过加载。 ({readme_path})")
        except Exception as e:
            logger.error(f"❌ 读取 README.md 失败 ({readme_path}): {e}")

        # --- (V3.1) 读取“压缩记忆” (V4.0 重构) ---
        previous_summary = None
        # (V4.0) 使用 context.project_data_path 和 global_config
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

        # 2. 检查环境 (V4.0 重构)
        # (V4.0) 使用 context.repo_path
        if not git_utils.is_git_repository(self.context.repo_path):
            logger.error(f"❌ 指定路径不是Git仓库: {self.context.repo_path}")
            return

        # 3. 获取和解析 Git 数据 (V4.0 重构)
        # (V4.0) git_utils 函数现在接收 RunContext
        log_output = git_utils.get_git_log(self.context)
        if not log_output:
            logger.error("❌ 未获取到Git提交记录")
            # (V4.0) 使用 context.time_range_desc
            print(f"💡 提示: 在 '{self.context.time_range_desc}' 范围内可能没有提交。")
            return

        commits = git_utils.parse_git_log(log_output)
        # (V4.0) git_utils 函数现在接收 RunContext
        stats = git_utils.get_git_stats(self.context)
        stats["total_commits"] = len(commits)

        # 4. 生成报告 (V4.0 未变)
        text_report = report_builder.generate_text_report(commits, stats)

        # 5. "Map" 阶段 (V4.0 重构)
        ai_diff_summary = None
        if not self.context.no_ai and ai_service:
            logger.info("🤖 正在启动 AI 'Map' 阶段 (逐条总结 Diff)...")
            diff_summaries_list = []
            for commit in commits:
                if commit.is_merge_commit:
                    logger.info(f"    (跳过 Merge Commit: {commit.hash})")
                    continue
                # (V4.0) git_utils 函数现在接收 RunContext
                diff_content = git_utils.get_commit_diff(self.context, commit.hash)
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

        # 6. "Reduce" 阶段 (V4.0 未变)
        ai_summary = None
        if not self.context.no_ai and ai_service:
            ai_summary = ai_service.get_ai_summary(
                text_report, ai_diff_summary, previous_summary
            )

        # 7. 生成 HTML 报告 (V4.0 重构)
        html_content = report_builder.generate_html_report(
            commits, stats, ai_summary, self.global_config  # (V4.0) 传入 global_config
        )
        # (V4.0) report_builder 函数现在接收 RunContext
        html_filename_full_path = report_builder.save_html_report(
            html_content, self.context
        )

        # 8. 更新“记忆”系统 (V4.0 重构)
        if ai_summary and ai_service:
            # (V4.0) 使用 context 和 global_config
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
                logger.info(f"✅ 成功追加到项目日志 ({log_file_path})")

                # (V4.0) ai_service 内部已重构为使用 context
                new_compressed_memory = ai_service.distill_project_memory()
                if new_compressed_memory:
                    memory_write_path = os.path.join(
                        self.context.project_data_path,
                        self.global_config.PROJECT_MEMORY_FILE,  # (V4.0)
                    )
                    with open(memory_write_path, "w", encoding="utf-8") as f:
                        f.write(new_compressed_memory)
                    logger.info(f"✅ 成功重写压缩记忆 ({memory_write_path})")
            except Exception as e:
                logger.error(f"❌ 更新记忆系统失败: {e}")

        if not html_filename_full_path:
            logger.error("❌ HTML 报告文件生成失败，中止后续操作。")
            return

        # 9. 风格转换 (V4.0 重构)
        public_article = None
        article_full_path = None
        # (V4.0) 使用 context
        needs_article = self.context.email_list and self.context.attach_format == "pdf"

        if (needs_article) or (
            not self.context.email_list and self.context.style != "default"
        ):
            if (
                ai_summary
                and previous_summary
                and not self.context.no_ai
                and ai_service
            ):
                logger.info(f"🤖 启动 V3.6 风格转换 (Style: {self.context.style})...")
                public_article = ai_service.generate_public_article(
                    ai_summary,
                    previous_summary,
                    project_readme,
                    style=self.context.style,  # (V4.0)
                )
                if public_article:
                    article_filename = f"PublicArticle_{self.context.style}_{datetime.now().strftime('%Y%m%d')}.md"
                    article_full_path = os.path.join(
                        self.context.project_data_path, article_filename  # (V4.0)
                    )
                    try:
                        with open(article_full_path, "w", encoding="utf-8") as f:
                            f.write(public_article)
                        logger.info(
                            f"✅ 公众号文章 (Markdown) 已保存: {article_full_path}"
                        )

                        if not self.context.email_list:  # (V4.0)
                            print("\n" + "=" * 50)
                            print(
                                f"📰 AI 生成的公众号文章 (风格: {self.context.style}) 预览 (已保存至 {article_full_path}):"
                            )
                            print("=" * 50)
                            print(public_article)
                    except Exception as e:
                        logger.error(f"❌ 保存公众号文章失败: {e}")
                        article_full_path = None
            else:
                logger.warning(f"ℹ️ 无法生成风格文章 (缺少 AI 摘要或历史记忆)。")

        # 10. 打印摘要到控制台 (V4.0 重构)
        if not self.context.email_list:  # (V4.0)
            print("\n" + "=" * 50)
            if ai_summary:
                print(f"🤖 AI 工作摘要 (由 {self.context.llm_id} 生成):")  # (V4.0)
                print("=" * 50)
                print(ai_summary)
            else:
                print("📄 原始文本报告 (AI未运行或生成失败):")
                print("=" * 50)
                print(text_report)
            print("=" * 50)

        # 11. 打印统计 (V4.0 重构)
        if not self.context.email_list:  # (V4.0)
            print("\n📊 代码变更统计:")
            print(f"   📈 新增行数: {stats['additions']}")
            print(f"   📉 删除行数: {stats['deletions']}")
            print(f"   📁 修改文件: {stats['files_changed']} (详情已包含在报告中)")
            print(f"   👥 参与作者: {len(set(commit.author for commit in commits))}")

        # 12. (可选) 打开浏览器 (V4.0 重构)
        if not self.context.no_browser:  # (V4.0)
            utils.open_report_in_browser(html_filename_full_path)

        # 13. [V4.3 重构] 多渠道通知分发
        # 13.1 准备通知内容
        notification_subject = f"Git工作日报 - {datetime.now().strftime('%Y-%m-%d')}"

        # 优先使用 AI 摘要作为正文，如果没有则回退到文本报告
        # 注意：如果是 HTML 邮件，EmailNotifier 会自己处理包装；
        # 如果是文本消息（如飞书），可能需要纯文本。
        # 这里我们传递最丰富的内容，由具体 Notifier 决定如何渲染。
        notification_content = ai_summary if ai_summary else text_report

        # 13.2 准备附件 (PDF or HTML)
        attachment_to_send = None
        pdf_full_path = None

        # 检查是否需要生成 PDF (仅当有通知渠道激活 且 指定了 pdf 格式时)
        # 为了简单起见，我们先准备好所有可能的附件路径
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

        # 13.3 加载并执行所有激活的通知器
        # (V4.3) 导入工厂
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
