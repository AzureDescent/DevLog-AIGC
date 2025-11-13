# DevLog-AIGC (AI驱动的Git工作日报)

本项目是一个基于 Python 和 Google Gemini AI 的 Git 工作日报自动化工具。

它能够抓取本地 Git 仓库在指定时间范围内的提交记录和变更统计，自动生成一份结构清晰、上下文连续、带 AI 总结的可视化 HTML 报告，并将其通过 Email 自动发送给指定收件人。

## ✨ 主要特性

* **Git 分析与智能过滤**：

  * 自动从 `git log` 提取提交历史、作者、分支信息。
  * 自动统计代码变更（新增/删除行数），并能**智能过滤** (Sieving) 掉锁文件 (`.lock`)、编译产物 (`dist/`)、IDE配置 (`.vscode/`) 和二进制文件，确保统计只关注核心代码。

* **两阶段 AI 摘要 (MapReduce)**：

  * **Map 阶段**: (V2.0) AI 作为 "Code Reviewer" 逐条阅读每个 `git diff`，用一句话总结其核心 *逻辑* 变更。
  * **Reduce 阶段**: (V2.0) AI 作为 "技术主管"，综合所有原始 Git 日志、上述 "Map" 总结以及下述的 "长期记忆"，生成一份高层级的、人类可读的最终工作日报。

* **长期项目记忆与蒸馏**：

  * **(V2.2) 地基日志**: 自动将每天生成的 AI 摘要（及变更统计）追加存入 `project_log.jsonl`，形成永久的项目历史记录。
  * **(V2.2) 记忆蒸馏**: AI 作为 "项目历史学家"，定期读取 *全部* 地基日志，并按 "时间权重" (Recency) 和 "变更权重" (Importance) 将其压缩提炼为一份单一的 `project_memory.md` 文件。
  * **(V2.1) 连续性报告**: 在生成新报告时，AI 会*务必*读取这份压缩记忆，确保今日的工作总结能与昨天的进展无缝衔接（例如 "在昨天完成XX的基础上，今天..."）。

* **可视化报告**：

  * 生成美观、易读的 HTML 报告，包含 AI 摘要 (支持 Markdown 渲染)、统计概览、文件变更列表和按作者分组的提交历史。

* **自动化分发**：

  * 支持通过 SMTP (使用 `yagmail`) 将 AI 摘要和完整的 HTML 报告（作为附件）自动发送到指定邮箱。

* **灵活配置**：

  * 通过 `.env` 文件管理所有敏感信息（API 密钥、SMTP 密码），代码安全，易于部署。

* **模块化设计**：

  * 代码已重构为多文件结构 (`ai_summarizer`, `git_utils`, `report_builder` 等)，遵循单一职责原则，易于维护和扩展。

## 🚀 安装指南

**1. 克隆仓库**

```bash
# (替换为你的 GitHub 仓库地址)
git clone https://github.com/YourUsername/DevLog-AIGC.git
cd DevLog-AIGC
```

**2. (推荐) 创建虚拟环境**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

**3. 安装依赖**

项目所需的所有库都已在 `requirements.txt` 中列出。

```bash
pip install -r requirements.txt
```

## ⚙️ 配置 (重要！)

在运行脚本之前，您**必须**配置 API 密钥和邮件服务器信息。

1. 在项目根目录（`DevLog-AIGC/`）下，创建一个名为 `.env` 的文件。
2. 复制以下模板，并**填入你自己的真实信息**：

<!-- end list -->

```ini
# .env

# 1. Google AI 密钥 (从 Google AI Studio 获取)
# (ai_summarizer.py 使用, 对应 config.py 中的 AI_API_KEY)
GOOGLE_API_KEY="YOUR_GOOGLE_AI_API_KEY_HERE"

# 2. SMTP 邮件配置 (email_sender.py 使用)
# (以QQ邮箱为例, 注意: SMTP_PASS 通常是邮箱设置中生成的 "授权码")
SMTP_SERVER="smtp.qq.com"
SMTP_USER="your-email@qq.com"
SMTP_PASS="YOUR_SMTP_AUTHORIZATION_CODE_HERE"
```

**(安全提示: `.gitignore` 文件已配置为忽略 `.env`、`*.jsonl` 和 `project_memory.md` 文件，因此您的密钥和记忆文件不会被意外上传。)**

## 🏃 如何运行

确保你在**一个 Git 仓库的根目录**下运行此脚本。

主入口文件是 `GitReport.py`。

**1. 基本用法 (默认分析昨天，并在浏览器中打开报告)**

```bash
python GitReport.py
```

**2. 指定时间范围 (例如：分析过去3天的)**

```bash
python GitReport.py --time "3 days ago"
```

**3. 完整用法 (分析过去7天，并发送邮件)**

这是最推荐的自动化用法。

```bash
python GitReport.py --time "7 days ago" --email "manager@example.com"
```

**4. 禁用 AI 或浏览器**

```bash
# 只生成报告，不调用 AI，也不自动打开浏览器
python GitReport.py --no-ai --no-browser
```

**5. 查看所有参数帮助**

```bash
python GitReport.py --help
```

```
usage: GitReport.py [-h] [-t TIME] [--no-ai] [--no-browser] [-e EMAIL]

Git 工作日报生成器

options:
  -h, --help            show this help message and exit
  -t TIME, --time TIME  指定Git日志的时间范围 (例如 '1 day ago'). 默认: '1 day ago'
  --no-ai               禁用 AI 摘要功能
  --no-browser          不自动在浏览器中打开报告
  -e EMAIL, --email EMAIL
                        报告生成后发送邮件到指定地址
```

## 📁 项目结构

```
DevLog-AIGC/
├── .env             # (私密) 配置文件，存放 API 密钥和 SMTP 密码
├── .gitignore       # (已配置) 忽略 .env, __pycache__, *.html, *.jsonl, project_memory.md
├── GitReport.py     # (主入口) 流程编排 (Map/Reduce/Memory) 和命令行参数
├── ai_summarizer.py # (模块 V2.2) 负责调用 Gemini AI (Map, Reduce, 记忆蒸馏)
├── config.py        # (模块 V2.2) 加载 .env 和管理配置 (过滤模式, 记忆文件路径)
├── email_sender.py  # (模块) 负责发送 SMTP 邮件 (yagmail)
├── git_utils.py     # (模块 V2.0) 负责 'git' 命令执行 (log, stats, diff) 和智能过滤
├── models.py        # (模块) 数据模型 (GitCommit, FileStat)
├── report_builder.py# (模块) 负责生成 HTML (Markdown渲染) 和 Text 报告
├── requirements.txt # (依赖) 项目依赖列表
├── utils.py         # (模块) 通用工具 (日志配置, 打开浏览器)
└── LICENSE          # (许可证) MIT License
```

## 📄 许可证

本项目采用 MIT 许可证。
