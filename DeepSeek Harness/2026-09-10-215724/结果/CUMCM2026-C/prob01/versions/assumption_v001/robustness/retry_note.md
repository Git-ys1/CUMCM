# attempt-001 失败残留说明（robustness 阶段目录）

> 本目录 `problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness/` 同时存放：
> ① 阶段级文件（本说明、`plan.md` 预注册方案、`task_spec.yaml`/`task_spec_v002.yaml`、
>    `prob01_robustness.py` 扫描脚本）；
> ② **attempt-001 的失败残留**（`raw/`、`summary.json`、`summary.csv`、`summary.md`、
>    `ci.json`、`solver_status.json`、`figures/`）。

## 事实

- 任务：`runtime/tasks/cd463874338e3f8a7f16`（attempt=1，output_directory 即本目录）。
- 终态：`failed`、returncode=1、failure_type=`process_exit`、failure_class=`code_runtime`、
  `feasible_incumbent=true`、`consumed=false`。
- 根因：43 情景 + 200 次蒙特卡洛全部算完、`summary.*`/`ci.json`/`solver_status.json`
  落盘之后，`write_outputs()` 写 `run_manifest.json` 时对**相对路径**调用
  `out_root.relative_to(ROOT)` 抛 `ValueError`。因此本目录**缺少 `run_manifest.json`**，
  产物链不完整。
- 本目录中的数值文件是上述失败 attempt 的原始残留；它们**不是**本阶段被接受的扫描结果，
  不得用于结论、图表登记或交付。请勿删除或覆盖（保留失败尝试的可追溯性）。

## 被接受的扫描结果在哪里

- 修复后重跑：`problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness_v002/`
  （task `66b12e7cd283813a098e`，规格见 `task_spec_v002.yaml`）。
- 之所以使用新输出目录：`wiki/compute-tasks.md` 与 `wiki/recovery-stale.md` 要求
  「失败重试使用新 attempt 和新输出目录」，且 `task_worker.py` 会在输出目录加
  `.automm-output.lock`，同一结果目录不允许两个任务写入。
- 预注册判据与情景矩阵未做任何事后修改；修复只涉及输出路径处理（见 `task_spec_v002.yaml` §1）。
