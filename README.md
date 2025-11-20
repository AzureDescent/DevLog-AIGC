# 🚀 DevLog-AIGC (V4.8)

**AI 驱动的全自动 Git 开发日报生成器**

> *无需繁琐编写，让 AI 为你的代码讲故事。支持本地/远程仓库、多风格叙事、PDF 导出及多渠道推送。*

-----

## ✨ 核心特性

### 🧠 **多模态 AI 支持**

* **云端模型**：原生支持 **Google Gemini** 和 **DeepSeek** API。
* **本地私有化 (New\!)**：完美支持 **Ollama** (如 qwen2.5, llama3)，实现**零成本**、**隐私安全**的离线分析。

### 🌐 **全场景数据源 (Data Sources)**

* **本地 Git (Local)**：直接分析本地开发的 Git 仓库。
* **远程仓库 (Remote) (New\!)**：无需 Clone 代码，直接通过 **GitHub API** 分析远程仓库 URL (如 `https://github.com/torvalds/linux`)。

### 🎨 **多风格与多格式**

* **叙事风格**：支持 **默认(Default)**、**赛博朋克(Cyberpunk)**、**修仙(Wuxia)**、**侦探(Detective)** 等多种文风。
* **精美报告**：生成 Jinja2 渲染的 **HTML** 报告。
* **PDF 导出**：内置 PrinceXML，支持**中文、Emoji 完美渲染**的 PDF 文档生成。

### 🧩 **高度可扩展架构**

* **插件系统 (Hooks)**：支持生命周期钩子（如 `CleanOutput` 清洗 AI 输出、`SensitiveFilter` 敏感词过滤）。
* **模块化通知**：支持邮件 (SMTP) 推送，架构预留了飞书/钉钉扩展接口。
* **Docker First**：提供开箱即用的 Docker 镜像，内置所有依赖与字体环境。

-----

## 🛠️ 快速开始 (Docker 方式 - 推荐)

无需配置 Python 环境，只需安装 Docker Desktop。

### 1\. 构建镜像

```powershell
docker build -t devlog-aigc .
```

*(注：镜像基于 Debian 12，内置了 PrinceXML 和 Google Noto CJK/Emoji 字体，构建需几分钟)*

### 2\. 准备配置文件

在项目根目录创建 `.env` 文件：

```ini
# LLM API Keys (选填，使用 Ollama 时不需要)
GEMINI_API_KEY="your_key"
DEEPSEEK_API_KEY="your_key"

# GitHub Token (建议配置，用于分析远程仓库以获得更高 API 配额)
GITHUB_TOKEN="ghp_xxxx..."

# 邮件配置 (可选)
SMTP_SERVER="smtp.qq.com"
SMTP_USER="your_email@qq.com"
SMTP_PASS="your_app_password"
```

### 3\. 场景演示

#### 场景 A：使用 Ollama 分析远程 GitHub 仓库 (生成 PDF)

假设您的电脑上运行着 Ollama (端口 11434)，要分析 Linux 内核仓库：

```powershell
docker run --rm `
  -v "${PWD}:/app" `
  -v "${PWD}\.env:/app/.env" `
  -e OLLAMA_BASE_URL="http://host.docker.internal:11434/v1" `
  -e OLLAMA_MODEL="qwen2.5:7b" `
  devlog-aigc `
  -r https://github.com/torvalds/linux `
  -n 5 `
  --llm ollama `
  --style cyberpunk `
  --attach-format pdf `
  --no-browser
```

#### 场景 B：分析本地项目

假设您的代码在 `E:\MyProject`：

```powershell
docker run --rm `
  -v "E:\MyProject:/target_repo" `
  -v "${PWD}:/app" `
  -v "${PWD}\.env:/app/.env" `
  devlog-aigc `
  -r /target_repo `
  -t "1 day ago" `
  --llm gemini
```

-----

## 📂 项目结构 (V4.8)

```text
DevLog-AIGC/
├── GitReport.py           # 程序启动入口
├── orchestrator.py        # [核心] 业务编排器 (V4.6 Hook集成)
├── context.py             # 运行时上下文模型
├── config.py              # 全局配置
├── data_sources/          # [V4.5] 数据源抽象层
│   ├── base.py            # 接口定义
│   ├── local_git.py       # 本地 Git 实现
│   ├── github_api.py      # [V4.8] GitHub API 实现
│   └── factory.py         # 数据源工厂
├── llm/                   # LLM 策略层
│   ├── gemini_provider.py
│   ├── deepseek_provider.py
│   └── ollama_provider.py # [V4.7] 本地模型支持
├── plugins/               # [V4.6] 插件系统
│   ├── sensitive_filter.py # 敏感词过滤
│   └── clean_output.py     # AI 输出清洗
├── templates/             # Jinja2 模板与样式
│   ├── report.html.j2
│   └── pdf_style.css      # [V4.7] PDF 专用样式 (含中文字体配置)
├── hooks/                 # 钩子管理器
├── notifiers/             # 通知模块
├── pdf_converter.py       # PDF 转换逻辑 (PrinceXML)
├── Dockerfile             # [V4.7] Debian 12 + Fonts + PrinceXML
└── data/                  # 输出产物目录
```

-----

## ⚙️ 详细配置

### 命令行参数

| 参数 | 说明 | 示例 |
| :--- | :--- | :--- |
| `-r`, `--repo-path` | 目标仓库路径 (本地路径或 HTTP URL) | `/target_repo` 或 `https://github.com/...` |
| `-n`, `--number` | 分析最近 N 次提交 | `-n 10` |
| `-t`, `--time` | 分析时间范围 | `-t "1 day ago"` |
| `--llm` | 指定 LLM 供应商 | `gemini`, `deepseek`, `ollama` |
| `--style` | 文章生成风格 | `default`, `novel`, `cyberpunk`, `detective`... |
| `--attach-format` | 附件格式 | `html` (默认) 或 `pdf` |
| `--no-browser` | 禁止自动打开浏览器 | (Docker 模式下必需) |

-----

## 🌟 致谢与依赖

本项目基于以下优秀的开源库构建：

* **PyGithub**: GitHub API 交互
* **PrinceXML**: 高质量 HTML 转 PDF 引擎
* **Jinja2**: 强大的模板引擎
* **Ollama**: 本地大模型运行时

-----

## 📄 许可证

[MIT License](https://www.google.com/search?q=LICENSE)

Copyright (c) 2025 AzureDescent
