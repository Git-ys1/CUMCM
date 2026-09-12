from __future__ import annotations
import csv,json
from datetime import datetime
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

ROOT=Path(__file__).resolve().parents[1]
FONT=Path(r"C:\Windows\Fonts\msyh.ttc")
fp=FontProperties(fname=str(FONT)) if FONT.exists() else None
plt.rcParams["axes.unicode_minus"]=False
COLORS={"Q2":"#557A95","Q3":"#1B998B","Q4-2":"#D9A441","Q4-3":"#C8553D"}

def j(path): return json.loads(path.read_text(encoding="utf-8"))
def csvrows(path):
    with path.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def label(ax,x,y,fmt="{:.2f}"):
    for xi,yi in zip(x,y): ax.text(xi,yi,fmt.format(yi),ha="center",va="bottom",fontsize=9,fontproperties=fp)

def save(fig,path):
    path.parent.mkdir(parents=True,exist_ok=True); fig.tight_layout(); fig.savefig(path,bbox_inches="tight"); plt.close(fig)

def main():
    # Q1 dispatch
    rows=csvrows(ROOT/"outputs"/"q1"/"solution.csv"); x=np.arange(144)/6
    load=np.array([float(r["load_kw"]) for r in rows]); pv=np.array([float(r["pv_kw"]) for r in rows])
    grid=np.array([float(r["grid_kwh"]) for r in rows])*6
    ch=np.array([float(r["charge_kwh"]) for r in rows])*6; dis=np.array([float(r["discharge_kwh"]) for r in rows])*6
    soc=np.array([float(r["soc_kwh"]) for r in rows]); price=np.array([float(r["price"]) for r in rows])
    fig,(ax1,ax2)=plt.subplots(2,1,figsize=(11,7),sharex=True)
    ax1.plot(x,load,label="负载",lw=1.8,color="#263238"); ax1.plot(x,pv,label="光伏",lw=1.8,color="#E6A700")
    ax1.plot(x,grid,label="外网购电",lw=1.6,color="#386FA4")
    ax1.fill_between(x,0,ch,alpha=.25,color="#1B998B",label="充电功率")
    ax1.fill_between(x,0,-dis,alpha=.25,color="#C8553D",label="放电功率")
    ax1.set_ylabel("功率 / kW",fontproperties=fp); ax1.grid(alpha=.2); ax1.legend(ncol=5,prop=fp,loc="upper center")
    ax2.plot(x,soc,color="#6A4C93",lw=2,label="SOC"); ax2.set_ylabel("储电量 / kWh",fontproperties=fp)
    ax2.set_xlabel("时刻 / h",fontproperties=fp); ax2.grid(alpha=.2)
    axp=ax2.twinx(); axp.step(x,price,where="post",color="#8D6E63",alpha=.75,label="电价")
    axp.set_ylabel("电价 / 元/kWh",fontproperties=fp)
    fig.suptitle("问题1：典型日购电—储能联合调度",fontproperties=fp,fontsize=15)
    save(fig,ROOT/"figures"/"q1"/"q1_dispatch.pdf")

    metrics={name:j(ROOT/"outputs"/folder/"metrics.json") for name,folder in
             [("Q2","q2"),("Q3","q3"),("Q4-2","q4-2"),("Q4-3","q4-3")]}
    names=list(metrics); xpos=np.arange(4)
    costs=np.array([metrics[n]["total_cost_yuan"]/1e4 for n in names])
    fig,ax=plt.subplots(figsize=(8,5)); bars=ax.bar(xpos,costs,color=[COLORS[n] for n in names],width=.62)
    ax.set_xticks(xpos,names); ax.set_ylabel("全年总费用 / 万元",fontproperties=fp); ax.grid(axis="y",alpha=.2)
    ax.set_title("固定与波动电价下的全年费用对比",fontproperties=fp,fontsize=14); label(ax,xpos,costs)
    save(fig,ROOT/"figures"/"comparison"/"annual_cost_comparison.pdf")

    emergency=np.array([metrics[n]["emergency_energy_kwh"]/1e4 for n in names])
    fig,ax=plt.subplots(figsize=(8,5)); ax.bar(xpos,emergency,color=[COLORS[n] for n in names],width=.62)
    ax.set_xticks(xpos,names); ax.set_ylabel("紧急购电量 / 万kWh",fontproperties=fp); ax.grid(axis="y",alpha=.2)
    ax.set_title("滚动预报对 5 倍紧急购电的抑制",fontproperties=fp,fontsize=14); label(ax,xpos,emergency,fmt="{:.3f}")
    save(fig,ROOT/"figures"/"comparison"/"emergency_energy_comparison.pdf")

    variants=[("原始阶梯","q3/variants/raw_step"),("校正阶梯","q3/variants/calibrated_step"),("校正线性","q3")]
    vm=[j(ROOT/"outputs"/p/"metrics.json") for _,p in variants]
    vcost=np.array([m["total_cost_yuan"]/1e4 for m in vm]); vem=np.array([m["emergency_energy_kwh"]/1e4 for m in vm])
    fig,ax=plt.subplots(figsize=(9,5.5)); xx=np.arange(3); width=.34
    b1=ax.bar(xx-width/2,vcost,width,color="#557A95",label="总费用（万元）")
    ax.set_ylabel("总费用 / 万元",fontproperties=fp); ax.set_xticks(xx,[v[0] for v in variants],fontproperties=fp)
    ax2=ax.twinx(); b2=ax2.bar(xx+width/2,vem,width,color="#C8553D",label="紧急购电（万kWh）")
    ax2.set_ylabel("紧急购电量 / 万kWh",fontproperties=fp); ax.grid(axis="y",alpha=.2)
    ax.set_title("Q3 策略变更的完整对照",fontproperties=fp,fontsize=14)
    ax.bar_label(b1,fmt="%.2f",padding=3,fontsize=8)
    ax2.bar_label(b2,fmt="%.3f",padding=3,fontsize=8)
    ax.legend(handles=[b1,b2],labels=["总费用","紧急购电"],prop=fp,loc="upper right")
    save(fig,ROOT/"figures"/"comparison"/"q3_variant_comparison.pdf")

    fig,ax=plt.subplots(figsize=(11,5.5))
    for name,folder in [("Q2","q2"),("Q3","q3"),("Q4-2","q4-2"),("Q4-3","q4-3")]:
        rows=csvrows(ROOT/"outputs"/folder/"daily_metrics.csv")
        dates=np.array([datetime.fromisoformat(r["date"]) for r in rows])
        daily=np.array([float(r["total_cost"]) for r in rows])
        smooth=np.convolve(daily,np.ones(7)/7,mode="same")
        ax.plot(dates[3:-3],smooth[3:-3]/1e4,label=name,color=COLORS[name],lw=1.5)
    ax.set_ylabel("7日移动平均费用 / 万元/日",fontproperties=fp); ax.grid(alpha=.2)
    ax.set_title("全年日费用变化（7日移动平均）",fontproperties=fp,fontsize=14); ax.legend(prop=fp,ncol=4)
    save(fig,ROOT/"figures"/"comparison"/"daily_cost_timeseries.pdf")
    print("generated 5 PDF figures")

if __name__=="__main__": main()
