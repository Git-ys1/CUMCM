# prob01 实现计划（assumption_v001 / formulation_v001）

> 版本：`assumption_v001`（accepted）→ `formulations/formulation_v001`（accepted）。
> 上游：`formulations/formulation_v001/formulation.md`、`formula_validation.md`、`parameters.yaml`、`versions/assumption_v001/version.yaml`、`problems/CUMCM2026-C/global_symbols.yaml`。
> 本文件由 implementation-agent 在 `act-0831b08be2e14c5a` 写入；只填写当前 accepted 版本目录，未触碰旧版本、其他小问、题面与附件。
> **本阶段未运行竞赛实例的完整 MILP**：只做 compileall / Ruff / CLI `--help` / `--smoke` 小规模合成实例探针 / `make_task_spec` 干跑。

## 1. 范围与交付物

| 项 | 内容 |
|---|---|
| 实现对象 | formulation_v001 主模型 M1（确定性单日日前 MILP）与其辅助模型 M2（LP 松弛） |
| 输入 | `data/附件1.xlsx`（144 行右端点标签：电价 / 小区负载 / 光伏发电预测功率），附录 1 设备参数 |
| 输出目录 | `problems/CUMCM2026-C/prob01/versions/assumption_v001/results/prob01_m1_formulation_v001/`（隔离 task 独占，禁止两个 task 共用） |
| 交付文件 | `result1.xlsx`（计划购电量 + 充放电量两张表），其余为数值、门禁与追踪文件 |
| 完整计算入口 | 只能由 computation 阶段的 Runner/dispatcher 依据 `task_spec.yaml` 创建隔离 task，再由 supervised worker 异步运行 |

## 2. 代码与接口

- 代码路径：`versions/assumption_v001/code/prob01_solver.py`（单文件，Python 3.12，numpy/pandas/scipy/openpyxl）。
- CLI（`--help` 已验证）：

| 参数 | 默认值 | 含义 |
|---|---|---|
| `--data` | `data/附件1.xlsx` | 附件 1 路径（只读） |
| `--output` | 无（完整实例必填） | 输出目录，必须与 task spec 的 `output_directory` 一致 |
| `--mode` | `both` | `milp` = 仅 M1；`lp` = 仅 M2；`both` = 两个都跑（交付解仍只取 M1） |
| `--seed` | `20260101` | 随机种子；本模型确定性，仅登记与写入身份 |
| `--time-limit` | `300` | 求解时限（秒），`0` 表示不限 |
| `--mip-gap` | `1e-4` | HiGHS `mip_rel_gap` 目标 |
| `--smoke` | 关 | 只跑 T=6 合成实例的接口探针，不读取附件 1 |

- 运行环境变量（由 `scripts/task_worker.py` 注入）：`AUTOMM_TASK_ID`、`AUTOMM_OUTPUT_DIR`、`AUTOMM_SEED`、`PYTHONHASHSEED`；代码自身不读取这些变量，落盘位置完全由 `--output` 决定。

## 3. 模型到代码的映射

变量按块排布，每块长度 `T=144`：`q` → `C` → `D` → `E` → `curtail`（→ `y`，仅 M1）。

| 公式 | 代码实现 |
|---|---|
| (C1) 能量平衡 | 144 条等式：`q_t + D_t - C_t - curtail_t = (load_t - pv_t)·dt` |
| (C2) SOC 递推 | 144 条等式：`E_t - E_{t-1} - eta_ch·C_t + D_t/eta_dis = 0`（t=1 右端为 `E0`），并网点侧口径 |
| (C3) 储电量区间 | 变量上下界 `[Emin, Emax] = [1200, 10800]` |
| (C4) 终端条件 | 1 条等式 `E_144 = E0 = 6000` |
| (C5) 变流器上限 | 变量上下界 `[0, Pbar]`，`Pbar = Pmax·dt = 833.33` |
| (C6) 充放电互斥 | 288 条不等式 `C_t - Pbar·y_t ≤ 0`、`D_t + Pbar·y_t ≤ Pbar`，`y_t` 为 0-1（`integrality=1`） |
| (C7) 购电非负 | `q_t` 下界 0（无上界，外网可无限供电） |
| (C8) 弃光上界 | `curtail_t ∈ [0, pv_t·dt]` |
| (O) 目标 | `min Σ price_t·q_t`，其余变量目标系数为 0 |

规模（T=144）：M1 共 864 个变量（720 连续 + 144 个 0-1）、289 条等式、288 条不等式；M2 共 720 个变量、289 条等式、0 条不等式（去掉 (C6) 与 `y`）。
M2 是**真松弛**（整条互斥约束被删除，而不是把 `y` 松弛到 [0,1]），因此 `Cost_day(LP) ≤ Cost_day(MILP)` 必然成立，可作为下界与退化诊断；交付的 `C_t/D_t` 只能取 M1 解（formulation.md §4）。

## 4. 求解策略与参数（预先固定）

- 库：`scipy.optimize.milp`，HiGHS 后端；`scipy>=1.11`（本环境 1.18.1），不依赖 `pulp` 或任何外部求解器。
- 预检通过：`pulp` 未安装，代码不 import 它。
- 报告字段：`status / success / message / objective / best_bound / mip_gap / node_count / runtime_seconds / num_variables / num_equalities / num_inequalities / pbar_kwh / seed / feasible_incumbent / incumbent_found`。
- 非全局最优（status=1，有时限/Gap）：仍按可行 incumbent 交付，由 sanity 按 `PASS_WITH_WARNING` 处理并保留 best bound 与 gap；不得人工阻塞。
- 求解器不可用、进程异常 → worker 记 `code_runtime`，由恢复策略路由回 implementation 修复一次。

## 5. 硬门禁与指标（写到 `metrics.json`，对应 formulation.md §8）

- 残差：平衡 `≤1e-6`、SOC 递推 `≤1e-6`、储电量边界 `≤1e-6`、终端 `≤1e-6`、功率上限 `≤1e-6`、非负性 `≤1e-6`、互斥 `max_t min(C_t,D_t) ≤1e-9`、NaN/Inf 计数为 0。
- 指标：`Cost_day`（并检查落在 `[20622.7344, 48052.0466]`）、`Q_day`、弃光总量与发生时段、`E_0/E_144`、表 1 六个时段 `q_t`、表 2 六个 4 小时块充放电量。
- M1 vs M2 比较：`lp_le_milp`（必须为真）、`lp_strictly_better`（必须为假）、`lp_max_min_charge_discharge`（LP 原始解的互斥违反量，仅诊断）。

## 6. 交付映射（asm-12 / 歧义 A9）

- `result1.xlsx` 的 `计划购电量` 表：**按行序一一对应**（模板第 t 行 = 时段 t），并把标签重写为物理区间 `0:00-0:10 … 23:50-24:00`；禁止按模板字面标签逐行对齐。
- 论文表 1：`10:00-10:10→t=61`、`12:00-12:10→t=73`、`14:00-14:10→t=85`、`16:00-16:10→t=97`、`18:00-18:10→t=109`、`20:00-20:10→t=121`（代码内常量 `PAPER_TABLE1_PERIODS`）。
- `result1.xlsx` 的 `充放电量` 表：6 个 4 小时块（`RULE_TABLE2_BLOCKS`）的 `ΣC_t`、`ΣD_t`，以及 `0:00`/`24:00` 储电量；保持附件 5 模板的 5 列布局。

## 7. 复现身份（implementation 阶段干跑记录）

| 项 | 值 |
|---|---|
| 代码 | `problems/CUMCM2026-C/prob01/versions/assumption_v001/code/prob01_solver.py` |
| 代码 sha256 | `4c22a3049b103eb4187b667949dc71f4878337b983eee6a015e82d44c003abaa` |
| harness `code_hash`（相对路径+内容） | `c1679061e0725bada20187dc30c3da1d01290c8612f6b1a49963b30f4ca484af` |
| 输入 | `data/附件1.xlsx`，sha256 `66b87134f5ecccd68184d3539bb1293ef039f9e0fdd955a589b9bfa7f227c377` |
| 输入 `input_hash` | `9784ee20f4315a757806885b5795d01e08da414e6abe40dade3d76f7ff111903` |
| 配置 | `config/compute.yaml`，`source_config_hash` `9f076ef018b3f05c039d1ee56d978ab95c041bd7b425d353e0c16592abb8f0b4`，合并 `config_hash` `88a3d11012bf2ebe28404d8d55896db1b7ca0da0337e081978745eacfda5ed0b` |
| 种子 | `20260101` |
| 时限 / Gap | `300 s` / `1e-4` |
| 输出目录 | `problems/CUMCM2026-C/prob01/versions/assumption_v001/results/prob01_m1_formulation_v001` |
| 干跑预测 task_id | `13bf04ee604e54581fa2`（`make_task_spec` 未提交，`runtime/tasks/` 未新增目录） |
| task spec | `versions/assumption_v001/task_spec.yaml` |

> 任一身份字段变化（代码、配置、输入、版本、backend）都会改变 `task_id`；重跑必须使用新的 output_directory，不得覆盖旧 attempt 结果。

## 8. 静态检查与探针证据（本阶段实际执行）

| 检查 | 命令 | 结果 |
|---|---|---|
| 语法编译 | `.venv\Scripts\python.exe -m compileall -q .../code` | 通过（exit 0） |
| 静态检查 | `.venv\Scripts\ruff.exe check .../code` | `All checks passed!` |
| 接口 | `python .../prob01_solver.py --help` | 正常输出用法（未读取数据、未求解） |
| 小规模接口探针 | `python .../prob01_solver.py --smoke --output runtime/tmp/prob01_smoke` | MILP 与 LP 均 `status=0`、门禁全过、`min(C,D)=0`；约 3 秒；产出 `result1.xlsx/solution.csv/solution.json/metrics.json/smoke_report.json` |
| 输入只读核验 | `load_problem_data(data/附件1.xlsx)` | 144 行、列名与右端点标签全部通过；price∈[0.3713,1.3952]、load∈[3309.39,5958.97]、pv∈[0,7612.32] |
| 矩阵静态构造 | `build_model`（**不求解**，M1/M2 各一次） | M1: 864 变量 / 289 等式 / 288 不等式；M2: 720 / 289 / 0；`Pbar=833.3333`；`curtail` 上界最大 1268.7193 kWh |
| task spec 干跑 | `runtime/tmp/prob01_task_spec_probe.py`（`make_task_spec`，不 `submit`） | 预检 `compileall=passed, ruff=passed`；`command` 未被改写；task_id 见 §7；未创建 `runtime/tasks/` 记录 |
| 相对解释器路径 | `.venv/Scripts/python.exe -c "print(...)"`（cwd=项目根） | `relative-python-ok`，确认 task 命令首项可用 |

探针输出位于 `runtime/tmp/`，属可重建临时物，**不是**正式产物，不进入产物链。

## 9. 失败条件与恢复路由

| 失败 | worker/脚本表现 | 路由 |
|---|---|---|
| 输入结构、列名、行数、负值、NaN/Inf、标签口径不符 | 异常，退出码 2/非零 | `code_runtime` → implementation 修复一次；若属题面/附件问题再上报 |
| MILP 无可行 incumbent（status=2/3） | 退出码 3，`solver_status.json` 记 `incumbent_found=false` | `model_infeasible` → 建议回 mathematical_formulation，不直接人工阻塞 |
| 硬门禁违反或 NaN/Inf | 退出码 3，`metrics.json` 记具体残差 | `code_runtime`/`needs_revision`，禁止把违反约束的解交付 |
| 有时限内可行解但未证最优 | 退出码 0，`mip_gap/best_bound` 保留 | `PASS_WITH_WARNING`，保留技术债说明 |
| 求解器不可用 / 进程被杀 | worker 记 `failed/timed_out` | 按 `infrastructure_transient` 重试（新 attempt、新输出目录） |

## 10. 未闭合项（转 computation / sanity / robustness）

- `I3`：是否存在 `curtail_t ≡ 0` 的可行调度仍待实测；代码必须报告弃光总量与发生时段（`curtail_periods`）。
- `I2`：144 个 0-1 的 MILP 最优性证据（status / best bound / gap）待 computation 给出。
- M1 在真实实例上的 `max_t min(C_t,D_t)`、LP 下界与 MILP 目标差待 computation 报告。
- `asm-02/04/05` 的端点取值、往返效率与计量口径敏感性仍由 robustness 承担，本实现只固定并网点侧口径。
- 本实现的完整实例（T=144）求解**尚未执行**；其正确性由 computation 阶段的隔离 task 与后续 sanity 验收。

## 11. 结论

实现计划、代码与 task spec 已就绪并通过全部允许的静态检查与小规模探针；未运行完整数据集、未创建正式 task、未修改原始数据与上游产物。下一步由 computation 阶段依据 `task_spec.yaml` 创建隔离 task 并交给 supervised worker 异步求解。
