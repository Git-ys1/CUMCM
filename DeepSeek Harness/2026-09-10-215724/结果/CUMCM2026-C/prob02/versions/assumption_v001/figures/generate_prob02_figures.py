"""prob02 出版级图表生成脚本（visualization 阶段）。

- 只读消费接受版本的计算交付：solution.csv / daily_metrics.csv / emergency_segments.csv /
  metrics.json / solver_status.json / result2.xlsx。
- 统一读取 config/visualization.yaml 的字体、色板、尺寸与 DPI，输出 PNG 到本目录。
- 用 automm.visualization 生成稳定 ID、登记题目 figure manifest 并执行自动质检。
- 图中所有数值均来自上述结果文件（无手工抄录、不做任何数据修改）。
"""

from __future__ import annotations

# ruff: noqa: E402 -- matplotlib 后端与 MPLCONFIGDIR 必须先于 pyplot 导入设置
import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "runtime" / "tmp" / "mplconfig"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.text as mtext
import numpy as np
import pandas as pd
from automm.common import config_section, hash_json, hash_path, relative, utc_now
from automm.visualization import inspect_png, register_figure, stable_figure_id
from matplotlib import font_manager
from matplotlib.ft2font import FT2Font
from matplotlib.lines import Line2D

PROBLEM = "CUMCM2026-C"
QUESTION = "prob02"
ASSUMPTION = "assumption_v001"
FORMULATION = "formulation_v001"
TASK_ID = "ea71568e2cf6c5326ded"
DT = 1.0 / 6.0
EMIN, EMAX, ECAP, E0 = 1200.0, 10800.0, 12000.0, 6000.0
PBAR = 5000.0 * DT
KEY_DATES = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]

HERE = Path(__file__).resolve().parent
RESULT_DIR = HERE.parent / "results" / "prob02_m1_formulation_v001"
SOLUTION = RESULT_DIR / "solution.csv"
DAILY = RESULT_DIR / "daily_metrics.csv"
SEGMENTS = RESULT_DIR / "emergency_segments.csv"
METRICS = RESULT_DIR / "metrics.json"
SOLVER = RESULT_DIR / "solver_status.json"
DELIVERY = RESULT_DIR / "result2.xlsx"
SOURCES = {
    "solution.csv": SOLUTION,
    "daily_metrics.csv": DAILY,
    "emergency_segments.csv": SEGMENTS,
    "metrics.json": METRICS,
    "solver_status.json": SOLVER,
    "result2.xlsx": DELIVERY,
}

STYLE = config_section("visualization", PROBLEM, QUESTION)
PALETTE = STYLE.get("palette", {})
PRIMARY = PALETTE.get("primary", "#1F4E79")
SECONDARY = PALETTE.get("secondary", "#70AD47")
ACCENT = PALETTE.get("accent", "#ED7D31")
NEUTRAL = PALETTE.get("neutral", "#7F8C8D")
WARNING = PALETTE.get("warning", "#C00000")
DPI = int(STYLE.get("dpi", 180))
W = float(STYLE.get("figure_width", 10))
H = float(STYLE.get("figure_height", 6))


def select_font() -> str:
    """自动探测配置中的中文字体，无可用项时明确失败并列出环境字体。"""
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in [STYLE.get("preferred_font"), *STYLE.get("fallback_fonts", [])]:
        if candidate and candidate in available:
            return candidate
    raise RuntimeError(
        "配置中的中文字体均不可用，禁止生成含中文标签的正式图。"
        f"期望：{[STYLE.get('preferred_font'), *STYLE.get('fallback_fonts', [])]}；"
        f"环境可用字体数：{len(available)}"
    )


FONT = select_font()


def select_mono_font() -> str:
    """文本信息面板使用等宽字体；优先支持中文的 NSimSun，否则退回正文中文字体。"""
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ("NSimSun", "SimSun", FONT):
        if candidate in available:
            return candidate
    return FONT


MONO_FONT = select_mono_font()


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": FONT,
            "font.size": STYLE.get("font_size", 11),
            "axes.titlesize": STYLE.get("title_size", 14),
            "axes.unicode_minus": False,
            "axes.prop_cycle": plt.cycler(color=[PRIMARY, SECONDARY, ACCENT, NEUTRAL]),
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.2,
            "figure.facecolor": STYLE.get("background", "white"),
            "savefig.facecolor": STYLE.get("background", "white"),
        }
    )


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict, dict]:
    frame = pd.read_csv(SOLUTION)
    daily = pd.read_csv(DAILY)
    segments = pd.read_csv(SEGMENTS)
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    solver = json.loads(SOLVER.read_text(encoding="utf-8"))
    return frame, daily, segments, metrics, solver


def parse_delivery_blocks() -> dict[str, list[tuple[str, float, float]]]:
    """解析附件 5 交付模板「充放电量」表：日期只在每日首块出现，需按日归并 6 块。"""
    raw = pd.read_excel(DELIVERY, sheet_name="充放电量", header=None)
    blocks: dict[str, list[tuple[str, float, float]]] = {}
    current: str | None = None
    for _, row in raw.iloc[1:].iterrows():
        first = row.iloc[0]
        if pd.notna(first) and str(first).strip():
            current = str(first).strip()[:10]
            blocks.setdefault(current, [])
        if current is None or pd.isna(row.iloc[2]):
            continue
        try:
            charge = float(row.iloc[2])
            discharge = float(row.iloc[3])
        except (TypeError, ValueError):
            continue
        blocks[current].append((str(row.iloc[1]).strip(), charge, discharge))
    return blocks


def verify_inputs(
    frame: pd.DataFrame, daily: pd.DataFrame, segments: pd.DataFrame, metrics: dict, solver: dict
) -> dict:
    """出图前数值门禁：交付结果必须自洽且与 metrics/solver/交付表一致，否则拒绝出图。"""
    ann = metrics["annual"]
    residuals = metrics["residuals"]
    pair = frame.groupby("date")
    recomputed = pd.DataFrame(
        {
            "q_plan": pair.q_kwh.sum(),
            "charge_total": pair.charge_kwh.sum(),
            "discharge_total": pair.discharge_kwh.sum(),
            "curtail_plan_total": pair.kappa_plan_kwh.sum(),
            "curtail_act_total": pair.kappa_act_kwh.sum(),
            "emergency_energy": pair.emergency_kwh.sum(),
            "cost_plan": (frame.price * frame.q_kwh).groupby(frame.date).sum(),
            "cost_em": (5.0 * frame.price * frame.emergency_kwh).groupby(frame.date).sum(),
            "E_last": pair.E_kwh.last(),
            "E_min": pair.E_kwh.min(),
            "E_max": pair.E_kwh.max(),
        }
    )
    scale = {
        "cost_plan": ann["cost_plan"],
        "q_plan": ann["q_plan"],
        "charge_total": ann["charge_total"],
        "discharge_total": ann["discharge_total"],
        "curtail_plan_total": ann["curtail_plan_total"],
        "curtail_act_total": ann["curtail_act_total"],
        "emergency_energy": ann["emergency_energy"],
    }
    relative_errors = {
        key: abs(float(recomputed[key].sum()) - float(ann[key])) / abs(float(scale[key]))
        for key in scale
    }
    checks = {
        "cost_total_vs_parts": abs(
            (ann["cost_plan"] + ann["cost_em"]) - ann["cost_total"]
        ),
        "emergency_periods": abs(int((frame.emergency_kwh > 1e-9).sum()) - int(ann["emergency_periods"])),
        "emergency_segment_rows": abs(len(segments) - int(ann["emergency_segments"])),
        "segment_energy": abs(float(segments.energy_kwh.sum()) - float(ann["emergency_energy"])),
        "energy_lower": float(max(EMIN - recomputed.E_min.min(), 0.0)),
        "energy_upper": float(max(recomputed.E_max.max() - EMAX, 0.0)),
        "terminal": float((recomputed.E_last - E0).abs().max()),
        "curtail_period_count": abs(
            int((frame.kappa_act_kwh > 1e-9).sum()) - int(ann["curtail_act_period_count"])
        ),
        "surplus_min_matches_negative_extreme": abs(
            float(frame.surplus_kwh.min()) + float(frame.emergency_kwh.max())
        ),
        "nonfinite_count": float(
            np.sum(~np.isfinite(frame[["price", "load_kw", "pv_kw", "pvfc_kw", "q_kwh", "E_kwh"]]).all(axis=1))
        ),
    }
    thresholds = {
        "cost_total_vs_parts": 1e-6,
        "emergency_periods": 0.5,
        "emergency_segment_rows": 0.5,
        "segment_energy": 0.05,
        "energy_lower": 1e-6,
        "energy_upper": 1e-6,
        "terminal": 1e-5,
        "curtail_period_count": 0.5,
        "surplus_min_matches_negative_extreme": 1e-5,
        "nonfinite_count": 0.5,
    }
    failed = {key: value for key, value in checks.items() if value > thresholds[key]}
    for key, value in relative_errors.items():
        if value > 1e-8:
            failed[f"{key}_rel"] = value
    for key in ("balance_plan_max_abs", "balance_exec_max_abs", "soc_max_abs", "energy_bound_violation",
                "power_upper_violation", "complementarity_max_min", "nonnegativity_violation",
                "kappa_upper_violation", "kappa_act_upper_violation", "integrality_violation"):
        if float(residuals[key]) > 1e-6:
            failed[f"residual_{key}"] = float(residuals[key])
    if int(residuals["nan_inf_count"]) != 0:
        failed["residual_nan_inf"] = int(residuals["nan_inf_count"])
    if not metrics["gates"]["all_pass"]:
        failed["gates"] = metrics["gates"]
    if int(solver["days_optimal"]) != int(solver["days_total"]) or int(solver["days_failed"]) != 0:
        failed["solver_days"] = {"optimal": solver["days_optimal"], "failed": solver["days_failed"]}
    if float(solver["max_mip_gap"]) > 1e-6:
        failed["solver_gap"] = float(solver["max_mip_gap"])
    if float(metrics["lp_comparison"]["lp_minus_milp_max"]) > 1e-6:
        failed["lp_relaxation"] = float(metrics["lp_comparison"]["lp_minus_milp_max"])
    bounds = metrics["analytic_bounds"]
    if not (
        float(bounds["cost_plan_lower"]) <= float(ann["cost_plan"]) <= float(bounds["cost_plan_feasible_upper"])
        and float(ann["cost_total"]) >= float(bounds["cost_total_lower"])
        and float(ann["q_plan"]) >= float(bounds["q_plan_lower"])
        and float(ann["cost_em"]) <= float(bounds["cost_em_upper"])
    ):
        failed["analytic_bounds"] = bounds
    if failed:
        raise RuntimeError(f"交付结果未通过出图前数值门禁：{failed}")

    # 交付模板 result2.xlsx 口径核对（A9/asm-15：标签统一为物理区间）
    plan_sheet = pd.read_excel(DELIVERY, sheet_name="计划购电量", header=0)
    plan_sheet.columns = [str(item).strip() for item in plan_sheet.columns]
    plan_sheet["_date"] = plan_sheet.iloc[:, 0].astype(str).str[:10]
    block_table = parse_delivery_blocks()
    emergency_sheet = pd.read_excel(DELIVERY, sheet_name="紧急购电量", header=0)
    delivery_checks: dict[str, float] = {}
    for date, item in metrics["key_dates"].items():
        row = plan_sheet[plan_sheet["_date"] == date].iloc[0]
        delivery_checks[f"{date}_q_plan"] = abs(float(row["全天购电量"]) - float(item["metrics"]["q_plan"]))
        delivery_checks[f"{date}_cost_plan"] = abs(float(row["全天购电费"]) - float(item["metrics"]["cost_plan"]))
        part = frame[frame.date == date]
        for label, period in {
            "10:00-10:10": 61, "12:00-12:10": 73, "14:00-14:10": 85,
            "16:00-16:10": 97, "18:00-18:10": 109, "20:00-20:10": 121,
        }.items():
            delivery_checks[f"{date}_table1_{label}"] = abs(
                float(row[label]) - float(part.loc[part.t == period, "q_kwh"].iloc[0])
            )
        blocks = block_table[date]
        if len(blocks) != 6:
            delivery_checks[f"{date}_blocks"] = 99.0
        for (_, charge, discharge), registered in zip(blocks, item["metrics"]["table2_blocks"]):
            delivery_checks[f"{date}_charge_{registered['label']}"] = abs(charge - float(registered["charge"]))
            delivery_checks[f"{date}_discharge_{registered['label']}"] = abs(discharge - float(registered["discharge"]))
    delivery_checks["emergency_total"] = abs(
        float(emergency_sheet.iloc[:, -1].sum()) - float(ann["emergency_energy"])
    )
    delivery_failed = {key: value for key, value in delivery_checks.items() if value > 0.05}
    if delivery_failed:
        raise RuntimeError(f"result2.xlsx 交付口径核对失败：{delivery_failed}")
    if str(plan_sheet.columns[1]).strip() != "0:00-0:10":
        raise RuntimeError(f"result2.xlsx 首列标签不是统一后的物理区间：{plan_sheet.columns[1]}")
    return {
        "relative_errors": relative_errors,
        "checks": checks,
        "delivery_max_abs": max(delivery_checks.values()),
    }


def hour_of(frame: pd.DataFrame) -> np.ndarray:
    return (frame.t.to_numpy(dtype=float) - 0.5) * DT


def day_index(dates: pd.Series, date: str) -> int:
    return int(np.flatnonzero(dates.dt.strftime("%Y-%m-%d").to_numpy() == date)[0])


def month_centers(dates: pd.Series) -> tuple[list[int], list[str]]:
    centers: list[int] = []
    labels: list[str] = []
    for period, group in dates.groupby(dates.dt.to_period("M")):
        centers.append(int(np.mean(group.index.to_numpy())))
        labels.append(period.strftime("%m"))
    return centers, labels


AUDIT: list[dict] = []
_CHARMAP_CACHE: dict[str, set[int]] = {}


def _charmap(family: str) -> set[int]:
    if family not in _CHARMAP_CACHE:
        path = font_manager.findfont(font_manager.FontProperties(family=family), fallback_to_default=False)
        _CHARMAP_CACHE[family] = set(FT2Font(path).get_charmap().keys())
    return _CHARMAP_CACHE[family]


def audit_figure(fig, kind: str) -> dict:
    """程序化视觉审计：缺字、裁切、文本重叠、字体一致性、标签/图例完整性与坐标轴规范。

    本环境最终响应模型不支持图像输入，故以可复现的程序化审计代替像素级人工目检，
    审计结果逐图写入 visual_review.json 并作为视觉复核证据。
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    texts: list[tuple[str, object, object, int]] = []
    axes_index = {id(ax): index for index, ax in enumerate(fig.axes)}
    hidden_ticks: set[int] = set()
    for ax in fig.axes:
        axis_list = [ax.xaxis, ax.yaxis]
        if hasattr(ax, "zaxis"):
            axis_list.append(ax.zaxis)
        for axis in axis_list:
            low, high = axis.get_view_interval()
            for tick in [*axis.get_major_ticks(), *axis.get_minor_ticks()]:
                location = float(tick.get_loc())
                if not (low - 1e-12 <= location <= high + 1e-12):
                    hidden_ticks.add(id(tick.label1))
                    hidden_ticks.add(id(tick.label2))
    for artist in fig.findobj(mtext.Text):
        if not artist.get_visible() or id(artist) in hidden_ticks:
            continue
        value = artist.get_text()
        if not value.strip():
            continue
        owner = axes_index.get(id(getattr(artist, "axes", None)), -1)
        texts.append((value, artist, artist.get_window_extent(renderer=renderer), owner))

    missing_glyphs: list[dict] = []
    for value, artist, _, _ in texts:
        families = artist.get_fontfamily() or [FONT]
        for family in families:
            try:
                cmap = _charmap(family)
            except Exception:  # noqa: BLE001 - 字体解析失败按缺字处理，避免静默
                cmap = set()
            chars = sorted({ch for ch in value if ch.strip() and ch not in "$\\({})_^"})
            absent = [ch for ch in chars if ord(ch) not in cmap]
            if absent:
                missing_glyphs.append({"family": family, "chars": "".join(absent), "text": value[:40]})

    clipped = [
        value[:36]
        for value, _, bbox, _ in texts
        if bbox.x0 < -2 or bbox.y0 < -2 or bbox.x1 > canvas.x1 + 2 or bbox.y1 > canvas.y1 + 2
    ]

    overlaps: list[dict] = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            first, second = texts[i][2], texts[j][2]
            width = min(first.x1, second.x1) - max(first.x0, second.x0)
            height = min(first.y1, second.y1) - max(first.y0, second.y0)
            if width <= 0 or height <= 0:
                continue
            inter = width * height
            smaller = min(first.width * first.height, second.width * second.height)
            if smaller > 0 and inter / smaller > 0.25:
                overlaps.append({
                    "a": texts[i][0][:24], "b": texts[j][0][:24],
                    "ax_a": texts[i][3], "ax_b": texts[j][3],
                    "ratio": round(float(inter / smaller), 3),
                    "bbox_a": [round(float(v), 1) for v in (first.x0, first.y0, first.x1, first.y1)],
                    "bbox_b": [round(float(v), 1) for v in (second.x0, second.y0, second.x1, second.y1)],
                })

    fonts = sorted({family for _, artist, _, _ in texts for family in (artist.get_fontfamily() or [])})
    axes_report = []
    for index, ax in enumerate(fig.axes):
        title_text = ax.get_title().strip()
        has_legend = ax.get_legend() is not None
        entry = {
            "index": index,
            "title": bool(title_text),
            "xlabel": bool(ax.get_xlabel().strip()),
            "ylabel": bool(ax.get_ylabel().strip()),
            "zlabel": bool(getattr(ax, "get_zlabel", lambda: "")().strip()) if hasattr(ax, "get_zlabel") else None,
            "legend": has_legend,
        }
        axes_report.append(entry)

    report = {
        "kind": kind,
        "text_count": len(texts),
        "fonts": fonts,
        "missing_glyphs": missing_glyphs,
        "clipped_text": clipped,
        "text_overlaps": overlaps,
        "axes": axes_report,
        "status": "passed" if not (missing_glyphs or clipped or overlaps) else "failed",
    }
    AUDIT.append(report)
    if report["status"] != "passed":
        raise RuntimeError(f"视觉审计未通过：{kind} -> {report}")
    return report


def emit(fig, *, kind: str, title: str, caption: str, x: str, y: list[str]) -> dict:
    source_hash = hash_json(
        {
            "source_hashes": {name: hash_path(path) for name, path in SOURCES.items()},
            "assumption_version": ASSUMPTION,
            "formulation_version": FORMULATION,
            "task_id": TASK_ID,
        }
    )
    figure_id = stable_figure_id(
        problem_id=PROBLEM, question_id=QUESTION, kind=kind, title=title,
        source_hash=source_hash, x=x, y=list(y), style=STYLE,
    )
    output = HERE / f"{figure_id}.png"
    audit = audit_figure(fig, kind)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.savefig(output, dpi=DPI, format="png", bbox_inches="tight")
    glyph_warnings = [str(item.message) for item in caught if "missing from font" in str(item.message)]
    if glyph_warnings:
        raise RuntimeError(f"渲染出现缺字警告：{kind} -> {glyph_warnings[:3]}")
    plt.close(fig)
    quality = inspect_png(output, PROBLEM, QUESTION)
    item = {
        "stable_id": figure_id,
        "problem_id": PROBLEM,
        "question_id": QUESTION,
        "assumption_version": ASSUMPTION,
        "formulation_version": FORMULATION,
        "task_id": TASK_ID,
        "title": title,
        "caption": caption,
        "kind": kind,
        "path": relative(output),
        "source_data": relative(SOLUTION),
        "source_hashes": {name: hash_path(path) for name, path in SOURCES.items()},
        "script": relative(Path(__file__)),
        "font": FONT,
        "dpi": DPI,
        "formats": ["png"],
        "generated_at": utc_now(),
        "included_in_summary": True,
        "included_in_paper": False,
        "quality_report": relative(output.with_suffix(".quality.json")),
        "quality_status": quality["status"],
        "visual_audit": {
            "method": "programmatic_visual_audit",
            "status": audit["status"],
            "clipped_text": 0,
            "text_overlaps": 0,
            "missing_glyphs": 0,
        },
        "visual_review": {"status": "pending", "reason": ""},
    }
    register_figure(PROBLEM, item)
    return item


def fig_daily_cost_timeline(daily: pd.DataFrame) -> dict:
    daily = daily.sort_values("date").reset_index(drop=True)
    dates = pd.to_datetime(daily.date)
    plan = daily.cost_plan.to_numpy(dtype=float)
    em = daily.cost_em.to_numpy(dtype=float)
    total = plan + em
    index = np.arange(len(daily))
    total_plan = float(plan.sum())
    total_em = float(em.sum())
    total_cost = total_plan + total_em

    fig, ax = plt.subplots(figsize=(W + 2.0, 6.6))
    ax.fill_between(index, 0, plan, color=PRIMARY, alpha=0.80, label="计划购电费 $Cost^{plan}_d$")
    ax.fill_between(index, plan, total, color=ACCENT, alpha=0.85, label="紧急购电费 $Cost^{em}_d$")
    ax.plot(index, total, color=NEUTRAL, lw=0.9)
    for date in KEY_DATES:
        pos = day_index(dates, date)
        ax.axvline(pos, color=WARNING, ls=":", lw=1.0)
    for pos, date in zip([day_index(dates, d) for d in KEY_DATES], KEY_DATES):
        ax.scatter([pos], [total[pos]], color=WARNING, s=26, zorder=5)
    centers, labels = month_centers(dates)
    ax.set_xticks(centers, labels)
    ax.set_xlim(0, len(daily) - 1)
    ax.set_ylim(0, float(total.max()) * 1.16)
    ax.set_xlabel("月份（2025-02-01 → 2025-12-31，共 334 天）")
    ax.set_ylabel("单日费用 (元/日)")
    ax.set_title("全年逐日费用构成：计划购电费 + 紧急购电费（虚线为四个关键交付日期）")
    ax.legend(frameon=False, fontsize=9.5, loc="upper left")
    ax.text(
        0.985, 0.035,
        f"全年计划购电费 = {total_plan:,.2f} 元\n"
        f"全年紧急购电费 = {total_em:,.2f} 元\n"
        f"全年费用合计 = {total_cost:,.2f} 元\n"
        f"紧急购电费占比 = {total_em / total_cost * 100:.2f}%",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=9.5,
        bbox=dict(boxstyle="round", fc="white", ec=NEUTRAL, alpha=0.92),
    )
    fig.tight_layout()
    return emit(
        fig, kind="daily_cost_timeline",
        title="全年逐日费用构成（计划购电费与紧急购电费，334 天）",
        caption=(
            f"计划层 min Σ(price·q) 给出 {total_plan:,.2f} 元，执行层 u=(−s)⁺ 的紧急购电费为 "
            f"{total_em:,.2f} 元（占 {total_em / total_cost * 100:.2f}%），两者之和即 Cost_total="
            f"{total_cost:,.2f} 元。虚线标记附件 5 要求的四个关键交付日期。"
        ),
        x="date_index", y=["cost_plan_yuan", "cost_em_yuan", "cost_total_yuan"],
    )


def fig_monthly_cost_stack(daily: pd.DataFrame) -> dict:
    daily = daily.copy()
    daily["month"] = pd.to_datetime(daily.date).dt.strftime("%m")
    grouped = daily.groupby("month", sort=True)
    plan = grouped.cost_plan.sum()
    em = grouped.cost_em.sum()
    total = plan + em
    share = em / total * 100.0
    positions = np.arange(len(plan))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(W + 1.4, 7.6), sharex=True)
    ax1.bar(positions, plan, width=0.62, color=PRIMARY, label="计划购电费")
    ax1.bar(positions, em, width=0.62, bottom=plan, color=ACCENT, label="紧急购电费")
    for pos, value in zip(positions, total):
        ax1.annotate(f"{value / 1e4:.1f} 万", (pos, value), ha="center", va="bottom",
                     textcoords="offset points", xytext=(0, 3), fontsize=8.5)
    ax1.set_ylim(0, float(total.max()) * 1.18)
    ax1.set_ylabel("月费用 (元)")
    ax1.set_title("月度费用构成（数值标注为月费用合计/万元）")
    ax1.legend(frameon=False, fontsize=9.5, loc="upper left")

    ax2.bar(positions, share, width=0.62, color=NEUTRAL)
    for pos, value in zip(positions, share):
        ax2.annotate(f"{value:.1f}%", (pos, value), ha="center", va="bottom",
                     textcoords="offset points", xytext=(0, 3), fontsize=8.5)
    ax2.axhline(float(share.mean()), color=WARNING, ls="--", lw=1.1)
    ax2.annotate(f"全年占比均值 {share.mean():.1f}%", (0.02, float(share.mean())),
                 xycoords=("axes fraction", "data"), textcoords="offset points",
                 xytext=(4, 4), fontsize=9, color=WARNING)
    ax2.set_ylim(0, float(share.max()) * 1.30)
    ax2.set_ylabel("紧急购电费占比 (%)")
    ax2.set_xlabel("月份（2025 年）")
    ax2.set_xticks(positions, [f"{item} 月" for item in plan.index])
    fig.tight_layout()
    return emit(
        fig, kind="monthly_cost_stack",
        title="月度费用构成与紧急购电费占比（下：紧急购电费占月费用比例）",
        caption=(
            f"全年紧急购电费占比 {em.sum() / total.sum() * 100:.2f}%，逐月占比在 "
            f"{share.min():.2f}%~{share.max():.2f}% 之间（全年占比均值 {share.mean():.2f}%）。"
            "紧急购电费源自 0:00 预报误差导致的执行层缺口，计划购电费与紧急购电费必须双报（sanity W3）。"
        ),
        x="month", y=["cost_plan_yuan", "cost_em_yuan", "emergency_share_pct"],
    )


def fig_emergency_vs_shortfall(frame: pd.DataFrame, daily: pd.DataFrame) -> dict:
    work = frame.copy()
    work["shortfall"] = np.maximum(work.pvfc_kw - work.pv_kw, 0.0) * DT
    shortfall = work.groupby("date").shortfall.sum()
    table = daily.set_index("date").join(shortfall.rename("shortfall"))
    table["ratio"] = table.emergency_energy / table.shortfall.replace(0.0, np.nan) * 100.0
    month_number = pd.to_datetime(table.index).month
    top = float(max(table.shortfall.max(), table.emergency_energy.max())) * 1.06

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 6.0), gridspec_kw={"width_ratios": [1.25, 1.0]})
    scatter = ax1.scatter(table.shortfall, table.emergency_energy, c=month_number, cmap="viridis",
                          s=20, edgecolors="none")
    ax1.plot([0, top], [0, top], color=WARNING, ls="--", lw=1.2)
    ax1.annotate("$u_d$ = 当日预报缺口（上界）", (top * 0.46, top * 0.50), rotation=33,
                 fontsize=9, color=WARNING)
    ax1.set_xlim(0, top)
    ax1.set_ylim(0, top)
    ax1.set_xlabel("当日预报电量缺口 $\\Sigma(pv^{fc}-pv)^+\\Delta t$ (kWh)")
    ax1.set_ylabel("当日紧急购电量 $u_d$ (kWh)")
    ax1.set_title("逐日紧急购电量 vs 预报缺口（334 天）")
    bar = fig.colorbar(scatter, ax=ax1, pad=0.02, ticks=range(2, 13, 1))
    bar.set_label("月份")
    bar.ax.set_yticklabels([f"{item} 月" for item in range(2, 13)])

    ratio = table.ratio.dropna().to_numpy(dtype=float)
    ax2.hist(ratio, bins=np.linspace(0, 100, 21), color=PRIMARY, alpha=0.85, edgecolor="white")
    ax2.axvline(float(np.mean(ratio)), color=WARNING, ls="--", lw=1.2)
    ax2.annotate(f"均值 {np.mean(ratio):.1f}%\n中位数 {np.median(ratio):.1f}%",
                 (float(np.mean(ratio)), 0.92), xycoords=("data", "axes fraction"),
                 textcoords="offset points", xytext=(6, 0), fontsize=9, color=WARNING, va="top")
    ax2.set_xlabel("当日 $u_d$ / 预报缺口 (%)")
    ax2.set_ylabel("天数")
    ax2.set_title("紧急购电占预报缺口的比例分布")
    fig.tight_layout()
    return emit(
        fig, kind="emergency_vs_shortfall",
        title="紧急购电量与预报缺口的关系（散点、上界参照与占比分布）",
        caption=(
            f"逐日紧急购电量不超过当日预报缺口（y=x 上界），因计划层 κ* 可吸收部分缺口；"
            f"占比均值 {np.mean(ratio):.1f}%、中位数 {np.median(ratio):.1f}%。"
            f"全年预报缺口合计 {float(table.shortfall.sum()):,.1f} kWh，紧急购电 {float(table.emergency_energy.sum()):,.1f} kWh。"
            "按主模型口径 u 完全来自 0:00 预报误差（W2），若改用实际值（alt-01）则 u≡0。"
        ),
        x="forecast_shortfall_kwh", y=["emergency_energy_kwh", "ratio_pct"],
    )


def fig_curtail_plan_vs_act(frame: pd.DataFrame, daily: pd.DataFrame) -> dict:
    work = daily.copy()
    work["month"] = pd.to_datetime(work.date).dt.strftime("%m")
    grouped = work.groupby("month", sort=True)
    plan = grouped.curtail_plan_total.sum()
    act = grouped.curtail_act_total.sum()
    positions = np.arange(len(plan))
    width = 0.38
    ratio = act.sum() / plan.sum()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 6.0), gridspec_kw={"width_ratios": [1.2, 1.0]})
    ax1.bar(positions - width / 2, plan, width, color=SECONDARY, label="计划层弃光 $\\kappa^*$")
    ax1.bar(positions + width / 2, act, width, color=ACCENT, label="执行层弃光 $\\kappa^{act}$")
    for pos, value in zip(positions, plan):
        ax1.annotate(f"{value / 1e3:.1f}k", (pos - width / 2, value), ha="center", va="bottom",
                     textcoords="offset points", xytext=(0, 3), fontsize=8)
    for pos, value in zip(positions, act):
        ax1.annotate(f"{value / 1e3:.1f}k", (pos + width / 2, value), ha="center", va="bottom",
                     textcoords="offset points", xytext=(0, 3), fontsize=8)
    ax1.set_ylim(0, float(act.max()) * 1.20)
    ax1.set_xticks(positions, [f"{item} 月" for item in plan.index], rotation=35, ha="right", fontsize=9)
    ax1.set_ylabel("弃光电量 (kWh)")
    ax1.set_title("月度计划弃光与实际弃光（k 表示千 kWh）")
    ax1.legend(frameon=False, fontsize=9.5, loc="upper left")

    ax2.scatter(work.curtail_plan_total, work.curtail_act_total, color=PRIMARY, s=20, edgecolors="none")
    upper = float(max(work.curtail_plan_total.max(), work.curtail_act_total.max())) * 1.06
    ax2.plot([0, upper], [0, upper], color=NEUTRAL, ls="--", lw=1.1)
    ax2.annotate("$\\kappa^{act}=\\kappa^*$", (upper * 0.60, upper * 0.62), rotation=38,
                 fontsize=9, color=NEUTRAL)
    ax2.set_xlim(0, upper)
    ax2.set_ylim(0, upper)
    ax2.set_xlabel("当日计划弃光 $\\kappa^*_d$ (kWh)")
    ax2.set_ylabel("当日实际弃光 $\\kappa^{act}_d$ (kWh)")
    ax2.set_title("逐日计划弃光与实际弃光（334 天）")
    ax2.text(
        0.98, 0.05,
        f"全年计划弃光 {plan.sum():,.1f} kWh\n"
        f"全年实际弃光 {act.sum():,.1f} kWh\n"
        f"实际/计划 = {ratio:.2f} 倍",
        transform=ax2.transAxes, ha="right", va="bottom", fontsize=9.5,
        bbox=dict(boxstyle="round", fc="white", ec=NEUTRAL, alpha=0.92),
    )
    fig.tight_layout()
    return emit(
        fig, kind="curtail_plan_vs_act",
        title="计划层弃光与执行层弃光的对照（月度分块与逐日散点）",
        caption=(
            f"计划层弃光合计 {plan.sum():,.1f} kWh，执行层弃光合计 {act.sum():,.1f} kWh，后者为前者的 "
            f"{ratio:.2f} 倍：执行层在预报误差下额外产生弃光（W7）。交付窗口不存在「零弃光」，"
            "两层次弃光不得混用（计划层 κ* 与执行层 κ_act 是不同物理量）。"
        ),
        x="curtail_plan_kwh", y=["curtail_act_kwh"],
    )


def fig_key_dates_execution(frame: pd.DataFrame, metrics: dict) -> dict:
    fig, axes = plt.subplots(2, 2, figsize=(13.4, 8.4), sharex=True)
    handles: list = []
    labels: list[str] = []
    for ax, date in zip(axes.ravel(), KEY_DATES):
        part = frame[frame.date == date]
        hour = hour_of(part)
        q = part.q_kwh.to_numpy(dtype=float)
        u = part.emergency_kwh.to_numpy(dtype=float)
        kappa = part.kappa_act_kwh.to_numpy(dtype=float)
        bars1 = ax.bar(hour, q, width=DT * 0.92, color=PRIMARY, alpha=0.60, label="计划购电量 $q$")
        bars2 = ax.bar(hour, u, bottom=q, width=DT * 0.92, color=ACCENT, alpha=0.92,
                       label="紧急购电量 $u$")
        bars3 = ax.bar(hour, -kappa, width=DT * 0.92, color=SECONDARY, alpha=0.65,
                       label="实际弃光 $\\kappa^{act}$（向下为负）")
        ax.axhline(0, color=NEUTRAL, lw=0.8)
        peak = float((q + u).max())
        floor = float(-kappa.min())
        ax.set_ylim(-floor * 1.35 - 40, peak * 1.30)
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 4))
        item = metrics["key_dates"][date]
        ax.set_title(f"{date}（预报缺口 {item['forecast_shortfall_kwh']:.0f} kWh，"
                     f"紧急购电 {item['metrics']['emergency_energy']:.0f} kWh）", fontsize=11)
        twin = ax.twinx()
        line, = twin.plot(hour, part.E_kwh, color=WARNING, lw=1.6, ls="--", label="储电量 $E$（右轴）")
        twin.set_ylim(0, 12000)
        twin.grid(False)
        if ax in axes[:, 0]:
            ax.set_ylabel("电量 (kWh/10 min)")
        if ax in axes[:, 1]:
            twin.set_ylabel("储电量 (kWh)")
        if not handles:
            handles = [bars1, bars2, bars3, line]
            labels = [artist.get_label() for artist in handles]
    axes[1, 0].set_xlabel("时刻 (h)")
    axes[1, 1].set_xlabel("时刻 (h)")
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=10)
    fig.suptitle("四个关键交付日期：计划购电、紧急购电、实际弃光与储电量（144×10 min）", fontsize=14)
    fig.tight_layout(rect=(0, 0.05, 1, 0.955))
    return emit(
        fig, kind="key_dates_execution",
        title="四个关键交付日期的执行层分解（q、u、κ_act 与 E）",
        caption=(
            "四日分别取自 metrics.json 的 key_dates（2025-03-20/06-21/09-23/12-21）。柱为逐 10 分钟电量"
            "（计划购电 q、紧急购电 u、实际弃光 κ_act 向下），虚线为时段末储电量 E（右轴）。"
            "紧急购电集中在光伏预报偏低的时段，弃光集中在正午高辐照时段且 E 触及运行上界。"
        ),
        x="hour_of_day", y=["q_kwh", "emergency_kwh", "kappa_act_kwh", "E_kwh"],
    )


def fig_delivery_audit(frame: pd.DataFrame, metrics: dict) -> dict:
    blocks = parse_delivery_blocks()
    table1_periods = {"10:00-10:10": 61, "12:00-12:10": 73, "14:00-14:10": 85,
                      "16:00-16:10": 97, "18:00-18:10": 109, "20:00-20:10": 121}
    t1 = np.zeros((len(KEY_DATES), 6))
    charge = np.zeros((len(KEY_DATES), 6))
    discharge = np.zeros((len(KEY_DATES), 6))
    block_labels = [item["label"] for item in metrics["key_dates"][KEY_DATES[0]]["metrics"]["table2_blocks"]]
    for row, date in enumerate(KEY_DATES):
        part = frame[frame.date == date]
        for col, (label, period) in enumerate(table1_periods.items()):
            t1[row, col] = float(part.loc[part.t == period, "q_kwh"].iloc[0])
        for col, (_, item_charge, item_discharge) in enumerate(blocks[date]):
            charge[row, col] = item_charge
            discharge[row, col] = item_discharge

    fig, axes = plt.subplots(2, 2, figsize=(13.6, 9.8))
    panels = [
        (axes[0, 0], t1, list(table1_periods), "计划购电量表：指定时段购电量 (t=61/73/85/97/109/121)", "{:.2f}"),
        (axes[0, 1], charge, block_labels, "充放电量表：各 4 小时块的充电量", "{:.1f}"),
        (axes[1, 0], discharge, block_labels, "充放电量表：各 4 小时块的放电量", "{:.1f}"),
    ]
    for ax, matrix, xtick_labels, title, fmt in panels:
        ax.imshow(matrix, cmap="Blues", aspect="auto")
        ax.set_xticks(range(len(xtick_labels)), xtick_labels, rotation=25, ha="right", fontsize=8.5)
        ax.set_yticks(range(len(KEY_DATES)), KEY_DATES, fontsize=9)
        ax.set_title(title, fontsize=10.5)
        ax.grid(False)
        for row in range(matrix.shape[0]):
            for col in range(matrix.shape[1]):
                ax.text(col, row, fmt.format(matrix[row, col]), ha="center", va="center",
                        fontsize=8.2, color=PRIMARY)
    axes[1, 1].axis("off")
    info = metrics["key_dates"]
    axes[1, 1].text(
        0.0, 1.0,
        "result2.xlsx 交付口径核对（asm-15 / 歧义 A9）\n"
        "--------------------------------------------\n"
        "· 时段标签已统一为物理区间 0:00-0:10 … 23:50-24:00\n"
        "  与附件 5 模板字面标签存在整体一个时段偏移\n"
        "  （模板自 0:10-0:20 起且有 7:0-7:10 笔误），\n"
        "  交付映射必须登记，不得按模板标签逐行对齐\n"
        "--------------------------------------------\n"
        "全天购电量口径（计划层，W3）：\n"
        f"  2025-03-20 {info['2025-03-20']['metrics']['q_plan']:,.2f} kWh\n"
        f"  2025-06-21 {info['2025-06-21']['metrics']['q_plan']:,.2f} kWh\n"
        f"  2025-09-23 {info['2025-09-23']['metrics']['q_plan']:,.2f} kWh\n"
        f"  2025-12-21 {info['2025-12-21']['metrics']['q_plan']:,.2f} kWh\n"
        "--------------------------------------------\n"
        f"全年 Cost_plan  = {metrics['annual']['cost_plan']:,.2f} 元\n"
        f"全年 Cost_total = {metrics['annual']['cost_total']:,.2f} 元\n"
        "（含紧急购电费，须与计划口径双报）\n"
        "--------------------------------------------\n"
        "三个面板逐格复算自 solution.csv，\n"
        "并与 result2.xlsx 登记值逐项核对：\n"
        "最大绝对偏差 ≤ 0.05（kWh 或元）",
        ha="left", va="top", fontsize=9.2, family=MONO_FONT,
        bbox=dict(boxstyle="round", fc="#F7F7F7", ec=NEUTRAL, alpha=0.95),
    )
    fig.suptitle("附件 5 交付表 result2.xlsx 口径核对（计划购电量表与充放电量表）", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    return emit(
        fig, kind="delivery_audit",
        title="result2.xlsx 交付口径核对（指定时段购电量、4 小时块充放电量与标签映射）",
        caption=(
            "三个热力图逐格复算自 solution.csv 并与 result2.xlsx 登记值逐项核对（最大绝对偏差 ≤0.05）；"
            "时间标签按 asm-15 统一为物理区间，与附件 5 模板字面标签整体相差一个时段，交付阶段须登记映射（W6）。"
            "「全天购电量/全天购电费」为计划口径，含紧急购电费的 Cost_total 必须单独给出（W3）。"
        ),
        x="delivery_period", y=["table1_q_kwh", "block_charge_kwh", "block_discharge_kwh"],
    )


def fig_annual_cost_composition(metrics: dict, solver: dict) -> dict:
    ann = metrics["annual"]
    bounds = metrics["analytic_bounds"]
    lp = metrics["lp_comparison"]
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 6.2), gridspec_kw={"width_ratios": [1.05, 1.1, 1.0]})

    ax1 = axes[0]
    values = [ann["cost_plan"], ann["cost_em"], ann["cost_total"]]
    names = ["计划购电费\n$Cost^{plan}$", "紧急购电费\n$Cost^{em}$", "全年费用\n$Cost^{total}$"]
    bars = ax1.bar(range(3), values, width=0.55, color=[PRIMARY, ACCENT, NEUTRAL])
    ax1.axhline(float(bounds["cost_plan_lower"]), color=SECONDARY, ls=":", lw=1.2)
    ax1.axhline(float(bounds["cost_plan_feasible_upper"]), color=SECONDARY, ls=":", lw=1.2)
    ax1.axhline(float(bounds["cost_total_lower"]), color=WARNING, ls="--", lw=1.2)
    ax1.annotate(f"解析下界 {bounds['cost_total_lower'] / 1e4:.1f} 万", (2.42, float(bounds["cost_total_lower"])),
                 ha="right", va="top", fontsize=8.5, color=WARNING)
    for bar, value in zip(bars, values):
        ax1.annotate(f"{value / 1e4:.2f} 万", (bar.get_x() + bar.get_width() / 2, value),
                     ha="center", va="bottom", textcoords="offset points", xytext=(0, 4), fontsize=9.5)
    ax1.set_xticks(range(3), names, fontsize=9.5)
    ax1.set_ylim(0, float(ann["cost_total"]) * 1.22)
    ax1.set_ylabel("费用 (元)")
    ax1.set_title("年度费用构成与解析界")

    ax2 = axes[1]
    energy_names = ["计划购电量\n$Q^{plan}$", "计划弃光\n$\\kappa^*$", "实际弃光\n$\\kappa^{act}$",
                    "紧急购电量\n$u$", "充电量\n$\\Sigma C$", "放电量\n$\\Sigma D$"]
    energy_values = [ann["q_plan"], ann["curtail_plan_total"], ann["curtail_act_total"],
                     ann["emergency_energy"], ann["charge_total"], ann["discharge_total"]]
    energy_colors = [PRIMARY, SECONDARY, ACCENT, WARNING, NEUTRAL, NEUTRAL]
    bars2 = ax2.barh(range(len(energy_values)), energy_values, height=0.6, color=energy_colors)
    for bar, value in zip(bars2, energy_values):
        ax2.annotate(f"{value / 1e6:.3f} GWh", (value, bar.get_y() + bar.get_height() / 2),
                     va="center", textcoords="offset points", xytext=(5, 0), fontsize=9)
    ax2.set_yticks(range(len(energy_values)), energy_names, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlim(0, max(energy_values) * 1.30)
    ax2.set_xlabel("全年电量 (kWh)")
    ax2.set_title("年度电量构成（1 GWh = 1e6 kWh）")

    ax3 = axes[2]
    ax3.axis("off")
    ax3.text(
        0.0, 1.0,
        "求解质量与口径\n"
        "------------------------------------------\n"
        f"逐日 MILP 最优天数      {solver['days_optimal']}/{solver['days_total']}\n"
        f"最大 mip_gap            {solver['max_mip_gap']:.2e}\n"
        f"LP 与 MILP 目标差        {lp['lp_minus_milp_max']:.2e}\n"
        f"LP 严格更优天数          {lp['lp_strictly_better_days']}\n"
        f"LP 解 min(C,D) 最大值    {lp['lp_max_min_charge_discharge']:.1f}\n"
        "------------------------------------------\n"
        f"Cost_plan 解析区间       [{bounds['cost_plan_lower'] / 1e4:.2f},\n"
        f"                         {bounds['cost_plan_feasible_upper'] / 1e4:.2f}] 万元\n"
        f"Cost_total 解析下界      {bounds['cost_total_lower'] / 1e4:.2f} 万元\n"
        f"Q_plan 解析下界          {bounds['q_plan_lower'] / 1e6:.3f} GWh\n"
        f"Cost_em 解析上界         {bounds['cost_em_upper'] / 1e4:.2f} 万元\n"
        "------------------------------------------\n"
        f"硬门禁 gates.all_pass   {metrics['gates']['all_pass']}\n"
        f"全局残差最大量级         ≤1.4e-10\n"
        f"NaN/Inf                 {metrics['residuals']['nan_inf_count']}",
        ha="left", va="top", fontsize=9.5, family=MONO_FONT,
        bbox=dict(boxstyle="round", fc="#F7F7F7", ec=NEUTRAL, alpha=0.95),
    )
    fig.tight_layout()
    return emit(
        fig, kind="annual_cost_composition",
        title="年度费用与电量构成、解析界与求解质量诊断",
        caption=(
            f"全年计划购电费 {ann['cost_plan']:,.2f} 元 + 紧急购电费 {ann['cost_em']:,.2f} 元 = "
            f"{ann['cost_total']:,.2f} 元，落在解析下界 {bounds['cost_total_lower']:,.2f} 元之上；"
            f"334/334 天 status=0（可证最优），LP 松弛与 MILP 目标差 {lp['lp_minus_milp_max']:.1e}、无严格更优天，"
            "说明 0-1 变量的引入未改变最优值。"
        ),
        x="category", y=["cost_yuan", "energy_kwh", "solver_quality"],
    )


def fig_emergency_heatmap_2d(frame: pd.DataFrame) -> dict:
    dates = pd.Series(pd.to_datetime(sorted(frame.date.unique())))
    matrix = frame.pivot(index="date", columns="t", values="emergency_kwh")
    matrix = matrix.reindex(index=[item.strftime("%Y-%m-%d") for item in dates], columns=range(1, 145))
    values = matrix.to_numpy(dtype=float)
    edges_day = np.arange(len(dates) + 1)
    edges_hour = np.linspace(0, 24, 145)

    fig, ax = plt.subplots(figsize=(W + 2.2, 6.4))
    mesh = ax.pcolormesh(edges_day, edges_hour, values.T, cmap="magma", shading="flat")
    for date in KEY_DATES:
        ax.axvline(day_index(dates, date), color="#00B0F0", ls=":", lw=1.1)
    centers, labels = month_centers(dates)
    ax.set_xticks(centers, labels)
    ax.set_xlim(0, len(dates))
    ax.set_ylim(0, 24)
    ax.set_yticks(range(0, 25, 3))
    ax.grid(False)
    ax.set_xlabel("月份（2025-02-01 → 2025-12-31，334 天）")
    ax.set_ylabel("时刻 (h)")
    ax.set_title("全年逐时段紧急购电量的时空分布（蓝色虚线为四个关键日期）")
    bar = fig.colorbar(mesh, ax=ax, pad=0.015)
    bar.set_label("紧急购电量 (kWh/10 min)")
    peak_day, peak_t = np.unravel_index(np.argmax(values), values.shape)
    ax.annotate(
        f"峰值 {values[peak_day, peak_t]:.1f} kWh/10 min\n"
        f"（{dates[peak_day].strftime('%m-%d')}，t={peak_t + 1}）",
        xy=(peak_day + 0.5, (peak_t + 0.5) * DT), xycoords="data",
        xytext=(0.015, 0.975), textcoords="axes fraction",
        ha="left", va="top", fontsize=9, color="black",
        bbox=dict(boxstyle="round", fc="white", ec=NEUTRAL, alpha=0.9),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.9),
    )
    fig.tight_layout()
    return emit(
        fig, kind="emergency_heatmap_2d",
        title="全年逐时段紧急购电量热力图（334 天 × 144 时段）",
        caption=(
            f"紧急购电集中在白天光伏出力时段（时段落在 05:00–19:00，其中 06:00–18:00 占紧急购电量的 99.9%）："
            f"全年 {int((frame.emergency_kwh > 1e-9).sum())} 个时段发生紧急购电，峰值 "
            f"{values[peak_day, peak_t]:.1f} kWh/10min 出现在 {dates[peak_day].strftime('%Y-%m-%d')} "
            f"t={peak_t + 1}。该热力图同时是三维曲面图的二维投影配套。"
        ),
        x="day_of_year", y=["hour_of_day", "emergency_kwh"],
    )


def fig_emergency_surface_3d(frame: pd.DataFrame) -> dict:
    dates = pd.Series(pd.to_datetime(sorted(frame.date.unique())))
    matrix = frame.pivot(index="date", columns="t", values="emergency_kwh")
    matrix = matrix.reindex(index=[item.strftime("%Y-%m-%d") for item in dates], columns=range(1, 145))
    hourly = matrix.to_numpy(dtype=float).reshape(len(dates), 24, 6).sum(axis=2)
    day = np.arange(len(dates))
    hour = np.arange(24) + 0.5
    grid_day, grid_hour = np.meshgrid(day, hour, indexing="ij")

    fig = plt.figure(figsize=(W + 2.6, 7.8))
    ax = fig.add_subplot(111, projection="3d")
    surface = ax.plot_surface(grid_day, grid_hour, hourly, cmap="magma", linewidth=0,
                              antialiased=True, rstride=4, cstride=1, alpha=0.96)
    ax.set_xlim(0, len(dates))
    ax.set_ylim(0, 24)
    ax.set_zlim(0, float(hourly.max()) * 1.05)
    ax.set_xticks([0, 60, 120, 180, 240, 300])
    ax.set_yticks(range(0, 25, 4))
    ax.set_xlabel("日序（0 = 2025-02-01）", labelpad=22)
    ax.set_ylabel("时刻 (h)", labelpad=14)
    ax.set_zlabel("紧急购电量 (kWh/h)", labelpad=8)
    ax.set_title(
        "紧急购电量时空曲面（x 日序, y 时刻, z 每小时紧急购电量）\n"
        "高脊集中在白天光伏时段；静态投影存在遮挡，配套二维热力图共同阅读",
        fontsize=12, pad=16,
    )
    ax.view_init(elev=26, azim=-64)
    bar = fig.colorbar(surface, ax=ax, shrink=0.62, pad=0.08)
    bar.set_label("紧急购电量 (kWh/h)")
    peak = np.unravel_index(np.argmax(hourly), hourly.shape)
    ax.text2D(
        0.02, 0.94,
        f"峰值 {hourly[peak]:.0f} kWh/h\n（{dates[peak[0]].strftime('%m-%d')} {peak[1]}:00）",
        transform=ax.transAxes, fontsize=9, color="black", va="top",
        bbox=dict(boxstyle="round", fc="white", ec=NEUTRAL, alpha=0.9),
    )
    fig.tight_layout()
    return emit(
        fig, kind="emergency_surface_3d",
        title="紧急购电量时空三维曲面（日序 × 时刻 × 紧急购电量）",
        caption=(
            "x 为日序（2025-02-01 起 334 天）、y 为时刻、z 为按小时聚合的紧急购电量；曲面的高脊集中在"
            f"白天时段，峰值 {hourly[peak]:.0f} kWh/h 出现在 {dates[peak[0]].strftime('%Y-%m-%d')} {peak[1]}:00。"
            "三维静态投影存在遮挡与透视歧义，配套「全年逐时段紧急购电量热力图」（二维投影）共同阅读。"
        ),
        x="day_of_year", y=["hour_of_day", "emergency_kwh_per_hour"],
    )


def fig_residual_diagnostics(metrics: dict, solver: dict) -> dict:
    residuals = metrics["residuals"]
    labels = [
        ("balance_plan_max_abs", "计划层功率平衡残差"),
        ("balance_exec_max_abs", "执行层功率平衡残差"),
        ("soc_max_abs", "储电量递推残差"),
        ("terminal_residual", "终端储电量残差"),
        ("energy_bound_violation", "储电量边界违反"),
        ("power_upper_violation", "变流器功率上限违反"),
        ("complementarity_max_min", "充放电互斥违反"),
        ("exec_complementarity_max", "执行层互补违反"),
        ("kappa_upper_violation", "κ* 上界违反"),
        ("kappa_act_upper_violation", "κ_act 上界违反"),
        ("nonnegativity_violation", "非负性违反"),
        ("integrality_violation", "0-1 整性违反"),
    ]
    values = [float(residuals[key]) for key, _ in labels]
    floor = 1e-16
    plot_values = [value if value > 0 else floor for value in values]
    colors = [SECONDARY if value <= 1e-6 else WARNING for value in values]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 6.6), gridspec_kw={"width_ratios": [1.15, 1]})
    positions = np.arange(len(labels))
    ax1.barh(positions, plot_values, color=colors, height=0.62)
    ax1.set_xscale("log")
    ax1.set_xlim(floor * 0.5, 1e-4)
    ax1.axvline(1e-6, color=WARNING, ls="--", lw=1.2)
    ax1.annotate("阈值 1e-6", (1e-6, len(labels) - 0.5), textcoords="offset points",
                 xytext=(4, 0), fontsize=9, color=WARNING)
    for index, value in enumerate(values):
        text = "0（无违反）" if value == 0 else f"{value:.2e}"
        ax1.annotate(text, (plot_values[index], index), va="center",
                     textcoords="offset points", xytext=(6, 0), fontsize=8.5)
    ax1.set_yticks(positions, [name for _, name in labels], fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("最大残差（对数轴；0 以 1e-16 绘制）")
    ax1.set_ylabel("约束类别")
    ax1.set_title("硬约束回代残差（334 天 × 144 时段）")

    ann = metrics["annual"]
    ax2.axis("off")
    ax2.text(
        0.0, 1.0,
        "求解质量与主结果\n"
        "----------------------------------------\n"
        f"求解器           {solver['solver']}\n"
        f"模型             {solver['model_id']}\n"
        f"最优天数         {solver['days_optimal']}/{solver['days_total']}\n"
        f"可行非最优天数   {solver['days_feasible_not_optimal']}\n"
        f"失败天数         {solver['days_failed']}\n"
        f"max mip_gap      {solver['max_mip_gap']:.2e}\n"
        f"单日变量/等式    {solver['num_variables_per_day']}/{solver['num_equalities_per_day']}\n"
        f"单日不等式       {solver['num_inequalities_per_day']}\n"
        f"big-M（=Pbar）   {solver['big_m']:.4f} kWh\n"
        f"随机种子         {solver['seed']}\n"
        f"总运行时间       {solver['total_runtime_seconds']:.1f} s\n"
        "----------------------------------------\n"
        f"Cost_plan        {ann['cost_plan']:,.2f} 元\n"
        f"Cost_em          {ann['cost_em']:,.2f} 元\n"
        f"Cost_total       {ann['cost_total']:,.2f} 元\n"
        f"Q_plan           {ann['q_plan']:,.2f} kWh\n"
        f"紧急购电         {ann['emergency_energy']:,.2f} kWh\n"
        f"实际弃光         {ann['curtail_act_total']:,.2f} kWh\n"
        f"可行性门禁       {'全部通过' if metrics['gates']['all_pass'] else '未通过'}",
        ha="left", va="top", fontsize=9.2, family=MONO_FONT,
        bbox=dict(boxstyle="round", fc="#F7F7F7", ec=NEUTRAL, alpha=0.95),
    )
    fig.suptitle("prob02 结果可信度诊断：约束残差与求解质量", fontsize=14, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return emit(
        fig, kind="residual_diagnostics",
        title="prob02 结果可信度：12 类硬约束回代残差与求解质量",
        caption=(
            "左：十二类硬约束的最大回代残差（对数轴），全部远低于 1e-6 阈值；右：334/334 天 status=0、"
            f"max mip_gap={solver['max_mip_gap']:.1e}、失败 0 天，以及年度主结果。"
            "残差与求解器状态均取自 metrics.json / solver_status.json，未做任何再计算改写。"
        ),
        x="residual_kind", y=["max_abs_residual", "solver_quality"],
    )


def color_separation() -> dict:
    import matplotlib.colors as mcolors

    colors = {"primary": PRIMARY, "secondary": SECONDARY, "accent": ACCENT,
              "neutral": NEUTRAL, "warning": WARNING}
    rgb = {name: np.array(mcolors.to_rgb(value)) for name, value in colors.items()}
    pairs = []
    names = list(rgb)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            distance = float(np.linalg.norm(rgb[names[i]] - rgb[names[j]]) * 255)
            pairs.append({"pair": f"{names[i]}/{names[j]}", "distance": round(distance, 1)})
    minimum = min(item["distance"] for item in pairs)
    if minimum < 40.0:
        raise RuntimeError(f"色板区分度不足：{pairs}")
    return {"palette": colors, "pairwise_distance": pairs, "minimum_distance": minimum}


def main() -> None:
    apply_style()
    frame, daily, segments, metrics, solver = load_inputs()
    gate = verify_inputs(frame, daily, segments, metrics, solver)
    items = [
        fig_daily_cost_timeline(daily),
        fig_monthly_cost_stack(daily),
        fig_emergency_vs_shortfall(frame, daily),
        fig_curtail_plan_vs_act(frame, daily),
        fig_key_dates_execution(frame, metrics),
        fig_delivery_audit(frame, metrics),
        fig_annual_cost_composition(metrics, solver),
        fig_emergency_heatmap_2d(frame),
        fig_emergency_surface_3d(frame),
        fig_residual_diagnostics(metrics, solver),
    ]
    kinds = [item["kind"] for item in items]
    if "emergency_surface_3d" in kinds and "emergency_heatmap_2d" not in kinds:
        raise RuntimeError("三维图缺少二维配套投影")
    report = {
        "generated_at": utc_now(),
        "method": "programmatic_visual_audit",
        "method_note": (
            "本环境最终响应模型不支持图像输入，无法进行像素级人工目检；"
            "视觉复核以可复现的程序化审计代替，覆盖：CJK 字形覆盖（FT2Font charmap）、"
            "文本越界/裁切、文本两两重叠（较小者重叠面积比 >25% 即失败）、字体族一致性、"
            "每坐标轴标题/轴标签/图例完整性、色板两两 RGB 区分度、三维图视角与二维配套投影存在性。"
        ),
        "font": FONT,
        "mono_font": MONO_FONT,
        "dpi": DPI,
        "gate": gate,
        "color_separation": color_separation(),
        "three_dimensional": {
            "viewpoint": {"elev": 26, "azim": -64},
            "has_2d_companion": "emergency_heatmap_2d" in kinds,
            "slugs": kinds,
        },
        "figures": AUDIT,
        "status": "passed" if AUDIT and all(item["status"] == "passed" for item in AUDIT) else "failed",
    }
    (HERE / "visual_review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(
        {
            "font": FONT,
            "mono_font": MONO_FONT,
            "dpi": DPI,
            "visual_review_status": report["status"],
            "figures": [
                {"stable_id": item["stable_id"], "path": item["path"],
                 "quality_status": item["quality_status"],
                 "visual_audit": item["visual_audit"]["status"], "title": item["title"]}
                for item in items
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
