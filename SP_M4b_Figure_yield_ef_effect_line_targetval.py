# -*- coding: utf-8 -*-
"""
Plot yield/EF/ruminate-intake sensitivity curves for Figure 5 (v2).
Reads: output/Plot/Fig5/samples.csv, output/MC_Sensitivity_Variable_Effect/samples.csv,
or histogram.csv + targets.csv
Outputs: PNG + SVG in the same folder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from config_paths import get_results_base

FIG_DIR = Path(get_results_base()) / "Plot" / "Fig5"
SAMPLES_PATH = FIG_DIR / "samples.csv"
HIST_PATH = FIG_DIR / "histogram.csv"
TARGETS_PATH = FIG_DIR / "targets.csv"
VARIABLE_EFFECT_SAMPLES_PATH = Path(get_results_base()) / "MC_Sensitivity_Variable_Effect" / "samples.csv"

# Front-end plotting options.
CONFIG = {
    # Input source:
    # "auto_latest" -> use the newest available sample file
    # "fig5_samples" -> use output/Plot/Fig5/samples.csv
    # "variable_effect_samples" -> use output/MC_Sensitivity_Variable_Effect/samples.csv
    # "histogram" -> use output/Plot/Fig5/histogram.csv
    "input_source": "auto_latest",
    # Y-axis mode:
    # "density" -> normalized density; area under each curve is about 1
    # "probability" -> normalized bin probability; values across bins sum to 1
    # "count" -> raw valid-run counts per bin, not comparable when n differs
    "y_axis_mode": "probability",
}

TARGET_COLORS = {
    "1.5D": "#2ca25f",
    "2D": "#2b8cbe",
    "RCP4.5": "#f1a340",
    "Current": "#d7301f",
}

PANEL_SPECS = [
    {
        "panel": "yield",
        "aliases": ["yield"],
        "title": "A. Effects of yield + feed efficiency",
        "order": ["yield_up_100", "yield_up_90", "yield_up_50", "yield_current", "yield_down_20"],
    },
    {
        "panel": "emission_factor",
        "aliases": ["emission_factor"],
        "title": "B. Effects of emission intensity",
        "order": ["ef_down_90", "ef_down_80", "ef_down_50", "ef_down_40", "ef_current", "ef_up_20"],
    },
    {
        "panel": "ruminate_intake",
        "aliases": ["ruminate_intake", "ruminant_reduction", "ruminate_share"],
        "title": "C. Effects of ruminant intake",
        "order": [
            "ruminant_down_90",
            "ruminate_intake_down_90",
            "ruminant_down_50",
            "ruminate_intake_down_50",
            "ruminate_intake_down_40",
            "ruminate_intake_down_20",
            "ruminant_current",
            "ruminate_intake_current",
            "rumi_lt_2",
            "rumi_2_6",
            "rumi_6_10",
            "rumi_gt_10",
            "ruminant_up_20",
            "ruminate_intake_up_20",
        ],
    },
]

LABEL_MAP = {
    "yield_up_100": "Yield rate +100%",
    "yield_up_90": "Yield rate +90%",
    "yield_up_50": "Yield rate +50%",
    "yield_current": "Yield rate current",
    "yield_down_20": "Yield rate -20%",
    "yield_ge_60": "Yield >= +60%",
    "yield_20_60": "Yield +20% to +60%",
    "yield_pm_20": "Yield -20% to +20%",
    "yield_lt_m20": "Yield < -20%",
    "ef_down_90": "Emission factor -90%",
    "ef_down_80": "Emission factor -80%",
    "ef_down_50": "Emission factor -50%",
    "ef_down_40": "Emission factor -40%",
    "ef_current": "Emission factor current",
    "ef_up_20": "Emission factor +20%",
    "ef_down_60_plus": "EF down >= 60%",
    "ef_down_20_60": "EF down 20% to 60%",
    "ef_pm_20": "EF change -20% to +20%",
    "ef_up_20_plus": "EF up > 20%",
    "ruminant_down_90": "Ruminant intake -90%",
    "ruminate_intake_down_90": "Ruminant intake -90%",
    "ruminant_down_50": "Ruminant intake -50%",
    "ruminate_intake_down_50": "Ruminant intake -50%",
    "ruminate_intake_down_40": "Ruminate intake -40%",
    "ruminate_intake_down_20": "Ruminate intake -20%",
    "ruminant_current": "Ruminant intake current",
    "ruminate_intake_current": "Ruminate intake current",
    "ruminant_up_20": "Ruminant intake +20%",
    "ruminate_intake_up_20": "Ruminate intake +20%",
    "rumi_lt_2": "Ruminant share < 2%",
    "rumi_2_6": "Ruminant share 2% to 6%",
    "rumi_6_10": "Ruminant share 6% to 10%",
    "rumi_gt_10": "Ruminant share > 10%",
}

CURVE_COLORS = {
    # Match SP1_2 palette families:
    # Yield rate -> red, Emission control -> cyan, Ruminate rate -> purple.
    "yield_up_100": "#f46d6d",
    "yield_up_90": "#f46d6d",
    "yield_up_50": "#ef4a4a",
    "yield_current": "#e31a1c",
    "yield_down_20": "#b71214",
    "yield_ge_60": "#f98d8f",
    "yield_20_60": "#f26b6f",
    "yield_pm_20": "#e84a4d",
    "yield_lt_m20": "#be2f34",
    "ef_down_90": "#b7ddb0",
    "ef_down_80": "#9fca98",
    "ef_down_50": "#86bd7a",
    "ef_down_40": "#6ca563",
    "ef_current": "#4c6f4a",
    "ef_up_20": "#2c462b",
    "ef_down_60_plus": "#b7ddb0",
    "ef_down_20_60": "#86bd7a",
    "ef_pm_20": "#5d8758",
    "ef_up_20_plus": "#2f4d2c",
    "ruminant_down_90": "#b3a6dd",
    "ruminate_intake_down_90": "#b3a6dd",
    "ruminant_down_50": "#8c7aca",
    "ruminate_intake_down_50": "#8c7aca",
    "ruminate_intake_down_40": "#9888c7",
    "ruminate_intake_down_20": "#7e6ab9",
    "ruminant_current": "#5A4884",
    "ruminate_intake_current": "#5A4884",
    "ruminant_up_20": "#3f2e65",
    "ruminate_intake_up_20": "#3f2e65",
    "rumi_lt_2": "#b3a6dd",
    "rumi_2_6": "#8c7aca",
    "rumi_6_10": "#675694",
    "rumi_gt_10": "#47366d",
}

SMOOTH_SIGMA_BINS = 2.2
BINS = 120
INVALID_TOTAL_CO2EQ_GT_VALUES = (1.264874,)
Y_AXIS_LABELS = {
    "density": "Normalized density",
    "probability": "Probability per bin",
    "count": "Number of simulations",
}

# Match SP1_2 sizing and typography scale.
FIG_WIDTH = 8.5
PANEL_HEIGHT = 5.5
AXIS_LABEL_FONTSIZE = 13.5
TICK_LABEL_FONTSIZE = 13
PANEL_TITLE_FONTSIZE = 13.5
LEGEND_FONTSIZE = 10.5


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _is_ascii_text(value: str) -> bool:
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _scenario_label(key: str, raw_label: Optional[Any] = None) -> str:
    key = str(key).strip()
    if key in LABEL_MAP:
        return LABEL_MAP[key]
    if raw_label is not None and pd.notna(raw_label):
        label = str(raw_label).strip()
        if label and _is_ascii_text(label):
            return label
    return key.replace("_", " ")


def _normalize_y_axis_mode(mode: Any) -> str:
    out = str(mode or "density").strip().lower().replace("-", "_")
    aliases = {
        "normalized_density": "density",
        "pdf": "density",
        "prob": "probability",
        "bin_probability": "probability",
        "raw": "count",
        "raw_count": "count",
        "counts": "count",
    }
    out = aliases.get(out, out)
    if out not in Y_AXIS_LABELS:
        valid = ", ".join(Y_AXIS_LABELS)
        raise ValueError(f"Invalid CONFIG['y_axis_mode']={mode!r}. Valid options: {valid}")
    return out


def _panel_key_label_from_variable(variable: Any, rate_value: Any) -> Tuple[str, str, str]:
    kind = str(variable or "").strip().lower()
    try:
        rate = float(rate_value)
    except Exception:
        return "", "", ""
    pct = int(round(abs(rate) * 100))
    direction = "up" if rate > 0 else "down"

    if kind == "yield_rate":
        if abs(rate) < 1e-9:
            return "yield", "yield_current", LABEL_MAP["yield_current"]
        key = f"yield_{direction}_{pct}"
        return "yield", key, _scenario_label(key)

    if kind == "emission_factor":
        if abs(rate) < 1e-9:
            return "emission_factor", "ef_current", LABEL_MAP["ef_current"]
        key = f"ef_{direction}_{pct}"
        return "emission_factor", key, _scenario_label(key)

    if kind == "ruminant_reduction":
        if abs(rate) < 1e-9:
            return "ruminant_reduction", "ruminant_current", LABEL_MAP["ruminant_current"]
        key = f"ruminant_{direction}_{pct}"
        return "ruminant_reduction", key, _scenario_label(key)

    return "", "", ""


def _samples_to_panel_schema(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    df = df.copy()
    panel_required = {"panel", "scenario_key", "emissions_2080_gt"}
    if panel_required.issubset(df.columns):
        if "scenario_label" not in df.columns:
            df["scenario_label"] = df["scenario_key"].map(_scenario_label)
        return df

    ve_required = {"variable", "rate_value", "sample_id", "emissions_2080_gt"}
    missing = sorted(ve_required.difference(df.columns))
    if missing:
        raise ValueError(f"{path.name} missing required columns: {', '.join(missing)}")

    mapped = df.apply(
        lambda row: _panel_key_label_from_variable(row.get("variable"), row.get("rate_value")),
        axis=1,
        result_type="expand",
    )
    mapped.columns = ["panel", "scenario_key", "scenario_label"]
    out = pd.concat([mapped, df], axis=1)
    out = out[out["panel"].astype(str).str.strip() != ""].copy()
    if "year" not in out.columns:
        out["year"] = 2080
    return out


def _load_targets() -> List[Tuple[str, float]]:
    if TARGETS_PATH.exists():
        df = pd.read_csv(TARGETS_PATH)
        df.columns = [str(c).strip() for c in df.columns]
        if "label" in df.columns and "emission_gt" in df.columns:
            out: List[Tuple[str, float]] = []
            for row in df.itertuples(index=False):
                if pd.notna(row.label) and pd.notna(row.emission_gt):
                    val = _to_float(row.emission_gt, np.nan)
                    if np.isfinite(val):
                        out.append((str(row.label), val))
            if out:
                return out
    return [("1.5D", 0.9), ("2D", 4.), ("RCP4.5", 14.5), ("Current", 12.9)]


def _read_csv_trimmed(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _sentinel_mask(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    bad_vals = [round(float(x), 6) for x in INVALID_TOTAL_CO2EQ_GT_VALUES]
    return vals.round(6).isin(bad_vals)


def _histogram_from_samples(path: Path) -> pd.DataFrame:
    df = _samples_to_panel_schema(_read_csv_trimmed(path), path)
    required = {"panel", "scenario_key", "emissions_2080_gt"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"{path.name} missing required columns: {', '.join(missing)}")

    df["panel"] = df["panel"].astype(str).str.strip()
    df["scenario_key"] = df["scenario_key"].astype(str).str.strip()
    df["emissions_2080_gt"] = pd.to_numeric(df["emissions_2080_gt"], errors="coerce")
    before_sentinel = len(df)
    df = df.loc[~_sentinel_mask(df["emissions_2080_gt"])].copy()
    if len(df) != before_sentinel:
        print(
            f"[INFO] dropped {before_sentinel - len(df)} sample rows with invalid "
            f"sentinel {INVALID_TOTAL_CO2EQ_GT_VALUES}"
        )
    df = df.dropna(subset=["panel", "scenario_key", "emissions_2080_gt"]).copy()
    if df.empty:
        raise ValueError(f"{path.name} has no numeric emissions_2080_gt values.")

    x_min = float(df["emissions_2080_gt"].min())
    x_max = float(df["emissions_2080_gt"].max())
    if x_min == x_max:
        x_min -= 0.5
        x_max += 0.5

    hist_rows: List[Dict[str, object]] = []

    for (panel, key), sub in df.groupby(["panel", "scenario_key"], sort=False):
        values = sub["emissions_2080_gt"].to_numpy(dtype=float)
        counts, edges = np.histogram(values, bins=BINS, range=(x_min, x_max))
        raw_label: Optional[Any] = None
        if "scenario_label" in sub.columns:
            labels = sub["scenario_label"].dropna().astype(str).str.strip()
            labels = labels[labels != ""]
            if not labels.empty:
                raw_label = labels.iloc[0]
        label = _scenario_label(str(key), raw_label)
        for i in range(len(counts)):
            hist_rows.append(
                {
                    "panel": str(panel),
                    "scenario_key": str(key),
                    "scenario_label": str(label),
                    "bin_left": float(edges[i]),
                    "bin_right": float(edges[i + 1]),
                    "count": int(counts[i]),
                }
            )

    return pd.DataFrame(hist_rows)


def _select_samples_path() -> Optional[Path]:
    source = str(CONFIG.get("input_source", "auto_latest") or "auto_latest").strip().lower()
    if source == "fig5_samples":
        return SAMPLES_PATH if SAMPLES_PATH.exists() else None
    if source == "variable_effect_samples":
        return VARIABLE_EFFECT_SAMPLES_PATH if VARIABLE_EFFECT_SAMPLES_PATH.exists() else None
    if source == "histogram":
        return None
    if source != "auto_latest":
        raise ValueError(
            "Invalid CONFIG['input_source']="
            f"{source!r}. Valid options: auto_latest, fig5_samples, variable_effect_samples, histogram"
        )

    candidates = [p for p in [SAMPLES_PATH, VARIABLE_EFFECT_SAMPLES_PATH] if p.exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_histogram() -> pd.DataFrame:
    samples_path = _select_samples_path()
    if samples_path is not None:
        print(f"[INFO] using samples: {samples_path}")
        return _histogram_from_samples(samples_path)

    if HIST_PATH.exists():
        print(f"[INFO] using histogram: {HIST_PATH}")
        df = _read_csv_trimmed(HIST_PATH)
        if "scenario_key" in df.columns:
            df["scenario_key"] = df["scenario_key"].astype(str).str.strip()
        if "scenario_label" in df.columns and "scenario_key" in df.columns:
            df["scenario_label"] = [
                _scenario_label(key, label)
                for key, label in zip(df["scenario_key"], df["scenario_label"])
            ]
        return df

    raise FileNotFoundError(f"Missing samples.csv or histogram.csv in {FIG_DIR}")


def _smooth_counts(counts: np.ndarray, sigma_bins: float) -> np.ndarray:
    if sigma_bins <= 0:
        return counts
    radius = int(max(1, round(sigma_bins * 3)))
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (x / sigma_bins) ** 2)
    kernel /= kernel.sum()
    return np.convolve(counts, kernel, mode="same")


def _curve_y_values(counts: np.ndarray, bin_width: float, y_axis_mode: str) -> np.ndarray:
    y = _smooth_counts(counts.astype(float), SMOOTH_SIGMA_BINS)
    if y_axis_mode == "count":
        return y

    total = float(np.nansum(y))
    if total <= 0 or not np.isfinite(total):
        return y

    if y_axis_mode == "probability":
        return y / total

    width = float(bin_width)
    if width <= 0 or not np.isfinite(width):
        width = 1.0
    return y / (total * width)


def _plot_panel(
    ax: Axes,
    hist: pd.DataFrame,
    panel: str,
    aliases: List[str],
    order: List[str],
    title: str,
    targets: List[Tuple[str, float]],
    y_axis_mode: str,
) -> None:
    panel_names = {str(panel).strip(), *(str(alias).strip() for alias in aliases)}
    panel_df = hist[hist["panel"].astype(str).str.strip().isin(panel_names)].copy()
    if panel_df.empty:
        available = ", ".join(sorted(hist["panel"].astype(str).str.strip().dropna().unique()))
        raise ValueError(f"No data for panel: {panel}. Available panels: {available}")

    panel_df["scenario_key"] = panel_df["scenario_key"].astype(str).str.strip()
    panel_df["bin_left"] = pd.to_numeric(panel_df["bin_left"], errors="coerce")
    panel_df["bin_right"] = pd.to_numeric(panel_df["bin_right"], errors="coerce")
    panel_df["count"] = pd.to_numeric(panel_df["count"], errors="coerce").fillna(0.0)
    panel_df = panel_df.dropna(subset=["bin_left", "bin_right"])
    panel_df["x_mid"] = (panel_df["bin_left"] + panel_df["bin_right"]) / 2.0

    ymax = 0.0
    plotted = 0
    for key in order:
        sub = panel_df[panel_df["scenario_key"] == key].sort_values("bin_left")
        if sub.empty:
            continue
        x = sub["x_mid"].to_numpy(dtype=float)
        bin_width = float(np.nanmedian((sub["bin_right"] - sub["bin_left"]).to_numpy(dtype=float)))
        y = _curve_y_values(sub["count"].to_numpy(dtype=float), bin_width, y_axis_mode)
        ymax = max(ymax, float(np.max(y)) if y.size else 0.0)
        raw_label = sub["scenario_label"].iloc[0] if "scenario_label" in sub.columns else None
        label = _scenario_label(key, raw_label)
        ax.plot(x, y, color=CURVE_COLORS.get(key, "#377eb8"), linewidth=6.5, label=label,alpha=0.72)
        plotted += 1

    if plotted == 0:
        available_keys = ", ".join(sorted(panel_df["scenario_key"].dropna().unique()))
        expected_keys = ", ".join(order)
        raise ValueError(f"No matching scenario_key for panel {panel}. Expected: {expected_keys}. Available: {available_keys}")

    for label, val in targets:
        ax.axvline(val, color=TARGET_COLORS.get(label, "#666666"), linewidth=1.75, linestyle=(0, (6, 4)), alpha=0.95)

    if ymax <= 0:
        ymax = 1.0
    ax.set_ylim(0, ymax * 1.15)
    ax.set_title(title, fontsize=PANEL_TITLE_FONTSIZE, fontweight="bold", loc="left", pad=6)
    ax.set_ylabel(Y_AXIS_LABELS[y_axis_mode], fontsize=AXIS_LABEL_FONTSIZE, fontweight="bold", labelpad=9)

    ax.tick_params(axis="both", which="both", labelsize=TICK_LABEL_FONTSIZE, width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)


def main() -> None:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    _ensure_dir(FIG_DIR)
    y_axis_mode = _normalize_y_axis_mode(CONFIG.get("y_axis_mode", "density"))
    print(f"[INFO] y_axis_mode={y_axis_mode}")
    hist = _load_histogram()
    targets = _load_targets()
    x_values = pd.concat(
        [
            pd.to_numeric(hist["bin_left"], errors="coerce"),
            pd.to_numeric(hist["bin_right"], errors="coerce"),
            pd.Series([val for _, val in targets], dtype=float),
        ],
        ignore_index=True,
    ).dropna()
    xmin = float(x_values.min())
    xmax = float(x_values.max())

    for spec in PANEL_SPECS:
        panel = str(spec["panel"])
        fig, ax = plt.subplots(1, 1, figsize=(FIG_WIDTH, PANEL_HEIGHT))
        _plot_panel(
            ax,
            hist,
            panel=panel,
            aliases=list(spec.get("aliases", [panel])),
            order=list(spec["order"]),
            title=str(spec["title"]),
            targets=targets,
            y_axis_mode=y_axis_mode,
        )
        ax.legend(loc="upper right", frameon=False, fontsize=LEGEND_FONTSIZE)
        ax.set_xlabel("GHG in 2080 (Gt CO2eq/yr)", fontsize=AXIS_LABEL_FONTSIZE, fontweight="bold", labelpad=10)
        ax.set_xlim(xmin, xmax)

        fig.tight_layout()
        png_path = FIG_DIR / f"Figure5_{panel}_effect_line_v2.png"
        svg_path = FIG_DIR / f"Figure5_{panel}_effect_line_v2.svg"
        fig.savefig(png_path, dpi=800)
        fig.savefig(svg_path)
        plt.close(fig)

        print(f"[DONE] {png_path}")
        print(f"[DONE] {svg_path}")


if __name__ == "__main__":
    main()
