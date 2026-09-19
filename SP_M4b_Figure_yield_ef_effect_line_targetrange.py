# -*- coding: utf-8 -*-
"""
Build Figure 5 v3 panel plots.

Panels B/C/D are rebuilt from merged MC full-variable simulation outputs:
  - output/MC_Full_Variables/merged/mc_success_fast_summary.csv
  - output/MC_Full_Variables/merged/mc_success_weighted_elements.csv

Outputs:
  - output/Plot/Fig5/Figure5_yield_effect_line_v3.png/.svg
  - output/Plot/Fig5/Figure5_emission_factor_effect_line_v3.png/.svg
  - output/Plot/Fig5/Figure5_ruminate_intake_effect_line_v3.png/.svg
  - output/Plot/Fig5/panel_samples_v3.csv
  - output/Plot/Fig5/histogram_v3.csv
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from config_paths import get_results_base


RESULTS_BASE = Path(get_results_base())
FIG5_DIR = RESULTS_BASE / "Plot" / "Fig5"
TARGETS_PATH = FIG5_DIR / "targets.csv"
MC_MERGED_DIR = RESULTS_BASE / "MC_Full_Variables" / "merged"
FAST_SUMMARY_PATH = MC_MERGED_DIR / "mc_success_fast_summary.csv"
DRAW_PATH = MC_MERGED_DIR / "mc_draws_long.csv"
WEIGHTED_ELEMENTS_PATH = MC_MERGED_DIR / "mc_success_weighted_elements.csv"
STATUS_PATH = MC_MERGED_DIR / "mc_sample_status.csv"
REALIZED_RUMINANT_PATH = MC_MERGED_DIR / "mc_success_realized_ruminant_share.csv"

YEAR = 2080
BINS = 120
SMOOTH_SIGMA_BINS = 2.2
DEFAULT_X_MIN = -3.0
DEFAULT_X_MAX = 18.0
RUMINANT_CURRENT_SHARE = 0.08
INVALID_TOTAL_CO2EQ_GT_VALUES = (1.264874,)

FIG_WIDTH = 17.2
FIG_HEIGHT = 10.2
AXIS_LABEL_FONTSIZE = 15
TICK_LABEL_FONTSIZE = 14
PANEL_TITLE_FONTSIZE = 17
INLINE_LABEL_FONTSIZE = 11.5
TARGET_LABEL_FONTSIZE = 13
MEAN_LINEWIDTH = 1.25
MEAN_LINE_ALPHA = 0.48

TARGET_ORDER = ["1.5D", "2D", "Current", "RCP4.5"]
TARGET_COLORS = {
    "1.5D": "#2ca25f",
    "2D": "#2b8cbe",
    "Current": "#4d4d4d",
    "RCP4.5": "#f1a340",
}

PANEL_SPECS = {
    "yield": {
        "title": "B. Effects of yield rate",
        "file_stem": "Figure5_yield_effect_line_v3",
        "order": ["yield_ge_60", "yield_20_60", "yield_pm_20", "yield_lt_m20"],
        "labels": {
            "yield_ge_60": "Yield >= +60%",
            "yield_20_60": "Yield +20% to +60%",
            "yield_pm_20": "Yield -20% to +20%",
            "yield_lt_m20": "Yield < -20%",
        },
        "colors": {
            "yield_ge_60": "#f98d8f",
            "yield_20_60": "#f26b6f",
            "yield_pm_20": "#e84a4d",
            "yield_lt_m20": "#be2f34",
        },
        "label_offsets": {
            "yield_ge_60": (-0.6, 0.05),
            "yield_20_60": (-0.2, 0.05),
            "yield_pm_20": (-0.5, 0.05),
            "yield_lt_m20": (0.4, 0.05),
        },
    },
    "emission_factor": {
        "title": "C. Effects of emission intensity",
        "file_stem": "Figure5_emission_factor_effect_line_v3",
        "order": ["ef_down_60_plus", "ef_down_20_60", "ef_pm_20", "ef_up_20_plus"],
        "labels": {
            "ef_down_60_plus": "EF down >= 60%",
            "ef_down_20_60": "EF down 20% to 60%",
            "ef_pm_20": "EF change -20% to +20%",
            "ef_up_20_plus": "EF up > 20%",
        },
        "colors": {
            "ef_down_60_plus": "#b7ddb0",
            "ef_down_20_60": "#86bd7a",
            "ef_pm_20": "#5d8758",
            "ef_up_20_plus": "#2f4d2c",
        },
        "label_offsets": {
            "ef_down_60_plus": (-0.6, 0.05),
            "ef_down_20_60": (0.4, 0.05),
            "ef_pm_20": (-0.2, 0.05),
            "ef_up_20_plus": (0.4, 0.05),
        },
    },
    "ruminate_share": {
        "title": "D. Effects of ruminant intake",
        "file_stem": "Figure5_ruminate_intake_effect_line_v3",
        "order": ["rumi_lt_2", "rumi_2_6", "rumi_6_10", "rumi_gt_10"],
        "labels": {
            "rumi_lt_2": "Ruminant share < 2%",
            "rumi_2_6": "Ruminant share 2% to 6%",
            "rumi_6_10": "Ruminant share 6% to 10%",
            "rumi_gt_10": "Ruminant share > 10%",
        },
        "colors": {
            "rumi_lt_2": "#b3a6dd",
            "rumi_2_6": "#8c7aca",
            "rumi_6_10": "#675694",
            "rumi_gt_10": "#47366d",
        },
        "label_offsets": {
            "rumi_lt_2": (-0.6, 0.05),
            "rumi_2_6": (-0.2, 0.05),
            "rumi_6_10": (0.0, 0.05),
            "rumi_gt_10": (0.4, 0.05),
        },
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


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _sentinel_mask(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    bad_vals = [round(float(x), 6) for x in INVALID_TOTAL_CO2EQ_GT_VALUES]
    return vals.round(6).isin(bad_vals)


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

    ordered: List[Tuple[str, float]] = []
    for label in TARGET_ORDER:
        if label in value_map:
            ordered.append((label, value_map[label]))
    if ordered:
        return ordered
    return default_targets


def _load_valid_success_keys() -> pd.DataFrame:
    if not STATUS_PATH.exists():
        return pd.DataFrame(columns=["scenario_id", "sample_id"])
    status = pd.read_csv(STATUS_PATH)
    if "scenario_id" not in status.columns or "sample_id" not in status.columns:
        return pd.DataFrame(columns=["scenario_id", "sample_id"])

    run_status = status.get("run_status", pd.Series("", index=status.index)).astype(str).str.strip().str.lower()
    run_ok = run_status.isin({"ok", "resumed"})
    model_code = pd.to_numeric(status.get("model_status_code", pd.Series(pd.NA, index=status.index)), errors="coerce")
    model_text = status.get("model_status_text", pd.Series("", index=status.index)).astype(str).str.strip().str.upper()
    has_model_status = bool(model_code.notna().any() or model_text.ne("").any())
    model_ok = model_code.eq(2) | model_text.eq("OPTIMAL")
    mask = run_ok & (model_ok if has_model_status else True)

    keys = status.loc[mask, ["scenario_id", "sample_id"]].copy()
    keys["scenario_id"] = keys["scenario_id"].astype(str)
    keys["sample_id"] = pd.to_numeric(keys["sample_id"], errors="coerce").astype("Int64")
    keys = keys.dropna(subset=["sample_id"]).copy()
    keys["sample_id"] = keys["sample_id"].astype(int)
    keys = keys.drop_duplicates().reset_index(drop=True)
    print(f"[INFO] valid OPTIMAL MC samples: {len(keys)}")
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
    out["sample_id"] = out["sample_id"].astype(int)
    valid_keys = _load_valid_success_keys()
    if not valid_keys.empty:
        before = len(out)
        out["scenario_id"] = out["scenario_id"].astype(str)
        out = out.merge(valid_keys, on=["scenario_id", "sample_id"], how="inner")
        print(f"[INFO] filtered MC emissions to OPTIMAL success rows: {len(out)}/{before}")
    return out


def _load_weighted_elements() -> pd.DataFrame:
    if not WEIGHTED_ELEMENTS_PATH.exists():
        raise FileNotFoundError(f"Missing merged weighted elements: {WEIGHTED_ELEMENTS_PATH}")
    df = pd.read_csv(WEIGHTED_ELEMENTS_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    if "scenario_id" not in df.columns or "sample_id" not in df.columns:
        raise ValueError("mc_success_weighted_elements.csv missing scenario_id/sample_id.")
    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    return df.dropna(subset=["scenario_id", "sample_id"]).copy()


def _load_draws_long() -> pd.DataFrame:
    if not DRAW_PATH.exists():
        raise FileNotFoundError(f"Missing merged draws: {DRAW_PATH}")
    df = pd.read_csv(
        DRAW_PATH,
        usecols=[
            "scenario_id",
            "sample_id",
            "spec_row_id",
            "kind",
            "item_selector",
            "value_draw",
            "mc_unit",
        ],
    )
    df.columns = [str(c).strip() for c in df.columns]
    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    df["spec_row_id"] = pd.to_numeric(df["spec_row_id"], errors="coerce")
    df["value_draw"] = pd.to_numeric(df["value_draw"], errors="coerce")
    return df.dropna(subset=["scenario_id", "sample_id", "spec_row_id"]).copy()


def _load_draw_weights() -> pd.DataFrame:
    if not WEIGHTED_ELEMENTS_PATH.exists():
        return pd.DataFrame(columns=["spec_row_id", "kind", "item_selector", "weight_kcal_total"])
    df = pd.read_csv(
        WEIGHTED_ELEMENTS_PATH,
        usecols=["spec_row_id", "kind", "item_selector", "weight_kcal_total"],
    )
    df.columns = [str(c).strip() for c in df.columns]
    df["spec_row_id"] = pd.to_numeric(df["spec_row_id"], errors="coerce")
    df["weight_kcal_total"] = pd.to_numeric(df["weight_kcal_total"], errors="coerce")
    return df.drop_duplicates(subset=["spec_row_id", "kind", "item_selector"]).copy()


def _load_realized_ruminant_share() -> pd.DataFrame:
    if not REALIZED_RUMINANT_PATH.exists():
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])
    df = pd.read_csv(REALIZED_RUMINANT_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"scenario_id", "sample_id", "realized_ruminant_share_kcal"}
    if not required.issubset(df.columns):
        print(f"[WARN] realized ruminant share file missing required columns: {REALIZED_RUMINANT_PATH}")
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df = df[df["year"] == YEAR].copy()
    df["sample_id"] = pd.to_numeric(df["sample_id"], errors="coerce")
    df["metric_value"] = pd.to_numeric(df["realized_ruminant_share_kcal"], errors="coerce")
    out = (
        df.dropna(subset=["scenario_id", "sample_id", "metric_value"])
        .groupby(["scenario_id", "sample_id"], as_index=False)["metric_value"]
        .mean()
    )
    out["scenario_id"] = out["scenario_id"].astype(str)
    out["sample_id"] = out["sample_id"].astype(int)
    out["metric_value"] = out["metric_value"].clip(lower=0.0, upper=1.0)
    print(f"[INFO] realized ruminant share rows: {len(out)}")
    return out


def _resolve_row_weight(df: pd.DataFrame) -> pd.Series:
    weight = pd.Series(1.0, index=df.index, dtype=float)
    if "weight_kcal_total" in df.columns:
        kcal = pd.to_numeric(df["weight_kcal_total"], errors="coerce")
        weight = np.where(kcal.notna() & (kcal > 0), kcal, weight)
        weight = pd.Series(weight, index=df.index, dtype=float)
    if "selected_pairs" in df.columns:
        pairs = pd.to_numeric(df["selected_pairs"], errors="coerce")
        mask = (weight <= 0) | ~np.isfinite(weight)
        fill_mask = mask & pairs.notna() & (pairs > 0)
        weight.loc[fill_mask] = pairs.loc[fill_mask].astype(float)
    weight = weight.where(np.isfinite(weight) & (weight > 0), 1.0)
    return weight


def _aggregate_weighted_metric(df: pd.DataFrame, metric: pd.Series) -> pd.DataFrame:
    work = df[["scenario_id", "sample_id"]].copy()
    work["metric_value"] = pd.to_numeric(metric, errors="coerce")
    work["row_weight"] = _resolve_row_weight(df)
    work = work.dropna(subset=["metric_value"])
    if work.empty:
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])

    rows: List[Dict[str, float]] = []
    for (scenario_id, sample_id), sub in work.groupby(["scenario_id", "sample_id"], sort=False):
        vals = sub["metric_value"].to_numpy(dtype=float)
        weights = sub["row_weight"].to_numpy(dtype=float)
        if vals.size == 0:
            continue
        if not np.isfinite(weights).any() or float(np.nansum(weights)) <= 0:
            agg = float(np.nanmean(vals))
        else:
            weights = np.where(np.isfinite(weights) & (weights > 0), weights, 0.0)
            if float(weights.sum()) <= 0:
                agg = float(np.nanmean(vals))
            else:
                agg = float(np.average(vals, weights=weights))
        rows.append(
            {
                "scenario_id": str(scenario_id),
                "sample_id": int(sample_id),
                "metric_value": agg,
            }
        )
    return pd.DataFrame(rows)


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
        ratio.loc[ratio.isna() & rate_mask & sample.notna()] = 1.0 + sample.loc[
            ratio.isna() & rate_mask & sample.notna()
        ]
        mult_mask = mc_unit == "multiplier"
        ratio.loc[ratio.isna() & mult_mask & sample.notna()] = sample.loc[
            ratio.isna() & mult_mask & sample.notna()
        ]

    return ratio


def _derive_ruminant_share_metric(df: pd.DataFrame) -> Tuple[pd.Series, str]:
    sample = _numeric_series(df, "weighted_value_sample")
    base = _numeric_series(df, "weighted_value_y2020")
    ratio = _numeric_series(df, "weighted_ratio")

    plausible_share = sample.notna() & np.isfinite(sample) & (sample >= 0.0) & (sample <= 1.0)
    base_positive = base.notna() & np.isfinite(base) & (base > 0.0)
    share_like = plausible_share.mean() >= 0.8 and (
        base_positive.any() or float(sample.dropna().quantile(0.95)) <= 0.25
    )
    if share_like:
        return sample.clip(lower=0.0, upper=1.0), "weighted_value_sample"

    if ratio.notna().any():
        share = float(RUMINANT_CURRENT_SHARE) * ratio
        return share.clip(lower=0.0, upper=1.0), "current_share * weighted_ratio"

    share = float(RUMINANT_CURRENT_SHARE) * (1.0 + sample)
    return share.clip(lower=0.0, upper=1.0), "current_share * (1 + weighted_value_sample)"


def _filter_panel_rows(weighted_df: pd.DataFrame, panel: str) -> pd.DataFrame:
    kind = weighted_df.get("kind", pd.Series("", index=weighted_df.index)).astype(str).str.strip().str.lower()
    elem = weighted_df.get("element_name", pd.Series("", index=weighted_df.index)).astype(str).str.strip().str.lower()

    if panel == "yield":
        mask = kind == "yield_rate"
        if not bool(mask.any()):
            mask = elem.str.contains("yield", regex=False) & ~elem.str.contains("feed", regex=False)
    elif panel == "emission_factor":
        mask = kind == "emission_factor"
        if not bool(mask.any()):
            mask = elem.str.contains("emission", regex=False) | elem.str.contains("ef", regex=False)
    elif panel == "ruminate_share":
        mask = kind.isin(["ruminant_reduction", "ruminant_intake_ratio", "ruminant_intake_decreasing_ratio"])
        if not bool(mask.any()):
            mask = elem.str.contains("ruminant", regex=False) | elem.str.contains("ruminate", regex=False)
    else:
        mask = pd.Series(False, index=weighted_df.index)
    return weighted_df.loc[mask].copy()


def _aggregate_draw_metric(
    draws_df: pd.DataFrame,
    weight_df: pd.DataFrame,
    *,
    kind: str,
    metric_kind: str,
) -> pd.DataFrame:
    sub = draws_df[draws_df["kind"] == kind].copy()
    if sub.empty:
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])

    sub = sub.merge(weight_df, on=["spec_row_id", "kind", "item_selector"], how="left")
    sub["weight_kcal_total"] = pd.to_numeric(sub["weight_kcal_total"], errors="coerce").fillna(1.0)
    sub["value_draw"] = pd.to_numeric(sub["value_draw"], errors="coerce")
    sub = sub.dropna(subset=["value_draw"])
    if sub.empty:
        return pd.DataFrame(columns=["scenario_id", "sample_id", "metric_value"])

    if metric_kind in {"yield_ratio", "ef_ratio", "ruminate_ratio"}:
        sub["metric_value"] = 1.0 + sub["value_draw"]
    else:
        raise ValueError(f"Unknown metric_kind: {metric_kind}")

    rows: List[Dict[str, float]] = []
    for (scenario_id, sample_id), g in sub.groupby(["scenario_id", "sample_id"], sort=False):
        vals = g["metric_value"].to_numpy(dtype=float)
        weights = g["weight_kcal_total"].to_numpy(dtype=float)
        weights = np.where(np.isfinite(weights) & (weights > 0), weights, 1.0)
        metric = float(np.average(vals, weights=weights)) if len(vals) else np.nan
        rows.append(
            {
                "scenario_id": str(scenario_id),
                "sample_id": int(sample_id),
                "metric_value": metric,
            }
        )
    return pd.DataFrame(rows)


def _yield_bucket(change: float) -> Optional[str]:
    if not np.isfinite(change):
        return None
    if change >= 0.60:
        return "yield_ge_60"
    if change >= 0.20:
        return "yield_20_60"
    if change >= -0.20:
        return "yield_pm_20"
    return "yield_lt_m20"


def _ef_bucket(change: float) -> Optional[str]:
    if not np.isfinite(change):
        return None
    if change <= -0.60:
        return "ef_down_60_plus"
    if change < -0.20:
        return "ef_down_20_60"
    if change <= 0.20:
        return "ef_pm_20"
    return "ef_up_20_plus"


def _ruminate_bucket(share: float) -> Optional[str]:
    if not np.isfinite(share):
        return None
    share_pct = share * 100.0
    if share_pct < 2.0:
        return "rumi_lt_2"
    if share_pct < 6.0:
        return "rumi_2_6"
    if share_pct <= 10.0:
        return "rumi_6_10"
    return "rumi_gt_10"


def _build_panel_samples(
    draws_df: pd.DataFrame,
    weight_df: pd.DataFrame,
    emissions_df: pd.DataFrame,
    realized_ruminant_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    panel_rows: List[pd.DataFrame] = []

    yield_metric = _aggregate_draw_metric(draws_df, weight_df, kind="yield_rate", metric_kind="yield_ratio")
    if not yield_metric.empty:
        yield_metric["change_value"] = pd.to_numeric(yield_metric["metric_value"], errors="coerce") - 1.0
        yield_metric["scenario_key"] = yield_metric["change_value"].apply(_yield_bucket)
        yield_metric["metric_display"] = yield_metric["change_value"] * 100.0
        yield_metric["panel"] = "yield"
        panel_rows.append(yield_metric)

    ef_metric = _aggregate_draw_metric(draws_df, weight_df, kind="emission_factor", metric_kind="ef_ratio")
    if not ef_metric.empty:
        ef_metric["change_value"] = pd.to_numeric(ef_metric["metric_value"], errors="coerce") - 1.0
        ef_metric["scenario_key"] = ef_metric["change_value"].apply(_ef_bucket)
        ef_metric["metric_display"] = ef_metric["change_value"] * 100.0
        ef_metric["panel"] = "emission_factor"
        panel_rows.append(ef_metric)

    if realized_ruminant_df is not None and not realized_ruminant_df.empty:
        rumi_metric = realized_ruminant_df.copy()
        print("[INFO] ruminant share metric source: solved Qd realized kcal share")
    else:
        rumi_metric = _aggregate_draw_metric(draws_df, weight_df, kind="ruminant_reduction", metric_kind="ruminate_ratio")
        if not rumi_metric.empty:
            rumi_metric["metric_value"] = float(RUMINANT_CURRENT_SHARE) * pd.to_numeric(
                rumi_metric["metric_value"], errors="coerce"
            )
            print("[INFO] ruminant share metric source: draws_long weighted average x current share")
    if not rumi_metric.empty:
        rumi_metric["scenario_key"] = pd.to_numeric(rumi_metric["metric_value"], errors="coerce").apply(_ruminate_bucket)
        rumi_metric["metric_display"] = pd.to_numeric(rumi_metric["metric_value"], errors="coerce") * 100.0
        rumi_metric["panel"] = "ruminate_share"
        panel_rows.append(rumi_metric)

    if not panel_rows:
        raise RuntimeError("No panel sample rows could be built from merged MC outputs.")

    samples = pd.concat(panel_rows, ignore_index=True)
    samples = samples.dropna(subset=["scenario_key"]).copy()
    samples["scenario_key"] = samples["scenario_key"].astype(str)
    samples = samples.merge(emissions_df, on=["scenario_id", "sample_id"], how="inner")

    labels: Dict[str, str] = {}
    for panel, spec in PANEL_SPECS.items():
        for key, label in spec["labels"].items():
            labels[key] = label
    samples["scenario_label"] = samples["scenario_key"].map(labels).fillna(samples["scenario_key"])
    return samples


def _build_histogram(panel_samples: pd.DataFrame, x_min: float, x_max: float) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for (panel, key, label), sub in panel_samples.groupby(["panel", "scenario_key", "scenario_label"], sort=False):
        values = pd.to_numeric(sub["emissions_2080_gt"], errors="coerce").dropna().to_numpy(dtype=float)
        if values.size == 0:
            continue
        counts, edges = np.histogram(values, bins=BINS, range=(x_min, x_max))
        for idx in range(len(counts)):
            rows.append(
                {
                    "panel": str(panel),
                    "scenario_key": str(key),
                    "scenario_label": str(label),
                    "bin_left": float(edges[idx]),
                    "bin_right": float(edges[idx + 1]),
                    "count": int(counts[idx]),
                }
            )
    return pd.DataFrame(rows)


def _build_emission_mean_lookup(panel_samples: pd.DataFrame) -> pd.DataFrame:
    work = panel_samples[["panel", "scenario_key", "emissions_2080_gt"]].copy()
    work["emissions_2080_gt"] = pd.to_numeric(work["emissions_2080_gt"], errors="coerce")
    work = work.dropna(subset=["panel", "scenario_key", "emissions_2080_gt"])
    if work.empty:
        return pd.DataFrame(columns=["panel", "scenario_key", "emissions_2080_gt_mean"])
    return (
        work.groupby(["panel", "scenario_key"], as_index=False)["emissions_2080_gt"]
        .mean()
        .rename(columns={"emissions_2080_gt": "emissions_2080_gt_mean"})
    )


def _plot_targets(ax: Axes, targets: List[Tuple[str, float]], ymax: float) -> None:
    y_text = ymax * 0.97
    for label, value in targets:
        color = TARGET_COLORS.get(label, "#666666")
        ax.axvline(value, color=color, linewidth=1.7, linestyle=(0, (6, 4)), alpha=0.95)
        if label == "Current":
            ax.text(
                value - 0.08,
                y_text,
                label,
                color=color,
                fontsize=TARGET_LABEL_FONTSIZE,
                fontweight="bold",
                fontstyle="italic",
                ha="right",
                va="top",
            )
        else:
            ax.text(
                value + 0.08,
                y_text,
                label,
                color=color,
                fontsize=TARGET_LABEL_FONTSIZE,
                fontweight="bold",
                ha="left",
                va="top",
            )


def _plot_density_panel(
    ax: Axes,
    hist: pd.DataFrame,
    emission_means: pd.DataFrame,
    *,
    panel: str,
    x_min: float,
    x_max: float,
    targets: List[Tuple[str, float]],
) -> None:
    spec = PANEL_SPECS[panel]
    panel_df = hist[hist["panel"] == panel].copy()
    if panel_df.empty:
        raise ValueError(f"No histogram data for panel: {panel}")

    panel_df["bin_left"] = pd.to_numeric(panel_df["bin_left"], errors="coerce")
    panel_df["bin_right"] = pd.to_numeric(panel_df["bin_right"], errors="coerce")
    panel_df["count"] = pd.to_numeric(panel_df["count"], errors="coerce").fillna(0.0)
    panel_df = panel_df.dropna(subset=["bin_left", "bin_right"])
    panel_df["x_mid"] = (panel_df["bin_left"] + panel_df["bin_right"]) / 2.0

    ymax = 0.0
    curves: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    for key in spec["order"]:
        sub = panel_df[panel_df["scenario_key"] == key].sort_values("bin_left")
        if sub.empty:
            continue
        x = sub["x_mid"].to_numpy(dtype=float)
        y = _smooth_counts(sub["count"].to_numpy(dtype=float), SMOOTH_SIGMA_BINS)
        curves[key] = (x, y)
        if y.size:
            ymax = max(ymax, float(np.max(y)))
        ax.plot(
            x,
            y,
            color=spec["colors"].get(key, "#777777"),
            linewidth=5.6,
            alpha=0.78,
        )
        mean_sub = emission_means[
            (emission_means["panel"] == panel)
            & (emission_means["scenario_key"] == key)
        ]
        if not mean_sub.empty:
            mean_x = pd.to_numeric(mean_sub["emissions_2080_gt_mean"].iloc[0], errors="coerce")
            if pd.notna(mean_x) and np.isfinite(float(mean_x)):
                ax.axvline(
                    float(mean_x),
                    color=spec["colors"].get(key, "#777777"),
                    linewidth=MEAN_LINEWIDTH,
                    linestyle="-",
                    alpha=MEAN_LINE_ALPHA,
                    zorder=2.2,
                )

    if ymax <= 0:
        ymax = 1.0
    ax.set_ylim(0, ymax * 1.18)
    _plot_targets(ax, targets, ymax * 1.18)

    for key in spec["order"]:
        if key not in curves:
            continue
        x, y = curves[key]
        if not len(y):
            continue
        idx = int(np.argmax(y))
        dx, dy = spec["label_offsets"].get(key, (0.0, 0.04))
        ax.text(
            float(x[idx]) + float(dx),
            float(y[idx]) + ymax * float(dy),
            spec["labels"][key],
            color=spec["colors"].get(key, "#777777"),
            fontsize=INLINE_LABEL_FONTSIZE,
            fontweight="bold",
            ha="center",
            va="bottom",
        )

    ax.set_xlim(x_min, x_max)
    ax.set_title(spec["title"], fontsize=PANEL_TITLE_FONTSIZE, fontweight="bold", loc="left", pad=6)
    ax.set_ylabel("Number of simulations", fontsize=AXIS_LABEL_FONTSIZE, fontweight="bold", labelpad=10)
    ax.tick_params(axis="both", which="both", labelsize=TICK_LABEL_FONTSIZE, width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    _ensure_dir(FIG5_DIR)

    targets = _load_targets()
    emissions_df = _load_mc_success_emissions()
    draws_df = _load_draws_long()
    weight_df = _load_draw_weights()
    realized_ruminant_df = _load_realized_ruminant_share()
    panel_samples = _build_panel_samples(draws_df, weight_df, emissions_df, realized_ruminant_df)

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
    emission_means = _build_emission_mean_lookup(panel_samples)
    panel_samples_path = FIG5_DIR / "panel_samples_v3.csv"
    hist_path = FIG5_DIR / "histogram_v3.csv"
    means_path = FIG5_DIR / "emission_means_v3.csv"
    panel_samples.to_csv(panel_samples_path, index=False, encoding="utf-8-sig")
    hist.to_csv(hist_path, index=False, encoding="utf-8-sig")
    emission_means.to_csv(means_path, index=False, encoding="utf-8-sig")

    print(f"[DONE] panel samples: {panel_samples_path}")
    print(f"[DONE] histogram: {hist_path}")
    print(f"[DONE] emission means: {means_path}")

    for panel, spec in PANEL_SPECS.items():
        fig, ax = plt.subplots(1, 1, figsize=(8.5, 5.5))
        _plot_density_panel(ax, hist, emission_means, panel=panel, x_min=x_min, x_max=x_max, targets=targets)
        ax.set_xlabel("GHG emission in 2080 (Gt CO$_2$eq/yr)", fontsize=AXIS_LABEL_FONTSIZE, fontweight="bold", labelpad=10)
        fig.tight_layout()

        png_path = FIG5_DIR / f"{spec['file_stem']}.png"
        svg_path = FIG5_DIR / f"{spec['file_stem']}.svg"
        fig.savefig(png_path, dpi=800)
        fig.savefig(svg_path)
        plt.close(fig)

        print(f"[DONE] {png_path}")
        print(f"[DONE] {svg_path}")

    for panel, spec in PANEL_SPECS.items():
        sub = panel_samples[panel_samples["panel"] == panel]
        counts = sub["scenario_key"].value_counts()
        summary = ", ".join(f"{spec['labels'][key]}={int(counts.get(key, 0))}" for key in spec["order"])
        print(f"[INFO] {panel}: {summary}")


if __name__ == "__main__":
    main()
