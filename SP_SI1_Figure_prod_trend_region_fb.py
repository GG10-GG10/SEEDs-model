from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from config_paths import get_results_base, get_src_base

DEFAULT_SCENARIO = "BASE"
PLOT_YEARS = [2020, 2030, 2040, 2050, 2060, 2070, 2080]
EMIS_MAP_LOOKUP_COLUMNS = [
    "Item_Production_Map",
    "Item_Emis",
    "Item_Stock_Map",
    "Item_Slaughtered_Map",
    "Item_Trade_Map",
]
NON_FOOD_EMIS_SUM_CATEGORIES = {"Roundwood", "Fires", "Forestland", "Organic soils", "no"}

REGION_ORDER = [
    "Europe and Russia",
    "Central Asia",
    "North America",
    "Middle East",
    "Sub-Saharan Africa",
    "Southeast Asia",
    "Latin America",
    "East Asia",
    "South Asia",
    "Oceania",
    "Other",
]

REGION_COLORS: Dict[str, str] = {
    "Europe and Russia": "#7C63A8",
    "Central Asia": "#BBB3DD",
    "North America": "#F07F24",
    "Middle East": "#F6C58A",
    "Sub-Saharan Africa": "#F3A5A2",
    "Southeast Asia": "#56A89A",
    "Latin America": "#8DCE8B",
    "East Asia": "#2B67AE",
    "South Asia": "#69ABD9",
    "Oceania": "#B7D8EC",
    "Other": "#CFCFCF",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot production trends by Region_FB from production_summary.csv."
    )
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO, help="Scenario name under output/<scenario>/DS.")
    parser.add_argument(
        "--production-file",
        type=Path,
        default=None,
        help="Optional path to production_summary.csv. Overrides --scenario.",
    )
    parser.add_argument(
        "--dict-path",
        type=Path,
        default=Path(get_src_base()) / "dict_v3.xlsx",
        help="Path to dict_v3.xlsx.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(get_results_base()) / "Plot" / "other_plot" / "Prod_trend",
        help="Directory for plot outputs.",
    )
    return parser.parse_args()


def _norm_m49(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    code = str(value).strip()
    if not code or code.lower() == "nan":
        return None
    code = code.lstrip("'").strip()
    if not code:
        return None
    return code.zfill(3)


def _build_region_fb_map(dict_path: Path) -> Dict[str, str]:
    region_df = pd.read_excel(dict_path, sheet_name="region", usecols=["M49_Country_Code", "Region_FB"])
    region_df["m49_norm"] = region_df["M49_Country_Code"].map(_norm_m49)
    region_df["Region_FB"] = region_df["Region_FB"].fillna("Other").astype(str).str.strip()
    region_df.loc[region_df["Region_FB"].eq("no"), "Region_FB"] = "Other"
    region_df = region_df.dropna(subset=["m49_norm"]).drop_duplicates(subset=["m49_norm"], keep="first")
    return dict(zip(region_df["m49_norm"], region_df["Region_FB"]))


def _build_emis_sum_mapping(dict_path: Path) -> tuple[Dict[str, str], List[str]]:
    usecols = EMIS_MAP_LOOKUP_COLUMNS + ["Item_EmisSum_map"]
    emis_df = pd.read_excel(dict_path, sheet_name="Emis_item", usecols=usecols)

    for col in usecols:
        emis_df[col] = emis_df[col].fillna("").astype(str).str.strip()

    category_order: List[str] = []
    for category in emis_df["Item_EmisSum_map"]:
        if not category or category in NON_FOOD_EMIS_SUM_CATEGORIES:
            continue
        if category not in category_order:
            category_order.append(category)

    raw_mapping: Dict[str, set[str]] = {}
    for lookup_col in EMIS_MAP_LOOKUP_COLUMNS:
        pairs = emis_df[[lookup_col, "Item_EmisSum_map"]].copy()
        pairs = pairs[(pairs[lookup_col] != "") & (pairs["Item_EmisSum_map"] != "")]
        pairs = pairs[~pairs["Item_EmisSum_map"].isin(NON_FOOD_EMIS_SUM_CATEGORIES)]
        pairs = pairs.drop_duplicates()
        for commodity, category in pairs.itertuples(index=False):
            raw_mapping.setdefault(commodity, set()).add(category)

    conflicts = {commodity: sorted(categories) for commodity, categories in raw_mapping.items() if len(categories) > 1}
    if conflicts:
        raise ValueError(f"Ambiguous Item_EmisSum_map mapping found: {conflicts}")

    mapping = {commodity: next(iter(categories)) for commodity, categories in raw_mapping.items()}
    return mapping, category_order


def _load_production_summary(production_file: Path, dict_path: Path) -> tuple[pd.DataFrame, List[str]]:
    if not production_file.exists():
        raise FileNotFoundError(f"production summary not found: {production_file}")
    if not dict_path.exists():
        raise FileNotFoundError(f"dict_v3.xlsx not found: {dict_path}")

    region_fb_map = _build_region_fb_map(dict_path)
    category_map, category_order = _build_emis_sum_mapping(dict_path)

    df = pd.read_csv(
        production_file,
        usecols=["M49_Country_Code", "year", "commodity", "production_t"],
        low_memory=False,
    )
    df["m49_norm"] = df["M49_Country_Code"].map(_norm_m49)
    df["Region_FB"] = df["m49_norm"].map(region_fb_map).fillna("Other")
    df["commodity"] = df["commodity"].astype(str).str.strip()
    df["category"] = df["commodity"].map(category_map)
    df = df[df["category"].notna()].copy()
    df = df[df["year"].isin(PLOT_YEARS)].copy()
    df["production_kt"] = pd.to_numeric(df["production_t"], errors="coerce").fillna(0.0) / 1000.0

    grouped = (
        df.groupby(["category", "Region_FB", "year"], as_index=False)["production_kt"]
        .sum()
        .sort_values(["category", "year", "Region_FB"])
    )
    present_categories = set(grouped["category"].dropna().astype(str))
    ordered_categories = [category for category in category_order if category in present_categories]
    extras = sorted(present_categories - set(ordered_categories))
    return grouped, ordered_categories + extras


def _present_regions(df: pd.DataFrame) -> List[str]:
    present = set(df["Region_FB"].dropna().astype(str))
    ordered = [region for region in REGION_ORDER if region in present]
    extras = sorted(present - set(ordered))
    return ordered + extras


def _subplot_grid(category_count: int) -> tuple[int, int]:
    ncols = min(4, max(1, category_count))
    nrows = int(np.ceil(category_count / ncols))
    return nrows, ncols


def _format_axes(ax: plt.Axes, years: Iterable[int], title: str) -> None:
    ax.set_title(title, loc="left", fontsize=18, fontweight="bold", pad=2)
    ax.set_xticks(range(len(PLOT_YEARS)))
    ax.set_xticklabels([str(y) for y in years], fontsize=9)
    ax.tick_params(axis="y", labelsize=9, length=0)
    ax.tick_params(axis="x", length=0)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True, min_n_ticks=3))
    ax.set_xlim(-0.55, len(PLOT_YEARS) - 0.45)
    ax.grid(False)
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_linewidth(0.9)
        spine.set_color("#7A7A7A")


def plot_prod_trend_region_fb(
    production_file: Path,
    dict_path: Path,
    output_dir: Path,
    scenario_name: str,
) -> List[Path]:
    grouped, categories = _load_production_summary(production_file, dict_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    regions = _present_regions(grouped)
    colors = {region: REGION_COLORS.get(region, REGION_COLORS["Other"]) for region in regions}

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    nrows, ncols = _subplot_grid(len(categories))
    fig, axes = plt.subplots(nrows, ncols, figsize=(15.2, max(3.0 * nrows - 0.3, 3.0)))
    axes_flat = np.atleast_1d(axes).flatten()
    x = np.arange(len(PLOT_YEARS))

    for ax, category in zip(axes_flat, categories):
        panel = grouped[grouped["category"] == category]
        pivot = (
            panel.pivot_table(index="year", columns="Region_FB", values="production_kt", aggfunc="sum")
            .reindex(PLOT_YEARS)
            .fillna(0.0)
        )
        bottom = np.zeros(len(PLOT_YEARS), dtype=float)
        for region in regions:
            values = pivot[region].to_numpy() if region in pivot.columns else np.zeros(len(PLOT_YEARS), dtype=float)
            if not np.any(values):
                continue
            ax.bar(
                x,
                values,
                width=0.78,
                bottom=bottom,
                color=colors[region],
                edgecolor="white",
                linewidth=0.35,
            )
            bottom += values
        _format_axes(ax, PLOT_YEARS, category)

    for ax in axes_flat[len(categories) :]:
        ax.axis("off")

    handles = [Patch(facecolor=colors[region], edgecolor="white", label=region) for region in regions]
    fig.legend(
        handles=handles,
        loc="center left",
        bbox_to_anchor=(0.835, 0.5),
        frameon=False,
        fontsize=11,
        handlelength=1.9,
        handleheight=1.0,
    )
    fig.subplots_adjust(left=0.055, right=0.81, top=0.965, bottom=0.08, wspace=0.26, hspace=0.28)

    base_name = f"{scenario_name}_prod_trend_region_fb"
    png_path = output_dir / f"{base_name}.png"
    svg_path = output_dir / f"{base_name}.svg"
    agg_path = output_dir / f"{base_name}_agg.csv"

    grouped.to_csv(agg_path, index=False, encoding="utf-8-sig")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    return [png_path, svg_path, agg_path]


def main() -> None:
    args = _parse_args()
    production_file = args.production_file
    if production_file is None:
        production_file = Path(get_results_base(args.scenario)) / "DS" / "production_summary.csv"

    outputs = plot_prod_trend_region_fb(
        production_file=production_file,
        dict_path=args.dict_path,
        output_dir=args.output_dir,
        scenario_name=args.scenario,
    )
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
