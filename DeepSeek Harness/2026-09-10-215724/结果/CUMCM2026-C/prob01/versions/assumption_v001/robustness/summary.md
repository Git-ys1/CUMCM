# prob01 鲁棒性扫描汇总（预注册方案：plan.md）

- 基线 Cost_day = 35126.948589 元（锚定偏差 7.276e-12，通过=True）
- 无储能参照 Cost_day = 48052.046591 元；储能节省 12925.098002 元（26.90%）
- 情景数（含基线）= 43；蒙特卡洛 200 次；判定 = **fragile**

## 判据结果

- C1 数值合法性：通过=True，违反=无
- C2 假设口径 ≤10%：通过=True，违反=无
- C3 参数包络 ≤25%：通过=False，违反=['E_load_-20pct', 'E_load_+20pct']
- C4 结构结论：通过=False，无弃光占比=88.4%，M1-M2 差=0.000e+00
- C5 时间标签错位：Δ=-0.000%（方向 down，仅登记）
- C6 蒙特卡洛：95% 区间宽度=+28.207%，均值偏差=+0.047%，通过=False
- 方向核验：41/43 通过；失败=['A3_meter_battery_side', 'B3_Emax_9600']
- 广义构造器等价性：max|Δ|=0.000e+00（keys_equal=True）
- 敏感性图错误：无

## 情景表

| 情景 | 组 | Cost_day | Δ% | 弃光 | 期望方向 | 实测 | 通过 |
|---|---|---|---|---|---|---|---|
| A1_baseline | A_structure | 35126.948589 | +0.000% | 0.000000 | same | same | True |
| A2_no_storage | A_structure | 48052.046591 | +36.795% | 6247.962967 | up | up | True |
| A3_meter_battery_side | A_structure | 35101.567554 | -0.072% | 0.000000 | up | down | False |
| A4_allow_zero_revenue_export | A_structure | 35126.948589 | +0.000% | 0.000000 | same | same | True |
| A5_lp_relaxation | A_structure | 35126.948589 | +0.000% | 0.000000 | same | same | True |
| B1_E0_4800 | B_terminal_bounds | 35133.231923 | +0.018% | 0.000000 | up | up | True |
| B2_E0_7200 | B_terminal_bounds | 35122.465256 | -0.013% | 0.000000 | down | down | True |
| B3_Emax_9600 | B_terminal_bounds | 36031.369451 | +2.575% | 0.000000 | not_up | up | False |
| B4_Emax_12000 | B_terminal_bounds | 34342.270892 | -2.234% | 0.000000 | not_up | down | True |
| B5_Emin_1800 | B_terminal_bounds | 35536.459371 | +1.166% | 0.000000 | not_down | up | True |
| C1_roundtrip_0.90 | C_efficiency | 33801.495542 | -3.773% | 0.000000 | down | down | True |
| C2_eta_0.855 | C_efficiency | 36447.922109 | +3.761% | 0.000000 | up | up | True |
| C3_eta_0.945 | C_efficiency | 33898.269806 | -3.498% | 0.000000 | down | down | True |
| C4_eta_0.81 | C_efficiency | 37888.249121 | +7.861% | 0.000000 | up | up | True |
| C5_eta_0.99 | C_efficiency | 32695.447407 | -6.922% | 0.000000 | down | down | True |
| D1_Pmax_-10pct | D_power_cap | 35156.499953 | +0.084% | 0.000000 | not_down | up | True |
| D2_Pmax_-20pct | D_power_cap | 35247.870900 | +0.344% | 0.000000 | not_down | up | True |
| D3_Pmax_+10pct | D_power_cap | 35103.851813 | -0.066% | 0.000000 | not_up | down | True |
| D4_Pmax_+20pct | D_power_cap | 35083.293480 | -0.124% | 0.000000 | not_up | down | True |
| E_price_-5pct | E_data_perturbation | 33370.601160 | -5.000% | 0.000000 | down | down | True |
| E_price_-10pct | E_data_perturbation | 31614.253730 | -10.000% | 0.000000 | down | down | True |
| E_price_-20pct | E_data_perturbation | 28101.558871 | -20.000% | 0.000000 | down | down | True |
| E_price_+5pct | E_data_perturbation | 36883.296019 | +5.000% | 0.000000 | up | up | True |
| E_price_+10pct | E_data_perturbation | 38639.643448 | +10.000% | 0.000000 | up | up | True |
| E_price_+20pct | E_data_perturbation | 42152.338307 | +20.000% | 0.000000 | up | up | True |
| E_load_-5pct | E_data_perturbation | 31552.184281 | -10.177% | 0.000000 | down | down | True |
| E_load_-10pct | E_data_perturbation | 28073.627585 | -20.080% | 0.000000 | down | down | True |
| E_load_-20pct | E_data_perturbation | 22159.430750 | -36.916% | 2166.795970 | down | down | True |
| E_load_+5pct | E_data_perturbation | 38834.167696 | +10.554% | 0.000000 | up | up | True |
| E_load_+10pct | E_data_perturbation | 42745.808549 | +21.690% | 0.000000 | up | up | True |
| E_load_+20pct | E_data_perturbation | 50929.885339 | +44.988% | 0.000000 | up | up | True |
| E_pv_-5pct | E_data_perturbation | 36697.187486 | +4.470% | 0.000000 | up | up | True |
| E_pv_-10pct | E_data_perturbation | 38422.561088 | +9.382% | 0.000000 | up | up | True |
| E_pv_-20pct | E_data_perturbation | 42269.092135 | +20.332% | 0.000000 | up | up | True |
| E_pv_+5pct | E_data_perturbation | 33630.579966 | -4.260% | 0.000000 | down | down | True |
| E_pv_+10pct | E_data_perturbation | 32211.933457 | -8.299% | 0.000000 | down | down | True |
| E_pv_+20pct | E_data_perturbation | 30873.958970 | -12.107% | 3258.395357 | down | down | True |
| F1_price+20_load+20 | F_stress_combinations | 61115.862407 | +73.986% | 0.000000 | up | up | True |
| F2_price-20_load+20 | F_stress_combinations | 40743.908271 | +15.990% | 0.000000 | any | up | True |
| F3_pv-20_load+20 | F_stress_combinations | 59202.571074 | +68.539% | 0.000000 | up | up | True |
| F4_pv+20_load-20 | F_stress_combinations | 20769.678516 | -40.873% | 11166.599473 | down | down | True |
| F5_price+20_pv+20_load-20 | F_stress_combinations | 24923.614219 | -29.047% | 11166.599473 | any | down | True |
| G1_cyclic_shift_1 | G_time_label | 35126.848589 | -0.000% | 0.000000 | any | down | True |

## 后续（聚合动作按 plan.md §6 执行）

1. 复核 summary.json 的 C1–C6 与基线锚定；
2. 运行 `--register-figures` 登记敏感性图到题目 figure manifest；
3. 写 `stability_conclusion.md` 并经 commands 记录 `record_figure_review` 与 `record_optional_stage`。
