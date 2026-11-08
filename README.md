# YunAgent Next

一个面向本地运行的桌面 AI Agent。YunAgent Next 将 Electron 桌面端与 Python/FastAPI Host 结合，支持对话式任务执行、运行记录、自动化、审批、记忆与交付物管理，并可配置多种模型服务和 MCP 工具。

## 功能

- **对话与任务运行**：通过桌面对话提交任务，查看运行状态和历史记录。
- **自动化与持续任务**：管理定时自动化及 Agent 维护的持续任务。
- **审批与权限**：查看待审批操作，并管理工具授权范围。
- **记忆与知识管理**：查看和维护长期记忆、知识条目及技能。
- **交付物管理**：查看 Agent 运行过程中生成的文件。
- **模型配置**：支持 OpenAI、Qwen、DeepSeek 和 Anthropic，可分别配置模型、Base URL 与 API Key。
- **MCP 扩展**：连接 MCP Server，并配置工具权限、文件系统范围和网络策略。
- **可选电脑操作**：支持通过本地辅助程序观察和操作桌面；需要 macOS、辅助程序及系统权限，默认关闭。

## 架构

- **desktop/**：React 与 Electron 桌面应用。
- **backend/**：Python/FastAPI Host，通过 WebSocket RPC 与前端通信，并使用 SQLite 保存状态。
- Docker 模式由 Host 同时提供浏览器界面和 RPC 服务。

## 快速开始：Docker

需要安装 Docker，并确保 Docker Compose 可用。以下示例使用 PowerShell；Linux 或 macOS 用户可在启动前设置环境变量 **KORENEXT_API_KEY**。

在项目根目录运行：

~~~powershell
$env:KORENEXT_PROVIDER = "openai"
$env:KORENEXT_MODEL = "gpt-4.1-mini"
$env:KORENEXT_API_KEY = "YOUR_API_KEY"
docker compose up --build -d
~~~

启动后打开 [http://127.0.0.1:8765](http://127.0.0.1:8765)。查看容器日志：

~~~powershell
docker compose logs -f yunagent
~~~

停止服务：

~~~powershell
docker compose down
~~~

Docker Compose 将运行数据、工作区和用户技能保存在命名卷中。Docker 容器运行在 Linux 环境中；通过桌面设置页保存 API Key 的方式需要 macOS Keychain 或 Windows DPAPI，因此 Docker 模式请通过环境变量提供 API Key。请勿将真实密钥提交到 GitHub。

## 本地开发：桌面端

需要 Python 3.11 或更高版本，以及 Node.js 20 或更高版本。

### 启动后端

在项目根目录打开 PowerShell：

~~~powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
python -m kore_next.server
~~~

Host 默认监听 127.0.0.1:8765。macOS 或 Linux 用户可创建并激活虚拟环境后安装 backend/requirements.txt，再设置 PYTHONPATH=backend 并运行 python -m kore_next.server。

### 启动桌面端

保持后端运行，在另一个终端执行：

~~~powershell
cd desktop
npm ci
npm run electron:dev
~~~

应用启动后，可在“设置”页面配置模型服务，并测试连接。Windows 与 macOS 的桌面端可通过系统凭据保护机制保存 API Key。

## 配置

后端从环境变量读取配置。当前实现的变量前缀仍为 **KORENEXT_**。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| KORENEXT_PROVIDER | openai | 默认模型服务 |
| KORENEXT_MODEL | gpt-4.1-mini | 默认模型 |
| KORENEXT_API_KEY | 空 | API Key；也可使用桌面设置页面配置 |
| KORENEXT_BASE_URL | https://api.openai.com/v1 | 模型服务 Base URL |
| KORENEXT_HOST | 127.0.0.1 | Host 监听地址 |
| KORENEXT_PORT | 8765 | Host 监听端口 |
| KORENEXT_DATA_DIR | backend/.yunagent-next | 数据库、记忆、设置与交付物目录 |
| KORENEXT_WORKSPACE_DIR | backend/workspace | Agent 工作区 |
| KORENEXT_USER_SKILLS_DIR | ~/.yunagent-next/skills | 用户技能目录 |
| KORENEXT_COMPUTER_ENABLED | false | 是否启用可选电脑操作 |

Docker Compose 会将数据目录、工作区和用户技能映射到持久化命名卷。

## 安全与平台说明

- Host 默认只监听本机地址。除非已配置并理解相应的访问控制，否则不要将服务端口暴露到公网或不可信网络。
- MCP Server 的权限、文件访问范围和网络策略应按需要设置；使用前请检查其命令和参数。
- 电脑操作默认关闭。启用前需要准备 macOS 辅助程序并授予所需的系统权限。
- 当前工作区沙箱能力依赖 macOS；在 Windows 和 Docker/Linux 环境中，部分 Shell 与默认 MCP 工作区工具不可用。
- 请通过本机环境变量或桌面端设置管理密钥，不要把 API Key 写入源码、README 或提交到仓库。

## 基准评测

项目包含 SWE-bench 与 FeatureBench 的评测入口。依赖、命令及评分方式见 [RUN_ON_DOCKER.md](RUN_ON_DOCKER.md)。该文档注明，当前项目尚未完成真实 Docker 构建和端到端评测验证。

## License

本仓库尚未声明开源许可证。添加许可证文件前，请确认项目代码及依赖的授权条件。
