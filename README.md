# DevLog-AIGC (AI 驱动的 Git 工作日报)

本项目是一个基于 Python 的 Git 工作日报自动化工具，现已进化为 V3.9，支持**多 LLM 供应商**、**多风格报告**，并引入了**持久化配置**和**项目管理**功能。

它能够抓取**任意指定路径**的 Git 仓库在指定时间范围内的提交记录和变更统计，自动生成一份结构清晰、上下文连续、带 AI 总结的可视化 HTML 报告，并将其通过 Email 自动（群发）给指定收件人。

## ✨ 主要特性 (V3.9 更新)

- **[V3.8] 项目别名与持久化配置**

  - 彻底告别繁琐的命令行参数。

  - 通过 `data/projects.json` 管理项目“别名”到“仓库路径”的映射。

  - 每个项目在 `data/<Project>/config.json` 中拥有自己的默认配置（LLM、风格、邮件列表等）。

- **[V3.9] 交互式项目管理**

  - 通过 `python GitReport.py --configure -r ...` 启动交互式向导，轻松配置项目别名和默认参数。

  - 通过 `python GitReport.py --cleanup -p ...` 启动交互式清理向导，安全地清理缓存或重置项目。

- **[V3.9] 邮件群发**

  - `config.json` 和 `-e` 参数现在支持配置**多个**收件人邮箱，实现日报的自动群发。

- **[V3.4] 可插拔的多 LLM 架构 (Strategy Pattern)**

  - 摆脱对单一供应商的硬编码依赖。

  - 使用策略模式 (Strategy Pattern) 实现，逻辑清晰，易于扩展（`llm/provider_abc.py`）。

  - 通过 `--llm [gemini|deepseek]` 命令行参数在运行时自由切换 AI 供应商。

- **[V3.6] 供应商/风格双重解耦 (PPO)**

  - **PPO (Prompt Per-Provider)**：每种 LLM（`prompts/gemini/`, `prompts/deepseek/`）拥有自己独立的提示词模板。

  - **多风格文章生成**：通过 `--style [style]` 参数，支持生成不同风格的“整活”公众号文章（例如 `anime`, `novel`）。

- **两阶段 AI 摘要 (MapReduce)**

  - **Map 阶段**: AI 作为 "Code Reviewer" 逐条阅读每个 `git diff`，总结其核心逻辑变更。

  - **Reduce 阶段**: AI 作为 "技术主管"，综合所有原始 Git 日志、"Map" 总结以及 "长期记忆"，生成最终工作日报。

- **长期项目记忆与蒸馏**

  - **地基日志**: 自动将每天生成的 AI 摘要存入 `project_log.jsonl`。

  - **记忆蒸馏**: AI 作为 "项目历史学家"，定期读取全部日志，压缩提炼为 `project_memory.md`。

- **[V3.7] 多格式附件**

  - 自动生成美观、易读的 HTML 报告（基于 `templates/`）。

  - 支持调用 PrinceXML 将 AI 生成的风格文章（Markdown）转换为 `PDF` 附件发送。

## 🚀 安装指南

**1. 克隆仓库**

Bash

```
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

Bash

```
pip install -r requirements.txt
```

_(请注意：V3.7 新增了 PDF 转换依赖，请确保 `prince` (PrinceXML) 已安装并处于系统 PATH 中，以便使用 PDF 附件功能)_

## ⚙️ 配置 (V3.9 工作流)

V3.8 引入了全新的配置工作流，取代了旧版的纯手动 `.env` 和参数。

**第 1 步：配置 `.env` (仅需一次)**

在项目根目录（`DevLog-AIGC/`）下，创建一个名为 `.env` 的文件。这是**唯一**需要手动配置的文件，用于存放**全局**密钥。

Ini, TOML

```
# .env

# [V3.4] LLM 供应商 API 密钥
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
DEEPSEEK_API_KEY="YOUR_DEEPSEEK_API_KEY_HERE"

# (可选) 默认 LLM (gemini 或 deepseek)，如果 --llm 未指定
DEFAULT_LLM="gemini"

# [V3.3] SMTP 邮件配置 (用于发送报告)
SMTP_SERVER="smtp.example.com"
SMTP_USER="your-email@example.com"
SMTP_PASS="YOUR_SMTP_AUTHORIZATION_CODE_HERE"
```

**第 2 步：[V3.8 新] 运行交互式配置向导**

这是配置**具体项目**（如 `my-work`）的推荐方式。指向你的 Git 仓库路径：

Bash

```
python GitReport.py --configure -r /path/to/your/git/repo
```

向导将引导你完成：

1. **设置项目别名** (例如 `my-work`)：这将保存到 `data/projects.json`。

2. **设置项目默认值**：(这将保存到 `data/my-work/config.json`)

    - 默认 LLM (gemini/deepseek)

    - 默认文章风格 (default/novel/anime...)

    - 默认收件人 (V3.9 支持群发，用逗号分隔)

    - 默认附件格式 (html/pdf)

**(安全提示: `.gitignore` 文件已配置为忽略 `.env`、`data/`、`*.jsonl` 和 `project_memory.md` 文件，因此您的密钥和项目数据不会被意外上传。)**

## 🏃 如何运行 (V3.9 更新)

主入口文件是 `GitReport.py`。

1. [V3.8] 配置你的第一个项目（必做）

(替换为你的仓库路径)

Bash

```
python GitReport.py --configure -r /path/to/my-project
```

2. [V3.8] 使用别名运行（推荐）

(假设你在上一步中将别名设置为 my-project)

Bash

```
python GitReport.py -p my-project
```

_(这将自动加载 `data/my-project/config.json` 中的所有默认设置)_

3. [V3.8] 覆盖默认值运行

(使用 my-project 的配置，但临时将风格改为 novel 并发送到不同邮箱)

Bash

```
python GitReport.py -p my-project --style novel -e "other@example.com,boss@example.com"
```

4. [V3.9] 清理项目缓存或重置

(交互式向导，用于删除 my-project 的报告、记忆或配置)

Bash

```
python GitReport.py --cleanup -p my-project
```

5. [Legacy] 兼容 V3.7 的直接路径模式

(不使用别名，手动指定所有参数)

Bash

```
python GitReport.py -r /path/to/repo -t "7 days ago" --llm deepseek --style anime -e "manager@example.com"
```

**6. 查看所有参数帮助 (V3.9)**

Bash

```
python GitReport.py --help
```

```
usage: GitReport.py [-h] [--configure] [--cleanup] [-p PROJECT | -r REPO_PATH] [-t TIME | -n NUMBER] [--llm {gemini,deepseek}] [--style STYLE] [--attach-format {html,pdf}] [-e EMAIL]
                    [--no-ai] [--no-browser]

Git 工作日报生成器 (V3.9)

options:
  -h, --help            show this help message and exit
  --configure           [V3.8] 运行交互式配置向导。
                           (需要 -r 指定要配置的仓库路径)
  --cleanup             [V3.9] 运行交互式项目清理向导。
                           (需要 -p 或 -r 指定清理目标)
  -p PROJECT, --project PROJECT
                        [V3.8] 使用已配置的项目别名运行报告。
                           (与 -r 互斥)
  -r REPO_PATH, --repo-path REPO_PATH
                        [V3.0] 指定要分析的 Git 仓库的根目录路径。
                           (用于 --configure, --cleanup 或直接运行未配置的项目)
  -t TIME, --time TIME  指定Git日志的时间范围 (例如 '1 day ago').
                        (默认: '1 day ago')
  -n NUMBER, --number NUMBER
                        [V3.2] 指定最近 N 次提交 (例如 5)。
                        (与 -t 互斥)
  --llm {gemini,deepseek}
                        [V3.4] (覆盖) 指定要使用的 LLM 供应商。
                        (默认: 使用项目 config.json 或全局 config.py 中的设置)
  --style STYLE         [V3.6] (覆盖) 指定公众号文章的风格。
                        例如: 'default', 'novel', 'anime'。
                        (默认: 使用项目 config.json 中的设置)
  --attach-format {html,pdf}
                        [V3.7] (覆盖) (与 -e 连用) 指定邮件的附件格式。
                        'html': 发送 GitReport_....html
                        'pdf': (实验性) 将风格文章转为 PDF (需安装 PrinceXML)
                        (默认: 使用项目 config.json 中的设置)
  -e EMAIL, --email EMAIL
                        [V3.9] (覆盖) 接收邮箱 (多个请用逗号,分隔)。
                        (默认: 使用项目 config.json 中的设置)
  --no-ai               禁用 AI 摘要功能
  --no-browser          不自动在浏览器中打开报告
```

## 📁 项目结构 (V3.9 重构后)

```
DevLog-AIGC/
├── .env               # (私密) API 密钥和 SMTP 密码
├── .gitignore         # (已配置) 忽略 .env, data/, *.html 等
├── GitReport.py       # (主入口 V3.9)
├── config.py          # (V3.4) 全局配置 (Key, 默认 LLM)
├── config_manager.py  # (V3.8) 核心：处理 config.json 和 projects.json
├── ai_summarizer.py   # (V3.5) AI 服务 "上下文" (Context)
├── report_builder.py  # (V3.3) HTML 报告生成
├── pdf_converter.py   # (V3.7) MD 转 PDF (PrinceXML)
├── git_utils.py       # (V3.2) Git 命令执行
├── email_sender.py    # (V3.9) 邮件发送 (支持群发)
├── models.py          # (V3.3) 数据模型 (GitCommit, FileStat)
├── utils.py           # (V3.3) 通用工具 (日志, 浏览器)
├── requirements.txt   # (V3.4) 依赖列表
|
├── llm/               # (V3.4) LLM 策略模式 (Strategy)
│   ├── provider_abc.py    # (V3.5) 抽象接口
│   ├── gemini_provider.py # (V3.6) Gemini 策略实现
│   └── deepseek_provider.py # (V3.6) DeepSeek 策略实现
|
├── prompts/           # (V3.6) 供应商/风格双重解耦
│   ├── gemini/
│   │   ├── articles/      # (V3.6) 风格文章 (default, anime, novel...)
│   │   ├── diff_map.txt
│   │   ├── memory_distill.txt
│   │   └── summary_reduce.txt
│   └── deepseek/
│       ├── articles/
│       ├── system.txt
│       ├── diff_map.txt
│       ├── memory_distill.txt
│       └── summary_reduce.txt
|
├── templates/         # (V3.3) 视图模板
│   ├── report.html.tpl
│   ├── styles.css
│   └── pdf_style.css    # (V3.7) PDF 样式
|
├── data/              # (运行时生成) (V3.8)
│   ├── projects.json    # (V3.8) 全局别名
│   └── Project-A/       # (示例) 目标仓库的项目数据
│       ├── config.json      # (V3.8) 项目默认配置
│       ├── GitReport_....html
│       ├── PublicArticle_anime_....md
│       ├── PublicArticle_anime_....pdf # (V3.7)
│       ├── project_log.jsonl
│       └── project_memory.md
|
└── LICENSE            # (许可证) MIT License
```

## 📄 许可证

本项目采用 MIT 许可证。
