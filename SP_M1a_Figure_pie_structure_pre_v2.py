from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

import SP_M1a_Figure_pie_structure_pre as base


OUTPUT_NAME = "Y2020_Emis_structure_summary_v2.xlsx"
NET_FOREST_PROCESS = "Net forest conversion flux"
FOREST_CONVERSION_PROCESSES = {"De/Reforestation", "Forest"}


def _merge_net_forest_conversion_flux(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    process = work["Process"].astype("string").str.strip()
    work.loc[process.isin(FOREST_CONVERSION_PROCESSES), "Process"] = NET_FOREST_PROCESS
    return work


def build_y2020_emis_structure_summary_v2() -> Path:
    df, year_col = base._prepare_source()
    df = _merge_net_forest_conversion_flux(df)
    sheets: Dict[str, pd.DataFrame] = {
        "Country": base._summarize(df, ["Region_emisSum"], year_col),
        "Process": base._summarize(df, ["Process"], year_col),
        "Item": base._summarize(df, ["Item"], year_col),
        "Country-Item": base._summarize(df, ["Region_emisSum", "Item"], year_col),
        "Process-Item": base._summarize(df, ["Process", "Item"], year_col),
        "Process-Country": base._summarize(df, ["Process", "Region_emisSum"], year_col),
    }

    output_dir = base._output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / OUTPUT_NAME

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    return output_path


def main() -> None:
    output_path = build_y2020_emis_structure_summary_v2()
    print(f"[DONE] {output_path}")


if __name__ == "__main__":
    main()
