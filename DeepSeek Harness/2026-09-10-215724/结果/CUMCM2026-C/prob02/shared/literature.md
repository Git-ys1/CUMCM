# prob02 文献研究：变化负载/光伏下的日前计划购电与紧急购电

> 上游：`problems/CUMCM2026-C/prob02/shared/problem_understanding.md`、`global_symbols.yaml`、`dependency_graph.yaml`。
> 本文件只登记可核验来源与方法先例，不替 assumption / formulation 阶段拍定关键假设。
> 机器可读文献池：`problems/CUMCM2026-C/prob02/shared/literature_pool.yaml`；题目引用表：`problems/CUMCM2026-C/citations.yaml`。
> 与 prob01 文献轮的边界：本轮按运行状态要求**更换术语与证据路径**，检索对象从"确定性日前调度 + 储能套利"转为"日前计划与实际偏差的惩罚性结算（紧急购电）、未供电经济价值、跨日边界、有限时域末端效应与长时段可解性"；prob01 的 18 条来源不复制进本池。

## 1. 本轮概览

| 项 | 值 |
|---|---|
| 轮次 | `rnd-bc12c1290345`（见 pool `rounds`，query 见第 2 节） |
| 检索日期 | 2026-09-10 |
| 池内条目 | 22（used 21，rejected 1，pending 0） |
| 元数据核验 | 22/22 通过 Crossref（`verified: true`，`verification_provider: crossref`） |
| dry | **true**，`dry_reason: all_candidates_decided`（全部候选已 used/rejected） |
| 权威级别（used） | A 级 18，B 级 3 |
| 内容核验深度（used） | 摘要级 14，题录级 7（已明确标注，不用于支撑关键定量主张） |
| 检索工具 | Crossref `query.bibliographic` 与 DOI 解析、OpenAlex 题录/倒排摘要、Semantic Scholar 题名交叉核对、出版方页面（部分被 403 拒绝） |

dry 说明：本轮候选全部完成裁决，且已覆盖 prob02 的六个证据方向——(i) 平衡/不平衡结算与偏差惩罚定价，(ii) 未供电/切负荷的经济度量与可靠性目标，(iii) 日前计划 + 实时补救的两阶段结构，(iv) 跨日/终端 SOC 边界与末端效应，(v) 0:00 信息集（完美信息 vs 预报），(vi) 334 天规模的可解性与分解。继续用同一术语检索的边际收益低，故按 `all_candidates_decided` 结束本轮。若 assumption/formulation 阶段产生新的模型族（如随机/鲁棒优化、违约结算），应换术语与证据路径重新开轮。

## 2. 检索策略

先建立术语（平衡市场/结算、未供电价值、两阶段调度），再查方法先例（MILP、终端边界、分解），最后核对 DOI 元数据：

```text
结算与惩罚：electricity balancing market / imbalance settlement / deviation penalty /
            two-settlement market / price cap up to value of lost load
未供电与可靠性：unserved energy / load shedding / value of lost load / cost-reliability optimization
两阶段结构：day-ahead plan + intra-day dispatch / two-stage microgrid day-ahead dispatching
储能边界：state-of-charge dynamics / terminal energy / end-of-horizon effect / daily-cycle
信息集：value of perfect information / PV power forecasting error / stochastic unit commitment
规模与求解：long-horizon MILP / Lagrangian relaxation / Benders decomposition / scenario tree
```

实际检索入口：Crossref `query.bibliographic`（题录与 DOI 解析）、OpenAlex（题录、倒排摘要、按被引排序的 title/abstract 检索）、Semantic Scholar Graph API（题录交叉核对，部分 Elsevier 条目无摘要）、出版方/机构页面（ScienceDirect 返回 403，未使用其正文）。所有 DOI 均由 Crossref 解析确认身份后才登记，未使用搜索摘要作为引用依据。

## 3. 文献池登记表

| ID | 标题 | 作者 | 年 | 来源 | DOI | 级别 | 内容核验 | 状态 |
|---|---|---|---|---|---|---|---|---|
| ref-prob02-balancing-vanderveen-2016 | The electricity balancing market: Exploring the design challenge | van der Veen, R. A. C.; Hakvoort, R. A. | 2016 | Utilities Policy, 43, 186-194 | [10.1016/j.jup.2016.10.008](https://doi.org/10.1016/j.jup.2016.10.008) | A | 摘要级 | used |
| ref-prob02-marketdesign-hu-2018 | Identifying barriers to large-scale integration of variable renewable electricity into the electricity market … | Hu, J.; Harmsen, R.; Crijns-Graus, W.; Worrell, E.; van den Broek, M. | 2018 | Renewable and Sustainable Energy Reviews, 81, 2181-2195 | [10.1016/j.rser.2017.06.028](https://doi.org/10.1016/j.rser.2017.06.028) | A | 摘要级 | used |
| ref-prob02-trading-morales-2010 | Short-Term Trading for a Wind Power Producer | Morales, J. M.; Conejo, A. J.; Pérez-Ruiz, J. | 2010 | IEEE Trans. Power Systems, 25(1), 554-564 | [10.1109/TPWRS.2009.2036810](https://doi.org/10.1109/TPWRS.2009.2036810) | A | 摘要级 | used |
| ref-prob02-imbalance-bottieau-2020 | Very-Short-Term Probabilistic Forecasting for a Risk-Aware Participation in the Single Price Imbalance Settlement | Bottieau, J. 等 | 2020 | IEEE Trans. Power Systems, 35(2), 1218-1230 | [10.1109/TPWRS.2019.2940756](https://doi.org/10.1109/TPWRS.2019.2940756) | A | 摘要级 | used |
| ref-prob02-voll-leahy-2011 | An estimate of the value of lost load for Ireland | Leahy, E.; Tol, R. S. J. | 2011 | Energy Policy, 39(3), 1514-1520 | [10.1016/j.enpol.2010.12.025](https://doi.org/10.1016/j.enpol.2010.12.025) | A | 题录级 | used |
| ref-prob02-voi-chazarra-2016 | Value of perfect information of spot prices in the joint energy and reserve hourly scheduling of pumped storage plants | Chazarra, M. 等 | 2016 | 2016 13th EEM Conference, 1-6 | [10.1109/EEM.2016.7521284](https://doi.org/10.1109/EEM.2016.7521284) | B | 摘要级 | used |
| ref-prob02-loadshed-zeinalzadeh-2017 | Minimizing risk of load shedding and renewable energy curtailment in a microgrid with energy storage | Zeinalzadeh, A.; Gupta, V. | 2017 | 2017 American Control Conference (ACC), 3412-3417 | [10.23919/ACC.2017.7963474](https://doi.org/10.23919/ACC.2017.7963474) | B | 摘要级 | used |
| ref-prob02-reliability-nojavan-2017 | An efficient cost-reliability optimization model for optimal siting and sizing of energy storage system in a microgrid … | Nojavan, S. 等 | 2017 | Energy, 139, 89-97 | [10.1016/j.energy.2017.07.148](https://doi.org/10.1016/j.energy.2017.07.148) | A | 题录级 | used |
| ref-prob02-ems-espin-2020 | Energy Management Systems for Microgrids: Main Existing Trends in Centralized Control Architectures | Espín-Sarzosa, D. 等 | 2020 | Energies, 13(3), 547 | [10.3390/en13030547](https://doi.org/10.3390/en13030547) | A | 摘要级 | used |
| ref-prob02-centralized-tsikalakis-2008 | Centralized Control for Optimizing Microgrids Operation | Tsikalakis, A. G.; Hatziargyriou, N. D. | 2008 | IEEE Trans. Energy Conversion, 23(1), 241-248 | [10.1109/TEC.2007.914686](https://doi.org/10.1109/TEC.2007.914686) | A | 摘要级 | used |
| ref-prob02-microgridcontrol-olivares-2014 | Trends in Microgrid Control | Olivares, D. E. 等 | 2014 | IEEE Trans. Smart Grid, 5(4), 1905-1919 | [10.1109/TSG.2013.2295514](https://doi.org/10.1109/TSG.2013.2295514) | A | 摘要级 | used |
| ref-prob02-bessmodels-rosewater-2019 | Battery Energy Storage Models for Optimal Control | Rosewater, D. M. 等 | 2019 | IEEE Access, 7, 178357-178391 | [10.1109/ACCESS.2019.2957698](https://doi.org/10.1109/ACCESS.2019.2957698) | A | 摘要级 | used |
| ref-prob02-aging-collath-2022 | Aging aware operation of lithium-ion battery energy storage systems: A review | Collath, N. 等 | 2022 | Journal of Energy Storage, 55, 105634 | [10.1016/j.est.2022.105634](https://doi.org/10.1016/j.est.2022.105634) | A | 摘要级 | used |
| ref-prob02-terminal-han-2025 | End-effect mitigation in renewable energy systems with energy storage using value function approximation of terminal energy level | Han, D.; Heo, S. | 2025 | Applied Energy, 401, 126785 | [10.1016/j.apenergy.2025.126785](https://doi.org/10.1016/j.apenergy.2025.126785) | A | 题录级 | used |
| ref-prob02-twostage-ma-2022 | Two-stage stochastic robust optimization model of microgrid day-ahead dispatching considering controllable air conditioning load | Ma, Y. 等 | 2022 | Int. J. Electrical Power & Energy Systems, 141, 108174 | [10.1016/j.ijepes.2022.108174](https://doi.org/10.1016/j.ijepes.2022.108174) | A | 题录级 | used |
| ref-prob02-milpdegr-minh-2024 | A mixed-integer linear programming model for microgrid optimal scheduling considering BESS degradation and RES uncertainty | Minh, N. Q. 等 | 2024 | Journal of Energy Storage, 104, 114663 | [10.1016/j.est.2024.114663](https://doi.org/10.1016/j.est.2024.114663) | A | 题录级 | used |
| ref-prob02-scuc-wu-2007 | Stochastic Security-Constrained Unit Commitment | Wu, L.; Shahidehpour, M.; Li, T. | 2007 | IEEE Trans. Power Systems, 22(2), 800-811 | [10.1109/TPWRS.2007.894843](https://doi.org/10.1109/TPWRS.2007.894843) | A | 摘要级 | used |
| ref-prob02-pvforecast-mayer-2021 | Extensive comparison of physical models for photovoltaic power forecasting | Mayer, M. J.; Gróf, G. | 2021 | Applied Energy, 283, 116239 | [10.1016/j.apenergy.2020.116239](https://doi.org/10.1016/j.apenergy.2020.116239) | A | 摘要级 | used |
| ref-prob02-decomposition-conejo-2006 | Decomposition Techniques in Mathematical Programming | Conejo, A. J. 等 | 2006 | Springer（教材） | [10.1007/3-540-27686-6](https://doi.org/10.1007/3-540-27686-6) | B | 题录级 | used |
| ref-prob02-storagevalue-sioshansi-2009 | Estimating the value of electricity storage in PJM: Arbitrage and some welfare effects | Sioshansi, R. 等 | 2009 | Energy Economics, 31(2), 269-277 | [10.1016/j.eneco.2008.10.005](https://doi.org/10.1016/j.eneco.2008.10.005) | A | 题录级 | used |
| ref-prob02-dayaheadintraday-xie-2021 | Greedy energy management strategy and sizing method for a stand-alone microgrid with hydrogen storage | Xie, Y. 等 | 2021 | Journal of Energy Storage, 44, 103406 | [10.1016/j.est.2021.103406](https://doi.org/10.1016/j.est.2021.103406) | A | 摘要级 | used |
| ref-prob02-eohe-alemany-2026 | Terminal energy valuation and end-of-horizon effects in battery arbitrage scheduling | Alemany, J. M. | 2026 | Academia Green Energy, 3 | [10.20935/acadenergy8488](https://doi.org/10.20935/acadenergy8488) | C | 摘要级 | **rejected** |

## 4. 关键来源的主张、适用条件与差异

- **ref-prob02-balancing-vanderveen-2016**：平衡市场是处理电力供需偏差的制度安排；其设计变量（偏差如何计价、惩罚强度、结算方向）与性能标准之间存在权衡。*适用*：prob02「日前计划量 + 实际供电不足按 5 倍电价结算」的机制定位。*差异*：批发市场机制设计视角，不含微网/储能模型，也不给出 5 倍乘子的依据。
- **ref-prob02-marketdesign-hu-2018**：综述欧盟市场设计中阻碍可变可再生并网的因素；主张双价不平衡结算、并把价格上限提高到失负荷价值(VOLL)。*适用*：把"供电不足的高价结算"合理化为一种惩罚性/可靠性定价，并提示用 VOLL 做量级对照。*差异*：面向欧盟批发市场；VOLL 的具体数值不可迁移，5 倍乘子仍属题面硬约束而非文献结论。
- **ref-prob02-trading-morales-2010**：日前决策 + 平衡偏差的两阶段交易可写成中等规模线性规划，偏差与平衡需求显式进入模型，并可在收益与风险间权衡。*适用*：prob02 的 $q$（日前计划）与 $u$（实时不足补救）两阶段结构可解性。*差异*：对象是风电生产商报价；本题紧急电价由题面固定。
- **ref-prob02-imbalance-bottieau-2020**：不平衡按规则价格结算，偏差有正负两个方向，结算规则决定参与者激励。*适用*：说明"偏差方向"与"结算价格"必须分别定义。*差异*：本题只对供电不足方向按 5 倍计价，属**不对称惩罚**，不能直接套用单一天平价格机制。
- **ref-prob02-loadshed-zeinalzadeh-2017 / ref-prob02-reliability-nojavan-2017 / ref-prob02-voll-leahy-2011**：微网中"向主网呈现的净负荷轨迹/计划"与"实际不足时的切负荷(未供电)"可分别建模，储能用于降低未供电与弃光风险；未供电有独立的经济价值(VOLL)，可靠性与费用可并列进入优化与评价。*适用*：prob02 中 $q_{d,t}$ 与 $u_{d,t}$ 的分离，以及"全年费用 + 紧急购电次数/电量"双指标口径。*差异*：前者目标为风险最小化并使用切负荷，本题改为**付费紧急购电**；后两者为容量规划，本题容量固定。
- **ref-prob02-voi-chazarra-2016**：以"完美信息价值"量化现货价格预测误差对储能调度收益的损失，并采用**日循环(daily-cycle)**边界。*适用*：A2（日循环 vs 连续跨日）与 A3（0:00 完美信息 vs 预报信息）两个待研究点的标准对照方法。*差异*：抽水蓄能 + 备用市场，非光伏-电池；不能迁移其数值。
- **ref-prob02-pvforecast-mayer-2021**：光伏功率预测的模型链选择会带来显著的精度差异（最优/最差模型链 MAE 相差约 13%、RMSE 约 12%、技能评分 23%–33%）。*适用*：说明"预测功率 ≠ 实际功率"，为 A3 的信息集讨论提供前提。*差异*：误差数值依赖站点与数据，不能当作附件 2/3 的误差量级。
- **ref-prob02-terminal-han-2025 / ref-prob02-bessmodels-rosewater-2019**：有限时域储能调度存在末端效应，终端能量价值/终端约束与循环边界都是标准处理手段；SOC 递推、效率与边界条件是储能最优控制模型的核心要素，建模选择会显著影响结果。*适用*：A2 跨日边界与终端储电量取值的论证依据；A14 效率/功率口径的模型地位。*差异*：Han 2025 仅题录级核验（出版方页面 403），只能用"边界处理影响结果"的定性主张；两文都不提供附录 1 的具体参数。
- **ref-prob02-twostage-ma-2022 / ref-prob02-dayaheadintraday-xie-2021**：微网"日前计划 + 日内/实时调度"的两阶段结构有明确先例，两阶段的信息集与目标不同。*适用*：prob02 的阶段划分，以及 prob03 的调整策略。*差异*：Ma 2022 为随机鲁棒且仅题录级；Xie 2021 为独立微网 + 氢储、由同一 MPC 滚动实施。
- **ref-prob02-scuc-wu-2007 / ref-prob02-decomposition-conejo-2006 / ref-prob02-milpdegr-minh-2024**：预测误差与随机扰动可用情景树/随机模型表示；长期大规模调度可用拉格朗日松弛、Benders 分解等分解为短期子问题；MILP 是微网调度的主流框架。*适用*：A5 关于 334 天 × 144 时段（48,096 个时段）规模可解性的讨论——若采用日循环边界则逐日天然解耦，不必引入复杂分解；否则需分解或情景削减。*差异*：Wu 2007 面向输电 SCUC，Conejo 2006 为通用教材，均不直接给出本题的解耦条件。
- **ref-prob02-ems-espin-2020 / ref-prob02-centralized-tsikalakis-2008 / ref-prob02-microgridcontrol-olivares-2014**：集中式 EMS/中央控制器是微网调度的主流架构，其目标函数与运行模型已有系统分类；并网模式下控制器优化与主网的功率交换（购电）以经济性为目标。*适用*：prob02 "每天 0:00 集中制定计划"的架构定位。*差异*：均为背景/分类性来源，不含紧急购电与 5 倍惩罚结构。
- **ref-prob02-aging-collath-2022**：老化应力会显著影响 BESS 经济性，忽略退化会高估收益/低估成本。*适用*：与 prob01 asm-10 一致的边界声明（本题无循环/老化数据，不建模退化）。*差异*：老化机理综述，不提供调度模型。
- **ref-prob02-storagevalue-sioshansi-2009**：储能价值可由全年逐时段价格下的套利优化估计，收益取决于价格时间结构与运行约束。*适用*：prob02 "逐日计划 × 全年 334 天"的评估口径先例。*差异*：批发市场套利与福利分析，不含紧急购电惩罚；仅题录级核验。

### 已否决候选

- **ref-prob02-eohe-alemany-2026（rejected）**：其 "末端效应(EOHE)" 概念与 A2 相关，但来源为 2026 年新刊（被引 0）、权威性不足以支撑关键假设，且同类概念已由 A 级 ref-prob02-terminal-han-2025 覆盖；按"关键假设原则上使用 A/B 来源"的要求不进入引用表，仅保留为后续检索线索。

## 5. 四类陈述的区分（本问证据边界）

**literature_fact（来源明确支持）**

- F1：电力平衡市场处理日前承诺与实际供需的偏差，偏差的结算规则与惩罚强度是市场设计的核心变量（ref-prob02-balancing-vanderveen-2016；ref-prob02-marketdesign-hu-2018）。
- F2：偏差（不平衡）有正负两个方向，其结算价格规则决定参与者的偏差激励（ref-prob02-imbalance-bottieau-2020；ref-prob02-trading-morales-2010）。
- F3：微网中"计划/净负荷轨迹"与"实际不足时的未供电"可以分别建模；储能用于降低未供电与弃光风险（ref-prob02-loadshed-zeinalzadeh-2017；ref-prob02-reliability-nojavan-2017）。
- F4：未供电（失负荷）有独立的经济价值(VOLL)，可用于对供电不足定价做量级对照（ref-prob02-voll-leahy-2011；ref-prob02-marketdesign-hu-2018）。
- F5：日前计划与日内/实时调度属于不同信息结构的两阶段问题，可写成线性/两阶段优化（ref-prob02-trading-morales-2010；ref-prob02-twostage-ma-2022；ref-prob02-dayaheadintraday-xie-2021）。
- F6：有限时域储能调度存在末端效应，终端能量价值/终端约束、循环边界与 SOC 递推/效率口径会显著影响结果（ref-prob02-terminal-han-2025；ref-prob02-bessmodels-rosewater-2019；ref-prob02-voi-chazarra-2016）。
- F7：光伏功率预测存在可观的模型间误差，预测值不等同于实际值（ref-prob02-pvforecast-mayer-2021）。
- F8：长期/大规模调度可用分解方法（拉格朗日松弛、Benders 等）求解，不确定性可用情景树表示（ref-prob02-scuc-wu-2007；ref-prob02-decomposition-conejo-2006）。
- F9：集中式 EMS 是微网调度的主流架构，并网模式下与主网的功率交换以经济性为目标优化（ref-prob02-ems-espin-2020；ref-prob02-centralized-tsikalakis-2008；ref-prob02-microgridcontrol-olivares-2014）。
- F10：忽略电池老化会高估储能运行收益/低估成本，须在边界中声明（ref-prob02-aging-collath-2022）。

**project_assumption（本题建立、需 assumption_definition 固定并在 sanity 中验证边界）**

- P1：0:00 制定计划时的信息集——按题面"利用当前数据尽可能精准地制定计划"，可将附件 2 的当日实际负载/光伏视为已知（完美信息口径）；该口径下 $u>0$ 只在物理不可行时出现，5 倍电价成为对不可行性的惩罚性成本 → 对应 **A3**，必须由 assumption_definition 显式固定。
- P2：跨日储能边界取**日循环**（每天 0:00 = 24:00 且 334 天共用同一初值口径）还是**连续**（前一天末状态为后一天初状态）→ 对应 **A2**；直接影响问题是否按日解耦，以及 2025-02-01 初值的设定（A10）。
- P3：供电不足的经济计量口径：紧急购电量按时段统计（表 4 的"日期 + 时间段 + 购电量"），且**只有不足方向**被惩罚（不对称惩罚），计划量本身按计划电价结算 → 对应 **A11**。
- P4：余电处理沿用 prob01 口径（弃光、不反送）→ 对应 **A4**；本问仍无文献能决定。
- P5：充放电互斥与 334 天规模的求解口径（真 MILP 逐日求解 vs 松弛 + 证明）→ 对应 **A5**，本阶段只提供"日循环可解耦/否则需分解"的依据。
- P6：不建模电池退化与容量衰减（与 prob01 asm-10 一致）→ 依据 F10，须在论文边界章节声明。

**agent_inference（由题面/数据/文献推导，待 formulation/computation 证实）**

- I1：若 A3 取完美信息且 A2 取日循环，则 334 天问题分解为 334 个互相独立的 144 时段 MILP，单日规模与 prob01 同量级，精确求解应可行；此推断需由 computation 的 solver status/gap 与逐日解耦的一致性检查证实。
- I2：5 倍紧急电价使 $u_{d,t}>0$ 成为"最后手段"；若物理可行域允许，最优解倾向用储能与（可能的）弃光调整规避紧急购电，但**不得预设** $u\equiv 0$，须由 computation 报告实际紧急购电量、时段与次数。
- I3：题面"其他时间段的购电费用均按计划购电量计算"意味着计划量 $q_{d,t}$ 是结算量而非实际取用量，计划高于实际需求的部分仍按计划电价付费；这会使"计划偏保守/偏激进"产生不对称经济后果，属口径推断，须在 formulation 明确并在 sanity 中检查。
- I4：A1 所涉"每天电价相同"与附件 1 代表日的关系（A13）仍是数据口径问题，文献不能裁决。

**team_decision（阶段内的阈值、口径与偏好选择，需记录理由）**

- D1：目标函数取"全年购电费用最小"（计划购电费 + 紧急购电费），是否在目标或约束中额外刻画紧急购电次数/未供电电量上限，由 assumption/formulation 阶段决定（依据 F3/F4，可靠性可作为并列指标）。
- D2：334 天的求解组织方式（逐日独立求解并统计，或整体长时段模型 + 分解）、求解器、容差与时限。
- D3：紧急购电量的最小记录阈值与四舍五入规则（表 4 格式），以及 |值| 噪声清零规则。
- D4：退化、弃光惩罚等题面未出现的项一律不进入主模型，作为 robustness/ablation 的对照变量（与 prob01 D3 一致）。

## 6. 生产的候选假设族与公式线索

1. **两阶段"计划—补救"主框架**：第一阶段（0:00）决定 $q_{d,t}, C_{d,t}, D_{d,t}, E_{d,t}$；第二阶段以实际负载/光伏计算不足量 $u_{d,t}$，目标 $\min \sum_d\sum_t (p_t q_{d,t} + 5 p_t u_{d,t})$（具体结算式待 formulation 固定）。证据：F1/F2/F5。
2. **供电平衡与不足变量的三种路线**：(a) 等式平衡 + 非负 $u$（不足即紧急购电）；(b) 不等式约束 + $u$ 松弛；(c) 引入弃光/余电变量后再取不足。对应 P3/P4，证据：F3。
3. **信息集族**：(a) 完美信息（附件 2 实际值已知）→ 确定性单阶段；(b) 仅用 0:00 可获得信息（预报/统计）→ 两阶段或鲁棒/随机。对应 A3，证据：F5/F7；先例 ref-prob02-voi-chazarra-2016。
4. **跨日边界族**：(a) 日循环 $E_{d,0}=E_{d,144}=E^{cyc}$；(b) 连续 $E_{d,0}=E_{d-1,144}$；(c) 终端约束 + 终端价值（残值）。对应 A2，证据：F6。
5. **规模与求解族**：(a) 日循环下逐日独立 MILP；(b) 连续边界下整体长时段 MILP + 分解（Lagrangian/Benders）或滚动时域。对应 A5，证据：F8。
6. **可靠性/评价指标族**：全年计划购电量与费用、紧急购电次数与电量、逐日峰值不足、未供电占负载比例。证据：F3/F4。

## 7. 待研究歧义的文献侧结论

| 歧义 | 文献侧结论 | 是否已可裁决 |
|---|---|---|
| A2 跨日储能边界 | 日循环边界是储能调度的常见设定（F6，Chazarra 2016）；有限时域边界处理会显著影响结果（Han 2025 题名级） | 否，属 project_assumption P2，须 assumption_definition 固定 |
| A3 0:00 信息集 | 日前/实时属不同信息结构，完美信息价值可量化（F5/F7）；但**不能**决定题面"尽可能精准"属哪一种 | 否，属 P1，本问核心待定点 |
| A4 余电处理 | 本问文献未见新依据；沿用 prob01 弃光口径（P4） | 否，维持 project_assumption |
| A5 互斥与全年规模 | 日循环可逐日解耦；否则可用分解方法（F8） | 部分，给出可解性路径，最终由 computation 证实 |
| A9 模板时间段标签偏移 | 属附件 5 模板与附件时间标签的口径问题，**无文献可援引** | 否，delivery 阶段处理 |
| A10 交付范围自 2025-02-01 起 | 属题面/附件约定，无文献依据 | 否，须数据口径说明 |
| A11 计量口径与紧急购电粒度 | 偏差结算的规则与方向必须显式定义（F1/F2）；本题只罚不足方向 | 部分，口径为 P3，须阶段内固定 |
| A13 附件 1 代表日含义 | 文献常用代表日/典型日做日前优化，但不能反推附件 1 的统计定义 | 否，数据口径问题 |
| A14 效率与功率口径 | 效率与边界条件是 BESS 模型核心，建模选择影响结果（F6） | 部分，沿用 prob01 口径并须在假设阶段固定 |

## 8. 引用闭合与交付

- 21 篇 used 来源已由 `scripts/automm/research.py:decide_reference` 同步写入 `problems/CUMCM2026-C/citations.yaml`，与 pool 的 `id` 一一对应；rejected 来源不进入引用表。
- 本轮 22/22 通过 Crossref 元数据核验（`verified: true`）；标注"题录级"的 7 条（leahy-2011、nojavan-2017、han-2025、ma-2022、minh-2024、conejo-2006、sioshansi-2009）只支撑题名级主张，**不得**用于支撑关键假设的定量内容。
- 后续 assumption 版本引用关键假设时，请使用"摘要级"来源：`ref-prob02-balancing-vanderveen-2016`、`ref-prob02-marketdesign-hu-2018`、`ref-prob02-trading-morales-2010`、`ref-prob02-imbalance-bottieau-2020`、`ref-prob02-voi-chazarra-2016`、`ref-prob02-loadshed-zeinalzadeh-2017`、`ref-prob02-ems-espin-2020`、`ref-prob02-centralized-tsikalakis-2008`、`ref-prob02-microgridcontrol-olivares-2014`、`ref-prob02-bessmodels-rosewater-2019`、`ref-prob02-aging-collath-2022`、`ref-prob02-scuc-wu-2007`、`ref-prob02-pvforecast-mayer-2021`、`ref-prob02-dayaheadintraday-xie-2021`。

## 9. 下一阶段建议

1. 进入 `assumption_definition`，优先固定 P1（A3 信息集）与 P2（A2 跨日边界）：这两条决定问题是"逐日确定性"还是"两阶段/连续"，也决定 334 天是否可逐日解耦；引用 ref-prob02-voi-chazarra-2016（日循环 + 完美信息价值）与 ref-prob02-terminal-han-2025（边界处理影响结果）。
2. 固定 P3（A11 计量口径与不对称惩罚）与 P4（A4 弃光），并明确 I3（计划量按计划电价结算）的口径；引用 ref-prob02-balancing-vanderveen-2016、ref-prob02-imbalance-bottieau-2020。
3. formulation 阶段给出 $u_{d,t}$ 的精确定义与目标函数中 5 倍电价的结算位置，禁止预设 $u\equiv 0$；由 computation 报告实际紧急购电量、时段与次数（对应 I2）。
4. 若 formulation 决定引入预报/不确定性（而非完美信息），应换随机/鲁棒术语重新开文献轮（本轮 F7/F8 只提供入口），不得复用本轮查询。
5. prob03（计划—调整违约结算）与 prob04（波动电价）的文献方向与本轮不同：prob03 需"上下调偏差结算/违约电价"证据，prob04 需"电价随机/鲁棒优化"证据，应分别更换术语与证据路径。
