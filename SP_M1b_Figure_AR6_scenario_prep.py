# -*- coding: utf-8 -*-
"""
Prepare AR6 scenario tables for Figure 6.

Generation targets:
1) base: 1.5D / 2D (from AR6_scenario.xlsx).
2) ratio: 1.5D_ratio / 2D_ratio (from AR6_scenario_prepared.xlsx -> 1.5D / 2D).
3) summary: 1.5D_summary / 2D_summary (from AR6_scenario_prepared.xlsx -> 1.5D / 2D).
4) summary amount: 1.5D_summary_amount / 2D_summary_amount (absolute values; all variables).
Output: AR6_scenario_prepared.xlsx in the same folder.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config_paths import get_results_base

FIG_DIR = Path(get_results_base()) / "Plot" / "Fig6"
INPUT_CANDIDATES = ["AR6_scenario.xlsx", "AR6_scenarios.xlsx"]
OUTPUT_NAME = "AR6_scenario_prepared_harmonization.xlsx"
GWP100_AR6 = {"CH4": 27.2, "N2O": 273.0}

# Generation switches (edit here directly; do not use CLI flags)
BUILD_BASE = False
BUILD_RATIO = True
BUILD_SUMMARY = True
BUILD_SUMMARY_AMOUNT = True


def _resolve_input() -> Path:
    for name in INPUT_CANDIDATES:
        path = FIG_DIR / name
        if path.exists():
            return path
    candidates = ", ".join(INPUT_CANDIDATES)
    raise FileNotFoundError(f"Missing input file in {FIG_DIR}: {candidates}")


def _prepared_path() -> Path:
    return FIG_DIR / OUTPUT_NAME


def _year_cols(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if str(c).startswith("Y") and str(c)[1:].isdigit()]
    return sorted(cols, key=lambda x: int(str(x)[1:]))


def _safe_div(numer: np.ndarray, denom: np.ndarray) -> np.ndarray:
    numer = np.asarray(numer, dtype=float)
    denom = np.asarray(denom, dtype=float)
    out = np.full_like(numer, np.nan, dtype=float)
    mask = np.isfinite(denom) & (np.abs(denom) > 1e-12)
    out[mask] = numer[mask] / denom[mask]
    return out


def _row_values(row: pd.Series, year_cols: List[str]) -> np.ndarray:
    return pd.to_numeric(row[year_cols], errors="coerce").to_numpy(dtype=float)


def _build_row(meta: Dict[str, object],
               year_cols: List[str],
               *,
               variable: str,
               unit: str,
               values: np.ndarray) -> Dict[str, object]:
    row = {**meta}
    row["Variable"] = variable
    row["Unit"] = unit
    for idx, col in enumerate(year_cols):
        row[col] = float(values[idx]) if idx < len(values) else np.nan
    return row


def _add_derived_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    year_cols = _year_cols(df)
    id_cols = [c for c in ["Model", "Scenario", "Scenario_map", "Region"] if c in df.columns]

    new_rows: List[Dict[str, object]] = []
    for _, grp in df.groupby(id_cols, dropna=False):
        meta = {col: grp.iloc[0][col] for col in id_cols}
        rows = {str(r.Variable): r for r in grp.itertuples(index=False)}

        def get(var: str) -> Optional[pd.Series]:
            r = rows.get(var)
            if r is None:
                return None
            return pd.Series(r._asdict())

        land_total = get("Land Cover")
        cropland = get("Land Cover|Cropland")
        forest = get("Land Cover|Forest")
        pasture = get("Land Cover|Pasture")

        if land_total is not None:
            total_vals = _row_values(land_total, year_cols)
            if cropland is not None:
                vals = _safe_div(_row_values(cropland, year_cols), total_vals)
                if "Land Cover|Cropland_share" not in rows:
                    new_rows.append(_build_row(meta, year_cols, variable="Land Cover|Cropland_share", unit="share", values=vals))
            if forest is not None:
                vals = _safe_div(_row_values(forest, year_cols), total_vals)
                if "Land Cover|Forest_share" not in rows:
                    new_rows.append(_build_row(meta, year_cols, variable="Land Cover|Forest_share", unit="share", values=vals))
            if pasture is not None:
                vals = _safe_div(_row_values(pasture, year_cols), total_vals)
                if "Land Cover|Pasture_share" not in rows:
                    new_rows.append(_build_row(meta, year_cols, variable="Land Cover|Pasture_share", unit="share", values=vals))

        def _co2eq_row(ch4_var: str, n2o_var: str, co2_var: str, out_var: str) -> Optional[np.ndarray]:
            ch4 = get(ch4_var)
            n2o = get(n2o_var)
            co2 = get(co2_var)
            if ch4 is None and n2o is None and co2 is None:
                return None
            zeros = np.zeros(len(year_cols), dtype=float)
            ch4_vals = _row_values(ch4, year_cols) * GWP100_AR6["CH4"] if ch4 is not None else zeros
            n2o_vals = _row_values(n2o, year_cols) * GWP100_AR6["N2O"] / 1000.0 if n2o is not None else zeros
            co2_vals = _row_values(co2, year_cols) if co2 is not None else zeros
            total = ch4_vals + n2o_vals + co2_vals
            if out_var not in rows:
                new_rows.append(_build_row(meta, year_cols, variable=out_var, unit="Mt CO2eq/yr", values=total))
            return total

        co2eq_afolu = _co2eq_row(
            "Emissions|CH4|AFOLU",
            "Emissions|N2O|AFOLU",
            "Emissions|CO2|AFOLU",
            "Emissions|CO2eq|AFOLU",
        )
        co2eq_ag = _co2eq_row(
            "Emissions|CH4|AFOLU|Agriculture",
            "Emissions|N2O|AFOLU|Agriculture",
            "Emissions|CO2|AFOLU|Agriculture",
            "Emissions|CO2eq|AFOLU|Agriculture",
        )
        co2eq_land = _co2eq_row(
            "Emissions|CH4|AFOLU|Land",
            "Emissions|N2O|AFOLU|Land",
            "Emissions|CO2|AFOLU|Land",
            "Emissions|CO2eq|AFOLU|Land",
        )

        if co2eq_afolu is not None and co2eq_land is not None:
            share = _safe_div(co2eq_land, co2eq_afolu)
            if "AFOLU land CO2eq share" not in rows:
                new_rows.append(_build_row(meta, year_cols, variable="AFOLU land CO2eq share", unit="share", values=share))
        if co2eq_afolu is not None and co2eq_ag is not None:
            share = _safe_div(co2eq_ag, co2eq_afolu)
            if "AFOLU agriculture CO2eq share" not in rows:
                new_rows.append(_build_row(meta, year_cols, variable="AFOLU agriculture CO2eq share", unit="share", values=share))

        ag_prod = get("Agricultural Production")
        pop = get("Population")
        if ag_prod is not None and pop is not None:
            vals = _safe_div(_row_values(ag_prod, year_cols), _row_values(pop, year_cols))
            if "Per capita Ag production" not in rows:
                new_rows.append(_build_row(meta, year_cols, variable="Per capita Ag production", unit="t DM/cap/yr", values=vals))

        if cropland is not None and pasture is not None and ag_prod is not None:
            land_use = _row_values(cropland, year_cols) + _row_values(pasture, year_cols)
            vals = _safe_div(land_use, _row_values(ag_prod, year_cols))
            if "Land-use intensity of Ag production" not in rows:
                new_rows.append(_build_row(meta, year_cols, variable="Land-use intensity of Ag production", unit="ha/t DM", values=vals))

        if co2eq_land is not None and cropland is not None and pasture is not None:
            land_use = _row_values(cropland, year_cols) + _row_values(pasture, year_cols)
            vals = _safe_div(co2eq_land, land_use)
            if "Emission intensity of land use" not in rows:
                new_rows.append(_build_row(meta, year_cols, variable="Emission intensity of land use", unit="t CO2eq/ha/yr", values=vals))

        if co2eq_ag is not None and ag_prod is not None:
            vals = _safe_div(co2eq_ag, _row_values(ag_prod, year_cols))
            if "Emission intensity of Ag production" not in rows:
                new_rows.append(_build_row(meta, year_cols, variable="Emission intensity of Ag production", unit="t CO2eq/t DM", values=vals))

        food_total = get("Food Demand")
        food_crops = get("Food Demand|Crops")
        food_livestock = get("Food Demand|Livestock")
        if food_total is not None:
            total_vals = _row_values(food_total, year_cols)
            if food_crops is not None:
                vals = _safe_div(_row_values(food_crops, year_cols), total_vals)
                if "Crop intake share" not in rows:
                    new_rows.append(_build_row(meta, year_cols, variable="Crop intake share", unit="share", values=vals))
            if food_livestock is not None:
                vals = _safe_div(_row_values(food_livestock, year_cols), total_vals)
                if "Livestock intake share" not in rows:
                    new_rows.append(_build_row(meta, year_cols, variable="Livestock intake share", unit="share", values=vals))

    if not new_rows:
        return df
    add_df = pd.DataFrame(new_rows)
    return pd.concat([df, add_df], ignore_index=True)


def _build_ratio(df: pd.DataFrame) -> pd.DataFrame:
    ratio = df.copy()
    year_cols = _year_cols(ratio)
    if "Y2010" not in year_cols or "Y2020" not in year_cols:
        return ratio
    arr = ratio[year_cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    idx2010 = year_cols.index("Y2010")
    idx2020 = year_cols.index("Y2020")
    y2010 = arr[:, idx2010]
    y2020 = arr[:, idx2020]
    out = arr.copy()
    out[:, idx2010] = 1.0
    out[:, idx2020] = _safe_div(arr[:, idx2020], y2010)
    for j in range(idx2020 + 1, len(year_cols)):
        out[:, j] = _safe_div(arr[:, j], y2020)
    ratio.loc[:, year_cols] = out
    return ratio


def _summary_from(df: pd.DataFrame,
                  variables: List[str],
                  scenario_label: str) -> pd.DataFrame:
    year_cols = _year_cols(df)
    subset = df[df["Variable"].isin(variables)].copy()
    if subset.empty:
        return pd.DataFrame(columns=["Variable", "Unit", "Stat"] + year_cols)

    rows: List[Dict[str, object]] = []
    for var, grp in subset.groupby("Variable"):
        unit = ""
        if "Unit" in grp.columns:
            unit_vals = grp["Unit"].dropna().astype(str)
            unit = unit_vals.iloc[0] if not unit_vals.empty else ""
        vals = grp[year_cols].apply(pd.to_numeric, errors="coerce")
        mean_vals = vals.mean(axis=0, skipna=True).to_numpy(dtype=float)
        max_vals = vals.max(axis=0, skipna=True).to_numpy(dtype=float)
        min_vals = vals.min(axis=0, skipna=True).to_numpy(dtype=float)
        for stat, arr in (("average", mean_vals), ("maxbound", max_vals), ("minbound", min_vals)):
            row = {
                "Variable": var,
                "Unit": unit,
                "Stat": stat,
                "Scenario": scenario_label,
                "Region": "World",
            }
            for idx, col in enumerate(year_cols):
                row[col] = float(arr[idx]) if idx < len(arr) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def _build_summary(base: pd.DataFrame, ratio: pd.DataFrame, label: str) -> pd.DataFrame:
    ratio_vars = [
        "Population",
        "Emissions|CO2eq|AFOLU",
        "Emissions|CH4|AFOLU",
        "Emissions|CO2|AFOLU",
        "Emissions|N2O|AFOLU",
        "Emissions|CO2eq|AFOLU|Agriculture",
        "Emissions|CO2eq|AFOLU|Land",
        "Per capita Ag production",
        "Land-use intensity of Ag production",
        "Emission intensity of land use",
        "Emission intensity of Ag production",
        "Fertilizer Use|Nitrogen",
        "Yield|Cereal",
        "Primary Energy|Biomass",
    ]
    share_vars = [
        "Land Cover|Cropland_share",
        "Land Cover|Forest_share",
        "Land Cover|Pasture_share",
        "EnergyCropsCroplandShare",
        "AFOLU land CO2eq share",
        "AFOLU agriculture CO2eq share",
        "Crop intake share",
        "Livestock intake share",
    ]
    summary_ratio = _summary_from(ratio, ratio_vars, label)
    summary_share = _summary_from(base, share_vars, label)
    summary = pd.concat([summary_ratio, summary_share], ignore_index=True)
    return summary


def _build_summary_amount(base: pd.DataFrame, label: str) -> pd.DataFrame:
    all_vars = (
        base["Variable"].dropna().astype(str).str.strip().replace("", np.nan).dropna().drop_duplicates().tolist()
        if "Variable" in base.columns else []
    )
    return _summary_from(base, all_vars, label)


def _read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet)


def _load_base_from_prepared(path: Path,
                             sheet_15: str = "1.5D",
                             sheet_2d: str = "2D") -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not path.exists():
        raise FileNotFoundError(f"Missing prepared file: {path}")
    xls = pd.ExcelFile(path)
    missing = [s for s in (sheet_15, sheet_2d) if s not in xls.sheet_names]
    if missing:
        raise ValueError(f"Prepared file missing base sheet(s): {', '.join(missing)}")
    return _read_sheet(path, sheet_15), _read_sheet(path, sheet_2d)


def _load_model_scenario_blocklist(path: Path, sheet: str) -> pd.Index:
    if not path.exists():
        raise FileNotFoundError(f"Missing prepared file: {path}")
    xls = pd.ExcelFile(path)
    if sheet not in xls.sheet_names:
        raise ValueError(f"Prepared file missing filtered sheet: {sheet}")

    filtered = _read_sheet(path, sheet)
    if "Model#Scenario" not in filtered.columns:
        raise ValueError(f"Filtered sheet missing required column 'Model#Scenario': {sheet}")

    keys = (
        filtered["Model#Scenario"]
        .dropna()
        .astype(str)
        .str.strip()
    )
    keys = keys[keys != ""].drop_duplicates()
    if keys.empty:
        return pd.Index([], name="Model#Scenario")
    return pd.Index(keys, name="Model#Scenario")


def _filter_base_by_blocklist(base: pd.DataFrame, blocklist: pd.Index, sheet: str) -> pd.DataFrame:
    if "Model#Scenario" not in base.columns:
        raise ValueError(f"Base sheet missing required column 'Model#Scenario': {sheet}")

    keys = base["Model#Scenario"].astype(str).str.strip()
    out = base.loc[~keys.isin(blocklist)].copy()
    if out.empty:
        raise ValueError(f"All rows were filtered out by Model#Scenario blocklist for sheet: {sheet}")
    return out


def _read_existing_workbook(path: Path) -> Dict[str, pd.DataFrame]:
    if not path.exists():
        return {}
    xls = pd.ExcelFile(path)
    return {sheet: _read_sheet(path, sheet) for sheet in xls.sheet_names}


def _write_updates(path: Path, updates: Dict[str, pd.DataFrame]) -> None:
    workbook = _read_existing_workbook(path)
    workbook.update(updates)
    if not workbook:
        raise ValueError("No sheets to write.")
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet, df in workbook.items():
            df.to_excel(writer, sheet_name=sheet, index=False)


def main() -> None:
    build_base = BUILD_BASE
    build_ratio = BUILD_RATIO
    build_summary = BUILD_SUMMARY
    build_summary_amount = BUILD_SUMMARY_AMOUNT
    if not (build_base or build_ratio or build_summary or build_summary_amount):
        raise ValueError(
            "No targets selected. Set at least one of "
            "BUILD_BASE/BUILD_RATIO/BUILD_SUMMARY/BUILD_SUMMARY_AMOUNT to True."
        )

    out_path = _prepared_path()

    if build_base:
        input_path = _resolve_input()
        xls = pd.ExcelFile(input_path)
        if "1.5D" not in xls.sheet_names or "2D" not in xls.sheet_names:
            raise ValueError("Missing required sheets in source file: 1.5D / 2D.")
        df_15 = _read_sheet(input_path, "1.5D")
        df_2d = _read_sheet(input_path, "2D")
        base_15 = _add_derived_rows(df_15)
        base_2d = _add_derived_rows(df_2d)
        _write_updates(out_path, {"1.5D": base_15, "2D": base_2d})

    if build_ratio or build_summary or build_summary_amount:
        # Always use harmonized sheets as the source for ratio/summary outputs.
        base_15, base_2d = _load_base_from_prepared(
            out_path,
            sheet_15="1.5D_harmonized",
            sheet_2d="2D_harmonized",
        )
        # Apply the same scenario filter to all downstream products.
        blocklist_15 = _load_model_scenario_blocklist(out_path, "1.5D_filtered")
        blocklist_2d = _load_model_scenario_blocklist(out_path, "2D_filtered")
        base_15 = _filter_base_by_blocklist(base_15, blocklist_15, "1.5D_harmonized")
        base_2d = _filter_base_by_blocklist(base_2d, blocklist_2d, "2D_harmonized")
        updates: Dict[str, pd.DataFrame] = {}

        ratio_15 = _build_ratio(base_15)
        ratio_2d = _build_ratio(base_2d)
        if build_ratio:
            updates["1.5D_ratio"] = ratio_15
            updates["2D_ratio"] = ratio_2d

        if build_summary:
            updates["1.5D_summary"] = _build_summary(base_15, ratio_15, "1.5D")
            updates["2D_summary"] = _build_summary(base_2d, ratio_2d, "2D")

        if build_summary_amount:
            updates["1.5D_summary_amount"] = _build_summary_amount(base_15, "1.5D")
            updates["2D_summary_amount"] = _build_summary_amount(base_2d, "2D")

        _write_updates(out_path, updates)

    print(f"[DONE] {out_path}")


if __name__ == "__main__":
    main()
