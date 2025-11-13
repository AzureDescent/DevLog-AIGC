# DevLog-AIGC (AI驱动的Git工作日报)

本项目是一个基于 Python 和 Google Gemini AI 的 Git 工作日报自动化工具。

它能够抓取**任意指定路径**的 Git 仓库在指定时间范围内的提交记录和变更统计，自动生成一份结构清晰、上下文连续、带 AI 总结的可视化 HTML 报告，并将其通过 Email 自动发送给指定收件人。

## ✨ 主要特性

- **Git 分析与智能过滤**：

  - 自动从 `git log` 提取提交历史、作者、分支信息。

  - 自动统计代码变更（新增/删除行数），并能**智能过滤** (Sieving) 掉锁文件 (`.lock`)、编译产物 (`dist/`)、IDE配置 (`.vscode/`) 和二进制文件，确保统计只关注核心代码。

- **两阶段 AI 摘要 (MapReduce)**：

  - **Map 阶段**: AI 作为 "Code Reviewer" 逐条阅读每个 `git diff`，用一句话总结其核心 _逻辑_ 变更。

  - **Reduce 阶段**: AI 作为 "技术主管"，综合所有原始 Git 日志、上述 "Map" 总结以及下述的 "长期记忆"，生成一份高层级的、人类可读的最终工作日报。

- **长期项目记忆与蒸馏**：

  - **(V2.2) 地基日志**: 自动将每天生成的 AI 摘要（及变更统计）追加存入 `project_log.jsonl`，形成永久的项目历史记录。

  - **(V2.2) 记忆蒸馏**: AI 作为 "项目历史学家"，定期读取 _全部_ 地基日志，并按 "时间权重" (Recency) 和 "变更权重" (Importance) 将其压缩提炼为一份单一的 `project_memory.md` 文件。

  - **(V2.1) 连续性报告**: 在生成新报告时，AI 会_务必_读取这份压缩记忆，确保今日的工作总结能与昨天的进展无缝衔接（例如 "在昨天完成XX的基础上，今天..."）。

- **解耦与数据隔离 (V3.0 / V3.1)**：

  - **工作区解耦**: 脚本不再依赖 CWD，通过 `-r / --repo-path` 参数可分析任意位置的 Git 仓库。

  - **数据隔离**: 自动在脚本目录下的 `data/` 中为每个目标仓库创建专属子目录（如 `data/Project-A/`），所有报告、日志、记忆文件均在此读写，彻底解决项目间的数据污染问题。

- **模板化设计 (V3.3)**：

  - **内容与逻辑分离**: 所有 AI Prompts, HTML 骨架, 和 CSS 样式均已从 Python 代码中分离。

  - **易于定制**: 用户可直接修改 `prompts/` 目录下的 `.txt` 文件来调整 AI 指令，或修改 `templates/` 目录下的 `.css` / `.tpl` 文件来自定义报告样式，无需触碰核心逻辑。

- **可视化报告与分发**：

  - 生成美观、易读的 HTML 报告，包含 AI 摘要 (支持 Markdown 渲染)、统计概览、文件变更列表和按作者分组的提交历史。

  - 支持通过 SMTP (使用 `yagmail`) 将 AI 摘要和完整的 HTML 报告（作为附件）自动发送到指定邮箱。

## 🚀 安装指南

**1. 克隆仓库**

Bash

```
# (替换为你的 GitHub 仓库地址)
git clone https://github.com/YourUsername/DevLog-AIGC.git
cd DevLog-AIGC
```

**2. (推荐) 创建虚拟环境**

Bash

```
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

**3. 安装依赖**

项目所需的所有库都已在 `requirements.txt` 中列出。

Bash

```
pip install -r requirements.txt
```

## ⚙️ 配置 (重要！)

在运行脚本之前，您**必须**配置 API 密钥和邮件服务器信息。

1. 在项目根目录（`DevLog-AIGC/`）下，创建一个名为 `.env` 的文件。

2. 复制以下模板，并**填入你自己的真实信息**：

Ini, TOML

```
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

**(安全提示: `.gitignore` 文件已配置为忽略 `.env`、`data/`、`*.jsonl` 和 `project_memory.md` 文件，因此您的密钥和项目数据不会被意外上传。)**

## 🏃 如何运行 (V3.2 更新)

主入口文件是 `GitReport.py`。您可以从_任何地方_运行此脚本，只需使用 `-r` 参数指向您想分析的 Git 仓库。

**1. 基本用法 (分析指定仓库的昨天提交)**

Bash

```
# 分析位于 /path/to/your/git/repo 的仓库
python GitReport.py -r /path/to/your/git/repo
```

**2. 分析当前目录 (等同于 V3.0 之前的默认行为)**

Bash

```
python GitReport.py -r .
# 或者
python GitReport.py
```

**3. 指定时间范围 (例如：分析过去3天的)**

Bash

```
python GitReport.py -r /path/to/repo -t "3 days ago"
```

**4. 指定最近N次提交 (V3.2 新增, 与 -t 互斥)**

这在调试时非常有用。

Bash

```
# 分析最近 5 次提交
python GitReport.py -r /path/to/repo -n 5
```

**5. 完整用法 (分析过去7天，并发送邮件)**

这是最推荐的自动化用法。

Bash

```
python GitReport.py -r /path/to/repo -t "7 days ago" --email "manager@example.com"
```

**6. 禁用 AI 或浏览器**

Bash

```
# 只生成报告，不调用 AI，也不自动打开浏览器
python GitReport.py -r /path/to/repo --no-ai --no-browser
```

**7. 查看所有参数帮助**

Bash

```
python GitReport.py --help
```

```
usage: GitReport.py [-h] [-r REPO_PATH] [-t TIME | -n NUMBER] [--no-ai] [--no-browser] [-e EMAIL]

Git 工作日报生成器 (V3.2)

options:
  -h, --help            show this help message and exit
  -r REPO_PATH, --repo-path REPO_PATH
                        [V3.0] 指定要分析的 Git 仓库的根目录路径。
                        (默认: '.')
  -t TIME, --time TIME  指定Git日志的时间范围 (例如 '1 day ago').
                        (默认: '1 day ago')
  -n NUMBER, --number NUMBER
                        [V3.2] 指定最近 N 次提交 (例如 5)。
                        (与 -t 互斥)
  --no-ai               禁用 AI 摘要功能
  --no-browser          不自动在浏览器中打开报告
  -e EMAIL, --email EMAIL
                        报告生成后发送邮件到指定地址
```

## 📁 项目结构 (V3.3 重构后)

```
DevLog-AIGC/
├── .env               # (私密) 配置文件，存放 API 密钥和 SMTP 密码
├── .gitignore         # (已配置) 忽略 .env, __pycache__, *.html, data/
├── GitReport.py       # (主入口) 流程编排 (V3.2 命令行参数)
├── config.py          # (模块 V3.1) 加载 .env, 管理路径, 过滤模式
├── ai_summarizer.py   # (模块 V3.3) 负责调用 Gemini AI, 从 prompts/ 加载模板
├── report_builder.py  # (模块 V3.3) 负责生成 HTML 报告, 从 templates/ 加载模板
├── git_utils.py       # (模块 V3.0) 负责 'git' 命令执行 (log, stats, diff)
├── email_sender.py    # (模块) 负责发送 SMTP 邮件 (yagmail)
├── models.py          # (模块) 数据模型 (GitCommit, FileStat)
├── utils.py           # (模块) 通用工具 (日志配置, 打开浏览器)
├── requirements.txt   # (依赖) 项目依赖列表
|
├── prompts/           # (V3.3) 存放所有 AI Prompt 模板
│   ├── diff_map.txt
│   ├── summary_reduce.txt
│   ├── memory_distill.txt
│   └── public_article.txt
|
├── templates/         # (V3.3) 存放所有 HTML/CSS 模板
│   ├── report.html.tpl
│   └── styles.css
|
├── data/              # (运行时生成) 存放所有隔离的项目数据
│   └── Project-A/     # (示例) 目标仓库的项目数据
│       ├── GitReport_....html
│       ├── PublicArticle_....md
│       ├── project_log.jsonl
│       └── project_memory.md
|
└── LICENSE            # (许可证) MIT License
```

## 📄 许可证

本项目采用 MIT 许可证。
