from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from config_paths import get_input_base, get_results_base, get_src_base


INPUT_CANDIDATES = (
    "emissions_summary_By_Country_Process_Item.csv",
    "emissions_summary_By_Country_Process_Item.xlsx",
)
OUTPUT_NAME = "Y2020_Emis_structure_summary.xlsx"
GROUP_LABELS = {
    "Region_label_new": "Country",
    "Region_emisSum": "Region",
    "Process": "Process",
    "Item": "Item",
}
AGGREGATE_REGION_LABELS = {"global", "world", "row"}
AGGREGATE_M49_CODES = {"000", "001"}
ORGANIC_SOIL_PROCESS = "Drained organic soils"
ORGANIC_SOIL_SOURCE_ITEMS = {
    "Organic soils",
    "Cropland organic soils",
    "Grassland organic soils",
    "Drained organic soils",
}
ORGANIC_SOIL_SPLIT_WORKBOOK = "Emission_history_1961-2020_summary.xlsx"


def _input_dir() -> Path:
    return Path(get_results_base("BASE")) / "Emis"


def _output_dir() -> Path:
    return Path(get_results_base()) / "Plot" / "Fig8"


def _dict_v3_path() -> Path:
    return Path(get_src_base()) / "dict_v3.xlsx"


def _organic_soil_split_path() -> Path:
    return Path(get_input_base()) / "Emission" / ORGANIC_SOIL_SPLIT_WORKBOOK


def _resolve_input_path() -> Path:
    for name in INPUT_CANDIDATES:
        path = _input_dir() / name
        if path.exists():
            return path
    candidates = ", ".join(str(_input_dir() / name) for name in INPUT_CANDIDATES)
    raise FileNotFoundError(f"Missing source file. Tried: {candidates}")


def _read_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def _pick_year_col(df: pd.DataFrame, year: int) -> str:
    target = str(year).casefold()
    for col in df.columns:
        text = str(col).strip()
        if text.casefold() == f"y{target}" or text.casefold() == target:
            return col
    raise KeyError(f"Missing year column for {year}.")


def _normalize_code(series: pd.Series) -> pd.Series:
    clean = (
        series.astype("string")
        .str.strip()
        .str.replace(r"^'+", "", regex=True)
        .str.replace(r"\.0$", "", regex=True)
    )
    return clean.where(~clean.str.fullmatch(r"\d{1,2}", na=False), clean.str.zfill(3))


def _clean_group_col(df: pd.DataFrame, column: str) -> pd.Series:
    return df[column].astype("string").str.strip()


def _alias_item_name(text: str) -> str:
    normalized = str(text).strip().casefold()
    normalized = normalized.replace(",", "").replace(" ", "")
    aliases = {
        "groundnuts": "Groundnut",
        "maize(corn)": "Maize (corn)",
        "potatoes": "Potatoes",
        "soyabeans": "Soya beans",
        "sugarbeet": "Sugarbeet",
        "sugarcane": "Sugar cane",
        "sweetpotatoes": "Sweetpotato",
        "treenutstotal": "Treenuts, Total",
    }
    return aliases.get(normalized, str(text).strip())


def _map_item_to_summary(series: pd.Series, item_map: Dict[str, str]) -> pd.Series:
    clean = series.astype("string").str.strip()
    alias = clean.map(_alias_item_name)
    mapped = clean.map(item_map)
    mapped_alias = alias.map(item_map)
    return mapped.fillna(mapped_alias).fillna(alias).fillna(clean)


def _normalize_column_name(value: object) -> str:
    return "".join(ch for ch in str(value).strip().casefold() if ch.isalnum())


def _find_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    normalized = {_normalize_column_name(col): str(col) for col in df.columns}
    for candidate in candidates:
        key = _normalize_column_name(candidate)
        if key in normalized:
            return normalized[key]
    return None


def _clean_mapping_pairs(df: pd.DataFrame, source_col: str, target_col: str | None) -> pd.DataFrame:
    source = df[source_col].astype("string").str.strip()
    target = source if target_col is None else df[target_col].astype("string").str.strip()
    work = pd.DataFrame({"source": source, "target": target})
    work = work.loc[
        work["source"].notna()
        & work["target"].notna()
        & work["source"].ne("")
        & work["target"].ne("")
        & ~work["source"].str.casefold().isin({"nan", "none"})
        & ~work["target"].str.casefold().isin({"nan", "none"})
    ].copy()
    return work.drop_duplicates(subset=["source"], keep="first")


def _load_emis_item_maps() -> tuple[Dict[str, str], Dict[str, str]]:
    dict_path = _dict_v3_path()
    if not dict_path.exists():
        raise FileNotFoundError(f"Missing dictionary file: {dict_path}")

    emis_item = pd.read_excel(dict_path, sheet_name="Emis_item")
    process_col = _find_column(emis_item, ["Process"])
    item_col = _find_column(emis_item, ["Item_Emis", "Item"])
    if process_col is None or item_col is None:
        available = ", ".join(str(col) for col in emis_item.columns)
        raise ValueError(
            "dict_v3.xlsx sheet Emis_item must contain Process and Item_Emis "
            f"columns. Available columns: {available}"
        )

    process_map_col = _find_column(
        emis_item,
        ["Process_map", "Process_EmisSum_map", "Process_Sum_map", "Process_Group"],
    )
    item_sum_col = _find_column(
        emis_item,
        ["Item_EmisSum_map", "Item_EmisSum", "Item_Emis_Sum", "Item_Sum_map", "Item_map"],
    )

    if process_map_col is None:
        print("[WARN] Emis_item missing Process_map; using identity process mapping.")
    if item_sum_col is None:
        print("[WARN] Emis_item missing Item_EmisSum_map; using identity item mapping.")

    process_map_df = _clean_mapping_pairs(emis_item, process_col, process_map_col)
    item_map_df = _clean_mapping_pairs(emis_item, item_col, item_sum_col)

    process_map = dict(zip(process_map_df["source"], process_map_df["target"]))
    item_map = dict(zip(item_map_df["source"], item_map_df["target"]))
    return process_map, item_map


def _load_organic_soil_split_shares(item_map: Dict[str, str]) -> tuple[Dict[str, List[tuple[str, float]]], List[tuple[str, float]]]:
    path = _organic_soil_split_path()
    if not path.exists():
        return {}, []

    try:
        soil_df = pd.read_excel(
            path,
            sheet_name="By_Country_Process_Item",
            usecols=["M49_Country_Code", "Process", "Item", "GHG", "Y2020"],
        )
    except Exception:
        return {}, []

    soil_df["Process"] = soil_df["Process"].astype("string").str.strip()
    soil_df["Item"] = soil_df["Item"].astype("string").str.strip()
    soil_df["GHG"] = soil_df["GHG"].astype("string").str.strip().str.casefold()
    soil_df["Y2020"] = pd.to_numeric(soil_df["Y2020"], errors="coerce")
    soil_df["M49_Country_Code"] = _normalize_code(soil_df["M49_Country_Code"])
    soil_df = soil_df.loc[
        soil_df["Process"].eq(ORGANIC_SOIL_PROCESS)
        & soil_df["GHG"].eq("co2eq")
        & soil_df["Y2020"].notna()
        & (soil_df["Y2020"] > 0)
    ].copy()
    if soil_df.empty:
        return {}, []

    soil_df["Item"] = _map_item_to_summary(soil_df["Item"], item_map)
    soil_df = soil_df.loc[
        soil_df["Item"].notna()
        & soil_df["Item"].ne("")
        & ~soil_df["Item"].isin(ORGANIC_SOIL_SOURCE_ITEMS)
        & ~soil_df["Item"].str.casefold().isin({"no", "nan"})
    ].copy()
    if soil_df.empty:
        return {}, []

    country_grouped = soil_df.groupby(["M49_Country_Code", "Item"], as_index=False)["Y2020"].sum()
    country_grouped["total"] = country_grouped.groupby("M49_Country_Code")["Y2020"].transform("sum")
    country_grouped = country_grouped.loc[country_grouped["total"] > 0].copy()
    country_grouped["share"] = country_grouped["Y2020"] / country_grouped["total"]

    country_shares: Dict[str, List[tuple[str, float]]] = {}
    for m49, group_df in country_grouped.groupby("M49_Country_Code", sort=False):
        country_shares[str(m49)] = [
            (str(row.Item), float(row.share))
            for row in group_df.itertuples(index=False)
            if pd.notna(row.share) and float(row.share) > 0
        ]

    global_grouped = soil_df.groupby("Item", as_index=False)["Y2020"].sum()
    global_total = float(global_grouped["Y2020"].sum())
    if global_total <= 0:
        return country_shares, []
    global_grouped["share"] = global_grouped["Y2020"] / global_total
    global_shares = [
        (str(row.Item), float(row.share))
        for row in global_grouped.itertuples(index=False)
        if pd.notna(row.share) and float(row.share) > 0
    ]
    return country_shares, global_shares


def _expand_organic_soil_aggregate_items(
    df: pd.DataFrame,
    year_col: str,
    item_map: Dict[str, str],
) -> pd.DataFrame:
    if df.empty:
        return df

    work = df.copy()
    process = work["Process"].astype("string").str.strip()
    item_raw = work["Item"].astype("string").str.strip()
    item_summary = _map_item_to_summary(item_raw, item_map)
    value = pd.to_numeric(work[year_col], errors="coerce")

    soil_mask = process.eq(ORGANIC_SOIL_PROCESS)
    aggregate_mask = soil_mask & (
        item_raw.isin(ORGANIC_SOIL_SOURCE_ITEMS) | item_summary.isin(ORGANIC_SOIL_SOURCE_ITEMS)
    )
    commodity_soil_mask = soil_mask & ~aggregate_mask & value.gt(0)
    if not aggregate_mask.any():
        return work

    if commodity_soil_mask.any():
        return work.loc[~aggregate_mask].copy()

    country_shares, global_shares = _load_organic_soil_split_shares(item_map)
    if not global_shares:
        return work

    expanded_rows = []
    for row in work.to_dict(orient="records"):
        row_process = str(row.get("Process", "") or "").strip()
        row_item = str(row.get("Item", "") or "").strip()
        mapped_item = item_map.get(row_item, row_item)
        is_soil_aggregate = (
            row_process == ORGANIC_SOIL_PROCESS
            and (row_item in ORGANIC_SOIL_SOURCE_ITEMS or mapped_item in ORGANIC_SOIL_SOURCE_ITEMS)
        )
        if not is_soil_aggregate:
            expanded_rows.append(row)
            continue

        row_value = pd.to_numeric(row.get(year_col), errors="coerce")
        if pd.isna(row_value) or float(row_value) == 0:
            expanded_rows.append(row)
            continue

        m49 = _normalize_code(pd.Series([row.get("M49_Country_Code")])).iloc[0]
        shares = country_shares.get(str(m49), global_shares)
        allocated = 0.0
        used_any = False
        for item, share in shares:
            if share <= 0:
                continue
            new_row = dict(row)
            new_row["Item"] = item
            new_value = float(row_value) * float(share)
            new_row[year_col] = new_value
            expanded_rows.append(new_row)
            allocated += new_value
            used_any = True
        if used_any:
            diff = float(row_value) - allocated
            if abs(diff) > 1e-9:
                expanded_rows[-1][year_col] = float(expanded_rows[-1][year_col]) + diff
        else:
            expanded_rows.append(row)

    return pd.DataFrame(expanded_rows, columns=work.columns)


def _load_region_emis_sum_map() -> Dict[str, str]:
    dict_path = _dict_v3_path()
    if not dict_path.exists():
        raise FileNotFoundError(f"Missing dictionary file: {dict_path}")

    region_df: pd.DataFrame | None = None
    sheet_used = ""
    for sheet_name in ("region_map", "region"):
        try:
            region_df = pd.read_excel(dict_path, sheet_name=sheet_name)
            sheet_used = sheet_name
            break
        except ValueError:
            continue

    if region_df is None:
        print("[WARN] dict_v3.xlsx missing region_map/region sheet; using source Region_label_new only.")
        return {}

    m49_col = _find_column(region_df, ["M49_Country_Code", "M49 Code", "M49", "Area Code"])
    region_col = _find_column(
        region_df,
        [
            "Region_emisSum",
            "Region_EmisSum",
            "Region_aggMC",
            "Region_label_new",
            "Region_label",
            "Region",
            "Region_agg4",
            "Region_agg3",
            "Region_agg2",
            "Region_FB",
        ],
    )
    if m49_col is None:
        available = ", ".join(str(col) for col in region_df.columns)
        print(
            f"[WARN] dict_v3.xlsx sheet {sheet_used!r} has no M49 column; "
            f"using source Region_label_new only. Available columns: {available}"
        )
        return {}
    if region_col is None:
        available = ", ".join(str(col) for col in region_df.columns)
        print(
            f"[WARN] dict_v3.xlsx sheet {sheet_used!r} has no Region_emisSum-compatible column; "
            f"using source Region_label_new only. Available columns: {available}"
        )
        return {}
    if region_col != "Region_emisSum":
        print(f"[WARN] Emis region map missing Region_emisSum; using {region_col} from sheet {sheet_used}.")

    work = region_df[[m49_col, region_col]].copy()
    work.columns = ["M49_Country_Code", "Region_emisSum"]
    work = work.dropna(subset=["M49_Country_Code", "Region_emisSum"]).copy()
    work["M49_Country_Code"] = _normalize_code(work["M49_Country_Code"])
    work["Region_emisSum"] = work["Region_emisSum"].astype("string").str.strip()
    work = work.loc[
        work["M49_Country_Code"].ne("")
        & work["Region_emisSum"].ne("")
        & ~work["Region_emisSum"].str.casefold().isin({"no", "nan", "none"})
    ].drop_duplicates(subset=["M49_Country_Code"], keep="first")

    return dict(zip(work["M49_Country_Code"], work["Region_emisSum"]))


def _prepare_source() -> tuple[pd.DataFrame, str]:
    path = _resolve_input_path()
    df = _read_source(path)
    process_map, item_map = _load_emis_item_maps()
    region_emis_sum_map = _load_region_emis_sum_map()

    required = {"M49_Country_Code", "Region_label_new", "Process", "Item", "GHG"}
    missing = required.difference(df.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise KeyError(f"Source file is missing required columns: {missing_text}")

    year_col = _pick_year_col(df, 2020)
    ghg = df["GHG"].astype("string").str.strip().str.casefold()
    region_label = _clean_group_col(df, "Region_label_new")
    m49_code = _normalize_code(df["M49_Country_Code"])

    is_aggregate = region_label.str.casefold().isin(AGGREGATE_REGION_LABELS) | m49_code.isin(AGGREGATE_M49_CODES)

    prepared = df.loc[ghg.eq("co2eq") & ~is_aggregate].copy()
    prepared[year_col] = pd.to_numeric(prepared[year_col], errors="coerce")
    prepared = prepared.loc[prepared[year_col].notna()].copy()

    prepared["Region_label_new"] = region_label.loc[prepared.index]
    prepared["Region_emisSum"] = m49_code.loc[prepared.index].map(region_emis_sum_map)
    prepared["Region_emisSum"] = prepared["Region_emisSum"].fillna(prepared["Region_label_new"])
    prepared["Region_emisSum"] = _clean_group_col(prepared, "Region_emisSum")
    prepared["Process"] = _clean_group_col(prepared, "Process")
    prepared["Item"] = _clean_group_col(prepared, "Item")
    prepared["Process"] = prepared["Process"].map(process_map).fillna(prepared["Process"])
    prepared = _expand_organic_soil_aggregate_items(prepared, year_col, item_map)
    prepared["Item"] = _map_item_to_summary(prepared["Item"], item_map)

    return prepared, year_col


def _summarize(df: pd.DataFrame, group_cols: Iterable[str], year_col: str) -> pd.DataFrame:
    group_cols = list(group_cols)
    valid_mask = pd.Series(True, index=df.index)
    for col in group_cols:
        values = _clean_group_col(df, col)
        valid_mask &= values.notna() & values.ne("")

    grouped = (
        df.loc[valid_mask, group_cols + [year_col]]
        .groupby(group_cols, as_index=False, dropna=False)[year_col]
        .sum()
        .rename(columns={year_col: "Y2020_CO2eq", **{col: GROUP_LABELS.get(col, col) for col in group_cols}})
    )
    grouped = grouped.loc[pd.to_numeric(grouped["Y2020_CO2eq"], errors="coerce").fillna(0).ne(0)].copy()

    sort_cols: List[str] = ["Y2020_CO2eq"] + [GROUP_LABELS.get(col, col) for col in group_cols]
    ascending = [False] + [True] * len(group_cols)
    return grouped.sort_values(sort_cols, ascending=ascending, kind="mergesort").reset_index(drop=True)


def build_y2020_emis_structure_summary() -> Path:
    df, year_col = _prepare_source()
    sheets: Dict[str, pd.DataFrame] = {
        "Country": _summarize(df, ["Region_emisSum"], year_col),
        "Process": _summarize(df, ["Process"], year_col),
        "Item": _summarize(df, ["Item"], year_col),
        "Country-Item": _summarize(df, ["Region_emisSum", "Item"], year_col),
        "Process-Item": _summarize(df, ["Process", "Item"], year_col),
        "Process-Country": _summarize(df, ["Process", "Region_emisSum"], year_col),
    }

    output_dir = _output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / OUTPUT_NAME

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    return output_path


def main() -> None:
    output_path = build_y2020_emis_structure_summary()
    print(f"[DONE] {output_path}")


if __name__ == "__main__":
    main()
