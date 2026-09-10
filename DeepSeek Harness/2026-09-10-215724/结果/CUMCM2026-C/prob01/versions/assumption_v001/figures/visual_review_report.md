# prob01 图表视觉复核报告

- problem_id: CUMCM2026-C
- question_id: prob01
- assumption_version: `assumption_v001`（accepted）
- formulation_version: `formulation_v001`（accepted）
- task_id: `13bf04ee604e54581fa2`（attempt 1，succeeded，rc=0）
- sanity 前置：L1–L4 = PASS_WITH_WARNING（sanity_check 阶段已独立复核）
- 生成脚本：`problems/CUMCM2026-C/prob01/versions/assumption_v001/figures/generate_prob01_figures.py`
- 生成与复核动作：`act-2885b0122f284329`（visualization 阶段）
- 复核时间：2026-09-10（UTC）

## 1. 输入与追溯

图表只读取接受版本的计算交付，未修改任何原始数据、模型或上游版本：

| 输入 | 路径 | 用途 |
|---|---|---|
| 最优解 | `.../results/prob01_m1_formulation_v001/solution.csv` | 全部时序与交付口径图 |
| 指标与残差 | `.../metrics.json` | 指标、表 1/表 2、残差诊断 |
| 求解质量 | `.../solver_status.json` | 求解状态、best bound、gap、规模 |

`figures.yaml` 中每张图登记了 `source_hashes`（三个输入文件的 sha256）、稳定 ID、脚本路径、版本与 caption，可完整回溯到输入与代码。

## 2. 统一样式

- 字体：`Microsoft YaHei`（配置首选，环境已探测可用）；信息面板使用 `NSimSun`（中文等宽，避免方框字符）。
- 色板：primary `#1F4E79`、secondary `#70AD47`、accent `#ED7D31`、neutral `#7F8C8D`、warning `#C00000`；色板两两最小 RGB 距离 **78.8**（阈值 40）。
- DPI 180、PNG、白底；图幅按 `config/visualization.yaml` 的 10×6 in 基线按面板数扩展。

## 3. 图表清单（均登记于 `problems/CUMCM2026-C/figures.yaml`）

| slug | stable_id | 标题 | 分辨率 | 自动质检 | 视觉审计 |
|---|---|---|---|---|---|
| day_profile | prob01_fig_day_profile_98e7bc98b7 | 代表日分时电价、负载与光伏预测（含净负荷） | 1776×1312 | passed | passed（文本 39；重叠 0；缺字 0；裁切 0） |
| netload_purchase | prob01_fig_netload_purchase_ea5dd09d3f | 净负荷与最优计划购电量（逐时段与累计） | 1777×1308 | passed | passed（文本 37；重叠 0；缺字 0；裁切 0） |
| soc_trajectory | prob01_fig_soc_trajectory_5ff0f90d06 | 储能储电量全天轨迹与运行边界（含贴界时段） | 1777×1092 | passed | passed（文本 29；重叠 0；缺字 0；裁切 0） |
| arbitrage | prob01_fig_arbitrage_e99ae14bd7 | 低谷充电与高峰放电的套利结构 | 1778×1308 | passed | passed（文本 38；重叠 0；缺字 0；裁切 0） |
| delivery_audit | prob01_fig_delivery_audit_a2257b367f | result1.xlsx 交付口径核对（表 1/表 2/分块购电费） | 1783×1415 | passed | passed（文本 63；重叠 0；缺字 0；裁切 0） |
| cumulative_cost | prob01_fig_cumulative_cost_bfd2cc2a57 | 全天购电费对比：M1 与无储能基线 | 1777×1346 | passed | passed（文本 39；重叠 0；缺字 0；裁切 0） |
| residual_diagnostics | prob01_fig_residual_diagnostics_f987826556 | 结果可信度：硬约束回代残差与求解质量 | 2214×1065 | passed | passed（文本 21；重叠 0；缺字 0；裁切 0） |
| state_price_trajectory_3d | prob01_fig_state_price_trajectory_3d_0608ca3079 | 储电量–电价–时刻三维调度轨迹 | 1305×1343 | passed | passed（文本 24；重叠 0；缺字 0；裁切 0） |
| price_soc_phase | prob01_fig_price_soc_phase_ecc766e65c | 电价–储电量相平面轨迹（三维配套二维投影） | 1674×1129 | passed | passed（文本 23；重叠 0；缺字 0；裁切 0） |

每张图回答一个明确问题，功能互补、不重复表达同一信息：输入结构 → 主要结果（购电量、储电量） → 套利机制 → 交付口径 → 经济效果 → 可信度诊断 → 三维动态轨迹及其二维投影。

## 4. 视觉审计方法

本环境最终响应模型不支持图像输入，无法进行像素级人工目检。因此视觉复核以**可复现的程序化审计**完成，审计脚本与图表脚本同源（`audit_figure`），逐图结果写入 `visual_review.json`：

1. **CJK 字形覆盖**：用 `FT2Font.get_charmap()` 按每个文本 artist 实际使用的字体族逐字符检查，缺字即失败；渲染阶段另捕获 matplotlib `Glyph ... missing from font` 警告，出现即失败（防止方框字符静默通过）。
2. **文本裁切/越界**：所有可见文本（标题、轴标签、刻度、图例、注释）的窗口包围盒必须落在画布内（容差 2 px）；三维坐标轴超出视图范围的刻度标签先按 `get_view_interval()` 过滤（未实际绘制）。
3. **文本重叠**：两两计算包围盒交集，较小者被覆盖面积比 >25% 即失败（容差外不允许压字）。
4. **标签与图例完整性**：逐坐标轴检查标题、x/y（及 z）轴标签是否非空，存在带 label 的图元时图例必须存在。
5. **色彩区分**：色板两两 RGB 欧氏距离 ≥40。
6. **三维专项**：固定视角 `elev=20, azim=-62`，检查三维轴标签不与刻度重叠、三维图必须存在二维配套投影（本问为 `price_soc_phase`）。

最终结果：9/9 图 `status=passed`；`visual_review.json.status=passed`。

## 5. 复核中发现并已修复的问题

| 问题 | 定位 | 修复 |
|---|---|---|
| 信息面板使用 DejaVu Sans Mono，中文缺字（方框风险） | `delivery_audit`、`residual_diagnostics` | 改用中文等宽 `NSimSun`，并把缺字检测纳入门禁 |
| 审计误报：把超出视图范围的刻度（如 -500、70000、12000）计入重叠/裁切 | `netload_purchase`、`state_price_trajectory_3d` | 按 `get_view_interval()` 过滤未绘制刻度，并补上 z 轴 |
| 下界注释与图例压字 | `soc_trajectory` | 图例移至左下 |
| 三维 y 轴标签与刻度 0.8/1.0 压字 | `state_price_trajectory_3d` | y 轴 `labelpad` 8→26，x/z 轴同步微调 |
| 文本面板长行越出画布 | `residual_diagnostics` | 精简字段行、字号 10→9.5 |
| 下界注释与图例压字 | `price_soc_phase` | 图例移至右上 |

## 6. 图文一致性与数值方向复核

- 图中数值全部来自 `solution.csv` / `metrics.json` / `solver_status.json`，无手工抄录；脚本在出图前执行**数值门禁**：Cost_day、Q_day、弃光、充放电总量、储电量边界、终端、互斥、非负性、NaN/Inf 与 metrics 一致，且 solver status=0、gap=0，否则拒绝出图。
- 交付口径：表 1 六时段取自 t=61/73/85/97/109/121；表 2 六块充放电量与 E_0/E_144 逐项一致；六块购电费合计 35126.9486 元与 Cost_day 完全一致（残差 0）。
- 无储能基线由附件 1 数据直接复算得 48052.0466 元，与 `metrics.json` 的解析可行上界 `cost_feasible_upper_bound` 一致（差 <5e-3），图中标注为基线而非新模型结果；M1 较基线节省 12925.0980 元（−26.90%）。
- 方向性：充电压价 0.4930 元/kWh < 放电压价 1.1376 元/kWh；55.4% 的充电量落在最低价四分位、64.1% 的放电量落在最高价四分位，与「低谷充电、高峰放电」一致；全天弃光 0 kWh。
- 边界解读：储电量贴运行上界 10800 kWh（t=34,35,87,91~108）与下界 1200 kWh（t=124~131），图中以对照线明确标注，caption 声明不得解读为设备余量，需 robustness 做端点敏感性。

## 7. 局限与移交

- 程序化审计能覆盖缺字、裁切、重叠、标签/图例完整性、颜色区分和三维投影配套，但**不能替代对图意误导性的像素级人工判断**。建议论文定稿团队在有图像能力的终端上对 9 张 PNG 做一次目检；本阶段结论不因此降级，登记为 warning。
- 上游技术债随图移交 robustness：asm-02（E_0=E_144=6000）、asm-04/asm-05（效率与计量口径）需对照；asm-12 标签口径与附件 5 模板存在整体一个时段的偏移（有意统一）；asm-10/asm-07/asm-03 边界需在论文声明；`y_binary` 存在 −1.52e-15 数值噪声（不影响任何指标）。
- 未登记图不得进入最终摘要；本次 9 张图全部登记且 `included_in_summary=true`，`included_in_paper` 交由论文阶段决定。

## 8. 结论

在 `assumption_v001` / `formulation_v001` 接受结果上生成并登记 **9 张**出版级 PNG（≥5 张门禁），全部通过自动质检与视觉审计，标题、轴、单位、图例、配色、文本完整性与三维可读性均达标；`visualization` 逻辑产物完成，进入 `robustness`。
