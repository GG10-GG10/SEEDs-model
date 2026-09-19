from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from config_paths import get_results_base
from SP1_8_2_Figure_pie_structure_plot import LUC_PROCESSES, PROCESS_COLORS


INPUT_NAME = "Y2020_Emis_structure_summary.xlsx"
OUTPUT_STEM = "Figure8_Emis_structure_bar"
DEFAULT_COLOR = "#bdbdbd"
LUC_ITEMS = {"Roundwood", "Fires", "Organic soils", "Forestland"}


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


def _load_process_df(summary_path: Path) -> pd.DataFrame:
    df = _read_sheet(summary_path, "Process").copy()
    process_col = _find_col(df, ["Process"])
    df = df.rename(columns={process_col: "Label"})
    df["Y2020_CO2eq"] = pd.to_numeric(df["Y2020_CO2eq"], errors="coerce")
    df = df.dropna(subset=["Y2020_CO2eq"]).copy()

    ag_df = df[(~df["Label"].isin(LUC_PROCESSES)) & (df["Label"] != "Forest") & (df["Y2020_CO2eq"] > 0)].copy()
    ag_df["Dominant_Process"] = ag_df["Label"]
    ag_df = ag_df.sort_values("Y2020_CO2eq", ascending=True, kind="mergesort")

    luc_df = df[df["Label"].isin(LUC_PROCESSES) & (df["Y2020_CO2eq"] > 0)].copy()
    luc_df["Dominant_Process"] = luc_df["Label"]
    luc_df = luc_df.sort_values("Y2020_CO2eq", ascending=True, kind="mergesort")

    forest_df = df[df["Label"] == "Forest"].copy()
    forest_df["Dominant_Process"] = "Forest"
    forest_df = forest_df.sort_values("Y2020_CO2eq", ascending=False, kind="mergesort")

    return pd.concat([ag_df, luc_df, forest_df], ignore_index=True)


def _load_item_df(summary_path: Path) -> pd.DataFrame:
    item_df = _read_sheet(summary_path, "Item").copy()
    item_col = _find_col(item_df, ["Item"])
    item_df = item_df.rename(columns={item_col: "Label"})
    item_df["Y2020_CO2eq"] = pd.to_numeric(item_df["Y2020_CO2eq"], errors="coerce")
    item_df = item_df.dropna(subset=["Y2020_CO2eq"]).copy()
    item_df = item_df[item_df["Y2020_CO2eq"] != 0].copy()

    proc_item_df = _read_sheet(summary_path, "Process-Item").copy()
    proc_col = _find_col(proc_item_df, ["Process"])
    pi_item_col = _find_col(proc_item_df, ["Item"])
    proc_item_df = proc_item_df.rename(columns={proc_col: "Process", pi_item_col: "Label"})
    proc_item_df["Y2020_CO2eq"] = pd.to_numeric(proc_item_df["Y2020_CO2eq"], errors="coerce")
    proc_item_df = proc_item_df.dropna(subset=["Y2020_CO2eq"]).copy()

    dominant_item = (
        proc_item_df.assign(abs_emis=proc_item_df["Y2020_CO2eq"].abs())
        .sort_values(["Label", "abs_emis"], ascending=[True, False], kind="mergesort")
        .drop_duplicates(subset=["Label"], keep="first")
        .set_index("Label")["Process"]
        .to_dict()
    )

    item_df["Dominant_Process"] = item_df["Label"].map(dominant_item).fillna("")

    ag_df = item_df[(~item_df["Label"].isin(LUC_ITEMS)) & (item_df["Y2020_CO2eq"] > 0)].copy()
    ag_df = ag_df.sort_values("Y2020_CO2eq", ascending=True, kind="mergesort")

    luc_pos_df = item_df[item_df["Label"].isin(LUC_ITEMS) & (item_df["Y2020_CO2eq"] > 0)].copy()
    luc_pos_df = luc_pos_df.sort_values("Y2020_CO2eq", ascending=True, kind="mergesort")

    luc_neg_df = item_df[item_df["Label"].isin(LUC_ITEMS) & (item_df["Y2020_CO2eq"] < 0)].copy()
    luc_neg_df = luc_neg_df.sort_values("Y2020_CO2eq", ascending=False, kind="mergesort")

    other_neg_df = item_df[(~item_df["Label"].isin(LUC_ITEMS)) & (item_df["Y2020_CO2eq"] < 0)].copy()
    other_neg_df = other_neg_df.sort_values("Y2020_CO2eq", ascending=False, kind="mergesort")

    return pd.concat([ag_df, luc_pos_df, luc_neg_df, other_neg_df], ignore_index=True)


def _load_country_df(summary_path: Path) -> pd.DataFrame:
    country_df = _read_sheet(summary_path, "Country").copy()
    region_col = _find_col(country_df, ["Region", "Country"])
    country_df = country_df.rename(columns={region_col: "Label"})
    country_df["Y2020_CO2eq"] = pd.to_numeric(country_df["Y2020_CO2eq"], errors="coerce")
    country_df = country_df.dropna(subset=["Y2020_CO2eq"]).copy()
    country_df = country_df[country_df["Y2020_CO2eq"] != 0].copy()

    proc_country_df = _read_sheet(summary_path, "Process-Country").copy()
    proc_col = _find_col(proc_country_df, ["Process"])
    pc_region_col = _find_col(proc_country_df, ["Region", "Country"])
    proc_country_df = proc_country_df.rename(columns={proc_col: "Process", pc_region_col: "Label"})
    proc_country_df["Y2020_CO2eq"] = pd.to_numeric(proc_country_df["Y2020_CO2eq"], errors="coerce")
    proc_country_df = proc_country_df.dropna(subset=["Y2020_CO2eq"]).copy()

    dominant_country = (
        proc_country_df[proc_country_df["Process"] != "Forest"]
        .sort_values(["Label", "Y2020_CO2eq"], ascending=[True, False], kind="mergesort")
        .drop_duplicates(subset=["Label"], keep="first")
        .set_index("Label")["Process"]
        .to_dict()
    )

    country_df["Dominant_Process"] = country_df["Label"].map(dominant_country).fillna("")
    return country_df.sort_values("Y2020_CO2eq", ascending=True, kind="mergesort").reset_index(drop=True)


def _stack_segments(
    ax: plt.Axes,
    x: float,
    df: pd.DataFrame,
    *,
    color_col: str,
    width: float,
) -> tuple[float, float]:
    pos_df = df[df["Y2020_CO2eq"] > 0].copy()
    neg_df = df[df["Y2020_CO2eq"] < 0].copy()

    pos_bottom = 0.0
    for _, row in pos_df.iloc[::-1].iterrows():
        value_mt = float(row["Y2020_CO2eq"]) / 1e6
        color = PROCESS_COLORS.get(str(row[color_col]).strip(), DEFAULT_COLOR)
        ax.bar(x, value_mt, width=width, bottom=pos_bottom, color=color, edgecolor="white", linewidth=1.0)
        pos_bottom += value_mt

    neg_bottom = 0.0
    for _, row in neg_df.sort_values("Y2020_CO2eq", ascending=False, kind="mergesort").iterrows():
        value_mt = float(row["Y2020_CO2eq"]) / 1e6
        color = PROCESS_COLORS.get(str(row[color_col]).strip(), DEFAULT_COLOR)
        ax.bar(x, value_mt, width=width, bottom=neg_bottom, color=color, edgecolor="white", linewidth=1.0)
        neg_bottom += value_mt

    return pos_bottom, neg_bottom


def plot_y2020_emis_structure_bar() -> Tuple[Path, Path]:
    summary_path = _summary_path()
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary workbook: {summary_path}")

    process_df = _load_process_df(summary_path)
    item_df = _load_item_df(summary_path)
    country_df = _load_country_df(summary_path)

    png_path, svg_path = _output_paths()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.4, 9.2), facecolor="white")
    bar_width = 0.56
    x_positions = [0.0, 1.25, 2.50]

    max_pos = 0.0
    min_neg = 0.0
    for x, df in zip(x_positions, [process_df, item_df, country_df]):
        pos_total, neg_total = _stack_segments(ax, x, df, color_col="Dominant_Process", width=bar_width)
        max_pos = max(max_pos, pos_total)
        min_neg = min(min_neg, neg_total)

    ax.axhline(0, color="#444444", linewidth=1.0)
    ax.set_xticks(x_positions, ["Process", "Item", "Country"])
    ax.tick_params(axis="x", labelsize=11)
    ax.tick_params(axis="y", labelsize=10)
    ax.set_ylabel("Mt CO$_2$eq", fontsize=11)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0f}" if abs(y) >= 1 else f"{y:.1f}"))
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    span = max_pos - min_neg
    pad = 0.08 * span if span > 0 else 0.5
    ax.set_ylim(min_neg - pad, max_pos + pad)
    ax.set_xlim(-0.65, 3.15)

    fig.subplots_adjust(left=0.11, right=0.98, top=0.98, bottom=0.09)
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return png_path, svg_path


def main() -> None:
    png_path, svg_path = plot_y2020_emis_structure_bar()
    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


if __name__ == "__main__":
    main()
