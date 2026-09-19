# -*- coding: utf-8 -*-
"""
Plot structure-importance stacks from Figure9_structure_importance_v3.xlsx.

Inputs:
- output/Plot/Fig9/Figure9_structure_importance_v3.xlsx
  * Region_pct
  * Item_pct
  * Process_pct
  * Strategy_pct

Outputs:
- output/Plot/Fig9/Figure9_structure_importance_region_v2.1.png/.svg
- output/Plot/Fig9/Figure9_structure_importance_item_v2.1.png/.svg
- output/Plot/Fig9/Figure9_structure_importance_process_v2.1.png/.svg
- output/Plot/Fig9/Figure9_structure_importance_strategy_v2.1.png/.svg
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors as mcolors

from config_paths import get_results_base


RESULTS_BASE = Path(get_results_base())
FIG_DIR = RESULTS_BASE / "Plot" / "Fig9"
DEFAULT_XLSX = FIG_DIR / "Figure9_structure_importance_v3.xlsx"
SCRIPT_DIR = Path(__file__).resolve().parent

CONFIG = {
    "x_min_gt": -2.0,
    "x_max_gt": 30.0,
    "dpi": 800,
    "fig_width": 7.2,
    "fig_height": 5.5,
    "inplot_label_fontsize": 8.8,
    "inplot_label_min_thickness_pct": 1.2,
}

SHEET_SPECS: Dict[str, Dict[str, str]] = {
    "Region_pct": {"slug": "region", "legend": "Region"},
    "Item_pct": {"slug": "item", "legend": "Item"},
    "Process_pct": {"slug": "process", "legend": "Process"},
    "Strategy_pct": {"slug": "strategy", "legend": "Strategy"},
}

FALLBACK_STRATEGY_COLORS = {
    "Reduce Ruminate": "#911c43",
    "Improve yield rate": "#e4754f",
    "Manure management": "#0868ac",
    "Improve feed efficiency": "#fdb75cf1",
    "Enteric fermentation management": "#5c509d",
    "Improve fertilizer efficiency": "#ccebc5",
    "Rice cultivation": "#7bccc4",
    "Rice management": "#7bccc4",
    "Crop residue management": "#2bafd7",
    "Reduce waste": "#fb9a99",
}

FALLBACK_PROCESS_COLORS = {
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
    "Net forest conversion flux": "#9d1748",
    "Forest":"#63965e",
}


def _load_color_dict_from_script(
    script_name: str,
    dict_name: str,
    fallback: Dict[str, str],
) -> Dict[str, str]:
    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        return dict(fallback)

    added_to_path = False
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
        added_to_path = True
    try:
        namespace = runpy.run_path(str(script_path))
        colors = namespace.get(dict_name)
        if isinstance(colors, dict):
            out = {
                str(key): str(value)
                for key, value in colors.items()
                if isinstance(value, str) and value.strip()
            }
            if out:
                return out
    except Exception:
        return dict(fallback)
    finally:
        if added_to_path:
            try:
                sys.path.remove(str(SCRIPT_DIR))
            except ValueError:
                pass
    return dict(fallback)


STRATEGY_COLORS = _load_color_dict_from_script(
    "SP_M3a_Figure_macc_stock_v3.1.py",
    "process_colors",
    FALLBACK_STRATEGY_COLORS,
)
STRATEGY_COLORS.update(
    {
        "Emission intensity": "#63965e",
        "Emission intensity of Ag production": "#63965e",
        "Emission intensity of land use": "#63965e",
        "Land carbon price": "#4d4d4d",
    }
)
STRATEGY_COLORS.setdefault("Emission control", "#63965e")

PROCESS_COLORS = _load_color_dict_from_script(
    "SP_M1a_Figure_pie_structure_plot_v2.1.py",
    "PROCESS_COLORS",
    FALLBACK_PROCESS_COLORS,
)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot structure-importance stacks from Figure9 workbook."
    )
    parser.add_argument("--xlsx", type=str, default=None)
    parser.add_argument("--fig-dir", type=str, default=None)
    return parser


def _resolve_paths(args: argparse.Namespace) -> Tuple[Path, Path]:
    xlsx_path = Path(args.xlsx) if args.xlsx else DEFAULT_XLSX
    fig_dir = Path(args.fig_dir) if args.fig_dir else FIG_DIR
    _ensure_dir(fig_dir)
    return xlsx_path, fig_dir


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _shade_color(base_color: str, idx: int, total: int) -> Tuple[float, float, float]:
    """Return a lighter/darker shade to keep same-class colors similar."""
    rgb = np.array(mcolors.to_rgb(base_color))
    if total <= 1:
        return tuple(rgb)
    # Blend between a darker and lighter variant of the base color.
    t = idx / max(1, total - 1)
    dark = rgb * 0.75
    light = 1.0 - (1.0 - rgb) * 0.75
    blended = dark + (light - dark) * t
    return tuple(np.clip(blended, 0.0, 1.0))


def _region_class(label: str) -> str:
    text = label.lower()
    if "africa" in text or "congo" in text:
        return "africa"
    if "asia" in text or "india" in text or "indonesia" in text:
        return "asia"
    if "europe" in text or "russia" in text:
        return "europe"
    if "america" in text or "brazil" in text:
        return "americas"
    if text.strip() == "other":
        return "other"
    return "other"


def _item_class(label: str) -> str:
    text = label.lower()
    if "cattle" in text or "buffalo" in text or "sheep" in text or "goat" in text:
        return "ruminant"
    if "meat" in text or "dairy" in text:
        return "ruminant"
    if "rice" in text:
        return "rice"
    if "roundwood" in text or "wood" in text or "forest" in text:
        return "forestry"
    if text.strip() == "other":
        return "other"
    return "crop"


def _process_class(label: str) -> str:
    text = label.lower()
    if "enteric" in text:
        return "enteric"
    if "manure" in text:
        return "manure"
    if "rice" in text:
        return "rice"
    if "fertilizer" in text:
        return "fertilizer"
    if "residue" in text:
        return "residue"
    if any(key in text for key in ("reforest", "wood", "fire", "peat", "drained")):
        return "landuse"
    if "fish" in text:
        return "fish"
    return "other"


def _strategy_class(label: str) -> str:
    return "strategy"


REGION_BASE_COLORS = {
    "africa": STRATEGY_COLORS["Improve yield rate"],
    "asia": STRATEGY_COLORS["Rice cultivation"],
    "americas": STRATEGY_COLORS["Reduce Ruminate"],
    "europe": STRATEGY_COLORS["Manure management"],
    "other": "#999999",
}

ITEM_BASE_COLORS = {
    "ruminant": STRATEGY_COLORS["Reduce Ruminate"],
    "rice": STRATEGY_COLORS["Rice cultivation"],
    "crop": STRATEGY_COLORS["Improve yield rate"],
    "forestry": STRATEGY_COLORS.get("Emission control", "#63965e"),
    "other": "#999999",
}

PROCESS_BASE_COLORS = {
    "enteric": STRATEGY_COLORS["Enteric fermentation management"],
    "manure": STRATEGY_COLORS["Manure management"],
    "rice": STRATEGY_COLORS["Rice cultivation"],
    "fertilizer": STRATEGY_COLORS["Improve fertilizer efficiency"],
    "residue": STRATEGY_COLORS["Crop residue management"],
    "landuse": STRATEGY_COLORS.get("Emission control", "#63965e"),
    "fish": STRATEGY_COLORS["Improve feed efficiency"],
    "other": "#999999",
}

STRATEGY_BASE_COLORS = {
    "strategy": "#999999",
}

REGION_COLORS = {
    "Rest of Africa": "#ce4e55",
    "D. R. Congo": "#fb9a99",
    "China": "#2bafd7",
    "Brazil": "#5c509d",
    "U.S.": "#0868ac",
    "Rest of Latin America & Caribbean": "#e4754f",
    "Rest of South-Southeast Asia": "#7bccc4",
    "Europe": "#fdb75cf1",
    "Indonesia": "#f2edb5",
    "India": "#ccebc5",
    "Other": "#999999",
    "Africa": "#ce4e55",   
    "North America": "#0868ac",
    "Indonesia": "#f2edb5",
    "Rest of Asia": "#ccebc5",
    "Europe+Russia": "#fdb75cf1",
    "Rest of World": "#999999",
}

FALLBACK_STRATEGY_COLORS = {
    "Reduce Ruminate": "#911c43",
    "Improve yield rate": "#e4754f",
    "Manure management": "#0868ac",
    "Improve feed efficiency": "#fdb75cf1",
    "Enteric fermentation management": "#5c509d",
    "Improve fertilizer efficiency": "#ccebc5",
    "Rice cultivation": "#7bccc4",
    "Rice management": "#7bccc4",
    "Crop residue management": "#2bafd7",
    "Reduce waste": "#fb9a99",
}


ITEM_COLORS = {
    "Cattle and buffalo": "#5c509d",
    "Sheep and goat": "#0868ac",
    "Roundwood": "#9d1748",
    "Rice": "#7bccc4",
    "Maize": "#2bafd7",
    "Pulses": "#ccebc5",
    "Wheat": "#f2edb5",
    "Other cereals": "#fdb75cf1",
    "Other": "#999999",
}

STRATEGY_ALIASES = {
    "Reduce reminate": "Reduce Ruminate",
    "Reduce ruminate": "Reduce Ruminate",
    "Ruminate rate": "Reduce Ruminate",
    "Ruminant rate": "Reduce Ruminate",
    "Ruminant intake": "Reduce Ruminate",
    "Yield rate": "Improve yield rate",
    "Feed efficiency": "Improve feed efficiency",
    "Fertilizer efficiency": "Improve fertilizer efficiency",
    "Fertilizer rate": "Improve fertilizer efficiency",
    "Crop residue+soil management": "Crop residue management",
    "Crop residue and soil management": "Crop residue management",
    "Crop management": "Crop residue management",
    "Losses rate": "Reduce waste",
    "Waste reduction": "Reduce waste",
    "Emission intensity": "Emission intensity",
    "Emission intensity of Ag production": "Emission intensity",
    "Emission intensity of land use": "Emission intensity",
    "land_carbon_price": "Land carbon price",
    "Land carbon price": "Land carbon price",
}

PROCESS_ALIASES = {
    "Enteric fermentation management": "Enteric fermentation",
    "Manure management": "Manure management and application",
    "Manure application": "Manure management and application",
    "Fertilizer": "Synthetic fertilizers",
    "Fertilizers": "Synthetic fertilizers",
    "Synthetic fertilizer": "Synthetic fertilizers",
    "Residues": "Crop residue management",
    "Crop residues": "Crop residue management",
    "Aquaculture": "Fish farming",
    "Deforestation": "De/Reforestation",
    "Reforestation": "De/Reforestation",
    "Forest": "Net forest conversion flux",
    "Forest conversion": "Net forest conversion flux",
    "Net forest conversion": "Net forest conversion flux",
    "Roundwood": "Wood harvest",
    "Fires": "Savanna/Peatlands fires",
}

IN_PLOT_LABELS = {
    "Strategy_pct": {
        "Emission intensity": "Emission intensity",
        "Improve yield rate": "Yield rate",
        "Reduce Ruminate": "Ruminant intake",
        "Reduce waste": "Waste rate",
        "Manure management": "Manure management",
        "Crop residue management": "Crop residue+soil management",
        "Improve fertilizer efficiency": "Nitrogen efficiency",
        "Improve feed efficiency": "Feed efficiency",
        "Land carbon price": "Land carbon price",
    },
    "Process_pct": {
        "De/Reforestation": "De/Reforestation",
        "Enteric fermentation": "Enteric fermentation",
        "Wood harvest": "Wood harvest",
        "Manure management and application": "Manure management and application",
        "Others": "Others",
        "Drained organic soils": "Drained organic soils",
        "Rice cultivation": "Rice cultivation",
        "Synthetic fertilizers": "Synthetic fertilizers",
        "Crop residue management": "Crop residue management",
    },
    "Item_pct": {
        "Cattle and buffalo": "Cattle and buffalo",
        "Roundwood": "Roundwood",
        "Rice": "Rice",
        "Sheep and goat": "Sheep and goat",
        "Maize": "Maize",
        "Pulses": "Pulses",
        "Wheat": "Wheat",
        "Other": "Other",
    },
    "Region_pct": {
        "Afraic": "Rest of Africa",
        "Brazil": "Brazil",
        "Rest of South-Southeast Asia": "Rest of South-Southeast Asia",
        "Indonesia": "Indonesia",
        "North America": "North America",
        "Rest of Latin America & Caribbean": "Rest of Latin America & Caribbean",
        "Rest of Asia": "Rest of Asia",
        "Europe+Russia": "Europe+Russia",
        "Rest of World": "Rest of World",
    },
}

TOP_STACK_LABELS = {"other", "others", "rest of world"}

LABEL_X_POSITIONS = {
    "Strategy_pct": {
        "Improve yield rate": 25.5,
        "Emission intensity": 15.0,
        "Reduce Ruminate": 24.5,
        "Reduce waste": 8.0,
        "Crop residue management": 10.5,
        "Manure management": 18.0,
        "Improve feed efficiency": 13.0,
        "Improve fertilizer efficiency": 23.0,
        "Land carbon price": 28.0,
    },
    "Process_pct": {
        "De/Reforestation": 26.5,
        "Enteric fermentation": 15.0,
        "Wood harvest": 7.0,
        "Manure management and application": 8.0,
        "Others": 6.0,
        "Drained organic soils": 13.0,
        "Rice cultivation": 24.0,
        "Synthetic fertilizers": 18.0,
        "Crop residue management": 4.0,
    },
    "Item_pct": {
        "Cattle and buffalo": 16.0,
        "Roundwood": 2.0,
        "Rice": 4.0,
        "Sheep and goat": 3.0,
        "Maize": 20.0,
        "Pulses": 7.0,
        "Wheat": 16.0,
        "Other": 25.0,
    },
    "Region_pct": {
        "Afraic": 19.0,
        "Brazil": 5.0,
        "Europe+Russia": 13.0,
        "North America": 18.0,
        "Rest of Latin America & Caribbean": 18.0,
        "Rest of Asia": 25.0,
        "Indonesia": 23.0,
        "Rest of South-Southeast Asia": 23.0,
        "Rest of World": 25.0,
    },
}


def _build_color_map(
    labels: Iterable[str],
    classifier: Callable[[str], str],
    base_colors: Dict[str, str],
) -> Dict[str, Tuple[float, float, float]]:
    class_groups: Dict[str, List[str]] = {}
    for label in labels:
        class_key = classifier(str(label))
        class_groups.setdefault(class_key, []).append(str(label))

    color_map: Dict[str, Tuple[float, float, float]] = {}
    for class_key, group_labels in class_groups.items():
        base = base_colors.get(class_key, "#999999")
        for idx, label in enumerate(group_labels):
            color_map[label] = _shade_color(base, idx, len(group_labels))
    return color_map


def _apply_explicit_palette(
    labels: Iterable[str],
    explicit: Dict[str, str],
    classifier: Callable[[str], str],
    base_colors: Dict[str, str],
    aliases: Dict[str, str] | None = None,
) -> Dict[str, Tuple[float, float, float]]:
    auto = _build_color_map(labels, classifier, base_colors)
    merged = dict(auto)
    explicit_lower = {str(key).strip().lower(): value for key, value in explicit.items()}
    alias_lower = {
        str(key).strip().lower(): str(value).strip()
        for key, value in (aliases or {}).items()
    }
    for label in labels:
        raw = str(label).strip()
        canonical = (aliases or {}).get(raw) or alias_lower.get(raw.lower(), raw)
        color = (
            explicit.get(raw)
            or explicit.get(canonical)
            or explicit_lower.get(raw.lower())
            or explicit_lower.get(str(canonical).lower())
        )
        if color:
            merged[str(label)] = mcolors.to_rgb(color)
    return merged


def _sheet_palette(sheet_name: str, labels: Iterable[str]) -> Dict[str, Tuple[float, float, float]]:
    if sheet_name == "Region_pct":
        return _apply_explicit_palette(labels, REGION_COLORS, _region_class, REGION_BASE_COLORS)
    if sheet_name == "Item_pct":
        return _apply_explicit_palette(labels, ITEM_COLORS, _item_class, ITEM_BASE_COLORS)
    if sheet_name == "Process_pct":
        return _apply_explicit_palette(
            labels,
            PROCESS_COLORS,
            _process_class,
            PROCESS_BASE_COLORS,
            PROCESS_ALIASES,
        )
    if sheet_name == "Strategy_pct":
        return _apply_explicit_palette(
            labels,
            STRATEGY_COLORS,
            _strategy_class,
            STRATEGY_BASE_COLORS,
            STRATEGY_ALIASES,
        )
    return _apply_explicit_palette(labels, {}, _strategy_class, STRATEGY_BASE_COLORS)


def _read_sheet_with_excel_com(xlsx_path: Path, sheet_name: str) -> pd.DataFrame:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    excel = None
    created_excel = False
    workbook = None
    opened_workbook = False
    try:
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
        except Exception:
            excel = win32com.client.DispatchEx("Excel.Application")
            created_excel = True
            excel.Visible = False
            excel.DisplayAlerts = False

        target = str(xlsx_path.resolve()).lower()
        target_name = xlsx_path.name.lower()
        for candidate in excel.Workbooks:
            try:
                full_name = str(candidate.FullName)
                candidate_name = str(candidate.Name).lower()
                local_match = False
                try:
                    local_match = str(Path(full_name).resolve()).lower() == target
                except Exception:
                    local_match = False
                if (
                    local_match
                    or candidate_name == target_name
                    or full_name.lower().endswith("/" + target_name)
                    or full_name.lower().endswith("\\" + target_name)
                ):
                    workbook = candidate
                    break
            except Exception:
                continue

        if workbook is None:
            workbook = excel.Workbooks.Open(
                str(xlsx_path),
                UpdateLinks=0,
                ReadOnly=True,
                IgnoreReadOnlyRecommended=True,
                Notify=False,
            )
            opened_workbook = True

        sheet = workbook.Worksheets(sheet_name)
        values = sheet.UsedRange.Value
        if values is None:
            return pd.DataFrame()
        if not isinstance(values, tuple):
            values = ((values,),)
        rows = [
            list(row) if isinstance(row, tuple) else [row]
            for row in values
        ]
        if not rows:
            return pd.DataFrame()
        headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
        return pd.DataFrame(rows[1:], columns=headers)
    finally:
        if opened_workbook and workbook is not None:
            workbook.Close(SaveChanges=False)
        if created_excel and excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()


def _label_text_color(fill_color: Tuple[float, float, float]) -> str:
    rgb = np.asarray(fill_color[:3], dtype=float)
    luminance = float(np.dot(rgb, [0.299, 0.587, 0.114]))
    return "white" if luminance < 0.52 else "#333333"


def _nearest_index(x: np.ndarray, target: float) -> int:
    return int(np.abs(x - float(target)).argmin())


def _label_anchor_index(
    sheet_name: str,
    label: str,
    x: np.ndarray,
    layer_height: np.ndarray,
) -> int:
    preferred = LABEL_X_POSITIONS.get(sheet_name, {}).get(str(label))
    if preferred is not None:
        idx = _nearest_index(x, float(preferred))
        if layer_height[idx] >= float(CONFIG["inplot_label_min_thickness_pct"]):
            return idx

    x_min = float(CONFIG["x_min_gt"])
    x_max = float(CONFIG["x_max_gt"])
    interior = (x >= x_min + 1.0) & (x <= x_max - 1.0)
    if interior.any():
        interior_idx = np.where(interior)[0]
        return int(interior_idx[np.argmax(layer_height[interior])])
    return int(np.argmax(layer_height))


def _add_inplot_labels(
    ax: plt.Axes,
    sheet_name: str,
    x: np.ndarray,
    values: pd.DataFrame,
    value_cols: List[str],
    colors: Dict[str, Tuple[float, float, float]],
) -> None:
    label_map = IN_PLOT_LABELS.get(sheet_name, {})
    cumulative = np.zeros(len(x), dtype=float)
    min_thickness = float(CONFIG["inplot_label_min_thickness_pct"])
    fontsize = float(CONFIG["inplot_label_fontsize"])

    for col in value_cols:
        layer = values[col].to_numpy(dtype=float)
        layer_height = np.maximum(layer, 0.0)
        if float(np.nanmax(layer_height)) < min_thickness:
            cumulative += layer
            continue

        idx = _label_anchor_index(sheet_name, str(col), x, layer_height)
        y_mid = cumulative[idx] + layer[idx] / 2.0
        label = label_map.get(str(col), str(col))
        fill_color = colors.get(str(col), (0.6, 0.6, 0.6))
        ax.text(
            float(x[idx]),
            float(y_mid),
            label,
            ha="center",
            va="center",
            fontsize=fontsize,
            color=_label_text_color(fill_color),
            clip_on=True,
        )
        cumulative += layer


def _load_sheet(xlsx_path: Path, sheet_name: str) -> pd.DataFrame:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Missing input workbook: {xlsx_path}")
    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
    except PermissionError as exc:
        try:
            df = _read_sheet_with_excel_com(xlsx_path, sheet_name)
        except Exception as com_exc:
            raise PermissionError(
                f"Cannot read {xlsx_path}. Close the workbook in Excel or release the "
                f"OneDrive lock. Excel COM fallback also failed: {com_exc}"
            ) from exc
    df = _normalize_columns(df)
    if "Emis" not in df.columns:
        raise ValueError(f"Sheet {sheet_name} missing Emis column.")
    return df


def _stack_order_by_lowest_visible_emission(
    work: pd.DataFrame,
    values: pd.DataFrame,
    value_cols: List[str],
) -> List[str]:
    x_min = float(CONFIG["x_min_gt"])
    x_max = float(CONFIG["x_max_gt"])
    visible = work["Emis"].between(x_min, x_max, inclusive="both")
    if visible.any():
        ref_idx = work.loc[visible, "Emis"].idxmin()
    else:
        ref_idx = work["Emis"].idxmin()

    ref_importance = values.loc[ref_idx, value_cols]
    order = ref_importance.sort_values(ascending=False, kind="mergesort").index.tolist()
    top_labels = [
        col for col in order
        if str(col).strip().lower() in TOP_STACK_LABELS
    ]
    main_labels = [
        col for col in order
        if str(col).strip().lower() not in TOP_STACK_LABELS
    ]
    return main_labels + top_labels


def _plot_sheet(sheet_name: str, df: pd.DataFrame, fig_dir: Path) -> List[Path]:
    plt.rcParams["font.family"] = "Helvetica"
    plt.rcParams["font.size"] = 12

    work = df.copy()
    work["Emis"] = pd.to_numeric(work["Emis"], errors="coerce")
    work = work.dropna(subset=["Emis"]).sort_values("Emis")

    value_cols = [c for c in work.columns if c != "Emis"]
    if not value_cols:
        raise ValueError(f"Sheet {sheet_name} has no importance columns.")

    values = work[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if np.isclose(values.to_numpy().sum(), 0.0):
        raise ValueError(f"All importance values are zero in {sheet_name}.")

    row_sum = values.sum(axis=1).replace(0.0, np.nan)
    values = values.div(row_sum, axis=0).fillna(0.0) * 100.0

    value_cols = _stack_order_by_lowest_visible_emission(work, values, value_cols)

    colors = _sheet_palette(sheet_name, value_cols)
    x = work["Emis"].to_numpy(dtype=float)
    y = [values[col].to_numpy(dtype=float) for col in value_cols]

    fig, ax = plt.subplots(figsize=(CONFIG["fig_width"], CONFIG["fig_height"]))
    ax.stackplot(x, y, colors=[colors[col] for col in value_cols], labels=value_cols)
    _add_inplot_labels(ax, sheet_name, x, values, value_cols, colors)

    ax.set_xlabel("GHG CO2eq in 2080 (Gt/yr)", fontsize=13.5, fontweight="bold", labelpad=12)
    ax.set_ylabel("Variable relative importance (%)", fontsize=13.5, fontweight="bold", labelpad=12)
    ax.set_xlim(float(CONFIG["x_min_gt"]), float(CONFIG["x_max_gt"]))
    ax.set_ylim(0, 100)

    x_min = float(CONFIG["x_min_gt"])
    x_max = float(CONFIG["x_max_gt"])
    xticks = sorted(set([t for t in ax.get_xticks() if x_min <= t <= x_max] + [x_min, x_max]))
    ax.set_xticks(xticks)
    ax.tick_params(axis="both", which="both", labelsize=13, width=1.8, length=8)
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)

    spec = SHEET_SPECS.get(sheet_name, {"legend": sheet_name, "slug": sheet_name.lower()})
    fig.tight_layout()
    slug = spec.get("slug", sheet_name.lower())
    outputs = [
        fig_dir / f"Figure9_structure_importance_{slug}_v2.1.png",
        fig_dir / f"Figure9_structure_importance_{slug}_v2.1.svg",
    ]
    fig.savefig(outputs[0], dpi=int(CONFIG["dpi"]))
    fig.savefig(outputs[1])
    plt.close(fig)
    return outputs


def main() -> None:
    args = _build_arg_parser().parse_args()
    xlsx_path, fig_dir = _resolve_paths(args)

    for sheet_name in SHEET_SPECS:
        df = _load_sheet(xlsx_path, sheet_name)
        outputs = _plot_sheet(sheet_name, df, fig_dir)
        for path in outputs:
            print(f"[DONE] figure: {path}")


if __name__ == "__main__":
    main()
