# DevLog-AIGC (V4.0) - AI 驱动的 Git 工作日报生成器

**DevLog-AIGC** 是一个基于 Python 的自动化工具，能够分析 Git 仓库的提交记录，利用大语言模型（LLM）生成结构清晰、风格多变的工作日报，并支持自动邮件发送。

🚀 **V4.0 重大更新**：本项目已完成核心架构重构，引入了 **Context/Orchestrator（上下文/编排器）** 模式，实现了配置、状态与业务逻辑的完全解耦，代码更健壮、更易扩展。

-----

## ✨ 核心特性

### 🏗️ V4.0 架构升级

  - **运行时上下文 (RunContext)**: 所有的运行时状态、配置参数和全局单例被封装在 `RunContext` 数据类中，在模块间统一传递，消除了混乱的参数列表。
  - **业务编排器 (Orchestrator)**: `GitReport.py` 仅作为启动入口，核心业务流程由 `orchestrator.py` 统一调度，逻辑流向一目了然。
  - **全局配置 (GlobalConfig)**: 环境变量和静态常量通过 `config.py` 统一管理。

### 🧠 强大的 AI 能力

  - **多 LLM 支持 (策略模式)**: 支持 **Google Gemini** 和 **DeepSeek**，通过 `llm/` 目录下的策略类实现热切换。
  - **Map-Reduce 摘要算法**:
    1.  **Map**: 逐条分析 Git Diff，理解代码逻辑变更。
    2.  **Reduce**: 结合“长期记忆”和当日所有变更，生成高层摘要。
  - **长期记忆系统**: 自动记录每日摘要，并定期“蒸馏”为项目里程碑（`project_memory.md`），让 AI 了解项目的前世今生。

### 🎨 多风格与多格式

  - **多风格文章生成**: 不止是日报！支持生成 **赛博朋克(Cyberpunk)**、**修仙(Wuxia)**、**异世界(Anime)**、**侦探(Detective)** 等风格的公众号推文。
  - **PPO (Prompt Per-Provider)**: 针对不同 LLM（Gemini/DeepSeek）优化独立的提示词模板。
  - **PDF 导出**: 支持将生成的风格化文章通过 PrinceXML 转换为精美的 PDF 附件。

### 🛠️ 便捷的项目管理

  - **交互式配置向导**: `python GitReport.py --configure` 引导式设置项目别名和参数。
  - **持久化配置**: 每个项目拥有独立的 `config.json`，无需每次输入冗长的命令行参数。
  - **邮件群发**: 支持配置多个收件人，一键发送汇报。

-----

## 🚀 快速开始

### 1\. 环境准备

克隆仓库并安装依赖（推荐使用虚拟环境）：

```bash
git clone https://github.com/YourUsername/DevLog-AIGC.git
cd DevLog-AIGC

# 创建虚拟环境
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

*(可选) 如需生成 PDF 附件，请安装 [PrinceXML](https://www.princexml.com/) 并确保将其添加到系统 PATH 中。*

### 2\. 配置 API 密钥

在项目根目录创建 `.env` 文件：

```ini
# .env
GEMINI_API_KEY="你的_GEMINI_KEY"
DEEPSEEK_API_KEY="你的_DEEPSEEK_KEY"

# 邮件发送配置 (SMTP)
SMTP_SERVER="smtp.example.com"
SMTP_USER="your_email@example.com"
SMTP_PASS="你的_应用专用密码"

# 全局默认设置
DEFAULT_LLM="gemini"
```

### 3\. 初始化项目配置 (推荐)

使用交互式向导配置你的 Git 仓库：

```bash
python GitReport.py --configure -r /path/to/your/local/repo
```

*向导将引导你设置项目别名（如 `my-work`）、默认 LLM、文章风格和接收邮箱。*

### 4\. 运行生成器

**方式 A：使用别名运行（最常用）**

```bash
python GitReport.py -p my-work
```

**方式 B：覆盖默认参数**

```bash
# 临时使用 DeepSeek 模型，生成“修仙”风格，并以 PDF 格式发送
python GitReport.py -p my-work --llm deepseek --style wuxia --attach-format pdf
```

**方式 C：直接指定路径 (Legacy)**

```bash
python GitReport.py -r /path/to/repo -t "1 day ago"
```

### 5\. 清理缓存

```bash
python GitReport.py --cleanup -p my-work
```

-----

## 📂 V4.0 项目结构

```text
DevLog-AIGC/
├── GitReport.py           # [入口] 仅负责启动，委托给 cli.py
├── cli.py                 # [V4.0] 命令行解析与入口逻辑
├── context.py             # [V4.0] 定义 RunContext (运行时上下文)
├── orchestrator.py        # [V4.0] 业务编排器 (核心流程控制)
├── config.py              # [V4.0] GlobalConfig (环境与常量)
├── config_manager.py      # [V3.9] 项目配置与别名管理 (JSON IO)
├── ai_summarizer.py       # [Service] AI 服务外观类
├── report_builder.py      # [Service] HTML 报告生成
├── git_utils.py           # [Service] Git 命令执行
├── email_sender.py        # [Service] 邮件发送
├── pdf_converter.py       # [Service] Markdown 转 PDF
├── models.py              # 数据模型 (GitCommit, FileStat)
├── utils.py               # 通用工具 (日志)
├── .env                   # API 密钥 (不上传)
├── requirements.txt       # 依赖列表
├── llm/                   # LLM 策略实现
│   ├── provider_abc.py
│   ├── gemini_provider.py
│   └── deepseek_provider.py
├── prompts/               # 提示词模板 (按供应商/风格隔离)
│   ├── deepseek/
│   └── gemini/
├── templates/             # 报告模板
│   ├── report.html.tpl
│   ├── styles.css
│   └── pdf_style.css
└── data/                  # [自动生成] 存储各项目的配置、日志和记忆
    ├── projects.json      # 全局别名映射
    └── <Project_Name>/    # 特定项目数据
```

-----

## 🛠️ 参数说明

运行 `python GitReport.py --help` 查看完整帮助：

| 参数                | 说明              | 备注                           |
| :------------------ | :---------------- | :----------------------------- |
| `--configure`       | 运行配置向导      | 需配合 `-r`                    |
| `--cleanup`         | 运行清理向导      | 需配合 `-p` 或 `-r`            |
| `-p`, `--project`   | 指定项目别名      | 优先加载 `data/` 下的配置      |
| `-r`, `--repo-path` | 指定 Git 仓库路径 | 直接运行模式                   |
| `-t`, `--time`      | Git 时间范围      | 默认为 "1 day ago"             |
| `-n`, `--number`    | 最近 N 次提交     | 与 `-t` 互斥                   |
| `--llm`             | 指定 LLM 供应商   | `gemini` 或 `deepseek`         |
| `--style`           | 指定文章风格      | `default`, `novel`, `anime`... |
| `--attach-format`   | 附件格式          | `html` (默认) 或 `pdf`         |
| `-e`, `--email`     | 接收邮箱          | 逗号分隔多个邮箱               |
| `--no-ai`           | 禁用 AI 功能      | 仅生成基础统计报告             |
| `--no-browser`      | 不自动打开浏览器  | 适用于服务器环境               |

-----

## 🤝 贡献指南

1.  Fork 本仓库。
2.  创建特性分支 (`git checkout -b feature/AmazingFeature`)。
3.  提交更改 (`git commit -m 'Add some AmazingFeature'`)。
4.  推送到分支 (`git push origin feature/AmazingFeature`)。
5.  开启 Pull Request。

**开发提示**: V4.0 所有模块均依赖 `RunContext` 对象进行状态传递。新增功能时，请确保在 `orchestrator.py` 中正确调用，并尽量保持服务的无状态性。

## 📄 许可证

[MIT License](https://www.google.com/search?q=LICENSE)

Copyright (c) 2025 AzureDescent
