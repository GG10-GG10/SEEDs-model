from __future__ import annotations

import runpy
import textwrap
from pathlib import Path
from typing import Dict, Iterable, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config_paths import get_results_base


BASE_SCENARIO = "BASE"
TARGET_SCENARIO = "S30"
SUMMARY_NAME = "Y2080_Emission_result_summary.xlsx"
OUTPUT_DIR = Path(get_results_base()) / "Plot" / "Fig10"
VALUE_COL = "Y2080_CO2eq"
GT_DIVISOR = 1_000_000.0
FOREST_PROCESS = "Forest"
FOREST_COLOR = "#006d2c"
INCREASE_COLOR = "#bdbdbd"
TOTAL_COLOR = "#202020"
EDGE_COLOR = "#303030"
DELTA_EDGE_LINEWIDTH = 0.45
TOTAL_GRADIENT_DARK = "#050505"
TOTAL_GRADIENT_LIGHT = "#6a6a6a"
FIG_SIZE = (13.2, 6.4)
BAR_WIDTH_BY_PANEL = {
    "process": 0.76,
    "item": 0.74,
}
X_STEP_BY_PANEL = {
    "process": 0.84,
    "item": 0.84,
}


def _load_process_colors() -> Dict[str, str]:
    script_path = Path(__file__).with_name("SP_M1a_Figure_pie_structure_plot_v2.1.py")
    colors: Dict[str, str] = {}
    if script_path.exists():
        try:
            namespace = runpy.run_path(str(script_path))
            raw = namespace.get("PROCESS_COLORS", {})
            if isinstance(raw, dict):
                colors.update({str(k): str(v) for k, v in raw.items()})
        except Exception as exc:
            print(f"[WARN] Failed to read colors from {script_path.name}: {exc}")
    if not colors:
        try:
            import SP_M1a_Figure_pie_structure_plot_v2 as base_colors

            colors.update({str(k): str(v) for k, v in base_colors.PROCESS_COLORS.items()})
        except Exception:
            pass
    colors[FOREST_PROCESS] = FOREST_COLOR
    return colors


PROCESS_COLORS = _load_process_colors()


def _summary_path(scenario: str) -> Path:
    return Path(get_results_base(scenario)) / SUMMARY_NAME


def _read_summary_sheet(scenario: str, sheet_name: str) -> pd.DataFrame:
    path = _summary_path(scenario)
    if not path.exists():
        raise FileNotFoundError(f"Missing summary workbook: {path}")
    df = pd.read_excel(path, sheet_name=sheet_name)
    if VALUE_COL not in df.columns:
        raise KeyError(f"{path} sheet {sheet_name!r} missing {VALUE_COL}")
    df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce").fillna(0.0)
    return df


def _series_from_sheet(scenario: str, sheet_name: str, label_col: str) -> pd.Series:
    df = _read_summary_sheet(scenario, sheet_name)
    if label_col not in df.columns:
        raise KeyError(f"{scenario} sheet {sheet_name!r} missing {label_col}")
    labels = df[label_col].astype("string").str.strip()
    work = pd.DataFrame({"label": labels, "value": df[VALUE_COL]})
    work = work.loc[work["label"].notna() & work["label"].ne("")].copy()
    return work.groupby("label", dropna=False)["value"].sum()


def _dominant_reduction_process_by_item() -> Dict[str, str]:
    base = _read_summary_sheet(BASE_SCENARIO, "Process-Item")
    target = _read_summary_sheet(TARGET_SCENARIO, "Process-Item")
    required = {"Process", "Item", VALUE_COL}
    if not required.issubset(base.columns) or not required.issubset(target.columns):
        return {}

    def prep(df: pd.DataFrame, value_name: str) -> pd.DataFrame:
        out = df[["Process", "Item", VALUE_COL]].copy()
        out["Process"] = out["Process"].astype("string").str.strip()
        out["Item"] = out["Item"].astype("string").str.strip()
        out[VALUE_COL] = pd.to_numeric(out[VALUE_COL], errors="coerce").fillna(0.0)
        out = out.loc[out["Process"].notna() & out["Item"].notna()].copy()
        return (
            out.groupby(["Item", "Process"], as_index=False)[VALUE_COL]
            .sum()
            .rename(columns={VALUE_COL: value_name})
        )

    merged = prep(base, "base").merge(prep(target, "target"), on=["Item", "Process"], how="outer")
    merged[["base", "target"]] = merged[["base", "target"]].fillna(0.0)
    merged["delta"] = merged["target"] - merged["base"]

    dominant: Dict[str, str] = {}
    for item, group in merged.groupby("Item", sort=False):
        reductions = group.loc[group["delta"].lt(0)].copy()
        if not reductions.empty:
            row = reductions.sort_values("delta", ascending=True, kind="mergesort").iloc[0]
        else:
            row = group.assign(abs_delta=group["delta"].abs()).sort_values(
                "abs_delta", ascending=False, kind="mergesort"
            ).iloc[0]
        dominant[str(item)] = str(row["Process"])
    return dominant


def _process_color(process: str) -> str:
    return PROCESS_COLORS.get(str(process), "#9e9e9e")


def _wrap_label(label: str, width: int = 15) -> str:
    text = str(label)
    if len(text) <= width:
        return text
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def _build_waterfall_data(
    *,
    sheet_name: str,
    label_col: str,
    color_by: str,
) -> pd.DataFrame:
    base = _series_from_sheet(BASE_SCENARIO, sheet_name, label_col)
    target = _series_from_sheet(TARGET_SCENARIO, sheet_name, label_col)
    labels = sorted(set(base.index).union(set(target.index)))
    work = pd.DataFrame({"label": labels})
    work["base_kt"] = work["label"].map(base).fillna(0.0)
    work["target_kt"] = work["label"].map(target).fillna(0.0)
    work["delta_kt"] = work["target_kt"] - work["base_kt"]
    work = work.loc[work["delta_kt"].abs().gt(1e-9)].copy()

    reductions = work.loc[work["delta_kt"].lt(0)].sort_values("delta_kt", ascending=True, kind="mergesort")
    increases = work.loc[work["delta_kt"].ge(0)].sort_values("delta_kt", ascending=False, kind="mergesort")
    work = pd.concat([reductions, increases], ignore_index=True)

    if color_by == "process":
        work["dominant_process"] = work["label"]
    elif color_by == "item":
        dominant = _dominant_reduction_process_by_item()
        work["dominant_process"] = work["label"].map(dominant).fillna("")
    else:
        work["dominant_process"] = ""
    process_colors = work["dominant_process"].map(_process_color)
    work["color"] = np.where(
        work["delta_kt"].lt(0) | work["dominant_process"].eq("Fish farming"),
        process_colors,
        INCREASE_COLOR,
    )
    work["color"] = work["color"].fillna(INCREASE_COLOR)

    running = float(base.sum())
    rows = [
        {
            "bar_type": "total_start",
            "label": BASE_SCENARIO,
            "dominant_process": "",
            "base_kt": np.nan,
            "target_kt": np.nan,
            "delta_kt": running,
            "start_kt": 0.0,
            "end_kt": running,
            "bottom_kt": 0.0,
            "height_kt": running,
            "color": TOTAL_COLOR,
        }
    ]
    for row in work.to_dict(orient="records"):
        delta = float(row["delta_kt"])
        start = running
        end = running + delta
        rows.append(
            {
                "bar_type": "delta",
                "label": row["label"],
                "dominant_process": row.get("dominant_process", ""),
                "base_kt": row["base_kt"],
                "target_kt": row["target_kt"],
                "delta_kt": delta,
                "start_kt": start,
                "end_kt": end,
                "bottom_kt": min(start, end),
                "height_kt": abs(delta),
                "color": row["color"],
            }
        )
        running = end

    final_total = float(target.sum())
    rows.append(
        {
            "bar_type": "total_end",
            "label": TARGET_SCENARIO,
            "dominant_process": "",
            "base_kt": np.nan,
            "target_kt": np.nan,
            "delta_kt": final_total,
            "start_kt": 0.0,
            "end_kt": final_total,
            "bottom_kt": 0.0,
            "height_kt": final_total,
            "color": TOTAL_COLOR,
        }
    )

    out = pd.DataFrame(rows)
    for col in ["base_kt", "target_kt", "delta_kt", "start_kt", "end_kt", "bottom_kt", "height_kt"]:
        out[col.replace("_kt", "_Gt")] = out[col] / GT_DIVISOR
    return out


def _nice_ylim(data: pd.DataFrame) -> Tuple[float, float]:
    low = float(pd.to_numeric(data["bottom_Gt"], errors="coerce").min())
    high = float(pd.to_numeric(data["end_Gt"], errors="coerce").max())
    high = max(high, float((data["bottom_Gt"] + data["height_Gt"]).max()))
    span = max(high - low, 1.0)
    return min(0.0, low - span * 0.08), high + span * 0.12


def _hex_to_rgb01(hex_color: str) -> np.ndarray:
    text = str(hex_color).strip().lstrip("#")
    if len(text) != 6:
        return np.array([0.0, 0.0, 0.0], dtype=float)
    return np.array([int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=float)


def _draw_total_gradient_bar(
    ax: plt.Axes,
    *,
    x_center: float,
    bottom: float,
    height: float,
    width: float,
) -> None:
    rect = plt.Rectangle(
        (x_center - width / 2.0, bottom),
        width,
        height,
        facecolor="none",
        edgecolor=EDGE_COLOR,
        linewidth=0.85,
        zorder=4,
    )
    ax.add_patch(rect)
    n = 256
    pos = np.linspace(0.0, 1.0, n)
    # Bright vertical highlight slightly right of center, close to the reference style.
    highlight = np.exp(-((pos - 0.58) / 0.22) ** 2)
    dark = _hex_to_rgb01(TOTAL_GRADIENT_DARK)
    light = _hex_to_rgb01(TOTAL_GRADIENT_LIGHT)
    rgb = dark[None, :] * (1.0 - highlight[:, None]) + light[None, :] * highlight[:, None]
    img = np.repeat(rgb[None, :, :], 4, axis=0)
    im = ax.imshow(
        img,
        extent=(x_center - width / 2.0, x_center + width / 2.0, bottom, bottom + height),
        origin="lower",
        aspect="auto",
        interpolation="bicubic",
        zorder=3.7,
    )
    im.set_clip_path(rect)


def _plot_waterfall(data: pd.DataFrame, *, panel: str, output_stem: str) -> Tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=FIG_SIZE, facecolor="white")
    x_step = X_STEP_BY_PANEL.get(panel, 0.84)
    x = np.arange(len(data), dtype=float) * x_step
    bar_width = BAR_WIDTH_BY_PANEL.get(panel, 0.82)

    delta_mask = data["bar_type"].eq("delta")
    ax.bar(
        x[delta_mask.to_numpy()],
        data.loc[delta_mask, "height_Gt"],
        bottom=data.loc[delta_mask, "bottom_Gt"],
        width=bar_width,
        color=data.loc[delta_mask, "color"],
        edgecolor=EDGE_COLOR,
        linewidth=DELTA_EDGE_LINEWIDTH,
        zorder=3,
    )
    for idx, row in data.loc[~delta_mask].iterrows():
        _draw_total_gradient_bar(
            ax,
            x_center=float(x[idx]),
            bottom=float(row["bottom_Gt"]),
            height=float(row["height_Gt"]),
            width=bar_width,
        )

    for idx, row in data.iterrows():
        xpos = float(x[idx])
        if row["bar_type"] == "delta":
            value = float(row["delta_Gt"])
            if abs(value) < 0.15:
                continue
            y = float(row["end_Gt"])
            va = "top" if value < 0 else "bottom"
            offset = -0.18 if value < 0 else 0.18
            ax.text(
                xpos,
                y + offset,
                f"{value:+.1f}",
                ha="center",
                va=va,
                fontsize=8.5,
                color="#202020",
                rotation=0,
            )
        else:
            ax.text(
                xpos,
                float(row["end_Gt"]) + 0.25,
                f"{float(row['end_Gt']):.1f}",
                ha="center",
                va="bottom",
                fontsize=9.5,
                fontweight="bold",
                color="#202020",
            )

    labels = [_wrap_label(label, 14 if panel == "item" else 17) for label in data["label"]]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=52, ha="right", fontsize=9)
    ax.set_ylabel("Food-system GHG emissions (Gt CO2-eq yr$^{-1}$)", fontsize=11)
    ax.axhline(0, color="#202020", linewidth=0.85)
    ax.grid(False)
    ax.set_axisbelow(True)
    ax.set_ylim(*_nice_ylim(data))
    ax.set_xlim(float(x.min()) - bar_width * 0.62, float(x.max()) + bar_width * 0.62)
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_color("#202020")
        ax.spines[spine].set_linewidth(0.75)
    ax.tick_params(axis="both", width=0.75, length=4, color="#202020")

    fig.subplots_adjust(left=0.085, right=0.985, bottom=0.31, top=0.965)
    png = OUTPUT_DIR / f"{output_stem}.png"
    svg = OUTPUT_DIR / f"{output_stem}.svg"
    fig.savefig(png, dpi=450)
    fig.savefig(svg)
    plt.close(fig)
    return png, svg


def build_fig10_emission_reduction_waterfalls() -> Dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    process_data = _build_waterfall_data(
        sheet_name="Process",
        label_col="Process",
        color_by="process",
    )
    item_data = _build_waterfall_data(
        sheet_name="Item",
        label_col="Item",
        color_by="item",
    )

    process_csv = OUTPUT_DIR / "Figure10_emis_reduction_waterfall_process_data.csv"
    item_csv = OUTPUT_DIR / "Figure10_emis_reduction_waterfall_item_data.csv"
    process_data.to_csv(process_csv, index=False, encoding="utf-8-sig")
    item_data.to_csv(item_csv, index=False, encoding="utf-8-sig")
    data_xlsx = OUTPUT_DIR / "Figure10_emis_reduction_waterfall_data.xlsx"
    with pd.ExcelWriter(data_xlsx, engine="openpyxl") as writer:
        process_data.to_excel(writer, sheet_name="Process", index=False)
        item_data.to_excel(writer, sheet_name="Item", index=False)

    process_png, process_svg = _plot_waterfall(
        process_data,
        panel="process",
        output_stem="Figure10_emis_reduction_waterfall_process",
    )
    item_png, item_svg = _plot_waterfall(
        item_data,
        panel="item",
        output_stem="Figure10_emis_reduction_waterfall_item",
    )
    return {
        "process_png": process_png,
        "process_svg": process_svg,
        "item_png": item_png,
        "item_svg": item_svg,
        "process_csv": process_csv,
        "item_csv": item_csv,
        "data_xlsx": data_xlsx,
    }


def main() -> None:
    outputs = build_fig10_emission_reduction_waterfalls()
    for key, path in outputs.items():
        print(f"[DONE] {key}: {path}")


if __name__ == "__main__":
    main()
