# hooks/manager.py
import logging
import os
import importlib.util
import inspect
from typing import List, Any
from context import RunContext
from .base import BasePlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """
    [V4.6] 插件管理器
    负责从 plugins/ 目录动态加载脚本，并管理钩子调用链。
    """

    def __init__(self, context: RunContext):
        self.context = context
        self.plugins: List[BasePlugin] = []

    def load_plugins(self):
        """
        从项目根目录下的 'plugins' 文件夹加载 .py 插件。
        """
        # 假设 plugins 目录位于脚本根路径下
        plugins_dir = os.path.join(
            self.context.global_config.SCRIPT_BASE_PATH, "plugins"
        )

        if not os.path.exists(plugins_dir):
            # 目录不存在则跳过，这不是错误
            return

        logger.info(f"🔌 [Hooks] 正在扫描插件目录: {plugins_dir}")

        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                plugin_path = os.path.join(plugins_dir, filename)
                self._load_plugin_from_file(plugin_path)

    def _load_plugin_from_file(self, filepath: str):
        """动态加载单个插件文件"""
        try:
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 查找模块中所有继承自 BasePlugin 的类
                loaded_count = 0
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BasePlugin)
                        and obj is not BasePlugin
                    ):

                        plugin_instance = obj()
                        self.register(plugin_instance)
                        loaded_count += 1
                        logger.info(f"   ✅ [Hooks] 已加载插件: {plugin_instance.name}")

                if loaded_count == 0:
                    logger.warning(
                        f"   ⚠️ [Hooks] 文件 {filepath} 中未发现 BasePlugin 子类"
                    )

        except Exception as e:
            logger.error(f"❌ [Hooks] 加载插件失败 {filepath}: {e}")

    def register(self, plugin: BasePlugin):
        """手动注册插件实例"""
        self.plugins.append(plugin)

    def trigger(self, event_name: str, *args, **kwargs):
        """
        触发无返回值的通知型钩子 (如 on_start)。
        """
        for plugin in self.plugins:
            method = getattr(plugin, event_name, None)
            if method:
                try:
                    method(self.context, *args, **kwargs)
                except Exception as e:
                    logger.error(
                        f"❌ [Hooks] 插件 {plugin.name} 执行 {event_name} 失败: {e}"
                    )

    def filter(self, event_name: str, initial_value: Any, *args, **kwargs) -> Any:
        """
        触发链式处理型钩子 (如 on_ai_summary_generated)。
        初始值会依次经过所有插件的处理，类似于管道 (Pipeline)。
        """
        value = initial_value
        for plugin in self.plugins:
            method = getattr(plugin, event_name, None)
            if method:
                try:
                    new_value = method(self.context, value, *args, **kwargs)
                    # 如果插件返回了新值，则更新；如果返回 None，则保持原值
                    if new_value is not None:
                        value = new_value
                except Exception as e:
                    logger.error(
                        f"❌ [Hooks] 插件 {plugin.name} 执行 {event_name} 失败: {e}"
                    )
        return value
