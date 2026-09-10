# AutoMM 本机部署与运行

验收日期：2026-09-10。状态：本机依赖、CLI、配置和合成测试通过；DeepSeek 官方 API 已配置并通过真实调用和 AutoMM provider 响应 schema 校验。完整建模流程尚未验收。

当前模型沿用本机设置：`deepseek-v4-flash`，`reasoningEffort: high`。密钥仅保存于 DSH 本机凭据文件，不记录其值。验证见 [真实往返](verification/deepseek-roundtrip.json) 和 [provider 校验](verification/deepseek-provider-probe.json)。

## 安装位置与版本

- 仓库：`F:\AcademicHub\000资料相关\数模\26国赛\AutoMM`
- 上游：[sghwr/AutoMM](https://github.com/sghwr/AutoMM)，0.0.4 Beta，commit `d0d97fd52bd633d9641bb02d879eacd6c29af569`。
- Python：项目 `.venv\Scripts\python.exe`，3.12.14；基础解释器复用本机 Codex bundled runtime，没有改系统 Python。其基础位置为 `C:\Users\yusu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`，该运行时若迁移或清理，需要重建 venv。
- Python 依赖：按上游 `scripts/requirements.txt` 安装；实际版本清单见 [requirements-installed.txt](verification/requirements-installed.txt)。未安装可选 uv，采用上游支持的 venv + pip 路线。
- Node.js：已有 v24.11.0，`F:\CodeForge\Node\node.exe`。
- DSH：npm 全局安装 `@deepseek-ai/dsh@0.1.5-rc.1`；入口 `C:\Users\yusu\AppData\Roaming\npm\dsh.cmd`；headless profile 已初始化。
- 当前计算后端：local，上游默认最多 4 个本地任务并结合内存自动约束。SSH 未启用、邮件未启用。
- 上游源码和配置没有修改，Git 工作区验收时干净。

## 已完成的验收

| 检查 | 结果与证据 |
|---|---|
| pip check 与科学计算依赖 import | 通过；numpy/pandas/scipy/sklearn/openpyxl/matplotlib/paramiko/jsonschema/psutil/PIL 可导入。 |
| 配置校验 | 16 个配置通过，[local-check.txt](verification/local-check.txt)。 |
| compileall scripts tests | 退出码 0。 |
| pytest | 72 passed，35.85 秒，[pytest.txt](verification/pytest.txt)。合成 fixture 位于临时目录，不是正式赛题运行。 |
| DSH | 版本、headless help、provider.probe、真实 JSON 往返与 provider 响应 schema 校验通过。 |
| Runner 入口 | --help 正常，[runner-help.txt](verification/runner-help.txt)。 |
| Dashboard | 首页及 state/tasks/tree/events/log 共 6 个 HTTP 端点为 200，[dashboard.json](verification/dashboard.json)。未将 HTTP 检查称作浏览器视觉验收。 |
| Ruff | 未通过：100 项，其中 E501 80、I001 14、F401 6；[ruff.txt](verification/ruff.txt)。均为当前上游静态规范问题，本次部署未批量改写源码。 |

## 日常入口

在 `26国赛` 目录使用 PowerShell：

```powershell
.\automm.ps1 check
.\automm.ps1 monitor
```

脚本固定使用项目 Python，并把 venv 放到子进程 PATH，避免系统旧 Python 或找不到 Ruff。Dashboard 地址：[http://127.0.0.1:8765](http://127.0.0.1:8765)。本次已后台启动；若端口已有服务，不要再重复启动。进程 ID 记录于 `verification/monitor.pid`，日志在同目录。关闭时先核对 PID 的程序确为本项目 monitor，再停止；PID 可能在重启后被复用。

## 凭据与模型设置（已完成，需要更换时使用）

```powershell
.\automm.ps1 configure-ai
```

它调用上游 `dsh web`，在本机 DSH 页面按提示配置官方 API 和实际使用模型。不要把 API key 发到聊天、仓库或学习文档。当前默认 DSH home 为 `C:\Users\yusu\.dsh`；若设置 `DSH_HOME` 则以该变量为准。上游说明的设置/凭据位置为 `settings.yaml` 与 `.credentials.yaml`，不要覆盖已有配置。

配置后先从 `26国赛` 根目录做一个小型模型往返（此处没有 AutoMM 的阶段 JSON 规则）：

```powershell
dsh.cmd --profile headless '只输出 JSON 对象 {"status":"ok"}，不要使用工具。'
```

本次实际退出码 0，输出为指定 JSON；另经 AutoMM provider 调用真实模型并通过 Agent JSON schema 校验。尚需在隔离往年题/合成题工作区验证工具执行、任务计算、sanity、跨问检查和总结链路；当前连通性检查不等于完整研究流程验收。

## 正式题目开始前

重要：本次检出的 `request/problem.md` 实际是 2024 C 题《农作物的种植策略》示例，尽管 README 声称发布不含真实赛题。保留此上游文件以便追踪，正式运行前必须替换为本次官方题面并核对所有附件和数据。

1. 将正式题面和数据放到 README 指定位置；原始数据不原地清洗或覆盖。
2. 确认题号、小问数、目标、约束及输出模板；不要照抄 SETUP.md 的 crop_2024 启动 prompt。
3. 在 AutoMM 目录用项目 Python 执行 `scripts\harness.py init-problem --problem-id <实际ID> --questions <实际小问数>`。
4. 回到本目录运行 `.\automm.ps1 once` 做单步检查；确认 Agent 往返与日志后，再运行 `.\automm.ps1 daemon`。
5. 按 [视频学习与评分导向](视频学习与评分导向.md) 执行人工审查，填写 [AI使用记录模板](AI使用记录模板.md)。

## 已识别的上游文档差异

- SETUP.md 一处称邮件强制依赖，但默认配置 `enabled: false` 且通过校验。当前先用本地仪表盘；邮件收发须另行配置与验收，不自行发送测试邮件。
- SETUP.md 末尾建议直接修改 workflow_state 解除部分阻塞，与 AGENTS.md/PROJECT.md 的受保护状态规则冲突。后续以状态机命令及合法恢复路径为准，不照抄直接改状态的片段。
- README 提到 `*.local.yaml`，但 `scripts/automm/common.py` 的通用配置读取将其作为独立 stem，不能假设任意 local 文件都会覆盖基础配置。以后配置具体后端时应检查对应实际读取逻辑。
- 本机全量测试通过不等于上游 Ruff 门禁通过，也不证明整题建模质量。

## 后续待办

- DeepSeek 官方凭据、真实 JSON 往返和 provider schema 校验已完成；隔离整题试跑待进行。
- 接收用户之后提供的 skills，核对它们与 Harness 阶段和团队验收要求的衔接。
- 补充学校/赛区通知、官方当前提交模板，以及正式题目与数据。
- 若要开启邮件或 SSH，再配置并分别验证；当前本地模式不依赖它们。
