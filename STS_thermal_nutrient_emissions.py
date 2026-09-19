# -*- coding: utf-8 -*-
"""STS Tier 2 feed, energy, manure N/P and emissions mass balance."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from STS_thermal_stress_model import ThermalStressDataError, canonical_species, normalize_m49


CH4_ENERGY_MJ_PER_KG = 55.65
CH4_DENSITY_KG_PER_M3 = 0.67
N_TO_N2O = 44.0 / 28.0
N_TO_NH3 = 17.0 / 14.0
N_TO_NO2 = 46.0 / 14.0


@dataclass
class Tier2EmissionsResult:
    inventory: pd.DataFrame
    activity: pd.DataFrame
    balance_diagnostics: pd.DataFrame


REQUIRED_PARAMETER_COLUMNS: Tuple[str, ...] = (
    "species",
    "production_role",
    "gross_energy_mj_per_kg_dm",
    "digestibility_fraction_base",
    "ash_fraction_dm",
    "ym_percent",
    "b0_m3_ch4_per_kg_vs",
    "manure_mcf_fraction",
    "feed_n_fraction_dm",
    "feed_p_fraction_dm",
    "product_n_kg_per_t",
    "product_p_kg_per_t",
    "housing_manure_fraction",
    "grazing_manure_fraction",
    "direct_application_fraction",
    "housing_nh3_n_fraction",
    "housing_nox_n_fraction",
    "storage_nh3_n_fraction",
    "storage_nox_n_fraction",
    "storage_n2_n_fraction",
    "application_nh3_n_fraction",
    "application_nox_n_fraction",
    "grazing_nh3_n_fraction",
    "grazing_nox_n_fraction",
    "application_leaching_fraction",
    "grazing_leaching_fraction",
    "direct_n2o_n_ef_storage",
    "direct_n2o_n_ef_application",
    "direct_n2o_n_ef_grazing",
    "indirect_n2o_n_ef_volatilization",
    "indirect_n2o_n_ef_leaching",
    "p_runoff_fraction",
    "p_leaching_fraction",
    "p_recovery_fraction",
    "grid_co2_kg_per_kwh",
    "fuel_co2_kg_per_gj",
    "source_id",
    "parameter_status",
)


def load_tier2_parameters(path: str | Path, *, strict: bool = True) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Tier 2 livestock parameter registry not found: {source}")
    if source.suffix.lower() in {".csv", ".txt"}:
        df = pd.read_csv(source)
    elif source.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(source)
    elif source.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(source)
    else:
        raise ThermalStressDataError(f"Unsupported Tier 2 registry format: {source.suffix}")
    missing = sorted(set(REQUIRED_PARAMETER_COLUMNS) - set(df.columns))
    if missing:
        raise ThermalStressDataError(f"Tier 2 registry missing columns: {missing}")
    out = df.copy()
    out["species"] = out["species"].map(canonical_species)
    out["production_role"] = out["production_role"].astype(str).str.lower().str.strip()
    if out["species"].isna().any():
        raise ThermalStressDataError("Tier 2 registry contains unsupported species")
    for column in REQUIRED_PARAMETER_COLUMNS[2:-2]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    numeric = list(REQUIRED_PARAMETER_COLUMNS[2:-2])
    if out[numeric].isna().any().any() or (out[numeric] < 0.0).any().any():
        raise ThermalStressDataError("Tier 2 numeric parameters must be finite and non-negative")
    fraction_columns = [
        column
        for column in numeric
        if "fraction" in column or column.startswith("direct_n2o") or column.startswith("indirect_n2o")
    ]
    if (out[fraction_columns] > 1.0).any().any():
        raise ThermalStressDataError("Tier 2 fractions/emission factors must not exceed one")
    status = out["parameter_status"].fillna("").astype(str).str.lower().str.strip()
    if strict and (~status.eq("production")).any():
        raise ThermalStressDataError("Tier 2 registry contains non-production rows")
    out = out.loc[status.eq("production")].copy()
    duplicate_key = [
        column
        for column in ("m49", "year", "production_system", "species", "production_role")
        if column in out.columns
    ]
    if out.duplicated(duplicate_key).any():
        raise ThermalStressDataError("Tier 2 registry has duplicate parameter keys")
    return out.reset_index(drop=True)


def _merge_parameters(ledger: pd.DataFrame, parameters: pd.DataFrame) -> pd.DataFrame:
    work = ledger.copy()
    work["m49"] = work["m49"].map(normalize_m49)
    work["species"] = work["species"].map(canonical_species)
    work["production_role"] = (
        work["production_role"].astype(str).str.lower().str.strip()
    )
    if "production_system" not in work.columns:
        work["production_system"] = "all"
    work["production_system"] = (
        work["production_system"].fillna("all").astype(str).str.lower().str.strip()
    )
    work["_ledger_id"] = np.arange(len(work), dtype=np.int64)
    params = parameters.copy()
    params["species"] = params["species"].map(canonical_species)
    params["parameter_role"] = (
        params.pop("production_role").astype(str).str.lower().str.strip()
    )
    if "production_system" in params.columns:
        params["parameter_system"] = (
            params.pop("production_system")
            .fillna("all")
            .astype(str)
            .str.lower()
            .str.strip()
        )
    else:
        params["parameter_system"] = "all"
    if "m49" in params.columns:
        raw_m49 = params.pop("m49")
        wildcard = raw_m49.isna() | raw_m49.astype(str).str.lower().str.strip().isin(
            ["", "all", "*", "global"]
        )
        params["parameter_m49"] = raw_m49.map(normalize_m49)
        params.loc[wildcard, "parameter_m49"] = "all"
    else:
        params["parameter_m49"] = "all"
    if "year" in params.columns:
        params["parameter_year"] = pd.to_numeric(
            params.pop("year"), errors="coerce"
        )
    else:
        params["parameter_year"] = np.nan

    merged = work.merge(params, on="species", how="left", validate="many_to_many")
    candidate = (
        merged["parameter_role"].isin(["all"])
        | merged["parameter_role"].eq(merged["production_role"])
    ) & (
        merged["parameter_system"].eq("all")
        | merged["parameter_system"].eq(merged["production_system"])
    ) & (
        merged["parameter_m49"].eq("all")
        | merged["parameter_m49"].eq(merged["m49"])
    ) & (
        merged["parameter_year"].isna()
        | merged["parameter_year"].eq(pd.to_numeric(merged["year"], errors="coerce"))
    )
    merged = merged.loc[candidate].copy()
    merged["_m49_rank"] = np.where(merged["parameter_m49"].eq("all"), 1, 0)
    merged["_year_rank"] = np.where(merged["parameter_year"].isna(), 1, 0)
    merged["_role_rank"] = np.where(merged["parameter_role"].eq("all"), 1, 0)
    merged["_system_rank"] = np.where(merged["parameter_system"].eq("all"), 1, 0)
    rank_columns = ["_m49_rank", "_year_rank", "_role_rank", "_system_rank"]
    merged = merged.sort_values(["_ledger_id"] + rank_columns)
    tied = merged.duplicated(["_ledger_id"] + rank_columns, keep=False)
    if tied.any():
        ambiguous = merged.loc[
            tied,
            [
                "m49",
                "year",
                "species",
                "production_role",
                "production_system",
                "parameter_m49",
                "parameter_year",
                "parameter_role",
                "parameter_system",
            ],
        ].drop_duplicates()
        raise ThermalStressDataError(
            "Tier 2 parameter overrides are ambiguous at equal priority: "
            + repr(ambiguous.head(20).to_dict(orient="records"))
        )
    merged = merged.drop_duplicates("_ledger_id", keep="first")
    missing_ids = sorted(set(work["_ledger_id"]) - set(merged["_ledger_id"]))
    if missing_ids:
        missing = work.loc[
            work["_ledger_id"].isin(missing_ids),
            [
                column
                for column in (
                    "m49",
                    "year",
                    "species",
                    "production_role",
                    "production_system",
                )
                if column in work.columns
            ],
        ]
        raise ThermalStressDataError(
            "Tier 2 parameters do not cover activity ledger rows: "
            + repr(missing.head(20).to_dict(orient="records"))
        )
    return merged.drop(
        columns=["_ledger_id", "parameter_m49", "parameter_year"] + rank_columns,
        errors="ignore",
    )


def _take_fraction(pool: pd.Series, fraction: pd.Series) -> tuple[pd.Series, pd.Series]:
    loss = pool * fraction.clip(0.0, 1.0)
    return loss, pool - loss


def calculate_tier2_livestock_emissions(
    ledger: pd.DataFrame,
    parameters: pd.DataFrame,
    *,
    strict: bool = True,
    balance_tolerance_kg: float = 1e-6,
) -> Tier2EmissionsResult:
    if ledger is None or ledger.empty:
        empty = pd.DataFrame()
        return Tier2EmissionsResult(empty, empty, empty)
    required_ledger = {
        "m49",
        "year",
        "commodity",
        "species",
        "production_role",
        "production_t",
        "dmi_t",
        "electricity_kwh",
        "fuel_gj",
    }
    missing = sorted(required_ledger - set(ledger.columns))
    if missing:
        raise ThermalStressDataError(f"Tier 2 activity ledger missing columns: {missing}")
    missing_parameters = sorted(
        set(REQUIRED_PARAMETER_COLUMNS) - set(parameters.columns)
    )
    if missing_parameters:
        raise ThermalStressDataError(
            f"Tier 2 parameter table missing columns: {missing_parameters}"
        )
    if not np.isfinite(float(balance_tolerance_kg)) or balance_tolerance_kg < 0.0:
        raise ThermalStressDataError(
            "Tier 2 balance_tolerance_kg must be finite and non-negative"
        )

    ledger_input = ledger.copy()
    required_activity_numeric = [
        "year",
        "production_t",
        "dmi_t",
        "electricity_kwh",
        "fuel_gj",
    ]
    activity_numeric = ledger_input[required_activity_numeric].apply(
        pd.to_numeric, errors="coerce"
    )
    if strict:
        activity_values = activity_numeric.to_numpy(dtype=float)
        invalid_activity = ~np.isfinite(activity_values) | (activity_values < 0.0)
        if invalid_activity.any():
            bad_columns = [
                column
                for index, column in enumerate(required_activity_numeric)
                if invalid_activity[:, index].any()
            ]
            raise ThermalStressDataError(
                "Tier 2 required activity must be finite and non-negative; "
                f"invalid columns: {bad_columns}"
            )
        year_values = activity_numeric["year"].to_numpy(dtype=float)
        if not np.equal(year_values, np.floor(year_values)).all():
            raise ThermalStressDataError("Tier 2 activity years must be integers")
    for column in required_activity_numeric:
        ledger_input[column] = activity_numeric[column]

    work = _merge_parameters(ledger_input, parameters)
    parameter_numeric = list(REQUIRED_PARAMETER_COLUMNS[2:-2])
    for column in parameter_numeric:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if strict:
        parameter_values = work[parameter_numeric].to_numpy(dtype=float)
        invalid_parameters = ~np.isfinite(parameter_values) | (
            parameter_values < 0.0
        )
        if invalid_parameters.any():
            bad_columns = [
                column
                for index, column in enumerate(parameter_numeric)
                if invalid_parameters[:, index].any()
            ]
            raise ThermalStressDataError(
                "Tier 2 numeric parameters must be finite and non-negative; "
                f"invalid columns: {bad_columns}"
            )
        status = work["parameter_status"].fillna("").astype(str).str.lower().str.strip()
        if (~status.eq("production")).any():
            raise ThermalStressDataError(
                "Tier 2 strict calculation requires production parameters"
            )
    for column, default in (
        ("digestibility_multiplier", 1.0),
        ("enteric_ch4_ef_multiplier", 1.0),
        ("volatile_solids_multiplier", 1.0),
        ("manure_ch4_ef_multiplier", 1.0),
        ("n_excretion_multiplier", 1.0),
        ("p_excretion_multiplier", 1.0),
        ("manure_n2o_ef_multiplier", 1.0),
    ):
        if column not in work.columns:
            work[column] = default
            continue
        values = pd.to_numeric(work[column], errors="coerce")
        if strict and (
            not np.isfinite(values.to_numpy(dtype=float)).all()
            or (values < 0.0).any()
        ):
            raise ThermalStressDataError(
                f"Tier 2 {column} must be finite and non-negative"
            )
        work[column] = values if strict else values.fillna(default)
    calculation_base_columns = set(work.columns)
    work["feed_dm_kg"] = pd.to_numeric(work["dmi_t"], errors="coerce") * 1000.0
    work["gross_energy_mj"] = work["feed_dm_kg"] * work["gross_energy_mj_per_kg_dm"]
    work["digestibility_fraction"] = (
        work["digestibility_fraction_base"] * work["digestibility_multiplier"]
    ).clip(0.0, 0.99)
    work["ym_percent_effective"] = work["ym_percent"] * work["enteric_ch4_ef_multiplier"]
    work["enteric_ch4_kg"] = (
        work["gross_energy_mj"] * work["ym_percent_effective"] / 100.0 / CH4_ENERGY_MJ_PER_KG
    )
    work["volatile_solids_kg_tier2"] = (
        work["feed_dm_kg"]
        * (1.0 - work["digestibility_fraction"])
        * (1.0 - work["ash_fraction_dm"])
        * work["volatile_solids_multiplier"]
    )
    work["manure_ch4_kg"] = (
        work["volatile_solids_kg_tier2"]
        * work["b0_m3_ch4_per_kg_vs"]
        * CH4_DENSITY_KG_PER_M3
        * work["manure_mcf_fraction"]
        * work["manure_ch4_ef_multiplier"]
    )

    work["n_intake_kg"] = work["feed_dm_kg"] * work["feed_n_fraction_dm"]
    work["n_retained_kg"] = (
        pd.to_numeric(work["production_t"], errors="coerce").fillna(0.0)
        * work["product_n_kg_per_t"]
    )
    work["p_intake_kg"] = work["feed_dm_kg"] * work["feed_p_fraction_dm"]
    work["p_retained_kg"] = (
        pd.to_numeric(work["production_t"], errors="coerce").fillna(0.0)
        * work["product_p_kg_per_t"]
    )
    if strict and (
        (work["n_retained_kg"] > work["n_intake_kg"] + balance_tolerance_kg).any()
        or (work["p_retained_kg"] > work["p_intake_kg"] + balance_tolerance_kg).any()
    ):
        raise ThermalStressDataError("Product N/P retention exceeds feed N/P intake")
    work["n_excretion_base_kg"] = (
        work["n_intake_kg"] - work["n_retained_kg"]
    ).clip(lower=0.0)
    work["p_excretion_base_kg"] = (
        work["p_intake_kg"] - work["p_retained_kg"]
    ).clip(lower=0.0)
    work["n_excreted_kg_tier2"] = (
        work["n_excretion_base_kg"] * work["n_excretion_multiplier"]
    )
    work["p_excreted_kg_tier2"] = (
        work["p_excretion_base_kg"] * work["p_excretion_multiplier"]
    )
    # Positive values are net body retention; negative values are mobilization.
    # Keeping this pool explicit preserves feed-input independence and closes
    # the nutrient balance when thermal stress changes excretion physiology.
    work["n_body_pool_change_kg"] = (
        work["n_intake_kg"]
        - work["n_retained_kg"]
        - work["n_excreted_kg_tier2"]
    )
    work["p_body_pool_change_kg"] = (
        work["p_intake_kg"]
        - work["p_retained_kg"]
        - work["p_excreted_kg_tier2"]
    )

    partition_sum = (
        work["housing_manure_fraction"]
        + work["grazing_manure_fraction"]
        + work["direct_application_fraction"]
    )
    if strict and not np.allclose(partition_sum, 1.0, atol=1e-9, rtol=0.0):
        raise ThermalStressDataError("Manure management partition fractions must sum to one")
    housing = work["n_excreted_kg_tier2"] * work["housing_manure_fraction"]
    grazing = work["n_excreted_kg_tier2"] * work["grazing_manure_fraction"]
    direct_application = work["n_excreted_kg_tier2"] * work["direct_application_fraction"]

    work["nh3_n_housing_kg"], housing_after_nh3 = _take_fraction(
        housing, work["housing_nh3_n_fraction"]
    )
    work["nox_n_housing_kg"], storage_input = _take_fraction(
        housing_after_nh3, work["housing_nox_n_fraction"]
    )
    work["nh3_n_storage_kg"], storage_after_nh3 = _take_fraction(
        storage_input, work["storage_nh3_n_fraction"]
    )
    work["nox_n_storage_kg"], storage_after_nox = _take_fraction(
        storage_after_nh3, work["storage_nox_n_fraction"]
    )
    work["n2_n_storage_kg"], storage_after_n2 = _take_fraction(
        storage_after_nox, work["storage_n2_n_fraction"]
    )
    work["n2o_n_direct_storage_kg"], storage_remaining = _take_fraction(
        storage_after_n2,
        work["direct_n2o_n_ef_storage"] * work["manure_n2o_ef_multiplier"],
    )
    application = storage_remaining + direct_application
    work["nh3_n_application_kg"], application_after_nh3 = _take_fraction(
        application, work["application_nh3_n_fraction"]
    )
    work["nox_n_application_kg"], application_after_nox = _take_fraction(
        application_after_nh3, work["application_nox_n_fraction"]
    )
    work["n2o_n_direct_application_kg"], application_after_n2o = _take_fraction(
        application_after_nox,
        work["direct_n2o_n_ef_application"] * work["manure_n2o_ef_multiplier"],
    )
    work["n_leached_application_kg"], work["n_to_soil_application_kg"] = _take_fraction(
        application_after_n2o, work["application_leaching_fraction"]
    )
    work["nh3_n_grazing_kg"], grazing_after_nh3 = _take_fraction(
        grazing, work["grazing_nh3_n_fraction"]
    )
    work["nox_n_grazing_kg"], grazing_after_nox = _take_fraction(
        grazing_after_nh3, work["grazing_nox_n_fraction"]
    )
    work["n2o_n_direct_grazing_kg"], grazing_after_n2o = _take_fraction(
        grazing_after_nox,
        work["direct_n2o_n_ef_grazing"] * work["manure_n2o_ef_multiplier"],
    )
    work["n_leached_grazing_kg"], work["n_to_soil_grazing_kg"] = _take_fraction(
        grazing_after_n2o, work["grazing_leaching_fraction"]
    )
    work["nh3_n_total_kg"] = work[
        ["nh3_n_housing_kg", "nh3_n_storage_kg", "nh3_n_application_kg", "nh3_n_grazing_kg"]
    ].sum(axis=1)
    work["nox_n_total_kg"] = work[
        ["nox_n_housing_kg", "nox_n_storage_kg", "nox_n_application_kg", "nox_n_grazing_kg"]
    ].sum(axis=1)
    work["n2o_n_direct_total_kg"] = work[
        ["n2o_n_direct_storage_kg", "n2o_n_direct_application_kg", "n2o_n_direct_grazing_kg"]
    ].sum(axis=1)
    work["n_leached_total_kg"] = work[
        ["n_leached_application_kg", "n_leached_grazing_kg"]
    ].sum(axis=1)
    work["n_to_soil_total_kg"] = work[
        ["n_to_soil_application_kg", "n_to_soil_grazing_kg"]
    ].sum(axis=1)
    work["n2o_n_indirect_volatilization_kg"] = (
        (work["nh3_n_total_kg"] + work["nox_n_total_kg"])
        * work["indirect_n2o_n_ef_volatilization"]
    )
    work["n2o_n_indirect_leaching_kg"] = (
        work["n_leached_total_kg"] * work["indirect_n2o_n_ef_leaching"]
    )

    p_fraction_sum = work[["p_runoff_fraction", "p_leaching_fraction", "p_recovery_fraction"]].sum(axis=1)
    if strict and (p_fraction_sum > 1.0 + 1e-9).any():
        raise ThermalStressDataError("P runoff/leaching/recovery fractions exceed one")
    work["p_runoff_kg"] = work["p_excreted_kg_tier2"] * work["p_runoff_fraction"]
    work["p_leached_kg"] = work["p_excreted_kg_tier2"] * work["p_leaching_fraction"]
    work["p_recovered_kg"] = work["p_excreted_kg_tier2"] * work["p_recovery_fraction"]
    work["p_to_soil_or_storage_kg"] = work["p_excreted_kg_tier2"] - work[
        ["p_runoff_kg", "p_leached_kg", "p_recovered_kg"]
    ].sum(axis=1)
    work["housing_energy_co2_kg"] = (
        pd.to_numeric(work["electricity_kwh"], errors="coerce").fillna(0.0)
        * work["grid_co2_kg_per_kwh"]
        + pd.to_numeric(work["fuel_gj"], errors="coerce").fillna(0.0)
        * work["fuel_co2_kg_per_gj"]
    )

    work["n_primary_out_kg"] = (
        work["n_retained_kg"]
        + work["n_body_pool_change_kg"]
        + work["nh3_n_total_kg"]
        + work["nox_n_total_kg"]
        + work["n2_n_storage_kg"]
        + work["n2o_n_direct_total_kg"]
        + work["n_leached_total_kg"]
        + work["n_to_soil_total_kg"]
    )
    work["n_balance_residual_kg"] = work["n_intake_kg"] - work["n_primary_out_kg"]
    work["p_primary_out_kg"] = (
        work["p_retained_kg"]
        + work["p_body_pool_change_kg"]
        + work["p_runoff_kg"]
        + work["p_leached_kg"]
        + work["p_recovered_kg"]
        + work["p_to_soil_or_storage_kg"]
    )
    work["p_balance_residual_kg"] = work["p_intake_kg"] - work["p_primary_out_kg"]
    if strict:
        calculation_columns = sorted(set(work.columns) - calculation_base_columns)
        nonfinite_columns = [
            column
            for column in calculation_columns
            if not np.isfinite(
                pd.to_numeric(work[column], errors="coerce").to_numpy(dtype=float)
            ).all()
        ]
        if nonfinite_columns:
            raise ThermalStressDataError(
                "Tier 2 calculation produced non-finite values in columns: "
                + repr(nonfinite_columns)
            )
        max_residual = float(
            work[["n_balance_residual_kg", "p_balance_residual_kg"]].abs().max().max()
        )
        if max_residual > float(balance_tolerance_kg):
            raise ThermalStressDataError(
                f"Tier 2 N/P mass balance residual {max_residual:.6g} kg exceeds tolerance"
            )

    identifiers = [
        column
        for column in ("m49", "year", "commodity", "species", "production_role", "production_system")
        if column in work.columns
    ]
    emission_specs = [
        ("Enteric fermentation", "CH4", "enteric_ch4_kg", "gross_energy_mj"),
        ("Manure management", "CH4", "manure_ch4_kg", "volatile_solids_kg_tier2"),
        ("Manure management", "N2O", "n2o_n_direct_storage_kg", "n_excreted_kg_tier2"),
        ("Manure applied to soils", "N2O", "n2o_n_direct_application_kg", "n_excreted_kg_tier2"),
        ("Manure left on pasture", "N2O", "n2o_n_direct_grazing_kg", "n_excreted_kg_tier2"),
        ("Indirect manure N", "N2O", "n2o_n_indirect_volatilization_kg", "nh3_n_total_kg"),
        ("Indirect manure N", "N2O", "n2o_n_indirect_leaching_kg", "n_leached_total_kg"),
        ("Housing", "NH3", "nh3_n_housing_kg", "n_excreted_kg_tier2"),
        ("Storage", "NH3", "nh3_n_storage_kg", "n_excreted_kg_tier2"),
        ("Manure application", "NH3", "nh3_n_application_kg", "n_excreted_kg_tier2"),
        ("Grazing", "NH3", "nh3_n_grazing_kg", "n_excreted_kg_tier2"),
        ("Housing", "NOX", "nox_n_housing_kg", "n_excreted_kg_tier2"),
        ("Storage", "NOX", "nox_n_storage_kg", "n_excreted_kg_tier2"),
        ("Manure application", "NOX", "nox_n_application_kg", "n_excreted_kg_tier2"),
        ("Grazing", "NOX", "nox_n_grazing_kg", "n_excreted_kg_tier2"),
        ("Manure N leaching/runoff", "N_LEACHING_RUNOFF", "n_leached_total_kg", "n_excreted_kg_tier2"),
        ("Manure P loss", "P_LOSS", "p_runoff_kg", "p_excreted_kg_tier2"),
        ("Manure P loss", "P_LOSS", "p_leached_kg", "p_excreted_kg_tier2"),
        ("Housing energy", "CO2", "housing_energy_co2_kg", "electricity_kwh"),
    ]
    inventory_rows: list[pd.DataFrame] = []
    for process, pollutant, value_column, activity_column in emission_specs:
        frame = work[identifiers + [value_column, activity_column, "source_id"]].copy()
        value = frame.pop(value_column)
        if pollutant == "N2O":
            value = value * N_TO_N2O
        elif pollutant == "NH3":
            value = value * N_TO_NH3
        elif pollutant == "NOX":
            value = value * N_TO_NO2
        frame["process"] = process
        frame["pollutant"] = pollutant
        frame["value"] = value
        frame["unit"] = "kg"
        frame["activity_name"] = activity_column
        frame["activity_value"] = frame.pop(activity_column)
        frame["pathway"] = value_column
        frame["activity_source"] = "authoritative_activity_ledger"
        frame["parameter_source"] = frame.pop("source_id")
        inventory_rows.append(frame)
    inventory = pd.concat(inventory_rows, ignore_index=True)
    inventory = inventory[inventory["value"].abs().gt(0.0)].reset_index(drop=True)
    diagnostics = work[
        identifiers
        + [
            "n_intake_kg",
            "n_retained_kg",
            "n_excretion_base_kg",
            "n_excreted_kg_tier2",
            "n_body_pool_change_kg",
            "n_primary_out_kg",
            "n_balance_residual_kg",
            "p_intake_kg",
            "p_retained_kg",
            "p_excretion_base_kg",
            "p_excreted_kg_tier2",
            "p_body_pool_change_kg",
            "p_primary_out_kg",
            "p_balance_residual_kg",
        ]
    ].copy()
    return Tier2EmissionsResult(inventory, work, diagnostics)


def tier2_inventory_to_gle_frames(
    inventory: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """Convert Tier 2 GHG rows to the GLE process-frame interface."""
    outputs: Dict[str, pd.DataFrame] = {}
    if inventory is None or inventory.empty:
        return outputs
    ghg = inventory[inventory["pollutant"].isin(["CH4", "N2O", "CO2"])].copy()
    standard_processes = {
        "Enteric fermentation",
        "Manure management",
        "Manure applied to soils",
        "Manure left on pasture",
    }
    ghg["process"] = ghg["process"].replace(
        {
            "Indirect manure N": "Manure management",
            "Housing energy": "Manure management",
        }
    )
    ghg = ghg[ghg["process"].isin(standard_processes)]
    for process, group in ghg.groupby("process", sort=False):
        pivot = group.pivot_table(
            index=["m49", "year", "commodity"],
            columns="pollutant",
            values="value",
            aggfunc="sum",
            fill_value=0.0,
        ).reset_index()
        for gas in ("CH4", "N2O", "CO2"):
            if gas in pivot.columns:
                gas_values = pd.to_numeric(pivot[gas], errors="coerce").fillna(0.0)
            else:
                gas_values = pd.Series(0.0, index=pivot.index)
            pivot[f"{gas}_kt"] = gas_values / 1e6
        pivot = pivot.rename(columns={"m49": "M49_Country_Code", "commodity": "Item"})
        pivot["process"] = process
        outputs[str(process)] = pivot[
            ["M49_Country_Code", "Item", "year", "process", "CH4_kt", "N2O_kt", "CO2_kt"]
        ]
    return outputs


__all__: Sequence[str] = (
    "Tier2EmissionsResult",
    "calculate_tier2_livestock_emissions",
    "load_tier2_parameters",
    "tier2_inventory_to_gle_frames",
)
