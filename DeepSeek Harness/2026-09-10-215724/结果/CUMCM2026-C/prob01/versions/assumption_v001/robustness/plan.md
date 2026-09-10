# prob01 鲁棒性分析预注册方案（assumption_v001 / formulation_v001）

> 小问：`prob01`（固定电价与负载下的单日计划购电模型）。
> 上游：`assumptions.md`（asm-01~asm-12）、`formulations/formulation_v001/formulation.md`、
> `code/prob01_solver.py`、`results/prob01_m1_formulation_v001/`（task `13bf04ee604e54581fa2`）、
> `sanity_report.md`（L1–L4 = PASS_WITH_WARNING，6 项非阻断技术债）。
> 本文件是**预注册方案**：在运行任何扰动扫描之前写定。运行开始后不得修改本文件；
> 任何事后追加的分析必须在 `stability_conclusion.md` 中显式标注为 `post-hoc`，不得改写本文件的判据。

## 0. 适用性决定

**robustness 适用（decision = completed，待扫描结束后确认）。** 理由：

1. 主模型存在 5 条 `project_assumption`（asm-02 终端取值、asm-03 弃光/反送、asm-04 效率口径、
   asm-05 计量侧与功率折算、asm-12 时间标签），题面与文献均不能唯一确定，属典型「脆弱参数」；
2. L1–L4 sanity 已确认最优解**贴运行边界**（弃光 = 0 使 $E_t$ 同时贴到上界 10800 与下界 1200），
   边界取值的变化可能改变结论，必须做端点敏感性；
3. 上述假设在 `sanity_report.md` 与 `workflow_state` 中被明确要求由 robustness 对照。

不适用项：本模型为**确定性 MILP**，无随机初始化、无随机算法分支，故「随机重启 / 初始化稳定性」
不适用；`solver seed` 仅登记不构成随机源（HiGHS 确定性分支定界）。

## 1. 被检核心结论（在看到扫描结果前固定）

| ID | 核心结论 | 基线值（task `13bf04ee604e54581fa2`） |
|---|---|---|
| K1 | 单日最优购电费 $Cost_{day}\approx 3.513\times 10^4$ 元，购电量 $Q_{day}\approx 5.948\times 10^4$ kWh | $Cost_{day}=35126.94858928963$，$Q_{day}=59482.69899835391$ |
| K2 | 全天弃光为 0（asm-03 零收益口径下不存在被迫弃光） | `curtail_total = 0.0` |
| K3 | 储能低电价充电 / 高电价放电，使全天购电费**严格低于**无储能情形 | 待扫描给出 $Cost^{nostorage}_{day}$ |
| K4 | 含互斥的 M1 与真 LP 松弛 M2 目标一致（真实实例上验证 open_item I1），交付解不含同时充放电 | M1 = M2 = 35126.94858928963，`min(C,D)=0` |

**基线锚定**：任何情景若使用基线参数，其 `cost_day` 必须复现 $35126.94858928963$ 元
（绝对容差 $10^{-6}$ 元），否则整个扫描作废并按 `code_runtime` 路由。

## 2. 稳定性判据（预注册，不得事后修改）

| ID | 判据 | 通过阈值 |
|---|---|---|
| C1 | **数值合法性**：每个情景 MILP `status=0`、可行 incumbent 存在，且回代硬门禁全过（平衡/SOC/边界/终端/功率/非负残差 $\le 10^{-6}$，互斥 $\max_t\min(C_t,D_t)\le 10^{-9}$，无 NaN/Inf） | 全部情景通过 |
| C2 | **假设口径稳定性**：asm-02 端点（$E_0{=}4800/7200$）、asm-04 往返效率 0.9（单侧 0.9487）、asm-05 电池侧计量、asm-03 允许零收益反送 这 5 类口径情景的 $\lvert\Delta Cost_{day}\rvert/Cost_{day}$ | $\le 10\%$ |
| C3 | **参数扰动包络**：price / load / pv / $P_{max}$ / $\eta$ 的单参数 $\pm5\%,\pm10\%,\pm20\%$ 扰动 | $\lvert\Delta Cost_{day}\rvert/Cost_{day}\le 25\%$ |
| C4 | **结构结论稳定性**：(a) 无弃光情景占非蒙特卡洛情景比例 $\ge 90\%$；(b) 所有情景 $Cost_{day}<Cost^{nostorage}_{day}$（K3 严格成立）；(c) 基线 M1 与 M2 目标差 $\le 10^{-7}$ 元（K4） | (a)(b)(c) 全部通过 |
| C5 | **时间标签口径**：asm-12 的整体错位一个时段（循环移位 1 个 10 分钟）对 $Cost_{day}$ 的影响必须被量化登记；**不作为失败判据**，作为交付风险登记 | 报告 $\lvert\Delta\rvert/Cost_{day}$ 与方向 |
| C6 | **输入不确定性（蒙特卡洛）**：price/load/pv 独立 $\pm5\%$ 均匀乘性噪声 200 次，$Cost_{day}$ 的 95% 分位区间宽度 $\le 15\%$ 基线，样本均值偏离基线 $\le 5\%$ | 同时满足 |

**判定规则（预注册）**

- 任一情景违反 C1 → verdict = `needs_revision`：按失败性质路由（模型/实现不一致 → `mathematical_formulation`；
  代码或求解异常 → `implementation`），**不得**进入 Level 6 或记录 robustness completed。
- C1 通过但 C2 或 C3 违反 → verdict = `fragile`：robustness 记 `completed`，但必须在结论、
  论文边界与 Level 6 报告中列出脆弱参数、方向与幅度。
- C1–C3 通过、C4(a) 或 C4(b) 违反 → verdict = `stable_with_caveats`：K2/K3 必须附加成立条件。
- C1–C4 通过（C5 仅登记、C6 可有条件通过）→ verdict = `stable`。
- C6 违反 → 在 K1 上附加输入不确定性区间，不改变 verdict（因噪声模型超出 asm-01 的确定性口径）。

## 3. 预注册方向预测（用于事后方向核验，不得修改）

| 扰动 | 预测方向 | 依据 |
|---|---|---|
| $E_0=E_{144}$ 4800 → 7200 | $Cost_{day}$ 单调**下降** | asm-02 偏差方向（终端留电越少，本日购电越多） |
| 往返效率 0.9（单侧 0.9487，效率提高） | $Cost_{day}$ **下降** | asm-04 偏差方向 |
| 电池侧计量（放电并网上限 $0.9P_{max}$，充电上限 $P_{max}/0.9$） | $Cost_{day}$ **上升**（可行域收缩） | asm-05 偏差方向 |
| 允许零收益反送 | $Cost_{day}$ **不变**（差值 $\le 10^{-6}$ 元） | asm-03：无上网电价时零收益反送与弃光目标等价 |
| $P_{max}$ 提高 | $Cost_{day}$ **不增** | 可行域单调扩张 |
| price 提高 / load 提高 / pv 提高 | $Cost_{day}$ **上升 / 上升 / 下降** | 目标与平衡式的单调性 |
| 无储能（$P_{max}=0$） | $Cost_{day}$ **上升** | K3 |

## 4. 情景矩阵（预注册）

统一设置：$dt=1/6$ h，$E_{min}=1200$、$E_{max}=10800$、$E_0=E_{144}=6000$、$P_{max}=5000$、
$\eta_{ch}=\eta_{dis}=0.90$（除显式覆盖），并网点侧计量，弃光上限 $pv_t\,dt$；每个情景同时求解
M1（MILP）与 M2（LP 松弛）以给出下界与退化诊断。

| 组 | 情景 | 覆盖 | 扰动 |
|---|---|---|---|
| A 结构/口径 | `A1_baseline` | 全部 | 基线（锚定 35126.94858928963） |
| | `A2_no_storage` | K3 | $P_{max}=0$（无储能参照） |
| | `A3_meter_battery_side` | asm-05 | 电池侧计量：充电上限 $P_{max}dt/\eta_{ch}$、放电上限 $P_{max}dt\cdot\eta_{dis}$ |
| | `A4_allow_zero_revenue_export` | asm-03 | 弃光/反送上限放宽为 $pv_t\,dt+P_{max}dt$，收益仍为 0 |
| | `A5_lp_relaxation` | K4/I1 | 基线 + M2（LP 真松弛）下界与退化诊断 |
| B 终端/边界 | `B1_E0_4800`、`B2_E0_7200` | asm-02 | $E_0=E_{144}\in\{4800,7200\}$ |
| | `B3_Emax_9600`、`B4_Emax_12000` | asm-08/边界贴界 | $E_{max}\in\{9600,12000\}$（12000 = $E_{cap}$，非运行上界，仅量化误用方向） |
| | `B5_Emin_1800` | asm-08 | $E_{min}=1800$ |
| C 效率 | `C1_roundtrip_0.90` | asm-04/alt-01 | $\eta_{ch}=\eta_{dis}=\sqrt{0.9}=0.9487$ |
| | `C2_eta_0.855`、`C3_eta_0.945` | asm-04 | 单向效率 $\pm5\%$ |
| | `C4_eta_0.81`、`C5_eta_0.99` | asm-04 | 单向效率 $\pm10\%$ |
| D 功率 | `D1_Pmax_-10%`、`D2_Pmax_-20%`、`D3_Pmax_+10%`、`D4_Pmax_+20%` | asm-05 | $P_{max}$ 缩放 |
| E 数据 ±5/10/20% | `E01..E18` | asm-01/07 | price / load / pv 各自 $\times(1\pm0.05,1\pm0.10,1\pm0.20)$ |
| F 组合压力 | `F1_price+20_load+20`、`F2_price-20_load+20`、`F3_pv-20_load+20`、`F4_pv+20_load-20`、`F5_price+20_pv+20_load-20` | 综合 | 多参数同向/反向应力 |
| G 时间口径 | `G1_cyclic_shift_1` | asm-12 | 三条曲线整体循环移位 1 个时段（10 分钟） |
| H 蒙特卡洛 | `H1_mc_noise_5pct` | 输入不确定性 | 200 次独立 $\pm5\%$ 均匀乘性噪声，seed = 20260101，记录每次 $Cost_{day}$、弃光与门禁 |
| I 一致性校验 | `I1_equivalence_check` | 实现一致性 | 广义构造器 vs 已接受 `build_model`/`evaluate_solution` 在 5 个对称口径情景上逐项比对 |

**原始与汇总分离**：逐情景原始记录写入 `raw/scenarios.jsonl`（含 milp/lp 状态、指标、残差、门禁），
蒙特卡洛逐次样本写入 `raw/monte_carlo_samples.csv`，关键情景轨迹写入 `raw/series/`；
汇总表、置信区间与判定写入 `summary.json` / `summary.csv` / `ci.json`；敏感性图写入 `figures/`。

## 5. 随机性与可复现

- 主模型确定性：不引入随机重启或随机抽样；求解器为 HiGHS 确定性分支定界，`seed` 仅登记。
- 蒙特卡洛（H1）是**超出 asm-01 确定性口径**的输入不确定性探针，仅用于给出 K1 的区间，
  不得替换主结论；噪声分布（i.i.d. 均匀 ±5%，乘性）与 200 次次数预注册；seed = 20260101。
- 求解配置沿用已接受 task：`--time-limit 300`、`--mip-gap 1e-4`、`scipy.optimize.milp`（HiGHS 1.18.1）。
- 输出目录：`problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness/`（隔离 task 独立输出目录）。

## 6. 执行与产物（后续动作按此执行）

1. **本动作**：写定本方案 + 扫描脚本 + task spec；经 `scripts/compute_dispatcher.py submit`
   提交隔离 task（stage = `robustness`，supervised worker，输出目录同上）；不在 Agent 内运行正式扫描、
   不等待 worker。
2. **下一次唤醒**：Runner 命中 `queued` 分支 `start_queued` 启动 supervised worker；worker 写出
   `raw/`、`summary.*`、`ci.json`、`figures/*.png`、`run_manifest.json`。
3. **聚合动作**（任务终态后的 robustness 唤醒）：
   - 复核 `summary.json` 的 C1–C6 判定与基线锚定；
   - 运行 `register_robustness_figures.py`（调用 `automm.visualization.register_figure` + `inspect_png`）
     登记敏感性图；
   - 写 `stability_conclusion.md`（稳定性结论、脆弱参数、方向核验、技术债移交）；
   - 经 `commands` 记录 `record_figure_review`（每张图）与
     `record_optional_stage(stage=robustness, decision=completed|skipped, reason=...)`，
     随后由 Runner 进入 Level 6 sanity（`sanity-checker`）。
   - 若 C1 失败 → 不记 completed，按 §2 判定规则路由。
4. **Level 6 sanity** 由 `sanity-checker` 执行，本阶段不自评。

## 7. 与上游技术债的对应

| 上游技术债（L1–L4 报告） | 本方案对应 |
|---|---|
| asm-02（$E_0=E_{144}=6000$）待对照 | B1/B2 + §3 方向预测 |
| asm-04（单向 90%）待对照 | C1–C5 |
| asm-05（并网点侧计量、833.33 kWh）待对照 | A3 + D1–D4 |
| $E$ 贴运行上下界需敏感性说明 | B1–B5（端点取值），并在结论中声明「贴界不等于设备余量」 |
| asm-12 标签口径需交付阶段登记 | G1 量化整体错位影响 |
| formulation §3.6 约束计数措辞、y 噪声 $-1.52\times10^{-15}$ | 与本阶段无关，维持上游技术债登记 |

## 8. 边界声明

- 本阶段不修改原始数据、假设版本、公式版本与既有结果目录；只在 `robustness/` 下新增产物。
- 不覆盖任何历史结果；隔离 task 使用独立输出目录，重跑必须新增 attempt。
- 敏感性结论只适用于附件 1 代表日（asm-07），不得外推全年；prob02~prob04 的电价/预测结构不同，
  须重新开轮。
