from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config_paths import get_results_base


INPUT_NAME = "Y2020_Emis_structure_summary.xlsx"
OUTPUT_STEM = "Figure8_Emis_structure_doughnut_v2"
START_ANGLE = 90
INNER_RADIUS = 0.72
OUTER_RADIUS = 1.35
OUTER_WIDTH = 0.43
WEDGE_EDGE_LINEWIDTH = 0.45
FIG_SIZE = (9.2, 8.65)

PROCESS_ORDER = [
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
    "Enteric fermentation": "#5c509d",
    "Manure management and application": "#0868ac",
    "Rice cultivation": "#7bccc4",
    "Synthetic fertilizers": "#ccebc5",
    "Crop residue management": "#2bafd7",
    "Fish farming": "#f2edb5",
    "De/Reforestation": "#9d1748",
    "Wood harvest": "#c94f58",
    "Drained organic soils": "#e87349",
    "Savanna/Peatlands fires": "#f2b463",
}


PROCESS_LABELS = {
    "Enteric fermentation": "Enteric\nfermentation",
    "Manure management and application": "Manure",
    "Rice cultivation": "Rice",
    "Synthetic fertilizers": "Fertilizer",
    "Crop residue management": "Residues",
    "Fish farming": "Aquaculture",
    "De/Reforestation": "Deforestation",
    "Wood harvest": "Wood\nharvest",
    "Drained organic soils": "Organic\nsoils",
    "Savanna/Peatlands fires": "Fires",
}
PRODUCT_LABELS = {
    "Cattle and buffalo": "Cattle &\nbuffalo",
    "Sheep and goat": "Sheep &\ngoats",
    "Other meat and dairy": "Other Meat\n& Dairy",
    "Fruits and vegetables": "Fruits &\nveg",
    "Sugar and oil crops": "Sugar &\noil crops",
    "Other cereals": "Other cereals",
}
INNER_CALLOUT_PROCESSES = {
    "Rice cultivation",
    "Synthetic fertilizers",
    "Crop residue management",
    "Fish farming",
}


def _fig_dir() -> Path:
    return Path(get_results_base()) / "Plot" / "Fig8"


def _summary_path() -> Path:
    return _fig_dir() / INPUT_NAME


def _output_paths() -> Tuple[Path, Path]:
    fig_dir = _fig_dir()
    return fig_dir / f"{OUTPUT_STEM}.png", fig_dir / f"{OUTPUT_STEM}.svg"


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


def _ordered_frame(df: pd.DataFrame, label_col: str, order: List[str]) -> pd.DataFrame:
    order_map = {label: idx for idx, label in enumerate(order)}
    work = df.copy()
    work["_order"] = work[label_col].map(order_map)
    known = work[work["_order"].notna()].sort_values("_order", kind="mergesort")
    other = work[work["_order"].isna()].sort_values("Y2020_CO2eq", ascending=False, kind="mergesort")
    return pd.concat([known, other], ignore_index=True).drop(columns="_order")


def _sort_by_emissions(df: pd.DataFrame, label_col: str) -> pd.DataFrame:
    return (
        df.sort_values(["Y2020_CO2eq", label_col], ascending=[False, True], kind="mergesort")
        .reset_index(drop=True)
    )


def _build_plot_data(summary_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    process_df = _read_sheet(summary_path, "Process")
    item_df = _read_sheet(summary_path, "Item")
    process_item_df = _read_sheet(summary_path, "Process-Item")

    process_col = _find_col(process_df, ["Process"])
    item_col = _find_col(item_df, ["Item"])
    pi_process_col = _find_col(process_item_df, ["Process"])
    pi_item_col = _find_col(process_item_df, ["Item"])
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
        process_df["Y2020_CO2eq"].gt(0) & process_df["Process"].ne("Forest")
    ].copy()
    item_df = item_df.loc[
        item_df["Y2020_CO2eq"].gt(0)
        & ~item_df["Item"].isin({"Forestland", "Organic soils", "no"})
    ].copy()
    process_item_df = process_item_df.loc[
        process_item_df["Y2020_CO2eq"].gt(0)
        & process_item_df["Process"].ne("Forest")
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

    process_df = _ordered_frame(process_df, "Process", PROCESS_ORDER)
    item_df = _sort_by_emissions(item_df, "Item")
    return process_df.reset_index(drop=True), item_df.reset_index(drop=True)


def _process_color(process: str) -> str:
    return PROCESS_COLORS.get(str(process), "#9e9e9e")


def _product_color(dominant_process: str) -> str:
    return PROCESS_COLORS.get(str(dominant_process), "#9e9e9e")


def _hex_luminance(hex_color: str) -> float:
    text = hex_color.strip().lstrip("#")
    if len(text) != 6:
        return 1.0
    rgb = [int(text[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [val / 12.92 if val <= 0.04045 else ((val + 0.055) / 1.055) ** 2.4 for val in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _text_color(fill_color: str) -> str:
    return "white" if _hex_luminance(fill_color) < 0.34 else "black"


def _pct_text(value: float, total: float) -> str:
    pct = 100 * float(value) / float(total) if total else 0.0
    if 0 < pct < 0.5:
        return "<1%"
    return f"{pct:.0f}%"


def _mid_xy(wedge, radius: float) -> tuple[float, float, float]:
    theta = np.deg2rad((wedge.theta1 + wedge.theta2) / 2.0)
    return float(np.cos(theta) * radius), float(np.sin(theta) * radius), float(theta)


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
        wedgeprops={
            "edgecolor": "white",
            "linewidth": WEDGE_EDGE_LINEWIDTH,
            **({"width": width} if width is not None else {}),
        },
    )
    return wedges


def _adjust_side_positions(entries: List[dict], min_gap: float, y_min: float, y_max: float) -> None:
    entries.sort(key=lambda item: item["y"])
    for idx in range(1, len(entries)):
        entries[idx]["y"] = max(entries[idx]["y"], entries[idx - 1]["y"] + min_gap)
    if entries and entries[-1]["y"] > y_max:
        shift = entries[-1]["y"] - y_max
        for entry in entries:
            entry["y"] -= shift
    for idx in range(len(entries) - 2, -1, -1):
        entries[idx]["y"] = min(entries[idx]["y"], entries[idx + 1]["y"] - min_gap)
    if entries and entries[0]["y"] < y_min:
        shift = y_min - entries[0]["y"]
        for entry in entries:
            entry["y"] += shift


def _draw_callouts(
    ax: plt.Axes,
    entries: List[dict],
    *,
    start_radius: float,
    text_radius: float,
    fontsize: float,
    min_gap: float,
    y_bounds: tuple[float, float],
) -> None:
    if not entries:
        return

    prepared: List[dict] = []
    for entry in entries:
        theta = entry["theta"]
        side = 1 if np.cos(theta) >= 0 else -1
        prepared.append(
            {
                **entry,
                "side": side,
                "x": side * text_radius,
                "y": float(np.sin(theta) * text_radius),
                "ha": "left" if side > 0 else "right",
            }
        )

    for side in (-1, 1):
        side_entries = [entry for entry in prepared if entry["side"] == side]
        _adjust_side_positions(side_entries, min_gap, y_bounds[0], y_bounds[1])
        for entry in side_entries:
            xy = (np.cos(entry["theta"]) * start_radius, np.sin(entry["theta"]) * start_radius)
            ax.annotate(
                entry["text"],
                xy=xy,
                xytext=(entry["x"], entry["y"]),
                ha=entry["ha"],
                va="center",
                fontsize=fontsize,
                color="black",
                arrowprops={
                    "arrowstyle": "-",
                    "color": "black",
                    "linewidth": 1.2,
                    "shrinkA": 0,
                    "shrinkB": 0,
                    "connectionstyle": "arc3,rad=0.0",
                },
            )


def _label_inner_sources(ax: plt.Axes, wedges, process_df: pd.DataFrame) -> None:
    total = float(process_df["Y2020_CO2eq"].sum())
    callouts: List[dict] = []
    for wedge, row in zip(wedges, process_df.itertuples(index=False)):
        process = str(row.Process)
        value = float(row.Y2020_CO2eq)
        pct = 100 * value / total if total else 0
        label = PROCESS_LABELS.get(process, process)
        text = f"{label}\n{_pct_text(value, total)}"
        color = _process_color(process)
        x, y, theta = _mid_xy(wedge, INNER_RADIUS * 0.55)

        if process == "Savanna/Peatlands fires":
            xy = (np.cos(theta) * INNER_RADIUS * 0.92, np.sin(theta) * INNER_RADIUS * 0.92)
            ax.annotate(
                text.replace("\n", ", ", 1),
                xy=xy,
                xytext=(-0.2, 0.88),
                ha="center",
                va="center",
                fontsize=12.5,
                color="black",
                arrowprops={
                    "arrowstyle": "-",
                    "color": "black",
                    "linewidth": 1.2,
                    "shrinkA": 0,
                    "shrinkB": 0,
                },
            )
            continue

        if process in INNER_CALLOUT_PROCESSES or pct < 3.2:
            callouts.append({"theta": theta, "text": text.replace("\n", ", ", 1)})
            continue

        ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=15 if pct >= 7 else 12,
            color=_text_color(color),
            linespacing=0.92,
        )

    _draw_callouts(
        ax,
        callouts,
        start_radius=INNER_RADIUS * 0.92,
        text_radius=1.03,
        fontsize=12.5,
        min_gap=0.09,
        y_bounds=(-0.55, 0.55),
    )


def _product_label(item: str) -> str:
    return PRODUCT_LABELS.get(str(item), str(item))


def _label_outer_products(ax: plt.Axes, wedges, item_df: pd.DataFrame) -> None:
    total = float(item_df["Y2020_CO2eq"].sum())
    callouts: List[dict] = []
    label_radius = OUTER_RADIUS - OUTER_WIDTH * 0.52
    for wedge, row in zip(wedges, item_df.itertuples(index=False)):
        item = str(row.Item)
        value = float(row.Y2020_CO2eq)
        pct = 100 * value / total if total else 0
        label = _product_label(item)
        text = f"{label}\n{_pct_text(value, total)}"
        color = _product_color(row.Dominant_Process)
        x, y, theta = _mid_xy(wedge, label_radius)

        if pct < 3.4:
            callouts.append({"theta": theta, "text": text.replace("\n", " ")})
            continue

        ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=13.5 if pct >= 7 else 11.5,
            color=_text_color(color),
            linespacing=0.95,
        )

    _draw_callouts(
        ax,
        callouts,
        start_radius=OUTER_RADIUS,
        text_radius=1.55,
        fontsize=11.5,
        min_gap=0.12,
        y_bounds=(-1.23, 1.28),
    )


def _add_group_arrows(ax: plt.Axes) -> None:
    box = {"boxstyle": "square,pad=0.08", "facecolor": "#f7cfd0", "edgecolor": "none", "alpha": 0.9}
    ax.annotate(
        "Land\nmanagement",
        xy=(0.06, 0.73),
        xytext=(0.48, 0.78),
        ha="center",
        va="center",
        fontsize=15.5,
        color="#5e52a2",
        rotation=-16,
        bbox=box,
        arrowprops={"arrowstyle": "-|>", "color": "black", "linewidth": 2.0},
    )
    ax.annotate(
        "Land-use\nchange",
        xy=(0.57, -0.73),
        xytext=(0.30, -0.87),
        ha="center",
        va="center",
        fontsize=15.5,
        color="#9d1748",
        rotation=24,
        bbox=box,
        arrowprops={"arrowstyle": "-|>", "color": "black", "linewidth": 2.0},
    )


def plot_y2020_emis_structure_v2() -> Tuple[Path, Path]:
    summary_path = _summary_path()
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary workbook: {summary_path}")

    process_df, item_df = _build_plot_data(summary_path)
    png_path, svg_path = _output_paths()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=FIG_SIZE, facecolor="white")

    process_colors = [_process_color(process) for process in process_df["Process"]]
    item_colors = [_product_color(process) for process in item_df["Dominant_Process"]]

    process_wedges = _pie(
        ax,
        process_df["Y2020_CO2eq"],
        process_colors,
        radius=INNER_RADIUS,
        width=None,
    )
    item_wedges = _pie(
        ax,
        item_df["Y2020_CO2eq"],
        item_colors,
        radius=OUTER_RADIUS,
        width=OUTER_WIDTH,
    )

    _label_inner_sources(ax, process_wedges, process_df)
    _label_outer_products(ax, item_wedges, item_df)
    _add_group_arrows(ax)

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


def main() -> None:
    png_path, svg_path = plot_y2020_emis_structure_v2()
    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


if __name__ == "__main__":
    main()
