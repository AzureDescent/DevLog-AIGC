# ai_summarizer.py
import logging
import os
import importlib.util
from typing import Optional

# (V4.0) 导入 GlobalConfig 和 RunContext
from config import GlobalConfig
from context import RunContext

# (V4.1) 导入 Registry 和基类
from llm.provider_abc import LLMProvider, PROVIDER_REGISTRY

logger = logging.getLogger(__name__)


# --- (V4.1) 动态加载器 ---
def load_providers_dynamically(script_base_path: str):
    """
    (V4.1) 扫描 llm/ 目录下的所有 .py 文件并导入它们。
    这将触发 @register_provider 装饰器，将类注册到 PROVIDER_REGISTRY 中。
    """
    llm_dir = os.path.join(script_base_path, "llm")
    if not os.path.exists(llm_dir):
        logger.warning(f"⚠️ 未找到 llm 目录: {llm_dir}")
        return

    for filename in os.listdir(llm_dir):
        if filename.endswith("_provider.py") or (
            filename.endswith(".py")
            and filename != "__init__.py"
            and filename != "provider_abc.py"
        ):
            # 构建模块名 (例如: llm.gemini_provider)
            module_name = f"llm.{filename[:-3]}"

            # 如果模块已经在 sys.modules 中，可能不需要重新导入，
            # 但为了确保注册，我们也可以检查 PROVIDER_REGISTRY。
            # 这里我们简单地使用 importlib 确保它被加载。
            try:
                importlib.import_module(module_name)
                # logger.debug(f"ℹ️ 已动态加载模块: {module_name}")
            except Exception as e:
                logger.error(f"❌ 动态加载模块 {module_name} 失败: {e}")


# --- (V4.1) 重构后的工厂函数 ---
def get_llm_provider(provider_id: str, global_config: GlobalConfig) -> LLMProvider:
    """
    (V4.1) 工厂函数：基于 Registry Pattern 实现。
    不再使用硬编码的 if/elif，而是从 PROVIDER_REGISTRY 查找。
    """
    logger.info(f"ℹ️ (V4.1) 正在初始化 LLM 供应商: {provider_id}")

    # 1. 动态加载所有可能的 providers
    load_providers_dynamically(global_config.SCRIPT_BASE_PATH)

    # 2. 检查配置 (is_provider_configured 逻辑保持不变，仍在 global_config 中)
    if not global_config.is_provider_configured(provider_id):
        logger.error(f"❌ 供应商 '{provider_id}' 未配置 API Key。")
        raise ValueError(
            f"供应商 '{provider_id}' 未配置。 "
            f"请在您的 .env 文件中设置相应的 API 密钥。"
        )

    # 3. 从注册表中查找
    if provider_id not in PROVIDER_REGISTRY:
        logger.error(f"❌ 未知的 LLM 供应商: '{provider_id}'")
        logger.error(f"   可用供应商: {list(PROVIDER_REGISTRY.keys())}")
        raise ValueError(f"未知的 LLM 供应商: {provider_id}")

    # 4. 实例化
    try:
        provider_class = PROVIDER_REGISTRY[provider_id]
        return provider_class(global_config)
    except ImportError as e:
        logger.error(f"❌ 供应商 '{provider_id}' 依赖缺失: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ 实例化供应商 '{provider_id}' 失败: {e}")
        raise


# --- (V3.5) AIService (V4.0 重构) ---
class AIService:
    """
    (V4.0 重构) 封装所有对 LLM 的调用。
    - 由 RunContext 初始化。
    - 将 GlobalConfig 传递给 LLMProvider。
    """

    def __init__(self, context: RunContext):
        """
        (V4.0) 初始化 AI 服务
        - 接收 RunContext
        """
        self.context = context
        self.global_config = context.global_config

        # (V4.1) 调用重构后的工厂
        self.provider: LLMProvider = get_llm_provider(
            context.llm_id, self.global_config
        )
        logger.info(
            f"✅ 🤖 AI 服务已成功初始化 (Provider: {self.provider.__class__.__name__})"
        )

    # --- 以下方法保持不变，纯委托逻辑 ---

    def get_single_diff_summary(self, diff_content: str) -> Optional[str]:
        if len(diff_content) > 100000:
            logger.warning(
                f"⚠️ Diff 内容过长 ({len(diff_content)} chars)，跳过 AI 总结。"
            )
            return "(Diff 内容过长，已跳过总结)"
        try:
            summary = self.provider.summarize_diff(diff_content)
            if summary:
                return summary.strip().replace("\n", " ")
            return None
        except Exception as e:
            logger.error(f"❌ (V3.5) get_single_diff_summary 失败: {e}")
            return None

    def get_ai_summary(
        self,
        text_report: str,
        diff_summaries: Optional[str] = None,
        previous_summary: Optional[str] = None,
    ) -> Optional[str]:
        try:
            return self.provider.summarize_report(
                text_report, diff_summaries, previous_summary
            )
        except Exception as e:
            logger.error(f"❌ (V3.5) get_ai_summary 失败: {e}")
            return None

    def distill_project_memory(self) -> Optional[str]:
        logger.info("🧠 正在启动 AI '记忆蒸馏' 阶段...")
        log_file_path = os.path.join(
            self.context.project_data_path, self.global_config.PROJECT_LOG_FILE
        )
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                full_log = f.read()
        except FileNotFoundError:
            logger.info(f"ℹ️ 未找到项目日志 ({log_file_path})，将创建新记忆。")
            return None
        except Exception as e:
            logger.error(f"❌ 读取项目日志失败 ({log_file_path}): {e}")
            return None

        if not full_log.strip():
            logger.info("ℹ️ 项目日志为空，无需蒸馏。")
            return None

        try:
            return self.provider.distill_memory(full_log)
        except Exception as e:
            logger.error(f"❌ (V3.5) distill_project_memory 失败: {e}")
            return None

    def generate_public_article(
        self,
        today_technical_summary: str,
        project_historical_memory: str,
        project_readme: Optional[str] = None,
        style: str = "default",
    ) -> Optional[str]:
        logger.info(f"✍️ 正在启动 AI '风格转换' 阶段 (Style: {style})...")
        try:
            return self.provider.generate_article(
                today_technical_summary,
                project_historical_memory,
                project_readme,
                style=style,
            )
        except Exception as e:
            logger.error(f"❌ (V3.6) generate_public_article (style={style}) 失败: {e}")
            return None
