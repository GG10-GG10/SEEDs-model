# -*- coding: utf-8 -*-
"""
Plot global MACC remaining emissions stack for Figure 4 (three bio cases).
Reads: output/Plot/Fig4/Figure4.xlsx (sheets: low_Bio, medium_Bio, high_Bio)
Outputs: PNG + SVG in the same folder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, cast

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.axes import Axes

from config_paths import get_results_base

SHEET_SPECS = [
    ("low_Bio", "Low Bio"),
    ("medium_Bio", "Medium Bio"),
    ("high_Bio", "High Bio"),
]

# Top-row layout for combining with SP1_3 map as the second row.
TOP_ROW_WIDTH = 12.2
TOP_ROW_HEIGHT = 6.0

COMMON_Y_MAX = 22.0

process_colors = {
    "Reduce Ruminate": "#6a51a3",
    "Improve yield rate": "#e31a1c",
    "Manure management": "#225ea8",
    "Improve feed efficiency": "#fb9a99",
    "Enteric fermentation management": "#41b6c4",
    "Improve fertilizer efficiency": "#edf8b1",
    "Rice cultivation": "#7fcdbb",
    "Crop residue management": "#1d91c0",
    "Reduce waste": "#cbbcdc",
}

process_orders = [
    "Yield rate",
    "Feed efficiency",
    "Reduce ruminate",
    "Reduce waste",
    "Manure management",
    "Crop residue+soil management",
    "Enteric fermentation management",
    "Rice cultivation",
    "Fertilizer efficiency",
]

alias_map: Dict[str, str] = {
    "Reduce reminate": "Reduce Ruminate",
    "Reduce ruminate": "Reduce Ruminate",
    "Yield rate": "Improve yield rate",
    "Feed efficiency": "Improve feed efficiency",
    "Fertilizer efficiency": "Improve fertilizer efficiency",
    "Crop residue+soil management": "Crop residue management",
}
fallback_color = "#d9d9d9"
wood_color = "#e0e0e0"
wood_line_color = "#6b3a15"


def _find_price_col(df: pd.DataFrame) -> str:
    for col in df.columns:
        if str(col).strip().lower() in {"price_usd_per_ton", "price", "carbon_price"}:
            return col
    raise ValueError("Missing price column in sheet.")


def _get_baseline_row(df: pd.DataFrame, price_col: str) -> pd.Series:
    label = df[price_col].astype(str).str.lower()
    mask = label.str.contains("baseline")
    if not mask.any():
        raise ValueError("Baseline emission row not found.")
    return df.loc[mask].iloc[0]


def _canonical_process(name: str) -> str:
    return alias_map.get(name, name)


def _pchip_interpolate(df: pd.DataFrame, target_index: np.ndarray) -> pd.DataFrame:
    df = df.copy()
    combined = df.index.union(pd.Index(target_index))
    combined = combined.sort_values().unique()
    df = df.reindex(combined)
    try:
        return df.interpolate(method="pchip").loc[target_index]
    except Exception:
        return df.interpolate(method="linear").loc[target_index]


def _prepare_sheet(df: pd.DataFrame) -> Dict[str, Any]:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    price_col = _find_price_col(df)

    baseline_row = _get_baseline_row(df, price_col)
    process_cols = [c for c in df.columns if c != price_col]
    baseline_vals = pd.to_numeric(baseline_row[process_cols], errors="coerce").fillna(0.0)

    price_num = pd.to_numeric(df[price_col], errors="coerce")
    df_num = df[price_num.notna()].copy()
    df_num[price_col] = price_num[price_num.notna()].astype(float)
    df_num = df_num.sort_values(price_col).set_index(price_col)

    target_index = np.arange(0, 1001, 10)
    abate_vals = df_num[process_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    df_final = _pchip_interpolate(abate_vals, target_index)

    x = df_final.index.to_numpy(dtype=float)
    idx_1000 = int(np.abs(x - 1000).argmin())
    wood_cols = [c for c in process_cols if str(c).strip().lower().startswith("wood harvest")]
    wood_col = wood_cols[0] if wood_cols else None
    strategy_cols = [c for c in process_cols if c != wood_col]
    order_desc = df_final.iloc[idx_1000][strategy_cols].sort_values(ascending=False).index.tolist()

    canonical_cols: Dict[str, str] = {}
    for col in strategy_cols:
        canonical_cols.setdefault(_canonical_process(col), col)

    ordered_cols = []
    for proc in process_orders:
        canonical = _canonical_process(proc)
        col = canonical_cols.get(canonical)
        if col and col not in ordered_cols:
            ordered_cols.append(col)
    for col in order_desc:
        if col not in ordered_cols:
            ordered_cols.append(col)

    return {
        "x": x,
        "df_final": df_final,
        "ordered_cols": ordered_cols,
        "wood_col": wood_col,
        "baseline_total": float(baseline_vals.sum()),
        "baseline_vals": baseline_vals,
    }


def _plot_one(
    ax: Axes,
    data: Dict[str, Any],
    title: str,
    show_ylabel: bool,
    y_max: float,
    y_ticks: np.ndarray,
) -> None:
    x = cast(np.ndarray, data["x"])
    df_final = cast(pd.DataFrame, data["df_final"])
    ordered_cols = cast(list, data["ordered_cols"])
    wood_col = cast(Optional[str], data["wood_col"])
    baseline_total = float(cast(float, data["baseline_total"]))
    baseline_vals = cast(pd.Series, data["baseline_vals"])

    current_y = np.full_like(x, baseline_total)
    for col in ordered_cols:
        abate = df_final[col].to_numpy(dtype=float)
        next_y = np.maximum(current_y - abate, 0.0)
        key = _canonical_process(col)
        color = process_colors.get(key, fallback_color)
        ax.fill_between(x, current_y, next_y, color=color, alpha=0.95, edgecolor="white", linewidth=0.5)
        current_y = next_y

    ax.fill_between(x, current_y, 0, color=wood_color, alpha=1.0)
    ax.axhline(baseline_total, color="black", linestyle="--", linewidth=1.2)

    if isinstance(wood_col, str) and wood_col in baseline_vals.index:
        wood_val = float(baseline_vals[wood_col])
        ax.axhline(wood_val, color=wood_line_color, linestyle=(0, (6, 4)), linewidth=1.4)

    ax.set_title(title, fontsize=12.5, fontweight="bold", pad=4)
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, y_max)
    ax.set_xticks([0, 200, 400, 600, 800, 1000])
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("$%d"))
    ax.set_yticks(y_ticks)
    # Match SP1_6 tick style: longer and thicker major ticks.
    ax.tick_params(axis="both", which="both", labelsize=11.5, width=1.8, length=8)
    # With shared y-axis, explicitly keep y tick labels visible on every panel.
    ax.tick_params(axis="y", labelleft=True)

    for spine in ax.spines.values():
        spine.set_linewidth(1.8)
    ax.spines["top"].set_visible(False)

    ax.set_xlabel("Abatement cost ($/tCO2eq)", fontsize=12.0, fontweight="bold", labelpad=7)
    if show_ylabel:
        ax.set_ylabel("Remaining emissions (Gt CO2eq)", fontsize=12.0, fontweight="bold", labelpad=8)


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 11

    fig_dir = Path(get_results_base()) / "Plot" / "Fig4"
    xlsx_path = fig_dir / "Figure4_v2.xlsx"
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Missing file: {xlsx_path}")

    sheet_data = []
    for sheet_name, title in SHEET_SPECS:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        sheet_data.append((title, _prepare_sheet(df)))

    # Use one fixed common y-axis for all three panels.
    y_top = COMMON_Y_MAX
    y_step = 3.0
    common_y_ticks = np.arange(0.0, y_top + 0.5 * y_step, y_step)

    # Three horizontal panels; tuned for a two-row composite figure.
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(TOP_ROW_WIDTH, TOP_ROW_HEIGHT),
        sharex=True,
        sharey=True,
    )

    for i, (ax, (title, data)) in enumerate(zip(axes, sheet_data)):
        _plot_one(
            ax,
            data,
            title,
            show_ylabel=(i == 0),
            y_max=y_top,
            y_ticks=common_y_ticks,
        )

    fig.tight_layout(w_pad=1.5)
    png_path = fig_dir / "Figure4_global_macc_v3.png"
    svg_path = fig_dir / "Figure4_global_macc_v3.svg"
    fig.savefig(png_path, dpi=600)
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


if __name__ == "__main__":
    main()
