# MathModel —— C 题论文 V4 复现说明

本目录是在论文 V3 与 `Codex-MathModel/Review/` 两篇审阅意见基础上形成的 V4 独立实现。
原始 `Codex/` 工程未被修改；求解、审计、制表、绘图、测试和 LaTeX 源码均保存在本目录。

## 一句话结论

原问题二结果偏低的**首要原因是把当天真实负载当成了 0:00 已知输入**（未来信息穿越），
修正为严格因果预测后全年费用由 1327.6 万元升至 **1477.4 万元**，原口径低估
149.8 万元（占修正结果 10.14%）。问题三按题面采用 additive 结算并加入充放电互斥，
0:00、6:00、12:00、18:00 四组费用依次为 1573.1、1451.1、1421.3、1391.7 万元。
问题四直接使用附件 4 电价的 Q4-2、Q4-3 主结果分别为 1552.4、1459.0 万元。

## 目录结构

```
MathModel/
├─ solve/                      求解与绘图源码
│  ├─ params.py                储能物理参数与口径变体（E1/E2 效率解释）
│  ├─ io_data.py               附件 1–5 读取与时间对齐
│  ├─ lp_core.py               LP/MILP 内核（调整等式、互斥二元变量、词典序）
│  ├─ forecast.py              光伏日前预测与 4:1 非对称风险定价
│  ├─ load_forecast.py         因果负载预测（在线滚动选型）
│  ├─ price_forecast.py        因果电价预测（问题四）
│  ├─ settle.py                实时储能反馈 ON/OFF 两种执行口径
│  ├─ q1.py … q4.py            四问主流程
│  ├─ export.py                官方 result*.xlsx 回填
│  ├─ ablation.py              全部对照实验总控
│  ├─ report.py                V4 审计报告、数值宏与提交文件汇总
│  └─ fig_*.py                 各类配图
├─ tests/                      验证套件
│  ├─ test_causality.py        未来信息泄漏 mutation 测试（6 项）
│  ├─ test_settlement.py       结算口径单元测试（9 项）
│  ├─ test_paper_consistency.py 正文宏、费用分解和 Excel 哈希一致性
│  └─ test_regression.py       legacy 参数组合回归测试
├─ outputs/                    结果
│  ├─ q1/                      问题一
│  └─ variants/model_audit_v4/ V4 全部对照实验
├─ reports/MODEL_AUDIT_V4.md   模型审计报告
├─ paper/                      LaTeX 论文（cumcm 模板）
└─ submit/                     五个官方 result*.xlsx 汇总
```

## 运行

要求 Python 3.12、SciPy（须提供 `scipy.optimize.milp`）、NumPy、pandas、openpyxl、
matplotlib 与 pytest。本机已锁定解释器为 `AutoMM\.venv\Scripts\python.exe`；不要使用旧 Anaconda 3.7。

```bash
cd F:\AcademicHub\000资料相关\数模\26国赛

# 四问主流程
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.q1
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.q2
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.q3
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.q4

# 全部对照实验（Q2 A/B/C/D、Q3 S0–S3 两种结算、Q4 价格信息、灵敏度）
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.ablation

# 验证（从项目根目录执行，唯一推荐命令）
AutoMM\.venv\Scripts\python.exe -m pytest MathModel/tests -q --import-mode=importlib

# 报告与数值宏
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.report

# 配图
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.fig_data
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.fig_q1
AutoMM\.venv\Scripts\python.exe -m MathModel.solve.fig_results

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
| `settlement_mode` | `additive` / `replacement` | 叠加口径为主；差额口径从头重优化作敏感性 |
| `update_nodes` | `(0,)` … `(0,36,72,108)` | 可重优化节点；关闭节点时最近有效计划继续执行 |
| `pv_update_nodes` | 节点子集 | 配对控制中单独控制官方光伏预报刷新 |
| `storage` | `StorageParams` | 效率口径 E1/E2 |

任何"严格在线"结果的硬性判据：决策时刻之后才会发生的真实负载、真实光伏与真实电价，
一律不得进入优化输入——由 `tests/test_causality.py` 自动验证。

## 理论要点

5 倍紧急电价使单位光伏偏差的损失为 `4π(高估)⁺ + π(低估)⁺`，即 **4:1 非对称损失**。
单时段报童模型给出光伏输出 **0.2 分位数**（`b/(a+b) = 1/5`）的可解释安全裕度起点；
它不是含 SOC 耦合的全年模型全局最优性证明。工程把残差定义为 `base-actual`，因此输出 0.2
分位对应“基预测减去残差 0.8 分位”，并在 0.80/0.85/0.90/0.95 候选中按历史样本外费用在线选择。
