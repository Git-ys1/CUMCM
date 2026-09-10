# prob02 图表视觉复核报告

- problem_id: CUMCM2026-C
- question_id: prob02
- assumption_version: `assumption_v001`（accepted）
- formulation_version: `formulation_v001`（accepted）
- task_id: `ea71568e2cf6c5326ded`（权威计算结果，succeeded，rc=0）
- sanity 前置：L1–L4 = PASS_WITH_WARNING（sanity_check 阶段已独立复核，85 项检查 0 失败）
- 生成脚本：`problems/CUMCM2026-C/prob02/versions/assumption_v001/figures/generate_prob02_figures.py`
- 生成与复核动作：`act-bed04bf56bb54db9`（visualization 阶段，policy P5）
- 复核时间：2026-09-10（UTC）

## 1. 输入与追溯

图表只读取接受版本的计算交付，未修改任何原始数据、模型或上游版本：

| 输入 | 路径 | 用途 |
|---|---|---|
| 最优解 | `.../results/prob02_m1_formulation_v001/solution.csv`（48096 行） | 全部时序、热力图、曲面与交付口径图 |
| 逐日指标 | `.../daily_metrics.csv`（334 行） | 逐日费用、弃光、紧急购电与求解状态 |
| 紧急购电分段 | `.../emergency_segments.csv`（1919 行） | 分段数与分段能量核对 |
| 指标与残差 | `.../metrics.json` | 年度指标、残差、gates、key_dates、LP 对照、解析界 |
| 求解质量 | `.../solver_status.json` | 求解状态、最优天数、max mip_gap、规模、种子 |
| 交付模板 | `.../result2.xlsx`（3 表） | 计划购电量表、充放电量表、紧急购电量表口径核对 |

`figures.yaml` 中每张图登记了 6 个输入文件的 sha256（`source_hashes`）、稳定 ID、脚本路径、版本与 caption，可完整回溯到输入与代码。

## 2. 统一样式

- 字体：`Microsoft YaHei`（配置首选，环境已探测可用）；信息面板使用 `NSimSun`（中文等宽，避免方框字符）。
- 色板：primary `#1F4E79`、secondary `#70AD47`、accent `#ED7D31`、neutral `#7F8C8D`、warning `#C00000`；色板两两最小 RGB 距离 **78.8**（阈值 40）。
- DPI 180、PNG、白底；图幅按 `config/visualization.yaml` 的 10×6 in 基线按面板数扩展。

## 3. 图表清单（均登记于 `problems/CUMCM2026-C/figures.yaml`，`included_in_summary=true`）

| slug | stable_id | 标题 | 分辨率 | 自动质检 | 视觉审计 |
|---|---|---|---|---|---|
| daily_cost_timeline | prob02_fig_daily_cost_timeline_50a9548c6f | 全年逐日费用构成（计划购电费与紧急购电费，334 天） | 2136×1164 | passed | passed（文本 22；重叠 0；缺字 0；裁切 0） |
| monthly_cost_stack | prob02_fig_monthly_cost_stack_761697d6ee | 月度费用构成与紧急购电费占比 | 2028×1344 | passed | passed（文本 55；重叠 0；缺字 0；裁切 0） |
| emergency_vs_shortfall | prob02_fig_emergency_vs_shortfall_77bce4105a | 紧急购电量与预报缺口的关系（散点、上界参照与占比分布） | 2287×1054 | passed | passed（文本 46；重叠 0；缺字 0；裁切 0） |
| curtail_plan_vs_act | prob02_fig_curtail_plan_vs_act_23932d4781 | 计划层弃光与执行层弃光的对照（月度分块与逐日散点） | 2311×1057 | passed | passed（文本 62；重叠 0；缺字 0；裁切 0） |
| key_dates_execution | prob02_fig_key_dates_execution_c82eafd470 | 四个关键交付日期的执行层分解（q、u、κ_act 与 E） | 2390×1505 | passed | passed（文本 90；重叠 0；缺字 0；裁切 0） |
| delivery_audit | prob02_fig_delivery_audit_444465cebd | result2.xlsx 交付口径核对（指定时段购电量、4 小时块充放电量与标签映射） | 2411×1732 | passed | passed（文本 95；重叠 0；缺字 0；裁切 0） |
| annual_cost_composition | prob02_fig_annual_cost_composition_d335daf2b4 | 年度费用与电量构成、解析界与求解质量诊断 | 2496×1093 | passed | passed（文本 35；重叠 0；缺字 0；裁切 0） |
| emergency_heatmap_2d | prob02_fig_emergency_heatmap_2d_68cd24fd83 | 全年逐时段紧急购电量热力图（334 天 × 144 时段） | 2020×1129 | passed | passed（文本 34；重叠 0；缺字 0；裁切 0） |
| emergency_surface_3d | prob02_fig_emergency_surface_3d_5bbc32f933 | 紧急购电量时空三维曲面（日序 × 时刻 × 紧急购电量） | 1602×1385 | passed | passed（文本 33；重叠 0；缺字 0；裁切 0） |
| residual_diagnostics | prob02_fig_residual_diagnostics_a6159fa4ae | 结果可信度：12 类硬约束回代残差与求解质量 | 2349×1171 | passed | passed（文本 26；重叠 0；缺字 0；裁切 0） |

每张图回答一个明确问题，功能互补、不重复表达同一信息：全年费用结构与月度分解 → 紧急购电的成因（预报缺口）→ 弃光的两个层次 → 关键日期执行层细节 → 交付模板口径 → 年度构成与解析界 → 时空分布（二维热力图 + 三维曲面）→ 可信度诊断。

## 4. 视觉审计方法

本环境最终响应模型不支持图像输入（`read_image` 明确返回“模型不支持图像输入”），无法进行像素级人工目检。因此视觉复核以**可复现的程序化审计**完成，审计脚本与图表脚本同源（`audit_figure`），逐图结果写入 `visual_review.json`：

1. **CJK 字形覆盖**：用 `FT2Font.get_charmap()` 按每个文本 artist 实际使用的字体族逐字符检查，缺字即失败；渲染阶段另捕获 matplotlib `Glyph ... missing from font` 警告，出现即失败（防止方框字符静默通过）。
2. **文本裁切/越界**：所有可见文本（标题、轴标签、刻度、图例、注释、信息面板）的窗口包围盒必须落在画布内（容差 2 px）；三维坐标轴超出视图范围的刻度标签先按 `get_view_interval()` 过滤（未实际绘制）。
3. **文本重叠**：两两计算包围盒交集，较小者被覆盖面积比 >25% 即失败（容差外不允许压字）。
4. **标签与图例完整性**：逐坐标轴检查标题、x/y（及 z）轴标签是否非空，存在带 label 的图元时图例必须存在。
5. **色彩区分**：色板两两 RGB 欧氏距离 ≥40。
6. **三维专项**：固定视角 `elev=26, azim=-64`，检查三维轴标签不与刻度重叠、三维图必须存在二维配套投影（本问为 `emergency_heatmap_2d`）。

最终结果：10/10 图 `status=passed`；`visual_review.json.status=passed`。

## 5. 复核中发现并已修复的问题

| 问题 | 定位 | 修复 |
|---|---|---|
| 标题中的 `10⁶` 上标字符在 Microsoft YaHei 中缺字 | `annual_cost_composition` | 改为 `1e6`，并把缺字检测纳入门禁（渲染时同步捕获 Glyph 警告） |
| 三维 x 轴标签「日序（0 = 2025-02-01）」与刻度 `180` 压字 | `emergency_surface_3d` | x 轴 `labelpad` 12→22、y 轴 12→14，配合固定视角 `elev=26, azim=-64` 留白 |
| `result2.xlsx` 三个面板共用一套 x 刻度标签（计划购电量表被误用块标签） | `delivery_audit` | 每个面板显式传入自身刻度标签（6 个指定时段 / 6 个 4 小时块） |
| 数值门禁中残留无效标签核对占位代码 | `verify_inputs` | 删除占位逻辑，改为对 `result2.xlsx` 三表逐项核对（最大绝对偏差 0.0117 ≤ 0.05） |
| 交付核对面板长文本可能越界 | `delivery_audit` | 面板高度 8.6→9.8 in、字号 9.5→9.2，文本纳入裁切检测 |

## 6. 图文一致性与数值方向复核

- 图中数值全部来自 `solution.csv` / `daily_metrics.csv` / `emergency_segments.csv` / `metrics.json` / `solver_status.json` / `result2.xlsx`，无手工抄录；脚本在出图前执行**数值门禁**，全部通过后才允许出图：
  - 年度聚合复算（Cost_plan、Q_plan、充放电、计划/实际弃光、紧急购电量）与 `metrics.json` 相对偏差 ≤3.1e-11；
  - 每日终端储电量 E_144=6000 kWh（残差 0）、储电量全程 ∈[1200, 10800] kWh、无 NaN/Inf；
  - 12 类硬约束残差全部 ≤2.2e-10（阈值 1e-6）、`gates.all_pass=true`；
  - 求解器 334/334 天 status=0、失败 0 天、max mip_gap=2.01e-16；LP 松弛与 MILP 目标差 3.6e-11、无严格更优天；
  - 解析界：Cost_plan=12 570 533.91 元 ∈[6 749 147.61, 16 565 407.28]、Cost_total=17 399 306.33 元 ≥6 660 821.06、Q_plan=20 385 219.04 kWh ≥18 177 074.097 kWh、Cost_em=4 828 772.42 元 ≤5 815 010.60 元；
  - `result2.xlsx` 三表与复算逐项一致（最大绝对偏差 0.0117，来自交付表 3 位小数舍入），首列标签为统一后的物理区间 `0:00-0:10`。
- 方向性：紧急购电随预报缺口同向变化，逐日 u ≤ 当日预报缺口（中位数 100%、均值 87.0%），紧急购电时段全部满足 pv<pvfc；全年紧急购电 1 156 789.40 kWh（10 877 个时段、1 919 段），紧急购电费占全年费用 27.75%。
- 弃光分层：计划弃光 961 173.68 kWh、执行弃光 2 355 847.68 kWh，后者为前者的 2.45 倍；图中以「计划层 κ* / 执行层 κ_act」分别标注，caption 明确两者不可混用、交付窗口不存在零弃光（W7）。
- 口径与边界：图中明确「全天购电量/全天购电费」取计划口径（W3），含紧急购电费的 Cost_total 单独给出；时间标签按 asm-15 统一为物理区间，与附件 5 模板字面标签整体相差一个时段并已登记映射（W6）；caption 声明 u 完全来自 0:00 预报误差，若取实际值（alt-01）则 u≡0（W2）；未对 asm-06/asm-09/asm-08/asm-14 做任何数值结论，留待 robustness 与论文边界章节（W4/W5）。
- `solution.csv` 中 `surplus_kwh` 最小 −440.83（等于 −max(u)）为派生量而非物理量负值，图中未把 surplus 当作弃光或购电量使用（W8）。

## 7. 局限与移交

- 程序化审计能覆盖缺字、裁切、重叠、标签/图例完整性、颜色区分和三维投影配套，但**不能替代对图意误导性的像素级人工判断**。建议论文定稿团队在有图像能力的终端上对 10 张 PNG 做一次目检；本阶段结论不因此降级，登记为 warning。
- 上游技术债随图移交 robustness 与论文阶段：W1 `formulation.md §3.7 (D-ex)` 符号笔误需在论文前修正（实现与全部交付数值正确）；W2 预报口径需边界声明与 alt-01 对照；W3 计划口径与 Cost_total 双报；W4 asm-06（E^cyc∈{4800,6000,7200}）与 asm-09（单向 90%/并网点侧计量）待 robustness 对照；W5 asm-08/asm-14 边界声明；W6 标签映射登记；W7 弃光非零按段报告；W8 surplus 负值读数说明。
- 未登记图不得进入最终摘要；本次 10 张图全部登记且 `included_in_summary=true`，`included_in_paper` 交由论文阶段决定。

## 8. 结论

在 `assumption_v001` / `formulation_v001` 接受结果（task `ea71568e2cf6c5326ded`）上生成并登记 **10 张**出版级 PNG（≥5 张门禁），全部通过自动质检与视觉审计，标题、轴、单位、图例、配色、文本完整性与三维可读性均达标；`visualization` 逻辑产物完成，进入 `robustness`。
