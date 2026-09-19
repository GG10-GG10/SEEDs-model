# -*- coding: utf-8 -*-
"""
Build Figure 5 quartile-distribution panels from merged MC full-variable outputs.

For yield, emission_factor, ruminate_intake, and luc_land_intensity, the script
ranks valid MC samples by the current merged metric value, splits them into
four equal-count quartiles, and plots the 2080 GHG probability distribution for
each quartile.

Outputs:
  - output/Plot/Fig5/Figure5_yield_quartile_effect_line_targetrange_v2.png/.svg
  - output/Plot/Fig5/Figure5_emission_factor_quartile_effect_line_targetrange_v2.png/.svg
  - output/Plot/Fig5/Figure5_ruminate_intake_quartile_effect_line_targetrange_v2.png/.svg
  - output/Plot/Fig5/Figure5_luc_land_intensity_quartile_effect_line_targetrange_v2.png/.svg
  - output/Plot/Fig5/panel_samples_quartile_v2.csv
  - output/Plot/Fig5/histogram_quartile_v2.csv
  - output/Plot/Fig5/quartile_summary_v2.csv
  - output/Plot/Fig5/yield_land_productivity_audit_v2.csv
  - output/Plot/Fig5/ruminant_human_diet_share_audit_v2.csv
  - output/Plot/Fig5/current_metrics_2020_v2.csv
  - output/Plot/Fig5/ef_production_intensity_audit_v2.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D

from config_paths import get_input_base, get_results_base, get_src_base


RESULTS_BASE = Path(get_results_base())
FIG5_DIR = RESULTS_BASE / "Plot" / "Fig5"
TARGETS_PATH = FIG5_DIR / "targets.csv"
MC_MERGED_DIR = RESULTS_BASE / "MC_Full_Variables" / "merged"
FAST_SUMMARY_PATH = MC_MERGED_DIR / "mc_success_fast_summary.csv"
PROCESS_CO2EQ_PATH = MC_MERGED_DIR / "mc_success_global_process_co2eq.csv"
WEIGHTED_ELEMENTS_PATH = MC_MERGED_DIR / "mc_success_weighted_elements.csv"
STATUS_PATH = MC_MERGED_DIR / "mc_sample_status.csv"
MC_DRAWS_PATH = MC_MERGED_DIR / "mc_draws_long.csv"
FINAL_FOOD_ENERGY_PATH = MC_MERGED_DIR / "mc_success_final_food_energy.csv"
LAND_BALANCE_PATH = MC_MERGED_DIR / "mc_success_crop_pasture_land_balance.csv"

YEAR = 2080
BASE_YEAR = 2020
BINS = 110  # 120
SMOOTH_SIGMA_BINS = 5.0
# DEFAULT_X_MIN = -3.0
# DEFAULT_X_MAX = 18.0
INVALID_TOTAL_CO2EQ_GT_VALUES = (1.264874,)

FIG_WIDTH = 7.2
FIG_HEIGHT = 5.5
FIG_DPI = 800
AXIS_LABEL_FONTSIZE = 13.5
AXIS_LABELPAD = 12
TICK_LABEL_FONTSIZE = 13
TICK_WIDTH = 1.8
TICK_LENGTH = 8
SPINE_LINEWIDTH = 1.8
PANEL_TITLE_FONTSIZE = 15
LEGEND_FONTSIZE = 10.5
TARGET_LABEL_FONTSIZE = 12
TARGET_LINEWIDTH = 1.5
DENSITY_LINEWIDTH = 5.8
DENSITY_LINE_JOINSTYLE = "round"
DENSITY_LINE_CAPSTYLE = "round"
MEAN_LINEWIDTH = 1.25
MEAN_LINE_ALPHA = 0.48

QUARTILE_KEYS = ["q1", "q2", "q3", "q4"]
QUARTILE_RANGES = {
    "q1": "0-25%",
    "q2": "25-50%",
    "q3": "50-75%",
    "q4": "75-100%",
}
PANEL_BASE_COLORS = {
    "yield": "#d37520",
    "emission_factor": "#4b9b7a",
    "ruminate_intake": "#8a1d41",
    "luc_land_intensity": "#574c94",
}
QUARTILE_SHADE_AMOUNTS = {
    "q1": -0.25,
    "q2": 0.00,
    "q3": 0.25,
    "q4": 0.45,
}
QUARTILE_ALPHAS = {
    "q1": 0.98,
    "q2": 0.92,
    "q3": 0.84,
    "q4": 0.76,
}
REVERSED_QUARTILE_STYLE_KEYS = {
    "q1": "q4",
    "q2": "q3",
    "q3": "q2",
    "q4": "q1",
}

LUC_LAND_INTENSITY_PROCESSES = (
    "De/Reforestation_crop",
    "De/Reforestation_pasture",
    "Forest",
    "Wood harvest",
    "Drained organic soils",
    "Peatlands fire",
    "Peatlands fires",
    "Peatlands_fire",
    "Savanna fire",
    "Savanna fires",
    "Savanna_fires",
)

PRODUCTION_EF_CROP_PROCESSES = (
    "Crop residues",
    "Burning crop residues",
    "Rice cultivation",
    "Synthetic fertilizers",
)
PRODUCTION_EF_LIVESTOCK_PROCESSES = (
    "Enteric fermentation",
    "Manure management",
    "Manure applied to soils",
    "Manure left on pasture",
)
PRODUCTION_EF_PROCESSES = (
    *PRODUCTION_EF_CROP_PROCESSES,
    *PRODUCTION_EF_LIVESTOCK_PROCESSES,
)

RUMINANT_NUTRITION_ITEMS = (
    "Mutton & Goat Meat-sheep",
    "Milk-buffalo",
    "Milk-cattle",
    "Bovine Meat-cattle",
    "Milk-goats",
    "Mutton & Goat Meat-goat",
    "Bovine Meat-buffalo",
    "Milk-camel",
    "Meat, Other-camels",
    "Meat, Other-other domestic camelids",
    "Milk-sheep",
)

TARGET_ORDER = ["1.5D", "2D", "Current", "RCP4.5"]
TARGET_COLORS = {
    "1.5D": "#2ca25f",
    "2D": "#2b8cbe",
    "Current": "#4d4d4d",
    "RCP4.5": "#f1a340",
}

CONFIG = {
    # X-axis GHG total emissions range in 2080 (Gt CO2eq/yr).
    # Samples outside this range are excluded before quartile grouping.
    # Set to None to keep all valid emissions and auto-scale the x-axis.
    "ghg_total_emissions_range_gt": (-5, 60),
    # Quartile ranking metric:
    # "ratio" -> rank by relative ratio. Yield labels show % change;
    # ruminant labels show intake-ratio % change.
    # "absolute" -> rank by variable absolute value. Yield uses matching
    # 2080 final-human-food kcal / 2080 crop+pasture ha in Mkcal/ha.
    # Other weighted elements use their panel-specific absolute metric.
    "quartile_rank_metric_mode": "absolute", # 'ratio','absolute'
    # Optional per-panel override. Valid panel keys:
    # yield, emission_factor, ruminate_intake, luc_land_intensity
    # Example:
    # {"yield": "absolute", "emission_factor": "absolute",
    # "ruminate_intake": "absolute", "luc_land_intensity": "absolute"}
    "quartile_rank_metric_mode_by_panel": {
        # Use absolute values for the variable quartile ranking.
        # EF absolute mode requires kg CO2eq/kcal intensity columns from S5_4_1.
        "yield": "absolute",
        "emission_factor": "absolute",
        "ruminate_intake": "absolute", 
        "luc_land_intensity": "absolute",
    },
    # Whole-food-system EF intensity baseline. Empty CSV overrides resolve from
    # the base-case input/output folders below.
    "ef_system_baseline_case": "BASE_nutrition5",
    "ef_system_baseline_emissions_csv": "",
    "ef_system_baseline_nutrition_csv": "",
    # Production EF denominator and crop/livestock commodity scope. Empty
    # overrides resolve to BASE_nutrition5/DS/production_summary.csv and
    # Code/src/dict_v3.xlsx.
    "ef_production_summary_csv": "",
    "ef_dictionary_xlsx": "",
    # Yield land-productivity numerator. Prefer a merged per-sample table with
    # scenario_id, sample_id, year, and final_food_kcal. The current merged MC
    # dataset predates that table, so an empty/default path triggers exact
    # reconstruction from its sampled Ruminate_CapXX diet profile and fixed
    # 2080 population vector.
    "yield_final_food_energy_csv": "",
    "yield_profile_xlsx": "",
    "yield_profile_sheet": "low_land_new",
    "yield_population_case": "BASE_nutrition5",
    "yield_population_csv": "",
    "quality_gate_enabled": True,
    "min_valid_success_count": 1000,
    "min_valid_success_fraction": 0.50,
    "min_quartile_samples": 100,
    "histogram_bins": BINS,
}

VALID_QUARTILE_RANK_METRIC_MODES = {"ratio", "absolute"}

PANEL_SPECS = {
    "yield": {
        "title": "B. Yield-rate quartiles",
        "kind": "yield_rate",
        "metric_label": "Yield change",
        "metric_unit": "%",
        "value_mode": "change_percent",
        "file_stem": "Figure5_yield_quartile_effect_line_targetrange_v2",
    },
    "emission_factor": {
        "title": "C. Production emission-factor quartiles",
        "kind": "emission_factor",
        "metric_label": "Production emission factor",
        "metric_unit": "%",
        "value_mode": "change_percent",
        "file_stem": "Figure5_emission_factor_quartile_effect_line_targetrange_v2",
    },
    "ruminate_intake": {
        "title": "D. Human-diet ruminant kcal-share quartiles",
        "kind": "ruminant_reduction",
        "metric_label": "Human-diet ruminant kcal share",
        "metric_unit": "%",
        "value_mode": "share_percent",
        "file_stem": "Figure5_ruminate_intake_quartile_effect_line_targetrange_v2",
    },
    "luc_land_intensity": {
        "title": "E. LUC emission intensity per crop + pasture + forest land",
        "kind": "luc_land_intensity",
        "metric_label": "LUC intensity",
        "metric_unit": "t CO2eq/ha/yr",
        "value_mode": "t_per_ha",
        "file_stem": "Figure5_luc_land_intensity_quartile_effect_line_targetrange_v2",
    },
}


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


def _shade_color(hex_color: str, amount: float) -> Tuple[float, float, float]:
    amount = min(max(float(amount), -1.0), 1.0)
    rgb = np.asarray(to_rgb(hex_color), dtype=float)
    if amount < 0:
        return tuple(rgb * (1.0 + amount))
    return tuple(rgb + (1.0 - rgb) * amount)


def _quartile_style(panel: str, key: str) -> Tuple[Tuple[float, float, float], float]:
    base_color = PANEL_BASE_COLORS.get(panel, "#777777")
    style_key = REVERSED_QUARTILE_STYLE_KEYS.get(key, key) if panel == "yield" else key
    color = _shade_color(base_color, QUARTILE_SHADE_AMOUNTS.get(style_key, 0.0))
    alpha = float(QUARTILE_ALPHAS.get(style_key, 0.86))
    return color, alpha


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _configured_ghg_total_emissions_range() -> Optional[Tuple[float, float]]:
    raw = CONFIG.get("ghg_total_emissions_range_gt")
    if raw is None or raw == "":
        return None
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(
            "CONFIG['ghg_total_emissions_range_gt'] must be None or a "
            "(min_gt, max_gt) pair."
        )
    x_min = float(raw[0])
    x_max = float(raw[1])
    if not np.isfinite(x_min) or not np.isfinite(x_max):
        raise ValueError("CONFIG['ghg_total_emissions_range_gt'] values must be finite.")
    if x_max <= x_min:
        raise ValueError("CONFIG['ghg_total_emissions_range_gt'] max must be greater than min.")
    return x_min, x_max


def _filter_emissions_to_configured_range(emissions_df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[Tuple[float, float]]]:
    x_range = _configured_ghg_total_emissions_range()
    if x_range is None:
        return emissions_df, None

    x_min, x_max = x_range
    values = pd.to_numeric(emissions_df["emissions_2080_gt"], errors="coerce")
    keep = values.between(x_min, x_max, inclusive="both")
    before = len(emissions_df)
    out = emissions_df.loc[keep].copy()
    print(
        f"[INFO] filtered MC emissions to configured GHG range "
        f"[{x_min:g}, {x_max:g}] Gt: {len(out)}/{before}"
    )
    if out.empty:
        raise RuntimeError(
            "No MC emissions remain after CONFIG['ghg_total_emissions_range_gt'] "
            f"filter [{x_min:g}, {x_max:g}] Gt."
        )
    return out, x_range


def _rank_metric_mode(panel: str) -> str:
    by_panel = CONFIG.get("quartile_rank_metric_mode_by_panel", {}) or {}
    mode = str(by_panel.get(panel, CONFIG.get("quartile_rank_metric_mode", "ratio")) or "ratio")
    mode = mode.strip().lower().replace("-", "_")
    aliases = {
        "relative": "ratio",
        "relative_ratio": "ratio",
        "change": "ratio",
        "abs": "absolute",
        "value": "absolute",
        "absolute_value": "absolute",
    }
    mode = aliases.get(mode, mode)
    if mode not in VALID_QUARTILE_RANK_METRIC_MODES:
        valid = ", ".join(sorted(VALID_QUARTILE_RANK_METRIC_MODES))
        raise ValueError(f"Invalid quartile rank metric mode for {panel}: {mode!r}. Valid: {valid}")
    if panel == "luc_land_intensity" and mode != "absolute":
        raise ValueError("luc_land_intensity only supports absolute quartile ranking.")
    return mode


def _active_panel_spec(panel: str) -> Dict[str, object]:
    spec = dict(PANEL_SPECS[panel])
    mode = _rank_metric_mode(panel)
    spec["rank_metric_mode"] = mode
    if panel == "yield" and mode == "absolute":
        spec["title"] = "B. Final-food land-productivity quartiles"
        spec["metric_label"] = "Final-food land productivity"
        spec["metric_unit"] = "Mkcal/ha"
        spec["value_mode"] = "absolute_unsigned"
    elif panel == "emission_factor" and mode == "absolute":
        spec["title"] = "C. Production emission-factor quartiles"
        spec["metric_label"] = "Production emission factor"
        spec["metric_unit"] = "g CO2e/kcal"
        spec["value_mode"] = "absolute_unsigned"
    elif panel == "ruminate_intake" and mode == "ratio":
        spec["title"] = "D. Ruminant-intake ratio quartiles"
        spec["metric_label"] = "Ruminant intake change"
        spec["metric_unit"] = "%"
        spec["value_mode"] = "change_percent"
    elif panel == "ruminate_intake" and mode == "absolute":
        spec["title"] = "D. Human-diet ruminant kcal-share quartiles"
        spec["metric_label"] = "Human-diet ruminant kcal share"
        spec["metric_unit"] = "%"
        spec["value_mode"] = "share_percent"
    return spec


def _sentinel_mask(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    bad_vals = [round(float(x), 6) for x in INVALID_TOTAL_CO2EQ_GT_VALUES]
    return vals.round(6).isin(bad_vals)


def _fmt_signed_pct(value: float) -> str:
    if not np.isfinite(value):
        return "NA"
    return f"{value:+.1f}%"


def _fmt_unsigned_pct(value: float) -> str:
    if not np.isfinite(value):
        return "NA"
    return f"{value:.2f}%"


def _format_metric(value: float, mode: str) -> str:
    if mode == "change_percent":
        return _fmt_signed_pct(value)
    if mode == "share_percent":
        return _fmt_unsigned_pct(value)
    if not np.isfinite(value):
        return "NA"
    if mode == "absolute_unsigned":
        return f"{value:.2f}"
    return f"{value:+.2f}"


def _format_metric_with_unit(value: float, spec: Dict[str, object]) -> str:
    text = _format_metric(value, str(spec.get("value_mode", "")))
    if str(spec.get("value_mode", "")) in {"change_percent", "share_percent"}:
        return text
    unit = str(spec.get("metric_unit", "") or "").strip()
    return f"{text} {unit}" if unit and text != "NA" else text


def _format_summary_metric(row: pd.Series, fallback_spec: Dict[str, object]) -> str:
    spec = dict(fallback_spec)
    for col in ("value_mode", "metric_unit"):
        if col in row.index and pd.notna(row[col]):
            spec[col] = row[col]
    return _format_metric_with_unit(float(row["metric_mean"]), spec)


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


def _first_existing_path(candidates: Sequence[Path], *, label: str) -> Path:
    for path in candidates:
        if path.exists():
            return path
    checked = "\n  - ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Missing {label}. Checked:\n  - {checked}")


def _resolve_ef_system_baseline_paths() -> Tuple[Path, Path]:
    base_case = str(CONFIG.get("ef_system_baseline_case", "BASE_nutrition5") or "BASE_nutrition5").strip()
    emissions_override = str(CONFIG.get("ef_system_baseline_emissions_csv", "") or "").strip()
    nutrition_override = str(CONFIG.get("ef_system_baseline_nutrition_csv", "") or "").strip()

    if emissions_override:
        emissions_candidates = [Path(emissions_override).expanduser()]
    else:
        emissions_name = "emissions_summary_By_Country_Process_Item.csv"
        emissions_candidates = [
            Path(get_input_base()) / "Emission" / base_case / "Emis" / emissions_name,
            RESULTS_BASE / base_case / "Emis" / emissions_name,
        ]

    if nutrition_override:
        nutrition_candidates = [Path(nutrition_override).expanduser()]
    else:
        nutrition_candidates = [
            RESULTS_BASE / base_case / "DS" / "nutrition_per_capita.csv",
        ]

    emissions_path = _first_existing_path(
        emissions_candidates,
        label=f"{BASE_YEAR} food-system baseline emissions CSV",
    )
    nutrition_path = _first_existing_path(
        nutrition_candidates,
        label=f"{BASE_YEAR} food-energy baseline CSV",
    )
    return emissions_path, nutrition_path


def _resolve_production_ef_paths() -> Tuple[Path, Path]:
    base_case = str(
        CONFIG.get("ef_system_baseline_case", "BASE_nutrition5")
        or "BASE_nutrition5"
    ).strip()
    production_override = str(
        CONFIG.get("ef_production_summary_csv", "") or ""
    ).strip()
    dictionary_override = str(CONFIG.get("ef_dictionary_xlsx", "") or "").strip()

    production_candidates = (
        [Path(production_override).expanduser()]
        if production_override
        else [RESULTS_BASE / base_case / "DS" / "production_summary.csv"]
    )
    dictionary_candidates = (
        [Path(dictionary_override).expanduser()]
        if dictionary_override
        else [Path(get_src_base()) / "dict_v3.xlsx"]
    )
    production_path = _first_existing_path(
        production_candidates,
        label=f"{BASE_YEAR} gross crop/livestock production CSV",
    )
    dictionary_path = _first_existing_path(
        dictionary_candidates,
        label="crop/livestock commodity energy dictionary",
    )
    return production_path, dictionary_path


def _load_gross_production_energy_2020(
    production_path: Path,
    dictionary_path: Path,
) -> Dict[str, object]:
    dictionary = pd.read_excel(
        dictionary_path,
        sheet_name="Emis_item",
        usecols=lambda c: str(c).strip()
        in {"Process", "Item_Emis", "kcal_per_100g"},
    )
    dictionary.columns = [str(c).strip() for c in dictionary.columns]
    required_dictionary = {"Process", "Item_Emis", "kcal_per_100g"}
    if not required_dictionary.issubset(dictionary.columns):
        missing = ", ".join(sorted(required_dictionary - set(dictionary.columns)))
        raise ValueError(f"Production EF dictionary missing columns {missing}: {dictionary_path}")
    dictionary["Process"] = dictionary["Process"].astype(str).str.strip()
    dictionary["Item_Emis"] = dictionary["Item_Emis"].astype(str).str.strip()
    dictionary["kcal_per_100g"] = pd.to_numeric(
        dictionary["kcal_per_100g"], errors="coerce"
    )
    scope = dictionary[
        dictionary["Process"].isin(PRODUCTION_EF_PROCESSES)
        & dictionary["Item_Emis"].ne("")
        & dictionary["kcal_per_100g"].notna()
    ].copy()
    if scope.empty:
        raise ValueError(
            f"No crop/livestock production commodities in dictionary: {dictionary_path}"
        )
    factor_spread = scope.groupby("Item_Emis")["kcal_per_100g"].agg(
        lambda values: float(values.max() - values.min())
    )
    inconsistent = factor_spread[factor_spread.gt(1e-12)]
    if not inconsistent.empty:
        raise ValueError(
            "Production commodities have inconsistent kcal_per_100g values: "
            + ", ".join(inconsistent.index.astype(str).tolist()[:10])
        )
    kcal_per_ton = (
        scope.groupby("Item_Emis", sort=False)["kcal_per_100g"].first() * 10000.0
    )

    production = pd.read_csv(
        production_path,
        usecols=lambda c: str(c).strip() in {"year", "commodity", "production_t"},
    )
    production.columns = [str(c).strip() for c in production.columns]
    required_production = {"year", "commodity", "production_t"}
    if not required_production.issubset(production.columns):
        missing = ", ".join(sorted(required_production - set(production.columns)))
        raise ValueError(f"Production summary missing columns {missing}: {production_path}")
    production["year"] = pd.to_numeric(production["year"], errors="coerce")
    production["production_t"] = pd.to_numeric(
        production["production_t"], errors="coerce"
    )
    production["commodity"] = production["commodity"].astype(str).str.strip()
    current = production[
        production["year"].eq(BASE_YEAR)
        & production["commodity"].isin(kcal_per_ton.index)
        & production["production_t"].notna()
        & production["production_t"].ge(0)
    ].copy()
    if current.empty:
        raise ValueError(
            f"No {BASE_YEAR} crop/livestock production rows in {production_path}"
        )
    current["kcal_per_ton"] = current["commodity"].map(kcal_per_ton)
    current["production_kcal"] = current["production_t"] * current["kcal_per_ton"]
    gross_production_kcal = float(current["production_kcal"].sum())
    if not np.isfinite(gross_production_kcal) or gross_production_kcal <= 0:
        raise ValueError(
            f"Non-positive {BASE_YEAR} gross crop/livestock production kcal: "
            f"{gross_production_kcal}"
        )
    return {
        "gross_production_kcal": gross_production_kcal,
        "production_rows": int(len(current)),
        "production_commodity_count": int(current["commodity"].nunique()),
        "production_scope_commodity_count": int(len(kcal_per_ton)),
        "production_path": str(production_path),
        "dictionary_path": str(dictionary_path),
    }


def _load_ef_system_baseline() -> Dict[str, object]:
    emissions_path, nutrition_path = _resolve_ef_system_baseline_paths()
    production_path, dictionary_path = _resolve_production_ef_paths()
    year_col = f"Y{BASE_YEAR}"

    emissions = pd.read_csv(
        emissions_path,
        usecols=lambda c: str(c).strip()
        in {"M49_Country_Code", "Process", "GHG", year_col},
        low_memory=False,
    )
    emissions.columns = [str(c).strip() for c in emissions.columns]
    required_emissions = {"M49_Country_Code", "Process", "GHG", year_col}
    if not required_emissions.issubset(emissions.columns):
        missing = ", ".join(sorted(required_emissions - set(emissions.columns)))
        raise ValueError(f"Baseline emissions CSV missing columns: {missing}. File: {emissions_path}")

    m49 = (
        emissions["M49_Country_Code"]
        .astype(str)
        .str.replace("'", "", regex=False)
        .str.strip()
        .str.zfill(3)
    )
    ghg = emissions["GHG"].astype(str).str.strip().str.upper()
    process = emissions["Process"].astype(str).str.strip()
    values_kt = pd.to_numeric(emissions[year_col], errors="coerce")
    co2eq_rows = ghg.eq("CO2EQ") & values_kt.notna()
    country_rows = co2eq_rows & m49.ne("000")
    selected_rows = country_rows if bool(country_rows.any()) else co2eq_rows & m49.eq("000")
    system_emissions_kt = float(values_kt.loc[selected_rows].sum())
    if not np.isfinite(system_emissions_kt) or system_emissions_kt <= 0:
        raise ValueError(
            f"No positive {BASE_YEAR} GHG=CO2eq total in baseline emissions CSV: {emissions_path}"
        )

    production_rows = selected_rows & process.isin(PRODUCTION_EF_PROCESSES)
    production_emissions_kt = float(values_kt.loc[production_rows].sum())
    if not np.isfinite(production_emissions_kt) or production_emissions_kt <= 0:
        raise ValueError(
            f"No positive {BASE_YEAR} crop/livestock production CO2e in {emissions_path}"
        )
    production_energy = _load_gross_production_energy_2020(
        production_path,
        dictionary_path,
    )

    nutrition = pd.read_csv(
        nutrition_path,
        usecols=lambda c: str(c).strip() in {"year", "energy_total_kcal"},
    )
    nutrition.columns = [str(c).strip() for c in nutrition.columns]
    required_nutrition = {"year", "energy_total_kcal"}
    if not required_nutrition.issubset(nutrition.columns):
        missing = ", ".join(sorted(required_nutrition - set(nutrition.columns)))
        raise ValueError(f"Baseline nutrition CSV missing columns: {missing}. File: {nutrition_path}")
    nutrition["year"] = pd.to_numeric(nutrition["year"], errors="coerce")
    food_kcal_rows = pd.to_numeric(
        nutrition.loc[nutrition["year"].eq(BASE_YEAR), "energy_total_kcal"],
        errors="coerce",
    ).dropna()
    food_kcal = float(food_kcal_rows.sum())
    if not np.isfinite(food_kcal) or food_kcal <= 0:
        raise ValueError(f"No positive {BASE_YEAR} food kcal in baseline nutrition CSV: {nutrition_path}")

    system_emissions_gt = system_emissions_kt * 1e-6
    system_emissions_kg = system_emissions_kt * 1e6
    baseline_intensity = system_emissions_kg * 1e3 / food_kcal
    production_emissions_gt = production_emissions_kt * 1e-6
    production_emissions_kg = production_emissions_kt * 1e6
    gross_production_kcal = float(production_energy["gross_production_kcal"])
    production_intensity = production_emissions_kg * 1e3 / gross_production_kcal
    result: Dict[str, object] = {
        "baseline_case": str(CONFIG.get("ef_system_baseline_case", "") or ""),
        "baseline_year": BASE_YEAR,
        "emissions_path": str(emissions_path),
        "nutrition_path": str(nutrition_path),
        "system_baseline_emissions_gt": system_emissions_gt,
        "system_baseline_emissions_kg": system_emissions_kg,
        "food_energy_kcal": food_kcal,
        "system_baseline_intensity_g_per_kcal": baseline_intensity,
        "production_baseline_emissions_gt": production_emissions_gt,
        "production_baseline_emissions_kg": production_emissions_kg,
        "gross_production_energy_2020_kcal": gross_production_kcal,
        "production_baseline_intensity_g_per_kcal": production_intensity,
        "production_processes": " | ".join(PRODUCTION_EF_PROCESSES),
        "production_emissions_rows": int(production_rows.sum()),
        "production_summary_path": str(production_path),
        "production_dictionary_path": str(dictionary_path),
        "production_rows": int(production_energy["production_rows"]),
        "production_commodity_count": int(
            production_energy["production_commodity_count"]
        ),
        "production_scope_commodity_count": int(
            production_energy["production_scope_commodity_count"]
        ),
        "emissions_rows": int(selected_rows.sum()),
        "nutrition_rows": int(len(food_kcal_rows)),
    }
    print(
        f"[INFO] {BASE_YEAR} whole-food-system reference for Yield/LUC: "
        f"emissions={system_emissions_gt:.6f} Gt CO2e, "
        f"food_energy={food_kcal / 1e15:.6f} Pkcal, "
        f"intensity={baseline_intensity:.6f} g CO2e/kcal"
    )
    print(
        f"[INFO] {BASE_YEAR} production EF baseline: "
        f"emissions={production_emissions_gt:.6f} Gt CO2e, "
        f"gross_production={gross_production_kcal / 1e15:.6f} Pkcal, "
        f"intensity={production_intensity:.6f} g CO2e/kcal"
    )
    print(f"[INFO] production emissions source: {emissions_path}")
    print(f"[INFO] gross production source: {production_path}")
    print(f"[INFO] production commodity dictionary: {dictionary_path}")
    return result


def _load_valid_success_keys() -> pd.DataFrame:
    if not STATUS_PATH.exists():
        if bool(CONFIG.get("quality_gate_enabled", True)):
            raise FileNotFoundError(f"Missing MC status file required for quality gate: {STATUS_PATH}")
        return pd.DataFrame(columns=["scenario_id", "sample_id"])

    status = pd.read_csv(STATUS_PATH)
    status.columns = [str(c).strip() for c in status.columns]
    if "scenario_id" not in status.columns or "sample_id" not in status.columns:
        if bool(CONFIG.get("quality_gate_enabled", True)):
            raise ValueError("mc_sample_status.csv missing scenario_id/sample_id required for quality gate.")
        return pd.DataFrame(columns=["scenario_id", "sample_id"])

    run_status = status.get("run_status", pd.Series("", index=status.index)).astype(str).str.strip().str.lower()
    run_ok = run_status.isin({"ok", "resumed"})
    model_code = pd.to_numeric(status.get("model_status_code", pd.Series(pd.NA, index=status.index)), errors="coerce")
    model_text = status.get("model_status_text", pd.Series("", index=status.index)).astype(str).str.strip().str.upper()
    has_model_status = bool(model_code.notna().any() or model_text.ne("").any())
    model_ok = model_code.eq(2) | model_text.eq("OPTIMAL")

    sentinel_ok = pd.Series(True, index=status.index)
    for col in ("afolu_emissions_gt_co2eq_yr", "total_co2eq_gt"):
        if col in status.columns:
            sentinel_ok = sentinel_ok & ~_sentinel_mask(status[col])

    mask = run_ok & (model_ok if has_model_status else True) & sentinel_ok
    keys = status.loc[mask, ["scenario_id", "sample_id"]].copy()
    keys["scenario_id"] = keys["scenario_id"].astype(str)
    keys["sample_id"] = pd.to_numeric(keys["sample_id"], errors="coerce").astype("Int64")
    keys = keys.dropna(subset=["sample_id"]).copy()
    keys["sample_id"] = keys["sample_id"].astype(int)
    keys = keys.drop_duplicates().reset_index(drop=True)
    total = int(len(status))
    valid = int(len(keys))
    valid_fraction = float(valid / total) if total else 0.0
    print(f"[INFO] valid OPTIMAL MC samples: {valid}/{total} ({valid_fraction:.1%})")
    if bool(CONFIG.get("quality_gate_enabled", True)):
        min_count = int(CONFIG.get("min_valid_success_count", 1000) or 0)
        min_fraction = float(CONFIG.get("min_valid_success_fraction", 0.50) or 0.0)
        issues: List[str] = []
        if valid < min_count:
            issues.append(f"valid_success_count={valid} < {min_count}")
        if valid_fraction < min_fraction:
            issues.append(f"valid_success_fraction={valid_fraction:.3f} < {min_fraction:.3f}")
        if issues:
            raise RuntimeError(
                "Figure5 MC quality gate failed: "
                + " | ".join(issues)
                + ". Current merged outputs are too success-conditioned for quartile plots. "
                "Rerun S5_4 after fixing model feasibility; disable CONFIG['quality_gate_enabled'] only for diagnostics."
            )
    return keys


def _load_mc_success_emissions() -> pd.DataFrame:
    if not FAST_SUMMARY_PATH.exists():
        raise FileNotFoundError(f"Missing merged fast summary: {FAST_SUMMARY_PATH}")

    df = pd.read_csv(FAST_SUMMARY_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    if "scenario_id" not in df.columns or "sample_id" not in df.columns:
        raise ValueError("mc_success_fast_summary.csv missing scenario_id/sample_id.")

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df = df[df["year"] == YEAR].copy()

    if "total_co2eq_gt" in df.columns:
        df["emissions_2080_gt"] = pd.to_numeric(df["total_co2eq_gt"], errors="coerce")
    elif "total_co2eq_kt" in df.columns:
        df["emissions_2080_gt"] = pd.to_numeric(df["total_co2eq_kt"], errors="coerce") * 1e-6
    else:
        raise ValueError("mc_success_fast_summary.csv missing total_co2eq_gt/kt column.")

    before_sentinel = len(df)
    df = df.loc[~_sentinel_mask(df["emissions_2080_gt"])].copy()
    if len(df) != before_sentinel:
        print(
            f"[INFO] dropped {before_sentinel - len(df)} MC emission rows with invalid "
            f"sentinel {INVALID_TOTAL_CO2EQ_GT_VALUES}"
        )

    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    out = (
        df.dropna(subset=["scenario_id", "sample_id", "emissions_2080_gt"])
        .groupby(["scenario_id", "sample_id"], as_index=False)["emissions_2080_gt"]
        .sum()
    )
    out["scenario_id"] = out["scenario_id"].astype(str)
    out["sample_id"] = out["sample_id"].astype(int)

    valid_keys = _load_valid_success_keys()
    if not valid_keys.empty:
        before = len(out)
        out = out.merge(valid_keys, on=["scenario_id", "sample_id"], how="inner")
        print(f"[INFO] filtered MC emissions to OPTIMAL success rows: {len(out)}/{before}")
    return out


def _load_weighted_elements() -> pd.DataFrame:
    if not WEIGHTED_ELEMENTS_PATH.exists():
        raise FileNotFoundError(f"Missing merged weighted elements: {WEIGHTED_ELEMENTS_PATH}")

    keep_cols = {
        "scenario_id",
        "sample_id",
        "kind",
        "item_selector",
        "process_selector",
        "ghg_selector",
        "mc_unit",
        "selected_pairs",
        "weight_kcal_total",
        "weighted_value_sample",
        "weighted_value_y2020",
        "weighted_value_draw",
        "weighted_ratio",
        "weighted_co2eq_intensity_y2020_kg_per_kcal",
        "weighted_co2eq_intensity_sample_kg_per_kcal",
        "co2eq_intensity_unit",
        "batch_count",
        "batch_tag",
    }
    df = pd.read_csv(WEIGHTED_ELEMENTS_PATH, usecols=lambda c: str(c).strip() in keep_cols)
    df.columns = [str(c).strip() for c in df.columns]
    if "scenario_id" not in df.columns or "sample_id" not in df.columns or "kind" not in df.columns:
        raise ValueError("mc_success_weighted_elements.csv missing scenario_id/sample_id/kind.")
    df["scenario_id"] = df["scenario_id"].astype(str)
    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    df["kind"] = df["kind"].astype(str).str.strip()
    return df.dropna(subset=["scenario_id", "sample_id", "kind"]).copy()


def _normalize_m49_code(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().replace("'", "")
    if not text:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(3) if text.isdigit() else text


def _resolve_yield_food_energy_paths() -> Tuple[Path, Path]:
    profile_override = str(CONFIG.get("yield_profile_xlsx", "") or "").strip()
    if profile_override:
        profile_path = Path(profile_override).expanduser()
    else:
        profile_path = (
            Path(get_input_base())
            / "Driver"
            / "Nutrition"
            / "Nutrition_profile_recalculated_fromD0_food_demand.xlsx"
        )

    population_override = str(CONFIG.get("yield_population_csv", "") or "").strip()
    if population_override:
        population_path = Path(population_override).expanduser()
    else:
        population_case = str(
            CONFIG.get("yield_population_case", "BASE_nutrition5") or "BASE_nutrition5"
        ).strip()
        population_path = RESULTS_BASE / population_case / "DS" / "nutrition_per_capita.csv"

    if not profile_path.exists():
        raise FileNotFoundError(f"Missing yield final-food nutrition profile: {profile_path}")
    if not population_path.exists():
        raise FileNotFoundError(f"Missing yield {YEAR} population CSV: {population_path}")
    return profile_path, population_path


def _load_yield_population(population_path: Path, *, year: int = YEAR) -> pd.Series:
    population = pd.read_csv(population_path)
    population.columns = [str(c).strip() for c in population.columns]
    if "year" not in population.columns or "population" not in population.columns:
        raise ValueError(
            f"Yield population CSV must contain year and population: {population_path}"
        )
    population["year"] = pd.to_numeric(population["year"], errors="coerce")
    population = population[population["year"].eq(int(year))].copy()
    if population.empty:
        raise ValueError(f"Yield population CSV has no {year} rows: {population_path}")

    codes = pd.Series("", index=population.index, dtype=object)
    if "M49_Country_Code" in population.columns:
        codes = population["M49_Country_Code"].map(_normalize_m49_code)
    if "country" in population.columns:
        fallback = population["country"].map(_normalize_m49_code)
        codes = codes.where(codes.astype(str).str.len().gt(0), fallback)
    population["m49_code"] = codes
    population["population"] = pd.to_numeric(population["population"], errors="coerce")
    population = population.dropna(subset=["population"])
    population = population[
        population["m49_code"].astype(str).str.len().gt(0)
        & population["population"].gt(0)
    ].copy()
    if population.empty:
        raise ValueError(f"No positive {year} country populations in {population_path}")
    out = population.groupby("m49_code", sort=False)["population"].sum()
    out.name = "population"
    return out


def _profile_final_food_kcal_by_cap(
    cap_pcts: Sequence[int],
    *,
    profile_path: Path,
    population_path: Path,
) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, str], Dict[str, float]]:
    cap_values = sorted({int(value) for value in cap_pcts})
    if not cap_values:
        raise ValueError("No ruminant-cap levels were supplied for final-food reconstruction.")
    wanted_cols = {
        "M49_Country_Code",
        "Area Code (M49)",
        "Item",
        "Element",
        f"Y{BASE_YEAR}",
    }
    for cap_pct in cap_values:
        wanted_cols.update({f"Ruminate_Cap{cap_pct}", f"Ruminate_Cap{cap_pct:02d}"})

    profile_sheet = str(CONFIG.get("yield_profile_sheet", "low_land_new") or "low_land_new")
    profile = pd.read_excel(
        profile_path,
        sheet_name=profile_sheet,
        usecols=lambda c: str(c).strip() in wanted_cols,
    )
    profile.columns = [str(c).strip() for c in profile.columns]
    if "Element" not in profile.columns:
        raise ValueError(f"Nutrition profile missing Element column: {profile_path}")
    if "Item" not in profile.columns:
        raise ValueError(f"Nutrition profile missing Item column: {profile_path}")
    m49_col = next(
        (col for col in ("M49_Country_Code", "Area Code (M49)") if col in profile.columns),
        None,
    )
    if m49_col is None:
        raise ValueError(f"Nutrition profile missing an M49 column: {profile_path}")

    energy = profile[
        profile["Element"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("food supply (kcal/capita/day)")
    ].copy()
    if energy.empty:
        raise ValueError(f"Nutrition profile has no food-energy rows: {profile_path}")
    energy["m49_code"] = energy[m49_col].map(_normalize_m49_code)
    energy = energy[energy["m49_code"].astype(str).str.len().gt(0)].copy()
    energy["is_ruminant_food"] = (
        energy["Item"].astype(str).str.strip().isin(RUMINANT_NUTRITION_ITEMS)
    )
    found_ruminant_items = set(
        energy.loc[energy["is_ruminant_food"], "Item"].astype(str).str.strip()
    )
    missing_ruminant_items = sorted(set(RUMINANT_NUTRITION_ITEMS) - found_ruminant_items)
    if missing_ruminant_items:
        raise ValueError(
            "Nutrition profile is missing ruminant food items: "
            + ", ".join(missing_ruminant_items)
        )

    cap_columns: Dict[int, str] = {}
    for cap_pct in cap_values:
        candidates = (f"Ruminate_Cap{cap_pct:02d}", f"Ruminate_Cap{cap_pct}")
        cap_col = next((candidate for candidate in candidates if candidate in energy.columns), None)
        if cap_col is None:
            raise ValueError(
                f"Nutrition profile is missing the sampled cap column for {cap_pct}%: {profile_path}"
            )
        cap_columns[cap_pct] = cap_col
        energy[cap_col] = pd.to_numeric(energy[cap_col], errors="coerce").fillna(0.0)

    population = _load_yield_population(population_path, year=YEAR)
    country_energy = energy.groupby("m49_code", sort=False)[list(cap_columns.values())].sum()
    country_ruminant_energy = energy[energy["is_ruminant_food"]].groupby(
        "m49_code", sort=False
    )[list(cap_columns.values())].sum()
    missing_population = country_energy.index.difference(population.index)
    if len(missing_population) > 0:
        preview = ", ".join(missing_population.astype(str).tolist()[:10])
        raise ValueError(
            f"Missing {YEAR} population for {len(missing_population)} nutrition-profile countries: "
            f"{preview}. Population source: {population_path}"
        )
    population = population.reindex(country_energy.index)

    totals: Dict[int, float] = {}
    ruminant_totals: Dict[int, float] = {}
    for cap_pct, cap_col in cap_columns.items():
        total = float((country_energy[cap_col] * population * 365.0).sum())
        if not np.isfinite(total) or total <= 0:
            raise ValueError(f"Non-positive reconstructed food energy for {cap_col}: {total}")
        ruminant_by_country = country_ruminant_energy[cap_col].reindex(
            country_energy.index, fill_value=0.0
        )
        ruminant_total = float((ruminant_by_country * population * 365.0).sum())
        if not np.isfinite(ruminant_total) or ruminant_total < 0 or ruminant_total > total:
            raise ValueError(
                f"Invalid reconstructed ruminant food energy for {cap_col}: {ruminant_total}"
            )
        totals[cap_pct] = total
        ruminant_totals[cap_pct] = ruminant_total

    current_col = f"Y{BASE_YEAR}"
    if current_col not in energy.columns:
        raise ValueError(f"Nutrition profile missing current-year column {current_col}: {profile_path}")
    energy[current_col] = pd.to_numeric(energy[current_col], errors="coerce").fillna(0.0)
    current_population = _load_yield_population(population_path, year=BASE_YEAR)
    current_country_energy = energy.groupby("m49_code", sort=False)[current_col].sum()
    current_country_ruminant = energy[energy["is_ruminant_food"]].groupby(
        "m49_code", sort=False
    )[current_col].sum()
    missing_current_population = current_country_energy.index.difference(current_population.index)
    if len(missing_current_population) > 0:
        preview = ", ".join(missing_current_population.astype(str).tolist()[:10])
        raise ValueError(
            f"Missing {BASE_YEAR} population for nutrition-profile countries: {preview}"
        )
    current_population = current_population.reindex(current_country_energy.index)
    current_total = float((current_country_energy * current_population * 365.0).sum())
    current_ruminant = float(
        (
            current_country_ruminant.reindex(current_country_energy.index, fill_value=0.0)
            * current_population
            * 365.0
        ).sum()
    )
    if not np.isfinite(current_total) or current_total <= 0:
        raise ValueError(f"Non-positive {BASE_YEAR} profile food energy: {current_total}")
    current_metrics = {
        "profile_food_kcal_2020": current_total,
        "profile_ruminant_food_kcal_2020": current_ruminant,
        "profile_ruminant_food_share_2020": current_ruminant / current_total,
    }
    return totals, ruminant_totals, cap_columns, current_metrics


def _reconstruct_final_food_energy_from_mc_profiles() -> pd.DataFrame:
    profile_sheet = str(CONFIG.get("yield_profile_sheet", "low_land_new") or "low_land_new")
    if profile_sheet.strip().lower().replace("-", "_") != "low_land_new":
        raise RuntimeError(
            "Profile-based final-food reconstruction is only defined for low_land_new. "
            "Provide CONFIG['yield_final_food_energy_csv'] for other diet-profile semantics."
        )
    if not MC_DRAWS_PATH.exists():
        raise FileNotFoundError(
            "Missing both merged final-food energy and MC draws needed for reconstruction: "
            f"{FINAL_FOOD_ENERGY_PATH}; {MC_DRAWS_PATH}"
        )
    draws_all = pd.read_csv(
        MC_DRAWS_PATH,
        usecols=lambda c: str(c).strip()
        in {"scenario_id", "sample_id", "spec_row_id", "kind", "value_draw"},
    )
    draws_all.columns = [str(c).strip() for c in draws_all.columns]
    required = {"scenario_id", "sample_id", "kind", "value_draw"}
    if not required.issubset(draws_all.columns):
        missing = ", ".join(sorted(required - set(draws_all.columns)))
        raise ValueError(f"MC draws missing columns needed for final-food reconstruction: {missing}")
    kind_norm = draws_all["kind"].astype(str).str.strip().str.lower()
    unsupported = kind_norm.str.contains("population", regex=False) | kind_norm.isin(
        {"nutrition_profile", "nutrition_profile_xlsx", "nutrition_profile_path"}
    )
    if bool(unsupported.any()):
        unsupported_kinds = sorted(kind_norm.loc[unsupported].unique().tolist())
        raise RuntimeError(
            "MC draws change population or the diet profile, so fixed-profile final-food "
            "reconstruction is not valid. Provide mc_success_final_food_energy.csv. "
            f"Unsupported kinds: {unsupported_kinds}"
        )
    draws = draws_all[
        kind_norm.eq("ruminant_reduction")
    ].copy()
    draws["sample_id"] = pd.to_numeric(draws["sample_id"], errors="coerce")
    draws["value_draw"] = pd.to_numeric(draws["value_draw"], errors="coerce")
    draws = draws.dropna(subset=["scenario_id", "sample_id", "value_draw"]).copy()
    if draws.empty:
        raise ValueError(f"No ruminant_reduction rows in MC draws: {MC_DRAWS_PATH}")

    caps = draws.groupby(["scenario_id", "sample_id"], as_index=False).agg(
        cap_rate_min=("value_draw", "min"),
        cap_rate_max=("value_draw", "max"),
        cap_rate=("value_draw", "mean"),
        cap_source_rows=("value_draw", "size"),
    )
    spread = caps["cap_rate_max"] - caps["cap_rate_min"]
    if bool(spread.gt(1e-9).any()):
        bad = caps.loc[spread.gt(1e-9), ["scenario_id", "sample_id"]].head(5)
        raise ValueError(
            "Ruminant-cap rows are inconsistent within samples: "
            + bad.to_dict("records").__repr__()
        )
    cap_pct_float = caps["cap_rate"] * 100.0
    caps["profile_cap_pct"] = np.rint(cap_pct_float).astype(int)
    if bool((cap_pct_float - caps["profile_cap_pct"]).abs().gt(1e-6).any()):
        raise ValueError("MC ruminant caps are not on the expected integer-percent profile grid.")
    if bool(caps["profile_cap_pct"].lt(0).any()):
        raise ValueError("MC ruminant caps contain negative profile percentages.")

    profile_path, population_path = _resolve_yield_food_energy_paths()
    totals, ruminant_totals, cap_columns, current_profile_metrics = _profile_final_food_kcal_by_cap(
        caps["profile_cap_pct"].unique().tolist(),
        profile_path=profile_path,
        population_path=population_path,
    )
    caps["final_food_kcal"] = caps["profile_cap_pct"].map(totals)
    caps["ruminant_food_kcal"] = caps["profile_cap_pct"].map(ruminant_totals)
    caps["ruminant_food_share"] = caps["ruminant_food_kcal"] / caps["final_food_kcal"]
    caps["profile_column"] = caps["profile_cap_pct"].map(cap_columns)
    caps["year"] = YEAR
    caps["final_food_energy_source"] = "nutrition_profile_x_2080_population"
    caps["nutrition_profile_path"] = str(profile_path)
    caps["population_path"] = str(population_path)
    for key, value in current_profile_metrics.items():
        caps[key] = float(value)
    caps["scenario_id"] = caps["scenario_id"].astype(str)
    caps["sample_id"] = caps["sample_id"].astype(int)
    print(
        f"[INFO] reconstructed {YEAR} final-food energy for {len(caps)} samples from "
        f"{len(totals)} sampled nutrition-profile caps; "
        f"range={caps['final_food_kcal'].min() / 1e15:.6f}-"
        f"{caps['final_food_kcal'].max() / 1e15:.6f} Pkcal"
    )
    print(
        f"[INFO] reconstructed human-diet ruminant kcal shares: "
        f"range={caps['ruminant_food_share'].min() * 100.0:.6f}-"
        f"{caps['ruminant_food_share'].max() * 100.0:.6f}%"
    )
    return caps


def _load_final_food_energy() -> pd.DataFrame:
    override = str(CONFIG.get("yield_final_food_energy_csv", "") or "").strip()
    path = Path(override).expanduser() if override else FINAL_FOOD_ENERGY_PATH
    if not path.exists():
        if override:
            raise FileNotFoundError(f"Configured yield final-food energy CSV does not exist: {path}")
        print(
            f"[WARN] merged final-food energy is unavailable ({path}); "
            "reconstructing from the exact sampled nutrition profiles."
        )
        return _reconstruct_final_food_energy_from_mc_profiles()

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"scenario_id", "sample_id", "year", "final_food_kcal"}
    if not required.issubset(df.columns):
        missing = ", ".join(sorted(required - set(df.columns)))
        raise ValueError(f"Merged final-food energy CSV missing columns {missing}: {path}")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    df["final_food_kcal"] = pd.to_numeric(df["final_food_kcal"], errors="coerce")
    if "ruminant_food_kcal" in df.columns:
        df["ruminant_food_kcal"] = pd.to_numeric(df["ruminant_food_kcal"], errors="coerce")
    if "ruminant_food_share" in df.columns:
        df["ruminant_food_share"] = pd.to_numeric(df["ruminant_food_share"], errors="coerce")
    elif "ruminant_food_kcal" in df.columns:
        df["ruminant_food_share"] = df["ruminant_food_kcal"] / df["final_food_kcal"]
    df = df[df["year"].eq(YEAR)].dropna(
        subset=["scenario_id", "sample_id", "final_food_kcal"]
    ).copy()
    df = df[df["final_food_kcal"].gt(0)].copy()
    duplicate = df.duplicated(["scenario_id", "sample_id"], keep=False)
    if bool(duplicate.any()):
        raise ValueError(
            f"Merged final-food energy has duplicate {YEAR} sample keys: "
            f"{df.loc[duplicate, ['scenario_id', 'sample_id']].head(5).to_dict('records')}"
        )
    df["scenario_id"] = df["scenario_id"].astype(str)
    df["sample_id"] = df["sample_id"].astype(int)
    if "final_food_energy_source" not in df.columns:
        df["final_food_energy_source"] = "merged_final_food_energy"
    print(f"[INFO] loaded {YEAR} final-food energy rows: {len(df)} from {path}")
    return df


def _build_human_diet_ruminant_share_metric(final_food_energy_df: pd.DataFrame) -> pd.DataFrame:
    empty_cols = ["scenario_id", "sample_id", "metric_value"]
    if final_food_energy_df is None or final_food_energy_df.empty:
        return pd.DataFrame(columns=empty_cols)
    required = {
        "scenario_id",
        "sample_id",
        "year",
        "final_food_kcal",
        "ruminant_food_kcal",
    }
    if not required.issubset(final_food_energy_df.columns):
        missing = ", ".join(sorted(required - set(final_food_energy_df.columns)))
        raise ValueError(
            "Human-diet ruminant share requires a food-only numerator and denominator. "
            f"Missing columns: {missing}"
        )
    out = final_food_energy_df.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["sample_id"] = pd.to_numeric(out["sample_id"], errors="coerce")
    out["final_food_kcal"] = pd.to_numeric(out["final_food_kcal"], errors="coerce")
    out["ruminant_food_kcal"] = pd.to_numeric(out["ruminant_food_kcal"], errors="coerce")
    out = out[out["year"].eq(YEAR)].dropna(
        subset=["scenario_id", "sample_id", "final_food_kcal", "ruminant_food_kcal"]
    ).copy()
    out = out[
        out["final_food_kcal"].gt(0)
        & out["ruminant_food_kcal"].ge(0)
        & out["ruminant_food_kcal"].le(out["final_food_kcal"])
    ].copy()
    if out.empty:
        return pd.DataFrame(columns=empty_cols)
    duplicate = out.duplicated(["scenario_id", "sample_id"], keep=False)
    if bool(duplicate.any()):
        raise ValueError("Human-diet ruminant share must have exactly one 2080 row per sample.")
    out["scenario_id"] = out["scenario_id"].astype(str)
    out["sample_id"] = out["sample_id"].astype(int)
    out["metric_value"] = out["ruminant_food_kcal"] / out["final_food_kcal"]
    out["metric_formula"] = "ruminant_human_food_kcal_2080 / total_human_food_kcal_2080"
    if "ruminant_food_share" in out.columns:
        stored = pd.to_numeric(out["ruminant_food_share"], errors="coerce")
        error = (stored - out["metric_value"]).abs()
        if bool(error.dropna().gt(1e-12).any()):
            raise ValueError(
                "Stored ruminant_food_share does not match ruminant_food_kcal/final_food_kcal."
            )
    out["ruminant_share_formula_error"] = 0.0
    print(
        f"[INFO] {YEAR} human-diet ruminant kcal-share rows: {len(out)}; "
        f"range={out['metric_value'].min() * 100.0:.6f}-"
        f"{out['metric_value'].max() * 100.0:.6f}%"
    )
    return out


def _load_luc_process_emissions() -> pd.DataFrame:
    if not PROCESS_CO2EQ_PATH.exists():
        print(f"[WARN] missing process CO2eq file for LUC intensity: {PROCESS_CO2EQ_PATH}")
        return pd.DataFrame(columns=["scenario_id", "sample_id", "luc_co2eq_gt"])

    df = pd.read_csv(
        PROCESS_CO2EQ_PATH,
        usecols=lambda c: str(c).strip()
        in {"scenario_id", "sample_id", "year", "Process", "co2eq_gt", "co2eq_kt"},
    )
    df.columns = [str(c).strip() for c in df.columns]
    required = {"scenario_id", "sample_id", "Process"}
    if not required.issubset(df.columns):
        print(f"[WARN] process CO2eq file missing required columns: {PROCESS_CO2EQ_PATH}")
        return pd.DataFrame(columns=["scenario_id", "sample_id", "luc_co2eq_gt"])

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df = df[df["year"] == YEAR].copy()

    df["Process"] = df["Process"].astype(str).str.strip()
    df = df[df["Process"].isin(LUC_LAND_INTENSITY_PROCESSES)].copy()
    if df.empty:
        print("[WARN] no matching LUC processes found for LUC intensity.")
        return pd.DataFrame(columns=["scenario_id", "sample_id", "luc_co2eq_gt"])

    if "co2eq_gt" in df.columns:
        df["luc_co2eq_gt"] = pd.to_numeric(df["co2eq_gt"], errors="coerce")
    elif "co2eq_kt" in df.columns:
        df["luc_co2eq_gt"] = pd.to_numeric(df["co2eq_kt"], errors="coerce") * 1e-6
    else:
        print(f"[WARN] process CO2eq file missing co2eq_gt/kt column: {PROCESS_CO2EQ_PATH}")
        return pd.DataFrame(columns=["scenario_id", "sample_id", "luc_co2eq_gt"])

    out = (
        df.dropna(subset=["scenario_id", "sample_id", "luc_co2eq_gt"])
        .assign(
            scenario_id=lambda x: x["scenario_id"].astype(str),
            sample_id=lambda x: pd.to_numeric(x["sample_id"], errors="coerce"),
        )
        .dropna(subset=["sample_id"])
        .groupby(["scenario_id", "sample_id"], as_index=False)["luc_co2eq_gt"]
        .sum()
    )
    out["sample_id"] = out["sample_id"].astype(int)
    print(f"[INFO] LUC process-emission rows: {len(out)}")
    return out


def _load_crop_pasture_land_balance() -> pd.DataFrame:
    empty_cols = [
        "scenario_id",
        "sample_id",
        "crop_pasture_land_ha",
        "land_year",
        "land_source",
    ]
    if not LAND_BALANCE_PATH.exists():
        print(f"[WARN] missing crop/pasture land-balance file for LUC intensity: {LAND_BALANCE_PATH}")
        return pd.DataFrame(columns=empty_cols)

    df = pd.read_csv(LAND_BALANCE_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"scenario_id", "sample_id", "year"}
    if not required.issubset(df.columns):
        print(f"[WARN] land-balance file missing required columns: {LAND_BALANCE_PATH}")
        return pd.DataFrame(columns=empty_cols)

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[df["year"] == YEAR].copy()
    if df.empty:
        return pd.DataFrame(columns=empty_cols)

    if "source" in df.columns:
        source = df["source"].astype(str).str.strip()
        preferred = df[source.eq("luc_land_area_DS_period")].copy()
        if not preferred.empty:
            df = preferred

    if {"crop_area_need_ha", "grass_area_need_ha"}.issubset(df.columns):
        crop = pd.to_numeric(df["crop_area_need_ha"], errors="coerce").fillna(0.0)
        pasture = pd.to_numeric(df["grass_area_need_ha"], errors="coerce").fillna(0.0)
    elif {"new_cropland_ha", "yr_grass_need_ha"}.issubset(df.columns):
        crop = pd.to_numeric(df["new_cropland_ha"], errors="coerce").fillna(0.0)
        pasture = pd.to_numeric(df["yr_grass_need_ha"], errors="coerce").fillna(0.0)
    else:
        print(
            "[WARN] land-balance file lacks crop_area_need_ha/grass_area_need_ha "
            "or new_cropland_ha/yr_grass_need_ha."
        )
        return pd.DataFrame(columns=empty_cols)

    work = df[["scenario_id", "sample_id"]].copy()
    work["crop_pasture_land_ha"] = crop + pasture
    work["land_year"] = YEAR
    work["land_source"] = (
        df["source"].astype(str).str.strip() if "source" in df.columns else "unspecified"
    )
    work["scenario_id"] = work["scenario_id"].astype(str)
    work["sample_id"] = pd.to_numeric(work["sample_id"], errors="coerce")
    work["crop_pasture_land_ha"] = pd.to_numeric(work["crop_pasture_land_ha"], errors="coerce")
    work = work.dropna(subset=["sample_id", "crop_pasture_land_ha"]).copy()
    work = work[work["crop_pasture_land_ha"] > 0].copy()
    if work.empty:
        return pd.DataFrame(columns=empty_cols)
    source_counts = work.groupby(["scenario_id", "sample_id"])["land_source"].nunique()
    if bool(source_counts.gt(1).any()):
        raise ValueError("Crop+pasture land denominator has multiple sources within a sample.")
    out = work.groupby(["scenario_id", "sample_id"], as_index=False).agg(
        crop_pasture_land_ha=("crop_pasture_land_ha", "mean"),
        land_year=("land_year", "first"),
        land_source=("land_source", "first"),
    )
    out["sample_id"] = out["sample_id"].astype(int)
    print(f"[INFO] crop+pasture land rows: {len(out)}")
    return out


def _first_numeric_column(df: pd.DataFrame, candidates: Sequence[str]) -> Tuple[Optional[str], pd.Series]:
    for col in candidates:
        if col not in df.columns:
            continue
        vals = pd.to_numeric(df[col], errors="coerce")
        if vals.notna().any():
            return col, vals
    return None, pd.Series(np.nan, index=df.index, dtype=float)


def _load_luc_land_intensity_land_balance() -> pd.DataFrame:
    """Load crop + pasture + forest area used as the LUC intensity denominator."""
    empty_cols = ["scenario_id", "sample_id", "luc_land_denominator_ha"]
    if not LAND_BALANCE_PATH.exists():
        print(f"[WARN] missing land-balance file for LUC intensity denominator: {LAND_BALANCE_PATH}")
        return pd.DataFrame(columns=empty_cols)

    df = pd.read_csv(LAND_BALANCE_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"scenario_id", "sample_id", "year"}
    if not required.issubset(df.columns):
        print(f"[WARN] land-balance file missing required columns: {LAND_BALANCE_PATH}")
        return pd.DataFrame(columns=empty_cols)

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[df["year"] == YEAR].copy()
    if df.empty:
        return pd.DataFrame(columns=empty_cols)

    source = df["source"].astype(str).str.strip() if "source" in df.columns else pd.Series("", index=df.index)
    source_order = (
        "luc_land_area_solver_period",
        "luc_land_area_LUH2Based_period",
        "luc_land_area_actual_period",
    )
    chosen = pd.DataFrame()
    for source_name in source_order:
        candidate = df[source.eq(source_name)].copy()
        if candidate.empty:
            continue
        forest_col, forest_vals = _first_numeric_column(candidate, ("forest_area_ha", "forest_ha"))
        if forest_col is not None and forest_vals.notna().any():
            chosen = candidate
            break
    if chosen.empty:
        forest_col, forest_vals = _first_numeric_column(df, ("forest_area_ha", "forest_ha"))
        if forest_col is not None and forest_vals.notna().any():
            chosen = df[forest_vals.notna()].copy()

    if chosen.empty:
        print(
            "[WARN] land-balance file has no forest absolute area for LUC intensity denominator. "
            "Rerun S5_4 with updated lightweight diagnostics so "
            "mc_success_crop_pasture_land_balance.csv includes forest_area_ha."
        )
        return pd.DataFrame(columns=empty_cols)

    crop_col, crop = _first_numeric_column(
        chosen,
        ("crop_area_ha", "cropland_area_ha", "cropland_ha", "crop_area_need_ha"),
    )
    pasture_col, pasture = _first_numeric_column(
        chosen,
        ("pasture_area_ha", "grassland_area_ha", "grassland_ha", "grass_area_need_ha"),
    )
    forest_col, forest = _first_numeric_column(chosen, ("forest_area_ha", "forest_ha"))
    if crop_col is None or pasture_col is None or forest_col is None:
        print(
            "[WARN] land-balance file lacks crop/pasture/forest absolute area columns "
            f"for LUC intensity denominator. Found crop={crop_col}, pasture={pasture_col}, forest={forest_col}."
        )
        return pd.DataFrame(columns=empty_cols)

    work = chosen[["scenario_id", "sample_id"]].copy()
    work["luc_land_denominator_ha"] = crop.fillna(0.0) + pasture.fillna(0.0) + forest.fillna(0.0)
    work["scenario_id"] = work["scenario_id"].astype(str)
    work["sample_id"] = pd.to_numeric(work["sample_id"], errors="coerce")
    work["luc_land_denominator_ha"] = pd.to_numeric(work["luc_land_denominator_ha"], errors="coerce")
    work = work.dropna(subset=["sample_id", "luc_land_denominator_ha"]).copy()
    work = work[work["luc_land_denominator_ha"] > 0].copy()
    if work.empty:
        return pd.DataFrame(columns=empty_cols)
    out = work.groupby(["scenario_id", "sample_id"], as_index=False)["luc_land_denominator_ha"].mean()
    out["sample_id"] = out["sample_id"].astype(int)
    print(f"[INFO] crop+pasture+forest land rows: {len(out)}")
    return out


def _build_luc_land_intensity_metric() -> pd.DataFrame:
    luc = _load_luc_process_emissions()
    land = _load_luc_land_intensity_land_balance()
    if luc.empty or land.empty:
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])
    out = luc.merge(land, on=["scenario_id", "sample_id"], how="inner")
    if out.empty:
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])
    # Gt CO2eq/yr -> t CO2eq/yr, divided by ha.
    out["metric_value"] = pd.to_numeric(out["luc_co2eq_gt"], errors="coerce") * 1e9 / pd.to_numeric(
        out["luc_land_denominator_ha"], errors="coerce"
    )
    out = out.dropna(subset=["metric_value"]).copy()
    print(f"[INFO] LUC land-use intensity rows: {len(out)}")
    return out[["scenario_id", "sample_id", "metric_value"]]


def _build_yield_land_productivity_metric(final_food_energy_df: pd.DataFrame) -> pd.DataFrame:
    empty_cols = [
        "scenario_id",
        "sample_id",
        "metric_value",
        "final_food_kcal",
        "crop_pasture_land_ha",
    ]
    if final_food_energy_df is None or final_food_energy_df.empty:
        return pd.DataFrame(columns=empty_cols)
    food = final_food_energy_df.copy()
    required = {"scenario_id", "sample_id", "year", "final_food_kcal"}
    if not required.issubset(food.columns):
        missing = ", ".join(sorted(required - set(food.columns)))
        raise ValueError(f"Final-food energy data missing columns: {missing}")
    food["year"] = pd.to_numeric(food["year"], errors="coerce")
    food["sample_id"] = pd.to_numeric(food["sample_id"], errors="coerce")
    food["final_food_kcal"] = pd.to_numeric(food["final_food_kcal"], errors="coerce")
    food = food[
        food["year"].eq(YEAR)
        & food["final_food_kcal"].gt(0)
    ].dropna(subset=["scenario_id", "sample_id"]).copy()
    if food.empty:
        return pd.DataFrame(columns=empty_cols)
    duplicate = food.duplicated(["scenario_id", "sample_id"], keep=False)
    if bool(duplicate.any()):
        raise ValueError("Final-food energy must have exactly one 2080 row per sample.")
    food["scenario_id"] = food["scenario_id"].astype(str)
    food["sample_id"] = food["sample_id"].astype(int)
    food = food.rename(columns={"year": "final_food_year"})

    land = _load_crop_pasture_land_balance()
    if land.empty:
        return pd.DataFrame(columns=empty_cols)
    out = food.merge(
        land,
        on=["scenario_id", "sample_id"],
        how="inner",
        validate="one_to_one",
    )
    if out.empty:
        return pd.DataFrame(columns=empty_cols)
    if not bool(out["final_food_year"].eq(YEAR).all()) or not bool(out["land_year"].eq(YEAR).all()):
        raise ValueError("Yield land productivity requires matching 2080 food and land rows.")
    out["metric_value"] = (
        pd.to_numeric(out["final_food_kcal"], errors="coerce")
        / 1e6
        / pd.to_numeric(out["crop_pasture_land_ha"], errors="coerce")
    )
    out = out.replace([np.inf, -np.inf], np.nan).dropna(subset=["metric_value"]).copy()
    out = out[out["metric_value"].gt(0)].copy()
    out["metric_formula"] = "final_food_kcal_2080 / 1e6 / crop_plus_pasture_ha_2080"
    print(
        f"[INFO] {YEAR} final-food land-productivity rows: {len(out)}; "
        f"range={out['metric_value'].min():.6f}-{out['metric_value'].max():.6f} Mkcal/ha"
    )
    return out


def _unique_numeric_value(
    values: pd.Series,
    *,
    label: str,
    require_positive: bool = True,
) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        raise ValueError(f"No numeric values available for {label}.")
    reference = float(numeric.median())
    tolerance = max(1e-12, abs(reference) * 1e-10)
    if float((numeric - reference).abs().max()) > tolerance:
        raise ValueError(f"{label} is not constant across baseline/sample rows.")
    if require_positive and reference <= 0:
        raise ValueError(f"{label} must be positive, got {reference}.")
    return reference


def _load_current_land_denominators_2020() -> Dict[str, object]:
    if not LAND_BALANCE_PATH.exists():
        raise FileNotFoundError(f"Missing land balance for Current 2020 metrics: {LAND_BALANCE_PATH}")
    land = pd.read_csv(LAND_BALANCE_PATH)
    land.columns = [str(c).strip() for c in land.columns]
    required = {"year", "source"}
    if not required.issubset(land.columns):
        raise ValueError(f"Land balance missing Current 2020 columns: {LAND_BALANCE_PATH}")
    land["year"] = pd.to_numeric(land["year"], errors="coerce")
    current = land[land["year"].eq(BASE_YEAR)].copy()
    if current.empty:
        raise ValueError(f"Land balance has no {BASE_YEAR} rows: {LAND_BALANCE_PATH}")

    ds = current[current["source"].astype(str).str.strip().eq("luc_land_area_DS_period")].copy()
    if ds.empty or not {"crop_area_need_ha", "grass_area_need_ha"}.issubset(ds.columns):
        raise ValueError("Current 2020 DS crop+pasture land denominator is unavailable.")
    crop_pasture = (
        pd.to_numeric(ds["crop_area_need_ha"], errors="coerce")
        + pd.to_numeric(ds["grass_area_need_ha"], errors="coerce")
    )
    crop_pasture_ha = _unique_numeric_value(
        crop_pasture,
        label="Current 2020 crop+pasture land",
    )

    luh = current[
        current["source"].astype(str).str.strip().eq("luc_land_area_LUH2Based_period")
    ].copy()
    luh_cols = {"crop_area_ha", "pasture_area_ha", "forest_area_ha"}
    if luh.empty or not luh_cols.issubset(luh.columns):
        raise ValueError("Current 2020 crop+pasture+forest land denominator is unavailable.")
    total_land = (
        pd.to_numeric(luh["crop_area_ha"], errors="coerce")
        + pd.to_numeric(luh["pasture_area_ha"], errors="coerce")
        + pd.to_numeric(luh["forest_area_ha"], errors="coerce")
    )
    crop_pasture_forest_ha = _unique_numeric_value(
        total_land,
        label="Current 2020 crop+pasture+forest land",
    )
    return {
        "crop_pasture_ha": crop_pasture_ha,
        "crop_pasture_source": f"{LAND_BALANCE_PATH}:luc_land_area_DS_period",
        "crop_pasture_forest_ha": crop_pasture_forest_ha,
        "crop_pasture_forest_source": (
            f"{LAND_BALANCE_PATH}:luc_land_area_LUH2Based_period"
        ),
    }


def _load_current_luc_emissions_2020(emissions_path: Path) -> Dict[str, object]:
    year_col = f"Y{BASE_YEAR}"
    emissions = pd.read_csv(
        emissions_path,
        usecols=lambda c: str(c).strip()
        in {"M49_Country_Code", "Process", "GHG", year_col},
        low_memory=False,
    )
    emissions.columns = [str(c).strip() for c in emissions.columns]
    required = {"M49_Country_Code", "Process", "GHG", year_col}
    if not required.issubset(emissions.columns):
        missing = ", ".join(sorted(required - set(emissions.columns)))
        raise ValueError(f"Baseline emissions missing LUC columns {missing}: {emissions_path}")
    m49 = emissions["M49_Country_Code"].map(_normalize_m49_code)
    process = emissions["Process"].astype(str).str.strip()
    ghg = emissions["GHG"].astype(str).str.strip().str.upper()
    values_kt = pd.to_numeric(emissions[year_col], errors="coerce")
    matched = (
        process.isin(LUC_LAND_INTENSITY_PROCESSES)
        & ghg.eq("CO2EQ")
        & values_kt.notna()
    )
    country_rows = matched & m49.ne("000")
    selected = country_rows if bool(country_rows.any()) else matched & m49.eq("000")
    luc_emissions_kt = float(values_kt.loc[selected].sum())
    if not np.isfinite(luc_emissions_kt):
        raise ValueError(f"No finite Current 2020 LUC CO2eq total in {emissions_path}")
    return {
        "luc_emissions_kt": luc_emissions_kt,
        "luc_emissions_gt": luc_emissions_kt * 1e-6,
        "luc_emissions_rows": int(selected.sum()),
        "luc_process_count": int(process.loc[selected].nunique()),
        "luc_emissions_source": str(emissions_path),
    }


def _current_profile_ruminant_metrics(final_food_energy_df: pd.DataFrame) -> Dict[str, float]:
    column_map = {
        "profile_food_kcal_2020": True,
        "profile_ruminant_food_kcal_2020": False,
        "profile_ruminant_food_share_2020": False,
    }
    if all(column in final_food_energy_df.columns for column in column_map):
        return {
            column: _unique_numeric_value(
                final_food_energy_df[column],
                label=column,
                require_positive=require_positive,
            )
            for column, require_positive in column_map.items()
        }

    profile_path, population_path = _resolve_yield_food_energy_paths()
    _, _, _, current_metrics = _profile_final_food_kcal_by_cap(
        [13],
        profile_path=profile_path,
        population_path=population_path,
    )
    return current_metrics


def _build_current_metrics_2020(
    ef_system_baseline: Dict[str, object],
    final_food_energy_df: pd.DataFrame,
) -> pd.DataFrame:
    land = _load_current_land_denominators_2020()
    current_profile = _current_profile_ruminant_metrics(final_food_energy_df)
    luc = _load_current_luc_emissions_2020(Path(str(ef_system_baseline["emissions_path"])))

    food_energy_2020 = float(ef_system_baseline["food_energy_kcal"])
    production_emissions_gt = float(
        ef_system_baseline["production_baseline_emissions_gt"]
    )
    gross_production_kcal = float(
        ef_system_baseline["gross_production_energy_2020_kcal"]
    )
    ruminant_food_2020 = float(current_profile["profile_ruminant_food_kcal_2020"])
    profile_food_2020 = float(current_profile["profile_food_kcal_2020"])
    ruminant_share_2020 = ruminant_food_2020 / profile_food_2020
    if "nutrition_profile_path" in final_food_energy_df.columns:
        profile_sources = final_food_energy_df["nutrition_profile_path"].dropna().astype(str)
        profile_source = str(profile_sources.iloc[0]) if not profile_sources.empty else ""
    else:
        profile_source = ""
    if not profile_source:
        profile_source = str(_resolve_yield_food_energy_paths()[0])

    absolute_metrics = {
        "yield": food_energy_2020 / 1e6 / float(land["crop_pasture_ha"]),
        "emission_factor": float(
            ef_system_baseline["production_baseline_intensity_g_per_kcal"]
        ),
        "ruminate_intake": ruminant_share_2020,
        "luc_land_intensity": (
            float(luc["luc_emissions_gt"])
            * 1e9
            / float(land["crop_pasture_forest_ha"])
        ),
    }
    provenance = {
        "yield": {
            "numerator_value": food_energy_2020,
            "numerator_unit": "kcal/yr",
            "denominator_value": float(land["crop_pasture_ha"]),
            "denominator_unit": "ha",
            "formula": "final_food_kcal_2020 / 1e6 / crop_plus_pasture_ha_2020",
            "numerator_source": str(ef_system_baseline["nutrition_path"]),
            "denominator_source": str(land["crop_pasture_source"]),
        },
        "emission_factor": {
            "numerator_value": production_emissions_gt,
            "numerator_unit": "Gt CO2e/yr",
            "denominator_value": gross_production_kcal,
            "denominator_unit": "kcal/yr",
            "formula": (
                "crop_plus_livestock_production_CO2e_2020_excluding_LUC "
                "/ gross_crop_plus_livestock_production_kcal_2020"
            ),
            "numerator_source": str(ef_system_baseline["emissions_path"]),
            "denominator_source": str(
                ef_system_baseline["production_summary_path"]
            ),
            "denominator_factor_source": str(
                ef_system_baseline["production_dictionary_path"]
            ),
            "process_scope": str(ef_system_baseline["production_processes"]),
        },
        "ruminate_intake": {
            "numerator_value": ruminant_food_2020,
            "numerator_unit": "kcal/yr",
            "denominator_value": profile_food_2020,
            "denominator_unit": "kcal/yr",
            "formula": "ruminant_human_food_kcal_2020 / total_human_food_kcal_2020",
            "numerator_source": profile_source,
            "denominator_source": profile_source,
        },
        "luc_land_intensity": {
            "numerator_value": float(luc["luc_emissions_gt"]),
            "numerator_unit": "Gt CO2eq/yr",
            "denominator_value": float(land["crop_pasture_forest_ha"]),
            "denominator_unit": "ha",
            "formula": "LUC_CO2eq_2020 * 1e9 / crop_plus_pasture_plus_forest_ha_2020",
            "numerator_source": str(luc["luc_emissions_source"]),
            "denominator_source": str(land["crop_pasture_forest_source"]),
        },
    }

    rows: List[Dict[str, object]] = []
    for panel in PANEL_SPECS:
        spec = _active_panel_spec(panel)
        absolute_value = float(absolute_metrics[panel])
        if str(spec["value_mode"]) == "change_percent":
            metric_value = 1.0
            metric_display = 0.0
        elif str(spec["value_mode"]) == "share_percent":
            metric_value = absolute_value
            metric_display = absolute_value * 100.0
        else:
            metric_value = absolute_value
            metric_display = absolute_value
        row: Dict[str, object] = {
            "panel": panel,
            "current_year": BASE_YEAR,
            "metric_value": metric_value,
            "metric_display": metric_display,
            "absolute_metric_value": absolute_value,
            "metric_label": str(spec["metric_label"]),
            "metric_unit": str(spec["metric_unit"]),
            "value_mode": str(spec["value_mode"]),
        }
        row.update(provenance[panel])
        rows.append(row)
    out = pd.DataFrame(rows)
    print(
        "[INFO] Current 2020 metrics: "
        + "; ".join(
            f"{row.panel}={_format_metric_with_unit(float(row.metric_display), _active_panel_spec(str(row.panel)))}"
            for row in out.itertuples(index=False)
        )
    )
    return out


def _resolve_row_weight(df: pd.DataFrame) -> pd.Series:
    weight = pd.Series(1.0, index=df.index, dtype=float)
    if "weight_kcal_total" in df.columns:
        kcal = pd.to_numeric(df["weight_kcal_total"], errors="coerce")
        weight.loc[kcal.notna() & (kcal > 0)] = kcal.loc[kcal.notna() & (kcal > 0)].astype(float)
    if "selected_pairs" in df.columns:
        pairs = pd.to_numeric(df["selected_pairs"], errors="coerce")
        fill_mask = ((weight <= 0) | ~np.isfinite(weight)) & pairs.notna() & (pairs > 0)
        weight.loc[fill_mask] = pairs.loc[fill_mask].astype(float)
    return weight.where(np.isfinite(weight) & (weight > 0), 1.0)


def _derive_ratio_metric(df: pd.DataFrame) -> pd.Series:
    if "weighted_ratio" in df.columns:
        ratio = _numeric_series(df, "weighted_ratio")
        if ratio.notna().any():
            return ratio

    sample = _numeric_series(df, "weighted_value_sample")
    base = _numeric_series(df, "weighted_value_y2020")
    ratio = pd.Series(np.nan, index=df.index, dtype=float)
    valid_base = base.notna() & np.isfinite(base) & (base != 0)
    ratio.loc[valid_base] = sample.loc[valid_base] / base.loc[valid_base]

    if "mc_unit" in df.columns:
        mc_unit = df["mc_unit"].astype(str).str.strip().str.lower()
        rate_mask = mc_unit == "rate"
        fill_mask = ratio.isna() & rate_mask & sample.notna()
        ratio.loc[fill_mask] = 1.0 + sample.loc[fill_mask]
        mult_mask = mc_unit == "multiplier"
        fill_mask = ratio.isna() & mult_mask & sample.notna()
        ratio.loc[fill_mask] = sample.loc[fill_mask]

    return ratio


def _derive_absolute_metric(df: pd.DataFrame, *, require_baseline: bool = False) -> pd.Series:
    sample = _numeric_series(df, "weighted_value_sample")
    base = _numeric_series(df, "weighted_value_y2020")
    ratio = _numeric_series(df, "weighted_ratio")
    out = pd.Series(np.nan, index=df.index, dtype=float)

    from_base = base.notna() & np.isfinite(base) & ratio.notna() & np.isfinite(ratio)
    out.loc[from_base] = base.loc[from_base] * ratio.loc[from_base]

    sample_ok = sample.notna() & np.isfinite(sample)
    if require_baseline:
        sample_ok = sample_ok & base.notna() & np.isfinite(base)
    out.loc[out.isna() & sample_ok] = sample.loc[out.isna() & sample_ok]

    if out.notna().any():
        return out
    return out


def _build_production_ef_intensity_metric(
    weighted_df: pd.DataFrame,
    baseline: Dict[str, object],
) -> pd.DataFrame:
    """Return crop/livestock production EF after applying sampled EF changes.

    EF-controlled production emissions are reconstructed by multiplying each
    row's kg-CO2e/kcal intensity by its fixed 2020 gross-production kcal
    activity. Production emissions outside the sampled EF rows remain at their
    2020 values. LUC and Fish farming are excluded from both the sampled rows
    and the production baseline. Gross crop/livestock production kcal is
    counted once, rather than once per EF parameter/process row.
    """
    sub = weighted_df[
        weighted_df["kind"].astype(str).str.strip().str.lower().eq("emission_factor")
    ].copy()
    if sub.empty:
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])

    required = {
        "scenario_id",
        "sample_id",
        "process_selector",
        "weight_kcal_total",
        "weighted_co2eq_intensity_y2020_kg_per_kcal",
        "weighted_co2eq_intensity_sample_kg_per_kcal",
    }
    missing = sorted(required - set(sub.columns))
    if missing:
        raise ValueError(
            "Production EF intensity requires columns "
            f"{', '.join(missing)} in {WEIGHTED_ELEMENTS_PATH}."
        )

    sub["process_selector"] = sub["process_selector"].astype(str).str.strip()
    sub = sub[sub["process_selector"].isin(PRODUCTION_EF_PROCESSES)].copy()
    if sub.empty:
        raise RuntimeError(
            "No sampled EF rows match the crop/livestock production processes: "
            + ", ".join(PRODUCTION_EF_PROCESSES)
        )

    sub["scenario_id"] = sub["scenario_id"].astype(str)
    sub["sample_id"] = pd.to_numeric(sub["sample_id"], errors="coerce")
    sub["ef_activity_kcal_2020"] = pd.to_numeric(sub["weight_kcal_total"], errors="coerce")
    sub["ef_baseline_intensity_kg_per_kcal"] = pd.to_numeric(
        sub["weighted_co2eq_intensity_y2020_kg_per_kcal"], errors="coerce"
    )
    sub["ef_sample_intensity_kg_per_kcal"] = pd.to_numeric(
        sub["weighted_co2eq_intensity_sample_kg_per_kcal"], errors="coerce"
    )
    valid = (
        sub["sample_id"].notna()
        & sub["ef_activity_kcal_2020"].gt(0)
        & sub["ef_baseline_intensity_kg_per_kcal"].notna()
        & sub["ef_sample_intensity_kg_per_kcal"].notna()
    )
    valid &= np.isfinite(sub["ef_activity_kcal_2020"])
    valid &= np.isfinite(sub["ef_baseline_intensity_kg_per_kcal"])
    valid &= np.isfinite(sub["ef_sample_intensity_kg_per_kcal"])
    dropped = int((~valid).sum())
    sub = sub.loc[valid].copy()
    if sub.empty:
        raise RuntimeError(
            "No valid EF rows with 2020 kcal weights and baseline/sample CO2e intensities. "
            f"Current file: {WEIGHTED_ELEMENTS_PATH}"
        )
    if dropped:
        print(f"[INFO] dropped {dropped} EF rows without reconstructable baseline/sample emissions")

    sub["ef_controlled_baseline_emissions_kg"] = (
        sub["ef_activity_kcal_2020"] * sub["ef_baseline_intensity_kg_per_kcal"]
    )
    sub["ef_controlled_sample_emissions_kg"] = (
        sub["ef_activity_kcal_2020"] * sub["ef_sample_intensity_kg_per_kcal"]
    )
    out = (
        sub.groupby(["scenario_id", "sample_id"], as_index=False)[
            ["ef_controlled_baseline_emissions_kg", "ef_controlled_sample_emissions_kg"]
        ]
        .sum()
    )
    out["sample_id"] = out["sample_id"].astype(int)

    production_baseline_kg = float(baseline["production_baseline_emissions_kg"])
    gross_production_kcal = float(baseline["gross_production_energy_2020_kcal"])
    expected_baseline_intensity = float(
        baseline["production_baseline_intensity_g_per_kcal"]
    )
    controlled = out["ef_controlled_baseline_emissions_kg"]
    controlled_reference = float(controlled.median())
    tolerance_kg = max(1.0, abs(controlled_reference) * 1e-10)
    max_deviation_kg = float((controlled - controlled_reference).abs().max())
    if max_deviation_kg > tolerance_kg:
        raise RuntimeError(
            "EF baseline-emission coverage differs across MC samples: "
            f"median={controlled_reference / 1e12:.9f} Gt, "
            f"max_deviation={max_deviation_kg / 1e12:.9f} Gt. "
            "This indicates missing or inconsistent weighted-element rows."
        )
    if controlled_reference > production_baseline_kg + max(
        1.0, production_baseline_kg * 1e-10
    ):
        raise RuntimeError(
            "EF-controlled emissions exceed the production baseline: "
            f"EF={controlled_reference / 1e12:.6f} Gt, "
            f"production={production_baseline_kg / 1e12:.6f} Gt."
        )

    out["production_baseline_emissions_gt"] = production_baseline_kg / 1e12
    out["gross_production_energy_2020_kcal"] = gross_production_kcal
    out["production_intensity_baseline_g_per_kcal"] = expected_baseline_intensity
    out["production_process_count"] = len(PRODUCTION_EF_PROCESSES)
    out["production_processes"] = " | ".join(PRODUCTION_EF_PROCESSES)
    out["ef_controlled_production_baseline_emissions_gt"] = (
        out["ef_controlled_baseline_emissions_kg"] / 1e12
    )
    out["ef_controlled_production_sample_emissions_gt"] = (
        out["ef_controlled_sample_emissions_kg"] / 1e12
    )
    out["non_ef_production_baseline_emissions_gt"] = (
        production_baseline_kg - out["ef_controlled_baseline_emissions_kg"]
    ) / 1e12
    out["production_emissions_sample_gt"] = (
        production_baseline_kg
        - out["ef_controlled_baseline_emissions_kg"]
        + out["ef_controlled_sample_emissions_kg"]
    ) / 1e12
    out["metric_value"] = (
        out["production_emissions_sample_gt"] * 1e15 / gross_production_kcal
    )
    out["metric_formula"] = (
        "(production_baseline_CO2e_excluding_LUC "
        "- ef_controlled_production_baseline_CO2e "
        "+ ef_controlled_production_sample_CO2e) "
        "/ gross_crop_livestock_production_kcal_2020"
    )

    baseline_check = production_baseline_kg * 1e3 / gross_production_kcal
    if not np.isclose(baseline_check, expected_baseline_intensity, rtol=1e-12, atol=1e-12):
        raise RuntimeError(
            "Production EF baseline invariant failed: "
            f"recomputed={baseline_check:.12f}, expected={expected_baseline_intensity:.12f} g CO2e/kcal."
        )

    print(
        f"[INFO] production EF accounting: production baseline="
        f"{production_baseline_kg / 1e12:.6f} Gt, EF-controlled baseline="
        f"{controlled_reference / 1e12:.6f} Gt, fixed non-EF baseline="
        f"{(production_baseline_kg - controlled_reference) / 1e12:.6f} Gt"
    )
    print(
        f"[INFO] production EF samples: n={len(out)}, "
        f"range={out['metric_value'].min():.6f}-{out['metric_value'].max():.6f} g CO2e/kcal"
    )
    return out.drop(
        columns=["ef_controlled_baseline_emissions_kg", "ef_controlled_sample_emissions_kg"]
    )


def _aggregate_weighted_metric(weighted_df: pd.DataFrame, kind: str, metric_mode: str) -> pd.DataFrame:
    sub = weighted_df[weighted_df["kind"].astype(str).str.strip().str.lower() == kind].copy()
    if sub.empty:
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])

    if metric_mode == "ratio":
        sub["metric_value"] = _derive_ratio_metric(sub)
    elif metric_mode == "absolute":
        if kind == "emission_factor":
            raise ValueError(
                "Absolute emission_factor must use _build_production_ef_intensity_metric() "
                "so the production-emissions numerator and single gross-production-kcal "
                "denominator are preserved."
            )
        sub["metric_value"] = _derive_absolute_metric(sub)
    else:
        raise ValueError(f"Unknown metric_mode: {metric_mode}")
    sub["row_weight"] = _resolve_row_weight(sub)
    sub = sub.dropna(subset=["metric_value"])
    if sub.empty:
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])

    rows: List[Dict[str, float]] = []
    for (scenario_id, sample_id), g in sub.groupby(["scenario_id", "sample_id"], sort=False):
        vals = g["metric_value"].to_numpy(dtype=float)
        weights = g["row_weight"].to_numpy(dtype=float)
        valid = np.isfinite(vals)
        vals = vals[valid]
        weights = weights[valid]
        if vals.size == 0:
            continue
        weights = np.where(np.isfinite(weights) & (weights > 0), weights, 1.0)
        metric = float(np.average(vals, weights=weights)) if float(weights.sum()) > 0 else float(np.nanmean(vals))
        rows.append(
            {
                "scenario_id": str(scenario_id),
                "sample_id": int(sample_id),
                "metric_value": metric,
            }
        )
    return pd.DataFrame(rows)


def _aggregate_weighted_ratio(weighted_df: pd.DataFrame, kind: str) -> pd.DataFrame:
    return _aggregate_weighted_metric(weighted_df, kind, "ratio")


def _build_metric_samples(
    panel: str,
    weighted_df: pd.DataFrame,
    emissions_df: pd.DataFrame,
    human_diet_ruminant_df: pd.DataFrame,
    ef_system_baseline: Optional[Dict[str, object]] = None,
    final_food_energy_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    spec = _active_panel_spec(panel)
    rank_mode = str(spec["rank_metric_mode"])
    if panel == "luc_land_intensity":
        metric_df = _build_luc_land_intensity_metric()
        if metric_df.empty:
            raise RuntimeError("No LUC land-use intensity rows available.")
    elif panel == "yield" and rank_mode == "absolute":
        if final_food_energy_df is None:
            raise RuntimeError("2080 final-food energy was not loaded for the yield panel.")
        metric_df = _build_yield_land_productivity_metric(final_food_energy_df)
        if metric_df.empty:
            raise RuntimeError("No 2080 final-food land-productivity rows available.")
    elif panel == "emission_factor" and rank_mode == "absolute":
        if ef_system_baseline is None:
            raise RuntimeError("Production EF baseline inputs were not loaded.")
        metric_df = _build_production_ef_intensity_metric(
            weighted_df,
            ef_system_baseline,
        )
        if metric_df.empty:
            raise RuntimeError("No crop/livestock production EF rows available.")
    elif panel == "ruminate_intake" and rank_mode == "absolute":
        if human_diet_ruminant_df.empty:
            raise RuntimeError("No human-diet ruminant kcal-share rows available.")
        metric_df = human_diet_ruminant_df.copy()
        print("[INFO] ruminate_intake metric source: ruminant human-food kcal / total human-food kcal")
    else:
        metric_df = _aggregate_weighted_metric(weighted_df, str(spec["kind"]).lower(), rank_mode)
        if panel == "ruminate_intake" and not metric_df.empty:
            print("[INFO] ruminate_intake metric source: weighted intake ratio")

    if metric_df.empty:
        raise RuntimeError(f"No metric rows available for panel: {panel}")

    metric_df["scenario_id"] = metric_df["scenario_id"].astype(str)
    metric_df["sample_id"] = pd.to_numeric(metric_df["sample_id"], errors="coerce")
    metric_df["metric_value"] = pd.to_numeric(metric_df["metric_value"], errors="coerce")
    metric_df = metric_df.dropna(subset=["scenario_id", "sample_id", "metric_value"]).copy()
    metric_df["sample_id"] = metric_df["sample_id"].astype(int)

    samples = metric_df.merge(emissions_df, on=["scenario_id", "sample_id"], how="inner")
    samples["panel"] = panel
    if str(spec["value_mode"]) == "change_percent":
        samples["metric_display"] = (samples["metric_value"] - 1.0) * 100.0
    elif str(spec["value_mode"]) == "share_percent":
        samples["metric_display"] = samples["metric_value"] * 100.0
    else:
        samples["metric_display"] = samples["metric_value"]
    samples["rank_metric_mode"] = rank_mode
    samples["metric_label"] = str(spec["metric_label"])
    samples["metric_unit"] = str(spec["metric_unit"])
    samples["value_mode"] = str(spec["value_mode"])
    return samples


def _assign_equal_count_quartiles(panel_samples: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    out_frames: List[pd.DataFrame] = []
    summary_rows: List[Dict[str, object]] = []

    for panel, sub in panel_samples.groupby("panel", sort=False):
        spec = _active_panel_spec(str(panel))
        work = sub.dropna(subset=["metric_value", "metric_display", "emissions_2080_gt"]).copy()
        work = work.sort_values("metric_value", kind="mergesort").reset_index(drop=True)
        n = len(work)
        if n == 0:
            continue

        quartile_index = np.minimum((np.arange(n) * 4) // n, 3).astype(int)
        work["quartile_index"] = quartile_index
        work["scenario_key"] = [QUARTILE_KEYS[idx] for idx in quartile_index]
        work["scenario_label"] = work["scenario_key"].map(
            lambda key: f"{QUARTILE_RANGES[key]} {spec['metric_label']} rank"
        )

        for key in QUARTILE_KEYS:
            q = work[work["scenario_key"] == key]
            if q.empty:
                continue
            if bool(CONFIG.get("quality_gate_enabled", True)):
                min_q = int(CONFIG.get("min_quartile_samples", 100) or 0)
                if len(q) < min_q:
                    raise RuntimeError(
                        f"Figure5 quartile quality gate failed for {panel}/{key}: "
                        f"n={len(q)} < {min_q}."
                    )
            summary_rows.append(
                {
                    "panel": panel,
                    "scenario_key": key,
                    "rank_range": QUARTILE_RANGES[key],
                    "n": int(len(q)),
                    "rank_metric_mode": str(q["rank_metric_mode"].iloc[0]) if "rank_metric_mode" in q.columns else spec["rank_metric_mode"],
                    "metric_label": str(q["metric_label"].iloc[0]) if "metric_label" in q.columns else spec["metric_label"],
                    "metric_unit": str(q["metric_unit"].iloc[0]) if "metric_unit" in q.columns else spec["metric_unit"],
                    "value_mode": str(q["value_mode"].iloc[0]) if "value_mode" in q.columns else spec["value_mode"],
                    "metric_min": float(q["metric_display"].min()),
                    "metric_max": float(q["metric_display"].max()),
                    "metric_mean": float(q["metric_display"].mean()),
                    "emissions_2080_gt_mean": float(q["emissions_2080_gt"].mean()),
                    "emissions_2080_gt_median": float(q["emissions_2080_gt"].median()),
                }
            )
        out_frames.append(work)

    if not out_frames:
        raise RuntimeError("No quartile samples could be built.")

    samples = pd.concat(out_frames, ignore_index=True)
    summary = pd.DataFrame(summary_rows)
    return samples, summary


def _build_histogram(panel_samples: pd.DataFrame, x_min: float, x_max: float) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    bins = int(CONFIG.get("histogram_bins", BINS) or BINS)
    if bins <= 0:
        raise ValueError(f"CONFIG['histogram_bins'] must be > 0, got {bins!r}")
    for (panel, key), sub in panel_samples.groupby(["panel", "scenario_key"], sort=False):
        values = pd.to_numeric(sub["emissions_2080_gt"], errors="coerce").dropna().to_numpy(dtype=float)
        if values.size == 0:
            continue
        counts, edges = np.histogram(values, bins=bins, range=(x_min, x_max))
        for idx in range(len(counts)):
            rows.append(
                {
                    "panel": str(panel),
                    "scenario_key": str(key),
                    "bin_left": float(edges[idx]),
                    "bin_right": float(edges[idx + 1]),
                    "count": int(counts[idx]),
                }
            )
    return pd.DataFrame(rows)


def _curve_y_values(counts: np.ndarray) -> np.ndarray:
    y = _smooth_counts(counts.astype(float), SMOOTH_SIGMA_BINS)
    total = float(np.nansum(y))
    if total <= 0 or not np.isfinite(total):
        return y
    return y / total


def _plot_targets(ax: Axes, targets: Sequence[Tuple[str, float]], ymax: float) -> None:
    for label, value in targets:
        color = TARGET_COLORS.get(label, "#666666")
        display_label = "Current GHG (2020)" if label == "Current" else label
        ax.axvline(
            value,
            color=color,
            linewidth=TARGET_LINEWIDTH,
            linestyle=(0, (6, 4)),
            alpha=0.92,
        )
        ax.text(
            value + 0.15,
            ymax * 0.018,
            display_label,
            color=color,
            fontsize=TARGET_LABEL_FONTSIZE - 0.5,
            fontweight="bold",
            fontstyle="italic" if label == "Current" else "normal",
            rotation=90,
            rotation_mode="anchor",
            ha="left",
            va="bottom",
            bbox={
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.78,
                "pad": 0.5,
            },
            zorder=4.0,
        )


def _summary_lookup(summary: pd.DataFrame, panel: str, key: str) -> Optional[pd.Series]:
    sub = summary[(summary["panel"] == panel) & (summary["scenario_key"] == key)]
    if sub.empty:
        return None
    return sub.iloc[0]


def _plot_quartile_panel(
    ax: Axes,
    hist: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    panel: str,
    x_min: float,
    x_max: float,
    targets: Sequence[Tuple[str, float]],
    current_metrics_2020: pd.DataFrame,
) -> None:
    spec = _active_panel_spec(panel)
    panel_df = hist[hist["panel"] == panel].copy()
    if panel_df.empty:
        raise ValueError(f"No histogram data for panel: {panel}")

    panel_df["bin_left"] = pd.to_numeric(panel_df["bin_left"], errors="coerce")
    panel_df["bin_right"] = pd.to_numeric(panel_df["bin_right"], errors="coerce")
    panel_df["count"] = pd.to_numeric(panel_df["count"], errors="coerce").fillna(0.0)
    panel_df = panel_df.dropna(subset=["bin_left", "bin_right"])
    panel_df["x_mid"] = (panel_df["bin_left"] + panel_df["bin_right"]) / 2.0

    ymax = 0.0
    handles = []
    labels = []
    for key in QUARTILE_KEYS:
        sub = panel_df[panel_df["scenario_key"] == key].sort_values("bin_left")
        if sub.empty:
            continue
        x = sub["x_mid"].to_numpy(dtype=float)
        y = _curve_y_values(sub["count"].to_numpy(dtype=float))
        if y.size:
            ymax = max(ymax, float(np.nanmax(y)))

        row = _summary_lookup(summary, panel, key)
        if row is None:
            label = f"{QUARTILE_RANGES[key]}"
        else:
            mean_text = _format_summary_metric(row, spec)
            label = f"{QUARTILE_RANGES[key]}, metric mean {mean_text}"

        quartile_color, quartile_alpha = _quartile_style(panel, key)
        line = ax.plot(
            x,
            y,
            color=quartile_color,
            linewidth=DENSITY_LINEWIDTH,
            alpha=quartile_alpha,
            label=label,
            solid_joinstyle=DENSITY_LINE_JOINSTYLE,
            solid_capstyle=DENSITY_LINE_CAPSTYLE,
        )[0]
        handles.append(line)
        labels.append(label)

        if row is not None and "emissions_2080_gt_mean" in row.index:
            mean_x = pd.to_numeric(row.get("emissions_2080_gt_mean"), errors="coerce")
            if pd.notna(mean_x) and np.isfinite(float(mean_x)):
                ax.axvline(
                    float(mean_x),
                    color=quartile_color,
                    linewidth=MEAN_LINEWIDTH,
                    linestyle="-",
                    alpha=MEAN_LINE_ALPHA,
                    zorder=2.2,
                )

        if y.size:
            idx = int(np.nanargmax(y))
            peak_x = float(x[idx])
            peak_offset_fraction = 0.035
            if panel == "emission_factor":
                peak_offset_fraction = {
                    "q1": 0.035,
                    "q2": 0.035,
                    "q3": 0.020,
                    "q4": 0.100,
                }[key]
            ax.text(
                peak_x,
                float(y[idx]) + max(ymax, 1e-9) * peak_offset_fraction,
                f"{key.upper()} peak {peak_x:.1f} Gt",
                color=quartile_color,
                alpha=quartile_alpha,
                fontsize=LEGEND_FONTSIZE,
                fontweight="bold",
                ha="center",
                va="bottom",
            )

    if ymax <= 0:
        ymax = 1.0
    ax.set_ylim(0, ymax * 1.2)
    _plot_targets(ax, targets, ymax * 1.2)
    current = current_metrics_2020[
        current_metrics_2020["panel"].astype(str).eq(panel)
    ]
    if len(current) != 1:
        raise ValueError(f"Expected one Current 2020 metric row for {panel}, found {len(current)}.")
    current_row = current.iloc[0]
    handles.append(
        Line2D(
            [],
            [],
            color="#333333",
            marker="*",
            markerfacecolor="#333333",
            markeredgecolor="#333333",
            markersize=12,
            linestyle="None",
        )
    )
    labels.append(_current_metric_legend_label(current_row, spec))
    ax.legend(handles=handles, labels=labels, loc="upper right", frameon=False, fontsize=LEGEND_FONTSIZE)

    ax.set_xlim(x_min, x_max)
    ax.set_title(str(spec["title"]), fontsize=PANEL_TITLE_FONTSIZE, fontweight="bold", loc="left", pad=6)
    ax.set_ylabel("Probability per bin", fontsize=AXIS_LABEL_FONTSIZE, fontweight="bold", labelpad=AXIS_LABELPAD)
    ax.tick_params(
        axis="both",
        which="both",
        labelsize=TICK_LABEL_FONTSIZE,
        width=TICK_WIDTH,
        length=TICK_LENGTH,
    )
    for spine in ax.spines.values():
        spine.set_linewidth(SPINE_LINEWIDTH)


def _current_metric_legend_label(
    current_row: pd.Series,
    spec: Dict[str, object],
) -> str:
    current_text = _format_metric_with_unit(float(current_row["metric_display"]), spec)
    return f"Current 2020 metric: {current_text}"


def _build_yield_land_productivity_audit(panel_samples: pd.DataFrame) -> pd.DataFrame:
    yield_rows = panel_samples[panel_samples["panel"].astype(str).eq("yield")].copy()
    if yield_rows.empty:
        return pd.DataFrame()
    required = {
        "scenario_id",
        "sample_id",
        "final_food_year",
        "final_food_kcal",
        "land_year",
        "crop_pasture_land_ha",
        "metric_value",
    }
    missing = sorted(required - set(yield_rows.columns))
    if missing:
        raise ValueError(f"Yield panel samples missing audit columns: {', '.join(missing)}")

    final_food_kcal = pd.to_numeric(yield_rows["final_food_kcal"], errors="coerce")
    land_ha = pd.to_numeric(yield_rows["crop_pasture_land_ha"], errors="coerce")
    metric = pd.to_numeric(yield_rows["metric_value"], errors="coerce")
    recomputed = final_food_kcal / 1e6 / land_ha
    yield_rows["metric_recomputed_mkcal_per_ha"] = recomputed
    yield_rows["formula_abs_error"] = (metric - recomputed).abs()
    max_error = float(yield_rows["formula_abs_error"].max())
    if not np.isfinite(max_error) or max_error > 1e-10:
        raise ValueError(f"Yield land-productivity formula audit failed: max_error={max_error}")
    if not bool(pd.to_numeric(yield_rows["final_food_year"], errors="coerce").eq(YEAR).all()):
        raise ValueError(f"Yield final-food numerator contains non-{YEAR} rows.")
    if not bool(pd.to_numeric(yield_rows["land_year"], errors="coerce").eq(YEAR).all()):
        raise ValueError(f"Yield land denominator contains non-{YEAR} rows.")

    preferred_cols = [
        "scenario_id",
        "sample_id",
        "scenario_key",
        "rank_range",
        "final_food_year",
        "final_food_kcal",
        "final_food_energy_source",
        "profile_cap_pct",
        "profile_column",
        "cap_source_rows",
        "nutrition_profile_path",
        "population_path",
        "land_year",
        "land_source",
        "crop_pasture_land_ha",
        "metric_value",
        "metric_recomputed_mkcal_per_ha",
        "formula_abs_error",
        "metric_formula",
    ]
    out = yield_rows[[col for col in preferred_cols if col in yield_rows.columns]].copy()
    out = out.rename(columns={"metric_value": "land_productivity_mkcal_per_ha"})
    return out.sort_values(["sample_id", "scenario_id"], kind="stable").reset_index(drop=True)


def _build_ruminant_human_diet_share_audit(panel_samples: pd.DataFrame) -> pd.DataFrame:
    ruminant_rows = panel_samples[
        panel_samples["panel"].astype(str).eq("ruminate_intake")
    ].copy()
    if ruminant_rows.empty:
        return pd.DataFrame()
    required = {
        "scenario_id",
        "sample_id",
        "year",
        "final_food_kcal",
        "ruminant_food_kcal",
        "metric_value",
    }
    missing = sorted(required - set(ruminant_rows.columns))
    if missing:
        raise ValueError(
            "Human-diet ruminant-share panel samples missing audit columns: "
            + ", ".join(missing)
        )

    year = pd.to_numeric(ruminant_rows["year"], errors="coerce")
    total_food = pd.to_numeric(ruminant_rows["final_food_kcal"], errors="coerce")
    ruminant_food = pd.to_numeric(ruminant_rows["ruminant_food_kcal"], errors="coerce")
    metric = pd.to_numeric(ruminant_rows["metric_value"], errors="coerce")
    if not bool(year.eq(YEAR).all()):
        raise ValueError(f"Human-diet ruminant-share numerator contains non-{YEAR} rows.")
    if bool((total_food <= 0).any()):
        raise ValueError("Human-diet ruminant-share denominator contains non-positive food kcal.")
    if bool(((ruminant_food < 0) | (ruminant_food > total_food)).any()):
        raise ValueError("Human-diet ruminant kcal must be between zero and total food kcal.")
    duplicate = ruminant_rows.duplicated(["scenario_id", "sample_id"], keep=False)
    if bool(duplicate.any()):
        raise ValueError("Human-diet ruminant-share audit has duplicate sample keys.")

    recomputed = ruminant_food / total_food
    ruminant_rows["metric_recomputed_share"] = recomputed
    ruminant_rows["formula_abs_error"] = (metric - recomputed).abs()
    max_error = float(ruminant_rows["formula_abs_error"].max())
    if not np.isfinite(max_error) or max_error > 1e-12:
        raise ValueError(
            f"Human-diet ruminant-share formula audit failed: max_error={max_error}"
        )

    preferred_cols = [
        "scenario_id",
        "sample_id",
        "scenario_key",
        "rank_range",
        "year",
        "final_food_kcal",
        "ruminant_food_kcal",
        "final_food_energy_source",
        "profile_cap_pct",
        "profile_column",
        "cap_source_rows",
        "nutrition_profile_path",
        "population_path",
        "metric_value",
        "metric_display",
        "metric_recomputed_share",
        "formula_abs_error",
        "metric_formula",
    ]
    out = ruminant_rows[
        [col for col in preferred_cols if col in ruminant_rows.columns]
    ].copy()
    out = out.rename(
        columns={
            "year": "food_year",
            "metric_value": "human_diet_ruminant_kcal_share",
            "metric_display": "human_diet_ruminant_kcal_share_percent",
        }
    )
    return out.sort_values(["sample_id", "scenario_id"], kind="stable").reset_index(
        drop=True
    )


def _build_production_ef_intensity_audit(
    panel_samples: pd.DataFrame,
    baseline: Optional[Dict[str, object]],
) -> pd.DataFrame:
    if baseline is None:
        return pd.DataFrame()
    ef = panel_samples[panel_samples["panel"].astype(str).eq("emission_factor")].copy()
    if ef.empty:
        return pd.DataFrame()
    required = {
        "ef_controlled_production_baseline_emissions_gt",
        "ef_controlled_production_sample_emissions_gt",
        "non_ef_production_baseline_emissions_gt",
        "production_emissions_sample_gt",
        "gross_production_energy_2020_kcal",
        "metric_value",
    }
    missing = sorted(required - set(ef.columns))
    if missing:
        raise ValueError(
            f"Production EF panel samples missing audit columns: {', '.join(missing)}"
        )

    recomputed = (
        pd.to_numeric(ef["production_emissions_sample_gt"], errors="coerce")
        * 1e15
        / pd.to_numeric(ef["gross_production_energy_2020_kcal"], errors="coerce")
    )
    formula_error = (
        pd.to_numeric(ef["metric_value"], errors="coerce") - recomputed
    ).abs()
    max_formula_error = float(formula_error.max())
    if not np.isfinite(max_formula_error) or max_formula_error > 1e-12:
        raise ValueError(
            f"Production EF formula audit failed: max_error={max_formula_error}"
        )

    row = {
        "baseline_case": baseline["baseline_case"],
        "baseline_year": baseline["baseline_year"],
        "production_emissions_path": baseline["emissions_path"],
        "production_summary_path": baseline["production_summary_path"],
        "production_dictionary_path": baseline["production_dictionary_path"],
        "production_processes": baseline["production_processes"],
        "production_process_count": len(PRODUCTION_EF_PROCESSES),
        "production_emissions_rows": baseline["production_emissions_rows"],
        "production_rows": baseline["production_rows"],
        "production_commodity_count": baseline["production_commodity_count"],
        "production_baseline_emissions_gt": baseline[
            "production_baseline_emissions_gt"
        ],
        "gross_production_energy_2020_kcal": baseline[
            "gross_production_energy_2020_kcal"
        ],
        "production_baseline_intensity_g_per_kcal": baseline[
            "production_baseline_intensity_g_per_kcal"
        ],
        "ef_controlled_production_baseline_emissions_gt": float(
            pd.to_numeric(
                ef["ef_controlled_production_baseline_emissions_gt"],
                errors="coerce",
            ).median()
        ),
        "non_ef_production_baseline_emissions_gt": float(
            pd.to_numeric(
                ef["non_ef_production_baseline_emissions_gt"], errors="coerce"
            ).median()
        ),
        "sample_count": int(len(ef)),
        "ef_controlled_production_sample_emissions_gt_min": float(
            pd.to_numeric(
                ef["ef_controlled_production_sample_emissions_gt"], errors="coerce"
            ).min()
        ),
        "ef_controlled_production_sample_emissions_gt_max": float(
            pd.to_numeric(
                ef["ef_controlled_production_sample_emissions_gt"], errors="coerce"
            ).max()
        ),
        "production_emissions_sample_gt_min": float(
            pd.to_numeric(ef["production_emissions_sample_gt"], errors="coerce").min()
        ),
        "production_emissions_sample_gt_max": float(
            pd.to_numeric(ef["production_emissions_sample_gt"], errors="coerce").max()
        ),
        "production_intensity_sample_g_per_kcal_min": float(
            pd.to_numeric(ef["metric_value"], errors="coerce").min()
        ),
        "production_intensity_sample_g_per_kcal_mean": float(
            pd.to_numeric(ef["metric_value"], errors="coerce").mean()
        ),
        "production_intensity_sample_g_per_kcal_max": float(
            pd.to_numeric(ef["metric_value"], errors="coerce").max()
        ),
        "formula_max_abs_error": max_formula_error,
        "formula": (
            "(production_baseline_emissions_excluding_LUC "
            "- ef_controlled_production_baseline_emissions "
            "+ ef_controlled_production_sample_emissions) "
            "/ gross_crop_livestock_production_kcal_2020"
        ),
        "excluded_processes": (
            "all LUC processes | Drained organic soils | Peatlands fire | "
            "Savanna fire | Fish farming"
        ),
    }
    return pd.DataFrame([row])


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build manuscript Figure 4e-h quartile-distribution panels."
    )
    parser.add_argument(
        "--merged-dir",
        type=Path,
        default=None,
        help="Merged S5_4 directory. Default: <NZF_OUTPUT_DIR>/MC_Full_Variables/merged.",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=None,
        help="Output directory for plot data and figures. Default: <NZF_OUTPUT_DIR>/Plot/Fig5.",
    )
    parser.add_argument(
        "--targets-csv",
        type=Path,
        default=None,
        help="Optional target-line CSV; built-in manuscript defaults are used when absent.",
    )
    return parser


def _apply_path_overrides(args: argparse.Namespace) -> None:
    global FIG5_DIR, TARGETS_PATH, MC_MERGED_DIR
    global FAST_SUMMARY_PATH, PROCESS_CO2EQ_PATH, WEIGHTED_ELEMENTS_PATH
    global STATUS_PATH, MC_DRAWS_PATH, FINAL_FOOD_ENERGY_PATH, LAND_BALANCE_PATH

    if args.merged_dir is not None:
        MC_MERGED_DIR = Path(args.merged_dir).expanduser().resolve()
        FAST_SUMMARY_PATH = MC_MERGED_DIR / "mc_success_fast_summary.csv"
        PROCESS_CO2EQ_PATH = MC_MERGED_DIR / "mc_success_global_process_co2eq.csv"
        WEIGHTED_ELEMENTS_PATH = MC_MERGED_DIR / "mc_success_weighted_elements.csv"
        STATUS_PATH = MC_MERGED_DIR / "mc_sample_status.csv"
        MC_DRAWS_PATH = MC_MERGED_DIR / "mc_draws_long.csv"
        FINAL_FOOD_ENERGY_PATH = MC_MERGED_DIR / "mc_success_final_food_energy.csv"
        LAND_BALANCE_PATH = MC_MERGED_DIR / "mc_success_crop_pasture_land_balance.csv"
    if args.figure_dir is not None:
        FIG5_DIR = Path(args.figure_dir).expanduser().resolve()
        TARGETS_PATH = FIG5_DIR / "targets.csv"
    if args.targets_csv is not None:
        TARGETS_PATH = Path(args.targets_csv).expanduser().resolve()


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _build_arg_parser().parse_args(argv)
    _apply_path_overrides(args)
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    _ensure_dir(FIG5_DIR)

    targets = _load_targets()
    emissions_df = _load_mc_success_emissions()
    emissions_df, configured_x_range = _filter_emissions_to_configured_range(emissions_df)
    weighted_df = _load_weighted_elements()
    final_food_energy_df = _load_final_food_energy()
    human_diet_ruminant_df = _build_human_diet_ruminant_share_metric(
        final_food_energy_df
    )
    ef_system_baseline = _load_ef_system_baseline()
    current_metrics_2020 = _build_current_metrics_2020(
        ef_system_baseline,
        final_food_energy_df,
    )

    panel_frames: List[pd.DataFrame] = []
    active_panels: List[str] = []
    for panel in PANEL_SPECS:
        try:
            panel_df = _build_metric_samples(
                panel,
                weighted_df,
                emissions_df,
                human_diet_ruminant_df,
                ef_system_baseline=ef_system_baseline,
                final_food_energy_df=final_food_energy_df,
            )
        except RuntimeError as exc:
            if panel == "luc_land_intensity":
                print(f"[WARN] skip {panel}: {exc}")
                continue
            raise
        if panel_df.empty:
            if panel == "luc_land_intensity":
                print(f"[WARN] skip {panel}: no rows")
                continue
            raise RuntimeError(f"No panel rows available for {panel}")
        panel_frames.append(panel_df)
        active_panels.append(panel)

    if not panel_frames:
        raise RuntimeError("No panel sample rows could be built.")
    panel_samples_raw = pd.concat(panel_frames, ignore_index=True)
    panel_samples, quartile_summary = _assign_equal_count_quartiles(panel_samples_raw)

    if configured_x_range is not None:
        x_min, x_max = configured_x_range
    else:
        x_values = pd.concat(
            [
                pd.to_numeric(panel_samples["emissions_2080_gt"], errors="coerce"),
                pd.Series([val for _, val in targets], dtype=float),
            ],
            ignore_index=True,
        ).dropna()
        if x_values.empty:
            x_min, x_max = DEFAULT_X_MIN, DEFAULT_X_MAX
        else:
            x_min = min(DEFAULT_X_MIN, float(np.floor(x_values.min())))
            x_max = max(DEFAULT_X_MAX, float(np.ceil(x_values.max())))

    hist = _build_histogram(panel_samples, x_min=x_min, x_max=x_max)

    panel_samples_path = FIG5_DIR / "panel_samples_quartile_v2.csv"
    hist_path = FIG5_DIR / "histogram_quartile_v2.csv"
    summary_path = FIG5_DIR / "quartile_summary_v2.csv"
    yield_audit_path = FIG5_DIR / "yield_land_productivity_audit_v2.csv"
    ruminant_audit_path = FIG5_DIR / "ruminant_human_diet_share_audit_v2.csv"
    current_metrics_path = FIG5_DIR / "current_metrics_2020_v2.csv"
    ef_audit_path = FIG5_DIR / "ef_production_intensity_audit_v2.csv"
    panel_samples.to_csv(panel_samples_path, index=False, encoding="utf-8-sig")
    hist.to_csv(hist_path, index=False, encoding="utf-8-sig")
    quartile_summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    yield_audit = _build_yield_land_productivity_audit(panel_samples)
    if not yield_audit.empty:
        yield_audit.to_csv(yield_audit_path, index=False, encoding="utf-8-sig")
    ruminant_audit = _build_ruminant_human_diet_share_audit(panel_samples)
    if not ruminant_audit.empty:
        ruminant_audit.to_csv(ruminant_audit_path, index=False, encoding="utf-8-sig")
    current_metrics_2020.to_csv(current_metrics_path, index=False, encoding="utf-8-sig")
    ef_audit = _build_production_ef_intensity_audit(
        panel_samples,
        ef_system_baseline,
    )
    if not ef_audit.empty:
        ef_audit.to_csv(ef_audit_path, index=False, encoding="utf-8-sig")

    print(f"[DONE] panel samples: {panel_samples_path}")
    print(f"[DONE] histogram: {hist_path}")
    print(f"[DONE] quartile summary: {summary_path}")
    if not yield_audit.empty:
        print(f"[DONE] yield land-productivity audit: {yield_audit_path}")
    if not ruminant_audit.empty:
        print(f"[DONE] human-diet ruminant-share audit: {ruminant_audit_path}")
    print(f"[DONE] Current 2020 metrics: {current_metrics_path}")
    if not ef_audit.empty:
        print(f"[DONE] production EF audit: {ef_audit_path}")

    for panel in active_panels:
        spec = _active_panel_spec(panel)
        fig, ax = plt.subplots(1, 1, figsize=(FIG_WIDTH, FIG_HEIGHT))
        _plot_quartile_panel(
            ax,
            hist,
            quartile_summary,
            panel=panel,
            x_min=x_min,
            x_max=x_max,
            targets=targets,
            current_metrics_2020=current_metrics_2020,
        )
        ax.set_xlabel(
            "GHG emission in 2080 (Gt CO$_2$eq/yr)",
            fontsize=AXIS_LABEL_FONTSIZE,
            fontweight="bold",
            labelpad=AXIS_LABELPAD,
        )
        fig.tight_layout()

        png_path = FIG5_DIR / f"{spec['file_stem']}.png"
        svg_path = FIG5_DIR / f"{spec['file_stem']}.svg"
        fig.savefig(png_path, dpi=FIG_DPI)
        fig.savefig(svg_path)
        plt.close(fig)

        print(f"[DONE] {png_path}")
        print(f"[DONE] {svg_path}")

    for panel in active_panels:
        spec = _active_panel_spec(panel)
        sub = quartile_summary[quartile_summary["panel"] == panel]
        parts = []
        for key in QUARTILE_KEYS:
            row = _summary_lookup(sub, panel, key)
            if row is None:
                continue
            mean_text = _format_summary_metric(row, spec)
            parts.append(f"{key.upper()} n={int(row['n'])}, mean={mean_text}")
        print(f"[INFO] {panel}: " + "; ".join(parts))


if __name__ == "__main__":
    main()
