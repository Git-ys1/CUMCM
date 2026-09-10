# prob02 建模假设（assumption_v001）

> 小问：`prob02`（问题 2，每天电价相同、负载与光伏逐日逐时段变化，0:00 制定当日计划购电策略，供电不足按 5 倍电价紧急购电）。
> 上游：`prob02/shared/problem_understanding.md`、`prob02/shared/literature.md`、`prob02/shared/literature_pool.yaml`、`global_symbols.yaml`、`dependency_graph.yaml`。
> 机器可读记录：`version.yaml`（本文件是其人类可读展开）。
> 本版本状态：**candidate → 请求 ACCEPT**（只填写 Runner 已创建的本版本目录，不覆盖任何旧版本、题面、附件与其他小问产物）。

## 0. 结论摘要

- 共登记 **17 条假设**（关键假设 10 条，非关键假设 7 条），另登记 **7 条被否决的备选路线**（保留为 robustness/ablation 对照）。
- **A3（0:00 计划的信息集）是本问的模型性质核心**：本版本固定为「当日负载已知（附件 2）+ 当日 0:00 发布的光伏预报（附件 3）→ 实际由附件 2 实现」的两阶段口径。完全信息口径（alt-01）与典型日预测口径（alt-02）已登记为对照，其中**完全信息口径下紧急购电恒为 0**，故不作为主模型。
- **A2（跨日储能边界）** 取**日循环** `E_{d,0} = E_{d,144} = 6000 kWh`（问题 1 的两端相同约定的逐日版本，配合表 2 逐日交付两端储电量），使 334 天逐日解耦、与 prob01 同量级的 144 时段 MILP 可解；连续跨日口径（alt-03）保留为对照。
- 关键假设全部绑定本问文献池中 **verified 且 used** 的来源；门禁 `check_key_assumptions` 已实测通过（`passed: true`）。文献只支撑**结构**（两阶段、偏差结算、日循环边界、SOC/效率建模地位），**取值与口径**（6000 kWh、5 倍、833.33 kWh、并网点侧计量、0:00 预报口径）一律标为 `project_assumption`/`problem_statement`。
- **无阻塞性冲突**（`blocking: []`）；必须成对使用的只有 asm-02×asm-07 与 asm-03×asm-04 两组，formulation 必须写明。
- 建议 formulation 方向：**两阶段「计划—执行—补救」MILP**——第一阶段用（当日负载 + 0:00 光伏预报）求 144 时段计划（目标 `min Σ_t price_t·q_dt`，含互斥与日循环）；第二阶段按实际负载/光伏执行计划，缺口 `u_dt ≥ 0` 以 `5×price_t` 结算；334 天逐日独立求解后汇总。

## 1. 证据边界（四类陈述）

| 类别 | 本版本条目 | 说明 |
|---|---|---|
| `literature_fact` | asm-01、asm-05、asm-10 | 有摘要级/题录级来源支撑的建模结构 |
| `problem_statement` | asm-04、asm-11、asm-13 | 题面/附录直接给定（硬约束或数据口径） |
| `project_assumption` | asm-02、asm-03、asm-06、asm-07、asm-08、asm-09、asm-12、asm-16 | 题面未唯一确定、需本题建立的建模选择 |
| `team_decision` | asm-14、asm-17 | 阈值/取舍类决策，须在论文边界声明 |

> 继承关系：asm-08/asm-09/asm-10/asm-14/asm-15 由 prob01 `assumption_v001` 的 asm-03/asm-04+asm-05/asm-06/asm-10/asm-12 继承，`version.yaml` 中以 `status: inherited` 与 `inherited_from` 显式登记；数值含义未改动。

## 2. accepted 假设清单

### 2.1 关键假设（key = true）

| ID | 假设 | 类型 | 证据类型 | 关键来源 |
|---|---|---|---|---|
| asm-01 | 两阶段「0:00 计划—实际补救」主框架 | 建模框架 | literature_fact | `ref-prob02-trading-morales-2010`、`ref-prob02-loadshed-zeinalzadeh-2017`、`ref-prob02-dayaheadintraday-xie-2021` |
| asm-02 | 0:00 信息集：负载已知 + 0:00 光伏预报（A3） | 信息结构 | project_assumption | `ref-prob02-voi-chazarra-2016`、`ref-prob02-pvforecast-mayer-2021`、`ref-prob02-imbalance-bottieau-2020` |
| asm-03 | 供电充足判定与 5 倍不对称紧急购电（A11） | 边界条件与结算 | project_assumption | `ref-prob02-balancing-vanderveen-2016`、`ref-prob02-imbalance-bottieau-2020`、`ref-prob02-marketdesign-hu-2018` |
| asm-04 | 计划量按计划购电量计费（I3） | 计费口径 | problem_statement | `ref-prob02-balancing-vanderveen-2016`、`ref-prob02-marketdesign-hu-2018` |
| asm-05 | 目标为全年总费用最小；日循环下逐日独立 MILP | 框架与求解 | literature_fact | `ref-prob02-centralized-tsikalakis-2008`、`ref-prob02-ems-espin-2020`、`ref-prob02-storagevalue-sioshansi-2009` |
| asm-06 | 跨日边界取日循环 `E_d,0 = E_d,144 = 6000`（A2/A10） | 边界条件 | project_assumption | `ref-prob02-voi-chazarra-2016`、`ref-prob02-bessmodels-rosewater-2019`、`ref-prob02-terminal-han-2025` |
| asm-07 | 执行层按计划执行储能，紧急购电是唯一补救手段 | 行为规则 | project_assumption | `ref-prob02-loadshed-zeinalzadeh-2017`、`ref-prob02-ems-espin-2020`、`ref-prob02-centralized-tsikalakis-2008` |
| asm-08 | 余电弃光、不反送（A4，继承） | 边界条件 | project_assumption | `ref-prob02-loadshed-zeinalzadeh-2017`、`ref-prob02-bessmodels-rosewater-2019` |
| asm-09 | 单向 90%、833.33 kWh/10min、并网点侧计量（A14，继承） | 机理简化与单位口径 | project_assumption | `ref-prob02-bessmodels-rosewater-2019`、`ref-prob02-milpdegr-minh-2024` |
| asm-10 | 充放电互斥（继承） | 物理约束 | literature_fact | `ref-prob02-bessmodels-rosewater-2019`、`ref-prob02-milpdegr-minh-2024` |

**asm-01 两阶段「0:00 计划—实际补救」主框架**。第一阶段在 0:00 确定当日计划购电量 $q_{d,t}$ 与储能计划 $C_{d,t},D_{d,t},E_{d,t}$；第二阶段按实际负载/光伏执行，供电不足由 $u_{d,t}$ 以 $5\times$ 交易时刻电价补足；目标为 334 天总购电费用最小。
*证据*：F5——日前计划与日内/实时补救属不同信息结构的两阶段问题，可写为线性/两阶段优化（`ref-prob02-trading-morales-2010`、`ref-prob02-dayaheadintraday-xie-2021`，摘要级；`ref-prob02-twostage-ma-2022` 题录级仅框架先例）；F3——微网可先确定向主网的净负荷/购电轨迹，实际不足用未供电变量刻画（`ref-prob02-loadshed-zeinalzadeh-2017`，摘要级）。
*适用边界*：单一微网、单一储能、单一外网通道；0:00 一次决策，当日不再调整（问题 3 才引入调整与偏差结算）。
*偏差方向*：若实际允许日内滚动修订，本模型会高估紧急购电与购电费；若信息比本版本更差（负载也需预测），则低估紧急购电。
*验证*：formulation 写明两阶段的决策时点与信息集；computation 分别报告计划量、执行量与逐日紧急购电总量/次数。

**asm-02 0:00 信息集：当日负载已知 + 当日 0:00 光伏预报（A3）**。0:00 制定计划时：当日小区负载（附件 2「小区负载」）视为已知刚性需求；光伏取**当日 0:00 发布的未来 24 小时整点预报**（附件 3），展开到 10 分钟时段后作为计划依据；实际时段取附件 2「光伏发电实际功率」。附件 1 只提供逐日相同的电价曲线。
*证据*：F7——光伏预测存在可观误差、预测≠实际（`ref-prob02-pvforecast-mayer-2021`，摘要级）；F5/F6——完美信息价值可量化、日前与实时属不同信息结构（`ref-prob02-voi-chazarra-2016`，摘要级）；F2——偏差方向与结算价格必须分别定义（`ref-prob02-imbalance-bottieau-2020`，摘要级）。题面问题 3 明示「在每天 0:00、6:00、12:00 和 18:00 可获得未来 24 小时整点的光伏发电功率预报」，即 **0:00 预报是既有的信息条件**；物理上 0:00 亦无法预知当日实际光伏。
*只读数据事实（本次探针，见 `runtime/tmp/prob02_alignment_probe.py` / `prob02_alignment_probe.json`）*：附件 3 的 0:00 报表与**同日**实际的小时级相对 L1 误差均值 **14.89%**（365 天），优于次日对齐 16.53% 与前日对齐 16.49%，证实「同日对齐」；全年 163 天实际净负荷高于预报净负荷。
*适用边界与张力*：题面问题 2 的数据清单只列「附件 1 的电价和附件 2 的数据」，未列附件 3；本版本把 0:00 预报纳入计划信息集属**口径选择**，若改用附件 2 实际值（alt-01）则 $u\equiv 0$、题面要求的紧急购电机制退化为空；若改用附件 1 的年度日均曲线（alt-02）则偏差被系统性放大。两种反面口径均已登记，论文与交付必须显式声明本口径，不得静默采用。
*偏差方向*：完全信息口径下全年费用更低（信息价值上界）；典型日预测口径下费用更高。
*验证*：formulation 固定信息集与「预报 k 小时→区间」的展开规则；computation 报告预报-实际偏差统计与逐日 $u$；robustness 对照 alt-01/alt-02。

**asm-03 供电充足判定与 5 倍不对称紧急购电（A11）**。逐 10 分钟按四源平衡判定：$q_{d,t}+u_{d,t}+pv_{d,t}\Delta t+D_{d,t}-C_{d,t}-curtail_{d,t}\ge load_{d,t}\Delta t$，缺口 $u_{d,t}\ge 0$ 按 $5\times price_t$ 结算；$\alpha_{em}=5$ 由题面给定。计划量超出实际需求的方向不额外罚款。
*证据*：F1——平衡市场处理日前承诺与实际供需偏差，偏差的结算规则与惩罚强度是核心设计变量（`ref-prob02-balancing-vanderveen-2016`、`ref-prob02-marketdesign-hu-2018`，摘要级）；F2——偏差有正负两个方向（`ref-prob02-imbalance-bottieau-2020`，摘要级）。题面明文给出「不可低于负载」与「5 倍电价」，属题面硬约束，**不**当作文献结论。
*适用边界*：全时段；$u$ 为目标中的惩罚性补救量，**不得预设为恒 0**，也不得与计划量重复计入供电。
*偏差方向*：若结算对正偏差也计费，本模型低估费用；若紧急电价低于 5 倍，则低估规避动机。
*验证*：computation 报告逐日紧急购电总量、发生时段与次数；sanity 独立回代四源平衡残差并检查计费单价恰为 $5\times price_t$；robustness 用 alt-01 验证「完全信息下 $u$ 应恒为 0」。

**asm-04 计划量按计划购电量计费（I3）**。$q_{d,t}$ 是结算量而非实际取用量：无论实际取用多少，均按 $q_{d,t}$ 与 $price_t$ 结算；多买不退，少买由 $u_{d,t}$ 以 5 倍补足。$\text{Cost}=Cost_{plan}+Cost_{em}$。
*证据*：题面明文「除紧急购电费用外，其他时间段的购电费用均按计划购电量计算」；F1/F4 提供「日前承诺量 + 偏差惩罚性结算」的机制定位（摘要级）。计费基数取计划量是题面规定，不属文献结论。
*适用边界*：表 1/表 2 的「全天购电量」「全天购电费」口径。
*偏差方向*：若实际按取用量计费，计划偏保守不产生额外成本，规避紧急购电的动机更强；本口径使「偏保守/偏激进」具有不对称经济后果。
*验证*：formulation 显式写出计划量结算式；sanity 检查 `C_plan = Σ price_t·q_dt` 与 result2.xlsx「全天购电费」一致，禁止实现静默改成按实际取用量计费。

**asm-05 目标与求解组织**。$\min \sum_d\sum_t (price_t q_{d,t} + 5\,price_t u_{d,t})$；日循环下 334 天互不耦合，等价于逐日独立求解 144 时段 MILP 后求和。
*证据*：F9——集中式 EMS 是微网调度主流架构，并网模式下与主网的功率交换以经济性为目标优化（`ref-prob02-centralized-tsikalakis-2008`、`ref-prob02-ems-espin-2020`，摘要级）；`ref-prob02-storagevalue-sioshansi-2009`（题录级）为全年逐时段评估提供口径先例。逐日解耦是日循环边界的数学结果，不依赖文献。
*验证*：formulation 给出可分离性说明；computation 报告逐日 solver status/best bound/gap 与全年汇总；robustness 对照 alt-03。

**asm-06 跨日储能边界取日循环（A2/A10）**。$E_{d,0}=E_{d,144}=6000$ kWh（334 天同值，6000 取自附录 1 的 2025-01-01 0:00 电量）。
*证据*：F6——日循环（daily-cycle）是储能调度常见设定（`ref-prob02-voi-chazarra-2016`，摘要级）；SOC 递推、效率与边界条件是 BESS 最优控制核心要素、边界处理显著影响结果（`ref-prob02-bessmodels-rosewater-2019` 摘要级；`ref-prob02-terminal-han-2025` 题录级）。题面问题 1 明写两端相等、问题 2 未重复，但表 2 仍逐日交付两端储电量；**共同取值 6000 来自附录 1，不来自文献**。
*适用边界*：全部 334 天；交付范围 2025-02-01~12-31。
*偏差方向*：若实际为连续跨日，日循环会切断跨日能量转移——PV 富余日高估弃光、亏缺日高估紧急购电；水平偏离 6000 会按峰谷价差方向改变费用。
*验证*：sanity 检查逐日两端残差均为 6000 且逐时段落在 [1200, 10800]；robustness 对照 alt-03 与 $E^{cyc}\in\{4800,6000,7200\}$。

**asm-07 执行层按计划执行储能**。第二阶段按已定 $C_{d,t},D_{d,t}$ 执行（不按实际光伏重新调度）；实际数据实现后若仍低于负载，只能由 $u_{d,t}$ 补足；实际光伏高于预报的超出部分（扣减计划充电后）以弃光处理。
*证据*：题面问题 2 只要求「制定当天的计划购电策略」，未提供任何日内调整机制；问题 3 才引入「根据其他时刻的预报调整购电策略」。F3——微网按给定净负荷轨迹执行、实际不足用未供电变量刻画（`ref-prob02-loadshed-zeinalzadeh-2017`，摘要级）；F9——集中式 EMS 以日前计划驱动运行（`ref-prob02-ems-espin-2020`、`ref-prob02-centralized-tsikalakis-2008`，摘要级）。
*适用边界*：问题 2；问题 3 引入调整机制后本口径失效。
*偏差方向*：不允许储能按实际光伏再调度会**放大**紧急购电量；alt-06（实时再调度）用于量化储能灵活性的价值。
*验证*：formulation 明确「计划层/执行层」两套变量；computation 分别报告计划充放电量与执行缺口；ablation 用 alt-06 对照。

**asm-08 余电弃光、不反送（A4，继承 prob01 asm-03）**。超出负载与充电需求的余电记为 $curtail_{d,t}\ge 0$（零收益），不建模上网或反送。
*证据*：题面与附件均无上网电价或反送计量要求；F3 表明弃光是微网调度常规建模手段（摘要级）。附件 2 全年有 330 天存在单时段正余电（探针：最大单时段余电 6 602.0 kW），弃光量预计显著非零。
*偏差方向*：若存在正上网电价，本模型低估收益、高估购电费；零收益假设下偏差可忽略。
*验证*：computation 报告全年弃光总量、发生时段与原因（SOC 达上界或单时段功率受限）；robustness 对照 alt-04。

**asm-09 效率与功率口径（A14，继承 prob01 asm-04/asm-05）**。90% 解释为充/放各 0.90（往返约 0.81），效率作用于状态转移；$P_{max}\Delta t = 5000/6\approx 833.33$ kWh；$C,D$ 统一取并网点侧电量口径。
*证据*：`ref-prob02-bessmodels-rosewater-2019`（A/摘要级）指出 SOC 递推、效率与边界条件是 BESS 模型核心要素、建模选择显著影响结果；`ref-prob02-milpdegr-minh-2024`（题录级）仅 MILP 框架先例。附录 1 未指明单侧/往返与计量侧，属 `project_assumption`。
*偏差方向*：若 90% 实为往返效率（单侧 0.9487），当前口径高估损耗、费用偏高；若 5000 kW 实为电池侧而按并网点侧解释，可行域被高估约 $1/\eta$。
*验证*：sanity 检查 $0\le C,D\le 833.33$、SOC 递推残差与量纲；robustness 沿用 prob01 的口径对照并报告方向一致性。

**asm-10 充放电互斥（继承 prob01 asm-06）**。同一时段不允许同时充放电，以 0-1 + big-M（$M=833.33$，由题面功率上限导出）作为硬约束。
*证据*：同时充放电物理不可实现；`ref-prob02-bessmodels-rosewater-2019`（摘要级）说明电池最优控制模型须显式表示 SOC 递推与功率边界；`ref-prob02-milpdegr-minh-2024`（题录级）提供 MILP 框架先例。**本问文献池没有专门的互补性/互斥来源**（prob01 的互补性论文不在本池），故 big-M 只由题面功率上限导出，不引文献数值。
*验证*：computation 检查 $\min(C_{d,t},D_{d,t})=0$（容差 $10^{-9}$）与整数性状态；若走松弛路线必须先给出成立条件或反例，不得照搬 prob01 的数值证据。

### 2.2 非关键假设（key = false）

| ID | 假设 | 证据类型 | 证据/来源 | 偏差方向与验证 |
|---|---|---|---|---|
| asm-11 | 运行区间 $1200\le E_{d,t}\le 10800$；12000 kWh 不作运行上界 | problem_statement | 附录 1 明文 | 误用 12000 会放宽可行域、低估费用与弃光；sanity 逐时段残差检查 |
| asm-12 | 时段内恒功率、电量 = 功率 × $dt$；整点预报在同一小时内取均值展开到 10 分钟 | project_assumption | 附件 2/4 为 10 分钟数据、附件 3 为整点预报；已用附件 2 小时均值核验附件 3 的整点口径 | 平滑掉小时内起伏；sanity 检查四源平衡残差、量纲与 4 小时块汇总一致性 |
| asm-13 | 电价取附件 1 的全年日均代表日曲线，逐日相同（A13） | problem_statement | 题面问题 2「每天的电价相同」；附件 1 已核验为日均代表日 | 用附件 4 会改变费用与套利空间（由问题 4 承担）；sanity 抽查 $price_t$ 与附件 1 一致且不随 $d$ 变 |
| asm-14 | 不建模电池退化/循环成本（继承 prob01 asm-10） | team_decision | 题面无循环/老化数据；`ref-prob02-aging-collath-2022`（摘要级）指出忽略退化为高估收益 | 高估日内套利与紧急购电规避；论文边界章节声明 |
| asm-15 | 时间标签口径统一（A9，继承 prob01 asm-12 并扩展到 result2.xlsx） | project_assumption | 附录 2「0:00+1 即当天 24:00」；result2.xlsx 末列 0:00-0:10+1 证实整体偏移；模板含字面笔误 `7:0-7:10` | **按标签字面逐行对齐会使 144 个时段整体错位一个间隔**；交付前核对表 1 的 10:00-10:10 取自第 61 列并抽查 3 个时段 |
| asm-16 | 交付 2025-02-01~12-31 共 334 天；日循环水平取 6000 kWh（A10） | project_assumption | 附件 5 result2.xlsx 行范围；附录 1 的 2025-01-01 0:00 电量 | 若应含 1 月或取连续口径，2 月起初值与费用会变；robustness 用 alt-03 对照 |
| asm-17 | 紧急购电逐 10 分钟判定；交付按表 4 合并连续时段；$\lvert u\rvert<10^{-9}$ 归零 | team_decision | 题面表 4 的填写示例（允许一日多段） | 阈值不一致会使表 3 分段合计与逐时段明细不闭合；sanity 核对合计（容差 $10^{-6}$） |

## 3. 关键假设来源（可核验性）

关键假设 10 条全部具备 verified & used 来源；文献池门禁 `check_key_assumptions` 本版本实测 **通过**（`passed: true`，21 篇 verified+used 满足 `minimum_items_per_question`）。

- **两阶段框架（asm-01）**：`ref-prob02-trading-morales-2010`（IEEE TPS，摘要级：日前决策 + 平衡偏差可写成线性规划）、`ref-prob02-dayaheadintraday-xie-2021`（JES，摘要级：微网日前计划 + 日内调度两阶段）、`ref-prob02-loadshed-zeinalzadeh-2017`（ACC，摘要级：净负荷轨迹 + 未供电变量）。
- **信息集（asm-02）**：`ref-prob02-voi-chazarra-2016`（摘要级：完美信息价值与日循环设定）、`ref-prob02-pvforecast-mayer-2021`（摘要级：预测模型间 MAE 相差约 13%，预测≠实际）、`ref-prob02-imbalance-bottieau-2020`（摘要级：偏差方向与结算规则）。
- **结算与惩罚（asm-03、asm-04）**：`ref-prob02-balancing-vanderveen-2016`、`ref-prob02-marketdesign-hu-2018`（摘要级：偏差定价与 VOLL 对照）、`ref-prob02-imbalance-bottieau-2020`（摘要级：单/双价不平衡结算）。
- **框架与求解（asm-05）**：`ref-prob02-centralized-tsikalakis-2008`、`ref-prob02-ems-espin-2020`（摘要级：集中式 EMS 与并网经济调度）、`ref-prob02-storagevalue-sioshansi-2009`（题录级：仅全年评估口径）。
- **跨日边界（asm-06）**：`ref-prob02-voi-chazarra-2016`（摘要级：daily-cycle）、`ref-prob02-bessmodels-rosewater-2019`（摘要级：边界与 SOC 建模地位）、`ref-prob02-terminal-han-2025`（题录级：边界处理影响结果）。
- **执行口径（asm-07）**：`ref-prob02-loadshed-zeinalzadeh-2017`、`ref-prob02-ems-espin-2020`、`ref-prob02-centralized-tsikalakis-2008`（均摘要级）。
- **弃光（asm-08）**：`ref-prob02-loadshed-zeinalzadeh-2017`（摘要级：弃光与切负荷风险）、`ref-prob02-bessmodels-rosewater-2019`（摘要级）。
- **效率与计量侧（asm-09）**：`ref-prob02-bessmodels-rosewater-2019`（摘要级）；`ref-prob02-milpdegr-minh-2024` 为**题录级**，只作框架先例，不支撑任何定量内容。
- **互斥（asm-10）**：`ref-prob02-bessmodels-rosewater-2019`（摘要级，SOC/功率边界）+ 物理必要性；**本池缺少专门互补性来源**，已在 `version.yaml` 的 `evidence` 中如实标注，big-M 由题面功率上限导出。

> 说明：asm-02/asm-03/asm-06/asm-07/asm-09 的**取值与口径选择**均为本题建立的项目假设或题面规定，文献只支撑其**结构合理性**；本文件与 `version.yaml` 均未把项目假设伪装成文献事实。asm-15/asm-16/asm-17 无文献可援引，`reference_ids: []`（非关键假设，不触发引用门禁）。

## 4. 冲突检查与处理

- **无阻塞性冲突（blocking = []）**。
- **asm-02 × asm-07（必须成对）**：asm-02 决定第一阶段计划依据（0:00 预报），asm-07 决定第二阶段按计划执行、缺口由 $u$ 补足。只取 asm-02 而允许实时重调度即退化为 alt-06；只取 asm-07 而以实际值做计划即退化为 alt-01。formulation 必须同时写明两层。
- **asm-03 × asm-04（必须分别实现）**：缺口按**实际**数据判定，费用按**计划量 + 紧急量**结算；不得把 $u$ 计入 $q$，也不得反过来。
- **asm-06 × asm-16**：日循环水平取 6000 kWh、334 天同值、1 月不进入交付，三者一致。
- **asm-09 × asm-06**：并网点侧计量下 $E_{d,t}=E_{d,t-1}+\eta_{ch}C_{d,t}-D_{d,t}/\eta_{dis}$ 且 $D_{d,t}$ 直接进入功率平衡；若改电池侧口径则 $E_{d,t}=E_{d,t-1}+C_{d,t}-D_{d,t}$ 且平衡式含 $\eta$。两条口径不得混用。
- **asm-05 × asm-06**：逐日独立最优在日循环下等价于全年最优；但不得据此省略全年汇总与逐日可追溯性。
- **与前问结论**：prob01 结论 `prob01-conclusion-v001`（version 1，hash `6a2546c6…`）作为设备层基线与费用对照被引用；asm-08/09/10/14/15 继承其 asm-03/04+05/06/10/12，数值含义未变。**prob01 的 asm-07（单日代表日、不外推全年）在本问失效**（本问用附件 2 逐日实际数据）；**prob01 的 asm-02（单日两端共同取 6000）被 asm-06 升级为逐日日循环水平 6000**，两种表述不得混用。
- **与题面硬约束**：全部假设均不削弱供电充足、1200~10800 kWh、单时段 ≤ 833.33 kWh、互斥、计划量按计划电价、紧急量按 5 倍电价等硬约束。**asm-02 与题面问题 2 的数据清单存在口径张力**，已在第 0/2/6 节与 `version.yaml` 的 `boundary_note` 显式登记。

## 5. 被否决的备选路线（保留为 robustness/ablation 对照）

| ID | 备选路线 | 否决理由 |
|---|---|---|
| alt-01 | 完全信息确定性口径（计划依据附件 2 实际光伏） | 该口径下 $u\equiv 0$，题面要求的紧急购电机制退化为空；保留为「完美信息」费用下界（信息价值）对照 |
| alt-02 | 典型日预测口径（计划依据附件 1 的年度日均光伏曲线） | 逐日偏差被系统性放大（探针 L1 误差均值约 11 056 kWh/日、最大 21 122 kWh/日，远大于 0:00 预报的 8 174 kWh/日），量级失真 |
| alt-03 | 连续跨日边界（$E_{d,0}=E_{d-1,144}$，1 月预热） | 需额外指定终端条件否则出现自由终端伪解，且使 334 天耦合；保留为 A2/A10 的对照 |
| alt-04 | 允许反送并计上网电价收益 | 题面与附件无上网电价，参数不可辨识；零收益下与 asm-08 等价 |
| alt-05 | 引入电池退化/循环成本 | 无循环/老化/温度数据，模型不可辨识；目标应贴合题面「购电费用」 |
| alt-06 | 储能实时再调度（实际数据下重优化 C/D，$q$ 不变） | 问题 2 无调整机制（问题 3 才引入）；保留为消融，量化储能灵活性对紧急购电的削减 |
| alt-07 | 自由终端储电量 | 会产生透支/留存的伪解，与 asm-06 冲突，仅记不可选 |

## 6. 待研究/待证实事项（传给 formulation 与 computation）

- **I1**（agent_inference，待 computation 证实）：紧急购电由 0:00 预报误差驱动。探针显示附件 3 的 0:00 预报与同日实际的小时级相对 L1 误差均值 **14.89%**；4 个交付日期（2025-03-20 / 06-21 / 09-23 / 12-21）的预报-实际光伏正缺口分别约 **6 059 / 3 618 / 3 343 / 2 007 kWh**；全年 **163 天**实际净负荷高于预报净负荷。computation 必须给出逐日 $u$ 总量、发生时段与次数，以及表 3 四个日期的数值；某日 $u=0$ 须显式登记为 0，不得留空。
- **I2**（agent_inference，待 computation 证实）：334 个独立的 144 时段 MILP（各含 144 个 0-1）+ 334 次缺口评估，规模与 prob01 同量级，精确求解应可行；须以 solver status、best bound 与 `mip_gap` 证实；若超时或 gap 缺失，按 `PASS_WITH_WARNING` 保留技术债，不得直接人工阻塞。
- **I3**（口径推断，待 formulation/sanity 检查）：计划量结算式必须显式实现，sanity 须核对 result2.xlsx「全天购电费」与 $\sum_t price_t q_{d,t}$（+ 紧急购电费）一致，禁止静默改成按实际取用量计费。
- **I4**（待 computation 报告）：实际光伏高于预报的时段出现弃光（附件 2 全年 330 天存在单时段正余电，最大单时段余电 6 602.0 kW）；低于预报的时段（计划充电/放电被照常执行）出现紧急购电；两者都必须按段报告时段与原因。
- **I5**（待 formulation 固定）：「预报 k 小时」与整点区间、跨日边界的对应关系；同日对齐已由探针证实（14.89% < 16.53% < 16.49%），展开到 10 分钟的规则必须写明。该口径错误会系统性改变 $q_{d,t}$ 与 $u_{d,t}$。
- **技术债提醒**：asm-02 的口径选择与题面问题 2 的数据清单存在张力；论文边界章节与交付说明必须声明本口径，并给出 alt-01（完全信息）对照，说明「紧急购电为 0」是 alt-01 的结论而非本模型结论。

## 7. 建议的 formulation 方向

1. **第一阶段（计划层，0:00）**：对每个 $d$（334 天）独立求解 MILP
   $\min \sum_{t=1}^{144} price_t\,q_{d,t}$
   s.t. 预测口径平衡 $q_{d,t}+pv^{fc}_{d,t}\Delta t+D_{d,t}-C_{d,t}-curtail_{d,t}\ge load_{d,t}\Delta t$、
   状态转移 $E_{d,t}=E_{d,t-1}+\eta_{ch}C_{d,t}-D_{d,t}/\eta_{dis}$、
   $1200\le E_{d,t}\le 10800$、$0\le C_{d,t},D_{d,t}\le 833.33$、互斥 0-1 + big-M、
   日循环 $E_{d,0}=E_{d,144}=6000$、终端与计划采购非负。
2. **第二阶段（执行/补救层）**：按计划的 $C^*_{d,t},D^*_{d,t}$ 与实际 $pv_{d,t}$ 计算缺口
   $u_{d,t}=\max\big(0,\ load_{d,t}\Delta t+C^*_{d,t}+curtail_{d,t}-q^*_{d,t}-pv_{d,t}\Delta t-D^*_{d,t}\big)$，
   并按 $5\,price_t$ 结算；实际光伏盈余按弃光登记。
3. **费用与指标（在看到结果前固定）**：全年与逐日 $Cost_{plan}$、$Cost_{em}$、总购电量 $Q$、紧急购电量与发生次数/时段、弃光总量、SOC 越界与功率越界计数、四源平衡残差、日循环残差、solver status/best bound/gap。
4. **robustness/ablation 固定对照**：alt-01（完全信息，验证 $u\equiv 0$）、alt-02（典型日预测）、alt-03（连续跨日）、alt-06（储能实时再调度）；日循环水平 $E^{cyc}\in\{4800,6000,7200\}$；asm-09 的效率与计量侧口径对照。
5. **禁止事项**：不得为通过 sanity 事后裁剪异常结果；不得在看到结果后修改上述比较指标；不得把 alt-01/alt-06 悄悄放回主模型；不得在交付中省略「紧急购电为 0 的日期」的显式登记。
