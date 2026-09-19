# -*- coding: utf-8 -*-
"""
Plot Figure 9 regression-based importance stacks.

This is intentionally separate from v2:
- v2 plots Region/Item/Process structure shares from group_emissions / total_emissions.
- v3 plots regression importance.

Definitions:
- Region/Item/Process: target-local weighted regression of total_emissions_gt on
  sample-level group emissions_gt from S5_5.
- Region/Item secondary labels: configurable Process annotation method; see
  CONFIG["dominant_process_mode"].
- Strategy: S5_0 target-local weighted regression importance from
  importance_by_variable.csv.

Inputs:
- <results>/MC_Region_Item_Process_Importance/merged_structure/
  mc_success_structure_emissions.csv
- <results>/MC_Region_Item_Process_Importance/merged_structure/
  mc_success_structure_totals.csv
- <results>/MC_Sensitivity/summary/importance_by_variable.csv
  fallback: <results>/MC_Sensitivity/summary/importance_detail.csv

Outputs:
- <results>/Plot/Fig9/Figure9_regression_importance_v3.xlsx
- <results>/Plot/Fig9/Figure9_structure_importance_region_regression_v3.png/.svg
- <results>/Plot/Fig9/Figure9_structure_importance_item_regression_v3.png/.svg
- <results>/Plot/Fig9/Figure9_structure_importance_process_regression_v3.png/.svg
- <results>/Plot/Fig9/Figure9_structure_importance_strategy_regression_v3.png/.svg
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors as mcolors
from scipy.interpolate import PchipInterpolator
from scipy.signal import savgol_filter

from config_paths import get_results_base

try:
    from SP_M4f_Figure_structure_importance_targetrange_v2 import (
        IN_PLOT_LABELS as LEGACY_IN_PLOT_LABELS,
        LABEL_X_POSITIONS as LEGACY_LABEL_X_POSITIONS,
        _sheet_palette as legacy_sheet_palette,
    )
except Exception:
    LEGACY_IN_PLOT_LABELS = {}
    LEGACY_LABEL_X_POSITIONS = {}
    legacy_sheet_palette = None


RESULTS_BASE = Path(get_results_base())
S5_0_SUMMARY_DIR = RESULTS_BASE / "MC_Sensitivity" / "summary"
STRUCTURE_DIR = RESULTS_BASE / "MC_Region_Item_Process_Importance" / "merged_structure"
FIG_DIR = RESULTS_BASE / "Plot" / "Fig9"

GROUPINGS = ("Region", "Item", "Process")
ALL_PANELS = ("Region", "Item", "Process", "Strategy")

CONFIG = {
    # 0 recalculates regression importance data and then plots.
    # 1 reads the existing Figure9_regression_importance_v3.xlsx and only plots.
    "plot_only": 1,
    # Visible plotting range. Edit here, or override with --x-min/--x-max.
    "plot_emission_range_gt": (-3.0, 60.0),
    # Regression target grid. None means use plot_emission_range_gt.
    "target_range_gt": None,
    "target_step_gt": 1.0,
    "regression_sigma_gt": 2.0,
    "min_effective_n_samples": 50.0,
    "current_afolu_ghg_gt": 12.9,
    "stack_order_target_emis_gt": -3.0,
    "top_n": {
        "Region": 10,
        "Item": 10,
        "Process": 10,
    },
    "use_smoothed_for_plot": True,
    "smooth_plot": True,
    "smooth_method": "savgol",
    "smooth_window": 21,
    "smooth_polyorder": 2,
    "smooth_iterations": 2,
    # Apply stronger smoothing to the Strategy panel at plotting time.
    # This also smooths an existing Strategy_pct_smoothed sheet in plot-only mode.
    "strategy_plot_resmooth": True,
    "strategy_plot_smooth_window": 41,
    "strategy_plot_smooth_polyorder": 2,
    "strategy_plot_smooth_iterations": 2,
    "plot_interpolation_points": 500,
    "structure_chunk_size": 500_000,
    "min_required_samples": 80,
    "dpi": 800,
    "fig_width": 7.2,
    "fig_height": 5.5,
    "inplot_label_fontsize": 8.8,
    "inplot_label_min_thickness_pct": 2.0,
    "inplot_label_edge_padding_frac": 0.09,
    # Region/Item layers retain their regression importance. The smaller
    # secondary label method is selected here:
    # - parent_max_emission_share: largest positive Process share in the MC
    #   sample where that Region/Item reaches maximum net emissions.
    # - baseline_2020_share: largest positive Process share in 2020.
    # - regression_contribution_max: largest within-parent Process regression
    #   contribution at the highest valid emission level.
    # - regression_contribution_average: largest mean within-parent Process
    #   regression contribution across all valid emission levels.
    "annotate_dominant_process": True,
    "dominant_process_mode": "regression_contribution_average",
    "dominant_process_fontsize": 6.4,
    "dominant_process_min_layer_thickness_pct": 4.0,
    "dominant_process_max_target_gap_gt": None,
}

STRATEGY_DISPLAY_ORDER = [
    "Improve yield rate",
    "Improve feed efficiency",
    "Improve fertilizer efficiency",
    "Reduce waste",
    "Reduce Ruminate",
    "Manure management",
    "Crop residue management",
    "Emission intensity",
    "Land carbon price",
]

STRATEGY_COLORS = {
    "Reduce Ruminate": "#911c43",
    "Improve yield rate": "#e4754f",
    "Manure management": "#0868ac",
    "Improve feed efficiency": "#fdb75cf1",
    "Enteric fermentation management": "#5c509d",
    "Improve fertilizer efficiency": "#ccebc5",
    "Rice cultivation": "#7bccc4",
    "Rice management": "#7bccc4",
    "Crop residue management": "#2bafd7",
    "Reduce waste": "#fb9a99",
    "Emission intensity": "#456842",
    "Land carbon price": "#4d4d4d",
    "Other": "#999999",
}

PROCESS_COLOR_OVERRIDES = {
    "Forest": "#63965e",
}

DOMINANT_PROCESS_PANELS = ("Region", "Item")

DOMINANT_PROCESS_MODES = (
    "parent_max_emission_share",
    "baseline_2020_share",
    "regression_contribution_max",
    "regression_contribution_average",
)

DOMINANT_PROCESS_SPECS = {
    "Region": {
        "grouping": "Region-Process",
        "parent_col": "group_1",
        "process_col": "group_2",
    },
    "Item": {
        "grouping": "Process-Item",
        "parent_col": "group_2",
        "process_col": "group_1",
    },
}

BASELINE_2020_PARENT_ALIASES = {
    "Item": {
        "Forestland": "Existing forestland",
    },
}

DOMINANT_PROCESS_LABELS = {
    "Manure management and application": "Manure management",
}

STRATEGY_PARAMETER_NAME_MAP = {
    "yield_rate": "Improve yield rate",
    "yield_multiplier": "Improve yield rate",
    "feed_efficiency": "Improve feed efficiency",
    "feed_intensity": "Improve feed efficiency",
    "fertilizer_rate": "Improve fertilizer efficiency",
    "losses_ratio": "Reduce waste",
    "waste_reduction": "Reduce waste",
    "losses_rate": "Reduce waste",
    "ruminant_reduction": "Reduce Ruminate",
    "ruminant_intake_ratio": "Reduce Ruminate",
    "manure_management_ratio": "Manure management",
    "crop_soil_management_ratio": "Crop residue management",
    "crop_management": "Crop residue management",
    "emission_factor": "Emission intensity",
    "emission_control": "Emission intensity",
    "land_carbon_price": "Land carbon price",
    "land carbon price": "Land carbon price",
}

STRATEGY_LABELS = {
    "Improve yield rate": "Yield rate",
    "Improve feed efficiency": "Feed efficiency",
    "Improve fertilizer efficiency": "Nitrogen efficiency",
    "Reduce waste": "Waste rate",
    "Reduce Ruminate": "Ruminant intake",
    "Manure management": "Manure management",
    "Crop residue management": "Crop residue+soil management",
    "Emission intensity": "Emission intensity",
    "Land carbon price": "Land carbon price",
}

STRATEGY_LABEL_X_POSITIONS = {
    "Improve yield rate": 24.0,
    "Emission intensity": 15.0,
    "Reduce Ruminate": 24.5,
    "Reduce waste": 7.0,
    "Crop residue management": 9.0,
    "Manure management": 18.0,
    "Improve feed efficiency": 13.0,
    "Improve fertilizer efficiency": 23.0,
    "Land carbon price": 19.0,
}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot Figure 9 regression-based Region/Item/Process/Strategy importance."
    )
    parser.add_argument("--summary-dir", type=str, default=None, help="S5_0 summary directory.")
    parser.add_argument("--structure-dir", type=str, default=None, help="S5_5 merged_structure directory.")
    parser.add_argument("--fig-dir", type=str, default=None)
    parser.add_argument("--x-min", type=float, default=None)
    parser.add_argument("--x-max", type=float, default=None)
    parser.add_argument("--target-min", type=float, default=None)
    parser.add_argument("--target-max", type=float, default=None)
    parser.add_argument("--target-step", type=float, default=None)
    parser.add_argument("--sigma", type=float, default=None)
    parser.add_argument("--min-ess", type=float, default=None)
    parser.add_argument("--no-smooth", action="store_true", default=False)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--plot-only",
        dest="plot_only",
        action="store_true",
        help="Plot from the existing regression-importance workbook.",
    )
    mode.add_argument(
        "--rebuild-regression",
        dest="plot_only",
        action="store_false",
        help="Recompute regression importance from merged S5_0/S5_5 outputs before plotting.",
    )
    parser.set_defaults(plot_only=None)
    return parser


def _resolve_paths(args: argparse.Namespace) -> Tuple[Path, Path, Path]:
    summary_dir = Path(args.summary_dir) if args.summary_dir else S5_0_SUMMARY_DIR
    structure_dir = Path(args.structure_dir) if args.structure_dir else STRUCTURE_DIR
    fig_dir = Path(args.fig_dir) if args.fig_dir else FIG_DIR
    fig_dir.mkdir(parents=True, exist_ok=True)
    return summary_dir, structure_dir, fig_dir


def _plot_range() -> Tuple[float, float]:
    lo, hi = CONFIG["plot_emission_range_gt"]
    lo_f = float(lo)
    hi_f = float(hi)
    if hi_f <= lo_f:
        raise ValueError("CONFIG['plot_emission_range_gt'] max must be greater than min.")
    return lo_f, hi_f


def _target_range() -> Tuple[float, float]:
    raw = CONFIG.get("target_range_gt")
    if raw is None:
        return _plot_range()
    lo, hi = raw
    lo_f = float(lo)
    hi_f = float(hi)
    if hi_f <= lo_f:
        raise ValueError("CONFIG['target_range_gt'] max must be greater than min.")
    return lo_f, hi_f


def _target_grid() -> List[float]:
    lo, hi = _target_range()
    step = float(CONFIG.get("target_step_gt", 1.0) or 1.0)
    if not np.isfinite(step) or step <= 0:
        raise ValueError("CONFIG['target_step_gt'] must be positive.")
    targets: List[float] = []
    cur = lo
    eps = abs(step) * 1e-9
    while cur <= hi + eps:
        targets.append(round(float(cur), 10))
        cur += step
    if not targets or not np.isclose(targets[-1], hi):
        targets.append(round(float(hi), 10))
    return targets


def _normalize_strategy_parameter(raw: object) -> str:
    text = str(raw or "").strip()
    key = text.lower()
    if "|" in key:
        key = key.split("|", 1)[0]
    return STRATEGY_PARAMETER_NAME_MAP.get(key, text)


def _clean_structure_label(group_key: object, group_1: object) -> str:
    label = str(group_1 or "").strip()
    if label and label.lower() != "nan":
        return label
    raw = str(group_key or "").strip()
    if "=" in raw:
        return raw.split("=", 1)[1].strip()
    return raw


def _load_run_meta(summary_dir: Path, structure_dir: Path) -> Dict[str, object]:
    meta: Dict[str, object] = {}
    for prefix, path in (
        ("s5_0", summary_dir / "run_meta.csv"),
        ("s5_5", structure_dir / "run_meta.csv"),
    ):
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
            if not df.empty:
                for key, value in df.iloc[0].to_dict().items():
                    if pd.notna(value):
                        meta[f"{prefix}.{key}"] = value
        except Exception:
            continue
    return meta


def _load_structure_totals(structure_dir: Path) -> pd.DataFrame:
    path = structure_dir / "mc_success_structure_totals.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing structure totals file: {path}")
    df = pd.read_csv(path, usecols=["scenario_id", "sample_id", "total_emissions_gt"])
    df.columns = [str(c).strip() for c in df.columns]
    df["scenario_id"] = df["scenario_id"].astype(str)
    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    df["total_emissions_gt"] = pd.to_numeric(df["total_emissions_gt"], errors="coerce")
    df = df.dropna(subset=["scenario_id", "sample_id", "total_emissions_gt"]).copy()
    df["sample_id"] = df["sample_id"].astype(int)
    df = df.drop_duplicates(subset=["scenario_id", "sample_id"], keep="last").reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No valid rows in {path}.")
    return df


def _load_structure_matrices(structure_dir: Path) -> Dict[str, pd.DataFrame]:
    path = structure_dir / "mc_success_structure_emissions.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing structure emissions file: {path}")
    usecols = ["scenario_id", "sample_id", "grouping", "group_key", "group_1", "emissions_gt"]
    chunksize = int(CONFIG.get("structure_chunk_size", 500_000) or 500_000)
    parts: Dict[str, List[pd.DataFrame]] = {grouping: [] for grouping in GROUPINGS}

    for idx, chunk in enumerate(pd.read_csv(path, usecols=usecols, chunksize=chunksize), start=1):
        chunk.columns = [str(c).strip() for c in chunk.columns]
        chunk = chunk[chunk["grouping"].isin(GROUPINGS)].copy()
        if chunk.empty:
            continue
        chunk["scenario_id"] = chunk["scenario_id"].astype(str)
        chunk["sample_id"] = pd.to_numeric(chunk["sample_id"], errors="coerce")
        chunk["emissions_gt"] = pd.to_numeric(chunk["emissions_gt"], errors="coerce")
        chunk = chunk.dropna(subset=["scenario_id", "sample_id", "grouping", "emissions_gt"])
        if chunk.empty:
            continue
        chunk["sample_id"] = chunk["sample_id"].astype(int)
        chunk["label"] = [
            _clean_structure_label(group_key, group_1)
            for group_key, group_1 in zip(chunk["group_key"], chunk["group_1"])
        ]
        chunk = chunk[chunk["label"].astype(str).str.strip() != ""].copy()
        if chunk.empty:
            continue
        grouped = (
            chunk.groupby(["scenario_id", "sample_id", "grouping", "label"], as_index=False)["emissions_gt"]
            .sum()
        )
        for grouping, sub in grouped.groupby("grouping", sort=False):
            if grouping in parts and not sub.empty:
                parts[grouping].append(sub[["scenario_id", "sample_id", "label", "emissions_gt"]].copy())
        if idx == 1 or idx % 20 == 0:
            counts = {key: sum(len(p) for p in value) for key, value in parts.items()}
            print(f"[SP_M4f_v3] read structure chunk {idx}; aggregated rows={counts}")

    matrices: Dict[str, pd.DataFrame] = {}
    for grouping in GROUPINGS:
        if not parts[grouping]:
            raise ValueError(f"No structure rows found for grouping {grouping}.")
        long = pd.concat(parts[grouping], ignore_index=True)
        long = (
            long.groupby(["scenario_id", "sample_id", "label"], as_index=False)["emissions_gt"]
            .sum()
        )
        wide = (
            long.pivot_table(
                index=["scenario_id", "sample_id"],
                columns="label",
                values="emissions_gt",
                aggfunc="sum",
                fill_value=0.0,
            )
            .reset_index()
        )
        wide.columns = [str(c) for c in wide.columns]
        matrices[grouping] = wide
        print(
            f"[SP_M4f_v3] built {grouping} regression matrix: "
            f"{len(wide)} samples x {max(0, len(wide.columns) - 2)} groups."
        )
    return matrices


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    denom = float(np.sum(weights))
    if denom <= 0:
        return np.full(values.shape[1], np.nan)
    return np.sum(values * weights[:, None], axis=0) / denom


def _weighted_standardize(values: np.ndarray, weights: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mean = _weighted_mean(values, weights)
    var = _weighted_mean((values - mean) ** 2, weights)
    std = np.sqrt(var)
    std_safe = np.where(std > 0, std, np.nan)
    return (values - mean) / std_safe, std_safe


def _compute_regression_importance(
    panel: str,
    matrix: pd.DataFrame,
    totals: pd.DataFrame,
    targets: List[float],
) -> pd.DataFrame:
    work = totals.merge(matrix, on=["scenario_id", "sample_id"], how="inner")
    if work.empty:
        raise ValueError(f"No matched totals/matrix rows for {panel}.")
    value_cols = [c for c in work.columns if c not in {"scenario_id", "sample_id", "total_emissions_gt"}]
    if not value_cols:
        raise ValueError(f"No predictor columns for {panel}.")

    y = pd.to_numeric(work["total_emissions_gt"], errors="coerce").to_numpy(dtype=float)
    x = work[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    finite = np.isfinite(y) & np.all(np.isfinite(x), axis=1)
    y = y[finite]
    x = x[finite]
    if len(y) < int(CONFIG["min_required_samples"]):
        raise ValueError(f"{panel} has too few finite samples: {len(y)}.")

    sigma = float(CONFIG.get("regression_sigma_gt", 2.0) or 2.0)
    min_ess = CONFIG.get("min_effective_n_samples")
    min_ess_f = None if min_ess is None else float(min_ess)
    rows: List[Dict[str, object]] = []
    for target in targets:
        weights = np.exp(-0.5 * ((y - float(target)) / sigma) ** 2)
        weights = np.where(np.isfinite(weights), weights, 0.0)
        if float(weights.sum()) <= 0:
            continue
        ess = float((weights.sum() ** 2) / max(float(np.sum(weights ** 2)), 1e-12))
        if min_ess_f is not None and ess < min_ess_f:
            print(
                f"[SP_M4f_v3] skip {panel} target {target:g} Gt: "
                f"ESS {ess:.2f} < {min_ess_f:g}."
            )
            continue
        x_std, x_scale = _weighted_standardize(x, weights)
        y_std = _weighted_standardize(y.reshape(-1, 1), weights)[0].reshape(-1)
        keep = np.isfinite(x_scale) & (x_scale > 0)
        if not keep.any():
            continue
        kept_cols = [col for col, flag in zip(value_cols, keep) if flag]
        x_use = x_std[:, keep]
        sqrt_w = np.sqrt(weights)
        try:
            beta, *_ = np.linalg.lstsq(x_use * sqrt_w[:, None], y_std * sqrt_w, rcond=None)
        except np.linalg.LinAlgError:
            continue
        abs_beta = np.abs(beta)
        total = float(abs_beta.sum())
        if total <= 0:
            continue
        imp = abs_beta / total
        for col, value in zip(kept_cols, imp):
            rows.append(
                {
                    "Emis": float(target),
                    "display_name": str(col),
                    "importance": float(value),
                    "panel": panel,
                    "effective_n_samples": ess,
                    "weight_sigma_gt": sigma,
                    "n_samples": int(len(y)),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError(f"No regression importance rows computed for {panel}.")
    return out


def _effective_n_filter(df: pd.DataFrame) -> pd.DataFrame:
    min_ess = CONFIG.get("min_effective_n_samples")
    if min_ess is None or "effective_n_samples" not in df.columns:
        return df
    work = df.copy()
    work["effective_n_samples"] = pd.to_numeric(work["effective_n_samples"], errors="coerce")
    before = len(work)
    work = work[work["effective_n_samples"].ge(float(min_ess))].copy()
    if work.empty:
        raise ValueError(
            "No Strategy importance rows remain after min_effective_n_samples filter "
            f"({min_ess})."
        )
    print(f"[SP_M4f_v3] Strategy ESS filter retained {len(work)}/{before} rows.")
    return work


def _load_strategy_importance_long(summary_dir: Path) -> pd.DataFrame:
    group_path = summary_dir / "importance_by_variable.csv"
    detail_path = summary_dir / "importance_detail.csv"

    if group_path.exists():
        group_df = pd.read_csv(group_path)
        group_df.columns = [str(c).strip() for c in group_df.columns]
        required = {"target_emission_gt", "parameter", "importance"}
        if required.issubset(group_df.columns):
            if "n_samples" in group_df.columns:
                n_samples = pd.to_numeric(group_df["n_samples"], errors="coerce").dropna()
                if not n_samples.empty and int(n_samples.max()) < int(CONFIG["min_required_samples"]):
                    raise ValueError(
                        "Sensitivity sample size is too small for plotting. "
                        f"Found up to {int(n_samples.max())}, "
                        f"required {int(CONFIG['min_required_samples'])}."
                    )
            group_df = _effective_n_filter(group_df)
            group_df["importance"] = pd.to_numeric(group_df["importance"], errors="coerce")
            if group_df["importance"].notna().any():
                keep_cols = ["target_emission_gt", "parameter", "importance"]
                for col in ("n_samples", "effective_n_samples", "weight_mode", "weight_sigma_gt"):
                    if col in group_df.columns:
                        keep_cols.append(col)
                out = group_df[keep_cols].copy()
                out["display_name"] = out["parameter"].map(_normalize_strategy_parameter)
                agg_spec = {"importance": "sum"}
                for col in ("n_samples", "effective_n_samples", "weight_sigma_gt"):
                    if col in out.columns:
                        agg_spec[col] = "max" if col != "weight_sigma_gt" else "first"
                if "weight_mode" in out.columns:
                    agg_spec["weight_mode"] = "first"
                result = (
                    out.groupby(["target_emission_gt", "display_name"], as_index=False)
                    .agg(agg_spec)
                    .rename(columns={"target_emission_gt": "Emis"})
                )
                result["panel"] = "Strategy"
                return result

    if detail_path.exists():
        detail_df = pd.read_csv(detail_path)
        detail_df.columns = [str(c).strip() for c in detail_df.columns]
        if {"target_emission_gt", "importance"}.issubset(detail_df.columns):
            detail_df = _effective_n_filter(detail_df)
            detail_df["importance"] = pd.to_numeric(detail_df["importance"], errors="coerce")
            source_col = "group" if "group" in detail_df.columns else "parameter"
            if detail_df["importance"].notna().any():
                out = detail_df[["target_emission_gt", source_col, "importance"]].copy()
                out["display_name"] = out[source_col].map(_normalize_strategy_parameter)
                result = (
                    out.groupby(["target_emission_gt", "display_name"], as_index=False)["importance"]
                    .sum()
                    .rename(columns={"target_emission_gt": "Emis"})
                )
                result["panel"] = "Strategy"
                return result

    raise FileNotFoundError(
        "No usable Strategy regression importance result found. Expected valid values in "
        f"{group_path} or {detail_path}."
    )


def _smooth_percentage_values(
    pct_values: pd.DataFrame,
    *,
    window: int | None = None,
    polyorder: int | None = None,
    iterations: int | None = None,
) -> pd.DataFrame:
    values = pct_values.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if not bool(CONFIG.get("smooth_plot", True)):
        return values

    window = int(CONFIG.get("smooth_window", 1) if window is None else window)
    if window <= 1 or len(values) <= 2:
        return values
    if window % 2 == 0:
        window += 1
    max_window = len(values) if len(values) % 2 == 1 else len(values) - 1
    window = min(window, max_window)
    if window <= 2:
        return values

    iterations = max(
        1,
        int(CONFIG.get("smooth_iterations", 1) if iterations is None else iterations),
    )
    method = str(CONFIG.get("smooth_method", "rolling")).strip().lower()
    smoothed = values.to_numpy(dtype=float)

    if method == "savgol":
        polyorder = int(CONFIG.get("smooth_polyorder", 2) if polyorder is None else polyorder)
        polyorder = max(1, min(polyorder, window - 1))
        for _ in range(iterations):
            smoothed = savgol_filter(
                smoothed,
                window_length=window,
                polyorder=polyorder,
                axis=0,
                mode="interp",
            )
        smoothed_df = pd.DataFrame(smoothed, columns=values.columns, index=values.index)
    else:
        smoothed_df = values.copy()
        for _ in range(iterations):
            smoothed_df = smoothed_df.rolling(window=window, center=True, min_periods=1).mean()

    smoothed_df = smoothed_df.clip(lower=0.0)
    row_sum = smoothed_df.sum(axis=1).replace(0.0, np.nan)
    return smoothed_df.div(row_sum, axis=0).fillna(0.0) * 100.0


def _collapse_panel_to_top(long_df: pd.DataFrame, panel: str) -> pd.DataFrame:
    if panel == "Strategy":
        return long_df.copy()
    top_n = int((CONFIG.get("top_n", {}) or {}).get(panel, 10) or 10)
    work = long_df.copy()
    rank = (
        work.groupby("display_name", as_index=False)["importance"]
        .mean()
        .sort_values("importance", ascending=False, kind="mergesort")
    )
    keep = set(rank["display_name"].head(top_n).tolist())
    work["display_name"] = np.where(work["display_name"].isin(keep), work["display_name"], "Other")
    return (
        work.groupby(["Emis", "display_name", "panel"], as_index=False)
        .agg(
            importance=("importance", "sum"),
            effective_n_samples=("effective_n_samples", "max"),
            n_samples=("n_samples", "max"),
        )
    )


def _build_panel_tables(long_df: pd.DataFrame, panel: str) -> Dict[str, pd.DataFrame]:
    work = _collapse_panel_to_top(long_df, panel)
    work["Emis"] = pd.to_numeric(work["Emis"], errors="coerce")
    work["importance"] = pd.to_numeric(work["importance"], errors="coerce")
    work["display_name"] = work["display_name"].astype(str).str.strip()
    work = work.dropna(subset=["Emis", "importance"])
    work = work[work["display_name"] != ""].copy()
    if work.empty:
        raise ValueError(f"{panel} regression importance long table is empty after cleanup.")

    raw_wide = (
        work.pivot_table(
            index="Emis",
            columns="display_name",
            values="importance",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
        .sort_values("Emis")
    )

    plot_wide = raw_wide.copy()
    if panel == "Strategy":
        for col in STRATEGY_DISPLAY_ORDER:
            if col not in plot_wide.columns:
                plot_wide[col] = 0.0
        extra_cols = [
            c for c in plot_wide.columns
            if c not in {"Emis", *STRATEGY_DISPLAY_ORDER}
        ]
        plot_wide = plot_wide[["Emis", *STRATEGY_DISPLAY_ORDER, *extra_cols]]
    else:
        val_cols = [c for c in plot_wide.columns if c != "Emis"]
        rank = plot_wide[val_cols].mean().sort_values(ascending=False, kind="mergesort")
        ordered = [c for c in rank.index.tolist() if c != "Other"]
        if "Other" in plot_wide.columns:
            ordered.append("Other")
        plot_wide = plot_wide[["Emis", *ordered]]
    plot_wide = plot_wide.sort_values("Emis").reset_index(drop=True)

    pct_wide = plot_wide.copy()
    value_cols = [c for c in pct_wide.columns if c != "Emis"]
    vals = pct_wide[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    row_sum = vals.sum(axis=1).replace(0.0, np.nan)
    pct_wide[value_cols] = vals.div(row_sum, axis=0).fillna(0.0) * 100.0

    pct_smoothed = pct_wide.copy()
    pct_smoothed[value_cols] = _smooth_percentage_values(pct_wide[value_cols])

    return {
        "org": raw_wide,
        "plot": plot_wide,
        "pct": pct_wide,
        "pct_smoothed": pct_smoothed,
        "long": work.sort_values(["Emis", "display_name"]).reset_index(drop=True),
    }


def _dominant_process_mode() -> str:
    mode = str(
        CONFIG.get("dominant_process_mode", "baseline_2020_share") or ""
    ).strip().lower()
    if mode not in DOMINANT_PROCESS_MODES:
        raise ValueError(
            "CONFIG['dominant_process_mode'] must be one of "
            f"{DOMINANT_PROCESS_MODES}; got {mode!r}."
        )
    return mode


def _dominant_process_method(mode: str) -> str:
    return {
        "parent_max_emission_share": (
            "largest positive Process share at parent maximum net emissions"
        ),
        "baseline_2020_share": "largest positive Process share in baseline 2020",
        "regression_contribution_max": (
            "within-parent Process regression abs(beta) share at highest "
            "valid emission level"
        ),
        "regression_contribution_average": (
            "mean within-parent Process regression abs(beta) share across "
            "all valid emission levels"
        ),
    }[mode]


def _panel_display_info(
    panel: str,
    panel_tables: Mapping[str, Dict[str, pd.DataFrame]],
) -> Tuple[pd.DataFrame, List[str], set[str]]:
    tables = panel_tables.get(panel, {})
    plotted = tables.get("pct_smoothed", tables.get("pct"))
    if plotted is None or plotted.empty:
        return pd.DataFrame(), [], set()
    displayed = [str(col) for col in plotted.columns if str(col) != "Emis"]
    return plotted, displayed, {label for label in displayed if label != "Other"}


def _assign_display_parents(
    source: pd.DataFrame,
    panel: str,
    displayed: List[str],
    individual: set[str],
) -> pd.DataFrame:
    spec = DOMINANT_PROCESS_SPECS[panel]
    parent_col = str(spec["parent_col"])
    process_col = str(spec["process_col"])
    sub = source.copy()
    sub["source_parent"] = sub[parent_col].fillna("").astype(str).str.strip()
    sub["process"] = sub[process_col].fillna("").astype(str).str.strip()
    sub = sub[sub["source_parent"].ne("") & sub["process"].ne("")].copy()
    if "Other" in displayed:
        sub["display_name"] = np.where(
            sub["source_parent"].isin(individual),
            sub["source_parent"],
            "Other",
        )
    else:
        sub = sub[sub["source_parent"].isin(individual)].copy()
        sub["display_name"] = sub["source_parent"]
    return sub


def _dominant_component_record(
    process_rows: pd.DataFrame,
    value_col: str,
) -> Dict[str, object] | None:
    if process_rows.empty:
        return None
    values = pd.to_numeric(process_rows[value_col], errors="coerce").fillna(0.0)
    positive = values.clip(lower=0.0)
    positive_total = float(positive.sum())
    if positive_total > 0:
        idx = positive.idxmax()
        share_pct = float(positive.loc[idx]) / positive_total * 100.0
        share_basis = "positive_process_emissions"
    else:
        absolute = values.abs()
        absolute_total = float(absolute.sum())
        if absolute_total <= 0:
            return None
        idx = absolute.idxmax()
        share_pct = float(absolute.loc[idx]) / absolute_total * 100.0
        share_basis = "absolute_process_emissions_no_positive_total"
    dominant = process_rows.loc[idx]
    parent_net = float(values.sum())
    dominant_value = float(values.loc[idx])
    return {
        "dominant_process": str(dominant["process"]),
        "dominant_process_emissions_gt": dominant_value,
        "dominant_process_share_pct": share_pct,
        "dominant_process_net_share_pct": (
            dominant_value / parent_net * 100.0
            if not np.isclose(parent_net, 0.0)
            else np.nan
        ),
        "parent_net_emissions_gt": parent_net,
        "positive_process_emissions_gt": positive_total,
        "share_basis": share_basis,
    }


def _expand_fixed_dominant_records(
    panel: str,
    plotted: pd.DataFrame,
    records: List[Dict[str, object]],
    mode: str,
) -> pd.DataFrame:
    targets = pd.to_numeric(plotted["Emis"], errors="coerce").dropna().tolist()
    rows = [
        {"panel": panel, "Emis": float(target), "mode": mode, **record}
        for record in records
        for target in targets
    ]
    return pd.DataFrame(rows).sort_values(
        ["Emis", "display_name"],
        kind="mergesort",
    ).reset_index(drop=True)


def _load_joint_structure_source(structure_dir: Path) -> pd.DataFrame:
    emissions_path = structure_dir / "mc_success_structure_emissions.csv"
    if not emissions_path.exists():
        raise FileNotFoundError(
            "Dominant Process mode requires sample-level S5_5 output: "
            f"{emissions_path}"
        )
    wanted = {str(spec["grouping"]) for spec in DOMINANT_PROCESS_SPECS.values()}
    usecols = [
        "scenario_id",
        "sample_id",
        "grouping",
        "group_1",
        "group_2",
        "emissions_gt",
    ]
    chunksize = int(CONFIG.get("structure_chunk_size", 500_000) or 500_000)
    parts: List[pd.DataFrame] = []
    for chunk in pd.read_csv(emissions_path, usecols=usecols, chunksize=chunksize):
        chunk = chunk[chunk["grouping"].astype(str).isin(wanted)].copy()
        if chunk.empty:
            continue
        chunk["scenario_id"] = chunk["scenario_id"].astype(str)
        chunk["sample_id"] = pd.to_numeric(chunk["sample_id"], errors="coerce")
        chunk["emissions_gt"] = pd.to_numeric(chunk["emissions_gt"], errors="coerce")
        chunk = chunk.dropna(subset=["sample_id", "emissions_gt"])
        chunk["sample_id"] = chunk["sample_id"].astype(int)
        parts.append(chunk)
    if not parts:
        raise ValueError(
            f"No Region-Process or Process-Item rows found in {emissions_path}."
        )
    return pd.concat(parts, ignore_index=True)


def _build_parent_max_process_tables(
    structure_dir: Path,
    panel_tables: Mapping[str, Dict[str, pd.DataFrame]],
) -> Dict[str, pd.DataFrame]:
    mode = "parent_max_emission_share"
    method = _dominant_process_method(mode)
    source = _load_joint_structure_source(structure_dir)
    totals = _load_structure_totals(structure_dir).set_index(
        ["scenario_id", "sample_id"]
    )
    output: Dict[str, pd.DataFrame] = {}
    for panel in DOMINANT_PROCESS_PANELS:
        plotted, displayed, individual = _panel_display_info(panel, panel_tables)
        if plotted.empty:
            continue
        spec = DOMINANT_PROCESS_SPECS[panel]
        sub = source[source["grouping"].astype(str).eq(str(spec["grouping"]))].copy()
        sub = _assign_display_parents(sub, panel, displayed, individual)
        grouped = (
            sub.groupby(
                ["scenario_id", "sample_id", "display_name", "process"],
                as_index=False,
            )["emissions_gt"]
            .sum()
        )
        grouped["parent_net_emissions_gt"] = grouped.groupby(
            ["scenario_id", "sample_id", "display_name"]
        )["emissions_gt"].transform("sum")
        records: List[Dict[str, object]] = []
        for display_name, display_rows in grouped.groupby("display_name", sort=False):
            max_parent = float(display_rows["parent_net_emissions_gt"].max())
            candidates = display_rows[
                np.isclose(
                    display_rows["parent_net_emissions_gt"].to_numpy(dtype=float),
                    max_parent,
                    rtol=0.0,
                    atol=1e-12,
                )
            ]
            sample_keys = (
                candidates[["scenario_id", "sample_id"]]
                .drop_duplicates()
                .sort_values(["scenario_id", "sample_id"], kind="mergesort")
            )
            if sample_keys.empty:
                continue
            scenario_id = str(sample_keys.iloc[0]["scenario_id"])
            sample_id = int(sample_keys.iloc[0]["sample_id"])
            sample_rows = candidates[
                candidates["scenario_id"].eq(scenario_id)
                & candidates["sample_id"].eq(sample_id)
            ]
            record = _dominant_component_record(sample_rows, "emissions_gt")
            if record is None:
                continue
            key = (scenario_id, sample_id)
            records.append(
                {
                    "display_name": str(display_name),
                    **record,
                    "parent_max_net_emissions_gt": max_parent,
                    "max_sample_total_emissions_gt": (
                        float(totals.loc[key, "total_emissions_gt"])
                        if key in totals.index
                        else np.nan
                    ),
                    "max_scenario_id": scenario_id,
                    "max_sample_id": sample_id,
                    "source_parent_count": int(
                        sub.loc[
                            sub["display_name"].eq(display_name), "source_parent"
                        ].nunique()
                    ),
                    "method": method,
                }
            )
        output[panel] = _expand_fixed_dominant_records(
            panel, plotted, records, mode
        )
    return output


def _load_s5_5_module() -> object:
    cached = getattr(_load_s5_5_module, "_cached", None)
    if cached is not None:
        return cached
    module_path = Path(__file__).with_name(
        "S5_5_1_Region-Item-Process_Importance_Gen.py"
    )
    spec = importlib.util.spec_from_file_location("s5_5_process_annotation", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load S5_5 module from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    setattr(_load_s5_5_module, "_cached", module)
    return module


def _build_baseline_2020_process_tables(
    panel_tables: Mapping[str, Dict[str, pd.DataFrame]],
) -> Dict[str, pd.DataFrame]:
    mode = "baseline_2020_share"
    method = _dominant_process_method(mode)
    s5_5 = _load_s5_5_module()
    base_dir = Path(get_results_base("BASE"))
    source_path = s5_5._find_country_process_item_path(base_dir)
    if source_path is None:
        raise FileNotFoundError(
            f"Missing BASE country/process/item emissions under {base_dir / 'Emis'}."
        )
    process_map, item_map = s5_5._load_emis_item_maps()
    region_map = s5_5._load_region_emis_sum_map()
    prepared, value_col = s5_5._prepare_groupable_emissions(
        source_path,
        year=2020,
        process_map=process_map,
        item_map=item_map,
        region_map=region_map,
    )
    prepared = prepared.copy()
    prepared["emissions_gt"] = (
        pd.to_numeric(prepared[value_col], errors="coerce").fillna(0.0) * 1e-6
    )

    output: Dict[str, pd.DataFrame] = {}
    for panel in DOMINANT_PROCESS_PANELS:
        plotted, displayed, individual = _panel_display_info(panel, panel_tables)
        if plotted.empty:
            continue
        spec = DOMINANT_PROCESS_SPECS[panel]
        baseline = pd.DataFrame(
            {
                str(spec["parent_col"]): prepared[
                    "Region_emisSum" if panel == "Region" else "Item"
                ],
                str(spec["process_col"]): prepared["Process"],
                "emissions_gt": prepared["emissions_gt"],
            }
        )
        parent_aliases = BASELINE_2020_PARENT_ALIASES.get(panel, {})
        if parent_aliases:
            parent_col = str(spec["parent_col"])
            baseline[parent_col] = baseline[parent_col].replace(parent_aliases)
        baseline = _assign_display_parents(
            baseline, panel, displayed, individual
        )
        grouped = (
            baseline.groupby(["display_name", "process"], as_index=False)[
                "emissions_gt"
            ]
            .sum()
        )
        records: List[Dict[str, object]] = []
        for display_name, display_rows in grouped.groupby("display_name", sort=False):
            record = _dominant_component_record(display_rows, "emissions_gt")
            if record is None:
                continue
            records.append(
                {
                    "display_name": str(display_name),
                    **record,
                    "baseline_year": 2020,
                    "baseline_source": str(source_path),
                    "source_parent_count": int(
                        baseline.loc[
                            baseline["display_name"].eq(display_name),
                            "source_parent",
                        ].nunique()
                    ),
                    "method": method,
                }
            )
        covered = {str(record["display_name"]) for record in records}
        for display_name in displayed:
            if display_name in covered:
                continue
            records.append(
                {
                    "display_name": str(display_name),
                    "dominant_process": "N/A",
                    "dominant_process_emissions_gt": np.nan,
                    "dominant_process_share_pct": np.nan,
                    "dominant_process_net_share_pct": np.nan,
                    "parent_net_emissions_gt": np.nan,
                    "positive_process_emissions_gt": np.nan,
                    "share_basis": "no_nonzero_baseline_2020_emissions",
                    "baseline_year": 2020,
                    "baseline_source": str(source_path),
                    "source_parent_count": 0,
                    "method": method,
                }
            )
        output[panel] = _expand_fixed_dominant_records(
            panel, plotted, records, mode
        )
    return output


def _compute_regression_contribution_detail(
    structure_dir: Path,
    panel_tables: Mapping[str, Dict[str, pd.DataFrame]],
) -> Dict[str, pd.DataFrame]:
    source = _load_joint_structure_source(structure_dir)
    totals = _load_structure_totals(structure_dir)
    totals_index = pd.MultiIndex.from_frame(totals[["scenario_id", "sample_id"]])
    y = totals["total_emissions_gt"].to_numpy(dtype=float)
    sigma = float(CONFIG.get("regression_sigma_gt", 2.0) or 2.0)
    min_ess = CONFIG.get("min_effective_n_samples")
    min_ess_f = None if min_ess is None else float(min_ess)

    output: Dict[str, pd.DataFrame] = {}
    for panel in DOMINANT_PROCESS_PANELS:
        plotted, displayed, individual = _panel_display_info(panel, panel_tables)
        if plotted.empty:
            continue
        spec = DOMINANT_PROCESS_SPECS[panel]
        sub = source[source["grouping"].astype(str).eq(str(spec["grouping"]))].copy()
        sub = _assign_display_parents(sub, panel, displayed, individual)
        grouped = (
            sub.groupby(
                ["scenario_id", "sample_id", "display_name", "process"],
                as_index=False,
            )["emissions_gt"]
            .sum()
        )
        rows: List[Dict[str, object]] = []
        targets = pd.to_numeric(plotted["Emis"], errors="coerce").dropna().tolist()
        for display_name, parent_rows in grouped.groupby("display_name", sort=False):
            matrix = (
                parent_rows.pivot_table(
                    index=["scenario_id", "sample_id"],
                    columns="process",
                    values="emissions_gt",
                    aggfunc="sum",
                    fill_value=0.0,
                )
                .reindex(totals_index, fill_value=0.0)
            )
            process_names = [str(col) for col in matrix.columns]
            x = matrix.to_numpy(dtype=float)
            for target in targets:
                weights = np.exp(-0.5 * ((y - float(target)) / sigma) ** 2)
                weights = np.where(np.isfinite(weights), weights, 0.0)
                if float(weights.sum()) <= 0:
                    continue
                ess = float(
                    (weights.sum() ** 2)
                    / max(float(np.sum(weights ** 2)), 1e-12)
                )
                if min_ess_f is not None and ess < min_ess_f:
                    continue
                x_std, x_scale = _weighted_standardize(x, weights)
                y_std = _weighted_standardize(
                    y.reshape(-1, 1), weights
                )[0].reshape(-1)
                keep = np.isfinite(x_scale) & (x_scale > 0)
                if not keep.any():
                    continue
                sqrt_w = np.sqrt(weights)
                try:
                    beta, *_ = np.linalg.lstsq(
                        x_std[:, keep] * sqrt_w[:, None],
                        y_std * sqrt_w,
                        rcond=None,
                    )
                except np.linalg.LinAlgError:
                    continue
                abs_beta = np.abs(beta)
                total_abs_beta = float(abs_beta.sum())
                if total_abs_beta <= 0:
                    continue
                beta_full = np.zeros(len(process_names), dtype=float)
                beta_full[keep] = beta
                share_full = np.abs(beta_full) / total_abs_beta * 100.0
                source_parent_count = int(
                    sub.loc[
                        sub["display_name"].eq(display_name),
                        "source_parent",
                    ].nunique()
                )
                for process_name, beta_value, share_value, estimable in zip(
                    process_names,
                    beta_full,
                    share_full,
                    keep,
                ):
                    rows.append(
                        {
                            "panel": panel,
                            "Emis": float(target),
                            "display_name": str(display_name),
                            "process": process_name,
                            "process_contribution_share_pct": float(share_value),
                            "process_standardized_beta": float(beta_value),
                            "process_estimable": bool(estimable),
                            "effective_n_samples": ess,
                            "source_parent_count": source_parent_count,
                        }
                    )
        output[panel] = pd.DataFrame(rows).sort_values(
            ["Emis", "display_name", "process"],
            kind="mergesort",
        ).reset_index(drop=True)
    return output


def _build_regression_contribution_tables(
    structure_dir: Path,
    panel_tables: Mapping[str, Dict[str, pd.DataFrame]],
    mode: str,
) -> Dict[str, pd.DataFrame]:
    detail_tables = _compute_regression_contribution_detail(
        structure_dir, panel_tables
    )
    return _summarize_regression_contribution_detail(
        detail_tables, panel_tables, mode
    )


def _summarize_regression_contribution_detail(
    detail_tables: Mapping[str, pd.DataFrame],
    panel_tables: Mapping[str, Dict[str, pd.DataFrame]],
    mode: str,
) -> Dict[str, pd.DataFrame]:
    if mode not in {
        "regression_contribution_max",
        "regression_contribution_average",
    }:
        raise ValueError(f"Unsupported regression contribution mode: {mode!r}")
    method = _dominant_process_method(mode)
    output: Dict[str, pd.DataFrame] = {}
    for panel in DOMINANT_PROCESS_PANELS:
        detail = detail_tables.get(panel, pd.DataFrame())
        plotted, _, _ = _panel_display_info(panel, panel_tables)
        if detail.empty or plotted.empty:
            continue
        records: List[Dict[str, object]] = []
        for display_name, parent_detail in detail.groupby(
            "display_name", sort=False
        ):
            level_count = int(parent_detail["Emis"].nunique())
            level_min = float(parent_detail["Emis"].min())
            level_max = float(parent_detail["Emis"].max())
            if mode == "regression_contribution_max":
                selected_level = level_max
                ranked = parent_detail[
                    parent_detail["Emis"].eq(selected_level)
                ].sort_values(
                    ["process_contribution_share_pct", "process"],
                    ascending=[False, True],
                    kind="mergesort",
                )
                dominant = ranked.iloc[0]
                contribution = float(
                    dominant["process_contribution_share_pct"]
                )
                beta_value = float(dominant["process_standardized_beta"])
                effective_n = float(dominant["effective_n_samples"])
                levels_averaged = 1
            else:
                averaged = (
                    parent_detail.groupby("process", as_index=False)
                    .agg(
                        mean_contribution_share_pct=(
                            "process_contribution_share_pct",
                            "mean",
                        ),
                        mean_standardized_beta=(
                            "process_standardized_beta",
                            "mean",
                        ),
                        estimable_level_count=("process_estimable", "sum"),
                    )
                    .sort_values(
                        ["mean_contribution_share_pct", "process"],
                        ascending=[False, True],
                        kind="mergesort",
                    )
                )
                dominant = averaged.iloc[0]
                contribution = float(
                    dominant["mean_contribution_share_pct"]
                )
                beta_value = float(dominant["mean_standardized_beta"])
                effective_n = float(
                    parent_detail.groupby("Emis")["effective_n_samples"]
                    .first()
                    .mean()
                )
                selected_level = np.nan
                levels_averaged = level_count
            records.append(
                {
                    "display_name": str(display_name),
                    "dominant_process": str(dominant["process"]),
                    "dominant_process_share_pct": contribution,
                    "dominant_process_standardized_beta": beta_value,
                    "regression_contribution_level_gt": selected_level,
                    "regression_level_min_gt": level_min,
                    "regression_level_max_gt": level_max,
                    "regression_level_count": level_count,
                    "regression_levels_averaged": levels_averaged,
                    "mean_effective_n_samples": effective_n,
                    "source_parent_count": int(
                        parent_detail["source_parent_count"].max()
                    ),
                    "method": method,
                }
            )
        output[panel] = _expand_fixed_dominant_records(
            panel, plotted, records, mode
        )
    return output


def _build_dominant_process_tables(
    structure_dir: Path,
    panel_tables: Mapping[str, Dict[str, pd.DataFrame]],
) -> Dict[str, pd.DataFrame]:
    if not bool(CONFIG.get("annotate_dominant_process", True)):
        return {}
    mode = _dominant_process_mode()
    if mode == "parent_max_emission_share":
        output = _build_parent_max_process_tables(structure_dir, panel_tables)
    elif mode == "baseline_2020_share":
        output = _build_baseline_2020_process_tables(panel_tables)
    else:
        output = _build_regression_contribution_tables(
            structure_dir, panel_tables, mode
        )
    for panel, table in output.items():
        print(
            f"[SP_M4f_v3] built {panel} dominant Process annotations: "
            f"{len(table)} rows; mode={mode}."
        )
    return output


def _write_workbook(
    panel_tables: Mapping[str, Dict[str, pd.DataFrame]],
    dominant_process_tables: Mapping[str, pd.DataFrame],
    run_meta: Dict[str, object],
    summary_dir: Path,
    structure_dir: Path,
    fig_dir: Path,
) -> Path:
    out_path = fig_dir / "Figure9_regression_importance_v3.1.xlsx"
    x_min, x_max = _plot_range()
    t_min, t_max = _target_range()
    dominant_mode = _dominant_process_mode()
    dominant_source = {
        "parent_max_emission_share": str(
            structure_dir / "mc_success_structure_emissions.csv"
        ),
        "baseline_2020_share": str(
            Path(get_results_base("BASE"))
            / "Emis"
            / "emissions_summary_By_Country_Process_Item.csv"
        ),
        "regression_contribution_max": str(
            structure_dir / "mc_success_structure_emissions.csv"
        ),
        "regression_contribution_average": str(
            structure_dir / "mc_success_structure_emissions.csv"
        ),
    }[dominant_mode]
    meta_rows = [
        {"key": "definition", "value": "target-local weighted regression abs(beta) share"},
        {"key": "structure_dir", "value": str(structure_dir)},
        {"key": "structure_emissions", "value": str(structure_dir / "mc_success_structure_emissions.csv")},
        {"key": "structure_totals", "value": str(structure_dir / "mc_success_structure_totals.csv")},
        {"key": "s5_0_summary_dir", "value": str(summary_dir)},
        {"key": "s5_0_group_csv", "value": str(summary_dir / "importance_by_variable.csv")},
        {"key": "s5_0_detail_csv", "value": str(summary_dir / "importance_detail.csv")},
        {"key": "plot_emission_range_gt", "value": f"({x_min}, {x_max})"},
        {"key": "target_range_gt", "value": f"({t_min}, {t_max})"},
        {"key": "target_step_gt", "value": CONFIG["target_step_gt"]},
        {"key": "regression_sigma_gt", "value": CONFIG["regression_sigma_gt"]},
        {"key": "min_effective_n_samples", "value": CONFIG["min_effective_n_samples"]},
        {"key": "current_afolu_ghg_gt", "value": CONFIG["current_afolu_ghg_gt"]},
        {"key": "stack_order_target_emis_gt", "value": CONFIG["stack_order_target_emis_gt"]},
        {"key": "use_smoothed_for_plot", "value": CONFIG["use_smoothed_for_plot"]},
        {"key": "smooth_plot", "value": CONFIG["smooth_plot"]},
        {"key": "smooth_method", "value": CONFIG["smooth_method"]},
        {"key": "smooth_window", "value": CONFIG["smooth_window"]},
        {"key": "smooth_polyorder", "value": CONFIG["smooth_polyorder"]},
        {"key": "smooth_iterations", "value": CONFIG["smooth_iterations"]},
        {"key": "plot_interpolation_points", "value": CONFIG["plot_interpolation_points"]},
        {"key": "inplot_label_edge_padding_frac", "value": CONFIG["inplot_label_edge_padding_frac"]},
        {"key": "annotate_dominant_process", "value": CONFIG["annotate_dominant_process"]},
        {"key": "dominant_process_mode", "value": dominant_mode},
        {
            "key": "dominant_process_definition",
            "value": _dominant_process_method(dominant_mode),
        },
        {
            "key": "dominant_process_source",
            "value": dominant_source,
        },
        {"key": "strategy_display_order", "value": " | ".join(STRATEGY_DISPLAY_ORDER)},
    ]
    for panel in GROUPINGS:
        meta_rows.append({"key": f"{panel}_top_n", "value": (CONFIG.get("top_n", {}) or {}).get(panel)})
    for key, value in (run_meta or {}).items():
        meta_rows.append({"key": f"run_meta.{key}", "value": value})

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        pd.DataFrame(meta_rows).to_excel(writer, sheet_name="meta", index=False)
        for panel in ALL_PANELS:
            tables = panel_tables[panel]
            tables["org"].to_excel(writer, sheet_name=f"{panel}_org"[:31], index=False)
            tables["plot"].to_excel(writer, sheet_name=panel[:31], index=False)
            tables["pct"].to_excel(writer, sheet_name=f"{panel}_pct"[:31], index=False)
            tables["pct_smoothed"].to_excel(writer, sheet_name=f"{panel}_pct_smoothed"[:31], index=False)
            tables["long"].to_excel(writer, sheet_name=f"{panel}_long"[:31], index=False)
        for panel, table in dominant_process_tables.items():
            table.to_excel(
                writer,
                sheet_name=f"{panel}_dominant_process"[:31],
                index=False,
            )
    return out_path


def _load_panel_tables_from_workbook(fig_dir: Path) -> Tuple[Dict[str, Dict[str, pd.DataFrame]], Path]:
    workbook_path = fig_dir / "Figure9_regression_importance_v3.1.xlsx"
    if not workbook_path.exists():
        raise FileNotFoundError(
            "CONFIG['plot_only']=1 requires the existing plotting-data workbook: "
            f"{workbook_path}"
        )

    required_suffixes = {
        "org": "_org",
        "plot": "",
        "pct": "_pct",
        "pct_smoothed": "_pct_smoothed",
        "long": "_long",
    }
    with pd.ExcelFile(workbook_path) as workbook:
        available = set(workbook.sheet_names)
        panel_tables: Dict[str, Dict[str, pd.DataFrame]] = {}
        for panel in ALL_PANELS:
            tables: Dict[str, pd.DataFrame] = {}
            for key, suffix in required_suffixes.items():
                sheet_name = f"{panel}{suffix}"[:31]
                if sheet_name not in available:
                    raise ValueError(
                        f"Existing plotting-data workbook is missing sheet {sheet_name!r}: "
                        f"{workbook_path}"
                    )
                tables[key] = pd.read_excel(workbook, sheet_name=sheet_name)
            panel_tables[panel] = tables
    return panel_tables, workbook_path


def _load_dominant_process_tables_from_workbook(
    workbook_path: Path,
) -> Dict[str, pd.DataFrame]:
    output: Dict[str, pd.DataFrame] = {}
    expected_mode = _dominant_process_mode()
    expected_method = _dominant_process_method(expected_mode).casefold()
    with pd.ExcelFile(workbook_path) as workbook:
        available = set(workbook.sheet_names)
        for panel in DOMINANT_PROCESS_PANELS:
            sheet_name = f"{panel}_dominant_process"[:31]
            if sheet_name in available:
                table = pd.read_excel(workbook, sheet_name=sheet_name)
                methods = (
                    table.get("method", pd.Series(dtype=str))
                    .dropna()
                    .astype(str)
                    .str.casefold()
                )
                modes = (
                    table.get("mode", pd.Series(dtype=str))
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )
                if (
                    methods.empty
                    or not methods.eq(expected_method).all()
                    or modes.empty
                    or not modes.eq(expected_mode).all()
                ):
                    print(
                        f"[SP_M4f_v3] WARNING: using stored legacy {sheet_name} "
                        f"because plot-only mode must remain reproducible even though "
                        f"it does not match dominant_process_mode={expected_mode!r}. "
                        "Use --rebuild-regression with complete S5_5 detail to update it."
                    )
                output[panel] = table
    return output


def _panel_slug(panel: str) -> str:
    return panel.lower()


def _panel_sheet_name(panel: str) -> str:
    return f"{panel}_pct"


def _panel_color_map(panel: str, labels: Iterable[str]) -> Dict[str, object]:
    label_list = [str(label) for label in labels]
    if panel == "Strategy":
        return {label: STRATEGY_COLORS.get(label, "#999999") for label in label_list}
    overrides = PROCESS_COLOR_OVERRIDES if panel == "Process" else {}
    if legacy_sheet_palette is not None:
        try:
            palette = dict(legacy_sheet_palette(_panel_sheet_name(panel), label_list))
            for label, color in overrides.items():
                for key in list(palette):
                    if str(key).strip().casefold() == label.casefold():
                        palette[key] = color
            return palette
        except Exception:
            pass
    fallback_colors = list(plt.cm.tab20.colors) + list(plt.cm.tab20b.colors) + list(plt.cm.tab20c.colors)
    palette = {
        label: ((0.7, 0.7, 0.7) if label == "Other" else fallback_colors[idx % len(fallback_colors)])
        for idx, label in enumerate(label_list)
    }
    for label, color in overrides.items():
        for key in list(palette):
            if str(key).strip().casefold() == label.casefold():
                palette[key] = color
    return palette


def _panel_label_map(panel: str) -> Dict[str, str]:
    if panel == "Strategy":
        return dict(STRATEGY_LABELS)
    return dict(LEGACY_IN_PLOT_LABELS.get(_panel_sheet_name(panel), {}))


def _panel_label_x_positions(panel: str) -> Dict[str, float]:
    if panel == "Strategy":
        return dict(STRATEGY_LABEL_X_POSITIONS)
    return dict(LEGACY_LABEL_X_POSITIONS.get(_panel_sheet_name(panel), {}))


def _pick_emis_row(df: pd.DataFrame, target: float) -> pd.Series:
    if df.empty or "Emis" not in df.columns:
        raise ValueError("Panel table is empty or missing Emis.")
    emis = pd.to_numeric(df["Emis"], errors="coerce")
    if emis.isna().all():
        raise ValueError("Emis column is not numeric.")
    idx = (emis - float(target)).abs().idxmin()
    row = df.loc[idx]
    if isinstance(row, pd.DataFrame):
        return row.iloc[0]
    return row


def _stack_order(df: pd.DataFrame, value_cols: List[str]) -> List[str]:
    order_row = _pick_emis_row(df[["Emis", *value_cols]], CONFIG["stack_order_target_emis_gt"])
    order = order_row[value_cols].sort_values(ascending=False, kind="mergesort").index.tolist()
    other = [col for col in order if str(col).strip().lower() in {"other", "others", "rest of world"}]
    main = [col for col in order if col not in other]
    return main + other


def _interpolate_stack_values(
    x: np.ndarray,
    plot_norm: pd.DataFrame,
    stack_order: List[str],
) -> Tuple[np.ndarray, List[np.ndarray], pd.DataFrame]:
    point_count = int(CONFIG.get("plot_interpolation_points", 0))
    if point_count <= len(x) or len(x) < 4:
        return x, [plot_norm[col].to_numpy(dtype=float) for col in stack_order], plot_norm[stack_order].copy()

    x_dense = np.linspace(float(np.min(x)), float(np.max(x)), point_count)
    dense = pd.DataFrame(index=np.arange(point_count))
    for col in stack_order:
        y = plot_norm[col].to_numpy(dtype=float)
        interpolator = PchipInterpolator(x, y, extrapolate=False)
        dense[col] = interpolator(x_dense)
    dense = dense.clip(lower=0.0).fillna(0.0)
    row_sum = dense.sum(axis=1).replace(0.0, np.nan)
    dense = dense.div(row_sum, axis=0).fillna(0.0) * 100.0
    return x_dense, [dense[col].to_numpy(dtype=float) for col in stack_order], dense[stack_order].copy()


def _nearest_index(x: np.ndarray, target: float) -> int:
    return int(np.abs(x - float(target)).argmin())


def _label_text_color(color: object) -> str:
    rgb = np.array(mcolors.to_rgb(color), dtype=float)
    luminance = float(np.dot(rgb, [0.299, 0.587, 0.114]))
    return "white" if luminance < 0.52 else "#333333"


def _dominant_process_at(
    annotations: pd.DataFrame | None,
    display_name: str,
    target_emis_gt: float,
) -> str | None:
    if annotations is None or annotations.empty:
        return None
    required = {"Emis", "display_name", "dominant_process"}
    if not required.issubset(annotations.columns):
        return None
    sub = annotations[
        annotations["display_name"].astype(str).eq(str(display_name))
    ].copy()
    if sub.empty:
        return None
    sub["Emis"] = pd.to_numeric(sub["Emis"], errors="coerce")
    sub = sub.dropna(subset=["Emis"])
    if sub.empty:
        return None
    idx = (sub["Emis"] - float(target_emis_gt)).abs().idxmin()
    row = sub.loc[idx]
    max_gap = CONFIG.get("dominant_process_max_target_gap_gt")
    if max_gap is not None and abs(float(row["Emis"]) - float(target_emis_gt)) > float(max_gap):
        return None
    process = str(row["dominant_process"] or "").strip()
    return process or None


def _add_inplot_labels(
    ax: plt.Axes,
    panel: str,
    x: np.ndarray,
    values: pd.DataFrame,
    value_cols: List[str],
    colors: Mapping[str, object],
    dominant_process_annotations: pd.DataFrame | None = None,
) -> None:
    label_map = _panel_label_map(panel)
    label_positions = _panel_label_x_positions(panel)
    cumulative = np.zeros(len(x), dtype=float)
    min_thickness = float(CONFIG["inplot_label_min_thickness_pct"])
    fontsize = float(CONFIG["inplot_label_fontsize"])
    x_min, x_max = _plot_range()
    edge_padding = (x_max - x_min) * float(CONFIG.get("inplot_label_edge_padding_frac", 0.04))
    label_x_min = x_min + edge_padding
    label_x_max = x_max - edge_padding
    edge_align_tol = max((x_max - x_min) * 0.02, edge_padding * 0.10)

    for col in value_cols:
        layer = values[col].to_numpy(dtype=float)
        if float(np.nanmax(layer)) < min_thickness:
            cumulative += layer
            continue
        preferred = label_positions.get(str(col))
        if preferred is not None:
            preferred = min(max(float(preferred), label_x_min), label_x_max)
            idx = _nearest_index(x, preferred)
            if layer[idx] < min_thickness:
                preferred = None
        if preferred is None:
            interior = (x >= label_x_min) & (x <= label_x_max)
            if interior.any():
                interior_idx = np.where(interior)[0]
                idx = int(interior_idx[np.argmax(layer[interior])])
            else:
                idx = int(np.argmax(layer))
        text_x = min(max(float(x[idx]), label_x_min), label_x_max)
        y_mid = cumulative[idx] + layer[idx] / 2.0
        label = label_map.get(str(col), str(col))
        fill = colors.get(str(col), "#999999")
        ha = "center"
        if text_x <= label_x_min + edge_align_tol:
            ha = "left"
        elif text_x >= label_x_max - edge_align_tol:
            ha = "right"
        process = None
        if (
            panel in DOMINANT_PROCESS_PANELS
            and bool(CONFIG.get("annotate_dominant_process", True))
            and layer[idx]
            >= float(CONFIG.get("dominant_process_min_layer_thickness_pct", 5.0))
        ):
            process = _dominant_process_at(
                dominant_process_annotations,
                str(col),
                text_x,
            )
        text_color = _label_text_color(fill)
        if process is None:
            ax.text(
                text_x,
                float(y_mid),
                label,
                ha=ha,
                va="center",
                fontsize=fontsize,
                color=text_color,
                clip_on=True,
            )
        else:
            process_label = DOMINANT_PROCESS_LABELS.get(
                process,
                _panel_label_map("Process").get(process, process),
            )
            annotation_y_mid = min(max(float(y_mid), 3.0), 96.0)
            ax.annotate(
                label,
                xy=(text_x, annotation_y_mid),
                xytext=(0, 1.2),
                textcoords="offset points",
                ha=ha,
                va="bottom",
                fontsize=fontsize,
                color=text_color,
                annotation_clip=True,
            )
            ax.annotate(
                process_label,
                xy=(text_x, annotation_y_mid),
                xytext=(0, -1.2),
                textcoords="offset points",
                ha=ha,
                va="top",
                fontsize=float(CONFIG.get("dominant_process_fontsize", 6.4)),
                color=text_color,
                annotation_clip=True,
            )
        cumulative += layer


def _plot_panel(
    panel: str,
    tables: Dict[str, pd.DataFrame],
    fig_dir: Path,
    dominant_process_annotations: pd.DataFrame | None = None,
) -> List[Path]:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    key = "pct_smoothed" if bool(CONFIG["use_smoothed_for_plot"]) else "pct"
    df = tables[key].copy()
    df["Emis"] = pd.to_numeric(df["Emis"], errors="coerce")
    df = df.dropna(subset=["Emis"]).sort_values("Emis").reset_index(drop=True)
    x_min, x_max = _plot_range()
    visible = df["Emis"].between(x_min, x_max, inclusive="both")
    if not visible.any():
        raise ValueError(f"No {panel} target points inside plot range ({x_min}, {x_max}).")
    df_visible = df.loc[visible].copy().reset_index(drop=True)

    value_cols = [c for c in df_visible.columns if c != "Emis"]
    values = df_visible[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if np.isclose(values.to_numpy().sum(), 0.0):
        raise ValueError(f"All {panel} importance values are zero in the selected range.")
    row_sum = values.sum(axis=1).replace(0.0, np.nan)
    values = values.div(row_sum, axis=0).fillna(0.0) * 100.0
    if (
        panel == "Strategy"
        and key == "pct_smoothed"
        and bool(CONFIG.get("strategy_plot_resmooth", True))
    ):
        values = _smooth_percentage_values(
            values,
            window=int(CONFIG.get("strategy_plot_smooth_window", 41)),
            polyorder=int(CONFIG.get("strategy_plot_smooth_polyorder", 2)),
            iterations=int(CONFIG.get("strategy_plot_smooth_iterations", 2)),
        )

    order = _stack_order(pd.concat([df_visible[["Emis"]], values], axis=1), value_cols)
    x = df_visible["Emis"].to_numpy(dtype=float)
    x_plot, y, dense_values = _interpolate_stack_values(x, values, order)
    colors = _panel_color_map(panel, order)

    fig, ax = plt.subplots(figsize=(CONFIG["fig_width"], CONFIG["fig_height"]))
    ax.stackplot(x_plot, y, colors=[colors[col] for col in order], labels=order)
    _add_inplot_labels(
        ax,
        panel,
        x_plot,
        dense_values,
        order,
        colors,
        dominant_process_annotations,
    )

    ax.set_xlabel("GHG CO2eq in 2080 (Gt/yr)", fontsize=13.5, fontweight="bold", labelpad=12)
    ax.set_ylabel("Variable relative importance (%)", fontsize=13.5, fontweight="bold", labelpad=12)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, 100)
    current = float(CONFIG["current_afolu_ghg_gt"])
    if x_min <= current <= x_max:
        ax.axvline(
            current,
            color="#534E4E",
            linewidth=1.5,
            linestyle=(0, (8, 6)),
        )
    xticks = sorted(set([t for t in ax.get_xticks() if x_min <= t <= x_max] + [x_min, x_max]))
    ax.set_xticks(xticks)
    ax.tick_params(axis="both", which="both", labelsize=13, width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)

    fig.tight_layout()
    slug = _panel_slug(panel)
    outputs = [
        fig_dir / f"Figure9_structure_importance_{slug}_regression_v3.1.png",
        fig_dir / f"Figure9_structure_importance_{slug}_regression_v3.1.svg",
    ]
    fig.savefig(outputs[0], dpi=int(CONFIG["dpi"]))
    fig.savefig(outputs[1])
    plt.close(fig)
    return outputs


def _apply_cli_overrides(args: argparse.Namespace) -> None:
    if args.plot_only is not None:
        CONFIG["plot_only"] = int(bool(args.plot_only))
    if args.x_min is not None or args.x_max is not None:
        current_lo, current_hi = _plot_range()
        CONFIG["plot_emission_range_gt"] = (
            current_lo if args.x_min is None else float(args.x_min),
            current_hi if args.x_max is None else float(args.x_max),
        )
    if args.target_min is not None or args.target_max is not None:
        current_lo, current_hi = _target_range()
        CONFIG["target_range_gt"] = (
            current_lo if args.target_min is None else float(args.target_min),
            current_hi if args.target_max is None else float(args.target_max),
        )
    if args.target_step is not None:
        CONFIG["target_step_gt"] = float(args.target_step)
    if args.sigma is not None:
        CONFIG["regression_sigma_gt"] = float(args.sigma)
    if args.min_ess is not None:
        CONFIG["min_effective_n_samples"] = float(args.min_ess)
    if args.no_smooth:
        CONFIG["smooth_plot"] = False
        CONFIG["use_smoothed_for_plot"] = False


def main() -> None:
    args = _build_arg_parser().parse_args()
    _apply_cli_overrides(args)
    summary_dir, structure_dir, fig_dir = _resolve_paths(args)
    plot_only = int(CONFIG.get("plot_only", 0) or 0) == 1

    if plot_only:
        panel_tables, workbook_path = _load_panel_tables_from_workbook(fig_dir)
        dominant_process_tables = _load_dominant_process_tables_from_workbook(workbook_path)
        missing_annotation_panels = set(DOMINANT_PROCESS_PANELS) - set(dominant_process_tables)
        if missing_annotation_panels:
            fallback_tables = _build_dominant_process_tables(
                structure_dir,
                panel_tables,
            )
            for panel in missing_annotation_panels:
                if panel in fallback_tables:
                    dominant_process_tables[panel] = fallback_tables[panel]
        print(f"[PLOT_ONLY] plotting from existing workbook: {workbook_path}")
    else:
        targets = _target_grid()
        totals = _load_structure_totals(structure_dir)
        matrices = _load_structure_matrices(structure_dir)

        panel_tables = {}
        for panel in GROUPINGS:
            long_df = _compute_regression_importance(panel, matrices[panel], totals, targets)
            panel_tables[panel] = _build_panel_tables(long_df, panel)

        strategy_long = _load_strategy_importance_long(summary_dir)
        panel_tables["Strategy"] = _build_panel_tables(strategy_long, "Strategy")
        dominant_process_tables = _build_dominant_process_tables(
            structure_dir,
            panel_tables,
        )

        run_meta = _load_run_meta(summary_dir, structure_dir)
        workbook_path = _write_workbook(
            panel_tables,
            dominant_process_tables,
            run_meta,
            summary_dir,
            structure_dir,
            fig_dir,
        )
        print(f"[DONE] workbook: {workbook_path}")

    for panel in ALL_PANELS:
        outputs = _plot_panel(
            panel,
            panel_tables[panel],
            fig_dir,
            dominant_process_tables.get(panel),
        )
        for path in outputs:
            print(f"[DONE] figure: {path}")


if __name__ == "__main__":
    main()
