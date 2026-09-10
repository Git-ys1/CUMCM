# prob02 实现计划（assumption_v001 / formulation_v001）

> 版本：`assumption_v001`（accepted）→ `formulations/formulation_v001`（accepted）。
> 上游：`formulations/formulation_v001/formulation.md`、`formula_validation.md`、`parameters.yaml`、`versions/assumption_v001/version.yaml`、`problems/CUMCM2026-C/global_symbols.yaml`。
> 本文件由 implementation-agent 在本次动作写入；只填写当前 accepted 版本目录，未触碰旧版本、其他小问、题面与附件。
> **本阶段未运行竞赛实例的任何优化**：只做 compileall / Ruff / CLI `--help` / `--smoke` 小规模合成实例探针 / 只读数据与矩阵静态构造探针 / `make_task_spec` 干跑。

## 1. 范围与交付物

| 项 | 内容 |
|---|---|
| 实现对象 | formulation_v001 主模型 M1（0:00 计划层逐日 MILP × 执行层闭式投影 (R)）与辅助模型 M2（去 (C6) 与 0-1 的真 LP 松弛） |
| 输入 | `data/附件1.xlsx`（144 时段电价，逐日相同）、`data/附件2.xlsx`（小区负载 + 光伏实际功率，365 天 × 144 时段）、`data/附件3.xlsx`（0:00 整点预报 1~24 小时）、`data/附件5/result2.xlsx`（交付模板，只读核验） |
| 输出目录 | `problems/CUMCM2026-C/prob02/versions/assumption_v001/results/prob02_m1_formulation_v001/`（隔离 task 独占，禁止两个 task 共用） |
| 交付文件 | `result2.xlsx`（计划购电量 + 充放电量 + 紧急购电量三张表），其余为数值、门禁与追踪文件 |
| 完整计算入口 | 只能由 computation 阶段的 Runner/dispatcher 依据 `task_spec.yaml` 创建隔离 task，再由 supervised worker 异步运行 |

## 2. 代码与接口

- 代码路径：`versions/assumption_v001/code/prob02_solver.py`（单文件，Python 3.11+，numpy/pandas/scipy/openpyxl）。
- CLI（`--help` 已验证）：

| 参数 | 默认值 | 含义 |
|---|---|---|
| `--price` | `data/附件1.xlsx` | 附件 1 电价曲线（只读） |
| `--load-pv` | `data/附件2.xlsx` | 附件 2「小区负载」「光伏发电实际功率」两个工作表（只读） |
| `--forecast` | `data/附件3.xlsx` | 附件 3 光伏预报；只取 `预报时刻=0:00` 子集（只读） |
| `--template` | `data/附件5/result2.xlsx` | 交付模板；只读核验三张表结构与规模 |
| `--output` | 无（完整实例必填） | 输出目录，必须与 task spec 的 `output_directory` 一致 |
| `--mode` | `both` | `milp` = 仅 M1；`lp` = 仅 M2；`both` = 两个都跑（交付解仍只取 M1） |
| `--seed` | `20260102` | 随机种子；本模型确定性，仅登记与写入身份 |
| `--time-limit` | `120` | **单日**求解时限（秒），`0` 表示不限 |
| `--total-budget` | `1500` | 全部日期的软总预算（秒）；超出后剩余日期用 `max(2, 剩余)` 秒求解，仍保证每天都被尝试 |
| `--mip-gap` | `1e-6` | HiGHS `mip_rel_gap`，**显式设定**（默认 1e-4 会把 gap 内可行解报为 `status=0`） |
| `--smoke` | 关 | 只跑 T=12、3 天的合成实例接口探针，不读取任何附件 |

- 运行环境变量（由 `scripts/task_worker.py` 注入）：`AUTOMM_TASK_ID`、`AUTOMM_OUTPUT_DIR`、`AUTOMM_SEED`、`PYTHONHASHSEED`；代码自身不读取这些变量，落盘位置完全由 `--output` 决定。
- 输出文件（全部写入 `--output`）：

| 文件 | 内容 |
|---|---|
| `solver_status.json` | 年度求解状态与 `feasible_incumbent`/`incumbent_found`（task_worker 判定可行解的依据） |
| `metrics.json` | 年度指标、硬门禁残差、4 个指定日期取值、M1 vs M2 比较与解析界登记 |
| `daily_metrics.csv` | 334 行逐日指标 + 逐日 solver status/best_bound/mip_gap/node_count/门禁 |
| `solution.csv` | 334×144 = 48 096 行逐时段 `price/load/pv/pvfc/q/C/D/E/kappa_plan/u/kappa_act/surplus/y`（utf-8-sig） |
| `emergency_segments.csv` | 按 asm-17 合并后的紧急购电连续时段（日期、起止时段、物理区间、购电量） |
| `result2.xlsx` | 交付三表 |
| `run_report.json` | milp/lp 模式汇总、M1 vs M2 比较、年度汇总 |
| `run_manifest.json` | 代码/输入 sha256、版本、种子、时限、gap、输出目录、Python/numpy/scipy/pandas 版本与交付映射 |

## 3. 模型到代码的映射

每日变量按块排布，每块长度 `T=144`：`q` → `C` → `D` → `E` → `kappa`（→ `y`，仅 M1）。

| 公式 | 代码实现 |
|---|---|
| (C1) 计划层平衡 | 144 条等式：`q_t + pvfc_t·dt + D_t − C_t − kappa_t = load_t·dt` |
| (C2) SOC 递推 | 144 条等式：`E_t − E_{t−1} − eta_ch·C_t + D_t/eta_dis = 0`（t=1 右端 `E0`），并网点侧口径 |
| (C3) 储电量区间 | 变量上下界 `[Emin, Emax] = [1200, 10800]` |
| (C4) 日循环边界 | 第 1 条 SOC 方程右端取 `E0`（即 `E_d,0=E0`）+ 1 条终端等式 `E_144 = E0 = 6000` |
| (C5) 功率上限 | 变量上下界 `[0, Pbar]`，`Pbar = Pmax·dt = 833.3̄` |
| (C6) 充放电互斥 | 288 条不等式 `C_t − Pbar·y_t ≤ 0`、`D_t + Pbar·y_t ≤ Pbar`，`y_t` 为 0-1（`integrality=1`） |
| (C7) 购电非负 | `q_t` 下界 0（无上界，外网可无限供电） |
| (C8) 计划弃光上界 | `kappa_t ∈ [0, pvfc_t·dt]` |
| (O) 计划层目标 | `min Σ price_t·q_t`，其余变量目标系数为 0 |
| (E) 预报展开 | `pvfc_t = pvfc_{d,0,ceil(t/6)}`，即 `values24[(t−1)//6]` |
| (R1)~(R3) 执行层投影 | `s_t = kappa*_t + (pv_t − pvfc_t)·dt`；`u_t = max(0, −s_t)`；`kappa_act_t = max(0, s_t)`；**不得**把计划层 `kappa*` 代入缺口式 |

规模（T=144，逐日）：M1 共 **864 个变量**（720 连续 + 144 个 0-1）、**289 条等式**（平衡 144 + 递推 144 + 终端 1）、**288 条不等式**（(C6)）；M2 共 **720 个变量、289 条等式、0 条不等式**。
M2 是**真松弛**（整条 (C6) 与 `y` 一并删除，而不是把 `y` 放宽到 [0,1]），因此逐日 `Cost_plan(LP) ≤ Cost_plan(MILP)` 必然成立，可作下界与退化诊断；交付的 `C_t/D_t` 只能取 M1 解（formulation.md §3.4）。
实现口径说明：代码中 (C3)(C5)(C8) 以变量界实现、(C6) 以不等式实现，与 prob01 的实现口径一致。

## 4. 求解策略与参数（预先固定）

- 库：`scipy.optimize.milp`，HiGHS 后端；`scipy>=1.11`（本环境 1.18.1），不依赖 `pulp` 或任何外部求解器。
- 逐日独立求解 334 次（日循环 (C4) 使各日解耦；全年最优 = 逐日最优之和），每次显式传入 `mip_rel_gap=1e-6`。
- 报告字段：逐日 `status / message / objective / best_bound / mip_gap / node_count / runtime_seconds / num_variables / num_equalities / num_inequalities`；任务级另记 `days_optimal / days_feasible_not_optimal / days_failed / max_mip_gap / total_runtime_seconds` 与 `pbar_kwh / big_m / seed / mip_rel_gap / 时限 / 总预算`。
- 非全局最优（`status=1`，时限或 gap 未闭合）：仍按可行 incumbent 交付，由 sanity 按 `PASS_WITH_WARNING` 处理并保留 best bound 与 gap；不得人工阻塞（`I2`）。
- 求解器不可用、进程异常 → worker 记 `code_runtime`，由恢复策略路由回 implementation 修复一次。

## 5. 硬门禁与指标（写入 `metrics.json`，对应 formulation.md §8）

- 计划层平衡 `≤1e-6`；执行层平衡 `≤1e-6`；SOC 递推 `≤1e-6`；终端残差 `≤1e-6`；储电量越界与功率越界 `=0`；
- 互斥 `max_t min(C_t,D_t) ≤ 1e-9`；执行层互补性 `max_t u_t·kappa_act_t ≤ 1e-9`；非负性 `≥ −1e-9`；
- `kappa_t ≤ pvfc_t·dt`、`kappa_act_t ≤ pv_t·dt` 越界计数为 0；0-1 整数性偏差 `≤1e-9`（求解器噪声在报告前把 `|y|<1e-9` 归零、`|y−1|<1e-9` 归一，避免 prob01 的 U1 类 −1.5e-15 噪声）；NaN/Inf 计数为 0；原始数据未被修改。
- 指标：`Cost_plan`（须落在解析界 `[6 749 147.6122, 16 565 407.2763]` 元）、`Cost_em`（`≤5 815 010.6013` 元）、`Cost_total`（`≥6 660 821.0595` 元）、`Q_plan`（`≥18 177 074.097` kWh）、弃光两层总量与发生时段、紧急购电总量/次数/段数与 `u=0` 天数、`E_0/E_144`、表 1 六个时段 `q_t`、表 2 六个 4 小时块充放电量。
- M1 vs M2：`lp_le_milp`（必须为真）、`lp_strictly_better_days`（必须为 0）、`lp_max_min_charge_discharge`（LP 原始解互斥违反量，仅诊断）。
- 解析界门禁仅在完整竞赛实例（334×144）上启用；`--smoke` 合成实例不适用解析界，只校验结构门禁。

## 6. 交付映射（asm-15 / asm-17）

- `result2.xlsx`「计划购电量」：第 d 行（2025-02-01 起 334 行）× 第 t 列 = `q*_{d,t}`；**按列序一一对应**（模板第 t 列 = 时段 t），时间标签统一重写为物理区间 `0:00-0:10 … 23:50-24:00`（模板原标签整体后移一个间隔且含字面笔误 `7:0-7:10`，禁止按标签字面逐行对齐）；末两列 `全天购电量 = Q_plan_d`、`全天购电费 = Cost_plan_d`（计划口径，与 asm-04 门禁一致；`Cost_total` 单列于 `metrics.json` 与 `run_report.json`）。
- 「充放电量」：每日 7 行 —— 6 个 4 小时块（`0:00-4:00`…`20:00-24:00`）填 `ΣC*`、`ΣD*`；第 1 行 `时刻=00:00` 填 `E_d,0`，第 2 行 `时刻=24:00` 填 `E_d,144`（保持模板 6 列布局）。
- 「紧急购电量」：按 asm-17 逐 10 分钟判定、合并同一日内连续时段；`|u|<1e-9` 归零；按实际段数增删行，日期列只在首段出现；**`u=0` 的日期显式登记为一行（时间段「无」、购电量 0）**，不因模板每日 3 行的示例而丢段。
- 论文表 1 的 6 个指定时段常量固定为 `t=61/73/85/97/109/121`（`PAPER_TABLE1_PERIODS`），表 2 的 6 个 4 小时块见 `RULE_TABLE2_BLOCKS`；4 个指定日期见 `KEY_DATES`。
- 数值位数固定：电量 3 位小数、费用 2 位小数（`DELIVERY_ROUNDING`），全表一致；`solution.csv` 保留 10 位有效数字供 sanity 独立回代。

## 7. 复现身份（implementation 阶段干跑记录）

| 项 | 值 |
|---|---|
| 代码 | `problems/CUMCM2026-C/prob02/versions/assumption_v001/code/prob02_solver.py` |
| 代码大小 / sha256 | 55 064 字节 / `b2e85d61d01a6e8d3abb66827585e55ed31745bbec1725ca6951ac4e72549bb0` |
| harness `code_hash`（相对路径+内容） | `16a4effa5b47bbecd795edd5ab48bf28daaaf0e75399a7b385c1c440145934d9` |
| 输入 | `data/`（目录）作为 `input_path`；`附件1.xlsx` `66b87134…c377`、`附件2.xlsx` `2e95fd44…4c72`、`附件3.xlsx` `8a61b06c…d843`、`附件5/result2.xlsx` `1c26494c…1a47` |
| 输入 `input_hash` | `4343d799b5830093d7a61d566219e1d2592f5bc39c8b7a9297286fa9e02d9434` |
| 配置 | `config/compute.yaml`，`source_config_hash` `9f076ef018b3f05c039d1ee56d978ab95c041bd7b425d353e0c16592abb8f0b4`，合并 `config_hash` `88a3d11012bf2ebe28404d8d55896db1b7ca0da0337e081978745eacfda5ed0b` |
| 种子 | `20260102` |
| 时限 / Gap / 总预算 | 单日 `120 s` / `1e-6` / `1500 s`（worker `timeout_seconds=3600`） |
| 输出目录 | `problems/CUMCM2026-C/prob02/versions/assumption_v001/results/prob02_m1_formulation_v001` |
| 干跑预测 task_id | `ea71568e2cf6c5326ded`（`make_task_spec` 未提交，`runtime/tasks/` 未新增目录） |
| task spec | `versions/assumption_v001/task_spec.yaml` |

> 任一身份字段变化（代码、配置、输入、版本、backend）都会改变 `task_id`；重跑必须使用新的 output_directory，不得覆盖旧 attempt 结果。
> `input_path` 取 `data/` 目录而非单文件，是为了让 `input_hash` 覆盖本问的全部 4 个输入文件（`hash_path` 对目录递归哈希）。

## 8. 静态检查与探针证据（本阶段实际执行）

| 检查 | 命令 | 结果 |
|---|---|---|
| 语法编译 | `.venv\Scripts\python.exe -m compileall -q "problems\CUMCM2026-C\prob02\versions\assumption_v001\code"` | 通过（exit 0） |
| 静态检查 | `.venv\Scripts\ruff.exe check "…/code"` | `All checks passed!`（exit 0） |
| 接口 | `python …/prob02_solver.py --help` | 正常输出用法（未读取数据、未求解） |
| 小规模接口探针 | `python …/prob02_solver.py --smoke --output runtime/tmp/prob02_smoke` | T=12、3 天；MILP 与 LP 均 `status=0`、`mip_gap=0`、门禁全过、返回码 0；产出 `result2.xlsx/solution.csv/daily_metrics.csv/metrics.json/...` |
| 数据/矩阵只读探针 | `runtime/tmp/prob02_implementation_probe.py` | 见下 |
| task spec 干跑 | `runtime/tmp/prob02_task_spec_probe.py`（`make_task_spec`，不 `submit`） | 预检 `compileall=passed, ruff=passed`；`command` 未被改写；task_id 见 §7；未创建 `runtime/tasks/` 记录 |

只读数据/矩阵探针的关键证据（`runtime/tmp/prob02_implementation_probe.json`）：

- 模型规模：M1 `864 变量（144 个 0-1）/ 289 等式 / 288 不等式`，M2 `720 / 289 / 0`，`Pbar = big_m = 833.3333`；与 formulation §3.6 及 §3.4 的紧 big-M 结论一致。
- 附件 1 电价 `144` 行，`min=0.3713`（t=34）、`max=1.3952`（t=124），与 parameters.yaml 一致。
- 附件 2 共 `365` 天，交付窗口 `334` 天（2025-02-01~2025-12-31）；附件 3 的 `0:00` 报表覆盖全部 334 天；附件 5 三张表结构为 `计划购电量 334×147`、`充放电量`/`紧急购电量` 列名与模板一致。
- 4 个指定日期的数据事实与 formulation.md §7 校准值一致（最大绝对偏差 `5.0e-4` kWh，属显示位数差异）：`2025-03-20` 预报缺口 6 059.487（36 段）、`2025-06-21` 3 812.266（49 段）、`2025-09-23` 3 500.289（31 段）、`2025-12-21` 2 272.067（33 段）。
- 年度数据事实：`Σ(load−pvfc)dt = 18 177 074.09705` kWh、`Σ(load−pv)dt = 17 939 189.49497` kWh，不可避免弃光时段数 预报口径 `272` / 实际口径 `241`；与 formulation §1/§7 完全一致。
- 执行层投影 (R) 的 500 组随机可行组合（构造满足 (C1)）：执行层平衡残差 `≤1.14e-12` kWh、互补性违反 `0`、`u<0` 或 `kappa_act<0` 为 `0`。

探针输出位于 `runtime/tmp/`，属可重建临时物，**不是**正式产物，不进入产物链。

## 9. 失败条件与恢复路由

| 失败 | worker/脚本表现 | 路由 |
|---|---|---|
| 附件结构、列名、行数、负值、NaN/Inf、标签口径、模板规模不符 | 异常，退出码 2/非零 | `code_runtime` → implementation 修复一次；若属题面/附件问题再上报 |
| 任一日 MILP 无可行 incumbent（status=2/3） | 退出码 3，`solver_status.json` 记 `days_failed>0` / `incumbent_found=false` | `model_infeasible` → 建议回 mathematical_formulation，不直接人工阻塞 |
| 硬门禁违反、解析界越界或 NaN/Inf | 退出码 3，`metrics.json` 记具体残差 | `code_runtime`/`needs_revision`，禁止把违反约束的解交付 |
| 有时限内可行解但未证最优 | 退出码 0，`mip_gap/best_bound` 保留 | `PASS_WITH_WARNING`，保留技术债说明 |
| 求解器不可用 / 进程被杀 / 超过 3600 s | worker 记 `failed/timed_out` | 按 `infrastructure_transient` 重试（新 attempt、新输出目录） |

## 10. 未闭合项（转 computation / sanity / robustness）

- `I1`：逐日紧急购电总量、发生时段与次数、4 个指定日期的表 3 逐段结果待 computation 报告；`u=0` 的日期必须显式登记为 0。
- `I2`：334 个含 144 个 0-1 的 MILP 的逐日 `status / best_bound / mip_gap` 与年度汇总待 computation 给出；若超时或 gap 缺失按 `PASS_WITH_WARNING`。
- `I4`：执行层实际弃光 `kappa_act` 的总量与发生时段（不可避免弃光至少 241 个时段）待 computation 报告。
- `I5`：预报展开式 (E) 已固定并在实现中按 `(t−1)//6` 展开，computation 仍须以数据检验同日对齐。
- M2 的 LP 下界与 MILP 目标差、LP 原始解 `max min(C,D)` 待 computation 报告（本阶段只证明 LP 必须作为诊断、不得作为交付解）。
- `asm-06/09` 等 project_assumption 的端点、效率与计量口径敏感性仍由 robustness 承担，本实现只固定主口径。
- 本实现的完整实例（334×144）求解**尚未执行**；其正确性由 computation 阶段的隔离 task 与后续 sanity 验收。

## 11. 结论

实现计划、代码与 task spec 已就绪并通过全部允许的静态检查与小规模探针；未运行完整数据集、未创建正式 task、未修改原始数据与上游产物。下一步由 computation 阶段依据 `task_spec.yaml` 创建隔离 task 并交给 supervised worker 异步求解。
