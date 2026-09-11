# C 题论文 V4 支撑材料

压缩包内的 `MathModel/` 应放在赛题项目根目录下，并与官方数据目录
`CUMCM2026Problems/C题/附件/` 保持同级关系。五个最终工作簿位于 `results/`；
求解、验证、制表与绘图代码位于 `solve/`；测试位于 `tests/`。

运行环境：Python 3.12，NumPy、pandas、openpyxl、matplotlib、pytest，以及提供
`scipy.optimize.milp` 的 SciPy 1.11 或更高版本。Windows PowerShell 示例：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install numpy pandas scipy openpyxl matplotlib pytest
.\.venv\Scripts\python.exe -m MathModel.solve.ablation
.\.venv\Scripts\python.exe -m MathModel.solve.report
.\.venv\Scripts\python.exe -m pytest MathModel/tests -q --import-mode=importlib
```

`ablation` 会依次重算问题二 A/B/C/D、问题三 additive 主口径与 replacement
敏感性、问题四附件 4 直用/因果价格两类结果及终端与效率敏感性；年度全量运行耗时较长。
`report` 会生成 V4 审计报告、论文数值宏、指定日期表并把题面主口径工作簿汇总到
`MathModel/submit/`。固定随机过程均使用显式随机种子；最终采用结果不依赖随机抽样。

主口径摘要：问题二总费用 14773804.78 元；问题三 additive 滚动方案总费用
13917403.19 元；问题四直接使用附件 4 电价时，Q4-2 与 Q4-3 分别为
15523884.83 元和 14589632.38 元。完整分项、对照与机器可读指标见 `reports/`。
