# -*- coding: utf-8 -*-
"""PALE-factor version of the AFOLU contour figure.

This figure uses realized PALE factors from S5.3 outputs:

    E = P * (A/P) * (L/A) * (E_LUC/L) + P * (A/P) * (E_Ag/A)

where L is cropland + pasture/grassland.  The heatmap is the PALE identity
evaluated over L/A and E_Ag/A perturbations around each panel's reference row;
model runs are overlaid as points at their realized PALE coordinates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config_paths import get_results_base
from SP_M2_Figure_contour import DEFAULT_TARGETS, TARGET_COLOR_MAP


RESULTS_BASE = Path(get_results_base())
PANEL_DIR = RESULTS_BASE / "Panel_Yield_EF"
FIG_DIR = RESULTS_BASE / "Plot" / "Fig1"

RUMINANT_CAP_COL = "ruminant_kcal_share_cap_pct"
DEPRECATED_RUMINANT_CAP_COL = "ruminant_intake_change_pct"

INPUT_PRIORITIES = {
    "figure_panel_dataset_long_plot_ready.csv": 3,
    "figure_panel_dataset_long.csv": 2,
    "figure_panel_dataset_long_rebuilt.csv": 1,
}

OUTPUT_STEM = "Figure1_AFOLU_contour_pale_v2"
PLOT_DATA_NAME = f"{OUTPUT_STEM}_plot_data.csv"
SUMMARY_NAME = f"{OUTPUT_STEM}_summary.csv"

CONFIG = {
    "target_year": 2080,
    "baseline_forest_pct": 0.0,
    "baseline_ruminant_cap_pct": 13.0,
    "baseline_yield_pct": 0.0,
    "baseline_ef_pct": 0.0,
    "grid_n": 180,
    "xlim": None,  # None -> observed PALE point range with padding
    "ylim": None,
    "point_size": 6,
    "point_alpha": 0.22,
    "dpi": 300,
}

REQUIRED_PALE_COLS = [
    "pale_population",
    "pale_ag_output_kcal",
    "pale_land_cropland_pasture_ha",
    "pale_luc_emissions_gt_co2eq_yr",
    "pale_ag_production_emissions_gt_co2eq_yr",
    "pale_a_per_p_kcal_cap_yr",
    "pale_l_per_a_ha_per_kcal",
    "pale_luc_intensity_gt_per_ha",
    "pale_ag_intensity_gt_per_kcal",
]


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _normalise_ruminant_col(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if RUMINANT_CAP_COL not in out.columns and DEPRECATED_RUMINANT_CAP_COL in out.columns:
        out = out.rename(columns={DEPRECATED_RUMINANT_CAP_COL: RUMINANT_CAP_COL})
    elif RUMINANT_CAP_COL in out.columns and DEPRECATED_RUMINANT_CAP_COL in out.columns:
        out[RUMINANT_CAP_COL] = out[RUMINANT_CAP_COL].where(
            out[RUMINANT_CAP_COL].notna(),
            out[DEPRECATED_RUMINANT_CAP_COL],
        )
        out = out.drop(columns=[DEPRECATED_RUMINANT_CAP_COL])
    return out


def _choose_input_dataset() -> Tuple[Path, pd.DataFrame]:
    best_path: Optional[Path] = None
    best_df: Optional[pd.DataFrame] = None
    best_score = -1
    for name, priority in INPUT_PRIORITIES.items():
        path = PANEL_DIR / name
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, low_memory=False)
        except Exception:
            continue
        score = priority * 1_000_000 + len(df)
        if score > best_score:
            best_score = score
            best_path = path
            best_df = df
    if best_path is None or best_df is None:
        raise FileNotFoundError(f"No usable panel dataset found under {PANEL_DIR}")
    return best_path, best_df


def _require_pale_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_PALE_COLS if c not in df.columns]
    if missing:
        raise RuntimeError(
            "PALE columns are missing from the panel dataset. "
            "Rerun S5_3_1_sensitivity_panel_yield_ef.py and then "
            "S5_3_2_panel_data_summary.py so the S5.3 table includes: "
            + ", ".join(missing)
        )


def _closest_reference_row(df: pd.DataFrame, *, forest_pct: Optional[float] = None, rumi_pct: Optional[float] = None) -> pd.Series:
    work = df.copy()
    valid = pd.Series(True, index=work.index)
    for col in REQUIRED_PALE_COLS:
        vals = _safe_numeric(work[col])
        valid &= vals.notna() & np.isfinite(vals)
    work = work.loc[valid].copy()
    if work.empty:
        raise RuntimeError("No rows with complete PALE factors are available.")

    def axis_distance(col: str, target: Optional[float]) -> pd.Series:
        if target is None or col not in work.columns:
            return pd.Series(0.0, index=work.index)
        return (_safe_numeric(work[col]) - float(target)).abs()

    score = (
        axis_distance("forest_area_change_pct", forest_pct if forest_pct is not None else CONFIG["baseline_forest_pct"])
        + axis_distance(RUMINANT_CAP_COL, rumi_pct if rumi_pct is not None else CONFIG["baseline_ruminant_cap_pct"])
        + axis_distance("yield_change_pct", CONFIG["baseline_yield_pct"])
        + axis_distance("emission_factor_change_pct", CONFIG["baseline_ef_pct"])
    )
    return work.loc[score.sort_values().index[0]]


def _prepare_pale_plot_data(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalise_ruminant_col(df)
    _require_pale_columns(df)

    required = [
        "scenario_id",
        "forest_area_change_pct",
        RUMINANT_CAP_COL,
        "yield_change_pct",
        "emission_factor_change_pct",
        "afolu_emissions_gt_co2eq_yr",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError("Panel dataset missing required columns: " + ", ".join(missing))

    out = df.copy()
    numeric_cols = required[1:] + REQUIRED_PALE_COLS
    for col in numeric_cols:
        out[col] = _safe_numeric(out[col])

    if "plot_data_status" in out.columns:
        out = out.loc[out["plot_data_status"].astype(str).str.lower().eq("observed")].copy()
    elif "run_status" in out.columns:
        out = out.loc[out["run_status"].astype(str).str.lower().isin({"ok", "resumed"})].copy()

    complete = pd.Series(True, index=out.index)
    for col in REQUIRED_PALE_COLS:
        complete &= out[col].notna() & np.isfinite(out[col])
    out = out.loc[complete].copy()
    if out.empty:
        raise RuntimeError("No observed S5.3 rows have complete PALE factors.")

    ref = _closest_reference_row(out)
    ref_l = float(ref["pale_l_per_a_ha_per_kcal"])
    ref_f = float(ref["pale_ag_intensity_gt_per_kcal"])
    if ref_l <= 0 or ref_f <= 0:
        raise RuntimeError("Reference row has non-positive PALE L/A or E_Ag/A.")

    out["x_pale_ag_intensity_change_pct"] = (out["pale_ag_intensity_gt_per_kcal"] / ref_f - 1.0) * 100.0
    out["y_pale_land_intensity_change_pct"] = (out["pale_l_per_a_ha_per_kcal"] / ref_l - 1.0) * 100.0
    out["point_emissions_gt"] = out["pale_total_emissions_gt_co2eq_yr"].where(
        out["pale_total_emissions_gt_co2eq_yr"].notna(),
        out["afolu_emissions_gt_co2eq_yr"],
    )
    out["pale_reference_scenario_id"] = str(ref.get("scenario_id", ""))
    out["pale_reference_l_per_a_ha_per_kcal"] = ref_l
    out["pale_reference_ag_intensity_gt_per_kcal"] = ref_f
    return out


def _axis_limits(values: pd.Series, configured) -> Tuple[float, float]:
    if configured is not None:
        lo, hi = configured
        return float(lo), float(hi)
    vals = _safe_numeric(values).replace([np.inf, -np.inf], np.nan).dropna()
    if vals.empty:
        return -60.0, 60.0
    lo = float(np.nanpercentile(vals, 1))
    hi = float(np.nanpercentile(vals, 99))
    if lo == hi:
        lo -= 1.0
        hi += 1.0
    pad = (hi - lo) * 0.08
    return lo - pad, hi + pad


def _panel_reference(sub: pd.DataFrame, all_df: pd.DataFrame, forest_pct: float, rumi_pct: float) -> pd.Series:
    try:
        return _closest_reference_row(sub, forest_pct=forest_pct, rumi_pct=rumi_pct)
    except RuntimeError:
        return _closest_reference_row(all_df, forest_pct=forest_pct, rumi_pct=rumi_pct)


def _pale_surface(
    ref: pd.Series,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    grid_n: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.linspace(xlim[0], xlim[1], int(grid_n))
    y = np.linspace(ylim[0], ylim[1], int(grid_n))
    xx, yy = np.meshgrid(x, y)

    population = float(ref["pale_population"])
    a_per_p = float(ref["pale_a_per_p_kcal_cap_yr"])
    l_per_a = float(ref["pale_l_per_a_ha_per_kcal"]) * (1.0 + yy / 100.0)
    luc_intensity = float(ref["pale_luc_intensity_gt_per_ha"])
    ag_intensity = float(ref["pale_ag_intensity_gt_per_kcal"]) * (1.0 + xx / 100.0)
    zz = population * a_per_p * l_per_a * luc_intensity + population * a_per_p * ag_intensity
    return xx, yy, zz


def _row_title(forest_pct: float) -> str:
    val = int(round(float(forest_pct)))
    if val < 0:
        return f"Net forest target {abs(val)}% below baseline"
    if val > 0:
        return f"Net forest target {val}% above baseline"
    return "Net forest target at baseline"


def _col_title(rumi_pct: float) -> str:
    return f"Ruminant kcal cap {float(rumi_pct):.0f}%"


def _build_summary(plot_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (forest, rumi), sub in plot_df.groupby(["forest_area_change_pct", RUMINANT_CAP_COL], dropna=False):
        rows.append(
            {
                "forest_area_change_pct": forest,
                RUMINANT_CAP_COL: rumi,
                "rows": len(sub),
                "x_min": sub["x_pale_ag_intensity_change_pct"].min(),
                "x_max": sub["x_pale_ag_intensity_change_pct"].max(),
                "y_min": sub["y_pale_land_intensity_change_pct"].min(),
                "y_max": sub["y_pale_land_intensity_change_pct"].max(),
                "model_emissions_mean_gt": sub["point_emissions_gt"].mean(),
                "model_emissions_min_gt": sub["point_emissions_gt"].min(),
                "model_emissions_max_gt": sub["point_emissions_gt"].max(),
            }
        )
    return pd.DataFrame(rows)


def plot_pale_figure(plot_df: pd.DataFrame, targets: Sequence[Tuple[str, float]]) -> Tuple[Path, Path]:
    forest_levels = sorted(plot_df["forest_area_change_pct"].dropna().unique().tolist())
    rumi_levels = sorted(plot_df[RUMINANT_CAP_COL].dropna().unique().tolist())
    xlim = _axis_limits(plot_df["x_pale_ag_intensity_change_pct"], CONFIG["xlim"])
    ylim = _axis_limits(plot_df["y_pale_land_intensity_change_pct"], CONFIG["ylim"])
    grid_n = int(CONFIG["grid_n"])

    panel_surfaces: Dict[Tuple[float, float], Tuple[np.ndarray, np.ndarray, np.ndarray, pd.Series]] = {}
    z_values = []
    for forest in forest_levels:
        for rumi in rumi_levels:
            sub = plot_df.loc[
                (plot_df["forest_area_change_pct"] == forest)
                & (plot_df[RUMINANT_CAP_COL] == rumi)
            ]
            ref = _panel_reference(sub, plot_df, float(forest), float(rumi))
            xx, yy, zz = _pale_surface(ref, xlim, ylim, grid_n)
            panel_surfaces[(float(forest), float(rumi))] = (xx, yy, zz, ref)
            z_values.append(zz[np.isfinite(zz)])

    z_all = np.concatenate(z_values) if z_values else np.array([0.0, 1.0])
    vmin = float(np.nanpercentile(z_all, 2))
    vmax = float(np.nanpercentile(z_all, 98))
    if vmin == vmax:
        vmin -= 1.0
        vmax += 1.0

    fig = plt.figure(figsize=(13.8, 12.0))
    gs = fig.add_gridspec(
        nrows=len(forest_levels),
        ncols=len(rumi_levels) + 1,
        width_ratios=[1.0] * len(rumi_levels) + [0.05],
        wspace=0.18,
        hspace=0.14,
    )

    axes: List[List[plt.Axes]] = []
    last_mesh = None
    for row_idx, forest in enumerate(forest_levels):
        row_axes: List[plt.Axes] = []
        for col_idx, rumi in enumerate(rumi_levels):
            ax = fig.add_subplot(gs[row_idx, col_idx])
            row_axes.append(ax)
            xx, yy, zz, ref = panel_surfaces[(float(forest), float(rumi))]
            last_mesh = ax.pcolormesh(xx, yy, zz, shading="auto", cmap="Spectral_r", vmin=vmin, vmax=vmax)

            zmin = float(np.nanmin(zz))
            zmax = float(np.nanmax(zz))
            levels = [float(v) for _, v in targets if zmin <= float(v) <= zmax]
            if levels:
                colors = [TARGET_COLOR_MAP.get(label, "#333333") for label, val in targets if zmin <= float(val) <= zmax]
                cs = ax.contour(xx, yy, zz, levels=levels, colors=colors, linewidths=2.0)
                label_map = {float(val): label for label, val in targets}
                ax.clabel(cs, fmt=lambda val: label_map.get(float(val), f"{val:g}"), inline=True, fontsize=9)

            sub = plot_df.loc[
                (plot_df["forest_area_change_pct"] == forest)
                & (plot_df[RUMINANT_CAP_COL] == rumi)
            ]
            ax.scatter(
                sub["x_pale_ag_intensity_change_pct"],
                sub["y_pale_land_intensity_change_pct"],
                s=float(CONFIG["point_size"]),
                c="black",
                alpha=float(CONFIG["point_alpha"]),
                linewidths=0,
            )
            ax.scatter(
                [0],
                [0],
                s=52,
                marker="*",
                c="white",
                edgecolors="black",
                linewidths=0.8,
                zorder=5,
            )

            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            ax.tick_params(axis="both", labelsize=9)
            if row_idx == 0:
                ax.set_title(_col_title(float(rumi)), fontsize=11, fontweight="bold")
            if col_idx != 0:
                ax.set_yticklabels([])
            if row_idx != len(forest_levels) - 1:
                ax.set_xticklabels([])
        axes.append(row_axes)

    cax = fig.add_subplot(gs[:, -1])
    if last_mesh is not None:
        cbar = fig.colorbar(last_mesh, cax=cax)
        cbar.set_label("AFOLU emissions from PALE identity (Gt CO2-eq per year)", fontsize=11)
        cbar.ax.tick_params(labelsize=9)

    for row_idx, forest in enumerate(forest_levels):
        bbox = axes[row_idx][0].get_position()
        fig.text(
            bbox.x0 - 0.07,
            (bbox.y0 + bbox.y1) / 2.0,
            _row_title(float(forest)),
            rotation=90,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
        )

    fig.text(
        0.5,
        0.035,
        "Realized change in agricultural production emissions intensity, E_Ag/A (%)",
        ha="center",
        fontsize=12,
        fontweight="bold",
    )
    fig.text(
        0.035,
        0.5,
        "Realized change in cropland + pasture land intensity, L/A (%)",
        va="center",
        rotation=90,
        fontsize=12,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.985,
        "PALE-factor decomposition surface with realized S5.3 model runs overlaid",
        ha="center",
        va="top",
        fontsize=13,
        fontweight="bold",
    )

    png_path = FIG_DIR / f"{OUTPUT_STEM}.png"
    svg_path = FIG_DIR / f"{OUTPUT_STEM}.svg"
    fig.savefig(png_path, dpi=int(CONFIG["dpi"]), bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    return png_path, svg_path


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 10
    _ensure_dir(FIG_DIR)

    input_path, input_df = _choose_input_dataset()
    try:
        plot_df = _prepare_pale_plot_data(input_df)
    except RuntimeError as exc:
        print(f"[PALE-FIG][ERROR] {exc}")
        raise SystemExit(1) from None
    plot_data_path = FIG_DIR / PLOT_DATA_NAME
    plot_df.to_csv(plot_data_path, index=False, encoding="utf-8-sig")
    summary_path = FIG_DIR / SUMMARY_NAME
    _build_summary(plot_df).to_csv(summary_path, index=False, encoding="utf-8-sig")
    png_path, svg_path = plot_pale_figure(plot_df, DEFAULT_TARGETS)

    print(f"[PALE-FIG] input={input_path}")
    print(f"[PALE-FIG] plot_data={plot_data_path} rows={len(plot_df)}")
    print(f"[PALE-FIG] summary={summary_path}")
    print(f"[PALE-FIG] output={png_path}")
    print(f"[PALE-FIG] output={svg_path}")


if __name__ == "__main__":
    main()
