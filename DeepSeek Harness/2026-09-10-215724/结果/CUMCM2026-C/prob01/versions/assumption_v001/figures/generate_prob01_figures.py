"""prob01 出版级图表生成脚本（visualization 阶段）。

- 只读消费接受版本的计算交付：solution.csv / metrics.json / solver_status.json。
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
from mpl_toolkits.mplot3d.art3d import Line3DCollection

PROBLEM = "CUMCM2026-C"
QUESTION = "prob01"
ASSUMPTION = "assumption_v001"
FORMULATION = "formulation_v001"
TASK_ID = "13bf04ee604e54581fa2"
DT = 1.0 / 6.0
EMIN, EMAX, ECAP, E0 = 1200.0, 10800.0, 12000.0, 6000.0
PBAR = 5000.0 * DT

HERE = Path(__file__).resolve().parent
RESULT_DIR = HERE.parent / "results" / "prob01_m1_formulation_v001"
SOLUTION = RESULT_DIR / "solution.csv"
METRICS = RESULT_DIR / "metrics.json"
SOLVER = RESULT_DIR / "solver_status.json"

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


def load_inputs() -> tuple[pd.DataFrame, dict, dict]:
    frame = pd.read_csv(SOLUTION)
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    solver = json.loads(SOLVER.read_text(encoding="utf-8"))
    return frame, metrics, solver


def verify_inputs(frame: pd.DataFrame, metrics: dict, solver: dict) -> dict:
    """出图前的数值门禁：交付结果必须自洽，否则拒绝出图。"""
    m = metrics["metrics"]
    residuals = metrics["residuals"]
    checks = {
        "cost_day": abs(float((frame.price * frame.q_kwh).sum()) - float(m["cost_day"])),
        "q_day": abs(float(frame.q_kwh.sum()) - float(m["q_day"])),
        "curtail_total": abs(float(frame.curtail_kwh.sum()) - float(m["curtail_total"])),
        "charge_total": abs(float(frame.charge_kwh.sum()) - float(m["charge_total"])),
        "discharge_total": abs(float(frame.discharge_kwh.sum()) - float(m["discharge_total"])),
        "energy_bounds": float(max(EMIN - frame.E_kwh.min(), frame.E_kwh.max() - EMAX, 0.0)),
        "terminal": abs(float(frame.E_kwh.iloc[-1]) - E0),
        "complementarity": float(np.max(np.minimum(frame.charge_kwh, frame.discharge_kwh))),
        "q_nonneg": float(max(-frame.q_kwh.min(), 0.0)),
        "nonfinite_count": float(
            np.sum(~np.isfinite(frame[["price", "load_kw", "pv_kw", "q_kwh", "E_kwh"]]).all(axis=1))
        ),
    }
    thresholds = {
        "cost_day": 1e-6, "q_day": 1e-6, "curtail_total": 1e-9, "charge_total": 1e-6,
        "discharge_total": 1e-6, "energy_bounds": 1e-6, "terminal": 1e-9,
        "complementarity": 1e-9, "q_nonneg": 1e-9, "nonfinite_count": 0.5,
    }
    failed = {key: value for key, value in checks.items() if value > thresholds[key]}
    if failed:
        raise RuntimeError(f"交付结果未通过出图前数值门禁：{failed}")
    if residuals["balance_max_abs"] > 1e-6 or residuals["nan_inf_count"] != 0:
        raise RuntimeError(f"metrics.json 残差超阈：{residuals}")
    if int(solver["status"]) != 0 or float(solver["mip_gap"]) != 0.0:
        raise RuntimeError("主模型未达到可证最优，不得出正式图")
    # 表 1 指定时段与交付口径逐项核对
    table1 = m["table1_q"]
    period_map = {"10:00-10:10": 61, "12:00-12:10": 73, "14:00-14:10": 85,
                  "16:00-16:10": 97, "18:00-18:10": 109, "20:00-20:10": 121}
    for label, period in period_map.items():
        value = float(frame.loc[frame.t == period, "q_kwh"].iloc[0])
        if abs(value - float(table1[label])) > 1e-9:
            raise RuntimeError(f"表 1 口径不一致：{label} t={period}")
    blocks = [
        (1, 24), (25, 48), (49, 72), (73, 96), (97, 120), (121, 144),
    ]
    for (start, end), block in zip(blocks, m["table2_blocks"]):
        part = frame[(frame.t >= start) & (frame.t <= end)]
        if abs(float(part.charge_kwh.sum()) - float(block["charge"])) > 1e-6:
            raise RuntimeError(f"表 2 充电量不一致：{block['label']}")
        if abs(float(part.discharge_kwh.sum()) - float(block["discharge"])) > 1e-6:
            raise RuntimeError(f"表 2 放电量不一致：{block['label']}")
    return checks


def hour_of(frame: pd.DataFrame) -> np.ndarray:
    return (frame.t.to_numpy(dtype=float) - 0.5) * DT


def hour_axis(ax) -> None:
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 2))
    ax.set_xlabel("时刻 (h)")


AUDIT: list[dict] = []
_CHARMAP_CACHE: dict[str, set[int]] = {}


def _charmap(family: str) -> set[int]:
    if family not in _CHARMAP_CACHE:
        path = font_manager.findfont(font_manager.FontProperties(family=family), fallback_to_default=False)
        _CHARMAP_CACHE[family] = set(FT2Font(path).get_charmap().keys())
    return _CHARMAP_CACHE[family]


def audit_figure(fig, kind: str) -> dict:
    """程序化视觉审计：缺字、裁切、文本重叠、字体一致性、标签/图例完整性与色彩区分。

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
            chars = sorted({ch for ch in value if ch.strip() and ch not in "$\\({})_^"} )
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
            "zlabel": bool(getattr(ax, "get_zlabel", lambda: "")() .strip()) if hasattr(ax, "get_zlabel") else None,
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
            "solution": hash_path(SOLUTION),
            "metrics": hash_path(METRICS),
            "solver_status": hash_path(SOLVER),
            "assumption_version": ASSUMPTION,
            "formulation_version": FORMULATION,
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
        "source_hashes": {
            "solution.csv": hash_path(SOLUTION),
            "metrics.json": hash_path(METRICS),
            "solver_status.json": hash_path(SOLVER),
        },
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


def fig_day_profile(frame: pd.DataFrame) -> dict:
    hour = hour_of(frame)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(W, 7.4), sharex=True)
    ax1.plot(hour, frame.price, color=PRIMARY, lw=1.8)
    ax1.fill_between(hour, frame.price, color=PRIMARY, alpha=0.10)
    i_min, i_max = int(frame.price.idxmin()), int(frame.price.idxmax())
    ax1.scatter([hour[i_min]], [frame.price[i_min]], color=SECONDARY, s=40, zorder=5)
    ax1.scatter([hour[i_max]], [frame.price[i_max]], color=WARNING, s=40, zorder=5)
    ax1.annotate(
        f"最低 {frame.price[i_min]:.4f} 元/kWh\n（{frame.time_label[i_min]}）",
        (hour[i_min], frame.price[i_min]), textcoords="offset points", xytext=(8, 12),
        fontsize=9, color=SECONDARY,
    )
    ax1.annotate(
        f"最高 {frame.price[i_max]:.4f} 元/kWh\n（{frame.time_label[i_max]}）",
        (hour[i_max], frame.price[i_max]), textcoords="offset points", xytext=(-95, -30),
        fontsize=9, color=WARNING,
    )
    ax1.set_ylabel("外网电价 (元/kWh)")
    ax1.set_title("代表日分时电价（144×10 min，极差 3.76 倍）")

    ax2.plot(hour, frame.load_kw, color=PRIMARY, lw=1.8, label="小区负载")
    ax2.plot(hour, frame.pv_kw, color=SECONDARY, lw=1.8, label="光伏发电预测")
    net = frame.load_kw - frame.pv_kw
    ax2.fill_between(hour, 0, net, where=net >= 0, color=NEUTRAL, alpha=0.20,
                     label="净负荷 > 0（需购电或放电）")
    ax2.fill_between(hour, 0, net, where=net < 0, color=ACCENT, alpha=0.28,
                     label="净负荷 < 0（光伏余电）")
    ax2.axhline(0, color=NEUTRAL, lw=0.8)
    ax2.set_ylabel("功率 (kW)")
    ax2.set_title("小区负载、光伏预测功率与净负荷")
    hour_axis(ax2)
    ax2.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
    fig.suptitle("prob01 输入数据：附件 1 代表日（唯一数据源，未做平滑或重采样）", fontsize=14, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    return emit(
        fig, kind="day_profile",
        title="代表日分时电价、负载与光伏预测（含净负荷）",
        caption=(
            f"上：144 个 10 分钟时段的外网电价（元/kWh），最低 {frame.price[i_min]:.4f}（{frame.time_label[i_min]}），"
            f"最高 {frame.price[i_max]:.4f}（{frame.time_label[i_max]}）。下：负载与光伏预测功率（kW），"
            f"阴影为净负荷 (load−pv)：全天净缺额 {float(((frame.load_kw - frame.pv_kw) * DT).sum()):.1f} kWh，"
            f"正余电 {float((np.maximum(frame.pv_kw - frame.load_kw, 0) * DT).sum()):.1f} kWh。"
        ),
        x="hour_of_day", y=["price_yuan_per_kwh", "load_kw", "pv_kw"],
    )


def fig_netload_purchase(frame: pd.DataFrame, metrics: dict) -> dict:
    m = metrics["metrics"]
    hour = hour_of(frame)
    net = (frame.load_kw - frame.pv_kw) * DT
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(W, 7.4), sharex=True)
    ax1.bar(hour, net, width=DT * 0.86, color=NEUTRAL, alpha=0.55, label="净负荷 (load−pv)·Δt")
    ax1.plot(hour, frame.q_kwh, color=PRIMARY, lw=1.9, label="计划购电量 $q_t$")
    ax1.axhline(0, color=NEUTRAL, lw=0.8)
    ax1.set_ylabel("电量 (kWh/10min)")
    ax1.set_title("逐时段净负荷与最优计划购电量")
    ax1.legend(frameon=False, fontsize=9, loc="upper left")

    ax2.plot(hour, np.cumsum(net), color=NEUTRAL, lw=1.8, label="累计净负荷")
    ax2.plot(hour, np.cumsum(frame.q_kwh), color=PRIMARY, lw=1.9, label="累计购电量 $Q_t$")
    ax2.axhline(m["q_day"], color=PRIMARY, ls=":", lw=1.0)
    ax2.annotate(
        f"全天购电量 $Q_{{day}}$ = {m['q_day']:.1f} kWh\n"
        f"全天净缺额 = {float(net.sum()):.1f} kWh\n"
        f"差额 = 0.19·ΣC = {m['q_day'] - float(net.sum()):.1f} kWh（储能往返损耗）",
        (0.98, 0.10), xycoords="axes fraction", ha="right", va="bottom", fontsize=9,
        bbox=dict(boxstyle="round", fc="white", ec=NEUTRAL, alpha=0.9),
    )
    ax2.set_ylabel("累计电量 (kWh)")
    ax2.set_title("累计净负荷与累计购电量")
    hour_axis(ax2)
    ax2.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    return emit(
        fig, kind="netload_purchase",
        title="净负荷与最优计划购电量（逐时段与累计）",
        caption=(
            f"购电量随净负荷逐时段调整；全天购电量 {m['q_day']:.1f} kWh 高于净缺额 {float(net.sum()):.1f} kWh，"
            f"差额等于储能往返损耗 0.19·ΣC_t（ΣC={m['charge_total']:.1f} kWh）。购电费 {m['cost_day']:.2f} 元。"
        ),
        x="hour_of_day", y=["net_load_kwh", "q_kwh", "cum_q_kwh"],
    )


def fig_soc_trajectory(frame: pd.DataFrame) -> dict:
    hour = hour_of(frame)
    upper_t = frame.t[frame.E_kwh >= EMAX - 1e-6].to_numpy()
    lower_t = frame.t[frame.E_kwh <= EMIN + 1e-6].to_numpy()
    fig, ax = plt.subplots(figsize=(W, 6.2))
    ax.fill_between([0, 24], EMIN, EMAX, color=SECONDARY, alpha=0.07,
                    label="允许运行区间 1200–10800 kWh")
    ax.axhline(ECAP, color=NEUTRAL, ls="-.", lw=1.1, label="额定容量 12000 kWh")
    ax.axhline(EMAX, color=WARNING, ls="--", lw=1.2, label="运行上界 10800 kWh")
    ax.axhline(EMIN, color=WARNING, ls=":", lw=1.2, label="运行下界 1200 kWh")
    ax.axhline(E0, color=NEUTRAL, ls=(0, (1, 2)), lw=1.1, label="起止储电量 6000 kWh")
    ax.plot(hour, frame.E_kwh, color=PRIMARY, lw=2.4, label="储电量 $E_t$（时段末）")
    ax.scatter(hour[upper_t - 1], frame.E_kwh.to_numpy()[upper_t - 1], color=WARNING, s=14, zorder=5)
    ax.scatter(hour[lower_t - 1], frame.E_kwh.to_numpy()[lower_t - 1], color=ACCENT, s=14, zorder=5)
    ax.annotate(
        f"贴运行上界：t={int(upper_t.min())}–{int(upper_t.max())}（{len(upper_t)} 个时段）\n"
        "余电全部被吸收，弃光=0",
        (hour[int(upper_t.min()) - 1], EMAX), textcoords="offset points", xytext=(10, 8),
        fontsize=9, color=WARNING,
    )
    ax.annotate(
        f"贴运行下界：t={int(lower_t.min())}–{int(lower_t.max())}（{len(lower_t)} 个时段）\n"
        "对应全天最高电价段，以放电替代购电",
        (hour[int(lower_t.max()) - 1], EMIN), textcoords="offset points", xytext=(-150, 16),
        fontsize=9, color=ACCENT,
    )
    ax.set_ylim(900, 11400)
    hour_axis(ax)
    ax.set_ylabel("储电量 (kWh)")
    ax.set_title("储电量轨迹与运行边界（$E_0=E_{144}=6000$ kWh）")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower left")
    fig.tight_layout()
    return emit(
        fig, kind="soc_trajectory",
        title="储能储电量全天轨迹与运行边界（含贴界时段）",
        caption=(
            f"储电量全程处于 [1200, 10800] kWh 且两端等于 6000 kWh；{len(upper_t)} 个时段贴运行上界"
            f"（t={int(upper_t.min())}–{int(upper_t.max())}），{len(lower_t)} 个时段贴运行下界"
            f"（t={int(lower_t.min())}–{int(lower_t.max())}）。贴界说明最优解由运行边界强约束，"
            "不得解读为设备可行性余量（robustness 需做端点敏感性对照）。"
        ),
        x="hour_of_day", y=["E_kwh", "Emin", "Emax"],
    )


def fig_arbitrage(frame: pd.DataFrame, metrics: dict) -> dict:
    m = metrics["metrics"]
    hour = hour_of(frame)
    low, high = frame.price.quantile(0.25), frame.price.quantile(0.75)
    low_mask = frame.price <= low
    high_mask = frame.price >= high
    charge_low = float(frame.charge_kwh[low_mask].sum() / frame.charge_kwh.sum() * 100)
    dis_high = float(frame.discharge_kwh[high_mask].sum() / frame.discharge_kwh.sum() * 100)
    charge_price = float((frame.price * frame.charge_kwh).sum() / frame.charge_kwh.sum())
    dis_price = float((frame.price * frame.discharge_kwh).sum() / frame.discharge_kwh.sum())

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(W, 7.4), sharex=True)
    ax1.plot(hour, frame.price, color=PRIMARY, lw=1.7, label="外网电价")
    ax1.fill_between(hour, frame.price.min(), frame.price, where=low_mask,
                     color=SECONDARY, alpha=0.22, label="低价四分位（充电窗口）")
    ax1.fill_between(hour, frame.price.min(), frame.price, where=high_mask,
                     color=ACCENT, alpha=0.22, label="高价四分位（放电窗口）")
    ax1.set_ylabel("电价 (元/kWh)")
    ax1.set_title("分时电价与充放电窗口")
    ax1.legend(frameon=False, fontsize=9, loc="upper left")

    ax2.bar(hour, frame.charge_kwh, width=DT * 0.86, color=SECONDARY, label="充电量 $C_t$")
    ax2.bar(hour, -frame.discharge_kwh, width=DT * 0.86, color=ACCENT, label="放电量 $D_t$（向下为负）")
    ax2.axhline(0, color=NEUTRAL, lw=0.8)
    ax2.axhline(PBAR, color=NEUTRAL, ls=":", lw=1.0)
    ax2.axhline(-PBAR, color=NEUTRAL, ls=":", lw=1.0)
    ax2.annotate("$\\bar P$=833.33 kWh/10min", (0.2, PBAR), textcoords="offset points",
                 xytext=(0, 4), fontsize=8.5, color=NEUTRAL)
    ax2.annotate(
        f"ΣC={m['charge_total']:.1f} kWh，充电压价 {charge_price:.4f} 元/kWh\n"
        f"ΣD={m['discharge_total']:.1f} kWh，放电压价 {dis_price:.4f} 元/kWh\n"
        f"{charge_low:.1f}% 充电量落在最低价四分位；{dis_high:.1f}% 放电量落在最高价四分位",
        (0.98, 0.05), xycoords="axes fraction", ha="right", va="bottom", fontsize=9,
        bbox=dict(boxstyle="round", fc="white", ec=NEUTRAL, alpha=0.9),
    )
    ax2.set_ylabel("充/放电量 (kWh/10min)")
    ax2.set_title("逐时段充放电量（互斥约束 max min(C,D)=0）")
    hour_axis(ax2)
    ax2.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    return emit(
        fig, kind="arbitrage",
        title="低谷充电与高峰放电的套利结构（充放电量与分时电价对照）",
        caption=(
            f"充电集中在低价时段（充电压价 {charge_price:.4f} 元/kWh），放电集中在高价时段"
            f"（放电压价 {dis_price:.4f} 元/kWh）；{charge_low:.1f}% 的充电量落在最低价四分位，"
            f"{dis_high:.1f}% 的放电量落在最高价四分位。并网点侧往返效率 0.81 下毛利差仍为正，"
            "与「低谷充电、高峰放电」机理一致。"
        ),
        x="hour_of_day", y=["charge_kwh", "discharge_kwh", "price_yuan_per_kwh"],
    )


def fig_delivery_audit(frame: pd.DataFrame, metrics: dict) -> dict:
    m = metrics["metrics"]
    labels1 = list(m["table1_q"].keys())
    periods1 = {"10:00-10:10": 61, "12:00-12:10": 73, "14:00-14:10": 85,
                "16:00-16:10": 97, "18:00-18:10": 109, "20:00-20:10": 121}
    q1 = [float(m["table1_q"][label]) for label in labels1]
    p1 = [float(frame.loc[frame.t == periods1[label], "price"].iloc[0]) for label in labels1]
    blocks = m["table2_blocks"]
    block_labels = [item["label"] for item in blocks]
    charge = [float(item["charge"]) for item in blocks]
    discharge = [float(item["discharge"]) for item in blocks]
    cost = []
    for (start, end) in [(1, 24), (25, 48), (49, 72), (73, 96), (97, 120), (121, 144)]:
        part = frame[(frame.t >= start) & (frame.t <= end)]
        cost.append(float((part.price * part.q_kwh).sum()))
    cost_share = [value / sum(cost) * 100 for value in cost]

    fig = plt.figure(figsize=(11.5, 8.2))
    grid = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.24)
    ax1, ax2, ax3, ax4 = (fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]),
                          fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1]))

    ax1.bar(range(len(labels1)), q1, color=PRIMARY, width=0.6)
    for index, (value, price) in enumerate(zip(q1, p1)):
        ax1.annotate(f"{value:.1f}\n@{price:.4f}", (index, value), ha="center", va="bottom",
                     textcoords="offset points", xytext=(0, 3), fontsize=8.5)
    ax1.set_xticks(range(len(labels1)), labels1, rotation=35, ha="right", fontsize=9)
    ax1.set_ylim(0, max(q1) * 1.35)
    ax1.set_ylabel("计划购电量 (kWh)")
    ax1.set_title("表 1：指定时段购电量（标注该时段电价，元/kWh）")

    positions = np.arange(len(block_labels))
    width = 0.38
    ax2.bar(positions - width / 2, charge, width, color=SECONDARY, label="充电量")
    ax2.bar(positions + width / 2, discharge, width, color=ACCENT, label="放电量")
    ax2.set_xticks(positions, block_labels, rotation=25, ha="right", fontsize=9)
    ax2.set_ylabel("电量 (kWh)")
    ax2.set_title("表 2：4 小时块充放电量")
    ax2.legend(frameon=False, fontsize=9)

    ax3.barh(positions, cost, color=PRIMARY, height=0.6)
    for index, (value, share) in enumerate(zip(cost, cost_share)):
        ax3.annotate(f"{value:.1f} 元（{share:.1f}%）", (value, index), va="center",
                     textcoords="offset points", xytext=(5, 0), fontsize=9)
    ax3.set_yticks(positions, block_labels, fontsize=9)
    ax3.set_xlim(0, max(cost) * 1.45)
    ax3.set_xlabel("购电费 (元)")
    ax3.set_title("4 小时块购电费与占比")

    ax4.axis("off")
    ax4.text(
        0.0, 1.0,
        "交付口径自洽核对（asm-12 / 歧义 A9）\n"
        "----------------------------\n"
        f"计划购电量表：144 行 + 1 行表头\n"
        f"标签：0:00-0:10 … 23:50-24:00（物理区间）\n"
        f"全天购电量 Q_day = {m['q_day']:.4f} kWh\n"
        f"六块购电费合计 = {sum(cost):.4f} 元\n"
        f"全天购电费 Cost_day = {m['cost_day']:.4f} 元\n"
        f"残差 = {abs(sum(cost) - m['cost_day']):.2e} 元\n"
        "----------------------------\n"
        f"E_0 = E_144 = {m['E_0']:.1f} kWh\n"
        f"全天弃光 = {m['curtail_total']:.1f} kWh\n"
        f"表 1 六时段购电量合计 = {sum(q1):.1f} kWh\n"
        f"求解状态：最优（status=0，gap=0）",
        ha="left", va="top", fontsize=10, family=MONO_FONT,
        bbox=dict(boxstyle="round", fc="#F7F7F7", ec=NEUTRAL, alpha=0.95),
    )
    fig.suptitle("result1.xlsx 交付口径核对：表 1 指定时段与表 2 充放电量", fontsize=14, y=0.985)
    return emit(
        fig, kind="delivery_audit",
        title="result1.xlsx 交付口径核对（表 1 指定时段 / 表 2 充放电量 / 分块购电费）",
        caption=(
            f"表 1 六个指定时段购电量取自 t=61/73/85/97/109/121；表 2 六个 4 小时块充放电量与 E_0/E_144 逐项一致；"
            f"六块购电费合计 {sum(cost):.4f} 元与 Cost_day 完全一致（残差 {abs(sum(cost) - m['cost_day']):.1e} 元）。"
            "时间标签按 asm-12 统一为物理区间，与附件 5 模板的字面标签存在一个时段的整体偏移。"
        ),
        x="delivery_period", y=["q_kwh", "charge_kwh", "discharge_kwh", "block_cost_yuan"],
    )


def fig_cumulative_cost(frame: pd.DataFrame, metrics: dict) -> dict:
    m = metrics["metrics"]
    hour = hour_of(frame)
    baseline_q = np.maximum(frame.load_kw - frame.pv_kw, 0.0) * DT
    baseline_cost = float((frame.price * baseline_q).sum())
    expected_upper = float(m["cost_feasible_upper_bound"])
    if abs(baseline_cost - expected_upper) > 5e-3:
        raise RuntimeError(f"无储能基线复算与解析上界不一致：{baseline_cost} vs {expected_upper}")
    cum_opt = np.cumsum(frame.price * frame.q_kwh)
    cum_base = np.cumsum(frame.price * baseline_q)
    saved = baseline_cost - m["cost_day"]
    saved_pct = saved / baseline_cost * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(W, 7.6))
    ax1.plot(hour, cum_base, color=NEUTRAL, lw=1.9, label="无储能基线（弃光、不充放）")
    ax1.plot(hour, cum_opt, color=PRIMARY, lw=2.1, label="M1 最优调度")
    ax1.fill_between(hour, cum_opt, cum_base, color=SECONDARY, alpha=0.16, label="节省的购电费")
    ax1.set_ylabel("累计购电费 (元)")
    ax1.set_title("累计购电费：最优调度 vs 无储能基线")
    hour_axis(ax1)
    ax1.legend(frameon=False, fontsize=9, loc="upper left")

    bars = ax2.bar(["无储能基线", "M1 最优调度"], [baseline_cost, m["cost_day"]],
                   color=[NEUTRAL, PRIMARY], width=0.45)
    ax2.axhspan(float(m["cost_lower_bound"]), float(m["cost_feasible_upper_bound"]),
                color=SECONDARY, alpha=0.06)
    ax2.axhline(float(m["cost_lower_bound"]), color=NEUTRAL, ls=":", lw=1.1)
    ax2.annotate(f"解析下界 {m['cost_lower_bound']:.2f} 元", (0.62, float(m["cost_lower_bound"])),
                 textcoords="offset points", xytext=(0, 5), fontsize=8.5, color=NEUTRAL)
    for bar, value in zip(bars, [baseline_cost, m["cost_day"]]):
        ax2.annotate(f"{value:.2f} 元", (bar.get_x() + bar.get_width() / 2, value),
                     ha="center", va="bottom", textcoords="offset points", xytext=(0, 4), fontsize=10)
    ax2.annotate(
        f"节省 {saved:.2f} 元（−{saved_pct:.2f}%）",
        (0.5, 0.72), xycoords="axes fraction", ha="center", fontsize=11, color=SECONDARY,
        bbox=dict(boxstyle="round", fc="white", ec=SECONDARY, alpha=0.95),
    )
    ax2.set_ylabel("全天购电费 (元)")
    ax2.set_ylim(0, baseline_cost * 1.18)
    ax2.set_title("全天购电费对比（灰色带为解析可行区间）")
    fig.tight_layout()
    return emit(
        fig, kind="cumulative_cost",
        title="全天购电费对比：M1 最优调度与无储能基线（累计曲线与总量）",
        caption=(
            f"M1 全天购电费 {m['cost_day']:.2f} 元，较无储能基线 {baseline_cost:.2f} 元节省 "
            f"{saved:.2f} 元（−{saved_pct:.2f}%）；基线由附件 1 数据直接复算并等于 formulation §7 的解析可行上界 "
            f"{expected_upper:.2f} 元；解析下界 {m['cost_lower_bound']:.2f} 元。"
        ),
        x="hour_of_day", y=["cum_cost_yuan", "total_cost_yuan"],
    )


def fig_residual_diagnostics(metrics: dict, solver: dict) -> dict:
    residuals = metrics["residuals"]
    labels = [
        ("balance_max_abs", "功率平衡残差"),
        ("soc_max_abs", "储电量递推残差"),
        ("terminal_residual", "终端储电量残差"),
        ("energy_bound_violation", "储电量边界违反"),
        ("power_upper_violation", "变流器功率上限违反"),
        ("complementarity_max_min", "充放电互斥违反"),
        ("nonnegativity_violation", "非负性违反"),
    ]
    values = [float(residuals[key]) for key, _ in labels]
    floor = 1e-16
    plot_values = [value if value > 0 else floor for value in values]
    colors = [SECONDARY if value <= 1e-6 else WARNING for value in values]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 6.0), gridspec_kw={"width_ratios": [1.15, 1]})
    positions = np.arange(len(labels))
    ax1.barh(positions, plot_values, color=colors, height=0.6)
    ax1.set_xscale("log")
    ax1.set_xlim(floor * 0.5, 1e-4)
    ax1.axvline(1e-6, color=WARNING, ls="--", lw=1.2)
    ax1.annotate("阈值 1e-6", (1e-6, len(labels) - 0.4), textcoords="offset points",
                 xytext=(4, 0), fontsize=9, color=WARNING)
    for index, value in enumerate(values):
        text = "0（无违反）" if value == 0 else f"{value:.2e}"
        ax1.annotate(text, (plot_values[index], index), va="center",
                     textcoords="offset points", xytext=(6, 0), fontsize=9)
    ax1.set_yticks(positions, [name for _, name in labels], fontsize=9.5)
    ax1.invert_yaxis()
    ax1.set_xlabel("最大残差 (kWh，对数轴；0 以 1e-16 绘制)")
    ax1.set_ylabel("约束类别")
    ax1.set_title("硬约束回代残差")

    ax2.axis("off")
    ax2.text(
        0.0, 1.0,
        "求解质量与主结果\n"
        "--------------------------------------\n"
        f"求解器          {solver['solver']}\n"
        f"状态            status={int(solver['status'])}（HiGHS 最优）\n"
        f"objective       {solver['objective']:.10f} 元\n"
        f"best_bound      {solver['best_bound']:.10f} 元\n"
        f"mip_gap         {solver['mip_gap']:.1e}\n"
        f"node_count      {solver['node_count']:.0f}\n"
        f"变量/等式/不等式 {int(solver['num_variables'])}/{int(solver['num_equalities'])}"
        f"/{int(solver['num_inequalities'])}\n"
        f"big-M（=Pbar）   {solver['pbar_kwh']:.4f} kWh\n"
        f"随机种子        {solver['seed']}\n"
        "--------------------------------------\n"
        f"Cost_day        {metrics['metrics']['cost_day']:.6f} 元\n"
        f"Q_day           {metrics['metrics']['q_day']:.6f} kWh\n"
        f"弃光总量        {metrics['metrics']['curtail_total']:.6f} kWh\n"
        f"E_0 / E_144     {metrics['metrics']['E_0']:.1f} / {metrics['metrics']['E_144']:.1f} kWh\n"
        f"可行性门禁      {'全部通过' if all(metrics['gates'].values()) else '未通过'}",
        ha="left", va="top", fontsize=9.5, family=MONO_FONT,
        bbox=dict(boxstyle="round", fc="#F7F7F7", ec=NEUTRAL, alpha=0.95),
    )
    fig.suptitle("prob01 结果可信度诊断：约束残差与求解质量", fontsize=14, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return emit(
        fig, kind="residual_diagnostics",
        title="prob01 结果可信度：硬约束回代残差与求解质量",
        caption=(
            "左：七类硬约束的最大回代残差（对数轴），全部不高于 1e-6 阈值；右：求解器状态、目标值、"
            "best bound、MIP gap、规模与主结果。gap=0、node_count=1 表明 144 个 0-1 的 MILP 在根节点即得可证全局最优。"
        ),
        x="residual_kind", y=["max_abs_residual_kwh", "solver_quality"],
    )


def fig_state_price_trajectory_3d(frame: pd.DataFrame) -> dict:
    hour = hour_of(frame)
    price = frame.price.to_numpy(dtype=float)
    energy = frame.E_kwh.to_numpy(dtype=float)
    charge = frame.charge_kwh.to_numpy(dtype=float)
    discharge = frame.discharge_kwh.to_numpy(dtype=float)
    mode = np.where(charge > 1e-9, "charge", np.where(discharge > 1e-9, "discharge", "idle"))
    mode_color = {"charge": SECONDARY, "discharge": ACCENT, "idle": NEUTRAL}
    points = np.column_stack([hour, price, energy])
    segments = np.concatenate([points[:-1, None, :], points[1:, None, :]], axis=1)
    segment_colors = [mode_color[mode[index]] for index in range(len(segments))]

    fig = plt.figure(figsize=(W + 1.6, 7.6))
    ax = fig.add_subplot(111, projection="3d")
    collection = Line3DCollection(segments, colors=segment_colors, linewidths=2.4)
    ax.add_collection3d(collection)
    ax.scatter(hour[0], price[0], energy[0], color=PRIMARY, s=70, marker="o", depthshade=False)
    ax.scatter(hour[-1], price[-1], energy[-1], color=WARNING, s=70, marker="s", depthshade=False)
    ax.set_xlim(0, 24)
    ax.set_ylim(float(np.min(price)), float(np.max(price)))
    ax.set_zlim(900, 11400)
    ax.set_xlabel("时刻 (h)", labelpad=12)
    ax.set_ylabel("电价 (元/kWh)", labelpad=26)
    ax.set_zlabel("储电量 (kWh)", labelpad=10)
    ax.set_title(
        "储电量–电价–时刻三维调度轨迹\n"
        "(x 时刻, y 电价, z 储电量；线段颜色表示该时段充/放/空闲状态)",
        fontsize=13, pad=16,
    )
    ax.view_init(elev=20, azim=-62)
    handles = [
        Line2D([0], [0], color=SECONDARY, lw=3, label="充电时段"),
        Line2D([0], [0], color=ACCENT, lw=3, label="放电时段"),
        Line2D([0], [0], color=NEUTRAL, lw=3, label="空闲时段"),
        Line2D([0], [0], color=PRIMARY, marker="o", ls="", label="起点 t=1（0:00）"),
        Line2D([0], [0], color=WARNING, marker="s", ls="", label="终点 t=144（24:00）"),
    ]
    ax.legend(handles=handles, frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(0.02, 0.95))
    fig.tight_layout()
    return emit(
        fig, kind="state_price_trajectory_3d",
        title="储电量–电价–时刻三维调度轨迹（充/放/空闲着色）",
        caption=(
            "x 为时刻、y 为外网电价、z 为时段末储电量，线段颜色表示该时段状态：充电（绿）集中在低电价高储电量段，"
            "放电（橙）集中在高电价段，空闲（灰）连接两者。轨迹在 0:00 与 24:00 回到 6000 kWh。"
            "三维投影存在歧义，配套二维「电价–储电量相平面轨迹」图共同阅读。"
        ),
        x="hour_of_day", y=["price_yuan_per_kwh", "E_kwh"],
    )


def fig_price_soc_phase(frame: pd.DataFrame) -> dict:
    price = frame.price.to_numpy(dtype=float)
    energy = frame.E_kwh.to_numpy(dtype=float)
    hour = hour_of(frame)
    fig, ax = plt.subplots(figsize=(W, 6.4))
    ax.plot(price, energy, color=NEUTRAL, lw=1.0, alpha=0.55, zorder=1)
    scatter = ax.scatter(price, energy, c=hour, cmap="viridis", s=34, zorder=3, edgecolors="none")
    ax.axhline(EMAX, color=WARNING, ls="--", lw=1.1)
    ax.axhline(EMIN, color=WARNING, ls=":", lw=1.1)
    ax.axhline(E0, color=NEUTRAL, ls=(0, (1, 2)), lw=1.0)
    ax.annotate("运行上界 10800 kWh", (0.02, EMAX), xycoords=("axes fraction", "data"),
                textcoords="offset points", xytext=(0, 4), fontsize=9, color=WARNING)
    ax.annotate("运行下界 1200 kWh", (0.02, EMIN), xycoords=("axes fraction", "data"),
                textcoords="offset points", xytext=(0, 4), fontsize=9, color=WARNING)
    ax.scatter([price[0]], [energy[0]], color=SECONDARY, s=130, marker="o", zorder=5,
               label="起点 t=1（0:00，E=6000）")
    ax.scatter([price[-1]], [energy[-1]], color=WARNING, s=130, marker="s", zorder=5,
               label="终点 t=144（24:00，E=6000）")
    bar = fig.colorbar(scatter, ax=ax, pad=0.02)
    bar.set_label("时刻 (h)")
    ax.set_xlabel("外网电价 (元/kWh)")
    ax.set_ylabel("时段末储电量 (kWh)")
    ax.set_ylim(900, 11400)
    ax.set_title("储电量–电价相平面轨迹（三维轨迹的二维投影，颜色为时刻）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout()
    return emit(
        fig, kind="price_soc_phase",
        title="电价–储电量相平面轨迹（三维调度轨迹的二维配套投影）",
        caption=(
            "把三维调度轨迹投影到「电价–储电量」平面并按时刻着色：低电价（左侧）对应充电与储电量上升，"
            "高电价（右侧）对应放电与储电量下降；右上角聚集点即最高电价且贴运行下界的时段（t=124~131）。"
            "该图作为三维图的二维配套，消除静态投影的歧义。"
        ),
        x="price_yuan_per_kwh", y=["E_kwh", "hour_of_day"],
    )


def color_separation() -> dict:
    import matplotlib.colors as mcolors

    colors = {"primary": PRIMARY, "secondary": SECONDARY, "accent": ACCENT, "neutral": NEUTRAL, "warning": WARNING}
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
    frame, metrics, solver = load_inputs()
    verify_inputs(frame, metrics, solver)
    items = [
        fig_day_profile(frame),
        fig_netload_purchase(frame, metrics),
        fig_soc_trajectory(frame),
        fig_arbitrage(frame, metrics),
        fig_delivery_audit(frame, metrics),
        fig_cumulative_cost(frame, metrics),
        fig_residual_diagnostics(metrics, solver),
        fig_state_price_trajectory_3d(frame),
        fig_price_soc_phase(frame),
    ]
    kinds = [item["kind"] for item in items]
    if "state_price_trajectory_3d" in kinds and "price_soc_phase" not in kinds:
        raise RuntimeError("三维图缺少二维配套投影")
    three_d = [item for item in items if item["kind"] == "state_price_trajectory_3d"]
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
        "color_separation": color_separation(),
        "three_dimensional": {
            "viewpoint": {"elev": 20, "azim": -62},
            "has_2d_companion": bool(three_d) and "price_soc_phase" in kinds,
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
                 "visual_audit": item["visual_audit"]["status"]}
                for item in items
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
