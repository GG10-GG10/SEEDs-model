# -*- coding: utf-8 -*-
"""
Plot SCI summary comparison figures (1.5D vs 2D), one variable per figure.

Reads:
  output/Plot/Fig6/SCI/SCI_Database_harmonization.xlsx
  - 1.5D_summary / 2D_summary
  - 1.5D_summary_amount / 2D_summary_amount

Outputs:
  PNG + SVG in the same SCI folder.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from config_paths import get_results_base

FIG_DIR = Path(get_results_base()) / "Plot" / "Fig6" / "SCI"
INPUT_NAME = "SCI_Database_harmonization.xlsx"
RAW_INPUT_NAME = "SCI_Database.xlsx"

SUMMARY_SHEET_15 = "1.5D_summary"
SUMMARY_SHEET_2D = "2D_summary"
AMOUNT_SHEET_15 = "1.5D_summary_amount"
AMOUNT_SHEET_2D = "2D_summary_amount"
BASE_SHEET_15 = "1.5D_harmonized"
BASE_SHEET_2D = "2D_harmonized"

SUMMARY_PLOT_VARS = [
    "Yield|Cropland|Oil Crops",
    "Carbon Removal|Land Use",
    "Agricultural Demand",
]

COMBINED_SUMMARY_VARS = [
    "Population",
    "Per capita Ag production",
    "Emission intensity of Ag production",
    "Land-use intensity of Ag production",
    "Emission intensity of land use",
    "Emissions|CO2eq|AFOLU",
]

AMOUNT_PLOT_VARS = [
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
    "Yield|Cropland|Cereals",
    "Land Cover|Forest_share",
    "Land Cover|Pasture_share",
    "Land Cover|Cropland_share",
    "EnergyCropsCroplandShare",
    "Primary Energy|Biomass",
    "risk_hunger_ratio",
    "food_crop_demand_ratio",
    "agricultural_bioenergy_crop_demand_ratio",
    "Carbon Removal|Land Use",
]

SCENARIO_STYLE = {
    "1.5D": {"color": "#1f77b4"},
    "2D": {"color": "#d62728"},
}
XTICKS = [2010, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
FIGURE_WIDTH = 4.8
FIGURE_HEIGHT = 3.5
COMBINED_WIDTH = 10.8
COMBINED_HEIGHT = 6.0

COMBINED_COLOR_MAP = {
    "Population": "#ff7f0e",
    "Per capita Ag production": "#ef3b53",
    "Emission intensity of Ag production": "#2b61ad",
    "Land-use intensity of Ag production": "#6a51a3",
    "Emission intensity of land use": "#3db7c7",
    "Emissions|CO2eq|AFOLU": "#9c5e0b",
}

TITLE_MAP = {
    "Emissions|CO2eq|AFOLU": "AFOLU CO2eq emission",
    "Emissions|CO2eq|AFOLU|Agriculture": "AFOLU CO2eq emission-Agriculture",
    "Emissions|CO2eq|AFOLU|Land": "AFOLU CO2eq emission-Land",
    "Emissions|CH4|AFOLU": "AFOLU CH4 emission",
    "Emissions|N2O|AFOLU": "AFOLU N2O emission",
    "Emissions|CO2|AFOLU": "AFOLU CO2 emission",
    "Emission intensity of Ag production": "Emission intensity of Ag production",
    "Emission intensity of land use": "Emission intensity of land use",
    "Land-use intensity of Ag production": "Land-use intensity of Ag production",
    "Per capita Ag production": "Per capita Ag production",
    "Yield|Cropland|Cereals": "Cereal yield rate",
    "Land Cover|Forest_share": "Share of forest area",
    "Land Cover|Pasture_share": "Share of pasture area",
    "Land Cover|Cropland_share": "Share of cropland area",
    "EnergyCropsCroplandShare": "Energy-crop share of cropland",
    "Primary Energy|Biomass": "Primary Energy|Biomass",
    "risk_hunger_ratio": "risk_hunger_ratio",
    "food_crop_demand_ratio": "food_crop_demand_ratio",
    "agricultural_bioenergy_crop_demand_ratio": "agricultural_bioenergy_crop_demand_ratio",
    "Carbon Removal|Land Use": "Carbon Removal|Land Use",
    "Yield|Cropland|Oil Crops": "Yield|Cropland|Oil Crops",
    "Agricultural Demand": "Agricultural Demand",
}


def _year_cols(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if str(c).startswith("Y") and str(c)[1:].isdigit()]
    return sorted(cols, key=lambda x: int(str(x)[1:]))


def _read_sheet(path: Path, sheet: str) -> Tuple[pd.DataFrame, List[str]]:
    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    if "Variable" not in df.columns or "Stat" not in df.columns:
        raise ValueError(f"Sheet {sheet} must include columns: Variable, Stat")
    year_cols = _year_cols(df)
    if not year_cols:
        raise ValueError(f"No year columns found in sheet: {sheet}")
    return df, year_cols


def _read_base_sheet(path: Path, sheet: str) -> Tuple[pd.DataFrame, List[str]]:
    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    if "Variable" not in df.columns:
        raise ValueError(f"Sheet {sheet} must include column: Variable")
    year_cols = _year_cols(df)
    if not year_cols:
        raise ValueError(f"No year columns found in sheet: {sheet}")
    return df, year_cols


def _ensure_amount_fallback_var(amount_df: pd.DataFrame, base_df: pd.DataFrame, var: str) -> pd.DataFrame:
    if "Variable" not in amount_df.columns or "Variable" not in base_df.columns:
        return amount_df
    if amount_df["Variable"].astype(str).eq(var).any():
        return amount_df

    work = base_df.copy()
    work.columns = [str(c).strip() for c in work.columns]
    year_cols = _year_cols(work)
    if not year_cols:
        return amount_df

    if var == "EnergyCropsCroplandShare":
        crop = work[work["Variable"].astype(str) == "Land Cover|Cropland"].copy()
        energy = work[work["Variable"].astype(str) == "Land Cover|Cropland|Energy Crops"].copy()
        key_cols = [c for c in ["Model", "Scenario", "Model#Scenario", "Scenario_map", "Region"] if c in work.columns]
        if not key_cols:
            return amount_df
        if crop.empty or energy.empty:
            return amount_df

        crop = crop[key_cols + ["Unit"] + year_cols].copy()
        energy = energy[key_cols + ["Unit"] + year_cols].copy()
        merged = crop.merge(energy, on=key_cols, how="inner", suffixes=("_crop", "_energy"))
        if merged.empty:
            return amount_df

        vals_crop = merged[[f"{c}_crop" for c in year_cols]].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
        vals_energy = merged[[f"{c}_energy" for c in year_cols]].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
        out = np.full_like(vals_energy, np.nan, dtype=float)
        mask = np.isfinite(vals_crop) & (np.abs(vals_crop) > 1e-12)
        out[mask] = vals_energy[mask] / vals_crop[mask]
        share_rows = merged[key_cols].copy()
        share_rows["Variable"] = var
        share_rows["Unit"] = "share"
        for idx, col in enumerate(year_cols):
            share_rows[col] = out[:, idx]
        work = pd.concat([work, share_rows], ignore_index=True)

    sub = work[work["Variable"].astype(str) == var].copy()
    if sub.empty:
        return amount_df

    unit = ""
    if "Unit" in sub.columns:
        unit_vals = sub["Unit"].dropna().astype(str)
        unit = unit_vals.iloc[0] if not unit_vals.empty else ""

    vals = sub[year_cols].apply(pd.to_numeric, errors="coerce")
    rows = []
    for stat, arr in (
        ("average", vals.mean(axis=0, skipna=True).to_numpy(dtype=float)),
        ("maxbound", vals.max(axis=0, skipna=True).to_numpy(dtype=float)),
        ("minbound", vals.min(axis=0, skipna=True).to_numpy(dtype=float)),
    ):
        row = {"Variable": var, "Unit": unit, "Stat": stat}
        for idx, col in enumerate(year_cols):
            row[col] = float(arr[idx]) if idx < len(arr) else np.nan
        rows.append(row)
    return pd.concat([amount_df, pd.DataFrame(rows)], ignore_index=True)


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


def _to_share_percent(arr: Optional[np.ndarray]) -> Optional[np.ndarray]:
    if arr is None:
        return None
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return arr
    if np.nanmax(finite) > 1.5:
        return arr
    return arr * 100.0


def _is_emissions_co2_or_co2eq(var: str) -> bool:
    if not var.startswith("Emissions|"):
        return False
    return ("CO2eq" in var) or ("|CO2|" in var) or var.endswith("|CO2")


def _is_emissions_n2o(var: str) -> bool:
    if not var.startswith("Emissions|"):
        return False
    return ("|N2O|" in var) or var.endswith("|N2O")


def _transform_series(
    source_kind: str,
    var: str,
    unit: str,
    *arrays: Optional[np.ndarray],
) -> Tuple[str, List[Optional[np.ndarray]]]:
    if source_kind in {"amount", "raw"} and unit.lower() == "share":
        return "Share (%)", [_to_share_percent(arr) for arr in arrays]
    if source_kind in {"amount", "raw"} and var == "Carbon Removal|Land Use":
        converted = [None if arr is None else arr / 1000.0 for arr in arrays]
        return "Gt CO2/yr", converted
    if source_kind in {"amount", "raw"} and _is_emissions_co2_or_co2eq(var):
        converted = [None if arr is None else arr / 1000.0 for arr in arrays]
        new_unit = unit.replace("Mt", "Gt") if unit else "Gt"
        return new_unit, converted
    if source_kind in {"amount", "raw"} and _is_emissions_n2o(var) and "kt" in unit.lower():
        converted = [None if arr is None else arr / 1000.0 for arr in arrays]
        new_unit = re.sub(r"(?i)kt", "Mt", unit) if unit else "Mt"
        return new_unit, converted
    if source_kind == "summary":
        return "Ratio (2010 = 1)", list(arrays)
    return unit, list(arrays)


def _format_tick_label(value: float, _pos: int) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return np.format_float_positional(float(value), trim="-")


def _collect_plotted_values(*arrays: Optional[np.ndarray]) -> np.ndarray:
    chunks: List[np.ndarray] = []
    for arr in arrays:
        if arr is None:
            continue
        vals = np.asarray(arr, dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size:
            chunks.append(vals)
    if not chunks:
        return np.array([], dtype=float)
    return np.concatenate(chunks)


def _adaptive_y_axis(
    arrays: List[np.ndarray],
    *,
    reference: Optional[float] = None,
    always_include_reference: bool = False,
) -> Optional[Tuple[float, float, np.ndarray]]:
    vals = _collect_plotted_values(*arrays)
    if vals.size == 0:
        return None

    ymin = float(np.min(vals))
    ymax = float(np.max(vals))
    if np.isclose(ymin, ymax):
        span = max(abs(ymin), 1.0) * 0.12
        ymin -= span
        ymax += span

    span = ymax - ymin
    # Keep the plotting area tight to the data; tick labels do not need to sit on the axis limits.
    pad = max(span * 0.035, max(abs(ymin), abs(ymax), 1.0) * 0.008)
    lower = ymin - pad
    upper = ymax + pad

    if reference is None:
        if ymin >= 0:
            lower = max(0.0, lower)
        if ymax <= 0:
            upper = min(0.0, upper)

    if reference is not None:
        if always_include_reference:
            lower = min(lower, reference)
            upper = max(upper, reference)
        else:
            if lower <= reference <= upper:
                pass
            else:
                gap = min(abs(reference - lower), abs(reference - upper))
                if gap <= span * 0.35:
                    lower = min(lower, reference)
                    upper = max(upper, reference)

    raw_step = max((upper - lower) / 5.0, 1e-12)
    step_scale = 10.0 ** np.floor(np.log10(raw_step))
    step_candidates = step_scale * np.array([0.5, 1.0, 2.0, 2.5, 5.0, 10.0], dtype=float)

    def _ticks_for_step(step: float) -> np.ndarray:
        tick_min = np.ceil(lower / step) * step
        tick_max = np.floor(upper / step) * step
        if tick_max < tick_min - step * 1e-9:
            return np.array([], dtype=float)
        ticks = np.arange(tick_min, tick_max + step * 0.5, step, dtype=float)
        ticks = np.round(ticks, 10)
        if reference is not None and lower <= reference <= upper:
            ref_tick = round(float(reference), 10)
            if not np.isclose(ticks, ref_tick).any():
                ticks = np.sort(np.append(ticks, ref_tick))
        return ticks

    best_ticks: Optional[np.ndarray] = None
    best_score: Optional[Tuple[float, float]] = None
    for step in step_candidates:
        ticks = _ticks_for_step(float(step))
        if ticks.size == 0:
            continue
        count = ticks.size
        score = (abs(count - 5), abs(float(step) - raw_step))
        if count < 3:
            score = (score[0] + 2.0, score[1])
        elif count > 7:
            score = (score[0] + 1.0, score[1])
        if best_score is None or score < best_score:
            best_score = score
            best_ticks = ticks

    if best_ticks is None or best_ticks.size < 2:
        return lower, upper, np.array([lower, upper], dtype=float)
    return float(lower), float(upper), best_ticks


def _has_sign_change(arrays: List[np.ndarray], reference: float = 0.0) -> bool:
    vals = _collect_plotted_values(*arrays)
    if vals.size == 0:
        return False
    return bool(np.min(vals) < reference < np.max(vals))


def _plot_variable(
    *,
    source_kind: str,
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
        print(f"[SKIP] {source_kind} {var}: missing in both sheets")
        return None

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))
    plotted_values: List[np.ndarray] = []

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

        # Historical segment should connect 2010 directly to 2020, skipping 2015.
        mask_hist = (years == 2010) | (years == 2020)
        mask_future_line = years >= 2020
        mask_future_fill = years >= 2020

        if mask_hist.any():
            ax.plot(years[mask_hist], mean_vals[mask_hist], color="#000000", linewidth=5.5)
            plotted_values.append(_collect_plotted_values(mean_vals[mask_hist]))

        if min_vals is not None and max_vals is not None and np.count_nonzero(mask_future_fill) >= 2:
            ax.fill_between(
                years[mask_future_fill],
                min_vals[mask_future_fill],
                max_vals[mask_future_fill],
                color=color,
                alpha=0.20,
                linewidth=0,
            )
            plotted_values.append(_collect_plotted_values(min_vals[mask_future_fill], max_vals[mask_future_fill]))

        if mask_future_line.any():
            ax.plot(years[mask_future_line], mean_vals[mask_future_line], color=color, linewidth=5.5, label=label)
            plotted_values.append(_collect_plotted_values(mean_vals[mask_future_line]))
        elif mask_hist.any():
            ax.plot(years[mask_hist], mean_vals[mask_hist], color="#000000", linewidth=5.5, label=label)
            plotted_values.append(_collect_plotted_values(mean_vals[mask_hist]))

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

    draw_zero_line = _has_sign_change(plotted_values, reference=0.0)
    if draw_zero_line:
        ax.axhline(0, color="#333333", linewidth=1.6, linestyle=(0, (5, 5)))
    y_axis = _adaptive_y_axis(
        plotted_values,
        reference=0.0 if draw_zero_line else None,
        always_include_reference=False,
    )
    if y_axis is not None:
        ymin, ymax, yticks = y_axis
        ax.set_ylim((ymin, ymax))
        ax.set_yticks(yticks)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_tick_label))
    ax.set_ylabel(unit if unit else "Value", fontsize=12.5, fontweight="bold")
    ax.set_xlabel("")
    ax.set_xlim(xlim)
    ax.set_xticks(XTICKS)
    ax.margins(x=0.01)
    ax.tick_params(axis="x", labelrotation=45)
    ax.tick_params(axis="both", which="both", labelsize=11.5, width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)
    ax.legend(loc="best", frameon=False, fontsize=10)

    safe_var = _safe_filename(var)
    png_path = FIG_DIR / f"Figure6_SCI_{source_kind}_{safe_var}.png"
    svg_path = FIG_DIR / f"Figure6_SCI_{source_kind}_{safe_var}.svg"
    fig.tight_layout()
    fig.savefig(png_path, dpi=700)
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")
    return png_path, svg_path


def _plot_from_sheet_pair(
    *,
    source_kind: str,
    df_15: pd.DataFrame,
    year_cols_15: List[str],
    df_2d: pd.DataFrame,
    year_cols_2d: List[str],
    plot_vars: List[str],
) -> None:
    years_15 = np.array([int(c[1:]) for c in year_cols_15], dtype=int)
    years_2d = np.array([int(c[1:]) for c in year_cols_2d], dtype=int)
    all_years = np.concatenate([years_15, years_2d])
    xlim = (int(np.min(all_years)), int(np.max(all_years)))

    for var in plot_vars:
        mean_15 = _series_for(df_15, var, "average", year_cols_15)
        min_15 = _series_for(df_15, var, "minbound", year_cols_15)
        max_15 = _series_for(df_15, var, "maxbound", year_cols_15)

        mean_2d = _series_for(df_2d, var, "average", year_cols_2d)
        min_2d = _series_for(df_2d, var, "minbound", year_cols_2d)
        max_2d = _series_for(df_2d, var, "maxbound", year_cols_2d)

        unit = _unit_for(df_15, var) or _unit_for(df_2d, var)
        unit, converted = _transform_series(
            source_kind,
            var,
            unit,
            mean_15,
            min_15,
            max_15,
            mean_2d,
            min_2d,
            max_2d,
        )
        mean_15, min_15, max_15, mean_2d, min_2d, max_2d = converted

        _plot_variable(
            source_kind=source_kind,
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


def _scenario_plot_arrays(
    years: np.ndarray,
    mean_vals: Optional[np.ndarray],
    min_vals: Optional[np.ndarray],
    max_vals: Optional[np.ndarray],
) -> List[np.ndarray]:
    if mean_vals is None:
        return []

    arrays: List[np.ndarray] = []
    mask_hist = (years == 2010) | (years == 2020)
    mask_future_line = years >= 2020
    mask_future_fill = years >= 2020

    if mask_hist.any():
        arrays.append(_collect_plotted_values(mean_vals[mask_hist]))
    if min_vals is not None and max_vals is not None and np.count_nonzero(mask_future_fill) >= 2:
        arrays.append(_collect_plotted_values(min_vals[mask_future_fill], max_vals[mask_future_fill]))
    if mask_future_line.any():
        arrays.append(_collect_plotted_values(mean_vals[mask_future_line]))
    elif mask_hist.any():
        arrays.append(_collect_plotted_values(mean_vals[mask_hist]))
    return arrays


def _load_prepare_module():
    script_path = Path(__file__).with_name("SP1_6_Figure_SCI_scenario_prepare.py")
    spec = importlib.util.spec_from_file_location("sci_prepare_module", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load prepare module: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_raw_amount_summaries() -> Tuple[pd.DataFrame, List[str], pd.DataFrame, List[str]]:
    prepare_module = _load_prepare_module()
    raw_path = FIG_DIR / RAW_INPUT_NAME
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing file: {raw_path}")

    raw_15 = pd.read_excel(raw_path, sheet_name="1.5D", engine="openpyxl")
    raw_2d = pd.read_excel(raw_path, sheet_name="2D", engine="openpyxl")
    raw_15 = prepare_module._add_derived_rows(raw_15)
    raw_2d = prepare_module._add_derived_rows(raw_2d)
    summary_15 = prepare_module._build_summary_amount(raw_15, "1.5D")
    summary_2d = prepare_module._build_summary_amount(raw_2d, "2D")
    return summary_15, _year_cols(summary_15), summary_2d, _year_cols(summary_2d)


def _plot_raw_vs_harmonized_compare(
    *,
    var: str,
    raw_df_15: pd.DataFrame,
    raw_year_cols_15: List[str],
    raw_df_2d: pd.DataFrame,
    raw_year_cols_2d: List[str],
    harm_df_15: pd.DataFrame,
    harm_year_cols_15: List[str],
    harm_df_2d: pd.DataFrame,
    harm_year_cols_2d: List[str],
) -> Optional[Tuple[Path, Path]]:
    raw_years_15 = np.array([int(c[1:]) for c in raw_year_cols_15], dtype=int)
    raw_years_2d = np.array([int(c[1:]) for c in raw_year_cols_2d], dtype=int)
    harm_years_15 = np.array([int(c[1:]) for c in harm_year_cols_15], dtype=int)
    harm_years_2d = np.array([int(c[1:]) for c in harm_year_cols_2d], dtype=int)

    raw_mean_15 = _series_for(raw_df_15, var, "average", raw_year_cols_15)
    raw_min_15 = _series_for(raw_df_15, var, "minbound", raw_year_cols_15)
    raw_max_15 = _series_for(raw_df_15, var, "maxbound", raw_year_cols_15)
    raw_mean_2d = _series_for(raw_df_2d, var, "average", raw_year_cols_2d)
    raw_min_2d = _series_for(raw_df_2d, var, "minbound", raw_year_cols_2d)
    raw_max_2d = _series_for(raw_df_2d, var, "maxbound", raw_year_cols_2d)
    harm_mean_15 = _series_for(harm_df_15, var, "average", harm_year_cols_15)
    harm_min_15 = _series_for(harm_df_15, var, "minbound", harm_year_cols_15)
    harm_max_15 = _series_for(harm_df_15, var, "maxbound", harm_year_cols_15)
    harm_mean_2d = _series_for(harm_df_2d, var, "average", harm_year_cols_2d)
    harm_min_2d = _series_for(harm_df_2d, var, "minbound", harm_year_cols_2d)
    harm_max_2d = _series_for(harm_df_2d, var, "maxbound", harm_year_cols_2d)

    unit = _unit_for(raw_df_15, var) or _unit_for(raw_df_2d, var) or _unit_for(harm_df_15, var) or _unit_for(harm_df_2d, var)
    raw_unit, raw_converted = _transform_series(
        "raw",
        var,
        unit,
        raw_mean_15,
        raw_min_15,
        raw_max_15,
        raw_mean_2d,
        raw_min_2d,
        raw_max_2d,
    )
    harm_unit, harm_converted = _transform_series(
        "amount",
        var,
        unit,
        harm_mean_15,
        harm_min_15,
        harm_max_15,
        harm_mean_2d,
        harm_min_2d,
        harm_max_2d,
    )
    raw_mean_15, raw_min_15, raw_max_15, raw_mean_2d, raw_min_2d, raw_max_2d = raw_converted
    harm_mean_15, harm_min_15, harm_max_15, harm_mean_2d, harm_min_2d, harm_max_2d = harm_converted
    final_unit = raw_unit or harm_unit or unit

    common_arrays = (
        _scenario_plot_arrays(raw_years_15, raw_mean_15, raw_min_15, raw_max_15)
        + _scenario_plot_arrays(raw_years_2d, raw_mean_2d, raw_min_2d, raw_max_2d)
        + _scenario_plot_arrays(harm_years_15, harm_mean_15, harm_min_15, harm_max_15)
        + _scenario_plot_arrays(harm_years_2d, harm_mean_2d, harm_min_2d, harm_max_2d)
    )
    draw_zero_line = _has_sign_change(common_arrays, reference=0.0)
    common_y_axis = _adaptive_y_axis(
        common_arrays,
        reference=0.0 if draw_zero_line else None,
        always_include_reference=False,
    )

    fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.8), sharey=True)

    def _draw_panel(
        ax: plt.Axes,
        title: str,
        years_15: np.ndarray,
        years_2d: np.ndarray,
        mean_15: Optional[np.ndarray],
        min_15: Optional[np.ndarray],
        max_15: Optional[np.ndarray],
        mean_2d: Optional[np.ndarray],
        min_2d: Optional[np.ndarray],
        max_2d: Optional[np.ndarray],
        *,
        show_ylabel: bool,
    ) -> None:
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

            mask_hist = (years == 2010) | (years == 2020)
            mask_future_line = years >= 2020
            mask_future_fill = years >= 2020

            if mask_hist.any():
                ax.plot(years[mask_hist], mean_vals[mask_hist], color="#000000", linewidth=4.8)
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
                ax.plot(years[mask_future_line], mean_vals[mask_future_line], color=color, linewidth=4.8, label=label)
            elif mask_hist.any():
                ax.plot(years[mask_hist], mean_vals[mask_hist], color="#000000", linewidth=4.8, label=label)

        _plot_scenario(years_15, mean_15, min_15, max_15, SCENARIO_STYLE["1.5D"]["color"], "1.5D average")
        _plot_scenario(years_2d, mean_2d, min_2d, max_2d, SCENARIO_STYLE["2D"]["color"], "2D average")

        if draw_zero_line:
            ax.axhline(0, color="#333333", linewidth=1.4, linestyle=(0, (5, 5)))
        if common_y_axis is not None:
            ymin, ymax, yticks = common_y_axis
            ax.set_ylim((ymin, ymax))
            ax.set_yticks(yticks)
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_tick_label))
        ax.set_ylabel(final_unit if show_ylabel else "", fontsize=11.0, fontweight="bold")
        ax.set_xlim((2010, 2100))
        ax.set_xticks(XTICKS)
        ax.margins(x=0.01)
        ax.tick_params(axis="x", labelrotation=45)
        ax.tick_params(axis="both", which="both", labelsize=10.0, width=1.8, length=7)
        for spine in ax.spines.values():
            spine.set_linewidth(1.8)
        ax.legend(loc="best", frameon=False, fontsize=9.0)

    _draw_panel(
        axes[0],
        f"{TITLE_MAP.get(var, var)} (raw)",
        raw_years_15,
        raw_years_2d,
        raw_mean_15,
        raw_min_15,
        raw_max_15,
        raw_mean_2d,
        raw_min_2d,
        raw_max_2d,
        show_ylabel=True,
    )
    _draw_panel(
        axes[1],
        f"{TITLE_MAP.get(var, var)} (harmonized)",
        harm_years_15,
        harm_years_2d,
        harm_mean_15,
        harm_min_15,
        harm_max_15,
        harm_mean_2d,
        harm_min_2d,
        harm_max_2d,
        show_ylabel=False,
    )

    safe_var = _safe_filename(var)
    png_path = FIG_DIR / f"Figure6_SCI_compare_raw_vs_harmonized_{safe_var}.png"
    svg_path = FIG_DIR / f"Figure6_SCI_compare_raw_vs_harmonized_{safe_var}.svg"
    fig.tight_layout()
    fig.savefig(png_path, dpi=700)
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")
    return png_path, svg_path


def _value_at_year(years: np.ndarray, values: Optional[np.ndarray], year: int) -> Optional[float]:
    if values is None:
        return None
    idx = np.where(years == year)[0]
    if idx.size == 0:
        return None
    val = values[int(idx[0])]
    return float(val) if np.isfinite(val) else None


def _plot_combined_summary_main(
    df_15: pd.DataFrame,
    year_cols_15: List[str],
    df_2d: pd.DataFrame,
    year_cols_2d: List[str],
) -> None:
    years_15 = np.array([int(c[1:]) for c in year_cols_15], dtype=int)
    years_2d = np.array([int(c[1:]) for c in year_cols_2d], dtype=int)

    fig, ax = plt.subplots(figsize=(COMBINED_WIDTH, COMBINED_HEIGHT))
    series_cache: Dict[str, Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]] = {}
    plotted_values: List[np.ndarray] = []

    for var in COMBINED_SUMMARY_VARS:
        mean_15 = _series_for(df_15, var, "average", year_cols_15)
        mean_2d = _series_for(df_2d, var, "average", year_cols_2d)
        if mean_15 is None and mean_2d is None:
            continue
        color = COMBINED_COLOR_MAP.get(var, "#333333")
        series_cache[var] = (years_15, mean_15, mean_2d)

        mask_hist_15 = (years_15 == 2010) | (years_15 == 2020)
        mask_future_15 = years_15 >= 2020
        mask_hist_2d = (years_2d == 2010) | (years_2d == 2020)
        mask_future_2d = years_2d >= 2020

        if mean_15 is not None:
            if mask_hist_15.any():
                ax.plot(
                    years_15[mask_hist_15],
                    mean_15[mask_hist_15],
                    color=color,
                    linewidth=6.0,
                    linestyle="-",
                    alpha=0.72,
                )
                plotted_values.append(_collect_plotted_values(mean_15[mask_hist_15]))
            if mask_future_15.any():
                ax.plot(
                    years_15[mask_future_15],
                    mean_15[mask_future_15],
                    color=color,
                    linewidth=6.0,
                    linestyle="-",
                    alpha=0.72,
                )
                plotted_values.append(_collect_plotted_values(mean_15[mask_future_15]))
        if mean_2d is not None:
            if mask_hist_2d.any():
                ax.plot(
                    years_2d[mask_hist_2d],
                    mean_2d[mask_hist_2d],
                    color=color,
                    linewidth=7.2,
                    linestyle=(0, (6, 3)),
                    alpha=0.98,
                )
                plotted_values.append(_collect_plotted_values(mean_2d[mask_hist_2d]))
            if mask_future_2d.any():
                ax.plot(
                    years_2d[mask_future_2d],
                    mean_2d[mask_future_2d],
                    color=color,
                    linewidth=7.2,
                    linestyle=(0, (6, 3)),
                    alpha=0.98,
                )
                plotted_values.append(_collect_plotted_values(mean_2d[mask_future_2d]))

    ax.axhline(1.0, color="#444444", linewidth=2.0, linestyle=(0, (5, 4)))
    ax.set_ylabel("Ratio (2010 = 1)", fontsize=16, fontweight="bold")
    ax.set_xlabel("Year", fontsize=18, fontweight="bold", labelpad=10)
    ax.set_xlim((2010, 2100))
    ax.set_xticks(XTICKS)
    ax.tick_params(axis="both", which="both", labelsize=13, width=2.2, length=12)
    for spine in ax.spines.values():
        spine.set_linewidth(2.2)

    scenario_handles = [
        plt.Line2D([0], [0], color="#222222", linewidth=5.0, linestyle="-", label="1.5Deg scenarios (mean)"),
        plt.Line2D([0], [0], color="#222222", linewidth=5.0, linestyle=(0, (6, 3)), label="2 Deg scenarios (mean)"),
    ]
    ax.legend(handles=scenario_handles, loc="upper left", frameon=False, fontsize=13)

    annotations = {
        "Per capita Ag production": (2028, 0.06, 20),
        "Population": (2084, 0.10, 0),
        "Emission intensity of Ag production": (2045, 0.10, 0),
        "Land-use intensity of Ag production": (2076, 0.07, 0),
        "Emission intensity of land use": (2022, -0.22, -45),
        "Emissions|CO2eq|AFOLU": (2070, -0.15, 0),
    }
    annotation_points: List[Tuple[str, int, float, int]] = []
    for var, (target_year, dy, rotation) in annotations.items():
        cached = series_cache.get(var)
        if cached is None:
            continue
        years, mean_15, _ = cached
        y = _value_at_year(years, mean_15, target_year)
        if y is None:
            continue
        annotation_points.append((var, target_year, y + dy, rotation))

    y_axis = _adaptive_y_axis(
        plotted_values + [np.array([point[2]], dtype=float) for point in annotation_points],
        reference=1.0,
        always_include_reference=True,
    )
    if y_axis is not None:
        ymin, ymax, yticks = y_axis
        ax.set_ylim((ymin, ymax))
        ax.set_yticks(yticks)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_tick_label))

    for var, target_year, y_pos, rotation in annotation_points:
        ax.text(
            target_year,
            y_pos,
            TITLE_MAP.get(var, var),
            color=COMBINED_COLOR_MAP.get(var, "#333333"),
            fontsize=15,
            fontweight="bold",
            rotation=rotation,
        )

    ax.text(2012, -0.48, "A. SCI attribution", fontsize=16, fontweight="bold", color="#111111")

    fig.tight_layout()
    png_path = FIG_DIR / "Figure6_SCI_summary_main_combined.png"
    svg_path = FIG_DIR / "Figure6_SCI_summary_main_combined.svg"
    fig.savefig(png_path, dpi=800)
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 11

    input_path = FIG_DIR / INPUT_NAME
    if not input_path.exists():
        raise FileNotFoundError(f"Missing file: {input_path}")

    summary_15, year_cols_summary_15 = _read_sheet(input_path, SUMMARY_SHEET_15)
    summary_2d, year_cols_summary_2d = _read_sheet(input_path, SUMMARY_SHEET_2D)
    amount_15, year_cols_amount_15 = _read_sheet(input_path, AMOUNT_SHEET_15)
    amount_2d, year_cols_amount_2d = _read_sheet(input_path, AMOUNT_SHEET_2D)
    base_15, _ = _read_base_sheet(input_path, BASE_SHEET_15)
    base_2d, _ = _read_base_sheet(input_path, BASE_SHEET_2D)

    for var in AMOUNT_PLOT_VARS:
        amount_15 = _ensure_amount_fallback_var(amount_15, base_15, var)
        amount_2d = _ensure_amount_fallback_var(amount_2d, base_2d, var)

    _plot_from_sheet_pair(
        source_kind="summary",
        df_15=summary_15,
        year_cols_15=year_cols_summary_15,
        df_2d=summary_2d,
        year_cols_2d=year_cols_summary_2d,
        plot_vars=SUMMARY_PLOT_VARS,
    )
    _plot_from_sheet_pair(
        source_kind="amount",
        df_15=amount_15,
        year_cols_15=year_cols_amount_15,
        df_2d=amount_2d,
        year_cols_2d=year_cols_amount_2d,
        plot_vars=AMOUNT_PLOT_VARS,
    )

    raw_compare_vars = [
        "Emissions|CO2eq|AFOLU",
        "Emissions|CO2eq|AFOLU|Agriculture",
        "Emissions|CO2eq|AFOLU|Land",
    ]
    raw_amount_15, raw_year_cols_15, raw_amount_2d, raw_year_cols_2d = _build_raw_amount_summaries()
    _plot_from_sheet_pair(
        source_kind="raw",
        df_15=raw_amount_15,
        year_cols_15=raw_year_cols_15,
        df_2d=raw_amount_2d,
        year_cols_2d=raw_year_cols_2d,
        plot_vars=raw_compare_vars,
    )
    for var in raw_compare_vars:
        _plot_raw_vs_harmonized_compare(
            var=var,
            raw_df_15=raw_amount_15,
            raw_year_cols_15=raw_year_cols_15,
            raw_df_2d=raw_amount_2d,
            raw_year_cols_2d=raw_year_cols_2d,
            harm_df_15=amount_15,
            harm_year_cols_15=year_cols_amount_15,
            harm_df_2d=amount_2d,
            harm_year_cols_2d=year_cols_amount_2d,
        )
    _plot_combined_summary_main(
        summary_15,
        year_cols_summary_15,
        summary_2d,
        year_cols_summary_2d,
    )


if __name__ == "__main__":
    main()
