# GitReport.py
"""
Git工作日报生成器 (V4.0)
- [V4.0] 架构重构：职责分离
  - cli.py: 负责命令行界面和配置组装
  - context.py: 负责运行时配置模型
  - orchestrator.py: 负责核心业务逻辑
  - GitReport.py: 仅作为主入口启动器
"""

import logging
import sys

# 1. 初始化日志 (必须在所有模块导入之前完成)
# (V4.0) utils 模块现在只包含无依赖的工具
import utils

utils.setup_logging()

# (V4.0) 日志记录器现在可以安全创建
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# V4.0 主程序入口
# -------------------------------------------------------------------
if __name__ == "__main__":
    try:
        # (V4.0) 延迟导入 cli 模块，确保日志已配置
        import cli

        # (V4.0) 将所有执行逻辑委托给 cli.run_cli()
        cli.run_cli()

    except Exception as e:
        # (V4.POST) 捕获所有未处理的全局异常
        logger.error(f"❌ (V4.0) 发生未处理的全局异常: {e}", exc_info=True)
        sys.exit(1)
