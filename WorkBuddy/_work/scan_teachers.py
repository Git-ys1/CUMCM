# -*- coding: utf-8 -*-
"""扫描各位老师的解题思路 PDF，抽取页数与关键方法信号，用于横向对比。"""
import os
import re

from pypdf import PdfReader

BASE = r"F:\AcademicHub\000资料相关\数模\26国赛\数模加油站"

FILES = [
    ("蒋老师", r"蒋老师\2026国赛C题解题思路-蒋老师.pdf"),
    ("胡老师", r"胡老师\2026国赛C题解题思路-胡老师.pdf"),
    ("胡老师(第一问)", r"胡老师\2026国赛C题第一问-胡老师.pdf"),
    ("吕老师", r"吕老师\2026国赛C题解题思路-吕老师.pdf"),
    ("张老师", r"张老师\2026国赛C题解题思路-张老师.pdf"),
    ("许老师", r"许老师\2026国赛C题解题思路-许老师.pdf"),
    ("顾老师", r"顾老师\2026国赛C题解题思路-顾老师.pdf"),
]

SIGNALS = {
    "线性规划LP": ["线性规划", "线性规划（LP）", "LP", "linprog", "单纯形", "内点法"],
    "混合整数MILP": ["混合整数", "MILP", "0-1变量", "整数规划"],
    "动态规划": ["动态规划", "DP", "递推", "贝尔曼"],
    "随机/鲁棒": ["随机规划", "鲁棒", "机会约束", "情景树", "蒙特卡洛"],
    "模型预测控制": ["模型预测控制", "MPC", "滚动时域", "滚动优化", "滚动"],
    "弃光变量": ["弃光", "弃电", "弃风", "w_t", "W_t", "剩余光伏", "无法消纳"],
    "紧急购电": ["紧急购电"],
    "初始6000": ["6000"],
    "日循环S0=S24": ["首尾相等", "0:00 与 24:00", "E_0 = E_T", "S0=S144", "日循环"],
    "光伏预测": ["预测", "预报", "预测模型", "日前预测"],
    "灵敏度分析": ["灵敏度", "敏感性"],
    "效率90": ["90%", "0.9", "效率"],
}


def main():
    for name, rel in FILES:
        path = os.path.join(BASE, rel)
        if not os.path.exists(path):
            print(f"### {name}: 缺失")
            continue
        try:
            reader = PdfReader(path)
            npages = len(reader.pages)
            text = []
            for p in reader.pages[: min(npages, 40)]:
                try:
                    text.append(p.extract_text() or "")
                except Exception:
                    pass
            full = "\n".join(text)
        except Exception as exc:
            print(f"### {name}: 读取失败 {exc}")
            continue

        hits = {}
        for k, kws in SIGNALS.items():
            c = sum(full.count(w) for w in kws)
            if c:
                hits[k] = c
        print(f"### {name} | 页数 {npages} | 抽取字符 {len(full)}")
        print("    信号:", ", ".join(f"{k}({v})" for k, v in sorted(hits.items(), key=lambda x: -x[1])))
        # 抓前若干标题行
        heads = [ln.strip() for ln in full.split("\n") if ln.strip()][:6]
        print("    开头:", " / ".join(h[:40] for h in heads))
        print()


if __name__ == "__main__":
    main()
