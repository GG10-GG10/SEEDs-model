# -*- coding: utf-8 -*-
"""Plot Figure 3d: country-level dominant mitigation intervention.

This plotter consumes the standardized S5.8.3 country source table.  Missing
rankings and unmatched geometries remain grey and are written to an explicit
join audit; no country is assigned a fallback intervention.
"""
from __future__ import annotations

import argparse
import ast
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from config_paths import get_src_base
from S5_8_3_prepare_country_dominant_mitigation_intervention import (
    ALLOWED_OUTPUT_ROOT,
    DEFAULT_OUTPUT_DIR,
    EXPECTED_STRATEGY_KINDS,
    STRATEGY_METADATA,
    ensure_output_child,
)


DEFAULT_INPUT_DATA = DEFAULT_OUTPUT_DIR / "figure3d_country_dominant_intervention.csv"
DEFAULT_FIGURE_DIR = DEFAULT_OUTPUT_DIR / "figure"
DEFAULT_REGION_DICTIONARY = Path(get_src_base()) / "dict_v3.xlsx"
DEFAULT_WORLD_SHAPEFILE = (
    Path(get_src_base()) / "World_map" / "polygon" / "World_polygon.shp"
)
NO_DATA_COLOR = "#d9d9d9"
LAND_EDGE_COLOR = "#777777"
FIGURE_WIDTH_IN = 12.2
FIGURE_HEIGHT_IN = 6.0
ISO3_ALIASES = {
    # Legacy codes in the bundled polygon layer.
    "ROU": "ROM",
    "SRB": "SEB",
    "MNE": "YUG",
    "TLS": "TMP",
}


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_m49(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).strip().replace("'", "")
    if not text or text.lower() == "nan":
        return ""
    try:
        return f"{int(float(text)):03d}"
    except (TypeError, ValueError, OverflowError):
        return text


def _decode_possible_bytes_literal(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if len(text) >= 3 and text[:2].lower() in {"b'", 'b"'}:
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, bytes):
                return parsed.decode("latin-1")
        except (SyntaxError, ValueError):
            pass
    return text


def _name_key(value: object) -> str:
    text = _decode_possible_bytes_literal(value)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").upper()
    return "".join(character for character in text if character.isalnum())


def _iso3(value: object) -> str:
    text = "" if value is None else str(value).strip().upper()
    return "" if text in {"", "NAN", "NONE", "-99"} else text


def _pick_column(columns: Sequence[object], candidates: Sequence[str]) -> str:
    normalized = {str(column).strip().upper(): str(column) for column in columns}
    for candidate in candidates:
        found = normalized.get(candidate.upper())
        if found:
            return found
    return ""


def _load_source(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing Figure 3d source data: {path}")
    if path.suffix.lower() in {".xlsx", ".xls"}:
        workbook = pd.ExcelFile(path)
        sheet = "country_dominant" if "country_dominant" in workbook.sheet_names else workbook.sheet_names[0]
        frame = pd.read_excel(path, sheet_name=sheet, dtype={"M49_Country_Code": str})
    else:
        frame = pd.read_csv(path, dtype={"M49_Country_Code": str})
    required = {
        "M49_Country_Code",
        "ISO3",
        "dominant_strategy_kind",
        "dominant_intervention",
        "dominant_color",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Figure 3d source data is missing columns: {missing}")
    frame = frame.copy()
    frame["M49_Country_Code"] = frame["M49_Country_Code"].map(_normalize_m49)
    frame["ISO3"] = frame["ISO3"].map(_iso3)
    if frame["M49_Country_Code"].duplicated().any():
        duplicates = sorted(
            frame.loc[frame["M49_Country_Code"].duplicated(False), "M49_Country_Code"].unique()
        )
        raise ValueError(f"Duplicate country rows in Figure 3d source data: {duplicates[:10]}")
    unknown = sorted(
        set(frame["dominant_strategy_kind"].dropna().astype(str).str.strip())
        .difference(EXPECTED_STRATEGY_KINDS)
        .difference({""})
    )
    if unknown:
        raise ValueError(f"Unknown Figure 3d strategy kinds: {unknown}")
    return frame


def prepare_geometry_join(
    source: pd.DataFrame,
    region_dictionary: pd.DataFrame,
    world: gpd.GeoDataFrame,
) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Join source rows to polygons with auditable name and ISO3 fallbacks."""

    region_m49_col = _pick_column(
        region_dictionary.columns,
        ("M49_Country_Code", "M49 Code", "M49"),
    )
    region_name_col = _pick_column(
        region_dictionary.columns,
        ("NAME", "Country", "Region_label_new"),
    )
    if not region_m49_col or not region_name_col:
        raise ValueError("Region dictionary must contain M49 and map NAME columns.")
    shape_name_col = _pick_column(
        world.columns,
        ("NAME", "ADMIN", "SOVEREIGNT", "NAME_LONG"),
    )
    shape_iso_col = _pick_column(
        world.columns,
        ("SOC", "ADM0_A3", "ISO_A3", "SOV_A3"),
    )
    if not shape_name_col:
        raise ValueError("World geometry must contain a country-name column.")

    region = region_dictionary[[region_m49_col, region_name_col]].copy()
    region["_m49"] = region[region_m49_col].map(_normalize_m49)
    region["_dictionary_name"] = region[region_name_col].map(
        _decode_possible_bytes_literal
    )
    region = region[region["_m49"].ne("")].drop_duplicates("_m49")

    prepared_source = source.copy()
    prepared_source["_m49"] = prepared_source["M49_Country_Code"].map(_normalize_m49)
    prepared_source = prepared_source.merge(
        region[["_m49", "_dictionary_name"]],
        on="_m49",
        how="left",
        validate="one_to_one",
    )
    prepared_source["_dictionary_name_key"] = prepared_source[
        "_dictionary_name"
    ].map(_name_key)

    prepared_world = world.copy()
    prepared_world["_shape_name"] = prepared_world[shape_name_col].fillna("").astype(str)
    prepared_world["_shape_name_key"] = prepared_world["_shape_name"].map(_name_key)
    prepared_world["_shape_iso3"] = (
        prepared_world[shape_iso_col].map(_iso3) if shape_iso_col else ""
    )
    shape_name_keys = set(
        prepared_world.loc[
            prepared_world["_shape_name_key"].ne(""), "_shape_name_key"
        ]
    )

    prepared_source["geometry_join_key"] = ""
    prepared_source["geometry_join_method"] = "unmatched"
    name_match = prepared_source["_dictionary_name_key"].isin(shape_name_keys)
    prepared_source.loc[name_match, "geometry_join_key"] = prepared_source.loc[
        name_match, "_dictionary_name_key"
    ]
    prepared_source.loc[name_match, "geometry_join_method"] = "m49_dictionary_name"

    for index in prepared_source.index[~name_match]:
        source_iso = _iso3(prepared_source.at[index, "ISO3"])
        target_iso = ISO3_ALIASES.get(source_iso, source_iso)
        if not target_iso or not shape_iso_col:
            continue
        candidates = prepared_world[
            prepared_world["_shape_iso3"].eq(target_iso)
            & prepared_world["_shape_name_key"].ne("")
        ]
        if candidates.empty:
            continue
        prepared_source.at[index, "geometry_join_key"] = candidates.iloc[0][
            "_shape_name_key"
        ]
        prepared_source.at[index, "geometry_join_method"] = "iso3_fallback"

    shape_counts = prepared_world["_shape_name_key"].value_counts()
    prepared_source["geometry_matched"] = prepared_source["geometry_join_key"].ne("")
    prepared_source["geometry_record_count"] = (
        prepared_source["geometry_join_key"].map(shape_counts).fillna(0).astype(int)
    )
    audit_columns = [
        column
        for column in (
            "M49_Country_Code",
            "ISO3",
            "country_name",
            "dominant_strategy_kind",
            "dominant_intervention",
            "selection_status",
        )
        if column in prepared_source.columns
    ] + [
        "_dictionary_name",
        "geometry_join_key",
        "geometry_join_method",
        "geometry_matched",
        "geometry_record_count",
    ]
    audit = prepared_source[audit_columns].copy()

    source_for_join = prepared_source.drop(
        columns=[
            "_m49",
            "_dictionary_name",
            "_dictionary_name_key",
        ],
        errors="ignore",
    )
    joined = prepared_world.merge(
        source_for_join,
        left_on="_shape_name_key",
        right_on="geometry_join_key",
        how="left",
        validate="many_to_one",
    )
    return joined, audit


def _format_lon(value: float) -> str:
    if value == 0:
        return "0"
    return f"{abs(int(value))}{'E' if value > 0 else 'W'}"


def _format_lat(value: float) -> str:
    if value == 0:
        return "0"
    return f"{abs(int(value))}{'N' if value > 0 else 'S'}"


def _style_axes(ax: Axes, bounds: Sequence[float]) -> None:
    minx, miny, maxx, maxy = [float(value) for value in bounds]
    ax.set_xlim(minx - 2.0, maxx + 2.0)
    ax.set_ylim(max(miny, -80.0), min(maxy, 90.0))
    lon_ticks = [-180, -120, -60, 0, 60, 120, 180]
    lat_ticks = [-60, -30, 0, 30, 60]
    ax.set_xticks(lon_ticks)
    ax.set_yticks(lat_ticks)
    ax.set_xticklabels([_format_lon(value) for value in lon_ticks], fontsize=7)
    ax.set_yticklabels([_format_lat(value) for value in lat_ticks], fontsize=7)
    ax.tick_params(axis="both", width=0.8, length=4, pad=1.5)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)


def plot_figure3d(
    joined: gpd.GeoDataFrame,
    *,
    output_stem: Path,
    title: str = "d  Intervention with the largest mitigation potential",
    dpi: int = 600,
    simplify_tolerance_degrees: float = 0.05,
) -> Dict[str, Path]:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    tolerance = float(simplify_tolerance_degrees)
    if tolerance < 0:
        raise ValueError("simplify_tolerance_degrees must be non-negative")
    rendered = joined.copy()
    if tolerance > 0:
        rendered.geometry = rendered.geometry.simplify(
            tolerance,
            preserve_topology=True,
        )
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, FIGURE_HEIGHT_IN))
    rendered.plot(ax=ax, color=NO_DATA_COLOR, edgecolor="white", linewidth=0.18)

    selected = rendered[
        rendered.get(
            "dominant_strategy_kind", pd.Series("", index=rendered.index)
        )
        .fillna("")
        .astype(str)
        .isin(EXPECTED_STRATEGY_KINDS)
    ].copy()
    if not selected.empty:
        selected["_plot_color"] = selected["dominant_strategy_kind"].map(
            {
                kind: str(STRATEGY_METADATA[kind]["color"])
                for kind in EXPECTED_STRATEGY_KINDS
            }
        )
        selected.plot(
            ax=ax,
            color=selected["_plot_color"],
            edgecolor="white",
            linewidth=0.18,
        )
    rendered.boundary.plot(ax=ax, color=LAND_EDGE_COLOR, linewidth=0.22)
    _style_axes(ax, rendered.total_bounds)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.text(
        0.01,
        0.018,
        title,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        fontweight="bold",
    )
    legend_handles = [
        Patch(
            facecolor=str(STRATEGY_METADATA[kind]["color"]),
            edgecolor="none",
            label=str(STRATEGY_METADATA[kind]["display_name"]),
        )
        for kind in EXPECTED_STRATEGY_KINDS
    ]
    legend_handles.append(
        Patch(facecolor=NO_DATA_COLOR, edgecolor="none", label="No data / no positive potential")
    )
    ax.legend(
        handles=legend_handles,
        loc="lower left",
        bbox_to_anchor=(0.012, 0.075),
        fontsize=6.3,
        handlelength=1.5,
        handleheight=0.8,
        labelspacing=0.45,
        borderaxespad=0.0,
    )
    fig.subplots_adjust(left=0.035, right=0.995, top=0.995, bottom=0.06)

    outputs = {
        "png": output_stem.with_suffix(".png"),
        "svg": output_stem.with_suffix(".svg"),
        "pdf": output_stem.with_suffix(".pdf"),
    }
    fig.savefig(outputs["png"], dpi=int(dpi))
    fig.savefig(outputs["svg"], format="svg")
    fig.savefig(outputs["pdf"], format="pdf")
    plt.close(fig)
    return outputs


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot the Figure 3d country-dominant mitigation intervention map."
    )
    parser.add_argument("--input-data", type=Path, default=DEFAULT_INPUT_DATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_FIGURE_DIR)
    parser.add_argument("--region-dictionary", type=Path, default=DEFAULT_REGION_DICTIONARY)
    parser.add_argument("--world-shapefile", type=Path, default=DEFAULT_WORLD_SHAPEFILE)
    parser.add_argument(
        "--title",
        default="d  Intervention with the largest mitigation potential",
    )
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument(
        "--simplify-tolerance-degrees",
        type=float,
        default=0.05,
        help="Topology-preserving global-map simplification; 0 disables it.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> Path:
    args = _build_arg_parser().parse_args(list(argv) if argv is not None else None)
    output_dir = ensure_output_child(Path(args.output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    source = _load_source(Path(args.input_data).expanduser().resolve())
    region_path = Path(args.region_dictionary).expanduser().resolve()
    shape_path = Path(args.world_shapefile).expanduser().resolve()
    if not region_path.exists():
        raise FileNotFoundError(f"Missing region dictionary: {region_path}")
    if not shape_path.exists():
        raise FileNotFoundError(f"Missing world shapefile: {shape_path}")
    region = pd.read_excel(region_path, sheet_name="region")
    world = gpd.read_file(shape_path)
    joined, audit = prepare_geometry_join(source, region, world)
    audit_path = output_dir / "figure3d_geometry_join_audit.csv"
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")

    output_stem = output_dir / "Figure3d_country_dominant_mitigation_intervention"
    figure_outputs = plot_figure3d(
        joined,
        output_stem=output_stem,
        title=str(args.title),
        dpi=int(args.dpi),
        simplify_tolerance_degrees=float(args.simplify_tolerance_degrees),
    )
    source_count = int(len(audit))
    matched_count = int(audit["geometry_matched"].fillna(False).astype(bool).sum())
    unmatched = audit.loc[
        ~audit["geometry_matched"].fillna(False).astype(bool),
        [column for column in ("M49_Country_Code", "ISO3", "country_name") if column in audit.columns],
    ]
    manifest = {
        "schema_version": 1,
        "generated_at_utc": _utc_now(),
        "input_data": str(Path(args.input_data).expanduser().resolve()),
        "world_shapefile": str(shape_path),
        "region_dictionary": str(region_path),
        "simplify_tolerance_degrees": float(args.simplify_tolerance_degrees),
        "source_country_count": source_count,
        "matched_country_count": matched_count,
        "geometry_join_rate": matched_count / source_count if source_count else 0.0,
        "unmatched_countries": unmatched.to_dict("records"),
        "no_positive_or_missing_selection_count": int(
            source["dominant_strategy_kind"].fillna("").astype(str).str.strip().eq("").sum()
        ),
        "outputs": {key: str(value) for key, value in figure_outputs.items()},
        "geometry_join_audit": str(audit_path),
    }
    manifest_path = output_dir / "figure3d_plot_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"[SP_M3D] png={figure_outputs['png']}")
    print(f"[SP_M3D] svg={figure_outputs['svg']}")
    print(f"[SP_M3D] pdf={figure_outputs['pdf']}")
    print(f"[SP_M3D] geometry_join={matched_count}/{source_count}")
    return output_dir


if __name__ == "__main__":
    main()
