# -*- coding: utf-8 -*-
"""
Rebuild Figure 2 sensitivity plotting workbook from S5_0 outputs and plot it.

Inputs:
- output/MC_Sensitivity/summary/importance_by_variable.csv
- fallback: output/MC_Sensitivity/summary/importance_detail.csv

Outputs:
- output/Plot/Fig2/Figure2_v3.xlsx
- output/Plot/Fig2/Figure2_sensitivity_stack_v3.png
- output/Plot/Fig2/Figure2_sensitivity_stack_v3.svg
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.signal import savgol_filter

from config_paths import get_results_base


CONFIG = {
    "current_afolu_ghg_gt": 12.9,
    "x_min_gt": -3.0,
    "x_max_gt": 60.0,
    "stack_order_target_emis_gt": -3.0,
    "smooth_plot": True,
    "smooth_method": "savgol",
    "smooth_window": 21,
    "smooth_polyorder": 2,
    "smooth_iterations": 2,
    "plot_interpolation_points": 500,
    "dpi": 800,
    "min_required_samples": 80,
}

DISPLAY_ORDER = [
    "Yield rate",
    "Feed efficiency",
    "Fertilizer rate",
    "Losses rate",
    "Ruminate rate",
    "Manure management",
    "Crop management",
    "Emission control",
    "Land carbon price",
]

STRATEGY_COLORS = {
    "Reduce Ruminate": "#6a51a3",
    "Improve yield rate": "#ce4e55",
    "Manure management": "#225ea8",
    "Improve feed efficiency": "#fb9a99",
    "Enteric fermentation management": "#41b6c4",
    "Emission control": "#67a863",
    "Improve fertilizer efficiency": "#edf8b1",
    "Rice cultivation": "#7fcdbb",
    "Crop residue management": "#1d91c0",
    "Reduce waste": "#cbbcdc",
    "Land carbon price": "#4d4d4d",
}

DISPLAY_ALIASES = {
    "Ruminate rate": "Reduce Ruminate",
    "Yield rate": "Improve yield rate",
    "Manure management": "Manure management",
    "Feed efficiency": "Improve feed efficiency",
    "Emission control": "Emission control",
    "Fertilizer rate": "Improve fertilizer efficiency",
    "Losses rate": "Reduce waste",
    "Crop management": "Crop residue management",
    "Land carbon price": "Land carbon price",
}

PARAMETER_NAME_MAP = {
    "yield_rate": "Yield rate",
    "yield_multiplier": "Yield rate",
    "feed_efficiency": "Feed efficiency",
    "feed_intensity": "Feed efficiency",
    "fertilizer_rate": "Fertilizer rate",
    "losses_ratio": "Losses rate",
    "waste_reduction": "Losses rate",
    "losses_rate": "Losses rate",
    "ruminant_reduction": "Ruminate rate",
    "ruminant_intake_ratio": "Ruminate rate",
    "manure_management_ratio": "Manure management",
    "crop_soil_management_ratio": "Crop management",
    "crop_management": "Crop management",
    "emission_factor": "Emission control",
    "emission_control": "Emission control",
    "land_carbon_price": "Land carbon price",
    "land carbon price": "Land carbon price",
}


def _results_root() -> Path:
    return Path(get_results_base())


def _summary_dir() -> Path:
    return _results_root() / "MC_Sensitivity" / "summary"


def _fig_dir() -> Path:
    path = _results_root() / "Plot" / "Fig2"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_run_meta() -> Dict[str, object]:
    meta_path = _summary_dir() / "run_meta.csv"
    samples_path = _summary_dir() / "samples.csv"
    meta: Dict[str, object] = {}
    if meta_path.exists():
        try:
            meta_df = pd.read_csv(meta_path)
            if not meta_df.empty:
                meta = {
                    str(k): v for k, v in meta_df.iloc[0].to_dict().items()
                    if pd.notna(v)
                }
        except Exception:
            meta = {}
    if "valid_samples" not in meta and samples_path.exists():
        try:
            meta["valid_samples"] = int(len(pd.read_csv(samples_path)))
        except Exception:
            pass
    return meta


def _color_for_var(var_name: str) -> str:
    canonical = DISPLAY_ALIASES.get(var_name, var_name)
    return STRATEGY_COLORS.get(canonical, "#999999")


def _pick_emis_row(df: pd.DataFrame, target: float) -> pd.Series:
    if df.empty or "Emis" not in df.columns:
        raise ValueError("Sensitivity table is empty or missing Emis.")
    emis = pd.to_numeric(df["Emis"], errors="coerce")
    if emis.isna().all():
        raise ValueError("Emis column is not numeric.")
    idx = (emis - float(target)).abs().idxmin()
    row = df.loc[idx]
    if isinstance(row, pd.DataFrame):
        return row.iloc[0]
    return row


def _normalize_parameter_name(raw: object) -> str:
    text = str(raw or "").strip().lower()
    return PARAMETER_NAME_MAP.get(text, str(raw or "").strip())


def _load_group_importance_long() -> pd.DataFrame:
    summary_dir = _summary_dir()
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
                        f"Found up to {int(n_samples.max())} valid samples, "
                        f"but at least {int(CONFIG['min_required_samples'])} are required."
                    )
            group_df["importance"] = pd.to_numeric(group_df["importance"], errors="coerce")
            if group_df["importance"].notna().any():
                out = group_df[["target_emission_gt", "parameter", "importance"]].copy()
                out["display_name"] = out["parameter"].map(_normalize_parameter_name)
                return (
                    out.groupby(["target_emission_gt", "display_name"], as_index=False)["importance"]
                    .sum()
                    .rename(columns={"target_emission_gt": "Emis"})
                )

    if detail_path.exists():
        detail_df = pd.read_csv(detail_path)
        detail_df.columns = [str(c).strip() for c in detail_df.columns]
        if {"target_emission_gt", "importance"}.issubset(detail_df.columns):
            source_col = "group" if "group" in detail_df.columns else "parameter"
            detail_df["importance"] = pd.to_numeric(detail_df["importance"], errors="coerce")
            if detail_df["importance"].notna().any():
                out = detail_df[["target_emission_gt", source_col, "importance"]].copy()
                out["display_name"] = out[source_col].map(_normalize_parameter_name)
                return (
                    out.groupby(["target_emission_gt", "display_name"], as_index=False)["importance"]
                    .sum()
                    .rename(columns={"target_emission_gt": "Emis"})
                )

    raise FileNotFoundError(
        "No usable sensitivity importance result found. Expected valid values in "
        f"{group_path} or {detail_path}."
    )


def _build_wide_tables(long_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    work = long_df.copy()
    work["Emis"] = pd.to_numeric(work["Emis"], errors="coerce")
    work["importance"] = pd.to_numeric(work["importance"], errors="coerce")
    work = work.dropna(subset=["Emis", "importance"])
    work["display_name"] = work["display_name"].astype(str).str.strip()
    work = work[work["display_name"] != ""].copy()
    if work.empty:
        raise ValueError("Sensitivity long table is empty after numeric cleanup.")

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
    for col in DISPLAY_ORDER:
        if col not in plot_wide.columns:
            plot_wide[col] = 0.0
    extra_cols = [
        c for c in plot_wide.columns
        if c not in {"Emis", *DISPLAY_ORDER}
    ]
    plot_wide = plot_wide[["Emis", *DISPLAY_ORDER, *extra_cols]].sort_values("Emis").reset_index(drop=True)

    pct_wide = plot_wide.copy()
    value_cols = [c for c in pct_wide.columns if c != "Emis"]
    vals = pct_wide[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    row_sum = vals.sum(axis=1).replace(0.0, np.nan)
    pct_wide[value_cols] = vals.div(row_sum, axis=0).fillna(0.0) * 100.0
    pct_smoothed = pct_wide.copy()
    pct_smoothed[value_cols] = _smooth_percentage_values(pct_wide[value_cols])

    return {
        "sensitivity_org": raw_wide,
        "sensitivity": plot_wide,
        "sensitivity_pct": pct_wide,
        "sensitivity_pct_smoothed": pct_smoothed,
        "sensitivity_long": work.sort_values(["Emis", "display_name"]).reset_index(drop=True),
    }


def _smooth_percentage_values(pct_values: pd.DataFrame) -> pd.DataFrame:
    values = pct_values.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if not bool(CONFIG.get("smooth_plot", True)):
        return values

    window = int(CONFIG.get("smooth_window", 1))
    if window <= 1 or len(values) <= 2:
        return values
    if window % 2 == 0:
        window += 1
    max_window = len(values) if len(values) % 2 == 1 else len(values) - 1
    window = min(window, max_window)
    if window <= 2:
        return values

    iterations = max(1, int(CONFIG.get("smooth_iterations", 1)))
    method = str(CONFIG.get("smooth_method", "rolling")).strip().lower()
    smoothed = values.to_numpy(dtype=float)

    if method == "savgol":
        polyorder = int(CONFIG.get("smooth_polyorder", 2))
        polyorder = max(1, min(polyorder, window - 1))
        for _ in range(iterations):
            smoothed = savgol_filter(
                smoothed,
                window_length=window,
                polyorder=polyorder,
                axis=0,
                mode="interp",
            )
        smoothed = pd.DataFrame(smoothed, columns=values.columns, index=values.index)
    else:
        smoothed = values.copy()
        for _ in range(iterations):
            smoothed = smoothed.rolling(window=window, center=True, min_periods=1).mean()

    smoothed = smoothed.clip(lower=0.0)
    row_sum = smoothed.sum(axis=1).replace(0.0, np.nan)
    return smoothed.div(row_sum, axis=0).fillna(0.0) * 100.0


def _interpolate_stack_values(
    x: np.ndarray,
    plot_norm: pd.DataFrame,
    stack_order: List[str],
) -> tuple[np.ndarray, List[np.ndarray]]:
    point_count = int(CONFIG.get("plot_interpolation_points", 0))
    if point_count <= len(x) or len(x) < 4:
        return x, [plot_norm[col].to_numpy(dtype=float) for col in stack_order]

    x_dense = np.linspace(float(np.min(x)), float(np.max(x)), point_count)
    dense = pd.DataFrame(index=np.arange(point_count))
    for col in stack_order:
        y = plot_norm[col].to_numpy(dtype=float)
        interpolator = PchipInterpolator(x, y, extrapolate=False)
        dense[col] = interpolator(x_dense)

    dense = dense.clip(lower=0.0).fillna(0.0)
    row_sum = dense.sum(axis=1).replace(0.0, np.nan)
    dense = dense.div(row_sum, axis=0).fillna(0.0) * 100.0
    return x_dense, [dense[col].to_numpy(dtype=float) for col in stack_order]


def _write_workbook(long_df: pd.DataFrame, run_meta: Dict[str, object]) -> Path:
    fig_dir = _fig_dir()
    out_path = fig_dir / "Figure2_v3.xlsx"
    tables = _build_wide_tables(long_df)

    meta_rows = [
        {"key": "source_group_csv", "value": str(_summary_dir() / "importance_by_variable.csv")},
        {"key": "source_detail_csv", "value": str(_summary_dir() / "importance_detail.csv")},
        {"key": "source_run_meta_csv", "value": str(_summary_dir() / "run_meta.csv")},
        {"key": "current_afolu_ghg_gt", "value": CONFIG["current_afolu_ghg_gt"]},
        {"key": "x_min_gt", "value": CONFIG["x_min_gt"]},
        {"key": "x_max_gt", "value": CONFIG["x_max_gt"]},
        {"key": "stack_order_target_emis_gt", "value": CONFIG["stack_order_target_emis_gt"]},
        {"key": "smooth_plot", "value": CONFIG["smooth_plot"]},
        {"key": "smooth_method", "value": CONFIG["smooth_method"]},
        {"key": "smooth_window", "value": CONFIG["smooth_window"]},
        {"key": "smooth_polyorder", "value": CONFIG["smooth_polyorder"]},
        {"key": "smooth_iterations", "value": CONFIG["smooth_iterations"]},
        {"key": "plot_interpolation_points", "value": CONFIG["plot_interpolation_points"]},
        {"key": "min_required_samples", "value": CONFIG["min_required_samples"]},
        {"key": "display_order", "value": " | ".join(DISPLAY_ORDER)},
    ]
    for key, value in (run_meta or {}).items():
        meta_rows.append({"key": f"run_meta.{key}", "value": value})
    meta_df = pd.DataFrame(meta_rows)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        meta_df.to_excel(writer, sheet_name="meta", index=False)
        tables["sensitivity"].to_excel(writer, sheet_name="sensitivity", index=False)
        tables["sensitivity_org"].to_excel(writer, sheet_name="sensitivity_org", index=False)
        tables["sensitivity_pct"].to_excel(writer, sheet_name="sensitivity_pct", index=False)
        tables["sensitivity_pct_smoothed"].to_excel(
            writer,
            sheet_name="sensitivity_pct_smoothed",
            index=False,
        )
        tables["sensitivity_long"].to_excel(writer, sheet_name="sensitivity_long", index=False)

    return out_path


def _plot_from_workbook(xlsx_path: Path) -> List[Path]:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    df = pd.read_excel(xlsx_path, sheet_name="sensitivity")
    if "Emis" not in df.columns:
        raise ValueError("Missing Emis column in Figure2_v3 sensitivity sheet.")

    df = df.copy()
    df["Emis"] = pd.to_numeric(df["Emis"], errors="coerce")
    df = df.dropna(subset=["Emis"]).sort_values("Emis")

    var_cols = [c for c in df.columns if c != "Emis"]
    if not var_cols:
        raise ValueError("No sensitivity variables found in Figure2_v3.xlsx.")

    vals = df[var_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if np.isclose(vals.to_numpy().sum(), 0.0):
        raise ValueError("All sensitivity values are zero; cannot plot stacked importance.")

    row_sum = vals.sum(axis=1).replace(0.0, np.nan)
    norm = vals.div(row_sum, axis=0).fillna(0.0) * 100.0
    plot_norm = _smooth_percentage_values(norm)

    order_row = _pick_emis_row(
        pd.concat([df[["Emis"]], plot_norm], axis=1),
        CONFIG["stack_order_target_emis_gt"],
    )
    order_desc = order_row[var_cols].sort_values(ascending=False).index.tolist()
    stack_order = order_desc

    x = df["Emis"].to_numpy(dtype=float)
    x_plot, y = _interpolate_stack_values(x, plot_norm, stack_order)
    colors = [_color_for_var(str(col)) for col in stack_order]

    fig, ax = plt.subplots(figsize=(7.2, 5.5))
    ax.stackplot(x_plot, y, colors=colors, labels=stack_order)
    ax.set_xlabel("GHG CO2eq in 2080 (Gt/yr)", fontsize=13.5, fontweight="bold", labelpad=12)
    ax.set_ylabel("Variable relative importance (%)", fontsize=13.5, fontweight="bold", labelpad=12)
    x_min = float(CONFIG["x_min_gt"])
    x_max = float(CONFIG["x_max_gt"])
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, 100)
    ax.axvline(
        float(CONFIG["current_afolu_ghg_gt"]),
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
    fig_dir = _fig_dir()
    outputs = [
        fig_dir / "Figure2_sensitivity_stack_v3.png",
        fig_dir / "Figure2_sensitivity_stack_v3.svg",
    ]
    fig.savefig(outputs[0], dpi=int(CONFIG["dpi"]))
    fig.savefig(outputs[1])
    plt.close(fig)
    return outputs


def main() -> None:
    run_meta = _load_run_meta()
    valid_samples = pd.to_numeric(pd.Series([run_meta.get("valid_samples", np.nan)]), errors="coerce").dropna()
    if not valid_samples.empty and int(valid_samples.iloc[0]) < int(CONFIG["min_required_samples"]):
        raise ValueError(
            "Sensitivity run does not have enough valid simulations for plotting. "
            f"valid_samples={int(valid_samples.iloc[0])}, "
            f"required={int(CONFIG['min_required_samples'])}."
        )
    long_df = _load_group_importance_long()
    workbook_path = _write_workbook(long_df, run_meta)
    figure_paths = _plot_from_workbook(workbook_path)

    print(f"[DONE] workbook: {workbook_path}")
    for path in figure_paths:
        print(f"[DONE] figure: {path}")


if __name__ == "__main__":
    main()
