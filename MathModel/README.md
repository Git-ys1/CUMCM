# MathModel —— C 题模型修订工程

本目录是对 `Codex/` 工程按《C题_Codex模型修订任务书_V2》做系统性修订后的独立实现。
**不修改、不覆盖 `Codex/` 下的任何文件**；所有新结果写入本目录。

## 一句话结论

原问题二结果偏低的**首要原因是把当天真实负载当成了 0:00 已知输入**（未来信息穿越），
修正为严格因果预测后全年费用由 1327.6 万元升至 **1477.4 万元**（+149.8 万元，约 +11.3%）；
光伏风险边际与 10 min 实时储能反馈分别再贡献 126.5 万元与 58.7 万元的节省。

## 目录结构

```
MathModel/
├─ solve/                      求解与绘图源码
│  ├─ params.py                储能物理参数与口径变体（E1/E2 效率解释）
│  ├─ io_data.py               附件 1–5 读取与时间对齐
│  ├─ lp_core.py               公共线性规划内核（含 inc/dec 精确线性化、三层词典序）
│  ├─ forecast.py              光伏日前预测与 4:1 非对称风险定价
│  ├─ load_forecast.py         因果负载预测（在线滚动选型）
│  ├─ price_forecast.py        因果电价预测（问题四）
│  ├─ settle.py                实时储能反馈 ON/OFF 两种执行口径
│  ├─ q1.py … q4.py            四问主流程
│  ├─ export.py                官方 result*.xlsx 回填
│  ├─ ablation.py              全部对照实验总控
│  ├─ report.py                审计报告、数值宏、提交文件汇总
│  └─ fig_*.py                 各类配图
├─ tests/                      验证套件
│  ├─ test_causality.py        未来信息泄漏 mutation 测试（6 项）
│  ├─ test_settlement.py       结算口径单元测试（9 项）
│  └─ test_regression.py       legacy 结果回归测试（4 项）
├─ outputs/                    结果
│  ├─ q1/                      问题一
│  └─ variants/model_audit_v2/ 本轮全部对照实验
├─ reports/MODEL_AUDIT_V2.md   模型审计报告
├─ paper/                      LaTeX 论文（cumcm 模板）
└─ submit/                     五个官方 result*.xlsx 汇总
```

## 运行

环境：`..\AutoMM\.venv\Scripts\python.exe`（Python 3.12 + numpy/scipy/pandas/matplotlib/seaborn）。

```bash
cd F:\AcademicHub\000资料相关\数模\26国赛

# 四问主流程
python -m MathModel.solve.q1
python -m MathModel.solve.q2
python -m MathModel.solve.q3
python -m MathModel.solve.q4

# 全部对照实验（Q2 A/B/C/D、Q3 S0–S3 两种结算、Q4 价格信息、灵敏度）
python -c "from MathModel.solve.ablation import *; run_q2_ablation(); run_q3_ablation('replacement'); run_q3_ablation('additive'); run_q4_ablation(); run_sensitivity()"

# 验证
python -m unittest MathModel.tests.test_settlement
python -m unittest MathModel.tests.test_causality     # 约 2 分钟
python -m unittest MathModel.tests.test_regression    # 约 5 分钟

# 报告与数值宏
python -m MathModel.solve.report

# 配图
python -m MathModel.solve.fig_data
python -m MathModel.solve.fig_q1
python -m MathModel.solve.fig_results
python -m MathModel.solve.fig_route

# 编译论文
bash MathModel/tools/build_paper.sh
```

## 信息集口径（本工程的核心）

| 维度 | 取值 | 含义 |
|---|---|---|
| `load_mode` | `perfect` / `causal` | 计划是否使用当天真实负载 |
| `price_mode` | `perfect` / `causal` | 计划是否使用当天真实电价 |
| `pv_risk_mode` | `asymmetric` / `point` | 是否施加 0.2 分位数安全下修 |
| `realtime_feedback` | `True` / `False` | 是否允许 10 min 级实时储能调节 |
| `terminal_policy` | `daily_cycle` / `free` | 计划终端 SOC 是否等于当日实际初值 |
| `settlement_mode` | `replacement` / `additive` | 问题三两种结算解释，**分别重新优化** |
| `update_nodes` | `(0,)` … `(0,36,72,108)` | 问题三可用预报节点，用于预报价值消融 |
| `storage` | `StorageParams` | 效率口径 E1/E2 |

任何"严格在线"结果的硬性判据：决策时刻之后才会发生的真实负载、真实光伏与真实电价，
一律不得进入优化输入——由 `tests/test_causality.py` 自动验证。

## 理论要点

5 倍紧急电价使单位光伏偏差的损失为 `4π(高估)⁺ + π(低估)⁺`，即 **4:1 非对称损失**。
由报童模型，最优光伏点预测应取预测分布的 **0.2 分位数**（`b/(a+b) = 1/5`）。
工程实现为"基预测减去残差的 0.80 分位数"，二者在数学上等价，已由独立数值实验验证最优性。
