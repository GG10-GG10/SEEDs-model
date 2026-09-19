# -*- coding: utf-8 -*-
"""
Plot structure-importance stacks and quartile distribution curves from S5_5 merged outputs.

Inputs (from S5_5_3 merged outputs):
- <output_root>/merged_structure/structure_stack_top_long.csv
- <output_root>/merged_structure/structure_quartile_histogram_top.csv
- <output_root>/merged_structure/structure_quartile_summary.csv

Outputs:
- output/Plot/Fig9/FigureS5_5_structure_<grouping>_stack_v1.png/.svg
- output/Plot/Fig9/FigureS5_5_<panel>_<grouping>_quartile_grid_v1.png/.svg
- output/Plot/Fig9/FigureS5_5_structure_importance_v1.xlsx
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from config_paths import get_results_base


RESULTS_BASE = Path(get_results_base())
DEFAULT_OUTPUT_ROOT = RESULTS_BASE / "MC_Region_Item_Process_Importance"
DEFAULT_MERGED_SUBDIR = "merged_structure"
FIG_DIR = RESULTS_BASE / "Plot" / "Fig9"
TARGETS_PATH = RESULTS_BASE / "Plot" / "Fig5" / "targets.csv"

STACK_GROUPINGS = (
    "Region",
    "Item",
    "Process",
    "Region-Item-Process",
)

PANEL_SPECS = {
    "yield": {
        "title": "Yield-rate quartiles",
        "metric_label": "Yield change",
        "metric_unit": "%",
        "value_mode": "change_percent",
    },
    "emission_factor": {
        "title": "Emission-factor quartiles",
        "metric_label": "EF change",
        "metric_unit": "%",
        "value_mode": "change_percent",
    },
    "ruminate_intake": {
        "title": "Ruminant-intake quartiles",
        "metric_label": "Ruminant kcal share",
        "metric_unit": "%",
        "value_mode": "share_percent",
    },
    "luc_land_intensity": {
        "title": "LUC intensity quartiles",
        "metric_label": "LUC intensity",
        "metric_unit": "t CO2eq/ha/yr",
        "value_mode": "absolute",
    },
}

CONFIG = {
    "stack_groupings": STACK_GROUPINGS,
    "stack_order_target_emis_gt": None,
    "stack_dpi": 800,
    "quartile_panels": ("emission_factor",),
    "quartile_groupings": ("Item", "Region", "Process"),
    "quartile_top_n_per_grouping": 4,
    "quartile_group_filters": {},
    "quartile_grid_cols": 2,
    "quartile_smooth_sigma_bins": 2.2,
    "quartile_y_axis_mode": "probability",
    "quartile_dpi": 800,
    "show_target_lines": False,
}

QUARTILE_KEYS = ("q1", "q2", "q3", "q4")
QUARTILE_RANGES = {
    "q1": "0-25%",
    "q2": "25-50%",
    "q3": "50-75%",
    "q4": "75-100%",
}
QUARTILE_COLORS = {
    "q1": "#3b4cc0",
    "q2": "#1fa187",
    "q3": "#f6c141",
    "q4": "#b40426",
}
TARGET_ORDER = ["1.5D", "2D", "Current", "RCP4.5"]
TARGET_COLORS = {
    "1.5D": "#2ca25f",
    "2D": "#2b8cbe",
    "Current": "#4d4d4d",
    "RCP4.5": "#f1a340",
}

TAB20_COLORS = list(plt.cm.tab20.colors) + list(plt.cm.tab20b.colors) + list(plt.cm.tab20c.colors)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _smooth_counts(counts: np.ndarray, sigma_bins: float) -> np.ndarray:
    if sigma_bins <= 0:
        return counts
    radius = int(max(1, round(sigma_bins * 3)))
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (x / sigma_bins) ** 2)
    kernel /= kernel.sum()
    return np.convolve(counts, kernel, mode="same")


def _load_targets() -> List[Tuple[str, float]]:
    default_targets = [("1.5D", 0.9), ("2D", 4.0), ("Current", 12.9), ("RCP4.5", 14.5)]
    if not TARGETS_PATH.exists():
        return default_targets

    df = pd.read_csv(TARGETS_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    if "label" not in df.columns or "emission_gt" not in df.columns:
        return default_targets

    value_map: Dict[str, float] = {}
    for row in df.itertuples(index=False):
        try:
            label = str(getattr(row, "label")).strip()
            value = float(getattr(row, "emission_gt"))
        except Exception:
            continue
        if label:
            value_map[label] = value

    ordered = [(label, value_map[label]) for label in TARGET_ORDER if label in value_map]
    return ordered if ordered else default_targets


def _load_panel_samples(merged_dir: Path) -> pd.DataFrame:
    path = merged_dir / "structure_quartile_panel_samples.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _resolve_panel_specs(panel_samples: pd.DataFrame) -> Dict[str, Dict[str, object]]:
    specs = {key: dict(value) for key, value in PANEL_SPECS.items()}
    if panel_samples.empty:
        return specs

    for panel, sub in panel_samples.groupby("panel", sort=False):
        spec = specs.setdefault(str(panel), {"title": f"{panel} quartiles"})
        label = sub.get("metric_label", pd.Series([], dtype=str)).dropna().astype(str).unique()
        if label.size:
            spec["metric_label"] = label[0]

        modes = sub.get("rank_metric_mode", pd.Series([], dtype=str)).dropna().astype(str).unique()
        rank_mode = modes[0].strip().lower() if modes.size else "absolute"
        if rank_mode == "ratio":
            if str(panel) == "ruminate_intake":
                spec["value_mode"] = "share_percent"
            else:
                spec["value_mode"] = "change_percent"
            spec["metric_unit"] = "%"
        else:
            spec["value_mode"] = "absolute"
            spec.setdefault("metric_unit", "")
    return specs


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot S5_5 structure-importance stacks and quartile distributions."
    )
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--merged-dir", type=str, default=None)
    parser.add_argument("--fig-dir", type=str, default=None)
    return parser


def _resolve_output_root(args: argparse.Namespace) -> Path:
    if args.output_dir:
        return Path(str(args.output_dir))
    env_output_dir = str(os.environ.get("RIPMC_OUTPUT_DIR", "") or "").strip()
    if env_output_dir:
        return Path(env_output_dir)
    return DEFAULT_OUTPUT_ROOT


def _resolve_merged_dir(args: argparse.Namespace, output_root: Path) -> Path:
    if args.merged_dir:
        return Path(str(args.merged_dir))
    return output_root / DEFAULT_MERGED_SUBDIR


def _resolve_fig_dir(args: argparse.Namespace) -> Path:
    if args.fig_dir:
        return Path(str(args.fig_dir))
    return FIG_DIR


def _load_csv(path: Path, *, required_cols: Optional[Iterable[str]] = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise KeyError(f"{path} missing columns: {missing}")
    return df


def _group_label(row: pd.Series) -> str:
    grouping = str(row.get("grouping", "") or "").strip()
    if grouping in {"Region", "Item", "Process"}:
        label = str(row.get("group_1", "") or "").strip()
        if label:
            return label
    parts = [str(row.get("group_1", "") or "").strip(), str(row.get("group_2", "") or "").strip(), str(row.get("group_3", "") or "").strip()]
    parts = [p for p in parts if p and p.lower() != "nan"]
    if parts:
        return " / ".join(parts)
    return str(row.get("group_key", "") or "").strip()


def _build_stack_tables(long_df: pd.DataFrame, grouping: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    work = long_df[long_df["grouping"].astype(str).str.strip() == grouping].copy()
    if work.empty:
        raise ValueError(f"No stack rows for grouping {grouping}.")

    work["Emis"] = pd.to_numeric(work["target_emission_gt"], errors="coerce")
    work["importance"] = pd.to_numeric(work["importance"], errors="coerce")
    work["Group"] = work.apply(_group_label, axis=1)
    work = work.dropna(subset=["Emis", "importance"]).copy()
    work = work[work["Group"] != ""].copy()
    if work.empty:
        raise ValueError(f"Grouping {grouping} has no valid importance rows.")

    wide = (
        work.groupby(["Emis", "Group"], as_index=False)["importance"]
        .sum()
        .pivot_table(index="Emis", columns="Group", values="importance", aggfunc="sum", fill_value=0.0)
        .reset_index()
        .sort_values("Emis")
    )

    pct = wide.copy()
    val_cols = [c for c in pct.columns if c != "Emis"]
    vals = pct[val_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    row_sum = vals.sum(axis=1).replace(0.0, np.nan)
    pct[val_cols] = vals.div(row_sum, axis=0).fillna(0.0) * 100.0
    return wide, pct


def _pick_stack_order(pct_df: pd.DataFrame, target: Optional[float]) -> List[str]:
    val_cols = [c for c in pct_df.columns if c != "Emis"]
    if not val_cols:
        return []
    if target is None:
        row = pct_df.iloc[len(pct_df) // 2]
    else:
        idx = (pd.to_numeric(pct_df["Emis"], errors="coerce") - float(target)).abs().idxmin()
        row = pct_df.loc[idx]
    return row[val_cols].sort_values(ascending=False).index.tolist()


def _color_map(labels: Sequence[str]) -> Dict[str, Tuple[float, float, float]]:
    cmap: Dict[str, Tuple[float, float, float]] = {}
    for idx, label in enumerate(labels):
        if label == "Other":
            cmap[label] = (0.7, 0.7, 0.7)
        else:
            cmap[label] = TAB20_COLORS[idx % len(TAB20_COLORS)]
    return cmap


def _write_stack_workbook(group_tables: Dict[str, Dict[str, pd.DataFrame]], fig_dir: Path) -> Path:
    out_path = fig_dir / "FigureS5_5_structure_importance_v1.xlsx"
    meta_rows = [
        {"key": "stack_groupings", "value": " | ".join(group_tables.keys())},
    ]
    meta_df = pd.DataFrame(meta_rows)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        meta_df.to_excel(writer, sheet_name="meta", index=False)
        for grouping, tables in group_tables.items():
            tables["raw"].to_excel(writer, sheet_name=f"{grouping}_org"[:31], index=False)
            tables["plot"].to_excel(writer, sheet_name=grouping[:31], index=False)
            tables["plot_pct"].to_excel(writer, sheet_name=f"{grouping}_pct"[:31], index=False)
    return out_path


def _plot_stack(grouping: str, pct_df: pd.DataFrame, fig_dir: Path, *, target: Optional[float]) -> List[Path]:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    work = pct_df.copy()
    work["Emis"] = pd.to_numeric(work["Emis"], errors="coerce")
    work = work.dropna(subset=["Emis"]).sort_values("Emis")
    val_cols = [c for c in work.columns if c != "Emis"]
    if not val_cols:
        raise ValueError(f"No plot columns for grouping {grouping}.")

    stack_order = _pick_stack_order(work, target)
    colors = _color_map(stack_order)

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    ax.stackplot(
        work["Emis"].to_numpy(dtype=float),
        [work[col].to_numpy(dtype=float) for col in stack_order],
        colors=[colors[col] for col in stack_order],
        labels=stack_order,
    )
    ax.set_title(f"{grouping} relative importance", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("GHG CO2eq in 2080 (Gt/yr)", fontsize=13, fontweight="bold", labelpad=10)
    ax.set_ylabel("Relative importance (%)", fontsize=13, fontweight="bold", labelpad=10)
    ax.set_ylim(0, 100)
    ax.tick_params(axis="both", which="both", labelsize=12, width=1.6, length=7)
    for spine in ax.spines.values():
        spine.set_linewidth(1.6)

    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        frameon=False,
        fontsize=10,
        title=grouping,
        title_fontsize=11,
    )

    fig.tight_layout()
    slug = grouping.lower().replace(" ", "_").replace("/", "_")
    outputs = [
        fig_dir / f"FigureS5_5_structure_{slug}_stack_v1.png",
        fig_dir / f"FigureS5_5_structure_{slug}_stack_v1.svg",
    ]
    fig.savefig(outputs[0], dpi=int(CONFIG["stack_dpi"]), bbox_inches="tight")
    fig.savefig(outputs[1], bbox_inches="tight")
    plt.close(fig)
    return outputs


def _format_metric(value: float, value_mode: str) -> str:
    if not np.isfinite(value):
        return "NA"
    if value_mode == "change_percent":
        return f"{value:+.1f}%"
    if value_mode == "share_percent":
        return f"{value:.2f}%"
    return f"{value:.2f}"


def _format_metric_with_unit(value: float, spec: Dict[str, object]) -> str:
    text = _format_metric(value, str(spec.get("value_mode", "")))
    unit = str(spec.get("metric_unit", "") or "").strip()
    if unit and text != "NA" and spec.get("value_mode") not in {"change_percent", "share_percent"}:
        return f"{text} {unit}"
    return text


def _summary_row(summary: pd.DataFrame, panel: str, grouping: str, group_key: str, quartile_key: str) -> Optional[pd.Series]:
    if summary.empty:
        return None
    sub = summary[
        (summary["panel"] == panel)
        & (summary["grouping"] == grouping)
        & (summary["group_key"] == group_key)
        & (summary["quartile_key"] == quartile_key)
    ]
    if sub.empty:
        return None
    return sub.iloc[0]


def _group_label_map(summary: pd.DataFrame) -> Dict[Tuple[str, str], str]:
    if summary.empty:
        return {}
    label_map: Dict[Tuple[str, str], str] = {}
    for row in summary.drop_duplicates(subset=["grouping", "group_key"]).itertuples(index=False):
        grouping = str(getattr(row, "grouping"))
        group_key = str(getattr(row, "group_key"))
        parts = [
            str(getattr(row, "group_1", "") or "").strip(),
            str(getattr(row, "group_2", "") or "").strip(),
            str(getattr(row, "group_3", "") or "").strip(),
        ]
        parts = [p for p in parts if p and p.lower() != "nan"]
        if grouping in {"Region", "Item", "Process"} and parts:
            label = parts[0]
        elif parts:
            label = " / ".join(parts)
        else:
            label = group_key
        label_map[(grouping, group_key)] = label
    return label_map


def _group_filter_keys(panel: str, grouping: str) -> List[str]:
    filters = CONFIG.get("quartile_group_filters", {}) or {}
    if (panel, grouping) in filters:
        return [str(x) for x in filters.get((panel, grouping), []) if str(x).strip()]
    if grouping in filters:
        return [str(x) for x in filters.get(grouping, []) if str(x).strip()]
    return []


def _filter_group_keys(
    hist: pd.DataFrame,
    label_map: Dict[Tuple[str, str], str],
    *,
    panel: str,
    grouping: str,
    filters: Sequence[str],
) -> List[str]:
    if not filters:
        return []
    sub = hist[(hist["panel"] == panel) & (hist["grouping"] == grouping)]
    if sub.empty:
        return []
    candidates = sorted({str(x) for x in sub["group_key"].dropna().astype(str)})
    lowered = [f.lower() for f in filters]
    selected: List[str] = []
    for key in candidates:
        label = label_map.get((grouping, key), key)
        text = label.lower()
        if any(f in text for f in lowered):
            selected.append(key)
    return selected


def _curve_y_values(counts: np.ndarray, y_axis_mode: str, bin_width: float, sigma_bins: float) -> np.ndarray:
    y = _smooth_counts(counts.astype(float), sigma_bins)
    total = float(np.nansum(y))
    if total <= 0 or not np.isfinite(total):
        return y
    if y_axis_mode == "probability":
        return y / total
    if y_axis_mode == "density":
        width = bin_width if bin_width > 0 else 1.0
        return y / (total * width)
    return y


def _plot_targets(ax: Axes, targets: Sequence[Tuple[str, float]], *, x_min: float, x_max: float, ymax: float) -> None:
    y_text = ymax * 0.97
    for label, value in targets:
        if value < x_min or value > x_max:
            continue
        color = TARGET_COLORS.get(label, "#666666")
        ax.axvline(value, color=color, linewidth=1.6, linestyle=(0, (6, 4)), alpha=0.92)
        ax.text(
            value + 0.05,
            y_text,
            label,
            color=color,
            fontsize=11,
            fontweight="bold",
            ha="left",
            va="top",
        )


def _plot_quartile_group(
    ax: Axes,
    hist: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    panel: str,
    grouping: str,
    group_key: str,
    label: str,
    panel_spec: Dict[str, object],
    y_axis_mode: str,
    sigma_bins: float,
    targets: Sequence[Tuple[str, float]],
    show_targets: bool,
    x_min: float,
    x_max: float,
) -> None:
    spec = panel_spec
    panel_df = hist[
        (hist["panel"] == panel)
        & (hist["grouping"] == grouping)
        & (hist["group_key"] == group_key)
    ].copy()
    if panel_df.empty:
        ax.set_visible(False)
        return

    panel_df["bin_left"] = pd.to_numeric(panel_df["bin_left"], errors="coerce")
    panel_df["bin_right"] = pd.to_numeric(panel_df["bin_right"], errors="coerce")
    panel_df["count"] = pd.to_numeric(panel_df["count"], errors="coerce").fillna(0.0)
    panel_df = panel_df.dropna(subset=["bin_left", "bin_right"])
    panel_df["x_mid"] = (panel_df["bin_left"] + panel_df["bin_right"]) / 2.0

    widths = panel_df["bin_right"] - panel_df["bin_left"]
    bin_width = float(widths.mean()) if widths.notna().any() else 1.0

    ymax = 0.0
    for key in QUARTILE_KEYS:
        sub = panel_df[panel_df["quartile_key"] == key].sort_values("bin_left")
        if sub.empty:
            continue
        x = sub["x_mid"].to_numpy(dtype=float)
        y = _curve_y_values(sub["count"].to_numpy(dtype=float), y_axis_mode, bin_width, sigma_bins)
        if y.size:
            ymax = max(ymax, float(np.nanmax(y)))

        row = _summary_row(summary, panel, grouping, group_key, key)
        if row is None:
            label_text = QUARTILE_RANGES[key]
            mean_text = ""
        else:
            mean_text = _format_metric_with_unit(float(row["metric_mean"]), spec)
            label_text = f"{QUARTILE_RANGES[key]}, mean {mean_text}" if mean_text else QUARTILE_RANGES[key]

        ax.plot(
            x,
            y,
            color=QUARTILE_COLORS.get(key, "#777777"),
            linewidth=3.4,
            alpha=0.88,
            label=label_text,
        )

        if y.size:
            idx = int(np.nanargmax(y))
            label_inline = f"{key.upper()} {mean_text}".strip()
            ax.text(
                float(x[idx]),
                float(y[idx]) + max(ymax, 1e-9) * 0.06,
                label_inline,
                color=QUARTILE_COLORS.get(key, "#777777"),
                fontsize=9.8,
                fontweight="bold",
                ha="center",
                va="bottom",
            )

    if ymax <= 0:
        ymax = 1.0
    ax.set_ylim(0, ymax * 1.2)
    if show_targets:
        _plot_targets(ax, targets, x_min=x_min, x_max=x_max, ymax=ymax * 1.2)

    ax.set_xlim(x_min, x_max)
    ax.set_title(label, fontsize=12.5, fontweight="bold", loc="left", pad=6)
    ax.tick_params(axis="both", which="both", labelsize=11, width=1.6, length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(1.6)


def _plot_quartile_grid(
    hist: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    panel: str,
    grouping: str,
    group_keys: Sequence[str],
    fig_dir: Path,
    targets: Sequence[Tuple[str, float]],
    panel_specs: Dict[str, Dict[str, object]],
) -> Optional[List[Path]]:
    if not group_keys:
        return None

    sub = hist[(hist["panel"] == panel) & (hist["grouping"] == grouping) & (hist["group_key"].isin(group_keys))]
    if sub.empty:
        return None

    x_min = float(pd.to_numeric(sub["bin_left"], errors="coerce").min())
    x_max = float(pd.to_numeric(sub["bin_right"], errors="coerce").max())

    label_map = _group_label_map(summary)
    cols = int(CONFIG["quartile_grid_cols"])
    rows = int(np.ceil(len(group_keys) / cols))
    fig_width = 12.0
    fig_height = 4.8 * rows
    fig, axes = plt.subplots(rows, cols, figsize=(fig_width, fig_height), squeeze=False)

    y_axis_mode = str(CONFIG["quartile_y_axis_mode"]).strip().lower()
    y_label = {
        "probability": "Probability per bin",
        "density": "Normalized density",
        "count": "Number of simulations",
    }.get(y_axis_mode, "Probability per bin")

    for idx, group_key in enumerate(group_keys):
        ax = axes[idx // cols][idx % cols]
        label = label_map.get((grouping, group_key), group_key)
        _plot_quartile_group(
            ax,
            hist,
            summary,
            panel=panel,
            grouping=grouping,
            group_key=group_key,
            label=label,
            panel_spec=panel_specs.get(panel, {}),
            y_axis_mode=y_axis_mode,
            sigma_bins=float(CONFIG["quartile_smooth_sigma_bins"]),
            targets=targets,
            show_targets=bool(CONFIG["show_target_lines"]),
            x_min=x_min,
            x_max=x_max,
        )

        if idx % cols == 0:
            ax.set_ylabel(y_label, fontsize=12, fontweight="bold", labelpad=8)
        if idx // cols == rows - 1:
            ax.set_xlabel("Group GHG in 2080 (Gt CO2eq/yr)", fontsize=12, fontweight="bold", labelpad=8)

    for idx in range(len(group_keys), rows * cols):
        axes[idx // cols][idx % cols].set_visible(False)

    spec = panel_specs.get(panel, {})
    fig.suptitle(f"{spec.get('title', panel)} - {grouping}", fontsize=14.5, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0.0, 1, 0.96])

    panel_slug = panel.lower().replace(" ", "_")
    grouping_slug = grouping.lower().replace(" ", "_").replace("/", "_")
    outputs = [
        fig_dir / f"FigureS5_5_{panel_slug}_{grouping_slug}_quartile_grid_v1.png",
        fig_dir / f"FigureS5_5_{panel_slug}_{grouping_slug}_quartile_grid_v1.svg",
    ]
    fig.savefig(outputs[0], dpi=int(CONFIG["quartile_dpi"]), bbox_inches="tight")
    fig.savefig(outputs[1], bbox_inches="tight")
    plt.close(fig)
    return outputs


def _pick_top_groups(summary: pd.DataFrame, hist: pd.DataFrame, *, panel: str, grouping: str, top_n: int) -> List[str]:
    if not summary.empty:
        sub = summary[(summary["panel"] == panel) & (summary["grouping"] == grouping)].copy()
        if not sub.empty and "group_emissions_gt_mean" in sub.columns:
            rank = (
                sub.groupby("group_key", as_index=False)["group_emissions_gt_mean"]
                .mean()
                .sort_values("group_emissions_gt_mean", ascending=False)
            )
            return rank["group_key"].head(top_n).astype(str).tolist()

    sub_hist = hist[(hist["panel"] == panel) & (hist["grouping"] == grouping)].copy()
    if sub_hist.empty:
        return []
    rank = (
        sub_hist.groupby("group_key", as_index=False)["count"]
        .sum()
        .sort_values("count", ascending=False)
    )
    return rank["group_key"].head(top_n).astype(str).tolist()


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    args = _build_arg_parser().parse_args()
    output_root = _resolve_output_root(args)
    merged_dir = _resolve_merged_dir(args, output_root)
    fig_dir = _resolve_fig_dir(args)
    _ensure_dir(fig_dir)

    stack_long_path = merged_dir / "structure_stack_top_long.csv"
    if not stack_long_path.exists():
        stack_long_path = merged_dir / "structure_stack_long.csv"
    stack_long = _load_csv(
        stack_long_path,
        required_cols=["target_emission_gt", "grouping", "group_key", "importance"],
    )

    group_tables: Dict[str, Dict[str, pd.DataFrame]] = {}
    for grouping in CONFIG["stack_groupings"]:
        raw_df, pct_df = _build_stack_tables(stack_long, grouping)
        group_tables[grouping] = {"raw": raw_df, "plot": raw_df, "plot_pct": pct_df}

    workbook_path = _write_stack_workbook(group_tables, fig_dir)
    print(f"[DONE] workbook: {workbook_path}")

    for grouping in CONFIG["stack_groupings"]:
        outputs = _plot_stack(
            grouping,
            group_tables[grouping]["plot_pct"],
            fig_dir,
            target=CONFIG["stack_order_target_emis_gt"],
        )
        for path in outputs:
            print(f"[DONE] figure: {path}")

    hist_path = merged_dir / "structure_quartile_histogram_top.csv"
    summary_path = merged_dir / "structure_quartile_summary.csv"
    hist = _load_csv(hist_path, required_cols=["panel", "quartile_key", "grouping", "group_key", "bin_left", "bin_right", "count"])
    summary = pd.DataFrame()
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        summary.columns = [str(c).strip() for c in summary.columns]

    panel_samples = _load_panel_samples(merged_dir)
    panel_specs = _resolve_panel_specs(panel_samples)

    targets = _load_targets() if CONFIG["show_target_lines"] else []
    label_map = _group_label_map(summary)
    for panel in CONFIG["quartile_panels"]:
        if panel not in panel_specs:
            print(f"[WARN] skip quartile panel {panel}: missing PANEL_SPECS entry")
            continue
        for grouping in CONFIG["quartile_groupings"]:
            filters = _group_filter_keys(panel, grouping)
            group_keys = _filter_group_keys(
                hist,
                label_map,
                panel=panel,
                grouping=grouping,
                filters=filters,
            )
            if not group_keys:
                group_keys = _pick_top_groups(
                    summary,
                    hist,
                    panel=panel,
                    grouping=grouping,
                    top_n=int(CONFIG["quartile_top_n_per_grouping"]),
                )
            outputs = _plot_quartile_grid(
                hist,
                summary,
                panel=panel,
                grouping=grouping,
                group_keys=group_keys,
                fig_dir=fig_dir,
                targets=targets,
                panel_specs=panel_specs,
            )
            if not outputs:
                print(f"[WARN] no quartile figure for panel={panel}, grouping={grouping}")
                continue
            for path in outputs:
                print(f"[DONE] figure: {path}")


if __name__ == "__main__":
    main()
