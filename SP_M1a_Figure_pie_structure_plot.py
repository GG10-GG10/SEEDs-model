from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from config_paths import get_results_base


INPUT_NAME = "Y2020_Emis_structure_summary.xlsx"
OUTPUT_STEM = "Figure8_Emis_structure_doughnut"
LEGEND_STEM = "Figure8_Emis_structure_doughnut_legend"
LUC_PROCESSES = [
    "De/Reforestation",
    "Wood harvest",
    "Drained organic soils",
    "Savanna/Peatlands fires",
]
LEGEND_PROCESSES = [
    "Enteric fermentation",
    "Manure management and application",
    "Rice cultivation",
    "Synthetic fertilizers",
    "Crop residue management",
    "Fish farming",
    "De/Reforestation",
    "Wood harvest",
    "Drained organic soils",
    "Savanna/Peatlands fires",
]
PROCESS_COLORS = {
    "Enteric fermentation": "#4eb3d3",
    "Manure management and application": "#084081",
    "Rice cultivation": "#b6df91",
    "Synthetic fertilizers": "#fee08b",
    "Crop residue management": "#70cfd2",
    "Fish farming": "#6a51a3",
    "De/Reforestation": "#cc4c02",
    "Wood harvest": "#662506",
    "Drained organic soils": "#fe9929",
    "Savanna/Peatlands fires": "#a50f15",
    "Forest": "#026429",
}
START_ANGLE = 90
INNER_RADIUS = 0.42
MIDDLE_RADIUS = 0.8
MIDDLE_WIDTH = 0.24
OUTER_RADIUS = 1.35
OUTER_WIDTH = 0.24


def _fig_dir() -> Path:
    return Path(get_results_base()) / "Plot" / "Fig8"


def _summary_path() -> Path:
    return _fig_dir() / INPUT_NAME


def _output_paths() -> Tuple[Path, Path]:
    fig_dir = _fig_dir()
    return fig_dir / f"{OUTPUT_STEM}.png", fig_dir / f"{OUTPUT_STEM}.svg"


def _legend_path() -> Path:
    return _fig_dir() / f"{LEGEND_STEM}.svg"


def _read_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)


def _find_col(df: pd.DataFrame, candidates: Iterable[str]) -> str:
    lower_map = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        col = lower_map.get(candidate.lower())
        if col:
            return col
    wanted = ", ".join(candidates)
    raise KeyError(f"Missing required column. Tried: {wanted}")


def _sort_by_emissions(df: pd.DataFrame, label_col: str) -> pd.DataFrame:
    return (
        df.sort_values(["Y2020_CO2eq", label_col], ascending=[False, True], kind="mergesort")
        .reset_index(drop=True)
    )


def _build_ring_data(summary_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    process_df = _read_sheet(summary_path, "Process")
    item_df = _read_sheet(summary_path, "Item")
    region_df = _read_sheet(summary_path, "Country")
    process_item_df = _read_sheet(summary_path, "Process-Item")
    process_region_df = _read_sheet(summary_path, "Process-Country")

    process_col = _find_col(process_df, ["Process"])
    item_col = _find_col(item_df, ["Item"])
    region_col = _find_col(region_df, ["Region", "Country"])
    process_item_process_col = _find_col(process_item_df, ["Process"])
    process_item_item_col = _find_col(process_item_df, ["Item"])
    process_region_process_col = _find_col(process_region_df, ["Process"])
    process_region_region_col = _find_col(process_region_df, ["Region", "Country"])

    process_df = process_df.rename(columns={process_col: "Process"})
    item_df = item_df.rename(columns={item_col: "Item"})
    region_df = region_df.rename(columns={region_col: "Region"})
    process_item_df = process_item_df.rename(columns={process_item_process_col: "Process", process_item_item_col: "Item"})
    process_region_df = process_region_df.rename(
        columns={process_region_process_col: "Process", process_region_region_col: "Region"}
    )

    for frame in (process_df, item_df, region_df, process_item_df, process_region_df):
        frame["Y2020_CO2eq"] = pd.to_numeric(frame["Y2020_CO2eq"], errors="coerce")
        frame.dropna(subset=["Y2020_CO2eq"], inplace=True)

    process_df = process_df[(process_df["Process"] != "Forest") & (process_df["Y2020_CO2eq"] > 0)].copy()
    item_df = item_df[(item_df["Item"] != "Forestland") & (item_df["Y2020_CO2eq"] > 0)].copy()
    region_df = region_df[region_df["Y2020_CO2eq"] > 0].copy()

    ag_df = process_df[~process_df["Process"].isin(LUC_PROCESSES)].sort_values(
        "Y2020_CO2eq", ascending=False, kind="mergesort"
    )
    luc_df = process_df[process_df["Process"].isin(LUC_PROCESSES)].sort_values(
        "Y2020_CO2eq", ascending=False, kind="mergesort"
    )
    process_df = pd.concat([ag_df, luc_df], ignore_index=True)
    item_df = _sort_by_emissions(item_df, "Item")
    region_df = _sort_by_emissions(region_df, "Region")

    process_item_df = process_item_df[
        (process_item_df["Process"] != "Forest")
        & (process_item_df["Item"] != "Forestland")
        & (process_item_df["Y2020_CO2eq"] > 0)
    ].copy()
    process_region_df = process_region_df[
        (process_region_df["Process"] != "Forest") & (process_region_df["Y2020_CO2eq"] > 0)
    ].copy()

    dominant_item = (
        process_item_df.sort_values(["Item", "Y2020_CO2eq"], ascending=[True, False], kind="mergesort")
        .drop_duplicates(subset=["Item"], keep="first")
        .set_index("Item")["Process"]
        .to_dict()
    )
    dominant_region = (
        process_region_df.sort_values(["Region", "Y2020_CO2eq"], ascending=[True, False], kind="mergesort")
        .drop_duplicates(subset=["Region"], keep="first")
        .set_index("Region")["Process"]
        .to_dict()
    )

    item_df["Dominant_Process"] = item_df["Item"].map(dominant_item)
    region_df["Dominant_Process"] = region_df["Region"].map(dominant_region)

    return process_df, item_df, region_df


def _build_process_colors(process_df: pd.DataFrame) -> Dict[str, str]:
    colors: Dict[str, str] = {}
    for process in process_df["Process"]:
        colors[process] = PROCESS_COLORS.get(process, "#9e9e9e")
    return colors


def _build_derived_colors(
    df: pd.DataFrame,
    label_col: str,
    dominant_col: str,
) -> Dict[str, str]:
    color_map: Dict[str, str] = {}
    fallback = "#bdbdbd"
    for _, row in df.iterrows():
        label = str(row[label_col])
        process = str(row.get(dominant_col, "")).strip()
        color_map[label] = PROCESS_COLORS.get(process, fallback)
    return color_map


def _pie(
    ax: plt.Axes,
    values: Iterable[float],
    colors: Iterable[str],
    *,
    radius: float,
    width: float | None,
):
    wedges, _ = ax.pie(
        list(values),
        radius=radius,
        startangle=START_ANGLE,
        counterclock=False,
        colors=list(colors),
        wedgeprops={"edgecolor": "white", "linewidth": 0.7, **({"width": width} if width is not None else {})},
    )
    return wedges


def save_process_legend_svg(out_path: Path, processes: Iterable[str] = LEGEND_PROCESSES) -> Path:
    labels = [str(process).strip() for process in processes if str(process).strip()]
    handles = [Patch(facecolor=PROCESS_COLORS[label], edgecolor="none", label=label) for label in labels]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig_height = max(1.2, 0.42 * len(labels))
    fig, ax = plt.subplots(figsize=(4.8, fig_height), facecolor="white")
    ax.axis("off")
    ax.legend(
        handles=handles,
        loc="center left",
        frameon=False,
        fontsize=11,
        handlelength=1.1,
        handleheight=1.1,
        labelspacing=0.9,
    )
    fig.savefig(out_path, format="svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def plot_y2020_emis_structure() -> Tuple[Path, Path]:
    summary_path = _summary_path()
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary workbook: {summary_path}")

    process_df, item_df, region_df = _build_ring_data(summary_path)
    process_colors = _build_process_colors(process_df)
    item_colors = _build_derived_colors(
        item_df,
        "Item",
        "Dominant_Process",
    )
    region_colors = _build_derived_colors(
        region_df,
        "Region",
        "Dominant_Process",
    )

    png_path, svg_path = _output_paths()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.2, 10.2), facecolor="white")

    process_labels = process_df["Process"].astype(str).tolist()
    process_color_list = [process_colors[p] for p in process_labels]
    item_color_list = [item_colors[i] for i in item_df["Item"]]
    region_color_list = [region_colors[r] for r in region_df["Region"]]

    _pie(
        ax,
        process_df["Y2020_CO2eq"],
        process_color_list,
        radius=INNER_RADIUS,
        width=None,
    )
    _pie(
        ax,
        item_df["Y2020_CO2eq"],
        item_color_list,
        radius=MIDDLE_RADIUS,
        width=MIDDLE_WIDTH,
    )
    _pie(
        ax,
        region_df["Y2020_CO2eq"],
        region_color_list,
        radius=OUTER_RADIUS,
        width=OUTER_WIDTH,
    )

    ax.set(aspect="equal")
    ax.set_xlim(-1.28, 1.28)
    ax.set_ylim(-1.28, 1.28)
    ax.axis("off")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return png_path, svg_path


def main() -> None:
    png_path, svg_path = plot_y2020_emis_structure()
    legend_path = save_process_legend_svg(_legend_path())
    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")
    print(f"[DONE] {legend_path}")


if __name__ == "__main__":
    main()
