# prob01 Level 6 Sanity Report（鲁棒性与敏感性稳定性）

- 题目 / 小问：`CUMCM2026-C` / `prob01`（固定电价与负载下的单日计划购电模型）
- 假设版本 / 公式版本：`assumption_v001` / `formulation_v001`
- 被检阶段与权威产物：robustness，`problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness_v002/`
- 基线计算 task：`13bf04ee604e54581fa2`（L1–L4 已验收）；权威扫描 task：`66b12e7cd283813a098e`（attempt 1，succeeded，rc=0，supervised worker）
- 检查方：`sanity-checker`（独立于 robustness-analyst，不自评自签）
- 前置状态：`level_1_4 = PASS_WITH_WARNING`（6 项非阻断技术债，仍在案），`optional_stages.robustness = completed`
- **Level 6 判定：`PASS_WITH_WARNING`**；`failure_type = null`，`return_stage = null`，无失败路由
- 核心稳定性结论：**`verdict = fragile`**（按预注册 plan.md §2：C1、C2 通过、C3 违反 → fragile），必须在论文边界章节与交付阶段列出脆弱参数与幅度

---

## 1. 检查对象与追踪链（L1 复核）

| 项 | 值 | 复核结果 |
|---|---|---|
| 扫描 task 终态 | `66b12e7cd283813a098e`：status=succeeded、attempt=1、returncode=0、worker_mode=supervised | 通过 |
| 排除残留 | `robustness/`（attempt-001，`cd463874338e3f8a7f16`）失败残留，未被任何结论、图源或 hash 引用 | 通过 |
| `code_sha256` | `run_manifest` 记录 `416a6903…31ac207`，与磁盘 `prob01_robustness.py` 实测一致 | 通过 |
| 已接受实现 hash | `4c22a304…c003abaa`，与 `code/prob01_solver.py` 实测一致 | 通过 |
| 原始数据 hash | `66b87134…f227c377`，与 `data/附件1.xlsx` 实测一致（原始附件未被修改） | 通过 |
| 必需产物 | `summary.json/csv/md`、`ci.json`、`solver_status.json`、`run_manifest.json`、`raw/scenarios.jsonl`、`raw/monte_carlo_samples.csv`、`raw/equivalence_check.json` 全部存在且非空 | 通过 |
| 规模与配置 | 43 情景 ×（MILP+LP）+ 200 次蒙特卡洛，seed=20260101，time-limit 300 s、mip-gap 1e-4、HiGHS 1.18.1，实际 34.65 s | 通过 |

## 2. 独立复核方法（不复用被检 Agent 的验证脚本）

- 由 sanity-checker 另写只读探针 `runtime/tmp/prob01_level6_verify.py`，直接从 `raw/scenarios.jsonl`、`raw/monte_carlo_samples.csv` 与**原始附件 1**重算判据、锚定、方向与「同条件无储能」参照，**共 81 项检查，0 失败**（机器结果 `runtime/tmp/prob01_level6_verify.json`）。
- 「同条件无储能」费用用解析式 $Cost^{ns}=\sum_t p_t\max(L_t-PV_t,0)\,dt$ 独立重算：基线情景精确复现 `48052.046590846665` 元（与 task 的 A2 结果逐位一致），再按各情景 `scale` 缩放重算，未使用被检方给出的任何中间量。
- 图表 `source_hashes` 按项目约定 `sha256(项目相对路径 + 文件字节)` 重算逐项比对（含 `raw/series/` 三个轨迹文件）。
- 阈值来自 `plan.md`（预注册，未修改）与 `config/sanity_check.yaml`；本次不重跑 MILP、不修改模型/代码/数据/结果。

## 3. 预注册判据复核（C1–C6）

| 判据 | 阈值 | 记录值 | 独立重算 | 判定 |
|---|---|---|---|---|
| C1 数值合法性 | 全部情景通过 | 43/43 status=0、max mip_gap=0.0、43/43 硬门禁全过、NaN/Inf=0 | 一致；最坏残差：平衡 3.41e-12、SOC 2.73e-12、能量界 4.55e-13、终端/功率/反送上限/非负 0、互斥 1.57e-12 | **通过** |
| 基线锚定 | \|Δ\|≤1e-6 元 | 7.276e-12 元 | 7.275957614183426e-12 元 | **通过** |
| C2 口径稳定性 | ≤10% | 最坏 C1_roundtrip_0.90 = −3.773% | A3 −0.0723%、A4 0、B1 +0.0179%、B2 −0.0128%、C1 −3.7733% | **通过** |
| C3 参数包络 | ≤25% | 违反：`E_load_-20pct`、`E_load_+20pct` | −36.9162% / +44.9881% 复现；纳入被实现遗漏的 η 组后最大仍为 7.8609%，不改变结论 | **未通过** |
| C4(a) 无弃光占比 | ≥90% | 38/43 = 88.3721% | 一致；弃光>0 仅 5 情景（A2 无储能 6247.963、E_load_-20% 2166.796、E_pv_+20% 3258.395、F4/F5 各 11166.599 kWh） | **未通过** |
| C4(b) 全部 < 无储能参照 | — | 统一基线参照下 3 项超标 | 同口径复现 E_load_+20pct / F1 / F3 超标 | **未通过** |
| C4(c) 基线 M1−M2 | ≤1e-7 元 | 0.0 | 0.0，`lp_le_milp=true` | **通过** |
| C5 时间标签错位 | 仅登记 | Δ=−0.100 元（−2.847e-6） | 复现（G1 循环移位 1 个时段） | 已登记 |
| C6 蒙特卡洛 | 宽度≤15% 且均值偏差≤5% | 200/200 status=0、门禁失败 0、弃光为正 0 次；宽度 28.207% > 15%，均值偏差 0.047% ≤5% | 均值 35143.340414159444、std 2533.2422、分位 [30627.463, 40535.809]、宽度 28.2072%、偏差 0.0467%、噪声 ≤4.975% 全部复现 | **未通过（仅宽度）** |
| 方向核验 | — | 41/43 | 逐情景重算 observed_direction 与 pass 逻辑完全一致；不一致仅 A3、B3 | 一致 |

**独立复核的 post-hoc 口径结论（不改变 verdict）**：
- **K3 在同条件参照下成立**：除刻意构造的无储能参照 A2 外，42/42 情景 `Cost_day` 严格低于**同条件**无储能费用；最小节省 9266.177 元（F2）。被检报告的 62512.606 / 75015.127 / 70539.185 元（E_load_+20%、F1、F3）由独立解析式逐位复现。
- **C4(a) 由无储能参照驱动**：剔除刻意构造的 A2 后为 38/42 = 90.476% ≥ 90%；但**预注册口径 88.372% 仍应作为未通过如实登记**，不得回改阈值。
- **R2（C3 包络集合与 plan 文本不一致）确认存在但无实质影响**：η 场景最大 7.861% ≤ 25%。
- **R3（B3 方向预测缺陷）确认**：`not_up` 与「收紧上界 ⇒ 费用不降」的可行域单调性矛盾，属预注册登记错误。

## 4. 硬门禁与非阻断技术债

- **硬门禁全部通过**：关键假设来源齐全（asm-02/04/05 已由 B/C/A 组对照，asm-03/12 已量化登记，文献门禁沿用 L1–L4 已通过结论）；物理/经济常识通过（能量守恒闭合、储能节省方向正确、费用落在独立解析界内）；跨小问一致性属 Level 5，当前仅 prob01 局部完成、**不适用**。
- **无失败项、无需回退**：C1 无违反，故不路由 `mathematical_formulation`/`implementation`；C3/C4/C6 未通过属预注册判据下的稳定性事实与技术债，不足以判 `NEEDS_REVISION`。
- 技术债清单：
  - 上游 U1–U4（沿用 L1–L4）：y_binary −1.52e-15 噪声、formulation §3.6 约束计数措辞、asm-12 标签映射登记、asm-10/07/03 边界声明。
  - R1：C4(a)/C4(b) 口径问题仅在 `stability_conclusion.md §8` 作 post-hoc 解释，双记「预注册口径未通过 / 同口径复核通过」。
  - R2：C3 包络组实现未含 η 组，建议下一版本显式修正集合。
  - R3：B3 `not_up` 预注册方向登记缺陷。
  - R4：本环境响应模型不支持图像输入，6 张敏感性图采用与上游一致的程序化审计（passed），**不能替代人眼图意判断**，建议对有图像能力的终端补目检（全部 15 张 PNG）。
  - R5：可用内存约 1 GB、effective_workers=1，本次 34.65 s 未受影响；重跑/扩样按 `infrastructure_transient`/`code_runtime` 新 attempt。
  - **R6（本次新增）**：`robustness_v002/stability_conclusion.md` §10 图表表中 `prob01_fig_efficiency_metering_…` 的 stable_id 有 1 个字符笔误（写作 `6ec5b3f7fb`，权威值 `6ec5b3b7fb`，与 `figures.yaml`/`figures/robustness_*/…quality.json` 不符）；`figures.yaml` 登记本身正确，属文档级追踪笔误，**不构成产物链缺失**，交付阶段修正或加注即可。

## 5. 结论影响、状态与路由

- Level 6 状态：**`PASS_WITH_WARNING`**（有完整可行、可追溯结果，且 C1/锚定/方向核验通过；仅存在预注册判据下的敏感性事实与非阻断技术债）。
- 对结论的影响：K1/K4 与基线结构结论不受影响；K2 仅在正余电超过储能吸收能力时失效（5 情景）；K3 在同条件参照下仍成立；**load 是首要脆弱参数**，±20% 预测误差对应 `Cost_day ∈ [22159.431, 50929.885]` 元，需求侧 ±20% 误差下 25% 费用包络不成立——该表述须进入论文边界章节。
- 路由：`failure_type = null`、`return_stage = null`；本动作记录 Level 6 通过后，prob01 进入 `locally_completed`（ablation 以「结构性消融已由 robustness 情景矩阵覆盖」为由记录 skipped）。
- Level 5 跨小问一致性待 prob02–prob04 局部完成后由 `cross_question_review` 执行；asm-12 时间标签映射须在交付与论文中同步登记。

## 6. 未解决警告（移交交付与论文）

1. `fragile`：load ±20% / 组合压力 F1（+73.986%）、F3（+68.539%）须在论文边界量化。
2. C6 输入不确定性区间（200 次 ±5% 噪声：95% 分位宽度 +28.207%）仅作 K1 的区间附加，不替换确定性主结论。
3. C4(a)/C4(b) 口径须双记，不得回改预注册阈值。
4. 「贴界不等于设备余量」：E 贴运行上下界（10800/1200）是最优性质，E_max 收紧至 9600 kWh 使费用 +2.575%，运行上界是有效约束。
5. R4 人眼目检、R6 stable_id 笔误、U1–U4 上游技术债。
