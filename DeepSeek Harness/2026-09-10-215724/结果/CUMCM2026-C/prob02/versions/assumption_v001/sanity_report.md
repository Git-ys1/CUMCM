# prob02 Sanity Check Report（Level 1–4，computation 结果验收）

> 小问：`prob02`；版本：`assumption_v001` / `formulation_v001`；阶段：`computation`
> 被检任务：`ea71568e2cf6c5326ded`（隔离 task，supervised worker，终态 `succeeded`，rc=0）
> 被检产物目录：`problems/CUMCM2026-C/prob02/versions/assumption_v001/results/prob02_m1_formulation_v001/`
> 判定：**PASS_WITH_WARNING**（L1–L4 硬门禁全部通过；仅 1 项非阻断文档技术债与若干上游口径技术债）
> 本报告由 sanity-checker 只读复核：未修改模型、代码、数据、上游产物，未创建新计算 task。

## 0. 结论

- **L1 文件和运行完整性：PASS**。task 终态 `succeeded`/rc=0/attempt=1/supervised；8 个产物均存在且非空；
  `code_hash`/`input_hash`/`source_config_hash`/`config_hash` 独立重算与 `task.json` 完全一致；
  `run_manifest.json` 的 code/输入 sha256 与文件裸 sha256 一致；4 个原始附件与 `request/attachments/` 逐字节相同。
- **L2 数值、范围与约束：PASS**。独立从 `solution.csv` 回代 (C1)(C2)(R)(C3)~(C8)：平衡、SOC、终端、
  储电量/功率边界、互斥、执行层互补性、弃光上界、非负性、整性全部在容差内（见 §2）；年度指标独立复算与
  `metrics.json`/`run_report.json` 一致；解析界门禁全部通过；`status=0` 334/334、`mip_gap ≤ 2.01e-16`。
- **L3 量纲、公式与实现一致性：PASS（含 1 项文档笔误技术债）**。电价/负载/光伏/预报逐列与附件 1/2/3 一致，
  式 (E) 展开规则按 `(t−1)//6` 实现且与附件 3 的 0:00 报表逐位相符；量纲自洽；big-M = Pbar = 833.33 由
  (C5) 导出；result2.xlsx 三表按 asm-15/asm-17 映射且与 solution 一致。**唯一缺陷**：`formulation.md`
  §3.7 的 (D-ex) 与首条全局恒等式把 (pv−pvfc) 项符号写反（文档式 +，正确式 −），与同节 boxed (R)、
  §3.7 自身推导及实测数据矛盾——属**文档笔误，不是实现不一致**（实现严格按 (R)，实测数据满足正确式）。
- **L4 常识与文献合理性：PASS**。18 个引用 ID 在 `prob02/shared/literature_pool.yaml` 与
  `CUMCM2026-C/citations.yaml` 中均 `verified=true`/`status=used`；关键假设门禁 `check_key_assumptions`
  实测 `passed=true`；费用方向、量级与解析界一致；u 只在 `pv<pvfc` 的时段出现（10877/10877）。
- **overall = PASS_WITH_WARNING**：无失败类型、无需回退；技术债已登记并移交交付/论文与 robustness。

## 1. Level 1：文件和运行完整性

| 项 | 证据 |
|---|---|
| task 终态 | `status.json`：`status=succeeded`、`returncode=0`、`attempt=1`、`worker_mode=supervised`、`feasible_incumbent=true`、`finished_at=2026-09-10T13:32:18Z` |
| 产物 | `solver_status.json` / `metrics.json` / `daily_metrics.csv` / `solution.csv` / `emergency_segments.csv` / `result2.xlsx` / `run_report.json` / `run_manifest.json` 均存在且非空 |
| 追踪链 | 独立重算 `hash_path`/`hash_json`：`code_hash=16a4effa…934d9`、`input_hash=4343d799…02d9434`、`source_config_hash=9f076ef0…8f0b4`、`config_hash=88a3d110…5ed0b`，与 `task.json` 完全一致 |
| 文件裸 hash | `run_manifest` 自报 `code_sha256=b2e85d61…549bb0`（55064 B）、附件 1 `66b87134…c377`、附件 2 `2e95fd44…4c2c72`、附件 3 `8a61b06c…9d843`、附件 5/result2 `1c26494c…a1a47`，与文件裸 sha256 逐一相同 |
| 数据完整性 | `data/附件1.xlsx`、`附件2.xlsx`、`附件3.xlsx`、`附件5/result2.xlsx` 与 `request/attachments/` 同名文件**逐字节相同**，原始数据未被修改 |
| 身份一致性 | `seed=20260102` 在 `task.json`/`solver_status.json`/`run_manifest.json` 三处一致；`mip_rel_gap=1e-6`、单日时限 120 s、总预算 1500 s、worker timeout 3600 s 与 `task.json` 一致 |
| 自动检查 | `scripts/run_sanity_check.py --task-id ea71568e2cf6c5326ded`：`failures=0`、7 个数值文件全部有限 |

## 2. Level 2：数值、范围与约束（独立回代）

从交付 `solution.csv`（334×144=48096 行）独立回代。**注**：`solution.csv` 以 `%.10g` 落盘，10 位有效数字的
存储舍入使绝对残差随量级放大（E~10⁴ 时约 1e-5），故 §2 表按量级取 3e-9 相对容差；求解器**内存精度**残差由
`metrics.json` 记录（另列一行，均 ≤1.4e-10，远小于 formulation §8 的 1e-6/1e-9 门禁）。

| 检查 | CSV 回代值 | 容差 | 判定 |
|---|---|---|---|
| (C1) 计划层平衡 max\|·\| | 5.00e-07 kWh | 3e-9·量级 | PASS |
| (B-ex)/(R) 执行层平衡 max\|·\| | 5.33e-07 kWh | 3e-9·量级 | PASS |
| (C2) SOC 递推 max\|·\| | 1.00e-05 kWh | 3e-9·量级 | PASS |
| (C4) 终端残留 max\|E₁₄₄−6000\| | 0.0 | 1e-6 | PASS |
| (C3) 储电量越界 | 0.0（E 触 1200/10800 不越界） | 1e-6 | PASS |
| (C5) 功率越界 | 0.0（C,D ≤ 833.33） | 1e-6 | PASS |
| (C6) 互斥 max min(C,D) | 1.85e-11 | 1e-9 | PASS |
| (R) 执行层互补 max u·κ_act | 0.0 | 1e-9 | PASS |
| (C8) κ ≤ pvfc·dt 越界 | 0.0 | 1e-6 | PASS |
| κ_act ≤ pv·dt 越界 | 3.33e-08（纯 CSV 舍入；内存精度 0.0） | 1e-6 | PASS |
| 非负性 min(q,C,D,κ,u,κ_act) | −2.11e-10 | 1e-9 | PASS |
| 整性 max\|y−round(y)\| | 0.0（y 精确 0/1，U1 已修复） | 1e-9 | PASS |
| u 与闭式投影一致性 | 6.67e-08（CSV 舍入） | 3e-9·量级 | PASS |
| NaN/Inf | 0 | — | PASS |
| 内存精度残差（metrics.json） | 平衡 9.46e-11 / SOC 1.36e-10 / 互斥 1.85e-11 / 非负 2.11e-10 / NaN·Inf 0 | 1e-6/1e-9 | PASS |

**独立指标复算**（与 `metrics.json`/`run_report.json` 一致）：

| 指标 | 独立复算值 |
|---|---|
| `Cost_plan` | 12 570 533.9138 元（解析界 [6 749 147.6122, 16 565 407.2763]） |
| `Cost_em` | 4 828 772.4163 元（≤ 上界 5 815 010.6013） |
| `Cost_total` | 17 399 306.3301 元（≥ 下界 6 660 821.0595） |
| `Q_plan` | 20 385 219.0362 kWh（≥ 下界 18 177 074.097） |
| 充电 / 放电 | 6 563 006.6215 / 5 316 035.3636 kWh（ΣD = 0.81·ΣC 闭合） |
| 计划弃光 κ* / 实际弃光 κ_act | 961 173.6810 / 2 355 847.6824 kWh（2 306 / 16 440 个时段） |
| 紧急购电量 / 时段 / 段 | 1 156 789.3993 kWh / 10 877 / 1 919（max 14 段/日） |
| `u=0` 的天数 | 0（334 天全部出现紧急购电，逐日显式登记） |
| 能量恒等式 | Σq = Σ(load−pvfc)dt + 0.19ΣC + Σκ* ✓；Σq+Σu = Σ(load−pv)dt + 0.19ΣC + Σκ_act ✓ |

**求解质量**：`status=0` 334/334（days_feasible_not_optimal=0）、`max mip_gap=2.01e-16`、
`best_bound` 与 `objective` 最大偏差 = 0、`max node_count=1`、总运行 32.64 s（预算 1500 s），
`Pbar=big_m=833.3333`，M1 规模 864 变量/289 等式/288 不等式，与 `implementation.md` §3 完全一致。
M2（真 LP 松弛）：目标与 M1 相同，`lp_strictly_better_days=0`、LP 原始解 `max min(C,D)=0.0`，
交付解取自 M1。**无超时/gap 技术债**。

## 3. Level 3：量纲、公式与实现一致性

- **量纲自洽**：`price` 元/kWh × `q` kWh = 元；功率 kW × `dt=1/6 h` → kWh；`Pbar=Pmax·dt=833.3̄ kWh`；
  平衡式 (C1)/(B-ex) 各项均为 kWh。
- **式 (E) 预报展开**：`solution.csv` 的 `pvfc` 与附件 3 的 0:00 报表按 `(t−1)//6` 展开逐位相同（最大偏差 0）；
  `price`、`load`、`pv` 分别与附件 1、附件 2 逐位相同（最大偏差 0）；`price` 逐日恒定（asm-13）。
- **实现 ≡ formulation**：`prob02_solver.py` 的 blocks 排布与 (C1)~(C8)、(O)、(R) 逐条对应；
  逐日模型规模、big-M、`mip_rel_gap` 显式设定均与文档一致；`--mode both` 交付解只取 milp。
- **交付映射**：`result2.xlsx`
  - 「计划购电量」334×147，列标签为物理区间 `0:00-0:10 … 23:50-24:00`（asm-15 重写），
    第 t 列 = 时段 t 的 `q`（与 solution 相差 ≤5e-4，即 3 位小数舍入）；末两列 = `Q_plan_d`、`Cost_plan_d`；
  - 「充放电量」334×6=2004 行，6 个 4 小时块 ΣC/ΣD 与逐时段解一致，首行 `00:00`/次行 `24:00` 置 6000；
  - 「紧急购电量」1919 行，逐段合并（asm-17），段合计与逐时段 u 之和在容差内闭合（≤1e-6/段），
    日期列只在首段出现；`u=0` 的日期按「无」显式登记（本期为 0 天）。
- **文档笔误（技术债 W1）**：`formulation.md` §3.7 式 (D-ex) 写作
  `u−κ_act = (pv−pvfc)dt − κ*`，正确推导（(B-ex)−(C1)）应为 `u−κ_act = −(pv−pvfc)dt − κ*`；
  紧随其后的 `s := κ*+(pv−pvfc)dt` 与 boxed (R) 均是正确式。实测数据：`Σu−Σκ_act = −1 199 058.283`，
  正确式 `−1 199 058.283`（匹配）、文档式 `−723 289.079`（不匹配）。§3.7 第二条恒等式（Σq+Σu）正确。
  **结论：文档符号笔误，实现 (R) 与全部交付数值正确且自洽；须在下一公式版本或交付勘误中修正，禁止把 (D-ex) 原样写入论文。**

## 4. Level 4：常识、极端行为与文献合理性

- **引用门禁**：`check_key_assumptions('CUMCM2026-C','prob02')` → `passed=true`；正文/假设/实现共引用
  **18** 个 `ref-prob02-*` ID，全部在文献池与 `citations.yaml` 中 `verified=true` 且 `status=used`，
  无缺失、无未核验。
- **机制合理性**：u>0 的 10 877 个时段**全部**满足 `pv < pvfc`，且 `u ≤ (pvfc−pv)⁺dt`（最大超出仅 3.3e-8，
  为 CSV 舍入），符合 (R)「实际低于预报→紧急购电」；`κ_act = max(0, κ*+(pv−pvfc)dt)` 与 u 互斥
  （互补性违反 0）。四个指定日期（2025-03-20/06-21/09-23/12-21）预报缺口 6 059.487 / 3 812.266 /
  3 500.289 / 2 272.067 kWh 与 `formulation.md` §7 登记值逐位一致，且当日 u（6059.487 / 1670.831 /
  3500.289 / 2272.067）均 ≤ 缺口，符合「缺口是 u 的上界（还需扣 κ*）」的登记。
- **数量级与边界**：日均 `Cost_plan`≈37 636 元、`Cost_total`≈52 093 元，与 prob01 同设备层代表日
  35 127 元同量级；`Cost_plan` 较无储能证书上界（16 565 407 元）低 24.1%、高于能量型下界（6 749 148 元），
  与 3.76 倍电价极差、5 MW/10.8 MWh 储能及 334 天逐日光伏波动相匹配，未见异常。
- **不可避免弃光**：计划弃光 961 174 kWh、实际弃光 2 355 848 kWh（16 440 时段），远大于探针登记的
  不可避免部分（272/241 时段），符合日循环 (C4) 与功率上限下「贴界」导致的强制弃光；方向与幅度合理。
- **边界声明（随上游移交，须写入论文）**：asm-02 口径张力（题面数据清单未列附件 3，主口径把 0:00 预报
  纳入信息集；alt-01 下 u≡0）、asm-06（日循环 6000）、asm-09（单向 90%/并网点侧）、asm-14（不建模退化）、
  asm-08（不反送）、asm-15（标签重写）均须在论文边界章节与交付说明登记。

## 5. 技术债与移交项

| ID | 级别 | 内容 | 处置 |
|---|---|---|---|
| W1 | 文档 | `formulation.md` §3.7 (D-ex) 与首条全局恒等式 (pv−pvfc) 项符号写反（实现与数据均为正确式） | 下一公式版本修正，或交付前出勘误；**不得**把 (D-ex) 写入论文 |
| W2 | 口径 | 题面问题 2 数据清单只列附件 1/2，主模型按 asm-02 使用附件 3 的 0:00 预报 | 论文边界章节 + 交付说明显式声明，并给出 alt-01（u≡0）对照 |
| W3 | 口径 | 全天购电量/购电费取**计划口径**（`Q_plan`/`Cost_plan`），与含紧急购电费的 `Cost_total` 不同 | 交付阶段登记映射并同时给出两个数（result2.xlsx 与论文表 1） |
| W4 | 假设 | asm-06（E₀=E₁₄₄=6000 日循环）、asm-09（单向 90%、并网点侧、833.33 kWh）为 project_assumption | robustness 必须做 E^cyc∈{4800,6000,7200}、往返 0.9（单侧 0.9487）与电池侧计量口径对照 |
| W5 | 假设 | asm-08（不反送）、asm-14（不建模退化）会高估套利/低估费用 | 论文边界章节声明 |
| W6 | 口径 | asm-15 标签重写与附件 5 模板字面标签存在整体一个时段偏移（有意统一） | 交付阶段在 result2.xlsx 与论文同步登记映射，不得静默改变 |
| W7 | 交付 | 弃光「零」的预期不成立（κ* 961 174 kWh / κ_act 2 355 848 kWh） | 论文如实报告并按段给发生时段与原因 |
| W8 | 说明 | `solution.csv` 的最小值 −440.83 来自**派生量 `surplus_kwh`**（s 可为负），并非物理量负值 | 交付/绘图不得把 surplus 当弃光或购电量使用 |

## 6. 路由与建议

- **不路由回退**：无 NaN/Inf、无硬约束违反、无量纲/量纲错误、无实现与 (R) 的语义不一致、原始数据未修改、
  追踪链完整，故 L1–L4 不触发 `NEEDS_REVISION`/`VERSION_REJECTED`。
- **建议下一阶段**：`visualization`（L1–L4 已通过，满足 `workflow.transition` 对进入 visualization 的门禁）；
  随后按预注册计划执行 robustness（asm-06/asm-09 端点与效率口径、alt-01 u≡0 验证），再由 Level 6 sanity 验收；
  Level 5 跨小问一致性在全部小问 locally completed 后执行。
- W1 属公式文档技术债，建议在 robustness 期间或论文定稿前以 formulation_v002 修正（若修正公式版本，须注意
  会改变 task 身份字段并触发新 task_id；本结果本身无需重跑）。

## 7. sanity_check 阶段确认（动作 `act-9c0509ccba81446b`，policy P3）

> 阶段：`sanity_check`；被检对象：`assumption_v001` / `formulation_v001` 的 computation 交付
> （task `ea71568e2cf6c5326ded`，目录 `results/prob02_m1_formulation_v001/`）。
> 复核方式：只读独立探针 `runtime/tmp/prob02_stage_sanity_probe.py`（输出 `runtime/tmp/prob02_stage_sanity_probe.json`，
> 共 **85 项自动检查、0 失败、1 警告**），不重跑优化、不创建 task、不修改模型/代码/数据/上游产物。

- **L1 维持 PASS**：task 终态 `succeeded`/rc=0/`supervised`/`consumed=true`；`code_hash`/`input_hash`/
  `source_config_hash`/`config_hash` 独立重算与 `task.json` 逐项一致；`run_manifest` 的 code/4 个输入 sha256
  与文件裸 sha256 一致；`data/附件1、附件2、附件3、附件5/result2` 与 `request/attachments/` 同名文件**逐字节相同**，
  原始数据未被修改；`seed=20260102` 与 `mip_rel_gap=1e-6` 三处一致。
- **L2 维持 PASS**：由 `solution.csv` 独立回代 (C1)(C2)(R)(C3)~(C8)——计划层平衡 5.00e-07、执行层平衡 5.33e-07、
  SOC 1.00e-05、终端残留 0.0、储电量/功率越界 0.0、互斥 1.85e-11、执行层互补 0.0、κ 上界越界 0.0、
  非负性 2.11e-10、整性 0.0、NaN/Inf 0（均为 10 位有效数字落盘舍入量级）；年度指标独立复算与
  `metrics.json`/`run_report.json` 一致；解析界四条门禁全部通过；334/334 `status=0`、`max mip_gap=2.01e-16`、
  `best_bound=objective`、`max node_count=1`、总运行 32.64 s；紧急购电分段逐日合计与逐时段 u 之和闭合（≤1e-6）。
- **L3 维持 PASS（W1 仍为文档技术债）**：电价/负载/实际光伏/0:00 预报分别与附件 1/2/3 逐位一致（最大偏差 0）；
  `result2.xlsx` 三表按 asm-15/asm-17 映射且与 solution 一致（计划表 334×147、物理区间标签、3 位小数容差；
  充放电表 6 个 4 小时块、E₀/E₁₄₄=6000；紧急购电表 1919 行与 `emergency_segments.csv` 行数相同）。
  **W1 复核**：实测 `Σu−Σκ_act = −1 199 058.283` 与**正确式**（−(pv−pvfc)dt − κ*）一致、与文档式（−723 289.079）
  不符，确认 §3.7 (D-ex) 为文档符号笔误，实现 (R) 与全部交付数值正确。`surplus_kwh` 与闭式 s 一致（可为负，非物理量负值）。
- **L4 维持 PASS**：18 个 `ref-prob02-*` 引用 ID 在 `prob02/shared/literature_pool.yaml` 与
  `CUMCM2026-C/citations.yaml` 中均 `verified=true`/`status=used`，无缺失；关键假设门禁维持 passed。
- **阶段判定**：L1–L4 维持 **PASS_WITH_WARNING**；**无新增技术债**（W1–W8 与 computation 阶段登记一致），
  无 failure_type、无需回退。按 `wiki/workflow-states.md` 主流程由 `sanity_check` 迁移至 `visualization`；
  `robustness`（asm-06 端点 E^cyc∈{4800,6000,7200}、asm-09 单向 90%/电池侧计量口径、alt-01 下 u≡0 对照）
  与 Level 6 sanity 随后执行；Level 5 跨小问一致性在全部小问 locally completed 后执行。
- 本动作只读复核并追加本节，未修改模型、代码、数据、task 结果或任何上游版本。
