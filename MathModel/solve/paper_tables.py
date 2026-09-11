from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path
import numpy as np
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=ROOT.parent/'CUMCM2026Problems'/'C题'/'附件'/'附件5'/'result2.xlsx'
DATES=('2025-03-20','2025-06-21','2025-09-23','2025-12-21')
INTERVALS=('10:00-10:10','12:00-12:10','14:00-14:10','16:00-16:10','18:00-18:10','20:00-20:10')
PERIODS=('0:00-4:00','4:00-8:00','8:00-12:00','12:00-16:00','16:00-20:00','20:00-24:00')

def read_rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def emergency_segments(values,tol=1e-7):
    output=[]; start=None
    for idx,active in enumerate(np.r_[np.asarray(values)>tol,False]):
        if active and start is None: start=idx
        elif not active and start is not None:
            def stamp(slot):
                minutes=slot*10
                return '24:00' if minutes==1440 else f'{minutes//60}:{minutes%60:02d}'
            output.append((f'{stamp(start)}-{stamp(idx)}',float(np.sum(values[start:idx]))))
            start=None
    return output

def build():
    wb=openpyxl.load_workbook(TEMPLATE,data_only=True,read_only=True)
    headers=list(next(wb.worksheets[0].iter_rows(min_row=1,max_row=1,values_only=True)))
    slot_index={label:headers.index(label)-1 for label in INTERVALS}
    scenarios=(('Q2','q2',False),('Q3','q3',True),('Q4-2','q4-2',False),('Q4-3','q4-3',True))
    text=['# 论文指定日期结果表','','位置口径：按官方结果模板表头定位六个10分钟区间；储能量按六个4小时块汇总。','']
    for title,folder,is_adjusted in scenarios:
        data=read_rows(ROOT/'outputs'/folder/'solution.csv')
        daily=read_rows(ROOT/'outputs'/folder/'daily_metrics.csv')
        grouped=defaultdict(list)
        for row in data: grouped[row['date']].append(row)
        daily_map={row['date']:row for row in daily}
        text.extend(['## '+title,''])
        for date in DATES:
            day=grouped[date]; drow=daily_map[date]
            text.extend(['### '+date,''])
            if is_adjusted:
                text.extend(['| 指定时段 | 计划购电量/kWh | 调整购电量/kWh |','|---|---:|---:|'])
            else:
                text.extend(['| 指定时段 | 计划购电量/kWh |','|---|---:|'])
            for interval in INTERVALS:
                row=day[slot_index[interval]]
                plan=float(row['baseline_grid_kwh'] if is_adjusted else row['grid_plan_kwh'])
                if is_adjusted: text.append(f'| {interval} | {plan:.4f} | {float(row["adjusted_grid_kwh"]):.4f} |')
                else: text.append(f'| {interval} | {plan:.4f} |')
            if is_adjusted:
                text.append(f'| **全天** | **{sum(float(r["baseline_grid_kwh"]) for r in day):.4f}** | **{sum(float(r["adjusted_grid_kwh"]) for r in day):.4f}** |')
                text.append(f'| **全天购电费** | **{float(drow["baseline_cost"]):.2f}元** | **{float(drow["settlement_cost"]):.2f}元** |')
            else:
                text.append(f'| **全天购电量** | **{sum(float(r["grid_plan_kwh"]) for r in day):.4f}** |')
                text.append(f'| **全天购电费** | **{float(drow["plan_cost"]):.2f}元** |')
            text.extend(['','| 时间段 | 充电量/kWh | 放电量/kWh |','|---|---:|---:|'])
            charge=np.array([float(r['charge_actual_kwh']) for r in day])
            discharge=np.array([float(r['discharge_actual_kwh']) for r in day])
            for block,period in enumerate(PERIODS):
                text.append(f'| {period} | {charge[block*24:(block+1)*24].sum():.4f} | {discharge[block*24:(block+1)*24].sum():.4f} |')
            text.extend([f'| **0:00 / 24:00 SOC** | **{float(drow["soc_initial"]):.4f}** | **{float(drow["soc_terminal"]):.4f}** |','','| 紧急购电时间段 | 购电量/kWh |','|---|---:|'])
            seg=emergency_segments([float(r['emergency_kwh']) for r in day])
            if seg:
                for period,value in seg: text.append(f'| {period} | {value:.4f} |')
            else: text.append('| 无 | 0.0000 |')
            text.append('')
    destination=ROOT/'reports'/'PAPER_TABLES.md'
    destination.write_text('\n'.join(text),encoding='utf-8')
    print(destination)

if __name__=='__main__': build()
