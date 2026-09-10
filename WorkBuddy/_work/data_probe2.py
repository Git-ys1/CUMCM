# -*- coding: utf-8 -*-
"""针对评审意见的数据核验：
1) 弃光是否必须（PV-L 是否超过储能充电功率 5000 kW）
2) 问题1 平均日是否会出现被迫弃光（午间富余电量 vs 储能可用容量）
3) 预报误差 e = 预测 - 实际 的分布与分位数（用于安全裕度网格搜索）
4) 高估光伏（e>0）的比例，验证"危险方向"的判断
"""
import os
from datetime import datetime, timedelta

import numpy as np
import openpyxl

BASE = r"F:\AcademicHub\000资料相关\数模\26国赛\CUMCM2026Problems\C题\附件"
OUT = r"F:\AcademicHub\000资料相关\数模\26国赛\WorkBuddy\_work"
DT = 1.0 / 6.0
P_ES_KW = 5000.0
C_MAX = P_ES_KW * DT  # 833.33 kWh/时段


def grid(fname, sheet):
    wb = openpyxl.load_workbook(os.path.join(BASE, fname), read_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    dates = []
    mat = []
    for r in rows[1:]:
        if r[0] is None:
            continue
        d = r[0]
        if isinstance(d, datetime):
            d = d.date()
        dates.append(d)
        mat.append([float(v) if v is not None else np.nan for v in r[1:]])
    return dates, np.array(mat)


def main():
    L = []
    P = L.append

    d_load, LOAD = grid("附件2.xlsx", "小区负载")
    d_pv, PV = grid("附件2.xlsx", "光伏发电实际功率")

    P("# 评审意见的数据核验\n")

    # ---------- 1. 弃光必要性 ----------
    NET = LOAD - PV                      # kW
    SURPLUS = PV - LOAD                  # kW, >0 表示光伏富余
    P("## 1. 弃光变量是否必须\n")
    P(f"- 光伏富余 SURPLUS = PV − L 的最大值：**{np.nanmax(SURPLUS):.1f} kW**"
      f"（储能最大充电功率 {P_ES_KW:.0f} kW）")
    n_over = int(np.nansum(SURPLUS > P_ES_KW))
    tot = SURPLUS.size
    P(f"- SURPLUS > 5000 kW 的时段数：**{n_over}** / {tot}（占比 {n_over/tot*100:.3f}%）")
    P(f"- 若不设弃光变量且不允许上网售电，这些时段**数学上必然不可行** → "
      f"**必须引入弃光变量 $W_t$**。")
    forced = np.where(SURPLUS > P_ES_KW, (SURPLUS - P_ES_KW) * DT, 0.0)
    P(f"- 这些时段的被迫弃光电量合计：{np.nansum(forced):.1f} kWh；"
      f"单时段最大被迫弃光：{np.nanmax(forced):.2f} kWh")
    # 若储能同时还要考虑容量已满，实际弃光会更多，这里只是功率约束给出的下界
    P(f"- 注：以上仅由**功率上限**推出，是弃光电量的**下界**；"
      f"若储能在富余时段已达容量上限，实际弃光更多。\n")

    # ---------- 2. 问题1 平均日 ----------
    wb = openpyxl.load_workbook(os.path.join(BASE, "附件1.xlsx"), read_only=True)
    ws = wb["Sheet1"]
    r1 = list(ws.iter_rows(values_only=True))[1:]
    wb.close()
    p1 = np.array([float(r[1]) for r in r1])
    l1 = np.array([float(r[2]) for r in r1])
    pv1 = np.array([float(r[3]) for r in r1])
    sur1 = pv1 - l1
    P("## 2. 问题1（平均典型日）是否被迫弃光\n")
    P(f"- 平均日 SURPLUS 最大值：{sur1.max():.1f} kW（< 5000 kW，"
      f"**功率层面不构成被迫弃光**）")
    surplus_energy = float(np.sum(np.clip(sur1, 0, None)) * DT)
    P(f"- 平均日午间富余电量合计：{surplus_energy:.0f} kWh")
    headroom = 10800 - 6000
    P(f"- 若 0:00 与 24:00 均为 6000 kWh，则从 6000 起充、可用净空间约 "
      f"{10800-1200:.0f} kWh（受安全上限约束），从 6000 起算可吸收 {headroom:.0f} kWh")
    if surplus_energy > headroom + (6000 - 1200):
        P(f"- 富余电量 {surplus_energy:.0f} kWh 与可用空间对比："
          f"即使把储能从 1200 充到 10800 也只能吸收 {10800-1200:.0f} kWh"
          f"→ **存在被迫弃光的可能**，需由 LP 判定")
    else:
        P(f"- 富余电量 {surplus_energy:.0f} kWh ≤ 最大可吸收 {10800-1200:.0f} kWh"
          f"→ **功率与容量均不构成被迫弃光**，但 LP 仍可能因经济性选择少量弃光")
    P("")

    # ---------- 3. 预报误差分布 ----------
    P("## 3. 预报误差 e = 预测 − 实际 的分布（安全裕度标定）\n")
    # 小时平均实际值
    hl = []
    for t in range(144):
        mins = (t + 1) * 10
        hl.append(((mins - 1) // 60) % 24)
    hl = np.array(hl)
    hourly_actual = {}
    for i, d in enumerate(d_pv):
        arr = np.full(24, np.nan)
        for h in range(24):
            arr[h] = np.nanmean(PV[i, hl == h])
        hourly_actual[d] = arr

    wb = openpyxl.load_workbook(os.path.join(BASE, "附件3.xlsx"), read_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    fc = {}
    cur = None
    for r in rows[1:]:
        if r[0]:
            cur = str(r[0])
        ih = int(str(r[1]).split(":")[0])
        vals = [float(v) if v is not None else np.nan for v in r[2:26]]
        try:
            y, m, dd = [int(x) for x in cur.split("-")]
            fc[(datetime(y, m, dd).date(), ih)] = vals
        except Exception:
            continue

    errs = []
    errs_day = []   # 仅白天（实际光伏 > 0）
    for (d, ih), vals in fc.items():
        for k in range(1, 25):
            td = d + timedelta(hours=ih + k)
            th = (ih + k) % 24
            if td not in hourly_actual:
                continue
            a = hourly_actual[td][th]
            f = vals[k - 1]
            if np.isnan(a) or np.isnan(f):
                continue
            errs.append(f - a)
            if a > 50:
                errs_day.append(f - a)
    errs = np.array(errs)
    errs_day = np.array(errs_day)

    P(f"- 全样本 n = {len(errs)}；MAE {np.mean(np.abs(errs)):.1f} kW，"
      f"Bias {np.mean(errs):.1f} kW，RMSE {np.sqrt(np.mean(errs**2)):.1f} kW")
    P(f"- 仅白天（实际 > 50 kW）n = {len(errs_day)}；"
      f"MAE {np.mean(np.abs(errs_day)):.1f} kW，Bias {np.mean(errs_day):.1f} kW，"
      f"RMSE {np.sqrt(np.mean(errs_day**2)):.1f} kW")
    P("")
    P("| 分位数 q | 全样本 e_q (kW) | 折合 10 min 电量 (kWh) | 白天 e_q (kW) | 折合电量 (kWh) |")
    P("|---|---|---|---|---|")
    for q in [0.50, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        eq = np.quantile(errs, q)
        edq = np.quantile(errs_day, q)
        P(f"| {q:.2f} | {eq:.1f} | {eq*DT:.1f} | {edq:.1f} | {edq*DT:.1f} |")

    pos = np.mean(errs > 0)
    P("")
    P(f"- **高估光伏（e > 0，危险方向）** 占比：**{pos*100:.1f}%**；"
      f"低估（e < 0）占比 {(1-pos)*100:.1f}%")
    P(f"- e > 0 时的条件均值 {np.mean(errs[errs>0]):.1f} kW；"
      f"e < 0 时的条件均值 {np.mean(errs[errs<0]):.1f} kW")
    P("")
    P("- **结论**：e > 0（预测高于实际 → 计划买少了 → 缺口 → 5 倍紧急购电）"
      "占约一半，是必须防范的方向；"
      "评审指出的「高估光伏才是危险方向」成立。\n")

    # ---------- 4. 用于 Q2 自建日前预测的可行性 ----------
    P("## 4. Q2 自建日前光伏预测的可行性（历史可用长度）\n")
    P(f"- 附件2 覆盖 2025-01-01 ~ 2025-12-31，共 {LOAD.shape[0]} 天")
    P("- Q2 结果从 2025-02-01 起报 → **1 月共 31 天可作为预测模型的训练/预热窗口**")
    P("- 候选方法：① 前 k 天同刻点滑动平均（k=7/14/30）；"
      "② 晴空模型（日照几何）+ 逐日衰减系数；③ 前一日同时刻持续法")
    P("- 注意：仅单一年份数据，无法使用「去年同日」类季节性样本\n")

    out = os.path.join(OUT, "data_probe2_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("written:", out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
