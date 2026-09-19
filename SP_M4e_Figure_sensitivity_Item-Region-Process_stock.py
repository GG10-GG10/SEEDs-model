# -*- coding: utf-8 -*-
"""
Build structure-importance plotting tables from S5_5 merged raw outputs and plot them.

Inputs:
- output/MC_Region_Item_Process_Importance/merged_structure/mc_success_structure_emissions.csv
- output/MC_Region_Item_Process_Importance/merged_structure/mc_success_structure_totals.csv
- output/MC_Sensitivity/summary/importance_by_variable.csv
  fallback: output/MC_Sensitivity/summary/importance_detail.csv

Outputs:
- output/Plot/Fig9/Figure9_structure_importance_v3.xlsx
- output/Plot/Fig9/Figure9_structure_<grouping>_stack_v3.png/.svg
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config_paths import get_results_base


CONFIG = {
    "top_n": {
        "Region": 10,
        "Item": 12,
        "Process": 10,
    },
    "target_emissions_gt": None,
    "target_quantile_min": 0.05,
    "target_quantile_max": 0.933,
    "target_quantile_count": 15,
    "target_window_gt": 0.25,
    "target_nearest_n": 200,
    "clip_targets_to_range": True,
    "min_target_samples": 30,
    "output_root": "",
    "s5_0_summary_root": "",
    "strategy_include_unmapped_parameters": False,
    "strategy_min_effective_n_samples": 50.0,
    "strategy_smoothing_enabled": True,
    "strategy_smoothing_bandwidth_gt": 2.5,
    "dpi": 800,
}

GROUPINGS = ("Region", "Item", "Process")
STRATEGY_GROUPING = "Strategy"
TAB20_COLORS = list(plt.cm.tab20.colors) + list(plt.cm.tab20b.colors) + list(plt.cm.tab20c.colors)

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


def _results_root() -> Path:
    return Path(get_results_base())


def _source_root() -> Path:
    configured = str(CONFIG.get("output_root", "") or "").strip()
    if configured:
        return Path(configured)
    env_output_dir = str(os.environ.get("RIPMC_OUTPUT_DIR", "") or "").strip()
    if env_output_dir:
        return Path(env_output_dir)
    return _results_root() / "MC_Region_Item_Process_Importance"


def _fig_dir() -> Path:
    path = _results_root() / "Plot" / "Fig9"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _merged_dir() -> Path:
    return _source_root() / "merged_structure"


def _s5_0_summary_dir() -> Path:
    configured = str(CONFIG.get("s5_0_summary_root", "") or "").strip()
    if configured:
        path = Path(configured)
        if path.name.lower() == "summary":
            return path
        return path / "summary"
    return _results_root() / "MC_Sensitivity" / "summary"


def _load_raw_structure() -> pd.DataFrame:
    path = _merged_dir() / "mc_success_structure_emissions.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing structure emissions file: {path}")
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"scenario_id", "sample_id", "grouping", "group_key", "group_1", "emissions_share"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"Structure emissions file missing columns: {sorted(missing)}")
    df["scenario_id"] = df["scenario_id"].astype(str)
    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    return df


def _load_raw_totals() -> pd.DataFrame:
    path = _merged_dir() / "mc_success_structure_totals.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing structure totals file: {path}")
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"scenario_id", "sample_id", "total_emissions_gt"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"Structure totals file missing columns: {sorted(missing)}")
    df["scenario_id"] = df["scenario_id"].astype(str)
    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    return df


def _valid_totals(totals_df: pd.DataFrame) -> pd.DataFrame:
    out = totals_df.copy()
    out["total_emissions_gt"] = pd.to_numeric(out["total_emissions_gt"], errors="coerce")
    out = out.dropna(subset=["scenario_id", "sample_id", "total_emissions_gt"]).copy()
    out["scenario_id"] = out["scenario_id"].astype(str)
    out["sample_id"] = pd.to_numeric(out["sample_id"], errors="coerce").astype(int)
    return out.drop_duplicates(subset=["scenario_id", "sample_id"], keep="last").reset_index(drop=True)


def _target_values(totals_df: pd.DataFrame) -> List[float]:
    configured = CONFIG.get("target_emissions_gt", None)
    if configured:
        return [float(x) for x in configured]
    vals = pd.to_numeric(totals_df["total_emissions_gt"], errors="coerce").dropna()
    if vals.empty:
        return []
    q_min = CONFIG.get("target_quantile_min", 0.05)
    q_max = CONFIG.get("target_quantile_max", 0.95)
    q_min = 0.05 if q_min is None else float(q_min)
    q_max = 0.95 if q_max is None else float(q_max)
    q_count = int(CONFIG.get("target_quantile_count", 10) or 10)
    if q_count < 2:
        q_count = 2
    quantiles = np.linspace(q_min, q_max, q_count)
    return [float(vals.quantile(q)) for q in quantiles]


def _select_samples_near_target(
    totals_df: pd.DataFrame, target: float
) -> Tuple[pd.DataFrame, str]:
    work = totals_df.copy()
    work["distance_gt"] = (work["total_emissions_gt"] - float(target)).abs()
    window = float(CONFIG.get("target_window_gt", 0.25) or 0.25)
    nearest_n = int(CONFIG.get("target_nearest_n", 200) or 200)
    within = work[work["distance_gt"] <= window].copy()
    if len(within) >= max(10, nearest_n // 4):
        return within.sort_values(["distance_gt", "scenario_id"], kind="mergesort"), f"window_{window:g}gt"
    return work.sort_values(["distance_gt", "scenario_id"], kind="mergesort").head(nearest_n), f"nearest_{nearest_n}"


def _group_label(row: pd.Series) -> str:
    label = str(row.get("group_1", "") or "").strip()
    if label and label.lower() != "nan":
        return label
    label = str(row.get("group_key", "") or "").strip()
    return label


def _normalize_strategy_parameter(raw: object) -> str:
    text = str(raw or "").strip()
    canonical = STRATEGY_PARAMETER_NAME_MAP.get(text.lower())
    if canonical:
        return canonical
    if bool(CONFIG.get("strategy_include_unmapped_parameters", False)):
        return text
    return ""


def _build_importance_long(structure_df: pd.DataFrame, totals_df: pd.DataFrame) -> pd.DataFrame:
    totals = _valid_totals(totals_df)
    if totals.empty:
        raise ValueError("No valid totals rows available for importance computation.")

    targets = _target_values(totals)
    if not targets:
        raise ValueError("No target emission values available for importance computation.")
    if bool(CONFIG.get("clip_targets_to_range", True)):
        min_gt = float(totals["total_emissions_gt"].min())
        max_gt = float(totals["total_emissions_gt"].max())
        targets = [t for t in targets if min_gt <= t <= max_gt]
        if not targets:
            raise ValueError("No target emissions remain after clipping to totals range.")

    structure = structure_df.copy()
    structure["scenario_id"] = structure["scenario_id"].astype(str)
    structure["sample_id"] = pd.to_numeric(structure["sample_id"], errors="coerce")
    structure["emissions_share"] = pd.to_numeric(structure["emissions_share"], errors="coerce")
    structure = structure.dropna(subset=["scenario_id", "sample_id", "grouping", "group_key", "emissions_share"]).copy()
    structure["sample_id"] = structure["sample_id"].astype(int)
    if structure.empty:
        raise ValueError("No usable structure emissions rows available.")

    rows: List[Dict[str, object]] = []
    min_samples = int(CONFIG.get("min_target_samples", 0) or 0)
    for target in targets:
        selected, method = _select_samples_near_target(totals, target)
        keys = selected[["scenario_id", "sample_id"]].drop_duplicates()
        n_samples = int(keys["sample_id"].nunique())
        if n_samples < max(1, min_samples):
            print(
                f"[WARN] skip target {target:g} Gt: only {n_samples} samples "
                f"(selection={method}, min_required={min_samples})"
            )
            continue
        sub = structure.merge(keys, on=["scenario_id", "sample_id"], how="inner")
        if sub.empty:
            continue
        grouped = (
            sub.groupby(["grouping", "group_key", "group_1"], as_index=False, dropna=False)
            .agg(importance_sum=("emissions_share", "sum"))
        )
        for rec in grouped.to_dict("records"):
            grouping = str(rec.get("grouping", "") or "")
            if grouping not in GROUPINGS:
                continue
            label = _group_label(pd.Series(rec))
            if not label:
                continue
            importance = float(rec.get("importance_sum", 0.0) or 0.0) / float(n_samples)
            rows.append(
                {
                    "Emis": float(target),
                    "Group": label,
                    "importance": importance,
                    "grouping": grouping,
                }
            )

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("Importance computation returned no rows.")
    return out


def _interpolate_strategy_targets(
    long_df: pd.DataFrame,
    target_emissions_gt: List[float],
) -> pd.DataFrame:
    if not target_emissions_gt:
        return long_df

    target_arr = np.asarray([float(x) for x in target_emissions_gt], dtype=float)
    target_arr = np.asarray(sorted(set(target_arr)), dtype=float)
    work = long_df.copy()
    work["Emis"] = pd.to_numeric(work["Emis"], errors="coerce")
    work["importance"] = pd.to_numeric(work["importance"], errors="coerce")
    work = work.dropna(subset=["Emis", "Group", "importance"]).copy()
    if work.empty:
        return work

    source_min = float(work["Emis"].min())
    source_max = float(work["Emis"].max())
    if float(target_arr.min()) < source_min or float(target_arr.max()) > source_max:
        print(
            "[WARN] Strategy target emissions extend beyond S5_0 importance targets "
            f"({source_min:g}-{source_max:g} Gt); edge values are used outside the source range."
        )

    rows: List[Dict[str, object]] = []
    for group, sub in work.groupby("Group", sort=False):
        series = (
            sub.groupby("Emis", as_index=True)["importance"]
            .sum()
            .sort_index()
        )
        x = series.index.to_numpy(dtype=float)
        y = series.to_numpy(dtype=float)
        if len(x) == 0:
            continue
        if len(x) == 1:
            values = np.full(len(target_arr), float(y[0]))
        else:
            values = np.interp(target_arr, x, y, left=float(y[0]), right=float(y[-1]))
        values = _smooth_strategy_values(target_arr, values)
        for target, importance in zip(target_arr, values):
            rows.append(
                {
                    "Emis": float(target),
                    "Group": str(group),
                    "grouping": STRATEGY_GROUPING,
                    "importance": float(importance),
                }
            )
    return _normalize_strategy_rows(pd.DataFrame(rows))


def _smooth_strategy_values(x: np.ndarray, values: np.ndarray) -> np.ndarray:
    if not bool(CONFIG.get("strategy_smoothing_enabled", False)):
        return values
    if len(values) < 3:
        return values
    bandwidth = float(CONFIG.get("strategy_smoothing_bandwidth_gt", 0.0) or 0.0)
    if not np.isfinite(bandwidth) or bandwidth <= 0:
        return values
    x = np.asarray(x, dtype=float)
    y = np.asarray(values, dtype=float)
    smoothed = np.empty_like(y)
    for idx, target in enumerate(x):
        weights = np.exp(-0.5 * ((x - target) / bandwidth) ** 2)
        weights = np.where(np.isfinite(weights), weights, 0.0)
        denom = float(weights.sum())
        smoothed[idx] = float(np.dot(weights, y) / denom) if denom > 0 else y[idx]
    return np.clip(smoothed, 0.0, None)


def _normalize_strategy_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["importance"] = pd.to_numeric(out["importance"], errors="coerce").fillna(0.0)
    denom = out.groupby("Emis")["importance"].transform("sum").replace(0.0, np.nan)
    out["importance"] = out["importance"].div(denom).fillna(0.0)
    return out


def _filter_strategy_by_ess(df: pd.DataFrame) -> pd.DataFrame:
    min_ess_raw = CONFIG.get("strategy_min_effective_n_samples", None)
    if min_ess_raw is None or "effective_n_samples" not in df.columns:
        return df
    min_ess = float(min_ess_raw)
    if not np.isfinite(min_ess) or min_ess <= 0:
        return df
    out = df.copy()
    out["effective_n_samples"] = pd.to_numeric(out["effective_n_samples"], errors="coerce")
    before_targets = int(pd.to_numeric(out["target_emission_gt"], errors="coerce").nunique())
    out = out[out["effective_n_samples"] >= min_ess].copy()
    after_targets = int(pd.to_numeric(out["target_emission_gt"], errors="coerce").nunique())
    print(
        f"[SP_M4e] Strategy ESS filter >= {min_ess:g}: "
        f"{after_targets}/{before_targets} source targets retained."
    )
    return out


def _load_strategy_importance_long(target_emissions_gt: List[float] | None = None) -> pd.DataFrame:
    summary_dir = _s5_0_summary_dir()
    group_path = summary_dir / "importance_by_variable.csv"
    detail_path = summary_dir / "importance_detail.csv"

    if group_path.exists():
        group_df = pd.read_csv(group_path)
        group_df.columns = [str(c).strip() for c in group_df.columns]
        required = {"target_emission_gt", "parameter", "importance"}
        if required.issubset(group_df.columns):
            cols = ["target_emission_gt", "parameter", "importance"]
            if "effective_n_samples" in group_df.columns:
                cols.append("effective_n_samples")
            out = group_df[cols].copy()
            out = _filter_strategy_by_ess(out)
            out["importance"] = pd.to_numeric(out["importance"], errors="coerce")
            out["Group"] = out["parameter"].map(_normalize_strategy_parameter)
            out = out.dropna(subset=["target_emission_gt", "importance"]).copy()
            out = out[out["Group"].astype(str).str.strip() != ""].copy()
            if not out.empty:
                out["grouping"] = STRATEGY_GROUPING
                agg_spec = {"importance": "sum"}
                if "effective_n_samples" in out.columns:
                    agg_spec["effective_n_samples"] = "min"
                long_df = (
                    out.groupby(["target_emission_gt", "Group", "grouping"], as_index=False)
                    .agg(agg_spec)
                    .rename(columns={"target_emission_gt": "Emis"})
                )
                return _interpolate_strategy_targets(long_df, target_emissions_gt or [])

    if detail_path.exists():
        detail_df = pd.read_csv(detail_path)
        detail_df.columns = [str(c).strip() for c in detail_df.columns]
        required = {"target_emission_gt", "importance"}
        if required.issubset(detail_df.columns):
            source_col = "group" if "group" in detail_df.columns else "parameter"
            if source_col in detail_df.columns:
                cols = ["target_emission_gt", source_col, "importance"]
                if "effective_n_samples" in detail_df.columns:
                    cols.append("effective_n_samples")
                out = detail_df[cols].copy()
                out = _filter_strategy_by_ess(out)
                out["importance"] = pd.to_numeric(out["importance"], errors="coerce")
                out["Group"] = out[source_col].map(_normalize_strategy_parameter)
                out = out.dropna(subset=["target_emission_gt", "importance"]).copy()
                out = out[out["Group"].astype(str).str.strip() != ""].copy()
                if not out.empty:
                    out["grouping"] = STRATEGY_GROUPING
                    agg_spec = {"importance": "sum"}
                    if "effective_n_samples" in out.columns:
                        agg_spec["effective_n_samples"] = "min"
                    long_df = (
                        out.groupby(["target_emission_gt", "Group", "grouping"], as_index=False)
                        .agg(agg_spec)
                        .rename(columns={"target_emission_gt": "Emis"})
                    )
                    return _interpolate_strategy_targets(long_df, target_emissions_gt or [])

    raise FileNotFoundError(
        "No usable S5_0 strategy importance result found. Expected valid values in "
        f"{group_path} or {detail_path}."
    )


def _build_plot_table(long_df: pd.DataFrame, grouping: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    top_n = int((CONFIG.get("top_n", {}) or {}).get(grouping, 10))
    rank_df = (
        long_df.groupby("Group", as_index=False)["importance"]
        .mean()
        .sort_values("importance", ascending=False, kind="mergesort")
    )
    keep_groups = rank_df["Group"].head(top_n).tolist()

    work = long_df.copy()
    work["Group_plot"] = np.where(work["Group"].isin(keep_groups), work["Group"], "Other")
    work = (
        work.groupby(["Emis", "Group_plot"], as_index=False)["importance"]
        .sum()
        .sort_values(["Emis", "Group_plot"], ascending=[True, True], kind="mergesort")
    )

    wide = (
        work.pivot_table(
            index="Emis",
            columns="Group_plot",
            values="importance",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
        .sort_values("Emis")
    )

    ordered_cols = [c for c in keep_groups if c in wide.columns]
    if "Other" in wide.columns:
        ordered_cols.append("Other")
    wide = wide[["Emis", *ordered_cols]].reset_index(drop=True)

    pct = wide.copy()
    val_cols = [c for c in pct.columns if c != "Emis"]
    vals = pct[val_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    row_sum = vals.sum(axis=1).replace(0.0, np.nan)
    pct[val_cols] = vals.div(row_sum, axis=0).fillna(0.0) * 100.0

    return wide, pct


def _build_strategy_plot_table(long_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    work = long_df.copy()
    work["Emis"] = pd.to_numeric(work["Emis"], errors="coerce")
    work["importance"] = pd.to_numeric(work["importance"], errors="coerce")
    work["Group"] = work["Group"].astype(str).str.strip()
    work = work.dropna(subset=["Emis", "importance"])
    work = work[work["Group"] != ""].copy()
    if work.empty:
        raise ValueError("Strategy importance table is empty after cleanup.")

    wide = (
        work.pivot_table(
            index="Emis",
            columns="Group",
            values="importance",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
        .sort_values("Emis")
    )

    ordered_cols = [col for col in STRATEGY_DISPLAY_ORDER if col in wide.columns]
    extra_cols = [
        col for col in wide.columns
        if col != "Emis" and col not in set(STRATEGY_DISPLAY_ORDER)
    ]
    wide = wide[["Emis", *ordered_cols, *extra_cols]].reset_index(drop=True)

    pct = wide.copy()
    val_cols = [c for c in pct.columns if c != "Emis"]
    vals = pct[val_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    row_sum = vals.sum(axis=1).replace(0.0, np.nan)
    pct[val_cols] = vals.div(row_sum, axis=0).fillna(0.0) * 100.0
    return wide, pct


def _color_map(labels: List[str]) -> Dict[str, Tuple[float, float, float]]:
    cmap: Dict[str, Tuple[float, float, float]] = {}
    for idx, label in enumerate(labels):
        if label == "Other":
            cmap[label] = (0.7, 0.7, 0.7)
        else:
            cmap[label] = TAB20_COLORS[idx % len(TAB20_COLORS)]
    return cmap


def _pick_stack_order(pct_df: pd.DataFrame) -> List[str]:
    val_cols = [c for c in pct_df.columns if c != "Emis"]
    if not val_cols:
        return []
    order_row = pct_df.iloc[len(pct_df) // 2]
    return order_row[val_cols].sort_values(ascending=False).index.tolist()


def _write_workbook(group_tables: Dict[str, Dict[str, pd.DataFrame]]) -> Path:
    out_path = _fig_dir() / "Figure9_structure_importance_v3.xlsx"
    meta_rows = [
        {"key": "source_root", "value": str(_source_root())},
        {"key": "merged_dir", "value": str(_merged_dir())},
        {"key": "structure_emissions", "value": "mc_success_structure_emissions.csv"},
        {"key": "structure_totals", "value": "mc_success_structure_totals.csv"},
        {"key": "s5_0_summary_dir", "value": str(_s5_0_summary_dir())},
        {"key": "s5_0_strategy_importance", "value": "importance_by_variable.csv"},
        {"key": "s5_0_strategy_fallback", "value": "importance_detail.csv"},
        {"key": "target_quantile_min", "value": float(CONFIG.get("target_quantile_min", 0.05))},
        {"key": "target_quantile_max", "value": float(CONFIG.get("target_quantile_max", 0.95))},
        {"key": "target_quantile_count", "value": int(CONFIG.get("target_quantile_count", 10))},
        {"key": "target_window_gt", "value": float(CONFIG.get("target_window_gt", 0.25))},
        {"key": "target_nearest_n", "value": int(CONFIG.get("target_nearest_n", 200))},
        {"key": "clip_targets_to_range", "value": bool(CONFIG.get("clip_targets_to_range", True))},
        {"key": "min_target_samples", "value": int(CONFIG.get("min_target_samples", 0))},
        {"key": "groupings", "value": " | ".join((*GROUPINGS, STRATEGY_GROUPING))},
        {"key": "strategy_display_order", "value": " | ".join(STRATEGY_DISPLAY_ORDER)},
        {
            "key": "strategy_min_effective_n_samples",
            "value": CONFIG.get("strategy_min_effective_n_samples", None),
        },
        {
            "key": "strategy_smoothing_enabled",
            "value": bool(CONFIG.get("strategy_smoothing_enabled", False)),
        },
        {
            "key": "strategy_smoothing_bandwidth_gt",
            "value": float(CONFIG.get("strategy_smoothing_bandwidth_gt", 0.0) or 0.0),
        },
        {
            "key": "strategy_include_unmapped_parameters",
            "value": bool(CONFIG.get("strategy_include_unmapped_parameters", False)),
        },
    ]
    for grouping in GROUPINGS:
        meta_rows.append(
            {
                "key": f"{grouping}_top_n",
                "value": int((CONFIG.get("top_n", {}) or {}).get(grouping, 10)),
            }
        )
    meta_df = pd.DataFrame(meta_rows)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        meta_df.to_excel(writer, sheet_name="meta", index=False)
        for grouping, tables in group_tables.items():
            tables["raw"].to_excel(writer, sheet_name=f"{grouping}_org"[:31], index=False)
            tables["plot"].to_excel(writer, sheet_name=grouping[:31], index=False)
            tables["plot_pct"].to_excel(writer, sheet_name=f"{grouping}_pct"[:31], index=False)
    return out_path


def _plot_grouping(grouping: str, wide_df: pd.DataFrame) -> List[Path]:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    work = wide_df.copy()
    work["Emis"] = pd.to_numeric(work["Emis"], errors="coerce")
    work = work.dropna(subset=["Emis"]).sort_values("Emis")
    val_cols = [c for c in work.columns if c != "Emis"]
    if not val_cols:
        raise ValueError(f"No plot columns available for grouping {grouping}.")

    vals = work[val_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    row_sum = vals.sum(axis=1).replace(0.0, np.nan)
    pct = vals.div(row_sum, axis=0).fillna(0.0) * 100.0
    plot_df = pd.concat([work[["Emis"]], pct], axis=1)

    stack_order = _pick_stack_order(plot_df)
    colors = _color_map(stack_order)

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    ax.stackplot(
        plot_df["Emis"].to_numpy(dtype=float),
        [plot_df[col].to_numpy(dtype=float) for col in stack_order],
        colors=[colors[col] for col in stack_order],
        labels=stack_order,
    )
    ax.set_title(f"{grouping} relative importance", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("GHG CO2eq in 2080 (Gt/yr)", fontsize=13, fontweight="bold", labelpad=10)
    ax.set_ylabel("Relative importance (%)", fontsize=13, fontweight="bold", labelpad=10)
    ax.set_ylim(0, 100)
    ax.tick_params(axis="both", which="both", labelsize=12, width=1.6, length=7)
    for spine in ax.spines.values():
        spine.set_linewidth(1.6)

    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        frameon=False,
        fontsize=10,
        title=grouping,
        title_fontsize=11,
    )

    fig.tight_layout()
    slug = grouping.lower().replace(" ", "_")
    fig_dir = _fig_dir()
    outputs = [
        fig_dir / f"Figure9_structure_{slug}_stack_v3.png",
        fig_dir / f"Figure9_structure_{slug}_stack_v3.svg",
    ]
    fig.savefig(outputs[0], dpi=int(CONFIG["dpi"]), bbox_inches="tight")
    fig.savefig(outputs[1], bbox_inches="tight")
    plt.close(fig)
    return outputs


def main() -> None:
    structure_df = _load_raw_structure()
    totals_df = _load_raw_totals()
    importance_long = _build_importance_long(structure_df, totals_df)

    group_tables: Dict[str, Dict[str, pd.DataFrame]] = {}
    for grouping in GROUPINGS:
        raw_df = importance_long[importance_long["grouping"] == grouping].copy()
        raw_df = raw_df.dropna(subset=["Emis", "importance"]).copy()
        raw_df = raw_df[(raw_df["Group"] != "") & (raw_df["Group"].str.lower() != "nan")].copy()
        raw_df = raw_df[raw_df["importance"] > 0].copy()
        if raw_df.empty:
            raise ValueError(f"Grouping {grouping} has no positive structure-importance rows.")
        wide_df, pct_df = _build_plot_table(raw_df, grouping)
        group_tables[grouping] = {
            "raw": raw_df,
            "plot": wide_df,
            "plot_pct": pct_df,
        }

    target_values = sorted(
        float(x)
        for x in pd.to_numeric(importance_long["Emis"], errors="coerce").dropna().unique()
    )
    strategy_raw_df = _load_strategy_importance_long(target_values)
    strategy_raw_df = strategy_raw_df.dropna(subset=["Emis", "importance"]).copy()
    strategy_raw_df = strategy_raw_df[(strategy_raw_df["Group"] != "") & (strategy_raw_df["Group"].str.lower() != "nan")].copy()
    strategy_raw_df = strategy_raw_df[strategy_raw_df["importance"] > 0].copy()
    if strategy_raw_df.empty:
        raise ValueError("Strategy has no positive S5_0 importance rows.")
    strategy_wide_df, strategy_pct_df = _build_strategy_plot_table(strategy_raw_df)
    group_tables[STRATEGY_GROUPING] = {
        "raw": strategy_raw_df,
        "plot": strategy_wide_df,
        "plot_pct": strategy_pct_df,
    }

    workbook_path = _write_workbook(group_tables)
    print(f"[DONE] workbook: {workbook_path}")

    for grouping in GROUPINGS:
        outputs = _plot_grouping(grouping, group_tables[grouping]["plot"])
        for path in outputs:
            print(f"[DONE] figure: {path}")


if __name__ == "__main__":
    main()
