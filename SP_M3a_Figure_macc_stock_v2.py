# -*- coding: utf-8 -*-
"""
Plot global MACC remaining emissions stack for Figure 4.
Reads: output/Plot/Fig4/Figure4.xlsx (sheet: global_macc)
Outputs: PNG + SVG in the same folder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from config_paths import get_results_base

process_colors = {
    "Reduce Ruminate": "#e31a1c",
    "Improve yield rate": "#6a51a3ee",
    "Manure management": "#225ea8",
    "Improve feed efficiency": "#cbbcdc",
    "Enteric fermentation management": "#41b6c4",
    "Improve fertilizer efficiency": "#edf8b1",
    "Rice cultivation": "#7fcdbb",
    "Crop residue management": "#1d91c0",
    "Reduce waste": "#fb9a99",
}

process_orders = [
    "Reduce ruminate",
    "Reduce waste",
    "Yield rate",
    "Feed efficiency",
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
label_map: Dict[str, str] = {
    'Yield rate': 'Improve yield rate',
    'Feed efficiency': 'Improve feed efficiency',
    'Fertilizer efficiency': 'Improve fertilizer efficiency',
    'Enteric fermentation management': 'Improve enteric fermentation management',
    'Manure management': 'Improve manure management',
    'Crop residue+soil management': 'Improve crop residue management',
    'Reduce reminate': 'Reduce ruminate',
}
fallback_color = "#d9d9d9"
wood_label = "Wood harvest+Fire+Soil"
wood_color = "#e0e0e0"
wood_line_color = "#6b3a15"


def _find_price_col(df: pd.DataFrame) -> str:
    for col in df.columns:
        if str(col).strip().lower() in {"price_usd_per_ton", "price", "carbon_price"}:
            return col
    raise ValueError("Missing price column in global_macc sheet.")


def _get_baseline_row(df: pd.DataFrame, price_col: str) -> pd.Series:
    label = df[price_col].astype(str).str.lower()
    mask = label.str.contains("baseline")
    if not mask.any():
        raise ValueError("Baseline emission row not found.")
    return df.loc[mask].iloc[0]


def _text_color(hex_color: str) -> str:
    text = hex_color.lstrip("#")
    if len(text) != 6:
        return "black"
    r = int(text[0:2], 16)
    g = int(text[2:4], 16)
    b = int(text[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    return "white" if luminance < 0.55 else "black"


def _canonical_process(name: str) -> str:
    return alias_map.get(name, name)


def _pchip_interpolate(df: pd.DataFrame, target_index: np.ndarray) -> pd.DataFrame:
    df = df.copy()
    combined = df.index.union(target_index)
    combined = combined.sort_values().unique()
    df = df.reindex(combined)
    try:
        return df.interpolate(method="pchip").loc[target_index]
    except Exception:
        return df.interpolate(method="linear").loc[target_index]


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 11

    fig_dir = Path(get_results_base()) / "Plot" / "Fig4"
    xlsx_path = fig_dir / "Figure4.xlsx"
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Missing file: {xlsx_path}")

    df = pd.read_excel(xlsx_path, sheet_name="global_macc")
    df.columns = [str(c).strip() for c in df.columns]
    price_col = _find_price_col(df)

    baseline_row = _get_baseline_row(df, price_col)
    process_cols = [c for c in df.columns if c != price_col]

    baseline_vals = pd.to_numeric(baseline_row[process_cols], errors="coerce").fillna(0.0)

    price_num = pd.to_numeric(df[price_col], errors="coerce")
    df_num = df[price_num.notna()].copy()
    df_num[price_col] = price_num[price_num.notna()].astype(float)
    df_num = df_num.sort_values(price_col)
    df_num = df_num.set_index(price_col)

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

    fig, ax = plt.subplots(figsize=(5.2, 8.6))
    current_y = np.full_like(x, float(baseline_vals.sum()))
    for col in ordered_cols:
        abate = df_final[col].to_numpy(dtype=float)
        next_y = np.maximum(current_y - abate, 0.0)
        key = _canonical_process(col)
        color = process_colors.get(key, fallback_color)
        ax.fill_between(x, current_y, next_y, color=color, alpha=0.95,
                        edgecolor="white", linewidth=0.5)
        current_y = next_y

    baseline_total = float(baseline_vals.sum())
    ax.axhline(baseline_total, color="black", linestyle="--", linewidth=1.2)

    ax.set_xlabel("Abatement cost ($/tCO2eq)", fontsize=13.5, fontweight="bold", labelpad=10)
    ax.set_ylabel("Remaining emissions (Gt CO2eq)", fontsize=13.5, fontweight="bold", labelpad=10)
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, baseline_total * 1.05)
    ax.set_xticks([0, 200, 400, 600, 800, 1000])
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("$%d"))
    ax.set_yticks([0, 3, 6, 9, 12, 15, 18])
    ax.tick_params(axis="both", which="both", labelsize=13, width=1.8, length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)
    ax.spines["top"].set_visible(False)

    ax.fill_between(x, current_y, 0, color=wood_color, alpha=1.0)
    if wood_col and wood_col in baseline_vals.index:
        wood_val = float(baseline_vals[wood_col])
        ax.axhline(wood_val, color=wood_line_color, linestyle=(0, (6, 4)), linewidth=1.4)

    # ax.legend()

    fig.tight_layout()
    png_path = fig_dir / "Figure4_global_macc.png"
    svg_path = fig_dir / "Figure4_global_macc.svg"
    fig.savefig(png_path, dpi=600)
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


if __name__ == "__main__":
    main()
