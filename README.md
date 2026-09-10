# 2026 国赛工作区

本目录部署 AutoMM，作为研究流程、版本、计算任务和证据的管理入口。团队主导建模判断；Codex 协助审查、调度、实现与复现。先经过 Harness 流程，再决定采用哪些成果。

## 入口

- [Skills 调用与安装登记](docs/Skills调用与安装登记.md)
- [快速使用](docs/快速使用.md)
- [部署与运行](docs/AutoMM部署与运行.md)
- [视频学习与评分导向](docs/视频学习与评分导向.md)
- [AI 使用记录模板](docs/AI使用记录模板.md)
- [AutoMM 上游安装说明](AutoMM/SETUP.md)
- [AutoMM 阶段规则](AutoMM/PROJECT.md)

原始视频笔记保留于 `C:\Users\yusu\Documents\Obsidian Vault\Clippings\Bilibili`；本地副本与校验信息在 `docs/sources/`。后续 skills 等用户提供后再配置。

## 每次开工

1. 阅读本目录文档，进入 AutoMM 后阅读其 AGENTS.md、PROJECT.md、RESEARCH_LOOP.md。
2. 检查题面、数据、既有状态和产物，再推进对应阶段；不直接修改受保护状态。
3. 题面放 `AutoMM/request/problem.md`，附件放 `AutoMM/request/attachments/`，数据放 `AutoMM/data/`。
4. 简单基线先行；每项复杂化需要证据。结论必须能追溯到输入、假设、公式、代码、输出和校验。
5. 同步填写 AI 使用记录，团队逐项确认采纳、修改和核验结果。
