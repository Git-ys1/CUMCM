# 论文评审（V5 · 仅源文本审查版）

**总评**：**良好，文字重写本身成功，但合并前必须先处理一项 P0**——文献引用体系从 14 条坍缩到 1 条（"研究现状综述"整节被删）。除此之外，V5 的叙事质量、数值一致性、宏与交叉引用全部核验通过，是四版中文字可读性最好的一版。

> 审查对象：`论文迭代/V5/texfile/1abstract.tex` ~ `7ModelEvaluation.tex`（网页端 GPT 撰写的重写稿，将覆盖合并到 V4.1 工程）。
> 审查方式：**仅源文本静态审查，未编译 PDF**（按约定，编译由 WorkBuddy 侧执行）。核对范围：题面事实、`numbers.tex` 全部宏定义、`generated/*.tex` 与保留文件的标签、附件 2 原始数据复算、V4 评审遗留问题逐条复查。
> 未修改任何文件。

---

## 评分

| 维度 | 分数 | 评语 |
| --- | --- | --- |
| 摘要 | 9/10 | 四问"方法—数值—结论"完整且表述克制（"低分位启发"不再声称全局最优）；扣分点是一处破折号排版（见问题 2）。 |
| 问题分析与假设 | 7/10 | 主线叙事清晰、11 条假设全部可追溯；但删除了 V4.1 的"研究现状综述"，导致全文几乎不再引用文献（P0）。 |
| 模型建立与求解 | 8/10 | 全部建模内容保留且动机化重写：结算口径、MILP 互斥、配对控制、计划持续性均表述正确；仍有 11 个公式/节标签未被正文引用（见问题 4）。 |
| 结果与可信度 | 8/10 | 所有数值均走宏引用，无手工抄数；三项费用恒等式与配对分解在数值上严格成立；V4.1 的"历史配置回归比对表"被删除（见问题 5）。 |
| 图表 | 8/10 | 8 幅图引用与图内子图编号全部对应（已核对 `fig_data.py` 面板结构）；但结算口径对比图与技术路线图未纳入（见问题 3）。 |
| 格式与规范 | 6/10 | 无编译级错误（`$` 配对、宏、标签全通过）；但参考文献将从 14 条坍缩为 1 条，破折号 `--` 混入中文正文 5 处。 |
| **合计** | **46/60** | |

**致命项：无**（四问均有结果、数值与宏/工作簿一致、无编造引用——因为几乎只剩 1 条引用了，见问题 1）。

---

## 已核验通过的清单（GPT 修改时请勿触碰）

以下项经独立复算/比对全部正确，**修改其他问题时不要连带改动**：

1. **宏解析**：7 个文件使用的全部 `\Qone* / \Qtwo* / \Qthree* / \Qfour* / \Delta* / \PvQuant* / \Corr* / \Sens*` 宏在 `numbers.tex` 中全部有定义（含新增的 `\CorrNetLoad=-0.1140`、`\CorrNetPv=-0.8796`、`\QthreeDownCost=24867.42`、`\QthreeUpCost=909599.29`）。
2. **交叉引用**：合并后（V5 七文件 + `generated/*` + `8AIUsageStatement/8Reference/9Appendix`）**零个未解析引用**。
3. **数据事实**（本人用附件 2 原始工作簿复算）：全年负载电量 40.5241×10⁶ kWh（文中 40.52 ✓）、光伏电量 20.2512×10⁶（20.25 ✓）、光伏>负载占比 19.2732%（19.27% ✓）、富余超 5000 kW 时段 241 个（✓）。
4. **数值恒等式**：12 640 688.81 + 934 466.71 + 342 247.67 = 13 917 403.19 ✓；24 867.42 + 909 599.29 = 934 466.71 ✓；配对分解三行各自左右相等 ✓；`\QoneSlotTen/Fourteen/Twenty = 0.00` 与"10:00、14:00、20:00 购电为零"表述一致 ✓。
5. **V4 评审遗留项复查**：`ightarrow` 宏损坏已消失、重复段落已消失、`\noindent` 顶格已消失、"未来信息穿越"已消失、评阅要点/红字已消失、相关系数与 MAE 表述已更正（0:00 最小）、4500 kW 与 12 MWh 单位已订正、0.307% 已订正——**V4 的 8 条问题在本稿中零复现**。
6. **结算手算例**（6ErrorAnalysis:41）：叠加 900+0.5×200=1000、差额 700+0.5×200=800、上调两种口径均 700+1.5×200=1000——全部正确。
7. **图-文对应**：`fig:data-overview` 确为 4 面板，文中 (a)/(b)(c) 引用成立；`fig:dispatch-0621` 的 (a)(c)/(d)/(b) 引用成立；其余图均未带面板号引用，无错位风险。

---

## 问题清单（按对得分的影响排序）

1. **[格式/规范 · P0] 文献引用从 14 条坍缩到 1 条，"研究现状综述"整节被删** — `2ProblemRestatement.tex`（V5 版无此节）；V5 七个文件合计仅 `7ModelEvaluation.tex:20` 一处 `\cite{liu2018dayahead}`
   - 现状：V4.1 的 `2ProblemRestatement.tex:21` 有"研究现状综述"小节（两段，含 `\cite{wu2014dynamic,nemati2018optimization}` 等 10 处引用），V5 重写时整体丢弃；`5MakeModel.tex` 中报童分位（V4.1 的 `\cite{qin2011newsvendor}`）、滚动 MPC（`\cite{elkazaz2020energy,silva2020optimal}`）等原有引注也全部消失。合并后 `\bibliography{book}` 的 14 条 DOI 核验文献将只剩 1 条出现在参考文献列表，其余 13 条全部丢失。
   - 影响：2026 规范第七条（引用他人成果须标注）；更重要的是竞赛论文没有文献综述会显得理论基础单薄——而 V4.1 已经把 14 条真实文献做齐了，这属于"把已经修好的东西又删掉"。
   - 改法（合并前必须完成）：
     - **回填研究现状综述**：从 `MathModel/paper/texfile/2ProblemRestatement.tex` 的 `\subsection{研究现状综述}` 整节（含两段文字与全部 `\cite`）复制到 V5 的 `2ProblemRestatement.tex`，插在"问题提出"之后，并可按 V5 文风微调（原文字已是学术语气，无需大改）；
     - **恢复正文行内引注**：`5MakeModel.tex` 报童分位段（约 236–244 行，`0.2` 分位结论处）加 `\cite{qin2011newsvendor,polat2024renewable}`；问题三滚动结构段（约 331 行）加 `\cite{elkazaz2020energy,silva2020optimal}`；光伏预测方法处可加 `\cite{markovics2022comparison}`；问题四或综述里保留 `\cite{wang2015review}`；
     - 验收：合并后全文 `\cite` 总数 ≥ 10，参考文献列表条目与 `book.bib` 对应。
   - 注意：这些 bib key 全部真实存在（`reports/REFERENCES.md` 有 DOI 核验记录），直接使用即可，不要新建文献。

2. **[格式] 中文破折号写成 ASCII `--`（5 处）** — 中文语境应使用 `——` 或 LaTeX 中直接输入全角破折号 `—`
   - 位置：`1abstract.tex:7`"费用--储能吞吐量--弃光量"；`5MakeModel.tex:225`"负载--光伏"；`5MakeModel.tex:447`"成本--收益比较"；`7ModelEvaluation.tex:16`"负荷--光伏"；`7ModelEvaluation.tex:20`"公共物理约束--信息分层--滚动修正"。
   - 改法：这 5 处 `--` 全部改为 `—`（全角破折号，前后不加空格）。**注意区分**：时间区间（`0:00--6:00`、`10:00--10:10`）和表头的 `---` 是正确用法，不要改。

3. **[图表] 两幅既有图未纳入正文** — 合并后它们将成为 `figures/` 目录中的孤立文件
   - 现状：① V4.1 的"两种结算口径分别重优化的对比"图（`figures/q3_settlement.pdf`）在 V5 中无引用，replace 口径只剩两句文字带过（`5MakeModel.tex:363、479`）；② 技术路线图（`figures/technical_route.pdf`）自 V4 起就未恢复，V5 的"总体思路"仍只有一句文字描述（`3ProblemAnalysis.tex:7`）。
   - 改法（二选一，不要都不做）：
     - **方案 A（推荐）**：在 `5MakeModel.tex` 结算小节（`eq:settle-rep` 之后）补一张图：`\includegraphics[width=0.98\textwidth]{figures/q3_settlement.pdf}`，配图注"两种结算口径分别重优化的全年费用对比"，并补一句"图 X 表明两种口径的绝对费用不同但'新增节点有价值'的方向一致"；技术路线图放回 `3ProblemAnalysis.tex` 总体思路段（`\includegraphics[width=\textwidth]{figures/technical_route.pdf}`），**注意这会推高正文页数，需在别处压缩约半页**（合并后由 WorkBuddy 编译时观察页数再决定）；
     - **方案 B**：明确放弃两图，则把 `figures/q3_settlement.pdf`、`figures/technical_route.pdf` 从工程中移除，避免留下未使用文件。

4. **[模型] 11 个公式/节标签定义了却从未被正文引用** — `5MakeModel.tex`、`6ErrorAnalysis.tex`、`7ModelEvaluation.tex`
   - 现状：`eq:nonneg`、`eq:newsvendor`、`eq:pv-residual`、`eq:pv-forecast`、`eq:pv-score`、`eq:q3-nodes`、`eq:q3-paired-value`、`eq:q3-value-result`、`eq:q3-cost-decomposition`、`eq:q4-roll-value`、`sec:settlement`、`sec:validation`、`sec:terminal`、`sec:efficiency`、`sec:improve`（后四个是章节标签，问题较小）。其中 `eq:q3-value-result` 与 `eq:q3-cost-decomposition` 承载了全文最重要的两个结论，却只靠表外文字复述。
   - 改法（挑重点做，不必全做）：在 `5MakeModel.tex:437`"各节点的边际价值为"后补 `\eqref{eq:q3-value-result}`；在 `:473`"主方案全年总费用可回代为"处把等式与 `\eqref{eq:q3-cost-decomposition}` 直接绑定；`:397` 处给 `\eqref{eq:q3-paired-value}` 一个引用；报童分位处（`:244`）引用 `\eqref{eq:newsvendor}`。

5. **[结果] "历史配置回归比对表"随内部叙事被整体删除** — `6ErrorAnalysis.tex`（V5 无此小节）
   - 现状：V4.1 的 `tab:regression`（修订前后五组数值 <10⁻³ 偏差）被当作"legacy 内部叙事"删除。回归复现是"修改未破坏既有结果"的唯一直接证据，竞赛评阅中属于加分项。
   - 改法：在 `6ErrorAnalysis.tex` 结算一致性小节后恢复一个小节"历史配置的复算一致性"，用学术措辞重写一句（如"为确认本文修订未改变历史参数组合下的结论，在前序配置的参数集下重算四问，费用相对偏差均小于 $10^{-3}$ 元"）+ 恢复该表。表体可从 V4.1 的 `6ErrorAnalysis.tex:64-82` 直接取（表内是硬编码数字，与 `MODEL_AUDIT_V4.md` 表 F 一致）。若坚持不放回，则必须同步删掉摘要/正文中任何"回归测试"字样（当前 V5 摘要已无此表述，一致性尚可）。

6. **[图表] 两处小瑕疵（顺手改）**
   - `1abstract.tex:7` 与 `5MakeModel.tex:160`："三层词典序目标"在两个文件里的写法分别是"费用--储能吞吐量--弃光量"（问题 2 已含）与正文一致，无需改；
   - `2ProblemRestatement.tex:13-19`：`\indent\textbf{问题一：}` 系列写法可用，但"问题一：…"与 `3ProblemAnalysis.tex` 的"问题一：…"格式一致 ✓；唯一建议是把重述里的"四个指定日期"补上具体日期（`2025-03-20、2025-06-21、2025-09-23、2025-12-21`），与生成表格呼应。

---

## 给合并/编译环节的交接注记（给 WorkBuddy 与 GPT 参考）

- 合并方式按 `V5_改稿说明.md` 第 4 节执行（仅覆盖 7 个 texfile），`document.tex`、`numbers.tex`、`generated/`、`figures/`、`8AIUsageStatement.tex`、`8Reference.tex`、`9Appendix.tex` 一律不动。
- V5 的 7 个文件经 `$` 配对扫描全部为偶数，LaTeX 环境与花括号在写稿说明中已声明成对；本审查未发现新的编译级风险。
- 合并后请重点目检：正文页数（V5 比 V4.1 文字略增，若放回技术路线图必然越 30 页，需提前想好压缩位置——建议优先压缩附录代码清单的注释空行）、宽表分页（12 张 `resizebox` 日期表未变）、图 3 与图 4 的浮动位置。
- 本审查未编译、未运行任何求解代码；所有数值结论均来自宏定义与工作簿静态比对，无需重算。

---

## 与既往评审的关系

| 审查 | 结论 |
| --- | --- |
| V4 评审（`review-V4.md`，50/60）的 8 条问题 | V5 已修复 7 条（宏损坏、重复段落、式号引用部分修复、单位、相关性、MAE 表述、附录 report.py 未涉及）；**未修复：技术路线图缺失（第 3 条）、公式未被引用（第 8 条，从 21 个减到 11 个）** |
| 本审查新发现 | P0：文献引用坍缩（14→1）+ 研究现状综述被删；`--` 破折号 5 处；q3_settlement 图失联；回归表删除 |
