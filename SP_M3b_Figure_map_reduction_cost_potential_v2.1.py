# -*- coding: utf-8 -*-
"""
Legacy compatibility plotter for process-dominance maps.
Reads: output/Plot/Fig3/Figure3.xlsx (sheet: map)
Outputs: PNG maps + a separate SVG legend in the same folder.

For current Figure 3d results use
``SP_M3d_Figure_country_dominant_mitigation_intervention.py``.  Missing
countries are no longer assigned to ``Improve yield rate`` by default.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.axes import Axes

from config_paths import get_results_base, get_src_base

FIG_DIR = Path(get_results_base()) / "Plot" / "Fig3"
XLSX_PATH = FIG_DIR / "Figure3.xlsx"
CSV_PATH = FIG_DIR / "Figure3.csv"
DICT_PATH = Path(get_src_base()) / "dict_v3.xlsx"
SHP_PATH = Path(get_src_base()) / "World_map" / "polygon" / "World_polygon.shp"

MAP_COLS = ["Max_Process", "Cost_Process"]
NO_DATA_COLOR = "#d9d9d9"
FILL_PROCESS = "Improve yield rate"

# Keep dimensions/colors aligned with SP1_4_Figure_macc_stock_v3.py for composition.
MAP_FIG_WIDTH = 12.2
MAP_FIG_HEIGHT = 6.0

process_colors = {
    'Reduce Ruminate': '#911c43',
    'Improve yield rate': '#e4754f',
    'Manure management': '#0868ac',
    'Improve feed efficiency': '#fdb75cf1',
    'Enteric fermentation management': "#5c509d",
    'Improve fertilizer efficiency': '#ccebc5',
    'Rice cultivation': "#7bccc4",
    'Crop residue management': '#2bafd7',
    'Reduce waste': '#fb9a99',
}


process_aliases = {
    'Yield rate': 'Improve yield rate',
    'Feed efficiency': 'Improve feed efficiency',
    'Fertilizer efficiency': 'Improve fertilizer efficiency',
    'Improve manure management': 'Manure management',
}
NO_FILL_NAMES = {
    "GREENLAND",
    "ANTARCTICA",
    "SVALBARD AND JAN MAYEN",
    "SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS",
    "BOUVET ISLAND",
    "HEARD ISLAND AND MCDONALD ISLANDS",
    "FRENCH SOUTHERN TERRITORIES",
    "PRINCE EDWARD ISLAND",
    "WESTERN SAHARA",
}
NO_FILL_KEYWORDS = {"SEA", "OCEAN", "DISPUTE"}
PACIFIC_ISLAND_NAMES = {
    "AMERICAN SAMOA",
    "NORTHERN MARIANA ISLANDS",
    "PALAU",
    "PITCAIRN",
    "WAKE ISLAND",
    "WALLIS AND FUTUNA",
    "NORFOLK ISLAND",
}


def _should_fill(name: object) -> bool:
    if not isinstance(name, str):
        return False
    name_u = name.strip().upper()
    if not name_u or name_u == "NAN":
        return False
    if name_u in NO_FILL_NAMES or name_u in PACIFIC_ISLAND_NAMES:
        return False
    for key in NO_FILL_KEYWORDS:
        if key in name_u:
            return False
    return True


def _clean_m49(val: object) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    text = str(val).strip().replace("'", "")
    if text == "":
        return ""
    try:
        num = int(float(text))
        return str(num).zfill(3)
    except Exception:
        return text


def _pick_sheet(xlsx_path: Path, preferred: str) -> str:
    xls = pd.ExcelFile(xlsx_path)
    if preferred in xls.sheet_names:
        return preferred
    return str(xls.sheet_names[0])


def _load_map_data(input_path: Optional[Path] = None) -> pd.DataFrame:
    if input_path is not None:
        if not input_path.exists():
            raise FileNotFoundError(f"Missing map input data: {input_path}")
        if input_path.suffix.lower() in {".xlsx", ".xls"}:
            sheet = _pick_sheet(input_path, "map")
            df = pd.read_excel(input_path, sheet_name=sheet)
        else:
            df = pd.read_csv(input_path)
    elif XLSX_PATH.exists():
        sheet = _pick_sheet(XLSX_PATH, "map")
        df = pd.read_excel(XLSX_PATH, sheet_name=sheet)
    elif CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
    else:
        raise FileNotFoundError(f"Missing Figure3.xlsx or Figure3.csv in {FIG_DIR}")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _find_m49_col(df: pd.DataFrame) -> str:
    candidates = ["M49_Country_Code", "M49 Code", "M49", "M49_Country"]
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for name in candidates:
        col = lower_map.get(name.lower())
        if col:
            return col
    raise ValueError("Missing M49 column in map data.")


def _format_lon(val: float) -> str:
    if val == 0:
        return "0"
    hemi = "E" if val > 0 else "W"
    return f"{abs(int(val))}{hemi}"


def _format_lat(val: float) -> str:
    if val == 0:
        return "0"
    hemi = "N" if val > 0 else "S"
    return f"{abs(int(val))}{hemi}"


def _style_axes(ax: Axes, bounds: List[float]) -> None:
    minx, miny, maxx, maxy = bounds
    miny = max(miny, -80)
    maxy = min(maxy, 90)
    minx -= 2
    maxx += 2
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    lon_ticks = [-180, -120, -60, 0, 60, 120, 180]
    lat_ticks = [-60, -30, 0, 30, 60]
    ax.set_xticks(lon_ticks)
    ax.set_yticks(lat_ticks)
    ax.set_xticklabels([_format_lon(v) for v in lon_ticks], fontsize=11.5)
    ax.set_yticklabels([_format_lat(v) for v in lat_ticks], fontsize=11.5)
    ax.tick_params(axis="both", which="both", width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)


def _collect_categories(df: pd.DataFrame, cols: List[str]) -> List[str]:
    cats: List[str] = []
    for col in cols:
        if col not in df.columns:
            continue
        for raw in df[col].dropna().tolist():
            val = str(raw).strip()
            if val and val not in cats:
                cats.append(val)
    return cats


def _build_color_map(categories: List[str]) -> Dict[str, str]:
    color_map: Dict[str, str] = {}
    for cat in categories:
        key = process_aliases.get(cat, cat)
        color_map[cat] = process_colors.get(key, "#999999")
    return color_map


def _plot_map(gdf_world: gpd.GeoDataFrame,
              gdf_plot: gpd.GeoDataFrame,
              column: str,
              color_map: Dict[str, str],
              out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(MAP_FIG_WIDTH, MAP_FIG_HEIGHT))
    gdf_world.plot(ax=ax, color="#f2f2f2", edgecolor="white", linewidth=0.3)
    plot_colors = gdf_plot[column].map(color_map).fillna(NO_DATA_COLOR)
    gdf_plot.assign(_plot_color=plot_colors).plot(
        ax=ax,
        color=plot_colors,
        edgecolor="white",
        linewidth=0.25,
    )
    gdf_world.boundary.plot(ax=ax, color="#777777", linewidth=0.35)
    _style_axes(ax, list(gdf_world.total_bounds))
    fig.subplots_adjust(left=0.03, right=0.995, top=0.995, bottom=0.06)
    # Keep exported canvas size exactly equal to MAP_FIG_WIDTH/MAP_FIG_HEIGHT.
    fig.savefig(out_path, dpi=600)
    plt.close(fig)


def _save_legend(categories: List[str], color_map: Dict[str, str], out_path: Path) -> None:
    handles = [Patch(facecolor=color_map[c], edgecolor="none", label=c) for c in categories]
    fig, ax = plt.subplots(figsize=(4.5, max(1.0, 0.35 * len(categories))))
    ax.axis("off")
    ax.legend(handles=handles, loc="center left", frameon=False, fontsize=11)
    fig.savefig(out_path, format="svg", bbox_inches="tight")
    plt.close(fig)


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot SP_M3b country strategy maps.")
    parser.add_argument(
        "--input-data",
        type=str,
        default=None,
        help="CSV or Excel map table. Default uses output/Plot/Fig3/Figure3.xlsx or Figure3.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory. Default uses output/Plot/Fig3.",
    )
    parser.add_argument(
        "--no-fill-missing",
        action="store_true",
        help="Deprecated compatibility flag; missing countries are already kept as no data.",
    )
    parser.add_argument(
        "--fill-missing-with-yield",
        action="store_true",
        help=(
            "Legacy visual reproduction only: assign missing map records to "
            "Improve yield rate. This is not valid for scientific analysis."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = _parse_args(argv)
    output_dir = Path(args.output_dir) if args.output_dir else FIG_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.input_data) if args.input_data else None

    df = _load_map_data(input_path)
    m49_col = _find_m49_col(df)

    df[m49_col] = df[m49_col].map(_clean_m49)
    df = df[df[m49_col] != ""].copy()

    region_df = pd.read_excel(DICT_PATH, sheet_name="region")
    region_df["m49_clean"] = region_df["M49_Country_Code"].map(_clean_m49)
    map_df = df.merge(region_df[["m49_clean", "NAME"]], left_on=m49_col, right_on="m49_clean", how="left")
    map_df = map_df.dropna(subset=["NAME"])

    gdf_world = gpd.read_file(SHP_PATH)
    join_col = "NAME" if "NAME" in gdf_world.columns else gdf_world.columns[0]
    gdf_world[join_col] = gdf_world[join_col].astype(str).str.strip()
    map_df["NAME"] = map_df["NAME"].astype(str).str.strip()
    gdf_plot = gdf_world.merge(map_df, left_on=join_col, right_on="NAME", how="left")

    if args.fill_missing_with_yield and not args.no_fill_missing:
        for col in MAP_COLS:
            if col in gdf_plot.columns:
                fill_mask = gdf_plot[col].isna() & gdf_plot[join_col].apply(_should_fill)
                gdf_plot.loc[fill_mask, col] = FILL_PROCESS

    categories = _collect_categories(map_df, MAP_COLS)
    if FILL_PROCESS not in categories:
        categories.append(FILL_PROCESS)
    color_map = _build_color_map(categories)

    for col in MAP_COLS:
        if col not in gdf_plot.columns:
            continue
        out_path = output_dir / f"Figure3_{col}_map2.1.png"
        _plot_map(gdf_world, gdf_plot, col, color_map, out_path)

    legend_path = output_dir / "Figure3_legend_v2.1.svg"
    _save_legend(categories, color_map, legend_path)

    print(f"[DONE] maps saved to {output_dir}")
    print(f"[DONE] legend saved to {legend_path}")
    missing_mask = gdf_plot[MAP_COLS].isna().any(axis=1) | gdf_plot["NAME"].isna()
    missing_names = gdf_plot.loc[missing_mask, join_col].dropna().astype(str)
    missing_names = [n for n in missing_names if n.strip() and n.strip().lower() != "nan"]
    missing_names = sorted(set(missing_names))
    missing_path = output_dir / "Figure3_missing_countries_v2.1.txt"
    with missing_path.open("w", encoding="utf-8-sig") as f:
        for name in missing_names:
            f.write(f"{name}\n")
    print(f"[DONE] missing countries: {missing_path}")


if __name__ == "__main__":
    main()

