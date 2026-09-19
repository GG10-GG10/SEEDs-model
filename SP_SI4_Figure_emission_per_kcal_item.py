from __future__ import annotations

import runpy
import textwrap
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config_paths import get_results_base


SCENARIOS = ("BASE", "S30")
SUMMARY_NAME = "Y2080_Emission_result_summary.xlsx"
OUTPUT_DIR = Path(get_results_base()) / "Plot" / "Fig11"
VALUE_COL = "Y2080_CO2eq"
GT_DIVISOR = 1_000_000.0
FIG_SIZE = (13.2, 6.4)
DPI = 450
COLORBAR_QUANTILE_BREAKS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

MAIN_SPAN = 8.25
SPECIAL_GAP = 0.16
SPECIAL_WIDTH = 0.42
SPECIAL_STEP = 0.47
TOTAL_GAP = 0.18
TOTAL_WIDTH = 0.48

EDGE_COLOR = "#303030"
TOTAL_GRADIENT_DARK = "#050505"
TOTAL_GRADIENT_LIGHT = "#6a6a6a"
CUMULATIVE_COLOR = "#111111"
CUMULATIVE_ALPHA = 0.55
CUMULATIVE_LINE_WIDTH = 0.65
CUMULATIVE_MARKER_HALF_WIDTH = 0.055
CUMULATIVE_MARKER_SIZE = 12
CUMULATIVE_ZERO_COLOR = "#202020"
CUMULATIVE_ZERO_ALPHA = 0.32
NEGATIVE_SPECIAL_COLOR = "#6baed6"


def _load_process_colors() -> Dict[str, str]:
    script_path = Path(__file__).with_name("SP_M1a_Figure_pie_structure_plot_v2.1.py")
    colors: Dict[str, str] = {}
    if script_path.exists():
        try:
            namespace = runpy.run_path(str(script_path))
            raw = namespace.get("PROCESS_COLORS", {})
            if isinstance(raw, dict):
                colors.update({str(key): str(value) for key, value in raw.items()})
        except Exception as exc:
            print(f"[WARN] Failed to read colors from {script_path.name}: {exc}")
    if not colors:
        try:
            import SP_M1a_Figure_pie_structure_plot_v2 as base_colors

            colors.update({str(key): str(value) for key, value in base_colors.PROCESS_COLORS.items()})
        except Exception:
            pass
    return colors


PROCESS_COLORS = _load_process_colors()
SPECIAL_COLORS = {
    "Roundwood": PROCESS_COLORS.get("Wood harvest", "#c94f58"),
    "Fires": PROCESS_COLORS.get("Savanna/Peatlands fires", "#f2b463"),
    "Existing forestland": "#006d2c",
    "Forest": "#006d2c",
    "Forestland": "#006d2c",
    "Fore set": "#006d2c",
}
SPECIAL_ORDER = ("Roundwood", "Fires", "Existing forestland", "Forest", "Forestland", "Fore set")
INTENSITY_EXCLUDE_KEYWORDS = ("fire", "forest", "forestland", "roundwood", "fore set")
DISPLAY_LABELS = {
    "Fruits and vegetables": "Fruits/veg",
    "Other meat and dairy": "Other meat/dairy",
    "Other cereals": "Other cereals",
    "Sugar and oil crops": "Sugar/oil crops",
    "Cattle and buffalo": "Cattle",
    "Sheep and goat": "Sheep",
    "Existing forestland": "Existing\nforestland",
}


def _summary_path(scenario: str) -> Path:
    return Path(get_results_base(scenario)) / SUMMARY_NAME


def _read_sheet(scenario: str, sheet_name: str) -> pd.DataFrame:
    path = _summary_path(scenario)
    if not path.exists():
        raise FileNotFoundError(f"Missing summary workbook: {path}")
    return pd.read_excel(path, sheet_name=sheet_name)


def _as_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _clean_item(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _is_special_item(item: object) -> bool:
    text = "" if item is None or pd.isna(item) else str(item).strip().lower()
    return any(keyword in text for keyword in INTENSITY_EXCLUDE_KEYWORDS)


def _wrap_label(label: object, width: int = 12) -> str:
    text = "" if label is None or pd.isna(label) else str(label)
    text = DISPLAY_LABELS.get(text, text)
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False)) or text


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
    zorder: float = 4.0,
) -> None:
    rect = plt.Rectangle(
        (x_center - width / 2.0, bottom),
        width,
        height,
        facecolor="none",
        edgecolor=EDGE_COLOR,
        linewidth=0.85,
        zorder=zorder,
    )
    ax.add_patch(rect)
    n = 256
    pos = np.linspace(0.0, 1.0, n)
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
        zorder=zorder - 0.3,
    )
    im.set_clip_path(rect)


def _load_item_data(scenario: str) -> Tuple[pd.DataFrame, pd.DataFrame, float]:
    kcal = _read_sheet(scenario, "Item-kcal")
    area = _read_sheet(scenario, "Item-area")
    item = _read_sheet(scenario, "Item")

    for df in (kcal, area, item):
        if "Item" not in df.columns:
            raise KeyError(f"{scenario} summary sheet missing Item column")
        df["Item"] = _clean_item(df["Item"])
    for col in (VALUE_COL, "kcal", "Emission/kcal"):
        if col not in kcal.columns:
            raise KeyError(f"{scenario} Item-kcal sheet missing {col}")
        kcal[col] = _as_number(kcal[col])
    for col in (VALUE_COL, "ag_area_ha", "Emission/ha"):
        if col not in area.columns:
            raise KeyError(f"{scenario} Item-area sheet missing {col}")
        area[col] = _as_number(area[col])
    item[VALUE_COL] = _as_number(item[VALUE_COL])

    main = kcal.merge(
        area[["Item", "ag_area_ha", "Emission/ha"]],
        on="Item",
        how="left",
        validate="one_to_one",
    )
    main = main.loc[~main["Item"].map(_is_special_item)].copy()
    main["Emission/ha"] = _as_number(main["Emission/ha"])
    main["emission_Gt"] = main[VALUE_COL] / GT_DIVISOR
    main["intensity_kg_per_1000kcal"] = main["Emission/kcal"] * 1_000_000_000.0
    main["emission_per_ha_kt"] = main["Emission/ha"]
    main = main.sort_values("intensity_kg_per_1000kcal", kind="mergesort").reset_index(drop=True)

    special = item.loc[item["Item"].map(_is_special_item), ["Item", VALUE_COL]].copy()
    special = special.groupby("Item", as_index=False)[VALUE_COL].sum()
    special["order"] = special["Item"].map({name: idx for idx, name in enumerate(SPECIAL_ORDER)})
    special["order"] = special["order"].fillna(len(SPECIAL_ORDER))
    special = special.sort_values(["order", "Item"], kind="mergesort").drop(columns="order")
    special["emission_Gt"] = special[VALUE_COL] / GT_DIVISOR

    total_gt = float(item[VALUE_COL].sum() / GT_DIVISOR)
    return main, special, total_gt


def _global_area_norm(scenarios: Iterable[str]) -> mpl.colors.BoundaryNorm:
    values: List[float] = []
    for scenario in scenarios:
        main, _, _ = _load_item_data(scenario)
        values.extend(main["emission_per_ha_kt"].replace([np.inf, -np.inf], np.nan).dropna().tolist())
    if not values:
        return mpl.colors.BoundaryNorm(np.array([0.0, 1.0]), ncolors=256, clip=True)

    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return mpl.colors.BoundaryNorm(np.array([0.0, 1.0]), ncolors=256, clip=True)

    boundaries = np.nanquantile(arr, COLORBAR_QUANTILE_BREAKS)
    boundaries = np.unique(np.asarray(boundaries, dtype=float))
    if boundaries.size < 2:
        center = float(boundaries[0]) if boundaries.size else 0.0
        boundaries = np.array([center - 0.5, center + 0.5], dtype=float)
    return mpl.colors.BoundaryNorm(boundaries, ncolors=256, clip=True)


def _format_colorbar_value(value: float, _pos: object = None) -> str:
    if np.isclose(value, 0.0):
        return "0"
    if abs(value) < 0.1:
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _main_bar_geometry(main: pd.DataFrame) -> pd.DataFrame:
    out = main.copy()
    kcal_total = float(out["kcal"].sum())
    if kcal_total <= 0:
        out["width"] = MAIN_SPAN / max(len(out), 1)
    else:
        out["width"] = out["kcal"] / kcal_total * MAIN_SPAN
    out["x_start"] = out["width"].cumsum().shift(fill_value=0.0)
    out["x_end"] = out["x_start"] + out["width"]
    out["x_center"] = (out["x_start"] + out["x_end"]) / 2.0
    out["cum_start_Gt"] = out["emission_Gt"].cumsum().shift(fill_value=0.0)
    out["cum_end_Gt"] = out["cum_start_Gt"] + out["emission_Gt"]
    return out


def _special_geometry(special: pd.DataFrame, start_x: float, start_cum: float, total_gt: float) -> pd.DataFrame:
    rows: List[Dict[str, float | str]] = []
    current = start_cum
    x = start_x + SPECIAL_GAP + SPECIAL_WIDTH / 2.0
    for _, row in special.iterrows():
        value = float(row["emission_Gt"])
        end = current + value
        rows.append(
            {
                "section": "special",
                "Item": str(row["Item"]),
                VALUE_COL: float(row[VALUE_COL]),
                "emission_Gt": value,
                "x_start": x - SPECIAL_WIDTH / 2.0,
                "x_end": x + SPECIAL_WIDTH / 2.0,
                "x_center": x,
                "cum_start_Gt": current,
                "cum_end_Gt": end,
                "bottom_Gt": min(current, end),
                "height_Gt": abs(value),
            }
        )
        current = end
        x += SPECIAL_STEP

    total_x = x - SPECIAL_STEP + SPECIAL_WIDTH / 2.0 + TOTAL_GAP + TOTAL_WIDTH / 2.0
    rows.append(
        {
            "section": "total",
            "Item": "Total",
            VALUE_COL: total_gt * GT_DIVISOR,
            "emission_Gt": total_gt,
            "x_start": total_x - TOTAL_WIDTH / 2.0,
            "x_end": total_x + TOTAL_WIDTH / 2.0,
            "x_center": total_x,
            "cum_start_Gt": 0.0,
            "cum_end_Gt": total_gt,
            "bottom_Gt": min(0.0, total_gt),
            "height_Gt": abs(total_gt),
        }
    )
    return pd.DataFrame(rows)


def _plot_limits(primary_values: pd.Series, cumulative_values: Iterable[float]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    p_low = min(0.0, float(primary_values.min()))
    p_high = max(0.0, float(primary_values.max()))
    p_span = max(p_high - p_low, 1.0)
    primary_ylim = (p_low - p_span * 0.10, p_high + p_span * 0.16)

    vals = list(cumulative_values)
    c_low = min(0.0, min(vals) if vals else 0.0)
    c_high = max(0.0, max(vals) if vals else 1.0)
    c_span = max(c_high - c_low, 1.0)
    cumulative_ylim = (c_low - c_span * 0.10, c_high + c_span * 0.16)
    return primary_ylim, cumulative_ylim


def _align_cumulative_zero_to_primary(
    primary_ylim: Tuple[float, float],
    cumulative_ylim: Tuple[float, float],
) -> Tuple[float, float]:
    primary_low, primary_high = primary_ylim
    cumulative_low, cumulative_high = cumulative_ylim
    primary_span = primary_high - primary_low
    if primary_span <= 0:
        return cumulative_ylim

    zero_frac = (0.0 - primary_low) / primary_span
    if zero_frac <= 0.0 or zero_frac >= 1.0:
        return cumulative_ylim

    span_for_low = (-cumulative_low / zero_frac) if cumulative_low < 0.0 else 0.0
    span_for_high = (cumulative_high / (1.0 - zero_frac)) if cumulative_high > 0.0 else 0.0
    cumulative_span = max(span_for_low, span_for_high, 1.0)
    return -zero_frac * cumulative_span, (1.0 - zero_frac) * cumulative_span


def _global_plot_limits(scenarios: Iterable[str]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    primary_values: List[float] = []
    cumulative_values: List[float] = []
    for scenario in scenarios:
        main, special, total_gt = _load_item_data(scenario)
        main_geom = _main_bar_geometry(main)
        special_geom = _special_geometry(
            special,
            float(main_geom["x_end"].max()),
            float(main_geom["cum_end_Gt"].iloc[-1]),
            total_gt,
        )
        primary_values.extend(main_geom["intensity_kg_per_1000kcal"].astype(float).tolist())
        cumulative_values.extend(main_geom["cum_end_Gt"].astype(float).tolist())
        cumulative_values.extend(special_geom["cum_start_Gt"].astype(float).tolist())
        cumulative_values.extend(special_geom["cum_end_Gt"].astype(float).tolist())
    primary_ylim, cumulative_ylim = _plot_limits(pd.Series(primary_values, dtype=float), cumulative_values)
    cumulative_ylim = _align_cumulative_zero_to_primary(primary_ylim, cumulative_ylim)
    return primary_ylim, cumulative_ylim


def _scenario_plot_limits(scenario: str) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    main, special, total_gt = _load_item_data(scenario)
    main_geom = _main_bar_geometry(main)
    special_geom = _special_geometry(
        special,
        float(main_geom["x_end"].max()),
        float(main_geom["cum_end_Gt"].iloc[-1]),
        total_gt,
    )
    primary_values = main_geom["intensity_kg_per_1000kcal"].astype(float)
    cumulative_values = main_geom["cum_end_Gt"].astype(float).tolist()
    cumulative_values.extend(special_geom["cum_start_Gt"].astype(float).tolist())
    cumulative_values.extend(special_geom["cum_end_Gt"].astype(float).tolist())
    primary_ylim, cumulative_ylim = _plot_limits(primary_values, cumulative_values)
    cumulative_ylim = _align_cumulative_zero_to_primary(primary_ylim, cumulative_ylim)
    return primary_ylim, cumulative_ylim


def _zero_crossing_x(rows: pd.DataFrame) -> float | None:
    for _, row in rows.iterrows():
        start = float(row["cum_start_Gt"])
        end = float(row["cum_end_Gt"])
        if np.isclose(start, 0.0) or np.isclose(end, 0.0) or start * end >= 0.0:
            continue
        fraction = -start / (end - start)
        return float(row["x_start"]) + fraction * float(row["x_end"] - row["x_start"])
    return None


def _draw_cumulative_markers(
    ax: plt.Axes,
    main_geom: pd.DataFrame,
    special_geom: pd.DataFrame,
    cumulative_ylim: Tuple[float, float],
) -> None:
    marker_rows = []
    marker_rows.append({"x": float(main_geom["x_start"].iloc[0]), "y": 0.0})
    marker_rows.extend(
        {"x": float(row["x_end"]), "y": float(row["cum_end_Gt"])}
        for _, row in main_geom.iterrows()
    )

    special_rows = special_geom.loc[special_geom["section"].eq("special")]
    marker_rows.extend(
        {"x": float(row["x_center"]), "y": float(row["cum_end_Gt"])}
        for _, row in special_rows.iterrows()
    )
    total_row = special_geom.loc[special_geom["section"].eq("total")].iloc[0]
    marker_rows.append({"x": float(total_row["x_center"]), "y": float(total_row["cum_end_Gt"])})

    xs = [row["x"] for row in marker_rows]
    ys = [row["y"] for row in marker_rows]
    ax.plot(
        xs,
        ys,
        color=CUMULATIVE_COLOR,
        alpha=CUMULATIVE_ALPHA,
        linewidth=CUMULATIVE_LINE_WIDTH,
        linestyle="-",
        solid_capstyle="round",
        zorder=5.8,
    )
    for x, y in zip(xs, ys):
        ax.hlines(
            y,
            x - CUMULATIVE_MARKER_HALF_WIDTH,
            x + CUMULATIVE_MARKER_HALF_WIDTH,
            color=CUMULATIVE_COLOR,
            alpha=CUMULATIVE_ALPHA,
            linewidth=2.4,
            zorder=6,
        )
    ax.scatter(
        xs,
        ys,
        s=CUMULATIVE_MARKER_SIZE,
        color=CUMULATIVE_COLOR,
        alpha=CUMULATIVE_ALPHA,
        linewidths=0,
        zorder=6.2,
    )

    zero_x = _zero_crossing_x(main_geom)
    if zero_x is None:
        return
    ax.vlines(
        zero_x,
        cumulative_ylim[0],
        0.0,
        color=CUMULATIVE_ZERO_COLOR,
        alpha=CUMULATIVE_ZERO_ALPHA,
        linewidth=0.9,
        linestyles=(0, (2.0, 2.0)),
        zorder=1.8,
    )
    ax.annotate(
        "cum=0",
        xy=(zero_x, 0.0),
        xytext=(3, 4),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=7,
        color=CUMULATIVE_ZERO_COLOR,
        alpha=0.58,
        zorder=7,
    )


def _plot_scenario(
    scenario: str,
    norm: mpl.colors.BoundaryNorm,
    primary_ylim: Tuple[float, float],
    cumulative_ylim: Tuple[float, float],
) -> Tuple[Path, Path, pd.DataFrame]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    main, special, total_gt = _load_item_data(scenario)
    main_geom = _main_bar_geometry(main)
    special_geom = _special_geometry(special, float(main_geom["x_end"].max()), float(main_geom["cum_end_Gt"].iloc[-1]), total_gt)

    cmap = mpl.colormaps["GnBu"]
    bar_colors = [cmap(norm(value)) for value in main_geom["emission_per_ha_kt"]]

    fig, ax = plt.subplots(figsize=FIG_SIZE, facecolor="white")
    ax.set_facecolor("white")
    ax.bar(
        main_geom["x_center"],
        main_geom["intensity_kg_per_1000kcal"],
        width=main_geom["width"],
        align="center",
        color=bar_colors,
        edgecolor=EDGE_COLOR,
        linewidth=0.85,
        zorder=3,
    )
    ax.axhline(0, color="#202020", linewidth=0.85, zorder=2)

    ax2 = ax.twinx()
    ax2.patch.set_alpha(0.0)
    for _, row in special_geom.iterrows():
        if row["section"] == "special":
            color = SPECIAL_COLORS.get(str(row["Item"]), NEGATIVE_SPECIAL_COLOR)
            ax2.bar(
                float(row["x_center"]),
                float(row["height_Gt"]),
                bottom=float(row["bottom_Gt"]),
                width=SPECIAL_WIDTH,
                color=color,
                edgecolor=EDGE_COLOR,
                linewidth=0.85,
                zorder=4,
            )
            va = "bottom" if float(row["emission_Gt"]) >= 0 else "top"
            offset = 0.18 if float(row["emission_Gt"]) >= 0 else -0.18
            ax2.text(
                float(row["x_center"]),
                float(row["cum_end_Gt"]) + offset,
                f"{float(row['emission_Gt']):+.1f}",
                ha="center",
                va=va,
                fontsize=8.5,
                color="#202020",
                zorder=8,
            )
        else:
            _draw_total_gradient_bar(
                ax2,
                x_center=float(row["x_center"]),
                bottom=float(row["bottom_Gt"]),
                height=float(row["height_Gt"]),
                width=TOTAL_WIDTH,
                zorder=4.5,
            )
            ax2.text(
                float(row["x_center"]),
                float(row["cum_end_Gt"]) + 0.28,
                f"{float(row['cum_end_Gt']):.1f}",
                ha="center",
                va="bottom",
                fontsize=9.5,
                fontweight="bold",
                color="#202020",
                zorder=8,
            )

    _draw_cumulative_markers(ax2, main_geom, special_geom, cumulative_ylim)

    all_x_centers = main_geom["x_center"].astype(float).tolist() + special_geom["x_center"].astype(float).tolist()
    labels = [_wrap_label(v, 11) for v in main_geom["Item"]]
    labels.extend(_wrap_label(v, 11) for v in special_geom["Item"])
    ax.set_xticks(all_x_centers)
    ax.set_xticklabels(labels, rotation=63, ha="right", fontsize=8.1)

    ax.set_ylim(*primary_ylim)
    ax2.set_ylim(*cumulative_ylim)
    ax.set_xlim(-0.08, float(special_geom["x_end"].max()) + 0.20)

    ax.set_ylabel("Emission intensity (kg CO2-eq per 1,000 kcal)", fontsize=11)
    ax2.set_ylabel("Cumulative GHG emissions (Gt CO2-eq yr$^{-1}$)", fontsize=11)
    ax.set_xlabel("kcal", fontsize=10.5)
    ax.grid(False)
    ax2.grid(False)

    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    boundaries = np.asarray(norm.boundaries, dtype=float)
    cax = ax.inset_axes([0.018, 0.74, 0.016, 0.22])
    cbar = fig.colorbar(
        sm,
        cax=cax,
        orientation="vertical",
        boundaries=boundaries,
        ticks=boundaries,
        spacing="uniform",
    )
    cbar.outline.set_linewidth(0.55)
    cbar.ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(_format_colorbar_value))
    cbar.ax.tick_params(labelsize=5.8, width=0.55, length=2)
    cbar.set_label("Emission/ha", fontsize=7.3, labelpad=3)

    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_color("#202020")
        ax.spines[spine].set_linewidth(0.75)
    ax2.spines["right"].set_color("#202020")
    ax2.spines["right"].set_linewidth(0.75)
    ax.tick_params(axis="both", width=0.75, length=4, color="#202020")
    ax2.tick_params(axis="y", width=0.75, length=4, color="#202020")

    plot_data_main = main_geom.copy()
    plot_data_main["section"] = "main"
    plot_data_main["bottom_Gt"] = np.nan
    plot_data_main["height_Gt"] = np.nan
    plot_data_main["color_value_emission_per_ha_kt"] = plot_data_main["emission_per_ha_kt"]
    plot_data_special = special_geom.copy()
    plot_data_special["kcal"] = np.nan
    plot_data_special["Emission/kcal"] = np.nan
    plot_data_special["intensity_kg_per_1000kcal"] = np.nan
    plot_data_special["ag_area_ha"] = np.nan
    plot_data_special["Emission/ha"] = np.nan
    plot_data_special["emission_per_ha_kt"] = np.nan
    plot_data_special["color_value_emission_per_ha_kt"] = np.nan
    plot_data = pd.concat([plot_data_main, plot_data_special], ignore_index=True, sort=False)
    plot_data.insert(0, "Scenario", scenario)
    plot_data["colorbar_quantile_breaks"] = ";".join(f"{value:g}" for value in COLORBAR_QUANTILE_BREAKS)
    plot_data["colorbar_boundaries_emission_per_ha_kt"] = ";".join(f"{value:.12g}" for value in boundaries)
    plot_data["colorbar_vmin_emission_per_ha_kt"] = float(boundaries[0])
    plot_data["colorbar_vmax_emission_per_ha_kt"] = float(boundaries[-1])
    plot_data["primary_ylim_min"] = primary_ylim[0]
    plot_data["primary_ylim_max"] = primary_ylim[1]
    plot_data["cumulative_ylim_min"] = cumulative_ylim[0]
    plot_data["cumulative_ylim_max"] = cumulative_ylim[1]

    fig.subplots_adjust(left=0.085, right=0.915, bottom=0.31, top=0.965)
    png = OUTPUT_DIR / f"Figure11_emission_per_kcal_item_{scenario}.png"
    svg = OUTPUT_DIR / f"Figure11_emission_per_kcal_item_{scenario}.svg"
    fig.savefig(png, dpi=DPI)
    fig.savefig(svg)
    plt.close(fig)
    return png, svg, plot_data


def build_fig11_emission_per_kcal_item(scenarios: Iterable[str] = SCENARIOS) -> Dict[str, Path]:
    scenario_list = [str(scenario) for scenario in scenarios]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    norm = _global_area_norm(scenario_list)
    primary_ylim, cumulative_ylim = _global_plot_limits(scenario_list)

    outputs: Dict[str, Path] = {}
    all_data: List[pd.DataFrame] = []
    for scenario in scenario_list:
        scenario_primary_ylim = primary_ylim
        scenario_cumulative_ylim = cumulative_ylim
        if scenario.upper() == "S30":
            scenario_primary_ylim, scenario_cumulative_ylim = _scenario_plot_limits(scenario)
        png, svg, data = _plot_scenario(scenario, norm, scenario_primary_ylim, scenario_cumulative_ylim)
        data_csv = OUTPUT_DIR / f"Figure11_emission_per_kcal_item_{scenario}_data.csv"
        data.to_csv(data_csv, index=False, encoding="utf-8-sig")
        outputs[f"{scenario}_png"] = png
        outputs[f"{scenario}_svg"] = svg
        outputs[f"{scenario}_data_csv"] = data_csv
        all_data.append(data)

    data_xlsx = OUTPUT_DIR / "Figure11_emission_per_kcal_item_data.xlsx"
    with pd.ExcelWriter(data_xlsx, engine="openpyxl") as writer:
        for data in all_data:
            scenario = str(data["Scenario"].iloc[0])
            data.to_excel(writer, sheet_name=scenario[:31], index=False)
    outputs["data_xlsx"] = data_xlsx
    return outputs


if __name__ == "__main__":
    outputs = build_fig11_emission_per_kcal_item()
    for key, path in outputs.items():
        print(f"{key}: {path}")
