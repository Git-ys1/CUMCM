# Sanity Check Report

- problem_id: CUMCM2026-C
- question_id: prob01
- assumption_version: assumption_v001
- formulation_version: formulation_v001
- task_id: 13bf04ee604e54581fa2（attempt 1，status=succeeded，returncode=0）
- output_directory: problems/CUMCM2026-C/prob01/versions/assumption_v001/results/prob01_m1_formulation_v001
- overall: PASS_WITH_WARNING
- checked_at: 2026-09-10T11:35Z
- checker: sanity-checker（action act-f74a5dcd7f9f4d77）
- 自动检查：`scripts/run_sanity_check.py`（machine_sanity.json，failures=0）；本报告补充的 L2-模型约束、L3、L4 由 sanity-checker 独立复核。

本报告检查对象是 computation 阶段隔离 task 的终态交付（M1 主模型 MILP 解 + result1.xlsx 交付表）。L5 跨小问一致性与 L6 鲁棒性按流程留待后续动作，不构成本次结论。

## Level 1：文件和运行完整性 — PASS

| 检查项 | 方法 | 阈值/期望 | 实际 | 判定 |
|---|---|---|---|---|
| task 终态 | 读 `runtime/tasks/13bf04ee604e54581fa2/status.json` | status=succeeded | succeeded，returncode=0，finished_at=2026-09-10T11:20:20Z | 通过 |
| worker 启动证据 | status.json | pid/create_time 存在 | pid=14312，worker_create_time=1789039218.458313 | 通过 |
| stdout/stderr | 文件存在且可追溯 | 存在 | stdout 3001 B；stderr 0 B（正常无错误输出） | 通过 |
| 必需产物 | 逐项列目录 | 非空 | metrics.json 2002 B、solver_status.json 528 B、run_report.json 2999 B、run_manifest.json 786 B、solution.csv 13856 B、solution.json 15112 B、result1.xlsx 8409 B | 通过 |
| 代码 hash | `hash_path(code)` 与 task.json 比对 | 相等 | c1679061…4af 一致 | 通过 |
| 输入 hash | `hash_path(data/附件1.xlsx)` 与 task.json 比对 | 相等 | 9784ee20…903 一致 | 通过 |
| 配置 hash | `hash_json(effective_config)` 与 task.json 比对 | 相等 | 88a3d110…d0b 一致 | 通过 |
| 交付自报 hash | run_manifest code_sha256/data_sha256 与文件裸 sha256 比对 | 相等 | 4c22a304…baa、66b87134…377 一致 | 通过 |
| 原始数据未被修改 | `data/附件1.xlsx` 与 `request/attachments/附件1.xlsx` 逐字节比对 | 相同 | 两者 sha256 均为 66b87134…377 | 通过 |
| 随机种子 | task.json / solver_status.json / run_manifest.json | 一致 | 三处均为 20260101 | 通过 |

补充说明（避免误判）：task.json 的 `code_hash`/`input_hash`（`hash_path`＝相对路径字节 + 文件字节的 sha256）与 run_manifest 的 `code_sha256`/`data_sha256`（仅文件字节的 sha256）定义不同，数值本就不等；两者均已按各自定义独立重算并一致，追踪链完整。

## Level 2：数值范围和约束 — PASS

方法：从交付的 `solution.csv` 逐时段回代 (C1)~(C8)，并与 `metrics.json`、`solver_status.json` 独立对账。

| 检查项 | 阈值 | 实际（独立复算） | 判定 |
|---|---|---|---|
| NaN/Inf | 0 | 0（6 个数值文件全部有限） | 通过 |
| 功率平衡最大残差 | ≤1e-6 | 2.27e-13 | 通过 |
| SOC 递推最大残差 | ≤1e-6 | 1.82e-12（CSV 往返约一个 ULP；solver 内存值 9.09e-13） | 通过 |
| 终端残差 \|E_144−E_0\| | ≤1e-6 | 0.0（E_0=E_144=6000.0） | 通过 |
| 充放电互斥 max min(C_t,D_t) | ≤1e-9 | 0.0 | 通过 |
| 变流器上限违反 max(C_t,D_t)−833.33… | ≤1e-6 | 0.0（C_max=833.3333，D_max=715.6530） | 通过 |
| 储电量边界 1200≤E≤10800 | 违反 0 | 违反 0（E_max=10800.0，E_min=1200.0，贴界不越界） | 通过 |
| 非负性 min(q,C,D,curtail) | ≥−1e-9 | 0.0 | 通过 |
| Cost_day 落在解析界内 | [20622.7344, 48052.0466] | 35126.9486；独立重算下界 20622.7344、上界 48052.0466 | 通过 |
| 交付指标复算一致 | 与 metrics.json 相同 | cost/q/curtail/charge/discharge 差均为 0.0；表 1、表 2 逐项一致 | 通过 |

结论性事实（回答 `I2`、`I3`）：

- `I2` 已证实：solver status=0（HiGHS "Optimal"），objective=best_bound=35126.94858928963，mip_gap=0.0，node_count=1（根节点 LP 松弛即整性），无求解质量技术债。
- `I3` 已证实：`curtail_total=0.0`，无任何时段弃光 >1e-9；附件 1 全天 6247.963 kWh 正余电全部被储能吸收。
- M1 vs M2：LP 松弛目标 = MILP 目标 = 35126.948589289634，`lp_strictly_better=false`，LP 原始解 `max min(C_t,D_t)=0.0`；真实 144 时段实例同样未出现 LP 严格更优，与 formulation §4 的条件性分析一致（主模型仍保留 0-1）。
- 能量恒等式闭合：ΣD = η_ch·η_dis·ΣC（残差 3.64e-12），Σq = 净缺额 55541.9724 + 0.19·ΣC + 弃光。

## Level 3：量纲和公式 — PASS

| 检查项 | 依据 | 证据 | 判定 |
|---|---|---|---|
| 目标量纲 | 元/kWh × kWh = 元 | (O) 实现为 `np.dot(price, q)`，与求解器 objective 一致 | 通过 |
| (C1) 量纲 | kW×h→kWh | q + pv·dt + D − C − curtail = load·dt，代码逐项系数正确 | 通过 |
| (C2) 量纲与效率口径 | 并网点侧 | `E_t = E_{t-1} + 0.9·C_t − D_t/0.9`，实现与 asm-04/asm-05 一致，未混用电池侧口径 | 通过 |
| (C5)/(C6) big-M | M 必须由上下界导出 | M = Pbar = Pmax·dt = 833.3333，与 (C5) 紧贴；`solver_status.pbar_kwh=833.3333` | 通过 |
| (C3)(C4)(C7)(C8) | 附录 1 / asm | 边界 1200/10800、E_144=E_0=6000、q≥0、0≤curtail≤pv·dt 全部实现且回代通过 | 通过 |
| 实现与 formulation 一致性 | 语义逐条比对 | `prob01_solver.py` 的 (C1)~(C8)、目标、交付映射与 formulation_v001 逐条对应；无遗漏或新增约束 | 通过 |
| 边界/极限行为 | 手算退化 | Pbar→0 退化为「只购电+弃光」，其上界恰等于 formulation §7 手工可行解成本 48052.0466 元；price≥0 时无套利动机异常 | 通过 |
| 交付映射 | asm-12 / A9 | result1.xlsx「计划购电量」144 行、标签为物理区间 0:00-0:10…23:50-24:00、数值与 solution q 逐行一致；表 1 取 t=61/73/85/97/109/121 与 solution.csv 同行；「充放电量」6 块与 table2_blocks 一致，E_0/E_144 按模板「时刻」列放在第 1/2 行 | 通过 |

## Level 4：常识与文献合理性 — PASS

- 文献支持：formulation/parameters 引用的 8 个引用 ID（silva-2020、garifi-2020、fortuny-1981、grimaldi-2024、luo-2015、modu-2025、palma-2013、ieee1547-2018）在 `prob01/shared/literature.md` 与 `CUMCM2026-C/citations.yaml` 中均存在且 `verified=true / status=used`，未出现引用不支持或缺失的定量主张。
- 经济方向（常识）：充电加权均价 0.4930 元/kWh、放电加权均价 1.1376 元/kWh；55.4% 的充电量落在最低价格四分位、64.1% 的放电量落在最高价格四分位；折算往返效率 0.81 后放电侧毛利差 ≈0.529 元/kWh。方向与量级符合「低谷充电、高峰放电」的套利机理。
- 数量级：全天购电费由无储能基线 48052.05 元降至 35126.95 元（−12925.10 元，−26.90%）；在电价极差 0.3713~1.3952 元/kWh（3.76 倍）与 5 MW/10.8 MWh 储能的场景下量级合理，未见 10~1000 倍异常。
- 物理边界：E 全程处于 1200~10800 kWh，充放电速率不超过 833.33 kWh/10min（=5000 kW），与附录 1 设备参数自洽。
- 已知边界（属 project_assumption，非本次缺陷）：asm-10 不计电池退化会高估频繁充放电经济性、使 Cost_day 偏低；asm-07 仅代表日、不外推全年；asm-03 不反送、无上网电价。三条均需在论文边界章节声明，并在 robustness 阶段做对照。

## 通过项与失败项汇总

- 通过：L1 全部 10 项；L2 全部 10 项（含 I2/I3 证实）；L3 全部 8 项；L4 全部 5 类。
- 失败（硬门禁）：无。未发现 NaN/Inf、硬约束违反、量纲错误、formulation 与实现语义不一致、原始数据被修改或追踪链缺失。

## 状态与失败分类

- L1-L4：**PASS_WITH_WARNING**（硬门禁全过；存在下列非阻断技术债）。
- failure_type：null（无需回退）。
- return_to_stage：null。

## 未解决警告（不影响推进，须登记并转交后续阶段）

1. 交付文件 `solution.csv` / `solution.json` 的 `y_binary` 列有一个取值为 −1.52e-15（其余为精确 0/1，整数性最大偏差 7.5e-15）。这是求解器数值噪声，不违反 y≥0，不影响任何指标；建议交付阶段把 |y|<1e-9 归零后再入论文/结果表。
2. `formulation.md` §3.6 写「等式约束 288 条，不等式约束约 720 条」，而实现报告为 289 等式（288 + 终端 E_144）/288 不等式（每时段 2 条 big-M）。模型语义逐条一致，仅文档计数不准；建议下一版本修正文字，不构成 formulation/实现不一致。
3. 关键假设 asm-02（E_0=E_144=6000）、asm-04（单向 90%）/asm-05（并网点侧、833.33 kWh）仍为 project_assumption，缺少同设备实测来源。必须在 robustness 阶段完成对照：E_0∈{4800, 6000, 7200}、往返效率 0.9（单侧 0.9487）与电池侧计量口径，并报告 Cost_day 变化方向与幅度。
4. asm-12 的时间标签重写与附件 5 模板字面标签（整体偏移一个时段）不一致，属有意统一；交付阶段若改回模板原标签，必须在论文与 result1.xlsx 中同步记录映射关系。
5. 弃光=0 使 E 同时贴到 1200 与 10800 两个边界（E=10800 出现在 t=34,35,87,91~108；E=1200 出现在 t=124~131），说明最优解由运行边界强约束；robustness 应报告端点取值对 Cost_day 的敏感性，避免把「贴界」误读为设备可行性的余量。

## 对结论的影响

本次交付可作为 prob01 的有效基线：M1 在真实 144 时段实例上取得可证全局最优（gap=0），全部硬门禁通过，数据、代码、配置、输入与随机种子可追溯，result1.xlsx 交付口径符合 asm-12。上述警告均为文档性/口径性或待 robustness 证实的项目假设，不改变 `Cost_day=35126.948589289634 元`、`Q_day=59482.69899835391 kWh`、`curtail=0`、`E_0=E_144=6000` 这组主结果。

## 修订或拒绝建议

- 不修订、不拒绝：不存在 `NEEDS_REVISION` 或 `VERSION_REJECTED` 项。
- 建议（非阻断）：交付阶段对 `y_binary` 做 1e-9 归零；下一公式版本修正 §3.6 的约束计数措辞；robustness 阶段按警告 3/5 完成对照实验。

## 路由

- failure_type: null
- return_to_stage: null
- blocking_reasons: 无
- warnings: 见「未解决警告」1~5
- 建议后续阶段：visualization（L1-L4 通过，可进入可视化）；随后 robustness → Level 6 sanity。

## sanity_check 阶段确认（action act-3641635a81184e38）

- 本动作在 `sanity_check` 阶段对上述 L1-L4 结论做独立只读复核（`runtime/tmp/prob01_stage_sanity_probe.py`），未重跑优化、未创建计算 task、未修改模型/代码/数据与任何上游版本。
- 数据完整性：`data/附件1.xlsx` 与 `request/attachments/附件1.xlsx` 的 sha256 均为 `66b87134…c377`，逐字节一致，原始数据未被修改。
- task `13bf04ee604e54581fa2`：status=succeeded、returncode=0、consumed=true；`run_manifest.json` 的 `code_sha256`/`data_sha256` 与文件裸 sha256 一致。
- 交付指标独立复算：cost_day=35126.948589289634 元、q_day=59482.69899835391 kWh、curtail_total=0.0，与 `metrics.json` 完全一致；落在解析界 [20622.7344, 48052.0466] 内。
- 硬约束回代（直接由 `solution.csv`）：平衡残差 2.27e-13、SOC 递推残差 2.56e-12、终端残差 0.0、互斥违反 0.0、功率上限/储电量边界/非负性违反均为 0.0、NaN/Inf 计数 0；`price/load/pv` 三列与附件 1 逐值相等。
- `result1.xlsx`：`计划购电量` 为 145×2（1 行表头 + 144 数据行），标签 `0:00-0:10 … 23:50-24:00`，数值与 `solution.csv` 的 `q_kwh` 逐行一致；`充放电量` 六块标签与数值均与 `table2_blocks` 一致，E_0/E_144 置于末两列首两行。
- `y_binary`：min=−1.52e-15，不存在 |y| 既非 0 也非 1 的点（容差 1e-9），与「未解决警告 1」一致，不影响任何指标。
- 口径澄清（避免误判）：`task.json` 的 `code_hash`（`hash_path`＝相对路径字节 + 文件字节）与代码文件裸 sha256 数值本就不等，属两套 hash 定义差异，非不一致；其后者的佐证是 `run_manifest.code_sha256` 与文件裸 sha256 一致。
- 结论：L1-L4 维持 **PASS_WITH_WARNING**，无新增失败项、无失败类型、无需回退；按流程迁移至 `visualization`。

