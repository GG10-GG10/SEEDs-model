# -*- coding: utf-8 -*-
"""
Plot AR6 summary-amount comparison panels (1.5D vs 2D), one variable per figure.
Reads:
  output/Plot/Fig6/AR6_scenario_prepared_harmonization.xlsx
  - 1.5D_summary_amount
  - 2D_summary_amount
Outputs:
  PNG + SVG in the same folder.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config_paths import get_results_base

FIG_DIR = Path(get_results_base()) / "Plot" / "Fig6"
INPUT_NAME = "AR6_scenario_prepared_harmonization.xlsx"

SHEET_15 = "1.5D_summary_amount"
SHEET_2D = "2D_summary_amount"

PLOT_VARS = [
    "Emissions|CO2eq|AFOLU",
    "Emissions|CO2eq|AFOLU|Agriculture",
    "Emissions|CO2eq|AFOLU|Land",
    "Emissions|CH4|AFOLU",
    "Emissions|N2O|AFOLU",
    "Emissions|CO2|AFOLU",
    "Emission intensity of Ag production",
    "Emission intensity of land use",
    "Land-use intensity of Ag production",
    "Per capita Ag production",
    "Yield|Cereal",
    "Land Cover|Forest_share",
    "Land Cover|Pasture_share",
    "Land Cover|Cropland_share",
    "EnergyCropsCroplandShare",
    "Primary Energy|Biomass",
]

SCENARIO_STYLE = {
    "1.5D": {"color": "#1f77b4"},
    "2D": {"color": "#d62728"},
}
XTICKS = [2010, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
FIXED_YLIM_VARS = {
    "Emissions|CO2eq|AFOLU|Agriculture": (2.0, 8.0),
    "Land Cover|Forest_share": (0.24, 0.48),
    "Yield|Cereal": (2.8, 7.0),
}
FIGURE_WIDTH = 4.8
FIGURE_HEIGHT = 3.5


def _year_cols(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if str(c).startswith("Y") and str(c)[1:].isdigit()]
    return sorted(cols, key=lambda x: int(str(x)[1:]))


def _read_sheet(path: Path, sheet: str) -> Tuple[pd.DataFrame, List[str]]:
    df = pd.read_excel(path, sheet_name=sheet)
    df.columns = [str(c).strip() for c in df.columns]
    if "Variable" not in df.columns or "Stat" not in df.columns:
        raise ValueError(f"Sheet {sheet} must include columns: Variable, Stat")
    year_cols = _year_cols(df)
    if not year_cols:
        raise ValueError(f"No year columns found in sheet: {sheet}")
    return df, year_cols


def _series_for(df: pd.DataFrame, var: str, stat: str, year_cols: List[str]) -> Optional[np.ndarray]:
    sub = df[(df["Variable"] == var) & (df["Stat"] == stat)]
    if sub.empty:
        return None
    vals = pd.to_numeric(sub.iloc[0][year_cols], errors="coerce").to_numpy(dtype=float)
    return vals


def _unit_for(df: pd.DataFrame, var: str) -> str:
    sub = df[df["Variable"] == var]
    if sub.empty or "Unit" not in sub.columns:
        return ""
    unit_vals = sub["Unit"].dropna().astype(str)
    if unit_vals.empty:
        return ""
    return unit_vals.iloc[0]


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def _is_emissions_co2_or_co2eq(var: str) -> bool:
    if not var.startswith("Emissions|"):
        return False
    return ("CO2eq" in var) or ("|CO2|" in var) or var.endswith("|CO2")


def _is_emissions_n2o(var: str) -> bool:
    if not var.startswith("Emissions|"):
        return False
    return ("|N2O|" in var) or var.endswith("|N2O")


def _convert_mt_to_gt(
    var: str,
    unit: str,
    *arrays: Optional[np.ndarray],
) -> Tuple[str, List[Optional[np.ndarray]]]:
    if not _is_emissions_co2_or_co2eq(var):
        return unit, list(arrays)

    converted: List[Optional[np.ndarray]] = []
    for arr in arrays:
        if arr is None:
            converted.append(None)
        else:
            converted.append(arr / 1000.0)

    new_unit = unit
    if new_unit:
        new_unit = new_unit.replace("Mt", "Gt")
    return new_unit, converted


def _convert_n2o_to_mt(
    var: str,
    unit: str,
    *arrays: Optional[np.ndarray],
) -> Tuple[str, List[Optional[np.ndarray]]]:
    if not _is_emissions_n2o(var):
        return unit, list(arrays)

    unit_lower = unit.lower()
    need_convert = "kt" in unit_lower
    if not need_convert:
        return unit, list(arrays)

    converted: List[Optional[np.ndarray]] = []
    for arr in arrays:
        if arr is None:
            converted.append(None)
        else:
            converted.append(arr / 1000.0)

    new_unit = unit
    if new_unit:
        # Keep wording, only convert mass unit text to Mt.
        new_unit = re.sub(r"(?i)kt", "Mt", new_unit)
    else:
        new_unit = "Mt"
    return new_unit, converted


def _plot_variable(
    var: str,
    years_15: np.ndarray,
    years_2d: np.ndarray,
    mean_15: Optional[np.ndarray],
    min_15: Optional[np.ndarray],
    max_15: Optional[np.ndarray],
    mean_2d: Optional[np.ndarray],
    min_2d: Optional[np.ndarray],
    max_2d: Optional[np.ndarray],
    unit: str,
    xlim: Tuple[int, int],
) -> Optional[Tuple[Path, Path]]:
    if mean_15 is None and mean_2d is None:
        print(f"[SKIP] {var}: missing in both sheets")
        return None

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    def _plot_scenario(
        years: np.ndarray,
        mean_vals: Optional[np.ndarray],
        min_vals: Optional[np.ndarray],
        max_vals: Optional[np.ndarray],
        color: str,
        label: str,
    ) -> None:
        if mean_vals is None:
            return

        # Draw 2010-2020 in black solid line.
        mask_hist = years <= 2020
        # Draw scenario color and uncertainty only after 2020.
        mask_future_line = years >= 2020
        mask_future_fill = years >= 2020

        if mask_hist.any():
            ax.plot(years[mask_hist], mean_vals[mask_hist], color="#000000", linewidth=5.5)

        if min_vals is not None and max_vals is not None and np.count_nonzero(mask_future_fill) >= 2:
            ax.fill_between(
                years[mask_future_fill],
                min_vals[mask_future_fill],
                max_vals[mask_future_fill],
                color=color,
                alpha=0.20,
                linewidth=0,
            )

        if mask_future_line.any():
            ax.plot(years[mask_future_line], mean_vals[mask_future_line], color=color, linewidth=5.5, label=label)
        elif mask_hist.any():
            ax.plot(years[mask_hist], mean_vals[mask_hist], color="#000000", linewidth=5.5, label=label)

    _plot_scenario(
        years_15,
        mean_15,
        min_15,
        max_15,
        SCENARIO_STYLE["1.5D"]["color"],
        "1.5D average",
    )
    _plot_scenario(
        years_2d,
        mean_2d,
        min_2d,
        max_2d,
        SCENARIO_STYLE["2D"]["color"],
        "2D average",
    )

    ax.axhline(0, color="#333333", linewidth=1.6, linestyle=(0, (5, 5)))
    ax.set_title(var, fontsize=13.5, fontweight="bold", pad=8)
    if unit:
        ax.set_ylabel(unit, fontsize=12.5, fontweight="bold")
    else:
        ax.set_ylabel("Value", fontsize=12.5, fontweight="bold")
    ax.set_xlabel("")
    ax.set_xlim(xlim)
    fixed_ylim = FIXED_YLIM_VARS.get(var)
    if fixed_ylim is not None:
        ax.set_ylim(fixed_ylim)
    ax.set_xticks(XTICKS)
    ax.tick_params(axis="x", labelrotation=45)
    ax.tick_params(axis="both", which="both", labelsize=11.5, width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)
    ax.legend(loc="best", frameon=False, fontsize=10)

    safe_var = _safe_filename(var)
    png_path = FIG_DIR / f"Figure6_AR6_amount_{safe_var}.png"
    svg_path = FIG_DIR / f"Figure6_AR6_amount_{safe_var}.svg"
    fig.tight_layout()
    fig.savefig(png_path, dpi=700)
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")
    return png_path, svg_path


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 11

    input_path = FIG_DIR / INPUT_NAME
    if not input_path.exists():
        raise FileNotFoundError(f"Missing file: {input_path}")

    df_15, year_cols_15 = _read_sheet(input_path, SHEET_15)
    df_2d, year_cols_2d = _read_sheet(input_path, SHEET_2D)

    years_15 = np.array([int(c[1:]) for c in year_cols_15], dtype=int)
    years_2d = np.array([int(c[1:]) for c in year_cols_2d], dtype=int)
    all_years = np.concatenate([years_15, years_2d])
    xlim = (int(np.min(all_years)), int(np.max(all_years)))

    for var in PLOT_VARS:
        mean_15 = _series_for(df_15, var, "average", year_cols_15)
        min_15 = _series_for(df_15, var, "minbound", year_cols_15)
        max_15 = _series_for(df_15, var, "maxbound", year_cols_15)

        mean_2d = _series_for(df_2d, var, "average", year_cols_2d)
        min_2d = _series_for(df_2d, var, "minbound", year_cols_2d)
        max_2d = _series_for(df_2d, var, "maxbound", year_cols_2d)

        unit = _unit_for(df_15, var) or _unit_for(df_2d, var)
        unit, converted = _convert_mt_to_gt(
            var,
            unit,
            mean_15,
            min_15,
            max_15,
            mean_2d,
            min_2d,
            max_2d,
        )
        unit, converted = _convert_n2o_to_mt(var, unit, *converted)
        mean_15, min_15, max_15, mean_2d, min_2d, max_2d = converted
        _plot_variable(
            var=var,
            years_15=years_15,
            years_2d=years_2d,
            mean_15=mean_15,
            min_15=min_15,
            max_15=max_15,
            mean_2d=mean_2d,
            min_2d=min_2d,
            max_2d=max_2d,
            unit=unit,
            xlim=xlim,
        )


if __name__ == "__main__":
    main()
