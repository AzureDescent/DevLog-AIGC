# DevLog-AIGC (AI 驱动的 Git 工作日报)

本项目是一个基于 Python 的 Git 工作日报自动化工具，现已重构为支持**多 LLM 供应商**（Google Gemini, DeepSeek）的**多风格**报告生成器。

它能够抓取**任意指定路径**的 Git 仓库在指定时间范围内的提交记录和变更统计，自动生成一份结构清晰、上下文连续、带 AI 总结的可视化 HTML 报告，并将其通过 Email 自动发送给指定收件人。

## ✨ 主要特性 (V3.6 更新)

- **[V3.4] 可插拔的多 LLM 架构 (Strategy Pattern)**

  - 彻底摆脱对单一供应商的硬编码依赖。
  - 使用策略模式 (Strategy Pattern) 实现，逻辑清晰，易于扩展（`llm/provider_abc.py`）。
  - 通过 `--llm [gemini|deepseek]` 命令行参数在运行时自由切换 AI 供应商。

- **[V3.5/V3.6] 供应商/风格双重解耦 (PPO)**

  - **PPO (Prompt Per-Provider)**：每种 LLM（`prompts/gemini/`, `prompts/deepseek/`）拥有自己独立的提示词模板，解决不同模型的指令差异。
  - **多风格文章生成**：通过 `--style [style]` 参数，支持生成不同风格的“整活”公众号文章（例如 `anime`, `novel`）。
  - **动态加载**：提示词被递归加载，添加新风格（例如 `prompts/gemini/articles/meme.txt`）无需修改代码。

- **Git 分析与智能过滤**

  - 自动从 `git log` 提取提交历史、作者、分支信息。
  - 自动统计代码变更（新增/删除），并能**智能过滤** (Sieving) 掉锁文件 (`.lock`)、编译产物 (`dist/`)、IDE配置 (`.vscode/`) 等。

- **两阶段 AI 摘要 (MapReduce)**

  - **Map 阶段**: AI 作为 "Code Reviewer" 逐条阅读每个 `git diff`，总结其核心逻辑变更。
  - **Reduce 阶段**: AI 作为 "技术主管"，综合所有原始 Git 日志、"Map" 总结以及 "长期记忆"，生成最终工作日报。

- **长期项目记忆与蒸馏**

  - **地基日志**: 自动将每天生成的 AI 摘要存入 `project_log.jsonl`，形成永久历史。
  - **记忆蒸馏**: AI 作为 "项目历史学家"，定期读取全部日志，按 "时间权重" 和 "变更权重" 压缩提炼为 `project_memory.md`。

- **解耦与数据隔离 (V3.0 / V3.1)**

  - **工作区解耦**: 通过 `-r / --repo-path` 参数可分析任意位置的 Git 仓库。
  - **数据隔离**: 自动在脚本目录下的 `data/` 中为每个目标仓库创建专属子目录（如 `data/Project-A/`），所有报告、日志、记忆文件均在此读写。

- **可视化报告与分发**

  - 生成美观、易读的 HTML 报告（基于 `templates/` 目录）。
  - 支持通过 SMTP (使用 `yagmail`) 将 AI 摘要和 HTML 报告（作为附件）自动发送到指定邮箱。

## 🚀 安装指南

**1. 克隆仓库**

```bash
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

```bash
pip install -r requirements.txt
```

*(请注意：V3.4+ 已新增 `openai` 和 `python-dotenv` 等依赖)*

## ⚙️ 配置 (V3.4 关键更新！)

在运行脚本之前，您**必须**配置 API 密钥。

1. 在项目根目录（`DevLog-AIGC/`）下，创建一个名为 `.env` 的文件。
2. 复制以下模板，并**填入你自己的真实信息**：

<!-- end list -->

```ini
# .env

# [V3.4] LLM 供应商 API 密钥
# (注意：V3.3 的 GOOGLE_API_KEY 已重命名为 GEMINI_API_KEY)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
DEEPSEEK_API_KEY="YOUR_DEEPSEEK_API_KEY_HERE"

# (可选) 默认 LLM (gemini 或 deepseek)，如果 --llm 未指定
# DEFAULT_LLM="gemini"

# [V3.3] SMTP 邮件配置
SMTP_SERVER="smtp.example.com"
SMTP_USER="your-email@example.com"
SMTP_PASS="YOUR_SMTP_AUTHORIZATION_CODE_HERE"
```

**(安全提示: `.gitignore` 文件已配置为忽略 `.env`、`data/`、`*.jsonl` 和 `project_memory.md` 文件，因此您的密钥和项目数据不会被意外上传。)**

## 🏃 如何运行 (V3.6 更新)

主入口文件是 `GitReport.py`。

**1. [V3.4] 使用 DeepSeek 分析最近 5 次提交**

```bash
python GitReport.py -r . -n 5 --llm deepseek
```

**2. [V3.6] 使用 Gemini 生成 "修仙" 风格文章**
分析目标仓库昨天至今的提交，使用 Gemini，并生成 `novel.txt` 定义的修仙风格公众号文章。

```bash
python GitReport.py -r /path/to/my/repo --llm gemini --style novel
```

**3. [V3.6] 使用 DeepSeek 生成 "二次元" 风格文章并发送邮件**
分析目标仓库过去 7 天的提交，使用 DeepSeek，生成 `anime.txt` 风格文章，并发送邮件。

```bash
python GitReport.py -r /path/to/repo -t "7 days ago" --llm deepseek --style anime -e "manager@example.com"
```

**4. 禁用 AI 或浏览器**

```bash
python GitReport.py -r /path/to/repo --no-ai --no-browser
```

**5. 查看所有参数帮助 (V3.6)**

```bash
python GitReport.py --help
```

```
usage: GitReport.py [-h] [-r REPO_PATH] [-t TIME | -n NUMBER] [--llm {gemini,deepseek}] [--style STYLE] [--no-ai] [--no-browser] [-e EMAIL]

Git 工作日报生成器 (V3.6)

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
  --llm {gemini,deepseek}
                        [V3.4] 指定要使用的 LLM 供应商。
                        可选: 'gemini', 'deepseek'
                        (默认: 在 config.py 中设置的 DEFAULT_LLM)
  --style STYLE         [V3.6] 指定公众号文章的风格。
                        对应 prompts/<provider>/articles/ 目录下的文件名 (不含.txt)。
                        例如: 'default', 'novel', 'anime'。 (默认: 'default')
  --no-ai               禁用 AI 摘要功能
  --no-browser          不自动在浏览器中打开报告
  -e EMAIL, --email EMAIL
                        报告生成后发送邮件到指定地址
```

## 📁 项目结构 (V3.6 重构后)

```
DevLog-AIGC/
├── .env               # (私密) API 密钥和 SMTP 密码
├── .gitignore         # (已配置) 忽略 .env, data/, *.html 等
├── GitReport.py       # (主入口 V3.6)
├── config.py          # (V3.4) 管理路径、密钥、LLM 默认值
├── ai_summarizer.py   # (V3.5) AI 服务 "上下文" (Context)
├── report_builder.py  # (V3.3) HTML 报告生成器
├── git_utils.py       # (V3.2) Git 命令执行
├── email_sender.py    # (V3.3) 邮件发送
├── models.py          # (V3.3) 数据模型 (GitCommit, FileStat)
├── utils.py           # (V3.3) 通用工具 (日志, 浏览器)
├── requirements.txt   # (V3.4) 依赖列表 (含 openai, google-generativeai)
|
├── llm/               # (V3.4) LLM 策略模式 (Strategy)
│   ├── provider_abc.py    # (V3.5) 抽象接口
│   ├── gemini_provider.py # (V3.6) Gemini 策略实现
│   └── deepseek_provider.py # (V3.6) DeepSeek 策略实现
|
├── prompts/           # (V3.6) 供应商/风格双重解耦
│   ├── gemini/
│   │   ├── articles/      # (V3.6) 风格文章
│   │   │   ├── default.txt
│   │   │   ├── anime.txt
│   │   │   └── novel.txt
│   │   ├── diff_map.txt
│   │   ├── memory_distill.txt
│   │   └── summary_reduce.txt
│   │
│   └── deepseek/
│       ├── articles/
│       │   ├── default.txt
│       │   ├── anime.txt
│       │   └── novel.txt
│       ├── system.txt
│       ├── diff_map.txt
│       ├── memory_distill.txt
│       └── summary_reduce.txt
|
├── templates/         # (V3.3) 视图模板
│   ├── report.html.tpl
│   └── styles.css
|
├── data/              # (运行时生成) (V3.1)
│   └── Project-A/     # (示例) 目标仓库的项目数据
│       ├── GitReport_....html
│       ├── PublicArticle_anime_....md  # (V3.6) 带风格的文章
│       ├── project_log.jsonl
│       └── project_memory.md
|
└── LICENSE            # (许可证) MIT License
```

## 📄 许可证

本项目采用 MIT 许可证。
