from __future__ import annotations

from pathlib import Path
import textwrap
from typing import Dict, Iterable, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

from config_paths import get_results_base
from SP1_8_2_Figure_pie_structure_plot import LUC_PROCESSES, PROCESS_COLORS


INPUT_NAME = "Y2020_Emis_structure_summary.xlsx"
OUTPUT_STEM = "Figure8_Emis_structure_bar2"
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


def _wrap_label(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(str(text), width=width, break_long_words=False))


def _process_panel(summary_path: Path) -> tuple[pd.DataFrame, Dict[str, str], int]:
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
    forest_df = forest_df.sort_values("Y2020_CO2eq", ascending=True, kind="mergesort")

    panel = pd.concat([ag_df, luc_df, forest_df], ignore_index=True)
    colors = {label: PROCESS_COLORS.get(proc, DEFAULT_COLOR) for label, proc in zip(panel["Label"], panel["Dominant_Process"])}
    return panel, colors, len(ag_df)


def _item_panel(summary_path: Path) -> tuple[pd.DataFrame, Dict[str, str], int]:
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
    luc_neg_df = luc_neg_df.sort_values("Y2020_CO2eq", ascending=True, kind="mergesort")

    other_neg_df = item_df[(~item_df["Label"].isin(LUC_ITEMS)) & (item_df["Y2020_CO2eq"] < 0)].copy()
    other_neg_df = other_neg_df.sort_values("Y2020_CO2eq", ascending=True, kind="mergesort")

    panel = pd.concat([ag_df, luc_pos_df, luc_neg_df, other_neg_df], ignore_index=True)
    colors = {
        label: PROCESS_COLORS.get(str(proc).strip(), DEFAULT_COLOR)
        for label, proc in zip(panel["Label"], panel["Dominant_Process"])
    }
    return panel, colors, len(ag_df)


def _country_panel(summary_path: Path) -> tuple[pd.DataFrame, Dict[str, str]]:
    country_df = _read_sheet(summary_path, "Country").copy()
    region_col = _find_col(country_df, ["Region", "Country"])
    country_df = country_df.rename(columns={region_col: "Label"})
    country_df["Y2020_CO2eq"] = pd.to_numeric(country_df["Y2020_CO2eq"], errors="coerce")
    country_df = country_df.dropna(subset=["Y2020_CO2eq"]).copy()
    country_df = country_df[country_df["Y2020_CO2eq"] != 0].sort_values("Y2020_CO2eq", ascending=True, kind="mergesort")

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

    colors = {
        label: PROCESS_COLORS.get(str(proc).strip(), DEFAULT_COLOR)
        for label, proc in zip(country_df["Label"], country_df["Dominant_Process"])
    }
    return country_df.reset_index(drop=True), colors


def _plot_panel(
    ax: plt.Axes,
    df: pd.DataFrame,
    *,
    color_map: Dict[str, str],
    title: str,
    wrap_width: int,
    separator_after: int | None = None,
) -> None:
    values_mt = df["Y2020_CO2eq"] / 1e6
    labels = [_wrap_label(label, wrap_width) for label in df["Label"].astype(str)]
    colors = [color_map.get(str(label), DEFAULT_COLOR) for label in df["Label"].astype(str)]
    y = range(len(df))

    ax.barh(y, values_mt, color=colors, edgecolor="white", linewidth=0.9)
    ax.set_yticks(list(y), labels=labels)
    ax.invert_yaxis()
    ax.axvline(0, color="#444444", linewidth=1.0)
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, fontsize=12.5, fontweight="bold", pad=8)
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=8.8, length=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    if separator_after is not None and 0 < separator_after < len(df):
        ax.axhline(separator_after - 0.5, color="#9a9a9a", linewidth=0.9)


def plot_y2020_emis_structure_bar2() -> Tuple[Path, Path]:
    summary_path = _summary_path()
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary workbook: {summary_path}")

    process_df, process_colors, process_ag_count = _process_panel(summary_path)
    item_df, item_colors, item_ag_count = _item_panel(summary_path)
    country_df, country_colors = _country_panel(summary_path)

    png_path, svg_path = _output_paths()
    png_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(15.8, 9.4),
        sharex=True,
        gridspec_kw={"width_ratios": [1.0, 1.0, 1.0]},
        facecolor="white",
    )

    _plot_panel(
        axes[0],
        process_df,
        color_map=process_colors,
        title="Process",
        wrap_width=18,
        separator_after=process_ag_count,
    )
    _plot_panel(
        axes[1],
        item_df,
        color_map=item_colors,
        title="Item",
        wrap_width=18,
        separator_after=item_ag_count,
    )
    _plot_panel(
        axes[2],
        country_df,
        color_map=country_colors,
        title="Country",
        wrap_width=22,
    )

    global_min = min(
        float(process_df["Y2020_CO2eq"].min()),
        float(item_df["Y2020_CO2eq"].min()),
        float(country_df["Y2020_CO2eq"].min()),
        0.0,
    ) / 1e6
    global_max = max(
        float(process_df["Y2020_CO2eq"].max()),
        float(item_df["Y2020_CO2eq"].max()),
        float(country_df["Y2020_CO2eq"].max()),
        0.0,
    ) / 1e6
    span = global_max - global_min
    pad = 0.08 * span if span > 0 else 0.5
    xlim = (global_min - pad, global_max + pad)

    for ax in axes:
        ax.set_xlim(*xlim)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.set_xlabel("Mt CO$_2$eq", fontsize=10)

    fig.subplots_adjust(left=0.07, right=0.985, top=0.94, bottom=0.08, wspace=0.12)
    fig.savefig(png_path, dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return png_path, svg_path


def main() -> None:
    png_path, svg_path = plot_y2020_emis_structure_bar2()
    print(f"[DONE] {png_path}")
    print(f"[DONE] {svg_path}")


if __name__ == "__main__":
    main()
