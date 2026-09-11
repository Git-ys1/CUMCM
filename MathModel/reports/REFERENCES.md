# 参考文献检索与核验记录

- **论文**：2026 全国大学生数学建模竞赛 C 题《微网与外部电网电力调控策略》
- **目标文件**：`F:\AcademicHub\000资料相关\数模\26国赛\MathModel\paper\book.bib`
- **检索工具**：`mathmodel:paper-search` Skill（OpenAlex + Crossref 双引擎）
- **检索日期**：2026-09-11
- **最终收录**：**14 条**（英文 12 条 + 中文 2 条），全部经 DOI 核验

---

## 一、检索与核验流程

1. **检索候选**：对每个主题分别调用
   `python scripts/paper_search.py search --query "<方法名> <领域名>" --limit 6~10`
   两个引擎并行查询，按 DOI / 标题规范化后交叉验证合并。共发起 20 余次检索（含中文主题）。
2. **元数据核验**：`python scripts/paper_search.py verify --doi <DOI>`
   逐条核对作者、题名、年份、期刊、卷、期、页码。
3. **生成 BibTeX**：`python scripts/paper_search.py bib --doi <DOI> --key <引用key>`
   由 doi.org / Crossref 权威元数据反查生成，**无一条凭记忆手写**。
4. **回归复核（本轮新增）**：写盘后重新拉取全部 14 条的在线权威 BibTeX，与 `book.bib`
   逐字段机器比对（title / journal / volume / number / pages / year），结果 **ALL MATCH**。
   - 13 条 Crossref 注册文献字段完全一致；
   - 1 条中文文献（`liu2018dayahead`）Crossref 未收录，改用出版方页面人工核验（见第三节）。

### 写盘时的规范化处理（唯一的两处改动）

Crossref 的 BibTeX 转换会输出 HTML 实体与排版连字符，直接编译会在 PDF 中显示为
`&amp;`，因此在保留 skill 生成的字段结构前提下做了两处**等价**规范化：

| 原始输出 | 改为 | 涉及条目 |
|---|---|---|
| `&amp;` | `\&` | `wu2014dynamic`、`elkazaz2020energy` |
| 页码中的 `–`（U+2013） | `--` | 全部有页码区间的条目 |

其余字段（含 `author`、`volume`、`number`、`pages`、`year`、`publisher`、`ISSN`）逐字保留
Crossref 输出。回归复核脚本在比对前对上述两处做了反向归一化，因此仍能逐字段对齐。

---

## 二、最终收录的 14 条

引用位置列中的文件名相对 `MathModel/paper/texfile/`。

| # | 引用 key | 题名 | 期刊 | 年 | DOI | 核验 | 论文中的引用位置 |
|---|---|---|---|---|---|---|---|
| 1 | `wu2014dynamic` | Dynamic economic dispatch of a microgrid: Mathematical models and solution algorithm | International Journal of Electrical Power & Energy Systems | 2014 | 10.1016/j.ijepes.2014.06.002 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §公共线性规划内核（微网经济调度的数学模型与求解算法）；§问题一 模型建立 |
| 2 | `nemati2018optimization` | Optimization of unit commitment and economic dispatch in microgrids based on genetic algorithm and mixed integer linear programming | Applied Energy | 2018 | 10.1016/j.apenergy.2017.07.007 | ✓ Crossref 反查 + 回归一致 | `3ProblemAnalysis.tex` 问题一的分析；`5MakeModel.tex` §问题一（微网经济调度的 MILP 建模路线） |
| 3 | `luo2020optimal` | Optimal scheduling of a renewable based microgrid considering photovoltaic system and battery energy storage under uncertainty | Journal of Energy Storage | 2020 | 10.1016/j.est.2020.101306 | ✓ Crossref 反查 + 回归一致 | `3ProblemAnalysis.tex` 问题二的分析；`5MakeModel.tex` §问题二 信息集界定与建模难点（光伏+储能不确定性调度） |
| 4 | `silva2020optimal` | Optimal Day-Ahead Scheduling of Microgrids with Battery Energy Storage System | Energies | 2020 | 10.3390/en13195188 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §问题一 模型建立（含储能的日前调度基准） |
| 5 | `elkazaz2020energy` | Energy management system for hybrid PV-wind-battery microgrid using convex programming, model predictive and rolling horizon predictive control with experimental validation | International Journal of Electrical Power & Energy Systems | 2020 | 10.1016/j.ijepes.2019.105483 | ✓ Crossref 反查 + 回归一致 | `3ProblemAnalysis.tex` 问题三的分析；`5MakeModel.tex` §问题三 滚动优化框架（滚动时域 / MPC 建模依据） |
| 6 | `zhang2018robust` | Robust model predictive control for optimal energy management of island microgrids with uncertainties | Energy | 2018 | 10.1016/j.energy.2018.08.200 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §问题三 滚动优化框架（不确定性下的鲁棒滚动优化） |
| 7 | `wu2016solution` | A Solution to the Chance-Constrained Two-Stage Stochastic Program for Unit Commitment With Wind Energy Integration | IEEE Transactions on Power Systems | 2016 | 10.1109/tpwrs.2015.2513395 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §问题二 信息集界定与建模难点（两阶段随机规划形式化，支撑式 `eq:q2-two-stage`） |
| 8 | `qin2011newsvendor` | The newsvendor problem: Review and directions for future research | European Journal of Operational Research | 2011 | 10.1016/j.ejor.2010.11.024 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §问题二 风险定价：从 5 倍电价到 0.2 分位点（式 `eq:newsvendor` 报童模型临界分位点） |
| 9 | `polat2024renewable` | Renewable GenCo bidding strategy using newsvendor-based neural networks: An example from Turkish electricity market | Electric Power Systems Research | 2024 | 10.1016/j.epsr.2024.110301 | ✓ Crossref 反查（双引擎交叉验证）+ 回归一致 | `5MakeModel.tex` §问题二 风险定价（报童模型在电力市场竞价中的实际应用） |
| 10 | `markovics2022comparison` | Comparison of machine learning methods for photovoltaic power forecasting based on numerical weather prediction | Renewable and Sustainable Energy Reviews | 2022 | 10.1016/j.rser.2022.112364 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §问题二 光伏预测构造（式 `eq:pv-forecast` 基方法族选型）；§问题三 降尺度与偏差校正 |
| 11 | `wang2015review` | Review of real-time electricity markets for integrating Distributed Energy Resources and Demand Response | Applied Energy | 2015 | 10.1016/j.apenergy.2014.10.048 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §问题四 模型迁移（实时电价与需求响应机制） |
| 12 | `maheshwari2020optimizing` | Optimizing the operation of energy storage using a non-linear lithium-ion battery degradation model | Applied Energy | 2020 | 10.1016/j.apenergy.2019.114360 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §公共线性规划内核 约束 2（式 `eq:soc` 储能效率与状态递推）；`7ModelEvaluation.tex` 储能寿命/效率建模的简化讨论 |
| 13 | `liu2018dayahead` | 考虑氢能-天然气混合储能的电-气综合能源微网日前经济调度优化 | 电网技术 | 2018 | 10.13335/j.1000-3673.pst.2017.0966 | ⚠ 非 Crossref，出版方页面人工核验（见第三节） | `3ProblemAnalysis.tex` 问题一的分析；`5MakeModel.tex` §问题一（中文核心期刊的微网日前经济调度建模） |
| 14 | `sun2025distributionally` | 考虑光伏出力不确定性的分布鲁棒优化调度方法 | 激光与光电子学进展 | 2025 | 10.3788/lop241935 | ✓ Crossref 反查 + 回归一致 | `5MakeModel.tex` §问题二 信息集界定（光伏出力不确定性的处理路线）；`7ModelEvaluation.tex` 模型可扩展方向 |

主题覆盖核对：微网经济调度 ×2（#1 #2）｜含光伏储能的不确定性日前调度 ×2（#3 #4）｜
滚动时域/MPC ×2（#5 #6）｜两阶段随机规划 ×1（#7）｜报童模型与分位数预测 ×2（#8 #9）｜
光伏功率预测 ×1（#10）｜实时电价与需求响应 ×1（#11）｜储能运行优化 ×1（#12）｜
中文核心期刊 ×2（#13 #14）。

---

## 三、中文文献 `liu2018dayahead` 的核验说明（唯一一条非 Crossref 条目）

该 DOI 由 **中国 DOI 注册机构（chndoi.org / 同方知网）** 注册，**未在 Crossref 登记**，
因此 `verify` 与 `bib` 子命令均返回 404：

```
[error] Crossref 无此 DOI：10.13335/j.1000-3673.pst.2017.0966。禁止引用未核验文献。
```

通过 `https://doi.org/10.13335/j.1000-3673.pst.2017.0966` 直接解析，返回 CNKI 的
多重解析页面，可确认**题名与作者**与该 DOI 绑定：

- 题名：考虑氢能-天然气混合储能的电-气综合能源微网日前经济调度优化
- 作者：刘继春; 周春燕; 高红均; 郭焱林; 朱雨薇

该解析页**未给出**卷、期、年、页码，故另行核对以下独立来源：

| 字段 | 取值 | 来源 |
|---|---|---|
| 期刊 | 电网技术（Power System Technology） | CNKI `DWJS201801022`；万方 `dwjs201801022`；维普 `674291029` |
| 年 / 期 | 2018 年 第 1 期 | CNKI 手机版「电网技术2018年01期」页面 |
| 卷 | 42 | 电网技术官网条目页、CNKI 条目页 |
| 页码 | 170–178 | 文章编号 **1000-3673(2018)01-0170-09** —— 起始页 `0170`、共 `09` 页，自洽 |
| DOI | 10.13335/j.1000-3673.pst.2017.0966 | doi.org 解析确认 |

即卷、期、页码三项由**文章编号编码**（`1000-3673(2018)01-0170-09`）与多个数据库页面
互相印证，未作任何推测。若评审环节发现该条难以核验，可直接删除
`book.bib` 中的 `liu2018dayahead` 条目，其余 13 条不受影响。

---

## 四、检索失败 / 被剔除的条目

### 4.1 引擎与核验失败

| 对象 | 情况 | 处置 |
|---|---|---|
| Carøe & Schultz, *A Two-Stage Stochastic Program for Unit Commitment Under Uncertainty in a Hydro-Thermal Power System* | OpenAlex 命中但**无 DOI** | 剔除（无法核验） |
| `10.1016/j.est.2019.101183` | Crossref 题名带 **RETRACTED** 前缀（撤稿） | 剔除 |
| `10.1016/j.ijhydene.2023.04.091` | Crossref 题名带 **RETRACTED** 前缀（撤稿） | 剔除 |
| 中文检索（`微网 经济调度 储能`、`分时电价 需求响应`、`储能 荷电状态 调度` 等） | OpenAlex/Crossref 对 CNKI 覆盖有限，返回结果多为 `数据期刊`、`工程建设`、`水利电力技术与应用` 等**非核心/掠夺性期刊** | 全部剔除，未采用 |

### 4.2 已通过核验但因 14 条上限未收录（备用条目，可直接追加）

这些条目**均已 verify 通过**，若需扩充参考文献可直接取用：

| 引用 key（建议） | 题名 | 期刊 / 年 | DOI |
|---|---|---|---|
| `pinson2013wind` | Wind Energy: Forecasting Challenges for Its Operational Management | Statistical Science, 2013, 28(4) | 10.1214/13-sts445 |
| `theocharides2020day` | Day-ahead photovoltaic power production forecasting methodology based on machine learning and statistical post-processing | Applied Energy, 2020, 268 | 10.1016/j.apenergy.2020.115023 |
| `mena2023multiobjective` | Multi-objective two-stage stochastic unit commitment model for wind-integrated power systems: A compromise programming approach | IJEPES, 2023, 152 | 10.1016/j.ijepes.2023.109214 |
| `oconnor2025quantile` | Optimising quantile-based trading strategies in electricity arbitrage | Energy and AI, 2025, 20 | 10.1016/j.egyai.2025.100476 |
| `guo2022evaluating` | Evaluating effects of battery storage on day-ahead generation scheduling of large hydro–wind–photovoltaic complementary systems | Applied Energy, 2022 | 10.1016/j.apenergy.2022.119781 |

> `pinson2013wind` 与论文问题二的「报童最优分位点」结论契合度最高，如需替换
> `sun2025distributionally` 可优先考虑它。

### 4.3 检索中发现但主题不符、未采用的典型结果

- 大量 *economic load dispatch* 类文献使用粒子群 / 鲸鱼 / 飞蛾扑火等**元启发式**算法，
  与本文的线性规划内核（HiGHS 精确求解）方法路线不符，未采用。
- 氢能、气电耦合、电动汽车 V2G、碳交易等方向的微网调度文献与本题边界不符，未采用。
- `10.1016/j.apenergy.2022.119781`（水-风-光互补）含水电，与本题「光伏+储能+外网」边界不符，
  虽通过核验仍列为备用而非正式条目。

---

## 五、可复现命令

```bash
SKILL="C:/Users/yusu/AppData/Roaming/@mathmodel/desktop/skills-plugin/skills/paper-search/scripts/paper_search.py"

# 检索
python "$SKILL" search --query "microgrid economic dispatch scheduling optimization" --limit 6 --year-from 2012
python "$SKILL" search --query "model predictive control microgrid energy management" --limit 6
python "$SKILL" search --query "newsvendor problem" --limit 10

# 核验
python "$SKILL" verify --doi 10.1016/j.ijepes.2014.06.002

# 生成并追加条目
python "$SKILL" bib --doi 10.1016/j.ijepes.2014.06.002 --key wu2014dynamic
```

回归复核脚本（临时文件，不随项目交付）：
`C:\Users\yusu\AppData\Local\Temp\verify_bib_roundtrip.py`

---

## 六、注意事项

1. **年份口径**：`book.bib` 中的 `year` 取自 Crossref 的正式出版年（与卷号绑定），
   可能与 OpenAlex 的「在线首发年」相差一年。例如 `nemati2018optimization` 在线首发
   2017，正式卷期为 Applied Energy **2018**, 210: 944–963；引用时请以 `book.bib` 为准。
   `qin2011newsvendor` 同理（DOI 中含 `2010`，正式出版年为 **2011**）。
2. **`\nocite{*}`**：`texfile/8Reference.tex` 目前使用 `\nocite{*}` 输出全部条目，
   正式论文建议删除该行并改用正文 `\cite{}`，否则 14 条会全部出现在参考文献表中。
3. **编译环境**：本机未检测到 `xelatex` / `kpsewhich`，因此**未能实际编译验证**
   gbt7714-numerical 的排版结果。已确认 `book.bib` 结构为 Crossref 标准字段
   （`journal` / `volume` / `number` / `pages` / `year` / `author`），并对 `&` 与页码
   连字符做了 LaTeX 安全处理；两条中文条目加了 `language = {zh}` 以便 gbt7714 正确
   输出「等」与中文标点。建议在装有 CTeX/TeX Live 的环境编译一次确认。
