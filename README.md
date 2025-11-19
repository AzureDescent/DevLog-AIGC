# DevLog-AIGC (V4.4) - AI 驱动的 Git 工作日报生成器

**DevLog-AIGC** 是一个高度可扩展的自动化工具，能够分析 Git 仓库的提交记录，利用大语言模型（LLM）生成结构清晰、风格多变的工作日报，并支持通过 **Email** 和 **飞书 (Feishu/Lark)** 多渠道自动推送。

🚀 **V4.4 版本特性**：新增 **飞书 (Feishu)** 通知渠道支持，并引入 **Jinja2 模板引擎** 实现高度自定义的报告样式。

-----

## ✨ 核心特性 (V4.x 演进)

### 📢 多渠道通知系统 (V4.3 - V4.4)

- **[New] 飞书 (Feishu) 集成**:
  - **企业自建应用模式**: 支持通过 `App ID` 和 `Secret` 上传 PDF/HTML 附件并点对点推送给指定邮箱用户。
  - **群组 Webhook 模式**: 支持通过 Webhook 向飞书群组发送文本摘要（降级方案）。
- **通知渠道抽象**: 采用了插件化的 `Notifier` 架构，未来可轻松扩展钉钉、Slack 等渠道。
- **邮件群发**: 继续支持通过 SMTP (yagmail) 发送富文本邮件和附件。

### 🎨 报告可视化升级 (V4.2)

- **Jinja2 模板引擎**: 彻底重构了 HTML 生成逻辑。现在您可以直接修改 `templates/report.html.j2` 来调整日报的布局、配色和字体，无需修改 Python 代码。
- **Markdown 渲染**: AI 生成的摘要在 HTML 报告中支持完整的 Markdown 语法渲染。

### 🏗️ 架构与扩展性 (V4.0 - V4.1)

- **动态 LLM 注册 (Registry Pattern)**: 支持通过简单的装饰器 `@register_provider` 添加新的 AI 模型（如 Claude, Ollama），无需修改核心工厂代码。
- **Context/Orchestrator 模式**: 运行时状态（RunContext）与业务流程（Orchestrator）完全解耦，系统更健壮。

### 🧠 AI 核心能力

- **多风格文章**: 支持生成 **赛博朋克**、**修仙**、**宫廷权谋**、**异世界** 等多种风格的公众号推文。
- **长期记忆**: 自动记录并“蒸馏”项目历史（`project_memory.md`），让 AI 理解项目的演进脉络。
- **Map-Reduce 摘要**: 逐条分析 Diff 细节，再宏观总结日报。

-----

## ⚙️ 配置指南

### 1\. 环境配置 (.env)

在项目根目录创建 `.env` 文件，配置 API 密钥和通知渠道凭证。

```ini
# .env

# --- AI 模型配置 ---
GEMINI_API_KEY="your_gemini_key"
DEEPSEEK_API_KEY="your_deepseek_key"
DEFAULT_LLM="gemini"

# --- 邮件配置 (可选) ---
SMTP_SERVER="smtp.example.com"
SMTP_USER="your_email@example.com"
SMTP_PASS="your_app_password"

# --- [V4.4 New] 飞书配置 (可选) ---
# 模式 A: 自建应用 (推荐，支持发文件)
FEISHU_APP_ID="cli_xxxxxxxx"
FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxx"

# 模式 B: 群机器人 Webhook (仅发文本)
FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/..."
```

### 2\. 项目初始化

使用交互式向导配置您的 Git 仓库：

```bash
python GitReport.py --configure -r /path/to/your/local/repo
```

*向导将引导您设置项目别名、默认 LLM、文章风格以及接收人列表（邮箱）。*

> **注意**: 对于飞书应用模式，系统会根据配置的接收人邮箱（`email_list`）自动匹配飞书用户进行发送。

-----

## 🚀 使用方法

### 基础运行 (使用别名)

```bash
python GitReport.py -p my-project
```

### 启用飞书通知

只要在 `.env` 中配置了飞书凭证，系统会自动检测并启用该渠道。

```bash
# 同时发送邮件和飞书通知
python GitReport.py -p my-project
```

### 生成 PDF 附件并发送

```bash
# 生成“修仙”风格文章，转为 PDF，并通过飞书/邮件发送
python GitReport.py -p my-project --style wuxia --attach-format pdf
```

*(需要安装 [PrinceXML](https://www.princexml.com/) 并在系统 PATH 中)*

### 仅运行 Webhook (测试)

如果未配置 `FEISHU_APP_ID`，系统将自动降级使用 `FEISHU_WEBHOOK` 向群组发送纯文本摘要。

-----

## 📂 V4.4 项目结构

```text
DevLog-AIGC/
├── GitReport.py           # [入口] 启动脚本
├── orchestrator.py        # [核心] 业务流程编排 (V4.4 更新)
├── notifiers/             # [V4.3 New] 通知渠道模块
│   ├── base.py            # 抽象基类
│   ├── factory.py         # 通知器工厂
│   ├── email_notifier.py  # 邮件实现
│   └── feishu_notifier.py # [V4.4] 飞书实现
├── templates/             # [V4.2 New] 模板文件
│   ├── report.html.j2     # Jinja2 HTML 模板
│   └── styles.css         # 样式表
├── llm/                   # AI 供应商策略
│   ├── provider_abc.py    # 包含注册表逻辑
│   ├── gemini_provider.py
│   └── deepseek_provider.py
├── report_builder.py      # [V4.2] 负责渲染 Jinja2 模板
├── config.py              # 全局配置 (包含飞书配置)
└── .env                   # 敏感凭证 (不上传)
```

-----

## ⚠️ 关于飞书功能的说明

当前 `FeishuNotifier` 包含两种模式：

1. **App 模式**: 调用 `im/v1/messages` 接口。需要企业自建应用权限（机器人能力）。
2. **Webhook 模式**: 调用群机器人 Webhook。

**待验证状态**: 由于开发环境限制，App 模式的文件上传和点对点发送功能尚未在真实的企业租户下进行完全验证。欢迎拥有权限的开发者测试并反馈。

-----

## 📄 许可证

[MIT License](https://www.google.com/search?q=LICENSE)

Copyright (c) 2025 AzureDescent
