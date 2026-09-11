# Codex C题独立求解工程

本目录接手WorkBuddy的题意分析和口径锁定，独立完成Q1-Q4建模、求解、官方Excel回填、论文表格、图表和全量回读验收。

## 快速运行

在国赛工作区根目录执行：

    AutoMM\.venv\Scripts\python.exe -m Codex.solve.q1
    AutoMM\.venv\Scripts\python.exe -m Codex.solve.q2
    AutoMM\.venv\Scripts\python.exe -m Codex.solve.q3
    AutoMM\.venv\Scripts\python.exe -m Codex.solve.q4

验收和材料生成：

    AutoMM\.venv\Scripts\python.exe -m unittest discover -s Codex\tests -v
    AutoMM\.venv\Scripts\python.exe -m Codex.solve.validate_all
    AutoMM\.venv\Scripts\python.exe -m Codex.solve.paper_tables
    AutoMM\.venv\Scripts\python.exe -m Codex.solve.plot_results
    AutoMM\.venv\Scripts\python.exe -m Codex.solve.build_manifest

## Q3变体重跑

Python调用run_q3，可设置：

- downscale="step"或"linear"
- calibrate=False或True
- price_matrix=None或附件4价格矩阵
- output_dir=独立目录
- template_name=官方模板文件名

所有已采用和未采用策略都登记在reports/DECISION_LOG.md，产物哈希在outputs/MANIFEST.json。不要用新结果覆盖variants目录。
