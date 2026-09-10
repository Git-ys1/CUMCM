# 数模 Skills 调用与安装登记

日期：2026-09-10。使用载体为本机 Codex。来源：[BZD Skills 分享](https://bzdshumo.com/)及本机《数模Skills 怎么用？从导入到评分完整演示》完整字幕；网页快照和字幕副本在 `docs/sources/`。

## 已安装

安装目录：`F:\AcademicHub\.codex\skills`（当前 CODEX_HOME），通过系统 skill-installer 按已核对的 Git commit 安装，保留 assets、references、scripts、模板等完整内容。下一轮对话可发现新 Skills。

共 **26 个可调用 Skill + 1 个共享参考目录**：

- BZD：16 个。包含网页列出的 15 个不同名称和上游新增总控 `bzd-modeling-workflow`。
- MathModelAgent：9 个可调用 Skill，包括六阶段流程、doctor、mathmodel-figure-templates、typst-author；另有 `_references` 共享规范目录，不单独调用。
- Humanizer-zh：1 个，安装名 `humanizer-zh`。

来源仓库：

1. https://github.com/BZDmathclub/bzd-math-modeling-skills
2. https://github.com/jihe520/MathModelAgent
3. https://github.com/op7418/Humanizer-zh

完整源码保留在本工作区 `skill-sources/`；每项来源、commit、源路径、安装位置见 [安装清单](verification/skills-installed.json)，验收见 [验证报告](verification/skills-validation.json)。BZD 同名分类副本内容相同，安装一份；参考文献检查器的嵌套重复目录选择内层完整 Skill，避免重复发现。

MathModelAgent 的 Skills 已安装，独立 Web 应用仅归档源码，没有另起其后端服务。网站所列商业平台和工具不是 Skills，不代为注册或购买。AutoMM 仍是当前计算 Harness。

## 六阶段调用顺序

| 阶段 | 调用 | 输入 → 输出 |
|---|---|---|
| 1 读题 | `$bzd-problem-translator` | 完整题面、附件说明 → 逐句解释、条件、任务映射、跨问关系 |
| 2 思路与选型 | `$bzd-modeling-ideas`，再 `$bzd-model-dictionary` | 题意、真实数据结构 → 全题主线、候选比较、模型适用条件与验证计划 |
| 3 求解与写作 | `$bzd-problem-restatement` 生成模式；AutoMM 管计算，Codex 协助写作 | 已审查思路、数据 → 可追溯的代码、结果、图表和论文草稿 |
| 4 内容自查 | 下表九项 | 同一版本论文与证据 → 分章问题、人工核验与修改记录 |
| 5 格式自查 | `$bzd-paper-format-checker` | 最终 PDF、可选 Word、当届规范 → 格式、匿名与文件检查 |
| 6 综合评审 | `$bzd-review-paper`；按需 `$bzd-cumcm-school-awards` | 相同版本论文、题目、格式报告及真实背景 → 经验评分、问题优先级和竞争参考 |

阶段 4 顺序：

1. `bzd-abstract-checker`
2. `bzd-problem-restatement`（检查模式）
3. `bzd-problem-analysis-checker`
4. `bzd-model-assumption-checker`
5. `bzd-symbol-notation-checker`
6. `bzd-model-solution-checker`
7. `bzd-reference-appendix-checker`
8. `bzd-ai-usage-disclosure`
9. `bzd-paper-aigc-auditor`

总入口可直接说：

```text
调用 $bzd-modeling-workflow。
当前阶段：刚拿到题目。
题面和附件位置：<实际路径>。
请先完成题意解释、全题建模路线和模型适用性检查。
计算阶段衔接本工作区 AutoMM，保留阶段报告和验证证据。
```

这是调用示例；本次安装没有真实赛题，因此没有执行这些建模和评审任务。后续按材料成熟度选阶段，不机械把所有 Skills 跑一遍。

## 与 AutoMM 的职责衔接

Codex 用 BZD 总控选择阶段和执行专项技能；AutoMM 保留其状态机、专职 Agent 和隔离计算任务。不能将另一套工作流的 plan/todo 或报告字段直接写入 AutoMM 受保护状态；输入解释、候选模型、评审报告应作为显式交接材料，由当前阶段按协议处理。

MathModelAgent 的 `1start-mathmodel` 是另一套完整总控。不要与 BZD 总控同时各自推进同一份题目。其 `2analysis-modeling`、`3coding-visual`、`4drawio`、`5writing`、`6verity` 可在合适范围使用，遵守 AutoMM 计算边界。

本次安装到 Codex 的全局 Skills，不代表 AutoMM 的 DSH Agent 会自动发现并调用全部新 Skills；直接让 DSH 使用它们需要后续明确接入和调用验证。

## 本机使用边界

- BZD 字典和学校查询使用随包本地数据；数据新旧与统计口径需要核验，查询结果不是官方当年结论。
- 字幕“35 分能省奖”等是作者经验，不作为真实分数线。质量分、格式分、竞争预测分别记录。
- `humanizer-zh` 用于改善措辞和可读性；保留事实、引用及真实 AI 披露，不生成虚假人工核验记录，也不承诺通过 AIGC 检测。
- 部分 MMA 示例写 Linux 路径或 Claude 工具名。在 Windows/Codex 上转换为实际可用路径和工具，不盲跑示例 shell 命令。
- Typst、XeLaTeX、DrawIO 等是按产物选用的外部工具，Skill 文件安装不等于这些工具全部就绪；本次未编译真实论文。
- 安装验收覆盖文件哈希、元数据、Python 语法及附带脚本探针；不等于所有技能在真实比赛任务上的效果验收。
