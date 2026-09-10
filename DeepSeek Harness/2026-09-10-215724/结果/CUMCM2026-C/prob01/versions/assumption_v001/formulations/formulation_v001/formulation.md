# prob01 数学模型（formulation_v001）

> 版本：`formulation_v001`（candidate），绑定 `assumption_v001`（accepted）。
> 上游：`prob01/shared/problem_understanding.md`、`versions/assumption_v001/version.yaml`、`problems/CUMCM2026-C/global_symbols.yaml`、`prob01/shared/literature.md`、`request/problem.md` 与附录 1。
> 本文件在**未查看任何优化结果之前**写定；第 8 节的比较标准一经登记不得事后修改。
> 本动作只填写 Runner 为本次调用创建的 candidate 公式版本，不覆盖旧版本、题面、附件、文献与其他小问产物。

## 1. 范围与信息结构

- 建模对象：问题 1 的单日（附件 1 代表日）计划购电策略，144 个 10 分钟时段，末端 24:00。
- 决策时点：每天 0:00 一次决策（`asm-11`，静态日前信息结构），决策时已知当天全部 `price_t`、`load_t`、`pv_t`；日内不更新信息、不滚动重优化。
- 目标：在满足小区负载的前提下最小化全天购电费（题面"尽可能节省微网的购电费用"，`D1`）。
- 硬约束：供电不低于负载；储电量在 0:00 与 24:00 相同；储电量始终处于 1200~10800 kWh；充放电功率不超过 5000 kW；充放电效率 90%（`asm-02`、`asm-04`、`asm-05`、`asm-08`）。
- 余电口径：光伏余电以弃光处理、不向外部电网反送（`asm-03`）。
- 本问不引入随机性、预测误差与电池退化（`asm-01`、`asm-10`）。

## 2. 符号与单位（沿用全局符号表，不重新定义）

| 类别 | 符号 | 含义 | 单位 | 来源 |
|---|---|---|---|---|
| 索引 | $t$ | 10 分钟时段，$t=1,\dots,144$ | — | `global_symbols:t` |
| 索引 | $t=0$ | 当天 0:00 初始时刻 | — | 本问约定（初始状态） |
| 参数 | $dt$ | 时段长度 $1/6$ | h | `global_symbols:dt` |
| 参数 | $T$ | 时段数 144 | 个 | `global_symbols:T` |
| 参数 | $price_t$ | 时段 $t$ 电价 | 元/kWh | `global_symbols:price_t` |
| 参数 | $load_t$ | 时段 $t$ 负载功率 | kW | `global_symbols:load_t` |
| 参数 | $pv_t$ | 时段 $t$ 光伏发电（预测）功率 | kW | `global_symbols:pv_t` |
| 参数 | $Ecap$ | 储能最大容量 12000 | kWh | 附录 1 |
| 参数 | $Emin$ | 运行下界 1200 | kWh | 附录 1 |
| 参数 | $Emax$ | 运行上界 10800 | kWh | 附录 1 |
| 参数 | $Pmax$ | 最大充放电功率 5000 | kW | 附录 1 |
| 参数 | $Pbar$ | 单时段能量上限 $Pmax\cdot dt=833.3\overline{3}$（派生） | kWh | 本问派生，非新物理量 |
| 参数 | $\eta_{ch}$ | 充电效率 0.90 | — | `asm-04` |
| 参数 | $\eta_{dis}$ | 放电效率 0.90 | — | `asm-04` |
| 参数 | $E_0$ | 初始储电量 6000（全局符号 `E0`） | kWh | 附录 1 + `asm-02` |
| 决策 | $q_t$ | 时段 $t$ 计划购电量 | kWh | `global_symbols:q_t` |
| 决策 | $C_t$ | 时段 $t$ 充电量（并网点侧口径） | kWh | `global_symbols:C_t` |
| 决策 | $D_t$ | 时段 $t$ 放电量（并网点侧口径） | kWh | `global_symbols:D_t` |
| 决策 | $E_t$ | 时段 $t$ 末储电量 | kWh | `global_symbols:E_t` |
| 决策 | $curtail_t$ | 时段 $t$ 弃光量 | kWh | `global_symbols:curtail_t` |
| 决策 | $y_t$ | 充放电互斥 0-1 指示 | — | `global_symbols:y_t` |
| 指标 | $Q_{day}$ | 全天购电量 $\sum_t q_t$ | kWh | `global_symbols:Q_day` |
| 指标 | $Cost_{day}$ | 全天购电费 $\sum_t price_t q_t$ | 元 | `global_symbols:Cost_day` |

约定：时段 $t$ 对应区间 $\left(\frac{t-1}{6}\text{h},\ \frac{t}{6}\text{h}\right]$，故 $t=144$ 即当天 24:00；$E_t$ 是"时段末"储电量，$E_0$ 是 0:00 储电量。功率参数单位为 kW，电量决策单位为 kWh，两者只通过 $dt$ 换算（`asm-09`）。

## 3. 逐步推导

### 3.1 由功率平衡到时段能量平衡

微网并网点在时刻的功率平衡（单位 kW）：

$$
\underbrace{p^{buy}(t)}_{\text{购电}} + pv(t) + \underbrace{p^{dis}(t)}_{\text{储能放电}} = load(t) + \underbrace{p^{ch}(t)}_{\text{储能充电}} + \underbrace{p^{curt}(t)}_{\text{弃光}}
$$

题面要求"微网提供的电能不可低于小区负载"，等价于 $p^{curt}(t)\ge 0$ 且不引入切负荷变量（与 `ref-prob01-dayahead-silva-2020` 的切负荷/孤岛变量刻意区分，见 `problem_understanding.md` §3）。

10 分钟离散化（`asm-09`：时段内功率取平均值且视为恒定）后，令 $q_t=p^{buy}_t dt$、$C_t=p^{ch}_t dt$、$D_t=p^{dis}_t dt$、$curtail_t=p^{curt}_t dt$，对区间积分得**能量平衡**（kWh）：

$$
q_t + pv_t\,dt + D_t = load_t\,dt + C_t + curtail_t,\qquad t=1,\dots,144. \tag{B}
$$

移项即"供电 ≥ 负载"：$q_t+pv_t dt+D_t-C_t=\underbrace{load_t dt+curtail_t}_{\ge load_t dt}$。$q_t$ 只允许为正（只购不售），"反送"被 `asm-03` 排除，故不设售电变量。

### 3.2 储电量状态转移（效率口径）

并网点侧计量口径（`asm-05`）：$C_t$ 是从并网点取入储能的电量，$D_t$ 是储能送抵并网点的电量。连续时间储能能量守恒为 $\dfrac{dE}{dt}=\eta_{ch}\,p^{ch}(t)-\dfrac{p^{dis}(t)}{\eta_{dis}}$，在时段内取平均并积分得递推

$$
E_t = E_{t-1} + \eta_{ch} C_t - \frac{D_t}{\eta_{dis}},\qquad t=1,\dots,144. \tag{S}
$$

由 (S) 可知一个完整充放循环的并网点侧往返效率为 $\eta_{ch}\eta_{dis}=0.81<1$，即储能是**净耗能**环节，这与"套利收益来自峰谷价差"的经济机理一致（`asm-04`、`ref-prob01-arbitrage-grimaldi-2024`）。`asm-04` 与 `asm-05` 必须联动，本版本固定采用上式（并网点侧口径），电池侧口径仅作为 robustness 对照，两者不得混用。

### 3.3 容量、功率与边界条件

- 运行区间：$Emin\le E_t\le Emax$（$t=0,\dots,144$）。最大容量 $Ecap=12000$ 不作为运行上界（`asm-08`）。
- 变流器功率上界折算为能量上界：$0\le C_t\le Pbar$、$0\le D_t\le Pbar$（`asm-05`）。
- 终端条件：$E_{144}=E_0=6000$（`asm-02`：0:00 与 24:00 储电量相同，共同取附录 1 的 6000 kWh）。
- 弃光上界：$0\le curtail_t\le pv_t\,dt$（弃光不能超过该时段可用光伏电量）。

### 3.4 充放电互斥与线性化

物理上同一时段不能同时充放电：$C_tD_t=0$（`asm-06`，`ref-prob01-complementarity-garifi-2020`）。用 0-1 变量 $y_t$ 与大 $M$ 线性化：

$$
C_t \le Pbar\, y_t,\qquad D_t \le Pbar\,(1-y_t),\qquad y_t\in\{0,1\}. \tag{Y}
$$

**大 $M$ 推导**（不允许写"足够大的数"）：由 §3.3 有 $0\le C_t,D_t\le Pbar=833.3\overline{3}$ kWh。取 $M=Pbar$ 时，$y_t=1\Rightarrow D_t\le 0$、$y_t=0\Rightarrow C_t\le 0$，与可行域紧贴；任何 $M>Pbar$ 都只削弱松弛而不增加可行解，故 $M^\*=Pbar$ 是紧上界。

### 3.5 目标函数

$$
\min\ Cost_{day}=\sum_{t=1}^{144} price_t\, q_t. \tag{O}
$$

目标只含购电费用，不含退化、循环惩罚与弃光惩罚（`asm-10`、`D3`）；弃光收益为零，故弃光进目标不改变最优值（`asm-03`）。$Q_{day}=\sum_t q_t$ 是输出指标而非目标项。

### 3.6 主模型 M1（完整表达）

$$
\begin{aligned}
\text{(M1)}\quad \min_{q,C,D,E,curtail,y}\ & \sum_{t=1}^{144} price_t\,q_t\\
\text{s.t.}\quad
& q_t+pv_t\,dt+D_t-C_t-curtail_t=load_t\,dt && \forall t \tag{C1}\\
& E_t=E_{t-1}+\eta_{ch}C_t-\frac{D_t}{\eta_{dis}} && \forall t \tag{C2}\\
& Emin\le E_t\le Emax && \forall t \tag{C3}\\
& E_{144}=E_0=6000 && \tag{C4}\\
& 0\le C_t\le Pbar,\quad 0\le D_t\le Pbar && \forall t \tag{C5}\\
& C_t\le Pbar\,y_t,\quad D_t\le Pbar(1-y_t),\quad y_t\in\{0,1\} && \forall t \tag{C6}\\
& q_t\ge 0 && \forall t \tag{C7}\\
& 0\le curtail_t\le pv_t\,dt && \forall t \tag{C8}
\end{aligned}
$$

变量规模：连续变量 $5\times144=720$ 个，0-1 变量 144 个，等式约束 288 条，不等式约束约 720 条。$q_t$ 无上界（外网可无限供电），因此模型有界：$Cost_{day}\ge 0$，且 §7 给出可行解，故最优值存在。

## 4. 互斥约束的必要性分析（对应 open_item I1）

`assumption_v001` 的 I1 要求回答："在 $\eta<1$ 且电价非负时，去掉 (C6) 的 LP 松弛是否已隐含互斥"。本版本给出**条件性分析**而不是把文献的条件性结论当定理（`ref-prob01-complementarity-garifi-2020` 只给出保证同时充放电次优的特定条件）。

**（1）交换论证（可行方向）**：设某可行解在时段 $t$ 有 $C_t>0,D_t>0$，记 $m=\min(C_t,D_t)>0$。把 $C_t,D_t$ 同时减去 $m$：由 (C1)，$D_t-C_t$ 不变、$q_t$ 与 $curtail_t$ 可保持，**并网点侧平衡不受影响**；由 (C2)，$t$ 及之后所有 $E_{t'}$ 将增加

$$
\delta=m\left(\frac{1}{\eta_{dis}}-\eta_{ch}\right)=m\left(\frac{1}{0.9}-0.9\right)\approx0.2222\,m>0 .
$$

即"同时充放"等价于在不改变并网点净交换的前提下**烧掉**储能中的能量，其单位损失率为 $\bigl(\frac{1}{\eta_{dis}}-\eta_{ch}\bigr)$。因此同时充放不会有任何收益，只可能被用来"消耗多余能量"。而在本模型中多余能量总有更便宜的去处：光伏余电可零成本弃光（(C8)），已购电量则本就不应购买（$price_t\ge0$），终端 $E_{144}=E_0$ 的盈余可通过减少充电或增加放电在**不劣化目标**的前提下消除。故在本文的可行域结构下，同时充放不可能是"唯一最优"。

**（2）解层面的反例（LP 原始解不可直接采用）**：上面的论证只保证"存在"互斥最优解，不保证 LP 求解器返回的就是互斥解。随机小规模数值检查（见 `formula_validation.md` §8，共 6 470 个实例：$T=2..8$，$\eta\in\{0.9,0.9487,0.95\}$，$price_t\ge0$，含/不含 $curtail_t\le pv_t dt$ 两种变体）结果：

- LP 松弛最优值与含 (C6) 的 MILP 最优值在全部实例上一致（差 $<10^{-7}$），未发现"LP 严格更优"的反例；
- 但在若干**退化**实例中，LP 返回的原始最优解出现 $\min(C_t,D_t)>0$（同时充放），目标值与 MILP 相同。

**结论**：本问主模型**保留 0-1 与 (C6)**，不使用 LP 松弛解作为交付的 $C_t,D_t$；LP 松弛只作为下界与退化诊断（比较标准见 §8）。此结论针对本问可行域，不外推到其他小问；`robustness` 阶段可对"仅 LP 松弛 + 罚函数"路线做消融对照。

## 5. 候选模型与求解策略

按 `knowledge/optimization.md`：模型 formulation 与求解策略是两个层次，必须先固定候选与比较标准，不得按题号或算法流行度预先决定。

| 候选 | 结构 | 适用性判定 |
|---|---|---|
| **M1 确定性日前 MILP（主）** | 目标 (O) + 约束 (C1)~(C8)，144 个 0-1 | **采用**。问题小规模、线性、含与设备物理一致的互补约束；MILP 可给出全局最优与最优性 gap 证据（`ref-prob01-dayahead-silva-2020`、`ref-prob01-milp-tenfen-2015`、`ref-prob01-unitcommit-nguyenduc-2022`）。 |
| M2 LP 松弛（去 (C6)） | 同 M1，无 0-1 | 仅作**下界/退化诊断**。§4(2) 表明其原始解可能违反互斥，不可作为交付解；最优值可作 $Cost_{day}$ 的下界与 MILP 的交叉校验。 |
| M3 罚函数/凸松弛替代互斥 | 在目标加入 $-\epsilon\sum C_tD_t$ 或凸松弛 | **不采用为主模型**。其有效性依赖条件且需调参，且会改变题面目标（`ref-prob01-complementarity-garifi-2020` 明确为条件性结论）；必要时仅作为 robustness 对照。 |
| M4 电池侧计量口径 | $E_t=E_{t-1}+C_t-D_t/\text{（含 }\eta\text{ 的平衡式）}$ | **不采用为主模型**（与 `asm-05` 冲突）。留作 robustness 对照，检验 $Cost_{day}$ 对口径的敏感性。 |
| M5 随机/鲁棒优化、滚动 MPC、启发式、元启发式 | 场景集/不确定集/滚动重优化/启发式搜索 | **本问不适用**。问题 1 数据与预测均视为已知、无不确定性（`asm-01`、`asm-11`）；144 变量规模下精确求解成本远低于其收益；按 `knowledge/optimization.md`，不得为"高级算法"强行改造。 |

**求解器与参数（预先固定）**：Python `scipy.optimize.milp`（HiGHS 后端，`scipy>=1.11`；当前环境 1.18.1 已验证可用，`pulp` 未安装）。时限、容差、线程与 seed 由 implementation 阶段写入 task spec，且必须记录；建议 HiGHS 默认 MIP gap $10^{-4}$ 并在报告中同时给出 best bound 与实际 gap。若求解器状态非最优，按 `PASS_WITH_WARNING` 处理并保留 $mip\_gap$。

## 6. 为什么不需要更复杂的方法

- 无不确定性来源：问题 1 的电价、负载与光伏均给定且每天相同（题面 + `asm-07`）；引入随机规划/鲁棒优化缺乏不确定集证据。
- 无滚动信息更新：决策只在 0:00 发生（`asm-11`），MPC/滚动时域在问题 3 才有信息结构依据。
- 无黑箱/强非凸：目标线性、约束线性、仅 144 个 0-1，精确 MILP 的分支规模很小（`I2` 待 computation 证实）。
- 无多目标冲突：题面目标是单一购电费最小；$Q_{day}$ 只作为解释性输出。

## 7. 可解性证据（手工可行解）

无需优化即可构造一个可行解作为可行性证书：取 $C_t=D_t=0$、$y_t=0$、$E_t\equiv6000$，并令

$$
q_t=\max(load_t-pv_t,\,0)\,dt,\qquad curtail_t=\max(pv_t-load_t,\,0)\,dt .
$$

它逐时段满足 (C1)(C2)(C3)(C4)(C5)(C7)(C8)，故 M1 可行。按附件 1 数据（只读探针，见 `formula_validation.md` §6）：

- $Q_{day}=61789.9354$ kWh，$Cost_{day}=48052.0466$ 元，全天弃光 $6247.963$ kWh；
- 因此最优值满足 $Cost_{day}^\*\le48052.0466$ 元。

另由全天能量守恒 $\sum_t q_t=55541.9724+\sum_t curtail_t+0.19\sum_t C_t\ \ge\ 55541.9724$ kWh（推导见 `formula_validation.md` §4）与 $price_t\ge price_{\min}=0.3713$ 得 $Cost_{day}^\*\ge price_{\min}\times55541.9724=20622.7344$ 元。

## 8. 比较标准（计算前固定，不得事后修改）

**主指标（交付与论文）**

| 指标 | 定义 | 单位 | 期望/门禁 |
|---|---|---|---|
| $Cost_{day}$ | $\sum_t price_t q_t$ | 元 | 主目标；须落在 $[20622.73,\ 48052.05]$ |
| $Q_{day}$ | $\sum_t q_t$ | kWh | $\ge55541.97$；与 4 小时块合计自洽 |
| 弃光总量 | $\sum_t curtail_t$ | kWh | 验证 `I3`；若 $>0$ 须给发生时段与原因 |
| 表 1 指定时段购电量 | $q_{61},q_{73},q_{85},q_{97},q_{109},q_{121}$ | kWh | 与 result1.xlsx 同口径一致 |
| 表 2 块充放电量与端点储电量 | $\sum_{t\in T_b}C_t,\sum_{t\in T_b}D_t,E_0,E_{144}$ | kWh | $E_0=E_{144}=6000$ |

**可行性指标（硬门禁，任一违反即失败）**

- 功率平衡残差 $\max_t|q_t+pv_t dt+D_t-C_t-curtail_t-load_t dt|$（相对容差 $10^{-6}$）；
- 储电量边界残差（$Emin\le E_t\le Emax$）与终端残差 $|E_{144}-E_0|$；
- 变流器上限违反 $\max_t\max(C_t-Pbar,\,D_t-Pbar,\,0)$；
- 互斥违反 $\max_t\min(C_t,D_t)$，必须 $\le10^{-9}$；
- 非负性 $\min_t\min(q_t,curtail_t)\ge-10^{-9}$；
- NaN/Inf 计数为 0。

**求解质量指标**

solver status、termination reason、objective、best bound、MIP gap、迭代/节点数、运行时间、变量与约束规模、$M$ 的实际取值（应为 833.33）。

**模型比较指标（M1 vs M2）**

$Cost_{day}$ 差（LP 下界与 MILP 最优值之比）、LP 解 $\max_t\min(C_t,D_t)$、是否存在 LP 严格更优（必须为否）、LP 下界是否 $\le$ MILP 最优值（必须为是）。

**解释性与复现指标**

每个交付字段可回溯到唯一决策变量；代码 hash、输入文件 hash、`formulation_v001` content_hash、随机种子（本模型确定性，仍须登记）、求解器版本。

## 9. 交付口径与输出映射

- `Q_day = Σ q_t`（全天购电量）、`Cost_day = Σ price_t q_t`（全天购电费），对应表 1 末两行与 result1.xlsx。
- 表 1 指定时段按**物理区间**取：10:00-10:10→$t=61$；12:00-12:10→$t=73$；14:00-14:10→$t=85$；16:00-16:10→$t=97$；18:00-18:10→$t=109$；20:00-20:10→$t=121$。
- 表 2 的 4 小时块：0:00-4:00→$t=1..24$；4:00-8:00→$25..48$；8:00-12:00→$49..72$；12:00-16:00→$73..96$；16:00-20:00→$97..120$；20:00-24:00→$121..144$；块充电量 $=\sum_{t\in T_b}C_t$，块放电量同理。
- **时间标签口径（`asm-12`，歧义 A9）**：附件 1 标签为右端点（`0:00+1`$=24:00$）；附件 5 `result1.xlsx`「计划购电量」模板标签整体后移一个间隔（首行 `0:10-0:20`、末行 `0:00+1-0:10+1`）。填写规则为**按行序一一对应**（模板第 $t$ 行 $=$ 时段 $t$），交付时按 `0:00-0:10 … 23:50-24:00` 重写标签，禁止按标签字面逐行对齐；论文表 1 一律使用物理区间标签。

## 10. 局限与边界声明

1. `asm-02` 的终端储电量 6000 kWh 与 `asm-04`/`asm-05` 的效率-计量口径均属 project_assumption，缺少同设备实测来源；必须由 robustness 对 $E_0\in\{4800,6000,7200\}$ 及往返效率/电池侧口径做对照。
2. 不建模电池退化，会高估频繁充放电的经济性、使 $Cost_{day}$ 偏低，须在论文边界章节声明（`asm-10`）。
3. 忽略上网电价与反送（`asm-03`）：若存在正的上网电价，本模型会低估收益、高估购电费。
4. 附件 1 仅为代表日（`asm-07`），结论不外推全年；`asm-09` 把时段内功率视为恒值会平滑 10 分钟内的波动。
5. 本模型不含预测误差与紧急购电，问题 2~4 的结构不同，不得直接复用本版本结论。

## 11. 追溯表（关键公式 → 依据）

| 公式 | 依据 |
|---|---|
| (B) 能量平衡 | 题面"微网提供的电能不可低于小区负载"；`problem_understanding.md` §4；`ref-prob01-dayahead-silva-2020`（微网功率平衡结构，删除切负荷/孤岛） |
| (S) 状态转移 | 附录 1 效率 90%；`asm-04`、`asm-05`；`ref-prob01-arbitrage-grimaldi-2024`（恒定效率保持 LP/MILP）、`ref-prob01-storage-luo-2015`（效率量级核对） |
| (C3) 容量区间 | 附录 1（1200~10800 kWh）；`asm-08` |
| (C4) 终端条件 | 题面"0:00 和 24:00 的储电量相同"；`asm-02` |
| (C5) 功率上限 | 附录 1（5000 kW）与 $dt=1/6$；`asm-05` |
| (C6) 互斥与 big-M | `asm-06`；`ref-prob01-complementarity-garifi-2020`、`ref-prob01-complementarity-fortuny-1981`；$M=Pbar$ 由 (C5) 导出 |
| (O) 目标函数 | 题面"尽可能节省微网的购电费用"；`D1`；`ref-prob01-tou-modu-2025`（分时电价下充放时点为核心决策） |
| 弃光 (C8) | `asm-03`；`ref-prob01-dayahead-silva-2020`（curtailment 是日前调度的常规建模手段） |
| 单日/信息结构 | `asm-07`、`asm-11`；`ref-prob01-rolling-palma-2013`（静态日前与滚动重优化属不同信息结构） |

## 12. 待 computation 证实的开放项

- `I2`：144 个 0-1 的 MILP 应在小分支规模内给出可证最优；须报告 solver status、best bound 与 gap。
- `I3`：预期存在 $curtail_t\equiv0$ 的可行调度（附件 1 全天正余电 6247.96 kWh，单时段最大余电 352.92 kWh $<$ 833.33 kWh，余电集中在 $t=58..87$）。formulation 不预设该结论；computation 必须报告实际弃光总量，若 $>0$ 须给出时段与原因（如 SOC 达上界且充电功率受限）。
- LP 松弛与 MILP 的目标差在本问真实实例上的数值（按 §8 比较指标报告）。

## 13. 下游接口

本版本的模型、`formulation_v001` 的 content_hash、$Cost_{day}$/$Q_{day}$ 与充放电结构将作为 prob02 的基线（`dependency_graph.yaml` 的 prob01→prob02 软依赖）。prob02 引入紧急购电后，目标函数与结算结构必须重新建模，仅继承 (C1)~(C8) 的设备层结构与符号。
