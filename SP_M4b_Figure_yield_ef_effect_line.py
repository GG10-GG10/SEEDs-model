# -*- coding: utf-8 -*-
"""
Plot yield/EF sensitivity curves for Figure 5.
Reads: output/Plot/Fig5/samples.csv or histogram.csv + targets.csv
Outputs: PNG + SVG in the same folder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config_paths import get_results_base

FIG_DIR = Path(get_results_base()) / "Plot" / "Fig5"
SAMPLES_PATH = FIG_DIR / "samples.csv"
HIST_PATH = FIG_DIR / "histogram.csv"
TARGETS_PATH = FIG_DIR / "targets.csv"

TARGET_ORDER = ["1.5D", "2D", "RCP4.5", "Current"]
TARGET_COLORS = {
    "1.5D": "#2ca25f",
    "2D": "#2b8cbe",
    "RCP4.5": "#f1a340",
    "Current": "#d7301f",
}

YIELD_ORDER = ["yield_up_100", "yield_up_50", "yield_current", "yield_down_20"]
EF_ORDER = ["ef_down_80", "ef_down_40", "ef_current", "ef_up_20"]
LABEL_MAP = {
    "yield_up_100": "产率提升100%",
    "yield_up_50": "产率提升50%",
    "yield_current": "当前产率",
    "yield_down_20": "产率降低20%",
    "ef_down_80": "EF降低80%",
    "ef_down_40": "EF降低40%",
    "ef_current": "当前EF",
    "ef_up_20": "EF升高20%",
}

CURVE_COLORS = {
    "yield_up_100": "#2b6cb0",
    "yield_up_50": "#3f8cc8",
    "yield_current": "#5fa7d6",
    "yield_down_20": "#1f4e79",
    "ef_down_80": "#2b6cb0",
    "ef_down_40": "#3f8cc8",
    "ef_current": "#5fa7d6",
    "ef_up_20": "#1f4e79",
}

SMOOTH_SIGMA_BINS = 2.2


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _load_targets() -> List[Tuple[str, float]]:
    if TARGETS_PATH.exists():
        df = pd.read_csv(TARGETS_PATH)
        df.columns = [str(c).strip() for c in df.columns]
        if "label" in df.columns and "emission_gt" in df.columns:
            return [
                (str(r.label), float(r.emission_gt))
                for r in df.itertuples(index=False)
                if pd.notna(r.label) and pd.notna(r.emission_gt)
            ]
    return [("1.5D", 0.9), ("2D", 5.0), ("RCP4.5", 14.5), ("Current", 12.6)]


def _load_histogram() -> pd.DataFrame:
    if HIST_PATH.exists():
        df = pd.read_csv(HIST_PATH)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    if not SAMPLES_PATH.exists():
        raise FileNotFoundError(f"Missing samples.csv or histogram.csv in {FIG_DIR}")
    df = pd.read_csv(SAMPLES_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    if not {"panel", "scenario_key", "emissions_2080_gt"}.issubset(df.columns):
        raise ValueError("samples.csv missing required columns.")
    x_min = float(df["emissions_2080_gt"].min())
    x_max = float(df["emissions_2080_gt"].max())
    bins = 90
    hist_rows: List[Dict[str, object]] = []
    for (panel, key), sub in df.groupby(["panel", "scenario_key"]):
        counts, edges = np.histogram(sub["emissions_2080_gt"], bins=bins, range=(x_min, x_max))
        label = sub["scenario_label"].iloc[0] if "scenario_label" in sub.columns else LABEL_MAP.get(key, key)
        for j in range(len(counts)):
            hist_rows.append(
                {
                    "panel": panel,
                    "scenario_key": key,
                    "scenario_label": label,
                    "bin_left": float(edges[j]),
                    "bin_right": float(edges[j + 1]),
                    "count": int(counts[j]),
                }
            )
    return pd.DataFrame(hist_rows)


def _smooth_counts(counts: np.ndarray, sigma_bins: float) -> np.ndarray:
    if sigma_bins <= 0:
        return counts
    radius = int(max(1, round(sigma_bins * 3)))
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (x / sigma_bins) ** 2)
    kernel /= kernel.sum()
    return np.convolve(counts, kernel, mode="same")


def _plot_panel(ax: plt.Axes, hist: pd.DataFrame, panel: str, order: List[str], title: str) -> None:
    panel_df = hist[hist["panel"] == panel].copy()
    if panel_df.empty:
        raise ValueError(f"No data for panel: {panel}")
    panel_df["bin_left"] = pd.to_numeric(panel_df["bin_left"], errors="coerce")
    panel_df["bin_right"] = pd.to_numeric(panel_df["bin_right"], errors="coerce")
    panel_df["count"] = pd.to_numeric(panel_df["count"], errors="coerce").fillna(0.0)
    panel_df = panel_df.dropna(subset=["bin_left", "bin_right"])
    panel_df["x_mid"] = (panel_df["bin_left"] + panel_df["bin_right"]) / 2.0

    ymax = 0.0
    for key in order:
        sub = panel_df[panel_df["scenario_key"] == key].sort_values("bin_left")
        if sub.empty:
            continue
        x = sub["x_mid"].to_numpy()
        y = sub["count"].to_numpy()
        y = _smooth_counts(y, SMOOTH_SIGMA_BINS)
        ymax = max(ymax, float(np.max(y)) if len(y) else 0.0)
        label = sub["scenario_label"].iloc[0] if "scenario_label" in sub.columns else LABEL_MAP.get(key, key)
        ax.plot(x, y, color=CURVE_COLORS.get(key, "#377eb8"), linewidth=2.2, label=label)

    targets = _load_targets()
    for label, val in targets:
        color = TARGET_COLORS.get(label, "#666666")
        ax.axvline(val, color=color, linewidth=1.6, linestyle=(0, (6, 6)), alpha=0.95)

    if ymax <= 0:
        ymax = 1.0
    ax.set_ylim(0, ymax * 1.15)
    ax.set_title(title, fontsize=12.5, fontweight="bold", loc="left", pad=6)
    ax.set_ylabel("Number of simulations", fontsize=12.5, fontweight="bold", labelpad=10)

    ax.tick_params(axis="both", which="both", labelsize=11.5, width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    _ensure_dir(FIG_DIR)
    hist = _load_histogram()

    fig, axes = plt.subplots(2, 1, figsize=(8.6, 9.2), sharex=True)
    _plot_panel(
        axes[0],
        hist,
        "yield",
        YIELD_ORDER,
        "A. Effects of yield + feed efficiency",
    )
    _plot_panel(
        axes[1],
        hist,
        "emission_factor",
        EF_ORDER,
        "B. Effects of emission intensity",
    )

    axes[1].set_xlabel("GHG in 2080 (Gt CO2eq/yr)", fontsize=12.5, fontweight="bold", labelpad=10)
    xmin = float(hist["bin_left"].min())
    xmax = float(hist["bin_right"].max())
    axes[1].set_xlim(xmin, xmax)

    axes[0].legend(loc="upper right", frameon=False, fontsize=10.5)
    axes[1].legend(loc="upper right", frameon=False, fontsize=10.5)

    fig.tight_layout()
    png_path = FIG_DIR / "Figure5_yield_ef_effect_line.png"
    svg_path = FIG_DIR / "Figure5_yield_ef_effect_line.svg"
    fig.savefig(png_path, dpi=800)
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


if __name__ == "__main__":
    main()
