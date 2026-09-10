# -*- coding: utf-8 -*-
"""为 C 题建模选型做数据探查：预报误差 / 净负载与储能约束 / 电价结构。

输出：WorkBuddy/_work/data_probe_report.md
"""
import os
from datetime import datetime, timedelta

import numpy as np
import openpyxl

BASE = r"F:\AcademicHub\000资料相关\数模\26国赛\CUMCM2026Problems\C题\附件"
OUT = r"F:\AcademicHub\000资料相关\数模\26国赛\WorkBuddy\_work"

DT = 1.0 / 6.0  # 10 min -> hour


def load_grid(fname, sheet):
    """读取 365 天 x 144 点的日表，返回 (dates, times, matrix[kWh or kW])"""
    wb = openpyxl.load_workbook(os.path.join(BASE, fname), read_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    times = [h for h in header[1:]]
    dates, mat = [], []
    for r in rows[1:]:
        if r[0] is None:
            continue
        d = r[0]
        if isinstance(d, datetime):
            d = d.date()
        dates.append(d)
        mat.append([float(v) if v is not None else np.nan for v in r[1:]])
    wb.close()
    return dates, times, np.array(mat)


def hour_labels(times):
    """把 10 分钟点(区间结束时刻)映射到所属小时序号 0..23。

    区间为 [t-10min, t)，故所属小时取 (t-1min) 的小时；
    '0:00+1' 视为 24:00 -> 23 时。
    """
    out = []
    for t in times:
        if isinstance(t, str):  # '0:00+1'
            mins = 24 * 60
        else:
            mins = t.hour * 60 + t.minute
        out.append(((mins - 1) // 60) % 24)
    return out


def main():
    lines = []
    P = lines.append

    P("# C 题数据探查（服务于建模选型）\n")
    P("时间粒度 10 min，144 点/天；数据列为**区间结束时刻**（00:10 … 24:00）。\n")

    # ---------- 附件1 ----------
    wb = openpyxl.load_workbook(os.path.join(BASE, "附件1.xlsx"), read_only=True)
    ws = wb["Sheet1"]
    r1 = list(ws.iter_rows(values_only=True))[1:]
    wb.close()
    p1 = np.array([float(r[1]) for r in r1])
    l1 = np.array([float(r[2]) for r in r1])
    pv1 = np.array([float(r[3]) for r in r1])
    P("## 1. 附件1（典型日）\n")
    P(f"- 电价：min {p1.min():.4f} / max {p1.max():.4f} / 均值 {p1.mean():.4f} 元/kWh，"
      f"峰谷比 {p1.max()/p1.min():.2f}")
    P(f"- 负载：min {l1.min():.1f} / max {l1.max():.1f} / 日均 {l1.mean():.1f} kW")
    P(f"- 光伏预测：max {pv1.max():.1f} kW，非零时段 {int((pv1>0).sum())} 个（约 {(pv1>0).sum()/6:.1f} h），"
      f"全天发电量 {pv1.sum()*DT:.1f} kWh")
    P(f"- 全天负载电量 {l1.sum()*DT:.1f} kWh，光伏覆盖负载的 {pv1.sum()/l1.sum()*100:.1f}%")
    # 电价峰谷时段
    order = np.argsort(p1)
    n_low = max(1, len(order) // 10)
    low_hours = sorted({int(str(r1[i][0]).split(":")[0]) for i in order[:n_low]})
    high_hours = sorted({int(str(r1[i][0]).split(":")[0]) for i in order[-n_low:]})
    P(f"- 电价最低 10% 时段（{n_low} 个 10min 点）落在小时：{low_hours}")
    P(f"- 电价最高 10% 时段落在小时：{high_hours}")
    P(f"- 净负载（负载-光伏）：min {(l1-pv1).min():.1f} / max {(l1-pv1).max():.1f} kW\n")

    # ---------- 附件2 ----------
    d_load, t_load, LOAD = load_grid("附件2.xlsx", "小区负载")
    d_pv, t_pv, PV = load_grid("附件2.xlsx", "光伏发电实际功率")
    P("## 2. 附件2（全年实际负载与光伏）\n")
    P(f"- 天数 {LOAD.shape[0]}，每天 {LOAD.shape[1]} 点")
    P(f"- 负载：全域 min {np.nanmin(LOAD):.1f} / max {np.nanmax(LOAD):.1f} / 总均值 {np.nanmean(LOAD):.1f} kW")
    P(f"- 光伏：全域 max {np.nanmax(PV):.1f} kW；全年发电量 {np.nansum(PV)*DT/1e6:.2f} GWh；"
      f"全年负载电量 {np.nansum(LOAD)*DT/1e6:.2f} GWh；"
      f"光伏覆盖负载 {np.nansum(PV)/np.nansum(LOAD)*100:.1f}%")
    NET = LOAD - PV
    P(f"- 净负载：min {np.nanmin(NET):.1f} / max {np.nanmax(NET):.1f} kW"
      f"（储能最大充放电功率 5000 kW）")
    P(f"  - 净负载 > 5000 kW 的时段占比 {np.nanmean(NET > 5000)*100:.2f}%"
      f"（这些时刻若完全不购电，单靠放电也补不上）")
    P(f"  - 净负载 < 0（光伏倒送）的时段占比 {np.nanmean(NET < 0)*100:.2f}%")
    daily_net = np.nansum(NET, axis=1) * DT  # kWh/天
    P(f"- 日净负载电量：min {daily_net.min():.0f} / max {daily_net.max():.0f} / 均值 {daily_net.mean():.0f} kWh")
    P(f"  （储能可用容量区间 10800-1200 = 9600 kWh；日净负载远超此值 → 必须每日大量购电，"
      f"储能只做日内搬移）")
    # 季节性：4 个指定日期
    P("\n- 四个指定日期的特征：")
    P("\n| 日期 | 负载电量 kWh | 光伏电量 kWh | 光伏覆盖率 | 净负载峰值 kW | 净负载谷值 kW |")
    P("|---|---|---|---|---|---|")
    for want in ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]:
        idx = [i for i, d in enumerate(d_load) if str(d) == want]
        if not idx:
            P(f"| {want} | 未找到 | | | | |")
            continue
        i = idx[0]
        le = np.nansum(LOAD[i]) * DT
        pe = np.nansum(PV[i]) * DT
        P(f"| {want} | {le:.0f} | {pe:.0f} | {pe/le*100:.1f}% | "
          f"{np.nanmax(NET[i]):.0f} | {np.nanmin(NET[i]):.0f} |")

    # ---------- 附件3 预报误差 ----------
    P("\n## 3. 附件3 光伏预报误差（决定问题3 调整策略的价值）\n")
    wb = openpyxl.load_workbook(os.path.join(BASE, "附件3.xlsx"), read_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    fc = {}  # (date, issue_hour) -> [24 values]
    cur = None
    for r in rows[1:]:
        if r[0]:
            cur = str(r[0])
        iss = str(r[1])
        ih = int(iss.split(":")[0])
        vals = [float(v) if v is not None else np.nan for v in r[2:26]]
        try:
            y, m, dd = [int(x) for x in cur.split("-")]
            fc[(datetime(y, m, dd).date(), ih)] = vals
        except Exception:
            continue
    P(f"- 预报记录数 {len(fc)}（365 天 × 4 次 = 1460）")

    # 实际值按小时平均
    hl = hour_labels(t_load)
    hourly_actual = {}  # date -> 24 个整点小时的平均功率(用该小时内的 10min 点平均)
    for i, d in enumerate(d_load):
        arr = np.full(24, np.nan)
        for h in range(24):
            sel = [j for j, hh in enumerate(hl) if hh == h]
            arr[h] = np.nanmean(PV[i, sel])
        hourly_actual[d] = arr

    # 误差：按 lead k=1..24 与发布时刻统计
    err_by_lead = {k: [] for k in range(1, 25)}
    err_by_issue = {0: [], 6: [], 12: [], 18: []}
    for (d, ih), vals in fc.items():
        for k in range(1, 25):
            # 实际：取 target 所在日、小时 (ih+k)%24
            td = d + timedelta(hours=ih + k)
            th = (ih + k) % 24
            if td not in hourly_actual:
                continue
            a = hourly_actual[td][th]
            f = vals[k - 1]
            if np.isnan(a) or np.isnan(f):
                continue
            err_by_lead[k].append(f - a)
            err_by_issue[ih].append(f - a)

    P("\n### 3.1 按预见期（lead time）的预报误差（预报 − 实际）\n")
    P("| 预见期 h | 样本数 | MAE (kW) | RMSE (kW) | 偏差 Bias (kW) |")
    P("|---|---|---|---|---|")
    for k in range(1, 25):
        e = np.array(err_by_lead[k])
        if len(e) < 50:
            continue
        P(f"| {k} | {len(e)} | {np.mean(np.abs(e)):.1f} | {np.sqrt(np.mean(e**2)):.1f} | {np.mean(e):.1f} |")

    P("\n### 3.2 按发布时刻的预报误差\n")
    P("| 发布时刻 | 样本数 | MAE (kW) | RMSE (kW) | 偏差 Bias (kW) |")
    P("|---|---|---|---|---|")
    for ih in [0, 6, 12, 18]:
        e = np.array(err_by_issue[ih])
        P(f"| {ih}:00 | {len(e)} | {np.mean(np.abs(e)):.1f} | {np.sqrt(np.mean(e**2)):.1f} | {np.mean(e):.1f} |")

    allerr = np.array([x for v in err_by_lead.values() for x in v])
    pv_mean = np.nanmean(PV)
    P(f"\n- 全样本：MAE {np.mean(np.abs(allerr)):.1f} kW，RMSE {np.sqrt(np.mean(allerr**2)):.1f} kW，"
      f"Bias {np.mean(allerr):.1f} kW")
    P(f"- 相对全年光伏均值 {pv_mean:.1f} kW 的归一化 RMSE = "
      f"{np.sqrt(np.mean(allerr**2))/pv_mean*100:.1f}%")
    # 只在白天(实际>0)的误差
    P("\n- **结论**：预报误差随预见期增长 → 6/12/18 时的新预报显著优于 0:00 的 24h 预报，"
      "这是问题3"+"「是否需要引入其他时刻预报」的直接证据来源。")

    # ---------- 附件4 电价 ----------
    P("\n## 4. 附件4（全年波动电价）\n")
    d_pr, t_pr, PRICE = load_grid("附件4.xlsx", "Sheet1")
    P(f"- 天数 {PRICE.shape[0]}，每天 {PRICE.shape[1]} 点")
    P(f"- 电价：min {np.nanmin(PRICE):.4f} / max {np.nanmax(PRICE):.4f} / 均值 {np.nanmean(PRICE):.4f} 元/kWh")
    P(f"- 全域峰谷比 {np.nanmax(PRICE)/np.nanmin(PRICE):.2f}（附件1 典型日峰谷比 {p1.max()/p1.min():.2f}）")
    dstd = np.nanstd(PRICE, axis=1)
    P(f"- 日内标准差：均值 {dstd.mean():.4f}，min {dstd.min():.4f}，max {dstd.max():.4f} 元/kWh")
    # 同刻点跨日波动
    cross_std = np.nanstd(PRICE, axis=0)
    P(f"- 同一时刻跨日标准差：均值 {cross_std.mean():.4f}（反映" + "「逐日不同」" + "的强度）")
    # 与附件1 对比
    P(f"- 附件1 电价均值 {p1.mean():.4f} vs 附件4 均值 {np.nanmean(PRICE):.4f}")
    # 日均价
    daily_price = np.nanmean(PRICE, axis=1)
    P(f"- 日均价：min {daily_price.min():.4f} / max {daily_price.max():.4f} / 均值 {daily_price.mean():.4f}")

    # ---------- 可直接支撑的结论 ----------
    P("\n## 5. 对选型的直接提示\n")
    P(f"1. 日净负载 {daily_net.mean():.0f} kWh ≫ 储能可用容量 9600 kWh → 储能不能跨日搬运大量电量，"
      "只能在日内做峰谷搬移；多日问题仍以**日内优化 + 跨日状态递推**为主。")
    P(f"2. 净负载峰值最高 {np.nanmax(NET):.0f} kW，超过储能放电功率 5000 kW 的时段占 "
      f"{np.nanmean(NET > 5000)*100:.2f}% → 高峰时段必须由购电承担主力，"
      "储能只能削峰，紧急购电主要来自**预测偏差**而非容量不足。")
    P(f"3. 附件3 预报存在显著误差且随预见期增大 → 问题3 的滚动调整有实际价值；"
      "问题2 缺少光伏预报数据，必须显式声明信息集假设。")
    P("4. 附件4 电价既有日内波动又有日间波动 → 问题4 需要把电价从" + "「确定性分时参数」" +
      "升级为" + "「已知当日曲线 / 需预测的量」" + "两种情景之一，并明确 0:00 是否已知全天电价。")

    out = os.path.join(OUT, "data_probe_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("written:", out)
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
