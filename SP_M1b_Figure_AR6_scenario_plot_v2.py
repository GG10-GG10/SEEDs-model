# -*- coding: utf-8 -*-
"""
Plot AR6 scenario summary panels for Figure 6 (1.5D + 2D in the same panels).
Reads: output/Plot/Fig6/AR6_scenario_prepared_harmonization.xlsx (1.5D_summary, 2D_summary)
Outputs: PNG + SVG in the same folder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

from config_paths import get_results_base

FIG_DIR = Path(get_results_base()) / "Plot" / "Fig6"
INPUT_NAME = "AR6_scenario_prepared_harmonization.xlsx"

# Panel switches: toggle any panel on/off here.
PLOT_SWITCHES = {
    "main": True,
    "afolu_gas": False,
    "yield": False,
    "biomass": False,
    "share_panels": [False, False, False],
}

# Layout knobs for adaptive sizing and label spacing.
# Wider than SP1_6_Figure_AR6_scenario_plot.py as requested.
FIGURE_WIDTH = 7.9
FIGURE_HEIGHT_UNIT = 1.35
Y_LABEL_X = -0.08

# Scenario style: 1.5D solid, 2D long dash.
SCENARIO_STYLES = {
    "1.5D": {"linestyle": "-", "linewidth_scale": 1.0},
    "2D": {"linestyle": (0, (4, 2)), "linewidth_scale": 1.0},
}

MAIN_VARS = [
    "Population",
    "Emissions|CO2eq|AFOLU",
    "Per capita Ag production",
    "Land-use intensity of Ag production",
    "Emission intensity of land use",
    "Emission intensity of Ag production",
]

AFOLU_GAS_VARS = [
    "Emissions|N2O|AFOLU",
    "Emissions|CO2|AFOLU",
    "Emissions|CH4|AFOLU",
]

YIELD_VARS = ["Yield|Cereal"]
BIOMASS_VARS = ["Primary Energy|Biomass"]

SHARE_PANELS = [
    [
        "Land Cover|Cropland_share",
        "Land Cover|Forest_share",
        "Land Cover|Pasture_share",
        "EnergyCropsCroplandShare",
    ],
    [
        "AFOLU land CO2eq share",
        "AFOLU agriculture CO2eq share",
    ],
    [
        "Crop intake share",
        "Livestock intake share",
    ],
]

PANEL_HEIGHT_RATIOS = {
    "main": 3.4,
    "afolu_gas": 1.25,
    "yield": 1.15,
    "biomass": 1.15,
    "share": 1.05,
}

COLOR_MAP = {
    "Population": "#f4751ad3",
    "Emissions|CO2eq|AFOLU": "#8c510a",
    "Per capita Ag production": "#e31a1c",
    "Land-use intensity of Ag production": "#6a51a3ee",
    "Emission intensity of land use": "#41b6c4",
    "Emission intensity of Ag production": "#225ea8",
    "Emissions|N2O|AFOLU": "#6a4c93",
    "Emissions|CO2|AFOLU": "#2f2f2f",
    "Emissions|CH4|AFOLU": "#1f78b4",
    "Yield|Cereal": "#1b9e77",
    "Primary Energy|Biomass": "#8c564b",
    "Land Cover|Cropland_share": "#cb181d",
    "Land Cover|Forest_share": "#006d2c",
    "Land Cover|Pasture_share": "#a6761d",
    "EnergyCropsCroplandShare": "#17becf",
    "AFOLU land CO2eq share": "#f4a3a8",
    "AFOLU agriculture CO2eq share": "#6b5b4d",
    "Crop intake share": "#3182bd",
    "Livestock intake share": "#e6550d",
}

LABEL_MAP = {
    "Population": "Population",
    "Emissions|CO2eq|AFOLU": "Emissions|CO2eq|AFOLU",
    "Per capita Ag production": "Per capita Ag production",
    "Land-use intensity of Ag production": "Land-use intensity of Ag production",
    "Emission intensity of land use": "Emission intensity of land use",
    "Emission intensity of Ag production": "Emission intensity of Ag production",
    "Emissions|N2O|AFOLU": "Emissions|N2O|AFOLU",
    "Emissions|CO2|AFOLU": "Emissions|CO2|AFOLU",
    "Emissions|CH4|AFOLU": "Emissions|CH4|AFOLU",
    "Yield|Cereal": "Yield|Cereal",
    "Primary Energy|Biomass": "Primary Energy|Biomass",
    "Land Cover|Cropland_share": "Cropland share",
    "Land Cover|Forest_share": "Forest share",
    "Land Cover|Pasture_share": "Pasture share",
    "EnergyCropsCroplandShare": "Energy crops/cropland share",
    "AFOLU land CO2eq share": "AFOLU land CO2eq share",
    "AFOLU agriculture CO2eq share": "AFOLU agriculture CO2eq share",
    "Crop intake share": "Crop intake share",
    "Livestock intake share": "Livestock intake share",
}


def _year_cols(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if str(c).startswith("Y") and str(c)[1:].isdigit()]
    return sorted(cols, key=lambda x: int(str(x)[1:]))


def _get_stat_series(df: pd.DataFrame, var: str, stat: str, year_cols: List[str]) -> Optional[np.ndarray]:
    sub = df[(df["Variable"] == var) & (df["Stat"] == stat)]
    if sub.empty:
        return None
    vals = pd.to_numeric(sub.iloc[0][year_cols], errors="coerce").to_numpy(dtype=float)
    return vals


def _read_summary_sheet(input_path: Path, sheet: str) -> Tuple[pd.DataFrame, List[str]]:
    df = pd.read_excel(input_path, sheet_name=sheet)
    df.columns = [str(c).strip() for c in df.columns]
    year_cols = _year_cols(df)
    if not year_cols:
        raise ValueError(f"No year columns found in sheet {sheet}")
    return df, year_cols


def _calc_ylim(series_list: List[np.ndarray], default: Tuple[float, float]) -> Tuple[float, float]:
    if not series_list:
        return default
    arr = np.concatenate([np.ravel(s) for s in series_list if s is not None])
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return default
    lo = float(np.nanmin(arr))
    hi = float(np.nanmax(arr))
    span = hi - lo
    if span <= 1e-9:
        pad = max(abs(hi) * 0.08, 1.0)
    else:
        pad = span * 0.08
    return lo - pad, hi + pad


def _to_share_percent(values: np.ndarray) -> np.ndarray:
    if np.nanmax(values) > 1.5:
        return values
    return values * 100.0


def _compute_common_axis_ranges(
    df_15: pd.DataFrame,
    year_cols_15: List[str],
    df_2d: pd.DataFrame,
    year_cols_2d: List[str],
) -> Dict[str, object]:
    all_years = [int(str(c)[1:]) for c in year_cols_15 + year_cols_2d]
    if not all_years:
        raise ValueError("No year columns available to build common x-axis range.")
    xlim = (min(all_years), max(all_years))

    main_series: List[np.ndarray] = []
    gas_series: List[np.ndarray] = []
    yield_series: List[np.ndarray] = []
    biomass_series: List[np.ndarray] = []
    share_series: List[List[np.ndarray]] = [[] for _ in SHARE_PANELS]

    for df, year_cols in ((df_15, year_cols_15), (df_2d, year_cols_2d)):
        for var in MAIN_VARS:
            avg = _get_stat_series(df, var, "average", year_cols)
            if avg is not None:
                main_series.append(avg)
        for var in AFOLU_GAS_VARS:
            avg = _get_stat_series(df, var, "average", year_cols)
            if avg is not None:
                gas_series.append((avg - 1.0) * 100.0)
        for var in YIELD_VARS:
            avg = _get_stat_series(df, var, "average", year_cols)
            if avg is not None:
                yield_series.append((avg - 1.0) * 100.0)
        for var in BIOMASS_VARS:
            avg = _get_stat_series(df, var, "average", year_cols)
            if avg is not None:
                biomass_series.append((avg - 1.0) * 100.0)
        for idx, panel_vars in enumerate(SHARE_PANELS):
            for var in panel_vars:
                avg = _get_stat_series(df, var, "average", year_cols)
                if avg is not None:
                    share_series[idx].append(_to_share_percent(avg))

    return {
        "xlim": xlim,
        "main_ylim": (-0.6, 2.2),
        "gas_ylim": _calc_ylim(gas_series, default=(-10.0, 10.0)),
        "yield_ylim": _calc_ylim(yield_series, default=(-10.0, 10.0)),
        "biomass_ylim": _calc_ylim(biomass_series, default=(-10.0, 10.0)),
        "share_ylims": [_calc_ylim(vals, default=(0.0, 100.0)) for vals in share_series],
    }


def _build_panel_specs() -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    if PLOT_SWITCHES.get("main", True):
        specs.append({"kind": "main", "height_ratio": PANEL_HEIGHT_RATIOS["main"]})
    if PLOT_SWITCHES.get("afolu_gas", True):
        specs.append(
            {
                "kind": "relative",
                "name": "afolu_gas",
                "variables": AFOLU_GAS_VARS,
                "line_width": 2.2,
                "legend_ncol": 1,
                "height_ratio": PANEL_HEIGHT_RATIOS["afolu_gas"],
            }
        )
    if PLOT_SWITCHES.get("yield", True):
        specs.append(
            {
                "kind": "relative",
                "name": "yield",
                "variables": YIELD_VARS,
                "line_width": 2.4,
                "legend_ncol": 1,
                "height_ratio": PANEL_HEIGHT_RATIOS["yield"],
            }
        )
    if PLOT_SWITCHES.get("biomass", True):
        specs.append(
            {
                "kind": "relative",
                "name": "biomass",
                "variables": BIOMASS_VARS,
                "line_width": 2.4,
                "legend_ncol": 1,
                "height_ratio": PANEL_HEIGHT_RATIOS["biomass"],
            }
        )

    share_switches = PLOT_SWITCHES.get("share_panels", [True] * len(SHARE_PANELS))
    for idx, vars_panel in enumerate(SHARE_PANELS):
        enabled = share_switches[idx] if idx < len(share_switches) else True
        if not enabled:
            continue
        specs.append(
            {
                "kind": "share",
                "share_index": idx,
                "variables": vars_panel,
                "height_ratio": PANEL_HEIGHT_RATIOS["share"],
            }
        )
    return specs


def _plot_main_panel_combined(
    ax: Axes,
    df_15: pd.DataFrame,
    year_cols_15: List[str],
    df_2d: pd.DataFrame,
    year_cols_2d: List[str],
) -> None:
    years_15 = np.array([int(str(c)[1:]) for c in year_cols_15], dtype=int)
    years_2d = np.array([int(str(c)[1:]) for c in year_cols_2d], dtype=int)

    for var in MAIN_VARS:
        color = COLOR_MAP.get(var, "#333333")

        avg_15 = _get_stat_series(df_15, var, "average", year_cols_15)
        if avg_15 is not None:
            ax.plot(
                years_15,
                avg_15,
                color=color,
                linewidth=5.,
                linestyle=SCENARIO_STYLES["1.5D"]["linestyle"],
                alpha=0.65,
                label=f"{LABEL_MAP.get(var, var)} (1.5D)",
            )

        avg_2d = _get_stat_series(df_2d, var, "average", year_cols_2d)
        if avg_2d is not None:
            ax.plot(
                years_2d,
                avg_2d,
                color=color,
                linewidth=5.4,
                linestyle=SCENARIO_STYLES["2D"]["linestyle"],
                alpha=0.98,
                label=f"{LABEL_MAP.get(var, var)} (2D)",
            )

    ax.axhline(1.0, color="#333333", linewidth=1.6, linestyle=(0, (5, 3)))
    ax.set_ylabel("Ratio (2010 = 1)", fontsize=12.5, fontweight="bold", labelpad=10)
    ax.tick_params(axis="both", which="both", labelsize=11.5, width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)


def _plot_relative_panel_combined(
    ax: Axes,
    df_15: pd.DataFrame,
    year_cols_15: List[str],
    df_2d: pd.DataFrame,
    year_cols_2d: List[str],
    variables: List[str],
    *,
    line_width: float = 2.2,
) -> None:
    years_15 = np.array([int(str(c)[1:]) for c in year_cols_15], dtype=int)
    years_2d = np.array([int(str(c)[1:]) for c in year_cols_2d], dtype=int)

    for var in variables:
        color = COLOR_MAP.get(var, "#444444")

        avg_15 = _get_stat_series(df_15, var, "average", year_cols_15)
        if avg_15 is not None:
            ax.plot(
                years_15,
                (avg_15 - 1.0) * 100.0,
                color=color,
                linewidth=line_width,
                linestyle=SCENARIO_STYLES["1.5D"]["linestyle"],
                label=f"{LABEL_MAP.get(var, var)} (1.5D)",
            )

        avg_2d = _get_stat_series(df_2d, var, "average", year_cols_2d)
        if avg_2d is not None:
            ax.plot(
                years_2d,
                (avg_2d - 1.0) * 100.0,
                color=color,
                linewidth=line_width,
                linestyle=SCENARIO_STYLES["2D"]["linestyle"],
                label=f"{LABEL_MAP.get(var, var)} (2D)",
            )

    ax.axhline(0, color="#333333", linewidth=1.3, linestyle=(0, (5, 3)))
    ax.set_ylabel("Rel. change (%)", fontsize=11.0, fontweight="bold", labelpad=8)
    ax.tick_params(axis="both", which="both", labelsize=10.5, width=1.6, length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(1.6)


def _plot_share_panel_combined(
    ax: Axes,
    df_15: pd.DataFrame,
    year_cols_15: List[str],
    df_2d: pd.DataFrame,
    year_cols_2d: List[str],
    variables: List[str],
) -> None:
    years_15 = np.array([int(str(c)[1:]) for c in year_cols_15], dtype=int)
    years_2d = np.array([int(str(c)[1:]) for c in year_cols_2d], dtype=int)

    for var in variables:
        color = COLOR_MAP.get(var, "#666666")

        avg_15 = _get_stat_series(df_15, var, "average", year_cols_15)
        if avg_15 is not None:
            ax.plot(
                years_15,
                _to_share_percent(avg_15),
                color=color,
                linewidth=2.2,
                linestyle=SCENARIO_STYLES["1.5D"]["linestyle"],
                label=f"{LABEL_MAP.get(var, var)} (1.5D)",
            )

        avg_2d = _get_stat_series(df_2d, var, "average", year_cols_2d)
        if avg_2d is not None:
            ax.plot(
                years_2d,
                _to_share_percent(avg_2d),
                color=color,
                linewidth=2.2,
                linestyle=SCENARIO_STYLES["2D"]["linestyle"],
                label=f"{LABEL_MAP.get(var, var)} (2D)",
            )

    ax.set_ylabel("Share (%)", fontsize=11.5, fontweight="bold", labelpad=8)
    ax.tick_params(axis="both", which="both", labelsize=10.5, width=1.6, length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(1.6)


def _plot_summary_combined(
    df_15: pd.DataFrame,
    year_cols_15: List[str],
    df_2d: pd.DataFrame,
    year_cols_2d: List[str],
    axis_ranges: Optional[Dict[str, object]] = None,
) -> None:
    panel_specs = _build_panel_specs()
    if not panel_specs:
        raise ValueError("No panels enabled in PLOT_SWITCHES.")

    height_ratios = [float(cast(float, spec["height_ratio"])) for spec in panel_specs]
    fig_height = max(4.8, sum(height_ratios) * FIGURE_HEIGHT_UNIT)
    fig, axes = plt.subplots(
        len(panel_specs),
        1,
        figsize=(FIGURE_WIDTH, fig_height),
        sharex=True,
        gridspec_kw={"height_ratios": height_ratios},
    )

    axes_arr = np.atleast_1d(axes)
    for ax, spec in zip(axes_arr, panel_specs):
        kind = spec["kind"]
        if kind == "main":
            _plot_main_panel_combined(ax, df_15, year_cols_15, df_2d, year_cols_2d)
            ax.set_title("Global", fontsize=13.5, fontweight="bold", pad=6)
            if axis_ranges is not None:
                ax.set_ylim(axis_ranges["main_ylim"])

            var_handles = [
                Line2D([0], [0], color=COLOR_MAP.get(var, "#333333"), linewidth=3.4, linestyle="-", label=LABEL_MAP.get(var, var))
                for var in MAIN_VARS
            ]
            scenario_handles = [
                Line2D([0], [0], color="#222222", linewidth=3.4, linestyle=SCENARIO_STYLES["1.5D"]["linestyle"], label="1.5D"),
                Line2D([0], [0], color="#222222", linewidth=3.4, linestyle=SCENARIO_STYLES["2D"]["linestyle"], label="2D"),
            ]
            legend1 = ax.legend(handles=var_handles, loc="upper center", frameon=False, ncol=2, fontsize=9.7)
            ax.add_artist(legend1)
            ax.legend(handles=scenario_handles, loc="upper right", frameon=False, fontsize=9.7)

        elif kind == "relative":
            _plot_relative_panel_combined(
                ax,
                df_15,
                year_cols_15,
                df_2d,
                year_cols_2d,
                cast(List[str], spec["variables"]),
                line_width=float(cast(float, spec["line_width"])),
            )
            name = cast(str, spec["name"])
            if axis_ranges is not None and name == "afolu_gas":
                ax.set_ylim(axis_ranges["gas_ylim"])
            if axis_ranges is not None and name == "yield":
                ax.set_ylim(axis_ranges["yield_ylim"])
            if axis_ranges is not None and name == "biomass":
                ax.set_ylim(axis_ranges["biomass_ylim"])
            ax.legend(loc="upper left", frameon=False, fontsize=9.0, ncol=1)

        elif kind == "share":
            _plot_share_panel_combined(
                ax,
                df_15,
                year_cols_15,
                df_2d,
                year_cols_2d,
                cast(List[str], spec["variables"]),
            )
            share_index = int(cast(int, spec["share_index"]))
            if axis_ranges is not None:
                share_ylims = cast(List[Tuple[float, float]], axis_ranges["share_ylims"])
                if share_index < len(share_ylims):
                    ax.set_ylim(share_ylims[share_index])
            ax.legend(loc="upper left", frameon=False, fontsize=9.0)

        ax.yaxis.set_label_coords(Y_LABEL_X, 0.5)

    if axis_ranges is not None:
        xlim = axis_ranges["xlim"]
        for ax in axes_arr:
            ax.set_xlim(xlim)

    axes_arr[-1].set_xlabel("Year", fontsize=12.5, fontweight="bold", labelpad=8)
    axes_arr[-1].set_xticks([2010, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100])

    fig.tight_layout()
    png_path = FIG_DIR / "Figure6_AR6_summary_v2.png"
    svg_path = FIG_DIR / "Figure6_AR6_summary_v2.svg"
    fig.savefig(png_path, dpi=800)
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    input_path = FIG_DIR / INPUT_NAME
    if not input_path.exists():
        raise FileNotFoundError(f"Missing file: {input_path}")

    df_15, year_cols_15 = _read_summary_sheet(input_path, "1.5D_summary")
    df_2d, year_cols_2d = _read_summary_sheet(input_path, "2D_summary")
    axis_ranges = _compute_common_axis_ranges(df_15, year_cols_15, df_2d, year_cols_2d)

    _plot_summary_combined(df_15, year_cols_15, df_2d, year_cols_2d, axis_ranges=axis_ranges)


if __name__ == "__main__":
    main()
