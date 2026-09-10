# prob01 文献研究：固定电价/负载下的计划购电模型

> 上游：`problems/CUMCM2026-C/prob01/shared/problem_understanding.md`、`global_symbols.yaml`、`dependency_graph.yaml`。
> 本文件只登记可核验来源与方法先例，不替 assumption / formulation 阶段拍定关键假设。
> 机器可读文献池：`problems/CUMCM2026-C/prob01/shared/literature_pool.yaml`；题目引用表：`problems/CUMCM2026-C/citations.yaml`。

## 1. 本轮概览

| 项 | 值 |
|---|---|
| 轮次 | `rnd-*`（见 pool `rounds`，query 见第 2 节） |
| 检索日期 | 2026-09-10 |
| 池内条目 | 18（used 16，rejected 2，pending 0） |
| 元数据核验 | 18/18 通过 Crossref（`verified: true`） |
| dry | **true**，`dry_reason: all_candidates_decided`（全部候选已 used/rejected） |
| 权威级别 | A 级 17（含 1 份 IEEE 标准），B 级 1（已否决） |
| 内容核验深度 | 摘要级 11，题录级 7（已明确标注，不用于支撑关键定量主张） |

dry 说明：本轮候选全部完成裁决，且已覆盖 prob01 的建模框架、储能状态方程、互斥约束、分时电价套利与并网背景五个证据方向；继续同一术语检索的边际收益低，故按 `all_candidates_decided` 结束本轮。若后续 formulation 出现新的模型族（如随机/鲁棒优化），应换术语与证据路径重新开轮，而不是重复本轮查询。

## 2. 检索策略

先建立术语（综述/标准），再查原始研究与方法细节，最后核对元数据：

```text
对象：microgrid / grid-connected microgrid / photovoltaic-battery storage
机理：state-of-charge dynamics / charging and discharging efficiency / round-trip efficiency
方法：mixed-integer linear programming / day-ahead scheduling / rolling horizon / model predictive control
约束：charge-discharge complementarity / big-M linearization / generation curtailment / no power export
场景：time-of-use tariff / energy arbitrage / unit commitment
```

实际使用的检索入口：Crossref `query.bibliographic`（题录与 DOI 核验）、OpenAlex（倒排摘要）、Semantic Scholar（受 429 限流，仅少量使用）、IOPscience / Elsevier Pure（机构仓储）权威页面读取摘要。所有 DOI 均由 Crossref 解析确认身份，未使用搜索摘要作为引用依据。

## 3. 文献池登记表

| ID | 标题 | 作者 | 年 | 来源 | DOI | 级别 | 内容核验 | 状态 |
|---|---|---|---|---|---|---|---|---|
| ref-prob01-milp-tenfen-2015 | A mixed integer linear programming model for the energy management problem of microgrids | Tenfen, D.; Finardi, E. C. | 2015 | Electric Power Systems Research, 122, 19-28 | [10.1016/j.epsr.2014.12.019](https://doi.org/10.1016/j.epsr.2014.12.019) | A | 题录级 | used |
| ref-prob01-dayahead-silva-2020 | Optimal Day-Ahead Scheduling of Microgrids with Battery Energy Storage System | Silva, V. A.; Aoki, A. R.; Lambert-Torres, G. | 2020 | Energies, 13(19), 5188 | [10.3390/en13195188](https://doi.org/10.3390/en13195188) | A | 摘要级 | used |
| ref-prob01-milp-morais-2010 | Optimal scheduling of a renewable micro-grid in an isolated load area using mixed-integer linear programming | Morais, H.; Kadar, P.; Faria, P.; Vale, Z.; Khodr, H. M. | 2010 | Renewable Energy, 35(1), 151-156 | [10.1016/j.renene.2009.02.031](https://doi.org/10.1016/j.renene.2009.02.031) | A | 题录级 | used |
| ref-prob01-mpc-parisio-2014 | A Model Predictive Control Approach to Microgrid Operation Optimization | Parisio, A.; Rikos, E.; Glielmo, L. | 2014 | IEEE Trans. Control Systems Technology, 22(5), 1813-1827 | [10.1109/TCST.2013.2295737](https://doi.org/10.1109/TCST.2013.2295737) | A | 摘要级 | used |
| ref-prob01-rolling-palma-2013 | A Microgrid Energy Management System Based on the Rolling Horizon Strategy | Palma-Behnke, R. 等 | 2013 | IEEE Trans. Smart Grid, 4(2), 996-1006 | [10.1109/TSG.2012.2231440](https://doi.org/10.1109/TSG.2012.2231440) | A | 摘要级 | used |
| ref-prob01-nottrott-2013 | Energy dispatch schedule optimization and cost benefit analysis for grid-connected, photovoltaic-battery storage systems | Nottrott, A.; Kleissl, J.; Washom, B. | 2013 | Renewable Energy, 55, 230-240 | [10.1016/j.renene.2012.12.036](https://doi.org/10.1016/j.renene.2012.12.036) | A | 题录级 | used |
| ref-prob01-complementarity-fortuny-1981 | A Representation and Economic Interpretation of a Two-Level Programming Problem | Fortuny-Amat, J.; McCarl, B. | 1981 | J. Operational Research Society, 32(9), 783-792 | [10.1057/jors.1981.156](https://doi.org/10.1057/jors.1981.156) | A | 摘要级 | used |
| ref-prob01-complementarity-garifi-2020 | Convex Relaxation of Grid-Connected Energy Storage System Models With Complementarity Constraints in DC OPF | Garifi, K.; Baker, K.; Christensen, D.; Touri, B. | 2020 | IEEE Trans. Smart Grid, 11(5), 4070-4079 | [10.1109/TSG.2020.2987785](https://doi.org/10.1109/TSG.2020.2987785) | A | 摘要级 | used |
| ref-prob01-storage-luo-2015 | Overview of current development in electrical energy storage technologies and the application potential in power system operation | Luo, X.; Wang, J.; Dooner, M.; Clarke, J. | 2015 | Applied Energy, 137, 511-536 | [10.1016/j.apenergy.2014.09.081](https://doi.org/10.1016/j.apenergy.2014.09.081) | A | 摘要级 | used |
| ref-prob01-arbitrage-grimaldi-2024 | Profitability of energy arbitrage net profit for grid-scale battery energy storage considering dynamic efficiency and degradation … | Grimaldi, A.; Minuto, F. D.; Brouwer, J.; Lanzini, A. | 2024 | Journal of Energy Storage, 95, 112380 | [10.1016/j.est.2024.112380](https://doi.org/10.1016/j.est.2024.112380) | A | 摘要级 | used |
| ref-prob01-unitcommit-nguyenduc-2022 | A Mixed-Integer Programming Approach for Unit Commitment in Micro-Grid with Incentive-Based Demand Response and Battery Energy Storage System | Nguyen-Duc, T. 等 | 2022 | Energies, 15(19), 7192 | [10.3390/en15197192](https://doi.org/10.3390/en15197192) | A | 摘要级 | used |
| ref-prob01-microgrid-review-hirsch-2018 | Microgrids: A review of technologies, key drivers, and outstanding issues | Hirsch, A.; Parag, Y.; Guerrero, J. M. | 2018 | Renewable and Sustainable Energy Reviews, 90, 402-411 | [10.1016/j.rser.2018.03.040](https://doi.org/10.1016/j.rser.2018.03.040) | A | 摘要级 | used |
| ref-prob01-ems-review-abbasi-2023 | Recent developments of energy management strategies in microgrids: An updated and comprehensive review and classification | Abbasi, A. R. 等 | 2023 | Energy Conversion and Management, 297, 117723 | [10.1016/j.enconman.2023.117723](https://doi.org/10.1016/j.enconman.2023.117723) | A | 题录级 | used |
| ref-prob01-tou-modu-2025 | The role of hybrid hydrogen-battery storage in a grid-connected renewable energy microgrid considering time-of-use electricity tariffs | Modu, B. 等 | 2025 | Journal of Energy Storage, 105, 114729 | [10.1016/j.est.2024.114729](https://doi.org/10.1016/j.est.2024.114729) | A | 摘要级 | used |
| ref-prob01-capacity-gitizadeh-2014 | Battery capacity determination with respect to optimized energy dispatch schedule in grid-connected photovoltaic (PV) systems | Gitizadeh, M. 等 | 2014 | Energy, 65, 665-674 | [10.1016/j.energy.2013.12.018](https://doi.org/10.1016/j.energy.2013.12.018) | A | 题录级 | used |
| ref-prob01-ieee1547-2018 | IEEE Standard for Interconnection and Interoperability of Distributed Energy Resources with Associated Electric Power Systems Interfaces | IEEE Standards Association | 2018 | IEEE Std 1547-2018 | [10.1109/IEEESTD.2018.8332112](https://doi.org/10.1109/IEEESTD.2018.8332112) | A | 题录级 | used |
| ref-prob01-degcost-koller-2013 | Defining a degradation cost function for optimal control of a battery energy storage system | Koller, M.; Borsche, T.; Ulbig, A.; Andersson, G. | 2013 | 2013 IEEE Grenoble Conference (PowerTech), 1-6 | [10.1109/PTC.2013.6652329](https://doi.org/10.1109/PTC.2013.6652329) | B | 题录级 | **rejected** |
| ref-prob01-degradation-reniers-2019 | Review and Performance Comparison of Mechanical-Chemical Degradation Models for Lithium-Ion Batteries | Reniers, J. M.; Mulder, G.; Howey, D. A. | 2019 | J. Electrochemical Society, 166(14), A3189-A3200 | [10.1149/2.0281914jes](https://doi.org/10.1149/2.0281914jes) | A | 摘要级 | **rejected** |

## 4. 关键来源的主张、适用条件与差异

- **ref-prob01-dayahead-silva-2020（核心同构）**：给出微网日前最优调度的详细数学建模，覆盖电池储能、光伏、直接可控负荷、切负荷、计划孤岛与**发电削减(curtailment)**，并在真实分时电价下验证储能套利的降本作用。*适用*：prob01 的问题类型（日前调度 + 储能 + 光伏 + 分时电价）。*差异*：该文含孤岛与切负荷变量、面向分时电价市场；本题 prob01 要求供电不低于负载、无孤岛，须删去切负荷/孤岛变量，并改用 5 倍紧急购电由 prob02 承担。
- **ref-prob01-mpc-parisio-2014 / ref-prob01-rolling-palma-2013**：微网运行优化写成 MILP 并用商用求解器高效求解；滚动时域策略每个决策步基于更新预报重求解，并需显式定义信息集。*适用*：prob01 的建模与求解策略；prob03 的"计划—调整"信息结构先例。*差异*：两者设备构成与结算结构均与本题不同（含可控负荷/柴油/需求侧管理），不能直接搬运目标函数。
- **ref-prob01-milp-tenfen-2015 / ref-prob01-milp-morais-2010**：MILP 作为微网日前能量管理/可再生微网调度的统一框架。*适用*：方法族先例。*差异*：含可控机组或孤岛结构；仅题录级核验，不用于支撑任何参数或公式细节。
- **ref-prob01-complementarity-fortuny-1981**：互补松弛条件的析取性质可用 0-1 变量与大 M 化为混合整数规划。*适用*：充放电互斥 $C_t D_t=0$ 的线性化依据。*差异*：原始语境是双层规划，不提供储能参数；大 M 必须由变量真实上下界导出。
- **ref-prob01-complementarity-garifi-2020**：储能互补约束用于排除同时充放电；除非凸整数方法外，可用**目标罚函数/凸松弛**，但其有效性依赖特定条件（文中给出保证同时充放电为次优解的条件）。*适用*：A5 建模与求解策略；是否必须引入 0-1 的判据。*差异*：DC OPF/MPC 语境，条件不能默认在本问成立。
- **ref-prob01-storage-luo-2015**：按介质分类综述储能技术原理与技术/经济性能，可用于核对 90% 效率与 12000 kWh / 5000 kW 是否处于常见量级。*适用*：A14 合理性对照与 sanity。*差异*：给出的是技术类别范围，**不能替换附录 1 的给定值**。
- **ref-prob01-arbitrage-grimaldi-2024**：套利净收益 = 套利收入 − 购电成本 − 退化成本；无退化为 LP、含退化为 MILP、功率相关动态效率才需 MINLP；退化使年净收益下降约 13%–24%。*适用*：说明**恒定效率下问题保持 LP/MILP**；退化项对经济结论影响显著、忽略须声明。*差异*：含售电收入与退化成本，本题 prob01 不售电、目标只含购电费。
- **ref-prob01-tou-modu-2025**：并网微网在分时电价下，储能"何时充、何时放"是决定系统成本的核心决策，且电价情景改变最优结果。*适用*：prob01 套利逻辑与 prob04 电价情景。*差异*：含氢储与容量优化，目标不同。
- **ref-prob01-unitcommit-nguyenduc-2022**：含 BESS 与需求响应的微网机组组合可用 MIP 建模，并与遗传算法对比验证。*适用*：prob01 采用精确 MILP 作为基线/验证基准的求解策略。*差异*：含柴油、排放与液流电池详细模型。
- **ref-prob01-nottrott-2013 / ref-prob01-capacity-gitizadeh-2014**：并网 PV-电池系统的调度优化与经济性/容量耦合的同构应用先例。*适用*：应用背景与约束刻画先例。*差异*：仅题录级核验，主张限于题名范围。
- **ref-prob01-microgrid-review-hirsch-2018**：微网由分布式电源、储能与负荷构成，可作为单一可控系统并网或孤岛运行。*适用*：术语与背景界定。*差异*：综述，无模型与参数。
- **ref-prob01-ieee1547-2018**：分布式能源并网的互联与互操作性有正式标准要求。*适用*：并网接口的规范背景。*差异*：标准**不规定**本题是否允许余电上网；"不向外部电网反送"仍属 project_assumption。
- **ref-prob01-ems-review-abbasi-2023**：微网能量管理策略存在系统分类（数学规划/MPC/启发式/随机规划）。*适用*：方法族定位与检索入口。*差异*：仅题录级，不支撑优劣结论。

### 已否决候选

- **ref-prob01-degcost-koller-2013（rejected）**：电池退化成本函数虽可进入最优控制目标，但 prob01 目标函数只含购电费用，题目也未提供循环/日历老化数据；本问不采用，仅作 prob04 / robustness 的扩展线索。
- **ref-prob01-degradation-reniers-2019（rejected）**：锂离子退化模型在数据不足时不可辨识（多模型可拟合同一小数据集）。该结论用于支持"prob01 不引入退化成本"的边界说明，但不进入 prob01 引用表；后续 robustness 若需要退化敏感性，应重新开轮并补充工况数据来源。

## 5. 四类陈述的区分（本问证据边界）

**literature_fact（来源明确支持）**

- F1：微网日前调度问题可用确定性 MILP 建模，储能、光伏与发电削减(curtailment)均可显式进入模型（ref-prob01-dayahead-silva-2020；ref-prob01-mpc-parisio-2014）。
- F2：储能同时充放电物理不可实现，必须显式排除；可用 big-M 整数化，或在满足特定条件时用目标罚函数/凸松弛（ref-prob01-complementarity-garifi-2020；ref-prob01-complementarity-fortuny-1981）。
- F3：分时电价下储能充放时点是决定系统成本的核心决策（ref-prob01-tou-modu-2025；ref-prob01-dayahead-silva-2020）。
- F4：恒定效率下套利/调度问题保持 LP/MILP；只有功率相关动态效率才需要 MINLP（ref-prob01-arbitrage-grimaldi-2024）。
- F5：滚动时域重优化与静态日前计划属于不同信息结构，重优化需显式定义每个决策时点的信息集（ref-prob01-rolling-palma-2013）。
- F6：分布式能源并网互联存在正式标准要求（ref-prob01-ieee1547-2018，标准范围）。

**project_assumption（本题建立、需验证边界）**

- P1：`0:00` 与 `24:00` 储电量相等且取附录 1 给定的 6000 kWh（题面只要求"相同"，共同取值由本问设定）→ 对应 A1。
- P2：当光伏 + 放电超过负载时，采用弃光而非向外部电网反送电（题面叙述与交付口径倾向"只购不售"）→ 对应 A4。
- P3：附录 1 的"充放电效率 90%"解释为**单向效率**（充电与放电各 0.9，往返约 0.81），而非往返效率 0.9 → 对应 A14。
- P4：功率上限 5000 kW 按每 10 分钟能量上限 $5000\times\frac{1}{6}=833.33$ kWh 折算，且计量口径统一在储能侧 → 对应 A14。
- P5：附件 1 的日曲线视为可代表"电价与负载每天相同"的典型日（A13），prob01 只使用该单日，不外推全年。

**agent_inference（由数据或推导得到，待 formulation 证实）**

- I1：在效率 $\eta<1$ 且电价非负时，同时充放电通常因能量损耗而次优，但仍需在 formulation 阶段对"无 0-1 变量的 LP 松弛是否已隐含互斥"给出条件证明；文献只给出条件性结论（F2），不能直接引用为本题定理。
- I2：本问 144 时段、单一储能、线性目标与约束的规模下，MILP 分支规模很小，精确求解应可证明最优；该推断需由 implementation/computation 的 solver 状态与 gap 证实。
- I3：终端 SOC 相等约束下，套利收益来自"低价充、高价放"，其上限受容量区间 $[1200,10800]$ 与单向效率约束。

**team_decision（阈值、权重与偏好选择）**

- D1：目标函数取全天购电费最小（题面"尽可能节省购电费用"的直接落地），不额外加入退化成本或循环次数惩罚（依据 F4/否决项与 D3）。
- D2：big-M 的取值方法（由 $C_t,D_t$ 的真实上下界 $[0,833.33]$ 与 SOC 区间导出），以及求解器、容差与时限。
- D3：退化、弃光惩罚等未在题面出现的项一律不进入 prob01 目标，作为 robustness/ablation 的对照变量而非主模型项。

## 6. 生产的候选假设族与公式线索

1. **确定性日前 MILP 主框架**：决策 $q_t, C_t, D_t, E_t$；目标 $\min\sum_t p_t q_t$；约束含时段功率平衡、SOC 递推、容量/功率上下限、终端 $E_{144}=E_0$、非负与互斥。证据：F1、F4。
2. **充放电互斥的三条路线**：(a) 0-1 指示 + big-M（F2）；(b) 目标罚函数/凸松弛（F2，需条件）；(c) 证明松弛已隐含互斥（I1，待证）。证据：ref-prob01-complementarity-garifi-2020、ref-prob01-complementarity-fortuny-1981。
3. **余电/弃光处理族**：(a) 显式弃光变量（F1 支持的建模手段）；(b) 强制反送（与题面叙述相悖，作为对照）；(c) 用等式功率平衡 + 弃光松弛。对应 P2、A4。
4. **效率口径族**：单向 0.9/0.9 与往返 0.9 两种 SOC 递推形式；影响最优购电费与充放电量，必须在 assumption_definition 固定并在 sanity 中做对比。对应 P3、A14。
5. **信息结构族**（供 prob03 预备）：静态日前计划 vs 滚动重优化；本问固定为 0:00 单点决策、信息集 $=$ 当天全部预报与电价。证据：F5。

## 7. 待研究歧义的文献侧结论

| 歧义 | 文献侧结论 | 是否已可裁决 |
|---|---|---|
| A1 终端储电量共同取值 | 文献只支持"日前储能调度通常施加终端/循环边界"，**不能**决定本题共同取值 | 否，属 project_assumption P1，待 assumption_definition |
| A4 余电处理 | Silva 2020 证明 curtailment 是日前调度中的常规建模手段；标准 1547 不规定本题是否允许反送 | 部分，取弃光为 P2 |
| A5 充放电互斥 | 有明确方法与条件（F2），但"本问是否可省 0-1"需在 formulation 证明 | 部分，路线已备 |
| A9 交付时间标签偏移 | 属附件 5 模板与附件时间标签的口径问题，**无文献可援引** | 否，须由数据口径统一，delivery 阶段处理 |
| A13 附件 1 代表日含义 | 综述与调度文献均使用"代表日/典型日"做日前优化，但**不能反推附件 1 的统计定义** | 否，属 P5，待数据说明 |
| A14 效率与功率口径 | 综述给出储能效率量级；Grimaldi 2024 说明恒定效率保持 LP/MILP 而动态效率需 MINLP | 部分，口径选择为 P3/P4 |

## 8. 引用闭合与交付

- 16 篇 used 来源已同步写入 `problems/CUMCM2026-C/citations.yaml`，与 pool 中的 `id` 一一对应；rejected 来源不进入引用表。
- 本轮所有来源均通过 Crossref 元数据核验（`verified: true`）；标注为"题录级"的 7 条只支撑题名级主张，**不得**用于支撑关键假设的定量内容。
- 后续 assumption 版本引用关键假设时，请使用"摘要级"来源（`ref-prob01-dayahead-silva-2020`、`ref-prob01-complementarity-garifi-2020`、`ref-prob01-complementarity-fortuny-1981`、`ref-prob01-arbitrage-grimaldi-2024`、`ref-prob01-tou-modu-2025`、`ref-prob01-mpc-parisio-2014`、`ref-prob01-rolling-palma-2013`、`ref-prob01-storage-luo-2015`、`ref-prob01-microgrid-review-hirsch-2018`、`ref-prob01-unitcommit-nguyenduc-2022`）。

## 9. 下一阶段建议

1. 进入 `assumption_definition`，优先固定 P1（终端储电量）、P3/P4（效率与功率口径）、P2（弃光与反送）四条关键假设，并绑定上述摘要级引用。
2. formulation 阶段对 I1 给出"是否必须引入 0-1 变量"的条件分析或反例，避免把文献的条件性结论当作本题定理。
3. prob02（紧急购电）与 prob03（计划—调整）的文献方向与本轮不同，届时须更换术语（价值损失负荷、滚动优化、违约结算）重新开轮；prob04（波动电价）需补随机/鲁棒优化证据。
