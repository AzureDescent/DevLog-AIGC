# orchestrator.py
"""
[V4.6] 业务逻辑编排器
- 集成 Context/Orchestrator 模式
- 集成 DataSource (V4.5)
- [V4.6] 集成 Hook 系统 (Lifecycle & Plugins)
"""
import logging
import os
import json
from datetime import datetime
from typing import Optional

# V4.0 导入
from context import RunContext
from config import GlobalConfig

# V4.0 导入服务
from ai_summarizer import AIService
import report_builder
import pdf_converter
import utils

# V4.5 导入数据源工厂
from data_sources.factory import get_data_source

# [V4.6] 导入插件管理器
from hooks.manager import PluginManager

logger = logging.getLogger(__name__)


class ReportOrchestrator:
    """
    (V4.0) 负责执行报告生成的核心业务逻辑。
    """

    def __init__(self, context: RunContext):
        self.context = context
        self.global_config = context.global_config

        # V4.5 初始化数据源
        self.data_source = get_data_source(context)

        # [V4.6] 初始化并加载插件
        self.plugin_manager = PluginManager(context)
        self.plugin_manager.load_plugins()

        logger.info("✅ (V4.6) ReportOrchestrator 已初始化 (含 Hooks)")

    def run(self):
        """
        (V4.0) 执行核心业务流程。
        """

        # --- [V4.6 Hook] 流程开始 ---
        self.plugin_manager.trigger("on_start")

        # --- 0. 验证数据源 ---
        if not self.data_source.validate():
            logger.error("❌ 数据源验证失败，终止运行。")
            return

        # --- 1. AI 实例创建 ---
        ai_service: Optional[AIService] = None
        if not self.context.no_ai:
            try:
                ai_service = AIService(self.context)
            except (ValueError, ImportError) as e:
                logger.error(f"❌ AI 服务初始化失败: {e}")
                logger.error("   将以 --no-ai 模式继续...")
                self.context.no_ai = True

        # --- 2. 读取 README ---
        project_readme = self.data_source.get_readme()

        # --- 3. 读取“压缩记忆” ---
        previous_summary = None
        memory_file_path = os.path.join(
            self.context.project_data_path, self.global_config.PROJECT_MEMORY_FILE
        )
        if not self.context.no_ai:
            try:
                if os.path.exists(memory_file_path):
                    with open(memory_file_path, "r", encoding="utf-8") as f:
                        previous_summary = f.read()
                    logger.info(f"✅ 成功加载压缩记忆: {memory_file_path}")
            except Exception as e:
                logger.error(f"❌ 加载压缩记忆失败 ({memory_file_path}): {e}")

        # --- 4. 获取 Git 数据 ---
        commits = self.data_source.get_commits()

        if not commits:
            logger.error("❌ 未获取到提交记录")
            return

        stats = self.data_source.get_stats()
        stats["total_commits"] = len(commits)

        # --- [V4.6 Hook] 数据就绪 ---
        self.plugin_manager.trigger("on_data_fetched", commits=commits, stats=stats)

        # --- 6. 生成文本报告 ---
        text_report = report_builder.generate_text_report(commits, stats)

        # --- 7. AI "Map" 阶段 ---
        ai_diff_summary = None
        if not self.context.no_ai and ai_service:
            logger.info("🤖 正在启动 AI 'Map' 阶段...")
            diff_summaries_list = []
            for commit in commits:
                if commit.is_merge_commit:
                    continue
                diff_content = self.data_source.get_diff(commit.hash)
                if diff_content:
                    single_summary = ai_service.get_single_diff_summary(diff_content)
                    if single_summary:
                        diff_summaries_list.append(
                            f"* {commit.hash} ({commit.author}): {single_summary}"
                        )
            if diff_summaries_list:
                ai_diff_summary = "\n".join(diff_summaries_list)
                logger.info("✅ AI 'Map' 阶段完成")

        # --- 8. AI "Reduce" 阶段 ---
        ai_summary = None
        if not self.context.no_ai and ai_service:
            ai_summary = ai_service.get_ai_summary(
                text_report, ai_diff_summary, previous_summary
            )

            # --- [V4.6 Hook] AI 摘要生成后 (Filter) ---
            # 允许插件修改摘要内容 (如敏感词过滤)
            if ai_summary:
                ai_summary = self.plugin_manager.filter(
                    "on_ai_summary_generated", ai_summary
                )

        # --- 9. 生成并保存 HTML 报告 ---
        html_content = report_builder.generate_html_report(
            commits, stats, ai_summary, self.global_config
        )

        # --- [V4.6 Hook] HTML 生成后 (Filter) ---
        # 允许插件注入水印、脚本等
        html_content = self.plugin_manager.filter("on_html_generated", html_content)

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
        # (省略文章生成代码，逻辑不变，文章生成通常不需要额外 Hook，除非也加 filter)
        article_full_path = None
        needs_article = (self.context.style != "default") or (
            self.context.attach_format == "pdf"
        )

        if (
            needs_article
            and ai_summary
            and previous_summary
            and not self.context.no_ai
            and ai_service
        ):
            # 重新获取一遍可能的文章内容
            public_article = ai_service.generate_public_article(
                ai_summary, previous_summary, project_readme, style=self.context.style
            )
            if public_article:
                article_filename = f"PublicArticle_{self.context.style}_{datetime.now().strftime('%Y%m%d')}.md"
                article_full_path = os.path.join(
                    self.context.project_data_path, article_filename
                )
                try:
                    with open(article_full_path, "w", encoding="utf-8") as f:
                        f.write(public_article)
                    logger.info(f"✅ 公众号文章已保存: {article_full_path}")
                except Exception as e:
                    logger.error(f"❌ 保存文章失败: {e}")

        # --- 12. 控制台输出 (省略) ---
        if not self.context.email_list and not self.context.no_browser:
            # 仅作示例，保持精简
            pass

        # --- 13. 浏览器打开 ---
        if not self.context.no_browser:
            utils.open_report_in_browser(html_filename_full_path)

        # --- 14. 多渠道通知 ---
        self._handle_notifications(
            ai_summary, text_report, article_full_path, html_filename_full_path
        )

        # --- [V4.6 Hook] 流程结束 ---
        self.plugin_manager.trigger("on_finish")

    def _handle_notifications(
        self, ai_summary, text_report, article_full_path, html_filename_full_path
    ):
        # ... (保持 V4.5 逻辑不变)
        # 为了完整性，这里可以从之前代码复制，但核心在于 run 方法的 hooks
        pass
