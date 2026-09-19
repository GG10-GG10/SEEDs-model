from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import FuncFormatter

from config_paths import get_input_base, get_results_base, get_src_base


YEAR = 2020
YEAR_COL = f"Y{YEAR}"
ELEMENT_TARGET = "Food supply (kcal/capita/day)"
RUMINANT_ITEMS = {
	"Bovine Meat",
	"Butter, Ghee",
	"Milk - Excluding Butter",
	"Mutton & Goat Meat",
}
TOTAL_ITEM = "Grand Total"

NO_DATA_COLOR = "#d9d9d9"
COLORBAR_COLORS = [
	"#fff7ec",
	"#fee8c8",
	"#fdd49e",
	"#fdbb84",
	"#fc8d59",
	"#ef6548",
	"#d7301f",
	"#b30000",
	"#7f0000",
]

MAP_FIG_WIDTH = 12.2
MAP_FIG_HEIGHT = 6.0


def _clean_m49(val: object) -> str:
	if val is None or (isinstance(val, float) and np.isnan(val)):
		return ""
	text = str(val).strip().replace("'", "").replace('"', "")
	if not text:
		return ""
	try:
		return str(int(float(text))).zfill(3)
	except Exception:
		return text


def _find_col(df: pd.DataFrame, candidates: Iterable[str], required: bool = True) -> str:
	lower_map = {str(c).strip().lower(): c for c in df.columns}
	for name in candidates:
		col = lower_map.get(name.lower())
		if col is not None:
			return str(col)
	if required:
		raise ValueError(f"Missing column, candidates={list(candidates)}")
	return ""


def _find_year_col(df: pd.DataFrame, year: int) -> str:
	candidates = [f"Y{year}", str(year), f"Y{year}F", f"{year}F"]
	try:
		return _find_col(df, candidates, required=True)
	except Exception:
		for col in df.columns:
			s = str(col).strip().upper()
			if s.startswith("Y") and s[1:].isdigit() and int(s[1:]) == year:
				return str(col)
		raise ValueError(f"Missing year column for {year}")


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


def _get_paths() -> dict[str, Path]:
	input_base = Path(get_input_base())
	src_base = Path(get_src_base())
	result_base = Path(get_results_base())

	fig_dir = result_base / "Plot" / "Fig7"
	cache_dir = fig_dir / "cache"
	cache_file = cache_dir / f"ruminate_intake_ratio_{YEAR}.csv"

	return {
		"input_xlsx": input_base / "Production_Trade" / "FoodBalanceSheets_E_All_Data_NOFLAG_demand_refilled.xlsx",
		"dict_v3": src_base / "dict_v3.xlsx",
		"world_shp": src_base / "World_map" / "polygon" / "World_polygon.shp",
		"fig_dir": fig_dir,
		"cache_dir": cache_dir,
		"cache_file": cache_file,
		"out_png": fig_dir / f"Figure7_ruminateIntakeRatio_map_{YEAR}.png",
		"out_svg": fig_dir / f"Figure7_ruminateIntakeRatio_map_{YEAR}.svg",
		"map_table": fig_dir / f"Figure7_ruminateIntakeRatio_map_{YEAR}.csv",
	}


def build_or_load_cache(force_rebuild: bool = False) -> pd.DataFrame:
	paths = _get_paths()
	cache_file = paths["cache_file"]
	cache_file.parent.mkdir(parents=True, exist_ok=True)

	if cache_file.exists() and not force_rebuild:
		out = pd.read_csv(cache_file)
		out["M49_Country_Code"] = out["M49_Country_Code"].astype(str).map(_clean_m49)
		out["ruminate_intake_ratio"] = pd.to_numeric(out["ruminate_intake_ratio"], errors="coerce")
		return out

	input_xlsx = paths["input_xlsx"]
	if not input_xlsx.exists():
		raise FileNotFoundError(f"Missing input file: {input_xlsx}")

	df = pd.read_excel(input_xlsx)
	df.columns = [str(c).strip() for c in df.columns]

	m49_col = _find_col(
		df,
		[
			"Area Code (M49)",
			"M49_Country_Code",
			"Area Code",
			"M49 Code",
			"M49",
		],
	)
	item_col = _find_col(df, ["Item"])
	element_col = _find_col(df, ["Element"])
	year_col = _find_year_col(df, YEAR)

	work = df[df[element_col].astype(str).str.strip() == ELEMENT_TARGET].copy()
	work["m49_clean"] = work[m49_col].map(_clean_m49)
	work = work[work["m49_clean"] != ""].copy()
	work["item_clean"] = work[item_col].astype(str).str.strip()
	work["value"] = pd.to_numeric(work[year_col], errors="coerce")
	work = work.dropna(subset=["value"])

	ruminate_sum = (
		work[work["item_clean"].isin(RUMINANT_ITEMS)]
		.groupby("m49_clean", as_index=False)["value"]
		.sum()
		.rename(columns={"value": "ruminate_kcal"})
	)

	total_sum = (
		work[work["item_clean"] == TOTAL_ITEM]
		.groupby("m49_clean", as_index=False)["value"]
		.sum()
		.rename(columns={"value": "grand_total_kcal"})
	)

	out = total_sum.merge(ruminate_sum, on="m49_clean", how="left")
	out["ruminate_kcal"] = out["ruminate_kcal"].fillna(0.0)
	out["ruminate_intake_ratio"] = np.where(
		out["grand_total_kcal"] > 0,
		out["ruminate_kcal"] / out["grand_total_kcal"],
		np.nan,
	)
	out = out.rename(columns={"m49_clean": "M49_Country_Code"})
	out["year"] = YEAR
	out = out[["M49_Country_Code", "year", "ruminate_kcal", "grand_total_kcal", "ruminate_intake_ratio"]]
	out.to_csv(cache_file, index=False, encoding="utf-8-sig")
	return out


def plot_map_2020(ratio_df: pd.DataFrame) -> None:
	paths = _get_paths()
	fig_dir = paths["fig_dir"]
	fig_dir.mkdir(parents=True, exist_ok=True)

	dict_path = paths["dict_v3"]
	shp_path = paths["world_shp"]
	if not dict_path.exists():
		raise FileNotFoundError(f"Missing dict_v3: {dict_path}")
	if not shp_path.exists():
		raise FileNotFoundError(f"Missing world shapefile: {shp_path}")

	region_df = pd.read_excel(dict_path, sheet_name="region")
	region_df["m49_clean"] = region_df["M49_Country_Code"].map(_clean_m49)
	map_df = ratio_df.copy()
	map_df["M49_Country_Code"] = map_df["M49_Country_Code"].map(_clean_m49)
	map_df = map_df.merge(
		region_df[["m49_clean", "NAME"]],
		left_on="M49_Country_Code",
		right_on="m49_clean",
		how="left",
	)
	map_df = map_df.dropna(subset=["NAME"])
	map_df["NAME"] = map_df["NAME"].astype(str).str.strip()

	gdf_world = gpd.read_file(shp_path)
	join_col = "NAME" if "NAME" in gdf_world.columns else gdf_world.columns[0]
	gdf_world[join_col] = gdf_world[join_col].astype(str).str.strip()

	gdf_plot = gdf_world.merge(
		map_df[["NAME", "M49_Country_Code", "ruminate_intake_ratio"]],
		left_on=join_col,
		right_on="NAME",
		how="left",
	)

	valid_mask = gdf_plot["ruminate_intake_ratio"].notna()

	fig, ax = plt.subplots(figsize=(MAP_FIG_WIDTH, MAP_FIG_HEIGHT))
	gdf_world.plot(ax=ax, color="#f2f2f2", edgecolor="white", linewidth=0.3)

	if (~valid_mask).any():
		gdf_plot.loc[~valid_mask].plot(ax=ax, color=NO_DATA_COLOR, edgecolor="white", linewidth=0.25)

	cmap = ListedColormap(COLORBAR_COLORS)
	norm: BoundaryNorm | None = None

	if valid_mask.any():
		vmin = float(gdf_plot.loc[valid_mask, "ruminate_intake_ratio"].min())
		vmax = float(gdf_plot.loc[valid_mask, "ruminate_intake_ratio"].max())
		if np.isclose(vmin, vmax):
			pad = max(abs(vmin) * 0.05, 1e-6)
			vmin -= pad
			vmax += pad

		boundaries = np.linspace(vmin, vmax, len(COLORBAR_COLORS) + 1)
		norm = BoundaryNorm(boundaries, cmap.N, clip=True)
		gdf_plot.loc[valid_mask].plot(
			ax=ax,
			column="ruminate_intake_ratio",
			cmap=cmap,
			norm=norm,
			edgecolor="white",
			linewidth=0.25,
		)

		sm = ScalarMappable(cmap=cmap, norm=norm)
		sm.set_array([])
		cbar = fig.colorbar(
			sm,
			ax=ax,
			orientation="horizontal",
			fraction=0.045,
			pad=0.09,
			aspect=35,
		)
		cbar.set_label("Ruminant-source intake ratio", fontsize=11.5, labelpad=6)
		cbar.ax.tick_params(labelsize=10.5, width=1.3, length=6)
		cbar.ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _pos: f"{x:.1%}"))

	gdf_world.boundary.plot(ax=ax, color="#777777", linewidth=0.35)
	_style_axes(ax, list(gdf_world.total_bounds))
	fig.subplots_adjust(left=0.03, right=0.995, top=0.995, bottom=0.12)
	fig.savefig(paths["out_png"], dpi=600)
	fig.savefig(paths["out_svg"])
	plt.close(fig)

	map_df = map_df[["M49_Country_Code", "NAME", "ruminate_intake_ratio"]].copy()
	map_df = map_df.sort_values(["M49_Country_Code"]).reset_index(drop=True)
	map_df.to_csv(paths["map_table"], index=False, encoding="utf-8-sig")

	print(f"[DONE] cache: {paths['cache_file']}")
	print(f"[DONE] map png: {paths['out_png']}")
	print(f"[DONE] map svg: {paths['out_svg']}")
	print(f"[DONE] map table: {paths['map_table']}")


def main() -> None:
	plt.rcParams["font.family"] = "Arial"
	plt.rcParams["font.size"] = 11
	ratio_df = build_or_load_cache(force_rebuild=False)
	plot_map_2020(ratio_df)


if __name__ == "__main__":
	main()
