from __future__ import annotations

"""
Build the 3x3 AFOLU contour figure from Panel_Yield_EF results.

Data source priority:
1. output/Panel_Yield_EF/figure_panel_dataset_long_plot_ready.csv
2. output/Panel_Yield_EF/figure_panel_dataset_long.csv
3. output/Panel_Yield_EF/figure_panel_dataset_long_rebuilt.csv

The script prefers the table with the largest number of valid plot points so it
can work both with a fully rebuilt/interpolated panel dataset and with a raw
partial run export.

Outputs:
  - output/Plot/Fig1/Figure1_AFOLU_contour.png
  - output/Plot/Fig1/Figure1_AFOLU_contour.svg
  - output/Plot/Fig1/Figure1_AFOLU_contour_plot_data.csv
"""

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import matplotlib.transforms as mtransforms
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, LogNorm, Normalize, PowerNorm
from matplotlib import colormaps
from matplotlib.path import Path as MplPath

from config_paths import get_results_base

try:
    from scipy.interpolate import RectBivariateSpline, make_interp_spline, splev, splprep
except ImportError:  # pragma: no cover - optional plotting refinement
    RectBivariateSpline = None
    make_interp_spline = None
    splev = None
    splprep = None


RESULTS_BASE = Path(get_results_base())
PANEL_DIR = RESULTS_BASE / "Panel_Yield_EF"
FIG_DIR = RESULTS_BASE / "Plot" / "Fig1"

INPUT_PRIORITIES = {
    "figure_panel_dataset_long_plot_ready.csv": 3,
    "figure_panel_dataset_long.csv": 2,
    "figure_panel_dataset_long_rebuilt.csv": 1,
}

OUTPUT_STEM = "Figure1_AFOLU_contour"
PLOT_DATA_NAME = "Figure1_AFOLU_contour_plot_data.csv"
DIAGNOSTICS_NAME = "Figure1_AFOLU_contour_diagnostics.csv"

RUMINANT_CAP_COL = "ruminant_kcal_share_cap_pct"
DEPRECATED_RUMINANT_CAP_COL = "ruminant_intake_change_pct"

CONFIG = {
    # Set to 1 to skip rebuilding Figure1_AFOLU_contour_plot_data.csv and
    # plot directly from the existing CSV under output/Plot/Fig1.
    "plot_only": 1,
    # Color scale controls. Robust limits avoid letting a few extreme values
    # flatten the color contrast across most panels.
    "colorbar_cmap": "Spectral_r",
    "colorbar_use_robust_limits": 1,
    "colorbar_percentile_min": 0.01,
    "colorbar_percentile_max": 99.1,
    "colorbar_manual_min": None,
    "colorbar_manual_max": None,
    "colorbar_extend": "both",
    # Color normalization. This controls how numeric values map to colors:
    # "linear" -> uniform numeric spacing; easiest to interpret.
    # "power" -> nonlinear continuous scale. gamma < 1 expands low/mid
    # values and compresses high values, which usually makes
    # this contour map show richer color variation.
    # "log" -> logarithmic scale for strictly positive data; useful when
    # values span orders of magnitude.
    # "quantile" -> nonuniform bins from data percentiles. Each bin gets a
    # similar amount of data, maximizing visual contrast but
    # making numeric color intervals uneven.
    "colorbar_norm": "linear",
    "colorbar_power_gamma": 0.65,
    "colorbar_quantile_bins": 14,
    # Target contour interpolation method used after grid smoothing and before
    # contour extraction:
    # "linear" -> conservative bilinear interpolation; default and most
    # faithful to the gridded model output.
    # "cubic_spline" -> smoother curved target lines via SciPy
    # RectBivariateSpline; falls back to linear if SciPy is
    # unavailable or the grid is too small.
    # "nearest" -> blocky nearest-neighbor refinement for diagnostics.
    "target_contour_interpolation": "cubic_spline",
    # Display-only smoothing. These settings only affect rendered figures; the
    # saved plot data and diagnostics remain on the original model grid.
    "surface_smooth_sigma": 1.25,
    "surface_upsample": 6,
    "surface_interpolation": "linear",
    "target_contour_smooth_sigma": 7.0,
    "target_contour_upsample": 40,
    "target_contour_path_smooth_iterations": 7,
    "target_contour_linewidth": 3.6,
    "target_contour_curve_spline": 1,
    "target_contour_curve_smoothing_rms": 1.2,
    "target_contour_curve_points_per_unit": 4.0,
    "target_contour_curve_min_points": 120,
    "target_contour_curve_max_points": 1200,
    "use_pale_l_per_a_if_available": 1,
}

# Figure styling.
FIG_WIDTH = 13.0
FIG_HEIGHT = 12.0
TITLE_FONTSIZE = 17
AXIS_LABEL_FONTSIZE = 16
TICK_LABEL_FONTSIZE = 12
PANEL_LETTER_FONTSIZE = 15
ROW_LABEL_FONTSIZE = 16
COL_LABEL_FONTSIZE = 15
CONTOUR_LABEL_FONTSIZE = 11.5
POINT_LABEL_FONTSIZE = 10.5
COLORBAR_LABEL_FONTSIZE = 14

SHOW_INTERPOLATED_POINTS = False
PANEL_AXIS_PADDING_FRACTION = 0.0
TARGET_CONTOUR_SMOOTH_SIGMA = 7.0  # grid cells; used only for target contour lines
TARGET_CONTOUR_UPSAMPLE = 40  # refinement used only for target contour lines
TARGET_CONTOUR_PATH_SMOOTH_ITERATIONS = 7
TARGET_CONTOUR_MIN_SEGMENT_LENGTH = 3.0
QUALITY_GATE_ENABLED = True
MIN_OBSERVED_POINT_FRACTION = 0.50
MAX_INTERPOLATED_POINT_FRACTION = 0.50
MIN_OBSERVED_POINTS_PER_PANEL = 25
MIN_OBSERVED_FRACTION_PER_PANEL = 0.25
MAX_INTERPOLATED_FRACTION_PER_PANEL = 0.75

# Prefer realized PALE L/A when S5.3 outputs it. Older panel CSVs only contain
# yield_change_pct, so the fallback maps higher yield to lower land intensity.
Y_AXIS_MODE = "negate_yield_pct"  # negate_yield_pct | yield_pct | reciprocal_land_intensity_pct

TARGET_COLOR_MAP = {
    "1.5D": "#4f183f",
    "2D": "#31418f",
    "Current": "#30986a",
    "RCP4.5": "#f46d43",
    "RCP8.5": "#9e0142",
}

DEFAULT_TARGETS = [
    ("1.5D", 0.9),
    ("2D", 4.20),
    ("Current", 13.20),
    ("RCP4.5", 14.50),
    ("RCP8.5", 29.50)
]

# These benchmark points are editorial annotations used in the reference
# figure. They are configurable here because the current pipeline does not yet
# maintain them in a dedicated data table.
BENCHMARK_POINTS = [
    {
        "forest_area_change_pct": -30.0,
        RUMINANT_CAP_COL: -30.0,
        "x": -5.0,
        "y": -12.0,
        "label": "S6_High-Bio.",
        "edgecolor": "#5b8bd3",
        "text_color": "white",
        "dx": 3.6,
        "dy": 1.2,
    },
    {
        "forest_area_change_pct": -30.0,
        RUMINANT_CAP_COL: 0.0,
        "x": 3.0,
        "y": 10.0,
        "label": "S1_Reference",
        "edgecolor": "#5b8bd3",
        "text_color": "white",
        "dx": -28.0,
        "dy": 6.0,
    },
    {
        "forest_area_change_pct": 0.0,
        RUMINANT_CAP_COL: -30.0,
        "x": -2.0,
        "y": -9.0,
        "label": "S2_Sust-Demand",
        "edgecolor": "#5b8bd3",
        "text_color": "white",
        "dx": -28.0,
        "dy": 5.0,
    },
    {
        "forest_area_change_pct": 0.0,
        RUMINANT_CAP_COL: -30.0,
        "x": -40.0,
        "y": -39.0,
        "label": "SSP1-2.6 [MAgPIE]",
        "edgecolor": "#6a83d7",
        "text_color": "white",
        "dx": 7.0,
        "dy": -4.0,
    },
    {
        "forest_area_change_pct": 0.0,
        RUMINANT_CAP_COL: -30.0,
        "x": -37.0,
        "y": -52.0,
        "label": "NET-ZERO [MAgPIE]",
        "edgecolor": "#6a83d7",
        "text_color": "white",
        "dx": 6.5,
        "dy": -2.0,
    },
    {
        "forest_area_change_pct": 0.0,
        RUMINANT_CAP_COL: 0.0,
        "x": 10.0,
        "y": 36.0,
        "label": "SSP2 Baseline\n[IMAGE]",
        "edgecolor": "#f39c34",
        "text_color": "black",
        "dx": -8.0,
        "dy": 5.0,
    },
    {
        "forest_area_change_pct": 0.0,
        RUMINANT_CAP_COL: 0.0,
        "x": 0.0,
        "y": 0.0,
        "label": "Current",
        "edgecolor": "#f39c34",
        "text_color": "white",
        "dx": -8.0,
        "dy": 5.0,
    },
    {
        "forest_area_change_pct": 0.0,
        RUMINANT_CAP_COL: 0.0,
        "x": -50.0,
        "y": -5.0,
        "label": "S4_Imp-Managt.",
        "edgecolor": "#6a83d7",
        "text_color": "white",
        "dx": -5.0,
        "dy": -10.0,
    },
    {
        "forest_area_change_pct": 0.0,
        RUMINANT_CAP_COL: 0.0,
        "x": -5.0,
        "y": -55.0,
        "label": "S3_Imp-Prodivt.",
        "edgecolor": "#6a83d7",
        "text_color": "white",
        "dx": -20.0,
        "dy": 6.0,
    },
    {
        "forest_area_change_pct": 30.0,
        RUMINANT_CAP_COL: -30.0,
        "x": -46.0,
        "y": -20.0,
        "label": "SSP1-1.9\n[GCAM]",
        "edgecolor": "white",
        "text_color": "white",
        "dx": -10.0,
        "dy": -10.0,
    },
    {
        "forest_area_change_pct": 30.0,
        RUMINANT_CAP_COL: -30.0,
        "x": -22.0,
        "y": -26.0,
        "label": "NET-ZERO [FAO]",
        "edgecolor": "white",
        "text_color": "white",
        "dx": 4.0,
        "dy": -2.0,
    },
    {
        "forest_area_change_pct": 30.0,
        RUMINANT_CAP_COL: -30.0,
        "x": -43.0,
        "y": -51.0,
        "label": "S7_Combination",
        "edgecolor": "white",
        "text_color": "white",
        "dx": -8.0,
        "dy": -10.0,
    },
    {
        "forest_area_change_pct": 30.0,
        RUMINANT_CAP_COL: 0.0,
        "x": -18.0,
        "y": -7.0,
        "label": "SSP1-2.6 [GCAM]",
        "edgecolor": "#f4f08a",
        "text_color": "white",
        "dx": -18.0,
        "dy": -10.0,
    },
    {
        "forest_area_change_pct": 30.0,
        RUMINANT_CAP_COL: 0.0,
        "x": -18.0,
        "y": -30.0,
        "label": "SSP1-2.6\n[IMAGE]",
        "edgecolor": "#f4f08a",
        "text_color": "white",
        "dx": -14.0,
        "dy": -10.0,
    },
    {
        "forest_area_change_pct": 30.0,
        RUMINANT_CAP_COL: 0.0,
        "x": 9.0,
        "y": -36.0,
        "label": "S6_Land-Prot.",
        "edgecolor": "#5b8bd3",
        "text_color": "white",
        "dx": -9.0,
        "dy": 6.0,
    },
]


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_csv_with_lock_fallback(df: pd.DataFrame, path: Path) -> Path:
    try:
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return path
    except PermissionError:
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        fallback = path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
        df.to_csv(fallback, index=False, encoding="utf-8-sig")
        print(f"[WARN] CSV is locked, wrote fallback: {fallback}")
        return fallback


def _load_targets() -> List[Tuple[str, float]]:
    return [(str(label), float(value)) for label, value in DEFAULT_TARGETS]


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _normalise_ruminant_cap_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    if RUMINANT_CAP_COL not in out.columns and DEPRECATED_RUMINANT_CAP_COL in out.columns:
        out = out.rename(columns={DEPRECATED_RUMINANT_CAP_COL: RUMINANT_CAP_COL})
    elif RUMINANT_CAP_COL in out.columns and DEPRECATED_RUMINANT_CAP_COL in out.columns:
        out[RUMINANT_CAP_COL] = out[RUMINANT_CAP_COL].where(
            out[RUMINANT_CAP_COL].notna(),
            out[DEPRECATED_RUMINANT_CAP_COL],
        )
        out = out.drop(columns=[DEPRECATED_RUMINANT_CAP_COL])
    if "ruminant_intake_multiplier" in out.columns:
        out = out.drop(columns=["ruminant_intake_multiplier"])
    return out


def _load_candidate_dataset(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        return None
    if df.empty or "afolu_emissions_gt_co2eq_yr" not in df.columns:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    df = _normalise_ruminant_cap_columns(df)
    df["afolu_emissions_gt_co2eq_yr"] = _safe_numeric(df["afolu_emissions_gt_co2eq_yr"])
    return df


def _choose_input_dataset() -> Tuple[Path, pd.DataFrame]:
    best_path: Optional[Path] = None
    best_df: Optional[pd.DataFrame] = None
    best_score: Tuple[int, int, int] = (-1, -1, -1)

    for name, priority in INPUT_PRIORITIES.items():
        path = PANEL_DIR / name
        df = _load_candidate_dataset(path)
        if df is None:
            continue
        valid_points = int(df["afolu_emissions_gt_co2eq_yr"].notna().sum())
        score = (valid_points, len(df), priority)
        if score > best_score:
            best_score = score
            best_path = path
            best_df = df

    if best_path is None or best_df is None:
        raise FileNotFoundError(
            "No usable panel dataset found under output/Panel_Yield_EF."
        )
    return best_path, best_df


def _land_intensity_change_pct(yield_change_pct: pd.Series) -> pd.Series:
    y = _safe_numeric(yield_change_pct).astype(float)
    if Y_AXIS_MODE == "yield_pct":
        return y
    if Y_AXIS_MODE == "reciprocal_land_intensity_pct":
        mult = 1.0 + y / 100.0
        out = pd.Series(np.nan, index=y.index, dtype=float)
        valid = np.isfinite(mult) & (np.abs(mult) > 1e-12)
        out.loc[valid] = (1.0 / mult.loc[valid] - 1.0) * 100.0
        return out
    return -y


def _reference_pale_l_per_a(df: pd.DataFrame, col: str = "pale_l_per_a_ha_per_kcal") -> Optional[float]:
    if col not in df.columns:
        return None
    work = df.copy()
    val = _safe_numeric(work[col]).astype(float)
    valid = val.notna() & np.isfinite(val) & val.gt(0)
    if not valid.any():
        return None

    def _axis_abs(axis_col: str, target: float = 0.0) -> pd.Series:
        if axis_col not in work.columns:
            return pd.Series(np.inf, index=work.index, dtype=float)
        return (_safe_numeric(work[axis_col]).astype(float) - float(target)).abs()

    rumi = _safe_numeric(work.get(RUMINANT_CAP_COL, pd.Series(np.nan, index=work.index))).astype(float)
    if rumi.notna().any():
        rumi_target = 13.0 if (rumi - 13.0).abs().min() <= 1e-9 else float(rumi.dropna().iloc[(rumi.dropna() - 13.0).abs().argmin()])
    else:
        rumi_target = np.nan
    score = (
        _axis_abs("forest_area_change_pct")
        + _axis_abs("yield_change_pct")
        + _axis_abs("emission_factor_change_pct")
    )
    if np.isfinite(rumi_target):
        score = score + (_safe_numeric(work[RUMINANT_CAP_COL]).astype(float) - rumi_target).abs()
    scored = work.loc[valid].copy()
    scored["_score"] = score.loc[valid]
    scored["_pale_l_per_a"] = val.loc[valid]
    scored = scored.sort_values("_score")
    if scored.empty:
        return None
    ref = float(scored.iloc[0]["_pale_l_per_a"])
    return ref if np.isfinite(ref) and ref > 0 else None


def _pale_l_per_a_change_pct(df: pd.DataFrame) -> Optional[pd.Series]:
    if not _config_bool("use_pale_l_per_a_if_available", True):
        return None
    col = "pale_l_per_a_ha_per_kcal"
    if col not in df.columns:
        return None
    vals = _safe_numeric(df[col]).astype(float)
    if vals.notna().sum() <= 0:
        return None
    ref = _reference_pale_l_per_a(df, col=col)
    if ref is None:
        return None
    out = pd.Series(np.nan, index=df.index, dtype=float)
    valid = vals.notna() & np.isfinite(vals) & vals.gt(0)
    out.loc[valid] = (vals.loc[valid] / ref - 1.0) * 100.0
    return out


def _validate_panel_input_quality(df: pd.DataFrame, source_path: Path) -> None:
    if not QUALITY_GATE_ENABLED:
        return
    total = int(len(df))
    if total <= 0:
        raise RuntimeError(f"Contour quality gate failed for {source_path}: no rows.")

    status = df.get("plot_data_status", pd.Series("observed", index=df.index)).astype(str).str.strip().str.lower()
    z = pd.to_numeric(df.get("z_plot_gt", pd.Series(np.nan, index=df.index)), errors="coerce")
    interp_flag = _bool_series(df.get("is_interpolated", pd.Series(False, index=df.index)))
    observed = status.eq("observed") & z.notna()
    interpolated = (status.eq("interpolated") | interp_flag) & z.notna()

    observed_fraction = float(observed.mean())
    interpolated_fraction = float(interpolated.mean())
    issues: List[str] = []
    if observed_fraction < MIN_OBSERVED_POINT_FRACTION:
        issues.append(
            f"observed_fraction={observed_fraction:.3f} < {MIN_OBSERVED_POINT_FRACTION:.3f} "
            f"({int(observed.sum())}/{total})"
        )
    if interpolated_fraction > MAX_INTERPOLATED_POINT_FRACTION:
        issues.append(
            f"interpolated_fraction={interpolated_fraction:.3f} > {MAX_INTERPOLATED_POINT_FRACTION:.3f} "
            f"({int(interpolated.sum())}/{total})"
        )

    weak_panels: List[str] = []
    interp_panels: List[str] = []
    for (forest_pct, rumi_pct), idxs in df.groupby(
        ["forest_area_change_pct", RUMINANT_CAP_COL], dropna=False
    ).groups.items():
        panel_total = int(len(idxs))
        if panel_total <= 0:
            continue
        panel_observed = int(observed.loc[idxs].sum())
        panel_observed_fraction = float(panel_observed / panel_total)
        panel_interpolated_fraction = float(interpolated.loc[idxs].sum() / panel_total)
        panel_label = f"F={forest_pct}, R={rumi_pct}"
        if (
            panel_observed < MIN_OBSERVED_POINTS_PER_PANEL
            or panel_observed_fraction < MIN_OBSERVED_FRACTION_PER_PANEL
        ):
            weak_panels.append(f"{panel_label}: observed={panel_observed}/{panel_total}")
        if panel_interpolated_fraction > MAX_INTERPOLATED_FRACTION_PER_PANEL:
            interp_panels.append(f"{panel_label}: interpolated={panel_interpolated_fraction:.3f}")

    if weak_panels:
        issues.append(
            f"{len(weak_panels)} panels below observed support gate; examples: "
            + "; ".join(weak_panels[:6])
        )
    if interp_panels:
        issues.append(
            f"{len(interp_panels)} panels above interpolation gate; examples: "
            + "; ".join(interp_panels[:6])
        )

    if issues:
        raise RuntimeError(
            f"Contour quality gate failed for {source_path}: "
            + " | ".join(issues)
            + ". Rebuild S5_3 after fixing model feasibility; disable "
            "QUALITY_GATE_ENABLED only for diagnostics."
        )


def _prepare_plot_data(df: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    df = _normalise_ruminant_cap_columns(df)
    required = [
        "forest_area_change_pct",
        RUMINANT_CAP_COL,
        "yield_change_pct",
        "emission_factor_change_pct",
        "afolu_emissions_gt_co2eq_yr",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Panel dataset missing columns: {missing}")

    out = df.copy()
    out["forest_area_change_pct"] = _safe_numeric(out["forest_area_change_pct"])
    out[RUMINANT_CAP_COL] = _safe_numeric(out[RUMINANT_CAP_COL])
    out["yield_change_pct"] = _safe_numeric(out["yield_change_pct"])
    out["emission_factor_change_pct"] = _safe_numeric(out["emission_factor_change_pct"])
    out["x_plot_pct"] = out["emission_factor_change_pct"]
    out["y_plot_pct"] = _land_intensity_change_pct(out["yield_change_pct"])
    out["y_plot_source"] = "yield_change_pct_proxy"
    pale_y = _pale_l_per_a_change_pct(out)
    if pale_y is not None:
        use_mask = pale_y.notna()
        out.loc[use_mask, "y_plot_pct"] = pale_y.loc[use_mask]
        out.loc[use_mask, "y_plot_source"] = "pale_l_per_a_ha_per_kcal"
    out["z_plot_gt"] = _safe_numeric(out["afolu_emissions_gt_co2eq_yr"])
    if "plot_data_status" not in out.columns:
        out["plot_data_status"] = "observed"
    if "is_interpolated" not in out.columns:
        out["is_interpolated"] = False
    out["source_dataset"] = source_path.name
    _validate_panel_input_quality(out, source_path)
    out = out.dropna(subset=["forest_area_change_pct", RUMINANT_CAP_COL, "x_plot_pct", "y_plot_pct", "z_plot_gt"]).copy()
    return out


def _load_existing_plot_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"CONFIG['plot_only']=1 but existing plot data CSV was not found: {path}"
        )
    df = pd.read_csv(path, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    df = _normalise_ruminant_cap_columns(df)
    required = [
        "forest_area_change_pct",
        RUMINANT_CAP_COL,
        "x_plot_pct",
        "y_plot_pct",
        "z_plot_gt",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Existing plot data CSV missing columns: {missing}")

    out = df.copy()
    for col in required:
        out[col] = _safe_numeric(out[col])
    if "is_interpolated" not in out.columns:
        out["is_interpolated"] = False
    out = out.dropna(subset=required).copy()
    if out.empty:
        raise ValueError(f"Existing plot data CSV has no valid plot rows: {path}")
    return out


def _build_color_scale(plot_df: pd.DataFrame) -> Tuple[Normalize, object, str]:
    z = _safe_numeric(plot_df["z_plot_gt"]).dropna().to_numpy(dtype=float)
    z = z[np.isfinite(z)]
    if z.size == 0:
        raise ValueError("No finite z_plot_gt values available for color scale.")

    data_min = float(np.nanmin(z))
    data_max = float(np.nanmax(z))

    manual_min = CONFIG.get("colorbar_manual_min")
    manual_max = CONFIG.get("colorbar_manual_max")
    use_robust = int(CONFIG.get("colorbar_use_robust_limits", 0) or 0) == 1
    if manual_min is not None or manual_max is not None:
        vmin = float(manual_min) if manual_min is not None else data_min
        vmax = float(manual_max) if manual_max is not None else data_max
    elif use_robust:
        pmin = float(CONFIG.get("colorbar_percentile_min", 2.0))
        pmax = float(CONFIG.get("colorbar_percentile_max", 98.0))
        if not (0.0 <= pmin < pmax <= 100.0):
            raise ValueError("CONFIG colorbar percentiles must satisfy 0 <= min < max <= 100.")
        vmin, vmax = [float(v) for v in np.nanpercentile(z, [pmin, pmax])]
    else:
        vmin, vmax = data_min, data_max

    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        vmin, vmax = data_min, data_max
    if vmax <= vmin:
        delta = max(abs(vmin) * 0.01, 1.0)
        vmin -= delta
        vmax += delta

    cmap = colormaps.get_cmap(str(CONFIG.get("colorbar_cmap", "Spectral_r"))).copy()
    cmap.set_under(cmap(0.0))
    cmap.set_over(cmap(1.0))

    configured_extend = str(CONFIG.get("colorbar_extend", "both") or "both").strip().lower()
    if configured_extend == "auto":
        under = data_min < vmin
        over = data_max > vmax
        if under and over:
            extend = "both"
        elif under:
            extend = "min"
        elif over:
            extend = "max"
        else:
            extend = "neither"
    else:
        extend = configured_extend

    norm_mode = str(CONFIG.get("colorbar_norm", "linear") or "linear").strip().lower()
    norm_mode = {
        "lin": "linear",
        "pow": "power",
        "powernorm": "power",
        "lognorm": "log",
        "percentile": "quantile",
        "quantiles": "quantile",
    }.get(norm_mode, norm_mode)

    if norm_mode == "power":
        gamma = float(CONFIG.get("colorbar_power_gamma", 0.65) or 0.65)
        if gamma <= 0:
            raise ValueError("CONFIG['colorbar_power_gamma'] must be > 0.")
        norm = PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax, clip=False)
        norm_note = f"power(gamma={gamma:g})"
    elif norm_mode == "log":
        if vmin <= 0:
            positive = z[z > 0]
            if positive.size == 0:
                raise ValueError("Log colorbar requested but z_plot_gt has no positive values.")
            vmin = float(np.nanmin(positive))
        norm = LogNorm(vmin=vmin, vmax=vmax, clip=False)
        norm_note = "log"
    elif norm_mode == "quantile":
        bins = max(3, int(CONFIG.get("colorbar_quantile_bins", 14) or 14))
        percentiles = np.linspace(0.0, 100.0, bins + 1)
        boundaries = np.nanpercentile(np.clip(z, vmin, vmax), percentiles)
        boundaries[0] = vmin
        boundaries[-1] = vmax
        boundaries = np.unique(boundaries.astype(float))
        if boundaries.size < 3:
            norm = Normalize(vmin=vmin, vmax=vmax)
            norm_note = "linear fallback from quantile"
        else:
            cmap = cmap.resampled(boundaries.size - 1)
            norm = BoundaryNorm(boundaries, cmap.N, clip=False)
            norm_note = f"quantile(bins={boundaries.size - 1})"
    elif norm_mode == "linear":
        norm = Normalize(vmin=vmin, vmax=vmax)
        norm_note = "linear"
    else:
        print(f"[WARN] Unknown colorbar_norm {norm_mode!r}; falling back to linear.")
        norm = Normalize(vmin=vmin, vmax=vmax)
        norm_note = "linear fallback"

    print(
        f"[INFO] color scale: data=[{data_min:.3g}, {data_max:.3g}], "
        f"display=[{vmin:.3g}, {vmax:.3g}], cmap={CONFIG.get('colorbar_cmap')}, "
        f"norm={norm_note}, extend={extend}"
    )
    return norm, cmap, extend


def _panel_title_for_ruminant(pct: float) -> str:
    val = int(round(float(pct)))
    if 0 <= val <= 100:
        return f"Ruminant kcal share cap\n{val}%"
    if val < 0:
        return f"{abs(val)}% decrease in caloric share of\nbeef and other ruminants"
    return "Current caloric share of\nbeef and other ruminants"


def _row_title_for_forest(pct: float) -> str:
    val = int(round(float(pct)))
    if val < 0:
        return f"{abs(val)}% decrease in share of\nglobal forest area"
    if val > 0:
        return f"{val}% increase in share of\nglobal forest area"
    return "Current global forest area"


def _rect_grid(sub: pd.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    xy = sub[["x_plot_pct", "y_plot_pct"]].drop_duplicates()
    xs = np.sort(xy["x_plot_pct"].unique())
    ys = np.sort(xy["y_plot_pct"].unique())
    if len(xs) * len(ys) != len(xy):
        return None

    pivot = sub.pivot_table(
        index="y_plot_pct",
        columns="x_plot_pct",
        values="z_plot_gt",
        aggfunc="mean",
    ).sort_index().sort_index(axis=1)
    if pivot.isna().any().any():
        return None
    x_sorted = pivot.columns.to_numpy(dtype=float)
    y_sorted = pivot.index.to_numpy(dtype=float)
    x_grid, y_grid = np.meshgrid(x_sorted, y_sorted)
    z_grid = pivot.to_numpy(dtype=float)
    return x_grid, y_grid, z_grid


def _longest_midpoint_and_tangent(segments: Sequence[np.ndarray]) -> Optional[Tuple[float, float, float, float]]:
    best_vertices: Optional[np.ndarray] = None
    best_length = -1.0
    for vertices in segments:
        arr = np.asarray(vertices, dtype=float)
        if arr.ndim != 2 or arr.shape[0] < 2:
            continue
        delta = np.diff(arr, axis=0)
        length = float(np.sum(np.hypot(delta[:, 0], delta[:, 1])))
        if length > best_length:
            best_length = length
            best_vertices = arr
    if best_vertices is None:
        return None

    delta = np.diff(best_vertices, axis=0)
    seglen = np.hypot(delta[:, 0], delta[:, 1])
    if seglen.size == 0:
        return None
    cum = np.concatenate([[0.0], np.cumsum(seglen)])
    half = cum[-1] / 2.0
    idx = int(np.searchsorted(cum, half) - 1)
    idx = int(np.clip(idx, 0, len(seglen) - 1))
    remain = half - cum[idx]
    frac = 0.0 if seglen[idx] == 0 else remain / seglen[idx]
    x = best_vertices[idx, 0] + frac * (best_vertices[idx + 1, 0] - best_vertices[idx, 0])
    y = best_vertices[idx, 1] + frac * (best_vertices[idx + 1, 1] - best_vertices[idx, 1])
    tx = best_vertices[idx + 1, 0] - best_vertices[idx, 0]
    ty = best_vertices[idx + 1, 1] - best_vertices[idx, 1]
    return float(x), float(y), float(tx), float(ty)


def _split_contour_path(path) -> List[np.ndarray]:
    vertices = np.asarray(path.vertices, dtype=float)
    if vertices.ndim != 2 or vertices.shape[0] < 2:
        return []
    codes = path.codes
    if codes is None:
        return [vertices]

    segments: List[np.ndarray] = []
    starts = np.flatnonzero(codes == MplPath.MOVETO)
    if starts.size == 0:
        keep = codes != MplPath.CLOSEPOLY
        segment = vertices[keep]
        return [segment] if segment.shape[0] >= 2 else []

    bounds = np.r_[starts, len(vertices)]
    for start, end in zip(bounds[:-1], bounds[1:]):
        segment = vertices[start:end]
        segment_codes = codes[start:end]
        if segment.shape[0] < 2:
            continue
        segment = segment[segment_codes != MplPath.CLOSEPOLY]
        if segment.shape[0] >= 2 and np.isfinite(segment).all():
            segments.append(segment)
    return segments


def _contour_segments_for_level(contour_set, level: float) -> List[np.ndarray]:
    levels = np.asarray(getattr(contour_set, "levels", []), dtype=float)
    if levels.size == 0 or not hasattr(contour_set, "get_paths"):
        return []
    idx = int(np.nanargmin(np.abs(levels - float(level))))
    if idx >= len(levels) or not np.isclose(levels[idx], float(level), rtol=1e-9, atol=1e-9):
        return []
    paths = contour_set.get_paths()
    if idx >= len(paths):
        return []
    return _split_contour_path(paths[idx])


def _polyline_length(vertices: np.ndarray) -> float:
    arr = np.asarray(vertices, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 2:
        return 0.0
    delta = np.diff(arr, axis=0)
    return float(np.sum(np.hypot(delta[:, 0], delta[:, 1])))


def _chaikin_open_polyline(vertices: np.ndarray) -> np.ndarray:
    arr = np.asarray(vertices, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 3:
        return arr

    pieces = [arr[0]]
    for p0, p1 in zip(arr[:-1], arr[1:]):
        pieces.append(0.75 * p0 + 0.25 * p1)
        pieces.append(0.25 * p0 + 0.75 * p1)
    pieces.append(arr[-1])
    return np.vstack(pieces)


def _config_float(key: str, default: float) -> float:
    value = CONFIG.get(key, default)
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _config_int(key: str, default: int) -> int:
    value = CONFIG.get(key, default)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _config_bool(key: str, default: bool) -> bool:
    value = CONFIG.get(key, default)
    if value is None:
        return bool(default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
    return bool(value)


def _drop_consecutive_duplicate_vertices(vertices: np.ndarray) -> np.ndarray:
    arr = np.asarray(vertices, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 2:
        return arr
    delta = np.diff(arr, axis=0)
    keep = np.r_[True, np.hypot(delta[:, 0], delta[:, 1]) > 1e-9]
    return arr[keep]


def _curve_spline_contour_segment(vertices: np.ndarray) -> np.ndarray:
    if not _config_bool("target_contour_curve_spline", True):
        return vertices

    arr = _drop_consecutive_duplicate_vertices(vertices)
    if arr.ndim != 2 or arr.shape[0] < 4 or not np.isfinite(arr).all():
        return vertices

    delta = np.diff(arr, axis=0)
    seglen = np.hypot(delta[:, 0], delta[:, 1])
    total_length = float(seglen.sum())
    if total_length <= 0:
        return vertices

    u = np.concatenate([[0.0], np.cumsum(seglen) / total_length])
    keep = np.r_[True, np.diff(u) > 1e-9]
    u = u[keep]
    arr = arr[keep]
    if arr.shape[0] < 4:
        return vertices

    min_points = max(2, _config_int("target_contour_curve_min_points", 120))
    max_points = max(min_points, _config_int("target_contour_curve_max_points", 1200))
    points_per_unit = max(0.1, _config_float("target_contour_curve_points_per_unit", 4.0))
    n_points = int(np.clip(np.ceil(total_length * points_per_unit), min_points, max_points))
    u_new = np.linspace(0.0, 1.0, n_points)

    if splprep is not None and splev is not None:
        try:
            smoothing_rms = max(0.0, _config_float("target_contour_curve_smoothing_rms", 1.2))
            smoothing_s = arr.shape[0] * smoothing_rms * smoothing_rms
            k = min(3, arr.shape[0] - 1)
            tck, _ = splprep(
                [arr[:, 0], arr[:, 1]],
                u=u,
                k=k,
                s=smoothing_s,
            )
            x_new, y_new = splev(u_new, tck)
            curved = np.column_stack([x_new, y_new])
            if curved.shape[0] >= 2 and np.isfinite(curved).all():
                return curved
        except Exception:
            pass

    if make_interp_spline is None:
        return vertices
    try:
        k = min(3, arr.shape[0] - 1)
        bc_type = "natural" if k == 3 else None
        x_spline = make_interp_spline(u, arr[:, 0], k=k, bc_type=bc_type)
        y_spline = make_interp_spline(u, arr[:, 1], k=k, bc_type=bc_type)
        curved = np.column_stack([x_spline(u_new), y_spline(u_new)])
        if curved.shape[0] >= 2 and np.isfinite(curved).all():
            return curved
    except Exception:
        return vertices
    return vertices


def _smooth_contour_segment(vertices: np.ndarray) -> np.ndarray:
    arr = np.asarray(vertices, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 3:
        return arr
    out = arr
    iterations = _config_int(
        "target_contour_path_smooth_iterations",
        TARGET_CONTOUR_PATH_SMOOTH_ITERATIONS,
    )
    for _ in range(max(0, iterations)):
        out = _chaikin_open_polyline(out)
    return _curve_spline_contour_segment(out)


def _remove_contour_set(contour_set) -> None:
    try:
        contour_set.remove()
    except Exception:
        for collection in getattr(contour_set, "collections", []):
            try:
                collection.remove()
            except Exception:
                pass


def _draw_smoothed_target_paths(
    ax: plt.Axes,
    contour_set,
    targets: Sequence[Tuple[str, float]],
) -> None:
    min_length = float(TARGET_CONTOUR_MIN_SEGMENT_LENGTH or 0.0)
    linewidth = _config_float("target_contour_linewidth", 3.6)
    segments_by_label: Dict[str, List[np.ndarray]] = {}

    for label, value in targets:
        raw_segments = _contour_segments_for_level(contour_set, value)
        smooth_segments: List[np.ndarray] = []
        for segment in raw_segments:
            if _polyline_length(segment) < min_length:
                continue
            smooth = _smooth_contour_segment(segment)
            if smooth.shape[0] >= 2 and np.isfinite(smooth).all():
                smooth_segments.append(smooth)
                ax.plot(
                    smooth[:, 0],
                    smooth[:, 1],
                    color=TARGET_COLOR_MAP.get(label, "#333333"),
                    linewidth=linewidth,
                    solid_capstyle="round",
                    solid_joinstyle="round",
                    zorder=4,
                )
        segments_by_label[label] = smooth_segments

    for label, value in targets:
        pos = _longest_midpoint_and_tangent(segments_by_label.get(label, []))
        if pos is None:
            continue
        x, y, tx, ty = pos
        _place_label_offline(
            ax,
            x,
            y,
            tx,
            ty,
            label,
            TARGET_COLOR_MAP.get(label, "#333333"),
            offset_pts=3.5,
        )


def _gaussian_kernel1d(sigma: float) -> np.ndarray:
    sigma = float(sigma)
    if sigma <= 0:
        return np.asarray([1.0], dtype=float)
    radius = max(1, int(np.ceil(3.0 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-(x * x) / (2.0 * sigma * sigma))
    kernel_sum = float(kernel.sum())
    return kernel / kernel_sum if kernel_sum > 0 else np.asarray([1.0], dtype=float)


def _smooth_grid_gaussian(z_grid: np.ndarray, sigma: float) -> np.ndarray:
    sigma = float(sigma or 0.0)
    if sigma <= 0:
        return z_grid
    z = np.asarray(z_grid, dtype=float)
    if z.ndim != 2 or min(z.shape) < 3 or not np.isfinite(z).all():
        return z_grid

    kernel = _gaussian_kernel1d(sigma)
    radius = len(kernel) // 2

    def _convolve(values: np.ndarray) -> np.ndarray:
        padded = np.pad(values, radius, mode="edge")
        return np.convolve(padded, kernel, mode="valid")

    smoothed = np.apply_along_axis(_convolve, axis=1, arr=z)
    smoothed = np.apply_along_axis(_convolve, axis=0, arr=smoothed)
    return smoothed


def _smooth_grid_for_surface(z_grid: np.ndarray) -> np.ndarray:
    return _smooth_grid_gaussian(
        z_grid,
        _config_float("surface_smooth_sigma", 0.0),
    )


def _smooth_grid_for_target_contours(z_grid: np.ndarray) -> np.ndarray:
    return _smooth_grid_gaussian(
        z_grid,
        _config_float("target_contour_smooth_sigma", TARGET_CONTOUR_SMOOTH_SIGMA),
    )


def _upsample_rect_grid(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    z_grid: np.ndarray,
    *,
    factor: int,
    method: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    factor = int(factor or 1)
    if factor <= 1:
        return x_grid, y_grid, z_grid

    x = np.asarray(x_grid, dtype=float)
    y = np.asarray(y_grid, dtype=float)
    z = np.asarray(z_grid, dtype=float)
    if x.ndim != 2 or y.ndim != 2 or z.ndim != 2 or x.shape != y.shape or x.shape != z.shape:
        return x_grid, y_grid, z_grid
    if min(z.shape) < 2 or not np.isfinite(z).all():
        return x_grid, y_grid, z_grid

    xs = x[0, :]
    ys = y[:, 0]
    if not (np.all(np.diff(xs) > 0) and np.all(np.diff(ys) > 0)):
        return x_grid, y_grid, z_grid

    x_fine = np.linspace(xs[0], xs[-1], (len(xs) - 1) * factor + 1)
    y_fine = np.linspace(ys[0], ys[-1], (len(ys) - 1) * factor + 1)

    method = str(method or "linear").strip().lower()
    method = {
        "bilinear": "linear",
        "cubic": "cubic_spline",
        "spline": "cubic_spline",
        "nearest_neighbor": "nearest",
    }.get(method, method)

    if method == "cubic_spline" and RectBivariateSpline is not None and len(xs) >= 4 and len(ys) >= 4:
        try:
            spline = RectBivariateSpline(ys, xs, z, kx=3, ky=3, s=0)
            z_fine = spline(y_fine, x_fine)
            x_fine_grid, y_fine_grid = np.meshgrid(x_fine, y_fine)
            return x_fine_grid, y_fine_grid, z_fine
        except Exception as exc:
            print(f"[WARN] cubic_spline contour interpolation failed; falling back to linear: {exc}")
    elif method == "cubic_spline":
        print("[WARN] cubic_spline contour interpolation unavailable; falling back to linear.")

    if method == "nearest":
        x_idx = np.abs(xs[:, None] - x_fine[None, :]).argmin(axis=0)
        y_idx = np.abs(ys[:, None] - y_fine[None, :]).argmin(axis=0)
        z_fine = z[np.ix_(y_idx, x_idx)]
        x_fine_grid, y_fine_grid = np.meshgrid(x_fine, y_fine)
        return x_fine_grid, y_fine_grid, z_fine
    if method != "linear":
        print(f"[WARN] Unknown target contour interpolation {method!r}; falling back to linear.")

    z_x = np.vstack([np.interp(x_fine, xs, row) for row in z])
    z_fine = np.vstack(
        [np.interp(y_fine, ys, z_x[:, col]) for col in range(z_x.shape[1])]
    ).T
    x_fine_grid, y_fine_grid = np.meshgrid(x_fine, y_fine)
    return x_fine_grid, y_fine_grid, z_fine


def _upsample_grid_for_surface(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    z_grid: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    return _upsample_rect_grid(
        x_grid,
        y_grid,
        z_grid,
        factor=max(1, _config_int("surface_upsample", 1)),
        method=str(CONFIG.get("surface_interpolation", "linear") or "linear"),
    )


def _upsample_grid_for_target_contours(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    z_grid: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    return _upsample_rect_grid(
        x_grid,
        y_grid,
        z_grid,
        factor=max(1, _config_int("target_contour_upsample", TARGET_CONTOUR_UPSAMPLE)),
        method=str(CONFIG.get("target_contour_interpolation", "linear") or "linear"),
    )


def _place_label_offline(
    ax: plt.Axes,
    x: float,
    y: float,
    tx: float,
    ty: float,
    text: str,
    color: str,
    *,
    offset_pts: float = 5.0,
) -> None:
    norm = np.hypot(tx, ty) or 1.0
    nx, ny = -ty / norm, tx / norm
    angle = np.degrees(np.arctan2(ty, tx))
    trans = ax.transData + mtransforms.ScaledTranslation(
        nx * offset_pts / 72.0,
        ny * offset_pts / 72.0,
        ax.figure.dpi_scale_trans,
    )
    txt = ax.text(
        x,
        y,
        text,
        color=color,
        fontsize=CONTOUR_LABEL_FONTSIZE,
        fontweight="bold",
        rotation=angle,
        rotation_mode="anchor",
        ha="center",
        va="center",
        transform=trans,
        zorder=5,
    )
    txt.set_path_effects([pe.withStroke(linewidth=2.0, foreground="white", alpha=0.55)])


def _draw_target_contours(
    ax: plt.Axes,
    sub: pd.DataFrame,
    targets: Sequence[Tuple[str, float]],
    grid: Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> None:
    if len(sub) < 3:
        return

    target_labels = [label for label, _ in targets]
    target_values = [value for _, value in targets]
    target_colors = [TARGET_COLOR_MAP.get(label, "#333333") for label in target_labels]

    if grid is not None:
        x_grid, y_grid, z_grid = grid
        z_contour = _smooth_grid_for_target_contours(z_grid)
        x_contour, y_contour, z_contour = _upsample_grid_for_target_contours(
            x_grid,
            y_grid,
            z_contour,
        )
        cs = ax.contour(
            x_contour,
            y_contour,
            z_contour,
            levels=target_values,
            colors=target_colors,
            linewidths=0.1,
            alpha=0.0,
        )
    else:
        cs = ax.tricontour(
            sub["x_plot_pct"].to_numpy(dtype=float),
            sub["y_plot_pct"].to_numpy(dtype=float),
            sub["z_plot_gt"].to_numpy(dtype=float),
            levels=target_values,
            colors=target_colors,
            linewidths=0.1,
            alpha=0.0,
        )

    _draw_smoothed_target_paths(ax, cs, targets)
    _remove_contour_set(cs)


def _draw_benchmark_points(
    ax: plt.Axes,
    forest_pct: float,
    ruminant_pct: float,
) -> None:
    panel_points = [
        item
        for item in BENCHMARK_POINTS
        if float(item["forest_area_change_pct"]) == float(forest_pct)
        and float(item[RUMINANT_CAP_COL]) == float(ruminant_pct)
    ]
    for item in panel_points:
        ax.scatter(
            [item["x"]],
            [item["y"]],
            s=48,
            marker="o",
            facecolors="white",
            edgecolors=item["edgecolor"],
            linewidths=1.4,
            zorder=6,
        )
        txt = ax.text(
            float(item["x"]) + float(item.get("dx", 0.0)),
            float(item["y"]) + float(item.get("dy", 0.0)),
            str(item["label"]),
            fontsize=POINT_LABEL_FONTSIZE,
            color=str(item.get("text_color", "white")),
            fontweight="bold",
            zorder=7,
        )
        txt.set_path_effects([pe.withStroke(linewidth=2.6, foreground="black", alpha=0.18)])


def _draw_panel(
    ax: plt.Axes,
    sub: pd.DataFrame,
    *,
    forest_pct: float,
    ruminant_pct: float,
    panel_letter: str,
    targets: Sequence[Tuple[str, float]],
    norm: Normalize,
    cmap,
    draw_base: bool = True,
    draw_targets: bool = True,
    draw_benchmark_points: bool = True,
    draw_panel_letter: bool = True,
) -> None:
    if draw_panel_letter:
        ax.text(
            0.05,
            0.92,
            panel_letter,
            transform=ax.transAxes,
            fontsize=PANEL_LETTER_FONTSIZE,
            fontweight="bold",
            color="black",
            ha="left",
            va="top",
            zorder=8,
        )

    if sub.empty or len(sub) < 3:
        if draw_base:
            ax.text(
                0.5,
                0.5,
                "No data",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=13,
                color="#666666",
            )
        return

    grid = _rect_grid(sub)
    if draw_base:
        if grid is not None:
            x_grid, y_grid, z_grid = grid
            z_display = _smooth_grid_for_surface(z_grid)
            x_display, y_display, z_display = _upsample_grid_for_surface(
                x_grid,
                y_grid,
                z_display,
            )
            ax.pcolormesh(
                x_display,
                y_display,
                z_display,
                shading="gouraud",
                cmap=cmap,
                norm=norm,
                rasterized=True,
            )
        else:
            ax.tricontourf(
                sub["x_plot_pct"].to_numpy(dtype=float),
                sub["y_plot_pct"].to_numpy(dtype=float),
                sub["z_plot_gt"].to_numpy(dtype=float),
                levels=np.linspace(norm.vmin, norm.vmax, 200),
                cmap=cmap,
                norm=norm,
                antialiased=True,
            )

    if draw_targets:
        _draw_target_contours(ax, sub, targets, grid)
    if draw_benchmark_points:
        _draw_benchmark_points(ax, forest_pct, ruminant_pct)

    if draw_base and SHOW_INTERPOLATED_POINTS and "is_interpolated" in sub.columns:
        interp = sub.loc[sub["is_interpolated"].fillna(False)]
        if not interp.empty:
            ax.scatter(
                interp["x_plot_pct"],
                interp["y_plot_pct"],
                s=7,
                marker="x",
                color="#595959",
                alpha=0.25,
                linewidths=0.6,
                zorder=5,
            )


def _bool_series(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    text = values.fillna(False).astype(str).str.strip().str.lower()
    return text.isin({"1", "true", "t", "yes", "y"})


def _target_crossing_diagnostics(
    z_grid: np.ndarray,
    interp_grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    target_value: float,
) -> Dict[str, float]:
    z = np.asarray(z_grid, dtype=float)
    if z.ndim != 2 or min(z.shape) < 2:
        return {
            "target_crossing_cells": 0,
            "target_any_interpolated_cell_frac": np.nan,
            "target_all_interpolated_cell_frac": np.nan,
            "target_mixed_interpolated_cell_frac": np.nan,
            "target_gradient_p10": np.nan,
            "target_gradient_median": np.nan,
        }

    cell_min = np.minimum.reduce([z[:-1, :-1], z[1:, :-1], z[:-1, 1:], z[1:, 1:]])
    cell_max = np.maximum.reduce([z[:-1, :-1], z[1:, :-1], z[:-1, 1:], z[1:, 1:]])
    crosses = (cell_min <= target_value) & (cell_max >= target_value)
    crossing_count = int(crosses.sum())
    if crossing_count == 0:
        return {
            "target_crossing_cells": 0,
            "target_any_interpolated_cell_frac": np.nan,
            "target_all_interpolated_cell_frac": np.nan,
            "target_mixed_interpolated_cell_frac": np.nan,
            "target_gradient_p10": np.nan,
            "target_gradient_median": np.nan,
        }

    interp = np.asarray(interp_grid, dtype=bool)
    interp_any = interp[:-1, :-1] | interp[1:, :-1] | interp[:-1, 1:] | interp[1:, 1:]
    interp_all = interp[:-1, :-1] & interp[1:, :-1] & interp[:-1, 1:] & interp[1:, 1:]
    interp_mixed = interp_any & ~interp_all

    grad_y, grad_x = np.gradient(z, ys, xs)
    grad = np.hypot(grad_x, grad_y)
    vertex_mask = np.zeros_like(z, dtype=bool)
    vertex_mask[:-1, :-1] |= crosses
    vertex_mask[1:, :-1] |= crosses
    vertex_mask[:-1, 1:] |= crosses
    vertex_mask[1:, 1:] |= crosses
    target_grad = grad[vertex_mask]

    return {
        "target_crossing_cells": crossing_count,
        "target_any_interpolated_cell_frac": float(interp_any[crosses].mean()),
        "target_all_interpolated_cell_frac": float(interp_all[crosses].mean()),
        "target_mixed_interpolated_cell_frac": float(interp_mixed[crosses].mean()),
        "target_gradient_p10": float(np.nanpercentile(target_grad, 10)),
        "target_gradient_median": float(np.nanmedian(target_grad)),
    }


def _build_contour_diagnostics(
    plot_df: pd.DataFrame,
    targets: Sequence[Tuple[str, float]],
) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    forest_levels = sorted(plot_df["forest_area_change_pct"].dropna().unique().tolist())
    ruminant_levels = sorted(plot_df[RUMINANT_CAP_COL].dropna().unique().tolist())

    for forest_pct in forest_levels:
        for ruminant_pct in ruminant_levels:
            sub = plot_df.loc[
                (plot_df["forest_area_change_pct"] == forest_pct)
                & (plot_df[RUMINANT_CAP_COL] == ruminant_pct)
            ].copy()
            grid = _rect_grid(sub)
            base: Dict[str, object] = {
                "forest_area_change_pct": float(forest_pct),
                RUMINANT_CAP_COL: float(ruminant_pct),
                "plot_points": int(len(sub)),
                "unique_x_points": int(sub["x_plot_pct"].nunique()),
                "unique_y_points": int(sub["y_plot_pct"].nunique()),
                "rectangular_grid": bool(grid is not None),
                "duplicate_xy_points": int(sub.duplicated(["x_plot_pct", "y_plot_pct"]).sum()),
                "interpolated_point_frac": float(_bool_series(sub["is_interpolated"]).mean())
                if "is_interpolated" in sub.columns
                else 0.0,
                "z_min_gt": float(sub["z_plot_gt"].min()) if not sub.empty else np.nan,
                "z_max_gt": float(sub["z_plot_gt"].max()) if not sub.empty else np.nan,
            }

            if grid is None:
                for target_label, target_value in targets:
                    row = dict(base)
                    row.update(
                        {
                            "target_label": target_label,
                            "target_value_gt": float(target_value),
                            "target_crossing_cells": np.nan,
                            "target_any_interpolated_cell_frac": np.nan,
                            "target_all_interpolated_cell_frac": np.nan,
                            "target_mixed_interpolated_cell_frac": np.nan,
                            "target_gradient_p10": np.nan,
                            "target_gradient_median": np.nan,
                        }
                    )
                    rows.append(row)
                continue

            x_grid, y_grid, z_grid = grid
            xs = x_grid[0, :].astype(float)
            ys = y_grid[:, 0].astype(float)
            interp_sub = sub.assign(_is_interpolated_bool=_bool_series(sub["is_interpolated"]))
            interp_grid = (
                interp_sub.pivot_table(
                    index="y_plot_pct",
                    columns="x_plot_pct",
                    values="_is_interpolated_bool",
                    aggfunc="max",
                )
                .sort_index()
                .sort_index(axis=1)
                .fillna(False)
                .to_numpy(dtype=bool)
            )

            dx = np.diff(z_grid, axis=1)
            dy = np.diff(z_grid, axis=0)
            interp_edges_x = np.abs(np.diff(interp_grid.astype(float), axis=1)) > 0
            interp_edges_y = np.abs(np.diff(interp_grid.astype(float), axis=0)) > 0
            base.update(
                {
                    "max_abs_dx_gt": float(np.nanmax(np.abs(dx))) if dx.size else np.nan,
                    "max_abs_dy_gt": float(np.nanmax(np.abs(dy))) if dy.size else np.nan,
                    "p99_abs_dx_gt": float(np.nanpercentile(np.abs(dx), 99)) if dx.size else np.nan,
                    "p99_abs_dy_gt": float(np.nanpercentile(np.abs(dy), 99)) if dy.size else np.nan,
                    "smooth_residual_rms_gt": float(
                        np.sqrt(np.nanmean((z_grid - _smooth_grid_for_target_contours(z_grid)) ** 2))
                    ),
                    "interpolation_edges_x": int(np.nansum(interp_edges_x)),
                    "interpolation_edges_y": int(np.nansum(interp_edges_y)),
                }
            )

            for target_label, target_value in targets:
                row = dict(base)
                row.update(
                    {
                        "target_label": target_label,
                        "target_value_gt": float(target_value),
                    }
                )
                row.update(
                    _target_crossing_diagnostics(
                        z_grid,
                        interp_grid,
                        xs,
                        ys,
                        float(target_value),
                    )
                )
                rows.append(row)

    return pd.DataFrame(rows)


def _save_contour_figure(
    plot_df: pd.DataFrame,
    targets: Sequence[Tuple[str, float]],
    *,
    mode: str,
    svg_path: Path,
    png_path: Optional[Path] = None,
    bbox_inches: Optional[str] = None,
) -> List[Path]:
    forest_levels = sorted(plot_df["forest_area_change_pct"].dropna().unique().tolist())
    ruminant_levels = sorted(plot_df[RUMINANT_CAP_COL].dropna().unique().tolist())
    if not forest_levels or not ruminant_levels:
        raise ValueError("No forest/ruminant panel levels found in panel dataset.")

    mode = str(mode).strip().lower()
    if mode not in {"base", "target_lines", "combined"}:
        raise ValueError(f"Unknown contour figure mode: {mode!r}")

    draw_base = mode in {"base", "combined"}
    draw_targets = mode in {"target_lines", "combined"}
    draw_benchmark_points = mode == "combined"
    draw_decorations = mode == "combined"
    draw_colorbar = mode in {"base", "combined"}
    transparent = mode == "target_lines"

    norm, cmap, colorbar_extend = _build_color_scale(plot_df)

    x_all = plot_df["x_plot_pct"].to_numpy(dtype=float)
    y_all = plot_df["y_plot_pct"].to_numpy(dtype=float)
    x_pad = (np.nanmax(x_all) - np.nanmin(x_all)) * float(PANEL_AXIS_PADDING_FRACTION)
    y_pad = (np.nanmax(y_all) - np.nanmin(y_all)) * float(PANEL_AXIS_PADDING_FRACTION)
    xlim = (float(np.nanmin(x_all) - x_pad), float(np.nanmax(x_all) + x_pad))
    ylim = (float(np.nanmin(y_all) - y_pad), float(np.nanmax(y_all) + y_pad))

    fig = plt.figure(figsize=(FIG_WIDTH, FIG_HEIGHT))
    if transparent:
        fig.patch.set_alpha(0.0)
    gs = fig.add_gridspec(
        nrows=len(forest_levels),
        ncols=len(ruminant_levels) + 1,
        width_ratios=[1.0] * len(ruminant_levels) + [0.05],
        wspace=0.18,
        hspace=0.10,
    )

    axes: List[List[plt.Axes]] = []
    for row_idx, forest_pct in enumerate(forest_levels):
        row_axes: List[plt.Axes] = []
        for col_idx, rumi_pct in enumerate(ruminant_levels):
            ax = fig.add_subplot(gs[row_idx, col_idx])
            if transparent:
                ax.patch.set_alpha(0.0)
            row_axes.append(ax)
            sub = plot_df.loc[
                (plot_df["forest_area_change_pct"] == forest_pct)
                & (plot_df[RUMINANT_CAP_COL] == rumi_pct)
            ].copy()
            panel_letter = chr(ord("a") + row_idx * len(ruminant_levels) + col_idx)
            _draw_panel(
                ax,
                sub,
                forest_pct=float(forest_pct),
                ruminant_pct=float(rumi_pct),
                panel_letter=panel_letter,
                targets=targets,
                norm=norm,
                cmap=cmap,
                draw_base=draw_base,
                draw_targets=draw_targets,
                draw_benchmark_points=draw_benchmark_points,
                draw_panel_letter=draw_decorations,
            )
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            if draw_decorations:
                for spine in ax.spines.values():
                    spine.set_linewidth(1.6)
                ax.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE, width=1.4, length=6)
                if row_idx != len(forest_levels) - 1:
                    ax.set_xticklabels([])
                if col_idx != 0:
                    ax.set_yticklabels([])
            else:
                ax.set_axis_off()
        axes.append(row_axes)

    cax = fig.add_subplot(gs[:, -1])
    if draw_colorbar:
        cbar = fig.colorbar(
            plt.cm.ScalarMappable(norm=norm, cmap=cmap),
            cax=cax,
            extend=colorbar_extend,
        )
        if draw_decorations:
            cbar.set_label("AFOLU GHG emissions (Gt CO2-eq per year)", fontsize=COLORBAR_LABEL_FONTSIZE)
            cbar.ax.tick_params(labelsize=TICK_LABEL_FONTSIZE, width=1.2, length=5)
        else:
            cbar.ax.set_axis_off()
    else:
        cax.set_axis_off()
        cax.patch.set_alpha(0.0)

    if draw_decorations:
        for col_idx, rumi_pct in enumerate(ruminant_levels):
            axes[0][col_idx].set_title(
                _panel_title_for_ruminant(rumi_pct),
                fontsize=COL_LABEL_FONTSIZE,
                fontweight="bold",
                pad=10,
            )

        for row_idx, forest_pct in enumerate(forest_levels):
            bbox = axes[row_idx][0].get_position()
            fig.text(
                bbox.x0 - 0.07,
                (bbox.y0 + bbox.y1) / 2.0,
                _row_title_for_forest(forest_pct),
                rotation=90,
                ha="center",
                va="center",
                fontsize=ROW_LABEL_FONTSIZE,
                fontweight="bold",
            )

        fig.text(
            0.5,
            0.03,
            "Relative change in current emission intensity (%)",
            ha="center",
            va="center",
            fontsize=AXIS_LABEL_FONTSIZE,
            fontweight="bold",
        )
        fig.text(
            0.03,
            0.5,
            "Relative change in cropland + pasture land intensity, L/A (%)",
            ha="center",
            va="center",
            rotation=90,
            fontsize=AXIS_LABEL_FONTSIZE,
            fontweight="bold",
        )

    fig.subplots_adjust(left=0.10, right=0.92, top=0.93, bottom=0.08)

    outputs: List[Path] = []
    if png_path is not None:
        fig.savefig(png_path, dpi=800, bbox_inches=bbox_inches, transparent=transparent)
        outputs.append(png_path)
    fig.savefig(svg_path, bbox_inches=bbox_inches, transparent=transparent)
    outputs.append(svg_path)
    plt.close(fig)
    return outputs


def _save_colorbar_legend(plot_df: pd.DataFrame, svg_path: Path) -> Path:
    norm, cmap, colorbar_extend = _build_color_scale(plot_df)
    fig = plt.figure(figsize=(1.45, 5.8))
    cax = fig.add_axes([0.30, 0.08, 0.22, 0.84])
    cbar = fig.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        extend=colorbar_extend,
    )
    cbar.set_label("AFOLU GHG emissions (Gt CO2-eq per year)", fontsize=COLORBAR_LABEL_FONTSIZE)
    cbar.ax.tick_params(labelsize=TICK_LABEL_FONTSIZE, width=1.2, length=5)
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    return svg_path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the manuscript Figure 2 3x3 AFOLU contour panels."
    )
    parser.add_argument(
        "--panel-dir",
        type=Path,
        default=None,
        help="Directory containing merged S5_3 panel CSVs.",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=None,
        help="Figure/data output directory. Default: <NZF_OUTPUT_DIR>/Plot/Fig1.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--plot-only",
        dest="plot_only",
        action="store_true",
        help="Use the existing Figure1_AFOLU_contour_plot_data.csv.",
    )
    mode.add_argument(
        "--rebuild-plot-data",
        dest="plot_only",
        action="store_false",
        help="Rebuild plot data and diagnostics from merged S5_3 outputs before plotting.",
    )
    parser.set_defaults(plot_only=None)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    global PANEL_DIR, FIG_DIR
    args = _build_arg_parser().parse_args(argv)
    if args.panel_dir is not None:
        PANEL_DIR = Path(args.panel_dir).expanduser().resolve()
    if args.figure_dir is not None:
        FIG_DIR = Path(args.figure_dir).expanduser().resolve()
    if args.plot_only is not None:
        CONFIG["plot_only"] = int(bool(args.plot_only))

    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    _ensure_dir(FIG_DIR)

    plot_only = int(CONFIG.get("plot_only", 0) or 0) == 1
    plot_data_path = FIG_DIR / PLOT_DATA_NAME
    diagnostics_path: Optional[Path] = None
    if plot_only:
        plot_df = _load_existing_plot_data(plot_data_path)
        input_path = plot_data_path
        print(f"[INFO] plot_only=1, using existing plot data: {plot_data_path}")
    else:
        input_path, input_df = _choose_input_dataset()
        plot_df = _prepare_plot_data(input_df, input_path)
        plot_data_path = _write_csv_with_lock_fallback(plot_df, plot_data_path)

    targets = _load_targets()
    if not plot_only:
        diagnostics_df = _build_contour_diagnostics(plot_df, targets)
        diagnostics_path = _write_csv_with_lock_fallback(diagnostics_df, FIG_DIR / DIAGNOSTICS_NAME)

    print(f"[INFO] contour input: {input_path}")
    print(f"[INFO] plot points: {len(plot_df)}")
    print(f"[INFO] targets: {targets}")

    png_path = FIG_DIR / f"{OUTPUT_STEM}.png"
    svg_path = FIG_DIR / f"{OUTPUT_STEM}.svg"
    base_png_path = FIG_DIR / f"{OUTPUT_STEM}_base.png"
    base_svg_path = FIG_DIR / f"{OUTPUT_STEM}_base.svg"
    target_svg_path = FIG_DIR / f"{OUTPUT_STEM}_target_lines.svg"
    combined_svg_path = FIG_DIR / f"{OUTPUT_STEM}_combined.svg"
    legend_svg_path = FIG_DIR / f"{OUTPUT_STEM}_legend.svg"

    output_paths: List[Path] = []
    output_paths.extend(
        _save_contour_figure(
            plot_df,
            targets,
            mode="combined",
            png_path=png_path,
            svg_path=svg_path,
            bbox_inches="tight",
        )
    )
    output_paths.extend(
        _save_contour_figure(
            plot_df,
            targets,
            mode="base",
            png_path=base_png_path,
            svg_path=base_svg_path,
            bbox_inches=None,
        )
    )
    output_paths.extend(
        _save_contour_figure(
            plot_df,
            targets,
            mode="target_lines",
            svg_path=target_svg_path,
            bbox_inches=None,
        )
    )
    output_paths.extend(
        _save_contour_figure(
            plot_df,
            targets,
            mode="combined",
            svg_path=combined_svg_path,
            bbox_inches=None,
        )
    )
    output_paths.append(_save_colorbar_legend(plot_df, legend_svg_path))

    for path in output_paths:
        print(f"[DONE] {path}")
    print(f"[DONE] {plot_data_path}")
    if diagnostics_path is not None:
        print(f"[DONE] {diagnostics_path}")


if __name__ == "__main__":
    main()
