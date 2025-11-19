# test_registry.py
import unittest
import os
import logging

# 导入核心模块
from config import GlobalConfig
from context import RunContext
from ai_summarizer import get_llm_provider
from llm.provider_abc import PROVIDER_REGISTRY

# 配置日志输出以便观察
logging.basicConfig(level=logging.INFO)


class TestV4Registry(unittest.TestCase):

    def setUp(self):
        # 模拟全局配置
        self.config = GlobalConfig()
        # 确保脚本路径正确，以便 scanner 能找到 llm/ 目录
        self.config.SCRIPT_BASE_PATH = os.path.dirname(os.path.abspath(__file__))

        # 模拟 mock provider 的配置 (MockProvider 不需要 key，但工厂可能会检查配置逻辑)
        # 这里我们要 hack 一下 GlobalConfig 的检查逻辑，或者确保 MockProvider 不需要 key
        # 在 V4.1 代码中，is_provider_configured 需要在 config.py 中扩展，
        # 或者我们可以临时绕过它。为了测试，我们假设 MockProvider 不需要 Key。
        pass

    def test_dynamic_discovery(self):
        """测试是否能自动扫描到 llm/mock_provider.py"""
        print("\n>>> 测试动态发现机制...")

        # 尝试获取 "mock" provider
        # 注意：我们需要临时 patch config.py 中的 is_provider_configured
        # 或者在 MockProvider 初始化时不检查 Key。
        # 在这里我们直接调用工厂，它会触发 load_providers_dynamically

        # 1. 触发加载
        try:
            # 这里的 hack 是为了绕过 "is_provider_configured" 检查
            # 实际项目中应该在 config.py 添加 'mock' 的支持，或者让 get_llm_provider 对 mock 特殊处理
            # 但为了演示动态注册，我们直接检查 REGISTRY
            from ai_summarizer import load_providers_dynamically

            load_providers_dynamically(self.config.SCRIPT_BASE_PATH)

            print(f"当前注册表内容: {list(PROVIDER_REGISTRY.keys())}")

            self.assertIn(
                "mock", PROVIDER_REGISTRY, "❌ 'mock' 未被自动注册！请检查文件位置。"
            )
            self.assertIn("gemini", PROVIDER_REGISTRY, "❌ 'gemini' 核心组件丢失！")
            self.assertIn("deepseek", PROVIDER_REGISTRY, "❌ 'deepseek' 核心组件丢失！")
            print("✅ 动态发现测试通过")

        except Exception as e:
            self.fail(f"测试失败: {e}")

    def test_instantiation(self):
        """测试是否能实例化 MockProvider"""
        print("\n>>> 测试实例化...")
        if "mock" not in PROVIDER_REGISTRY:
            self.skipTest("Mock provider 未加载，跳过实例化测试")

        provider_cls = PROVIDER_REGISTRY["mock"]
        provider_instance = provider_cls(self.config)

        summary = provider_instance.summarize_diff("print('hello')")
        self.assertTrue(
            summary.startswith("[Mock]"), "❌ MockProvider 返回内容不符合预期"
        )
        print("✅ 实例化与调用测试通过")


if __name__ == "__main__":
    unittest.main()
