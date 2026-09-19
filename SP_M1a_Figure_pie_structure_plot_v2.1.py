from __future__ import annotations

from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import SP_M1a_Figure_pie_structure_plot_v2 as base


INPUT_NAME = "Y2020_Emis_structure_summary_v2.xlsx"
OUTPUT_STEM = "Figure8_Emis_structure_doughnut_v2_1"
NET_FOREST_PROCESS = "Net forest conversion flux"
LEGACY_FOREST_PROCESSES = {"De/Reforestation", "Forest"}

PROCESS_ORDER = [
    "Enteric fermentation",
    "Manure management and application",
    "Rice cultivation",
    "Synthetic fertilizers",
    "Crop residue management",
    "Fish farming",
    NET_FOREST_PROCESS,
    "Wood harvest",
    "Drained organic soils",
    "Savanna/Peatlands fires",
]
PROCESS_COLORS = {
    **base.PROCESS_COLORS,
    NET_FOREST_PROCESS: base.PROCESS_COLORS.get("De/Reforestation", "#9d1748"),
}
PROCESS_LABELS = {
    **base.PROCESS_LABELS,
    NET_FOREST_PROCESS: "Net forest\nconversion\nflux",
}
INNER_SEPARATOR_AFTER_PROCESSES = {
    "Fish farming",
}
INNER_SEPARATOR_COLOR = "black"
INNER_SEPARATOR_LINEWIDTH = 2.1
INNER_SEPARATOR_RADIUS = base.INNER_RADIUS


base.INPUT_NAME = INPUT_NAME
base.OUTPUT_STEM = OUTPUT_STEM
base.PROCESS_ORDER = PROCESS_ORDER
base.PROCESS_COLORS = PROCESS_COLORS
base.PROCESS_LABELS = PROCESS_LABELS


def _build_plot_data(summary_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    process_df = base._read_sheet(summary_path, "Process")
    item_df = base._read_sheet(summary_path, "Item")
    process_item_df = base._read_sheet(summary_path, "Process-Item")

    process_col = base._find_col(process_df, ["Process"])
    item_col = base._find_col(item_df, ["Item"])
    pi_process_col = base._find_col(process_item_df, ["Process"])
    pi_item_col = base._find_col(process_item_df, ["Item"])
    process_df = process_df.rename(columns={process_col: "Process"})
    item_df = item_df.rename(columns={item_col: "Item"})
    process_item_df = process_item_df.rename(
        columns={pi_process_col: "Process", pi_item_col: "Item"}
    )

    for frame in (process_df, item_df, process_item_df):
        frame["Y2020_CO2eq"] = pd.to_numeric(frame["Y2020_CO2eq"], errors="coerce")
        frame.dropna(subset=["Y2020_CO2eq"], inplace=True)

    process_df["Process"] = process_df["Process"].astype("string").str.strip()
    item_df["Item"] = item_df["Item"].astype("string").str.strip()
    process_item_df["Process"] = process_item_df["Process"].astype("string").str.strip()
    process_item_df["Item"] = process_item_df["Item"].astype("string").str.strip()
    process_df = process_df.loc[
        process_df["Y2020_CO2eq"].gt(0)
        & ~process_df["Process"].isin(LEGACY_FOREST_PROCESSES)
    ].copy()
    item_df = item_df.loc[
        item_df["Y2020_CO2eq"].gt(0)
        & ~item_df["Item"].isin({"Forestland", "Organic soils", "no"})
    ].copy()
    process_item_df = process_item_df.loc[
        process_item_df["Y2020_CO2eq"].gt(0)
        & ~process_item_df["Process"].isin(LEGACY_FOREST_PROCESSES)
        & ~process_item_df["Item"].isin({"Forestland", "Organic soils", "no"})
    ].copy()

    dominant_process = (
        process_item_df.sort_values(
            ["Item", "Y2020_CO2eq"],
            ascending=[True, False],
            kind="mergesort",
        )
        .drop_duplicates("Item", keep="first")
        .set_index("Item")["Process"]
    )
    item_df["Dominant_Process"] = item_df["Item"].map(dominant_process)

    process_df = base._ordered_frame(process_df, "Process", PROCESS_ORDER)
    item_df = base._sort_by_emissions(item_df, "Item")
    return process_df.reset_index(drop=True), item_df.reset_index(drop=True)


base._build_plot_data = _build_plot_data


def _separator_angle_after(process_df: pd.DataFrame, process_name: str) -> float | None:
    total = float(process_df["Y2020_CO2eq"].sum())
    if total <= 0:
        return None
    cumulative = 0.0
    for row in process_df.itertuples(index=False):
        cumulative += float(row.Y2020_CO2eq)
        if str(row.Process) == process_name:
            return float(base.START_ANGLE - 360.0 * cumulative / total)
    return None


def _draw_inner_separator_line(ax: plt.Axes, angle_deg: float) -> None:
    theta = np.deg2rad(angle_deg)
    ax.plot(
        [0.0, np.cos(theta) * INNER_SEPARATOR_RADIUS],
        [0.0, np.sin(theta) * INNER_SEPARATOR_RADIUS],
        color=INNER_SEPARATOR_COLOR,
        linewidth=INNER_SEPARATOR_LINEWIDTH,
        solid_capstyle="butt",
        zorder=2.5,
    )


def _add_inner_separator_lines(ax: plt.Axes, process_df: pd.DataFrame) -> None:
    _draw_inner_separator_line(ax, float(base.START_ANGLE))
    for process_name in INNER_SEPARATOR_AFTER_PROCESSES:
        angle = _separator_angle_after(process_df, process_name)
        if angle is not None:
            _draw_inner_separator_line(ax, angle)


def plot_y2020_emis_structure_v2_1() -> Tuple[Path, Path]:
    summary_path = base._summary_path()
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary workbook: {summary_path}")

    process_df, item_df = _build_plot_data(summary_path)
    png_path, svg_path = base._output_paths()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=base.FIG_SIZE, facecolor="white")

    process_colors = [base._process_color(process) for process in process_df["Process"]]
    item_colors = [base._product_color(process) for process in item_df["Dominant_Process"]]

    process_wedges = base._pie(
        ax,
        process_df["Y2020_CO2eq"],
        process_colors,
        radius=base.INNER_RADIUS,
        width=None,
    )
    item_wedges = base._pie(
        ax,
        item_df["Y2020_CO2eq"],
        item_colors,
        radius=base.OUTER_RADIUS,
        width=base.OUTER_WIDTH,
    )

    _add_inner_separator_lines(ax, process_df)
    base._label_inner_sources(ax, process_wedges, process_df)
    base._label_outer_products(ax, item_wedges, item_df)
    base._add_group_arrows(ax)

    ax.text(-1.58, 0.82, "a", ha="left", va="center", fontsize=30, fontweight="bold")

    ax.set(aspect="equal")
    ax.set_xlim(-1.80, 1.90)
    ax.set_ylim(-1.56, 1.56)
    ax.axis("off")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png_path, svg_path


base.plot_y2020_emis_structure_v2 = plot_y2020_emis_structure_v2_1


def main() -> None:
    png_path, svg_path = plot_y2020_emis_structure_v2_1()
    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


if __name__ == "__main__":
    main()
