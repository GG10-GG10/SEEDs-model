# -*- coding: utf-8 -*-
"""STS thermal-stress extension shared by Module 3 and Module 4.

The expensive 5 km meteorology and AGLW livestock-grid processing is external to
the market model.  This module consumes a versioned, quality-controlled table,
turns cold/heat exposure into livestock response multipliers, and creates the
single animal-activity ledger used by feed, land, greenhouse-gas and pollutant
calculations.

No literature coefficient is hard coded here.  A run is quantitative only when
the response/activity/pollutant registries contain source-backed production
parameters.  Templates marked ``placeholder_do_not_use`` are rejected in strict
mode so that a missing parameter cannot silently become a zero effect.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


HISTORICAL_YEARS: Tuple[int, ...] = tuple(range(1960, 2021))
FUTURE_YEARS: Tuple[int, ...] = tuple(range(2030, 2081, 10))
MODEL_YEARS: Tuple[int, ...] = HISTORICAL_YEARS + FUTURE_YEARS

SUPPORTED_SPECIES: Tuple[str, ...] = (
    "dairy_cattle",
    "beef_cattle",
    "goat",
    "sheep",
    "pig",
    "poultry",
)

# Grid-level metrics emitted by STS_thermal_exposure_pipeline and eligible for
# animal-weighted country/system aggregation.  Registry-requested custom
# drivers are added to this contract explicitly by load_thermal_exposure().
STANDARD_EXPOSURE_DRIVER_COLUMNS: Tuple[str, ...] = (
    "heat_event_hours",
    "cold_event_hours",
    "heat_event_days",
    "cold_event_days",
    "longest_heat_event_hours",
    "longest_cold_event_hours",
    "nocturnal_recovery_deficit",
    "mean_thi",
    "mean_cei",
    "heat_load_p95",
    "cold_load_p95",
    "heat_load_72h_max",
    "wet_cold_hours",
)

_RESERVED_EXPOSURE_NON_DRIVER_COLUMNS = frozenset(
    {
        "grid_id",
        "m49",
        "year",
        "species",
        "production_system",
        "scenario",
        "climate_model",
        "animal_weight",
        "grid_resolution_km",
        "source_grid_cells",
        "source_hour_rows",
        "country_species_weight_fraction",
        "livestock_weight_year",
        "livestock_weight_source",
        "source_dataset_version",
        "animal_weight_relative_uncertainty",
        "weight_imputation_flag",
    }
)

PRODUCTION_ROLES: Tuple[str, ...] = ("dairy", "meat", "eggs", "all")

MULTIPLIER_IMPACTS: Tuple[str, ...] = (
    # This is the only thermal response allowed to modify the market supply
    # driver.  Per-animal production_yield_multiplier belongs to the activity
    # ledger and must not be applied to Node.Ymult a second time.
    "supply_capacity_multiplier",
    "production_yield_multiplier",
    "cycle_length_multiplier",
    "dm_intake_multiplier",
    "digestibility_multiplier",
    "maintenance_energy_multiplier",
    "replacement_multiplier",
    "direct_stock_multiplier",
    "enteric_ch4_ef_multiplier",
    "volatile_solids_multiplier",
    "manure_ch4_ef_multiplier",
    "n_excretion_multiplier",
    "p_excretion_multiplier",
    "manure_n2o_ef_multiplier",
    "housing_energy_multiplier",
)

ADDITIVE_IMPACTS: Tuple[str, ...] = ("mortality_rate_delta",)
SUPPORTED_IMPACTS = set(MULTIPLIER_IMPACTS) | set(ADDITIVE_IMPACTS)

POLLUTANT_GROUPS: Dict[str, str] = {
    "NH3": "air",
    "NOX": "air",
    "PM2.5": "air",
    "PM10": "air",
    "NMVOC": "air",
    "H2S": "air",
    "CH4": "ghg",
    "N2O": "ghg",
    "CO2": "ghg",
    "N_LEACHING_RUNOFF": "water_nutrient",
    "P_LOSS": "water_nutrient",
}

_SPECIES_ALIASES: Dict[str, str] = {
    "dairy cattle": "dairy_cattle",
    "dairy_cattle": "dairy_cattle",
    "milk cattle": "dairy_cattle",
    "beef cattle": "beef_cattle",
    "beef_cattle": "beef_cattle",
    "non-dairy cattle": "beef_cattle",
    "nondairy cattle": "beef_cattle",
    "goat": "goat",
    "goats": "goat",
    "sheep": "sheep",
    "pig": "pig",
    "pigs": "pig",
    "swine": "pig",
    "poultry": "poultry",
    "chicken": "poultry",
    "chickens": "poultry",
    "broiler": "poultry",
    "broilers": "poultry",
    "layer": "poultry",
    "layers": "poultry",
    "duck": "poultry",
    "ducks": "poultry",
    "turkey": "poultry",
    "turkeys": "poultry",
}


class ThermalStressDataError(ValueError):
    """Raised when a thermal-stress input violates the declared schema."""


@dataclass(frozen=True)
class ThermalStressSettings:
    enabled: bool = False
    target_resolution_km: float = 5.0
    resolution_tolerance_km: float = 0.25
    strict: bool = True
    future_scenario: Optional[str] = None
    climate_model: Optional[str] = None
    historical_scenario: Optional[str] = None
    historical_climate_model: Optional[str] = None
    historical_scenarios: Tuple[str, ...] = (
        "historical",
        "observed",
        "reanalysis",
    )
    historical_emissions_mode: str = "attribution_only"
    required_years: Tuple[int, ...] = MODEL_YEARS
    required_species: Tuple[str, ...] = SUPPORTED_SPECIES
    require_unique_future_selection: bool = True
    require_complete_coverage: bool = True
    require_complete_response_registry: bool = True
    require_data_manifest: bool = True
    uncertainty_draw: Optional[int] = None
    uncertainty_seed: int = 0


@dataclass
class ThermalStressBundle:
    settings: ThermalStressSettings
    exposure: pd.DataFrame
    impacts_by_system: pd.DataFrame
    impacts_model: pd.DataFrame
    commodity_map: pd.DataFrame
    commodity_impacts: pd.DataFrame
    activity_factors: pd.DataFrame = field(default_factory=pd.DataFrame)
    pollutant_factors: pd.DataFrame = field(default_factory=pd.DataFrame)
    strain: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def multiplier_lookup(self, column: str) -> Dict[Tuple[str, str, int], float]:
        """Return a model lookup keyed by (M49, Item_Emis commodity, year)."""
        if column not in self.commodity_impacts.columns:
            return {}
        rows = self.commodity_impacts[["m49", "commodity", "year", column]].copy()
        rows[column] = pd.to_numeric(rows[column], errors="coerce")
        rows = rows.dropna(subset=[column])
        key_columns = ["m49", "commodity", "year"]
        if rows.duplicated(key_columns).any():
            duplicates = rows.loc[
                rows.duplicated(key_columns, keep=False), key_columns
            ].drop_duplicates()
            raise ThermalStressDataError(
                "Thermal multiplier lookup is ambiguous; select one future "
                "scenario and climate model. Duplicate keys: "
                + repr(duplicates.head(20).to_dict(orient="records"))
            )
        return {
            (str(row.m49), str(row.commodity), int(row.year)): float(getattr(row, column))
            for row in rows.itertuples(index=False)
        }


def _read_tabular(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Thermal-stress input not found: {source}")
    suffix = source.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(source)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(source)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    raise ThermalStressDataError(
        f"Unsupported thermal-stress input format {suffix!r}: {source}"
    )


def _sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def validate_exposure_manifest(
    manifest_path: Optional[str | Path],
    *,
    exposure_path: str | Path,
    required: bool,
) -> Dict[str, Any]:
    """Validate the processed exposure checksum before a production run."""
    if manifest_path is None or not str(manifest_path).strip():
        if required:
            raise ThermalStressDataError(
                "Strict thermal run requires a versioned exposure data manifest"
            )
        return {}
    source = Path(manifest_path)
    if not source.exists():
        raise FileNotFoundError(f"Thermal exposure manifest not found: {source}")
    try:
        manifest = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ThermalStressDataError(f"Invalid thermal exposure manifest: {exc}") from exc
    if manifest.get("qc_status") != "passed":
        raise ThermalStressDataError(
            f"Thermal exposure manifest qc_status is {manifest.get('qc_status')!r}, not 'passed'"
        )
    exposure_entry = (manifest.get("files") or {}).get("exposure") or {}
    expected = str(exposure_entry.get("sha256") or "").strip().lower()
    if not expected:
        raise ThermalStressDataError("Thermal exposure manifest has no exposure sha256")
    observed = _sha256_file(exposure_path)
    if observed.lower() != expected:
        raise ThermalStressDataError(
            "Thermal exposure checksum mismatch: "
            f"manifest={expected}, observed={observed}"
        )
    return manifest


def normalize_m49(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text.startswith("'"):
        text = text[1:]
    if text.count(".") == 1:
        left, right = text.split(".", 1)
        if left.isdigit() and right.strip("0") == "":
            text = left
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    return f"'{digits.zfill(3)}"


def canonical_species(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    raw = str(value).strip().lower().replace("-", " ")
    raw = " ".join(raw.split())
    direct = _SPECIES_ALIASES.get(raw)
    if direct:
        return direct
    underscored = raw.replace(" ", "_")
    if underscored in SUPPORTED_SPECIES:
        return underscored
    return None


def validate_model_years(years: Iterable[Any]) -> List[int]:
    parsed: List[int] = []
    invalid: List[Any] = []
    for raw in years:
        try:
            year = int(raw)
        except (TypeError, ValueError):
            invalid.append(raw)
            continue
        if year not in MODEL_YEARS:
            invalid.append(raw)
        else:
            parsed.append(year)
    if invalid:
        raise ThermalStressDataError(
            "Years outside 1960-2020 historical or 2030-2080 decadal scope: "
            + ", ".join(map(str, invalid[:20]))
        )
    return sorted(set(parsed))


def _require_columns(df: pd.DataFrame, required: Sequence[str], label: str) -> None:
    missing = [name for name in required if name not in df.columns]
    if missing:
        raise ThermalStressDataError(f"{label} missing required columns: {missing}")


def _weighted_mean(group: pd.DataFrame, column: str, weight_col: str) -> float:
    values = pd.to_numeric(group[column], errors="coerce")
    weights = pd.to_numeric(group[weight_col], errors="coerce").fillna(0.0)
    valid = values.notna() & weights.gt(0.0)
    if not valid.any():
        return float("nan")
    return float(np.average(values.loc[valid], weights=weights.loc[valid]))


def _normalize_requested_exposure_drivers(
    required_driver_columns: Optional[Iterable[str]],
) -> Tuple[str, ...]:
    if required_driver_columns is None:
        return ()
    raw_names: Iterable[str]
    if isinstance(required_driver_columns, str):
        raw_names = (required_driver_columns,)
    else:
        raw_names = required_driver_columns
    names = tuple(str(name).strip() for name in raw_names)
    if any(not name for name in names):
        raise ThermalStressDataError(
            "Requested exposure driver names must not be blank"
        )
    reserved = sorted(set(names) & _RESERVED_EXPOSURE_NON_DRIVER_COLUMNS)
    if reserved:
        raise ThermalStressDataError(
            "Requested exposure drivers use reserved non-driver columns: "
            + ", ".join(reserved)
        )
    return tuple(sorted(set(names)))


def load_thermal_exposure(
    path: str | Path,
    settings: ThermalStressSettings,
    *,
    target_years: Optional[Iterable[int]] = None,
    required_driver_columns: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Load and aggregate externally prepared 5 km exposure.

    The table may contain one row per 5 km cell or may already be aggregated.
    ``animal_weight`` must represent AGLW heads, head-equivalents, or a set of
    weights proportional to heads.  Strict runs also require the weight vintage,
    source/version, an indicative relative uncertainty, and an imputation flag.
    Non-linear heat/cold indices must already have been computed at grid level;
    this function only performs animal-weighted aggregation.  Standard pipeline
    metrics are retained when present.  Additional response/strain drivers must
    be named in ``required_driver_columns`` and must be finite numeric columns.
    """
    df = _read_tabular(path)
    df.columns = [str(c).strip() for c in df.columns]
    _require_columns(
        df,
        [
            "m49",
            "year",
            "species",
            "heat_load",
            "cold_load",
            "animal_weight",
            "grid_resolution_km",
        ],
        "thermal exposure",
    )
    provenance_columns = [
        "livestock_weight_year",
        "livestock_weight_source",
        "source_dataset_version",
        "animal_weight_relative_uncertainty",
        "weight_imputation_flag",
    ]
    if settings.strict:
        _require_columns(df, provenance_columns, "thermal exposure provenance")

    requested_drivers = _normalize_requested_exposure_drivers(
        required_driver_columns
    )
    missing_requested = sorted(set(requested_drivers) - set(df.columns))
    if missing_requested:
        raise ThermalStressDataError(
            "Requested exposure drivers are absent from thermal exposure: "
            + ", ".join(missing_requested)
        )
    driver_columns = list(
        dict.fromkeys(
            [
                "heat_load",
                "cold_load",
                *(
                    name
                    for name in STANDARD_EXPOSURE_DRIVER_COLUMNS
                    if name in df.columns
                ),
                *requested_drivers,
            ]
        )
    )

    df = df.copy()
    df["m49"] = df["m49"].map(normalize_m49)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["species"] = df["species"].map(canonical_species)
    df["animal_weight"] = pd.to_numeric(df["animal_weight"], errors="coerce")
    df["grid_resolution_km"] = pd.to_numeric(
        df["grid_resolution_km"], errors="coerce"
    )
    for column in driver_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if "livestock_weight_year" in df.columns:
        df["livestock_weight_year"] = pd.to_numeric(
            df["livestock_weight_year"], errors="coerce"
        )
    if "animal_weight_relative_uncertainty" in df.columns:
        df["animal_weight_relative_uncertainty"] = pd.to_numeric(
            df["animal_weight_relative_uncertainty"], errors="coerce"
        )

    bad_species = int(df["species"].isna().sum())
    if bad_species:
        examples = df.loc[df["species"].isna(), "species"].head(10).tolist()
        raise ThermalStressDataError(
            f"Exposure contains {bad_species} unsupported species rows: {examples}"
        )
    if df["m49"].isna().any():
        raise ThermalStressDataError("Exposure contains missing or invalid M49 codes")
    if df["year"].isna().any():
        raise ThermalStressDataError("Exposure contains non-numeric years")
    df["year"] = df["year"].astype(int)
    validate_model_years(df["year"].unique())

    resolution_delta = (df["grid_resolution_km"] - settings.target_resolution_km).abs()
    bad_resolution = resolution_delta.gt(settings.resolution_tolerance_km) | resolution_delta.isna()
    if bad_resolution.any():
        values = sorted(df.loc[bad_resolution, "grid_resolution_km"].dropna().unique())
        raise ThermalStressDataError(
            "Exposure is not consistently 5 km within tolerance; observed values="
            f"{values[:20]}"
        )
    if not np.isfinite(df["animal_weight"].to_numpy(dtype=float)).all() or (
        df["animal_weight"] < 0
    ).any():
        raise ThermalStressDataError("animal_weight must be finite and non-negative")
    if not np.isfinite(df[driver_columns].to_numpy(dtype=float)).all():
        raise ThermalStressDataError(
            "Every selected exposure driver must contain finite numeric values"
        )
    if (df[["heat_load", "cold_load"]] < 0).any().any():
        raise ThermalStressDataError("heat_load and cold_load must be non-negative")

    present_provenance = [column for column in provenance_columns if column in df.columns]
    if present_provenance:
        if "livestock_weight_year" in df.columns:
            if df["livestock_weight_year"].isna().any():
                raise ThermalStressDataError("livestock_weight_year must be numeric")
            df["livestock_weight_year"] = df["livestock_weight_year"].astype(int)
        if "animal_weight_relative_uncertainty" in df.columns:
            uncertainty = df["animal_weight_relative_uncertainty"]
            if uncertainty.isna().any() or (uncertainty < 0).any():
                raise ThermalStressDataError(
                    "animal_weight_relative_uncertainty must be finite and non-negative"
                )
        for column in (
            "livestock_weight_source",
            "source_dataset_version",
            "weight_imputation_flag",
        ):
            if column in df.columns:
                df[column] = df[column].fillna("").astype(str).str.strip()
                if df[column].eq("").any():
                    raise ThermalStressDataError(f"{column} must not be blank")

        if settings.strict and "livestock_weight_year" in df.columns:
            rows_1960 = df["year"].eq(1960)
            bad_weight_year = rows_1960 & ~df["livestock_weight_year"].eq(1961)
            if bad_weight_year.any():
                raise ThermalStressDataError(
                    "1960 exposure must explicitly backcast the 1961 AGLW weight year"
                )
            if rows_1960.any() and "weight_imputation_flag" in df.columns:
                flags_1960 = df.loc[rows_1960, "weight_imputation_flag"].str.lower()
                if ~flags_1960.str.contains("backcast_1961_to_1960", regex=False).all():
                    raise ThermalStressDataError(
                        "1960 exposure must use weight_imputation_flag="
                        "backcast_1961_to_1960"
                    )

    if "production_system" not in df.columns:
        df["production_system"] = "all"
    if "scenario" not in df.columns:
        df["scenario"] = "historical"
    if "climate_model" not in df.columns:
        df["climate_model"] = "unspecified"
    df["production_system"] = (
        df["production_system"].fillna("all").astype(str).str.strip().str.lower()
    )
    df["scenario"] = df["scenario"].fillna("historical").astype(str).str.strip()
    df["climate_model"] = (
        df["climate_model"].fillna("unspecified").astype(str).str.strip()
    )
    if "grid_id" not in df.columns:
        df["grid_id"] = np.arange(len(df), dtype=np.int64).astype(str)

    if target_years is not None:
        allowed = set(validate_model_years(target_years))
        df = df[df["year"].isin(allowed)].copy()

    future_rows = df["year"].gt(2020)
    if settings.strict and settings.require_unique_future_selection and future_rows.any():
        future_scenarios = sorted(
            {str(value).strip() for value in df.loc[future_rows, "scenario"].dropna()}
        )
        future_models = sorted(
            {str(value).strip() for value in df.loc[future_rows, "climate_model"].dropna()}
        )
        if not settings.future_scenario and len(future_scenarios) != 1:
            raise ThermalStressDataError(
                "Strict thermal run requires one explicit future_scenario when "
                f"the exposure contains {future_scenarios}"
            )
        if not settings.climate_model and len(future_models) != 1:
            raise ThermalStressDataError(
                "Strict thermal run requires one explicit climate_model when "
                f"the exposure contains {future_models}"
            )

    historical_allowed = {item.lower() for item in settings.historical_scenarios}
    if settings.future_scenario:
        future_scenario = settings.future_scenario.strip().lower()
        scenario_lower = df["scenario"].str.lower()
        keep = np.where(
            df["year"].le(2020),
            scenario_lower.isin(historical_allowed),
            scenario_lower.eq(future_scenario),
        )
        df = df.loc[keep].copy()
    if settings.climate_model:
        model_lower = settings.climate_model.strip().lower()
        climate_lower = df["climate_model"].str.lower()
        keep = df["year"].le(2020) | climate_lower.eq(model_lower)
        df = df.loc[keep].copy()

    # Historical rows also belong to ensemble members.  Keeping every
    # historical GCM while selecting one future GCM creates duplicate business
    # keys and, worse, averages unrelated members downstream.  Resolve exactly
    # one historical scenario/model, preferring an explicitly requested member
    # and then the selected future model when it is available.
    historical = df["year"].le(2020)
    if historical.any():
        hist = df.loc[historical].copy()
        scenario_values = sorted(hist["scenario"].dropna().astype(str).unique())
        if settings.historical_scenario:
            selected_hist_scenario = str(settings.historical_scenario).strip()
            if selected_hist_scenario.lower() not in {
                value.lower() for value in scenario_values
            }:
                raise ThermalStressDataError(
                    "Requested historical_scenario is absent from exposure: "
                    f"{selected_hist_scenario!r}; available={scenario_values!r}"
                )
        elif len(scenario_values) == 1:
            selected_hist_scenario = scenario_values[0]
        elif settings.strict:
            raise ThermalStressDataError(
                "Strict thermal run requires one historical_scenario when "
                f"multiple historical members are present: {scenario_values!r}"
            )
        else:
            preferred = [
                value for value in scenario_values if value.lower() == "historical"
            ]
            selected_hist_scenario = preferred[0] if preferred else scenario_values[0]
        hist = hist[
            hist["scenario"].str.lower().eq(selected_hist_scenario.lower())
        ].copy()

        model_values = sorted(hist["climate_model"].dropna().astype(str).unique())
        if settings.historical_climate_model:
            selected_hist_model = str(settings.historical_climate_model).strip()
            if selected_hist_model.lower() not in {
                value.lower() for value in model_values
            }:
                raise ThermalStressDataError(
                    "Requested historical_climate_model is absent from exposure: "
                    f"{selected_hist_model!r}; available={model_values!r}"
                )
        elif settings.climate_model and str(settings.climate_model).strip().lower() in {
            value.lower() for value in model_values
        }:
            selected_hist_model = str(settings.climate_model).strip()
        elif len(model_values) == 1:
            selected_hist_model = model_values[0]
        elif settings.strict:
            raise ThermalStressDataError(
                "Strict thermal run requires one historical_climate_model when "
                f"multiple historical members are present: {model_values!r}"
            )
        else:
            selected_hist_model = model_values[0]
        hist = hist[
            hist["climate_model"].str.lower().eq(selected_hist_model.lower())
        ].copy()
        df = pd.concat([hist, df.loc[~historical]], ignore_index=True)

    if df.empty:
        raise ThermalStressDataError("Exposure is empty after year/scenario/model filtering")
    if target_years is not None and settings.strict:
        required_years = set(validate_model_years(target_years))
        missing_years = sorted(required_years - set(df["year"].unique()))
        if missing_years:
            raise ThermalStressDataError(
                "Exposure is missing required model years after filtering: "
                + ", ".join(map(str, missing_years))
            )
        if settings.require_complete_coverage:
            required_species = {
                canonical_species(item) for item in settings.required_species
            }
            required_species.discard(None)
            missing_species = sorted(required_species - set(df["species"].unique()))
            if missing_species:
                raise ThermalStressDataError(
                    "Exposure is missing required species after filtering: "
                    + ", ".join(missing_species)
                )
            incomplete: List[Dict[str, Any]] = []
            coverage_keys = ["m49", "species", "production_system"]
            coverage_frame = df[df["species"].isin(required_species)]
            countries = sorted(coverage_frame["m49"].dropna().unique())
            species_years = {
                (m49, species): set(group["year"].astype(int))
                for (m49, species), group in coverage_frame.groupby(
                    ["m49", "species"], dropna=False, sort=False
                )
            }
            for m49 in countries:
                for species in sorted(required_species):
                    missing = sorted(
                        required_years - species_years.get((m49, species), set())
                    )
                    if missing:
                        incomplete.append(
                            {
                                "m49": m49,
                                "species": species,
                                "production_system": "<any>",
                                "missing_years": missing,
                            }
                        )
                        if len(incomplete) >= 20:
                            break
                if len(incomplete) >= 20:
                    break
            if len(incomplete) < 20:
                for key, group in coverage_frame.groupby(
                    coverage_keys, dropna=False, sort=False
                ):
                    missing = sorted(required_years - set(group["year"].astype(int)))
                    if missing:
                        incomplete.append(
                            {
                                **dict(zip(coverage_keys, key)),
                                "missing_years": missing,
                            }
                        )
                        if len(incomplete) >= 20:
                            break
            if incomplete:
                raise ThermalStressDataError(
                    "Exposure has incomplete country/species/system year coverage: "
                    + repr(incomplete)
                )

    keys = [
        "m49",
        "year",
        "species",
        "production_system",
        "scenario",
        "climate_model",
    ]
    rows: List[Dict[str, Any]] = []
    extra_exposure_cols = [
        name for name in driver_columns if name not in {"heat_load", "cold_load"}
    ]
    for key, group in df.groupby(keys, dropna=False, sort=False):
        weight_sum = float(group["animal_weight"].sum())
        if weight_sum <= 0:
            if settings.strict:
                raise ThermalStressDataError(f"Exposure group has zero animal weight: {key}")
            continue
        row = dict(zip(keys, key))
        row.update(
            {
                "animal_weight": weight_sum,
                "heat_load": _weighted_mean(group, "heat_load", "animal_weight"),
                "cold_load": _weighted_mean(group, "cold_load", "animal_weight"),
                "source_grid_cells": int(group["grid_id"].nunique()),
                "grid_resolution_km": float(settings.target_resolution_km),
            }
        )
        for column in extra_exposure_cols:
            row[column] = _weighted_mean(group, column, "animal_weight")
        if "animal_weight_relative_uncertainty" in group.columns:
            # This is a traceable weighted summary, not a claim that pixel errors
            # are independent or a replacement for ensemble uncertainty runs.
            row["animal_weight_relative_uncertainty"] = _weighted_mean(
                group, "animal_weight_relative_uncertainty", "animal_weight"
            )
        for column in (
            "livestock_weight_year",
            "livestock_weight_source",
            "source_dataset_version",
            "weight_imputation_flag",
        ):
            if column not in group.columns:
                continue
            values = [str(value) for value in group[column].dropna().unique()]
            if settings.strict and len(values) != 1:
                raise ThermalStressDataError(
                    f"Exposure group mixes {column} values: {key} -> {values[:10]}"
                )
            if column == "livestock_weight_year" and len(values) == 1:
                row[column] = int(float(values[0]))
            else:
                row[column] = "|".join(sorted(values))
        rows.append(row)

    out = pd.DataFrame(rows)
    if not np.isfinite(out[driver_columns].to_numpy(dtype=float)).all():
        raise ThermalStressDataError(
            "Exposure aggregation produced a non-finite selected driver"
        )
    return out.sort_values(keys).reset_index(drop=True)


def load_response_registry(
    path: str | Path,
    *,
    strict: bool = True,
    uncertainty_draw: Optional[int] = None,
    uncertainty_seed: int = 0,
) -> pd.DataFrame:
    df = _read_tabular(path)
    df.columns = [str(c).strip() for c in df.columns]
    _require_columns(
        df,
        [
            "species",
            "production_role",
            "production_system",
            "impact",
            "response_form",
            "heat_coefficient",
            "cold_coefficient",
            "heat_load_scale",
            "cold_load_scale",
            "lower_bound",
            "upper_bound",
            "source_id",
            "parameter_status",
        ],
        "thermal response registry",
    )
    df = df.copy()
    df["species"] = df["species"].map(canonical_species)
    if df["species"].isna().any():
        raise ThermalStressDataError("Response registry contains unsupported species")
    df["production_role"] = df["production_role"].fillna("all").astype(str).str.lower().str.strip()
    if not set(df["production_role"]).issubset(PRODUCTION_ROLES):
        bad = sorted(set(df["production_role"]) - set(PRODUCTION_ROLES))
        raise ThermalStressDataError(f"Unsupported production roles: {bad}")
    df["production_system"] = df["production_system"].fillna("all").astype(str).str.lower().str.strip()
    df["impact"] = df["impact"].astype(str).str.strip()
    bad_impacts = sorted(set(df["impact"]) - SUPPORTED_IMPACTS)
    if bad_impacts:
        raise ThermalStressDataError(f"Unsupported thermal impacts: {bad_impacts}")

    allowed_forms = {"linear_multiplier", "exponential_multiplier", "additive_rate"}
    df["response_form"] = df["response_form"].astype(str).str.lower().str.strip()
    if not set(df["response_form"]).issubset(allowed_forms):
        bad = sorted(set(df["response_form"]) - allowed_forms)
        raise ThermalStressDataError(f"Unsupported response forms: {bad}")
    invalid_additive = df["impact"].isin(ADDITIVE_IMPACTS) & ~df[
        "response_form"
    ].eq("additive_rate")
    invalid_multiplier = df["impact"].isin(MULTIPLIER_IMPACTS) & df[
        "response_form"
    ].eq("additive_rate")
    if invalid_additive.any() or invalid_multiplier.any():
        invalid = df.loc[
            invalid_additive | invalid_multiplier,
            ["impact", "response_form"],
        ].drop_duplicates()
        raise ThermalStressDataError(
            "Response form is incompatible with impact semantics: "
            + repr(invalid.to_dict(orient="records"))
        )

    numeric_cols = [
        "heat_coefficient",
        "cold_coefficient",
        "heat_load_scale",
        "cold_load_scale",
        "lower_bound",
        "upper_bound",
    ]
    if "intercept" not in df.columns:
        df["intercept"] = np.nan
    numeric_cols.append("intercept")
    for column in numeric_cols:
        raw = df[column]
        converted = pd.to_numeric(raw, errors="coerce")
        supplied = raw.notna() & raw.astype(str).str.strip().ne("")
        if (supplied & converted.isna()).any():
            raise ThermalStressDataError(
                f"Response {column} contains non-numeric values"
            )
        df[column] = converted
    required_numeric = [
        "heat_coefficient",
        "cold_coefficient",
        "heat_load_scale",
        "cold_load_scale",
    ]
    required_values = df[required_numeric].to_numpy(dtype=float)
    if not np.isfinite(required_values).all():
        raise ThermalStressDataError(
            "Response coefficients and load scales must be finite"
        )
    for column in ("lower_bound", "upper_bound", "intercept"):
        present = df[column].dropna().to_numpy(dtype=float)
        if not np.isfinite(present).all():
            raise ThermalStressDataError(
                f"Response {column} must be finite when provided"
            )
    if (df[["heat_load_scale", "cold_load_scale"]] <= 0).any().any():
        raise ThermalStressDataError("Response heat/cold load scales must be positive")
    bounded = df["lower_bound"].notna() & df["upper_bound"].notna()
    if (df.loc[bounded, "lower_bound"] > df.loc[bounded, "upper_bound"]).any():
        raise ThermalStressDataError(
            "Response lower_bound must not exceed upper_bound"
        )

    status = df["parameter_status"].fillna("").astype(str).str.lower().str.strip()
    placeholders = ~status.eq("production")
    if strict and placeholders.any():
        sources = sorted(df.loc[placeholders, "source_id"].astype(str).unique())
        raise ThermalStressDataError(
            "Response registry contains non-production parameters: " + ", ".join(sources[:20])
        )
    df = df.loc[~placeholders].copy()
    if df.empty:
        raise ThermalStressDataError("No production-ready thermal response parameters remain")

    duplicate_cols = ["species", "production_role", "production_system", "impact"]
    if df.duplicated(duplicate_cols).any():
        duplicates = df.loc[df.duplicated(duplicate_cols, keep=False), duplicate_cols]
        raise ThermalStressDataError(
            "Duplicate thermal response definitions: "
            + duplicates.drop_duplicates().head(20).to_dict(orient="records").__repr__()
        )
    for column, default in (
        ("heat_driver", "heat_load"),
        ("cold_driver", "cold_load"),
    ):
        if column not in df.columns:
            df[column] = default
        df[column] = df[column].fillna(default).astype(str).str.strip()
        if df[column].eq("").any():
            raise ThermalStressDataError(f"Response {column} must not be blank")
    uncertainty_columns = (
        "intercept_sd",
        "heat_coefficient_sd",
        "cold_coefficient_sd",
    )
    for column in uncertainty_columns:
        if column not in df.columns:
            df[column] = 0.0
        raw = df[column]
        converted = pd.to_numeric(raw, errors="coerce")
        supplied = raw.notna() & raw.astype(str).str.strip().ne("")
        if (supplied & converted.isna()).any():
            raise ThermalStressDataError(
                f"Response {column} contains non-numeric values"
            )
        df[column] = converted.fillna(0.0)
        if not np.isfinite(df[column].to_numpy(dtype=float)).all() or (
            df[column] < 0.0
        ).any():
            raise ThermalStressDataError(
                f"Response {column} must be finite and non-negative"
            )
    if uncertainty_draw is not None:
        draw = int(uncertainty_draw)
        rng = np.random.default_rng(int(uncertainty_seed) + draw)
        for coefficient, sd_column in (
            ("intercept", "intercept_sd"),
            ("heat_coefficient", "heat_coefficient_sd"),
            ("cold_coefficient", "cold_coefficient_sd"),
        ):
            mean = pd.to_numeric(df[coefficient], errors="coerce")
            sampled = rng.normal(mean.fillna(0.0), df[sd_column])
            if coefficient == "intercept":
                sampled = np.where(mean.isna(), np.nan, sampled)
            df[f"{coefficient}_mean"] = mean
            df[coefficient] = sampled
        df["uncertainty_draw"] = draw
    return df.reset_index(drop=True)


def load_strain_registry(
    path: Optional[str | Path], *, strict: bool = True
) -> pd.DataFrame:
    """Load optional hazard-to-animal-strain transformations."""
    df = _load_optional_registry(path, "Thermal strain registry")
    if df.empty:
        return df
    required = [
        "species",
        "production_system",
        "strain_name",
        "heat_driver",
        "cold_driver",
        "intercept",
        "heat_coefficient",
        "cold_coefficient",
        "heat_load_scale",
        "cold_load_scale",
        "lower_bound",
        "upper_bound",
        "source_id",
        "parameter_status",
    ]
    _require_columns(df, required, "thermal strain registry")
    df = df.copy()
    df["species"] = df["species"].map(canonical_species)
    if df["species"].isna().any():
        raise ThermalStressDataError("Strain registry contains unsupported species")
    for column in ("production_system", "strain_name", "heat_driver", "cold_driver"):
        df[column] = df[column].fillna("").astype(str).str.strip()
        if df[column].eq("").any():
            raise ThermalStressDataError(f"Strain registry {column} must not be blank")
    numeric = [
        "intercept",
        "heat_coefficient",
        "cold_coefficient",
        "heat_load_scale",
        "cold_load_scale",
        "lower_bound",
        "upper_bound",
    ]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if df[numeric].isna().any().any():
        raise ThermalStressDataError("Strain registry numeric fields must be finite")
    if (df[["heat_load_scale", "cold_load_scale"]] <= 0.0).any().any():
        raise ThermalStressDataError("Strain load scales must be positive")
    status = df["parameter_status"].fillna("").astype(str).str.lower().str.strip()
    if strict and (~status.eq("production")).any():
        raise ThermalStressDataError("Strain registry contains non-production rows")
    df = df.loc[status.eq("production")].copy()
    duplicate = ["species", "production_system", "strain_name"]
    if df.duplicated(duplicate).any():
        raise ThermalStressDataError("Strain registry contains duplicate definitions")
    return df.reset_index(drop=True)


def _driver_values(rows: pd.DataFrame, driver_column: str) -> np.ndarray:
    values = np.full(len(rows), np.nan, dtype=float)
    for driver in rows[driver_column].astype(str).unique():
        if driver not in rows.columns:
            raise ThermalStressDataError(
                f"Response/strain driver {driver!r} is absent from exposure"
            )
        mask = rows[driver_column].eq(driver)
        values[mask.to_numpy()] = pd.to_numeric(
            rows.loc[mask, driver], errors="coerce"
        ).to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ThermalStressDataError(f"Driver selected by {driver_column} is non-finite")
    return values


def calculate_thermal_strain(
    exposure: pd.DataFrame,
    strain_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Create explicit animal-strain metrics from environmental hazards."""
    if strain_registry is None or strain_registry.empty:
        return exposure.copy()
    left = exposure.reset_index(drop=True).copy()
    left["_strain_exposure_id"] = np.arange(len(left), dtype=np.int64)
    right = strain_registry.rename(columns={"production_system": "strain_system"})
    joined = left.merge(right, on="species", how="left", validate="many_to_many")
    matched = joined[
        joined["strain_system"].eq("all")
        | joined["strain_system"].eq(joined["production_system"])
    ].copy()
    matched["_system_rank"] = np.where(matched["strain_system"].eq("all"), 1, 0)
    matched = matched.sort_values(["_strain_exposure_id", "strain_name", "_system_rank"])
    matched = matched.drop_duplicates(["_strain_exposure_id", "strain_name"], keep="first")
    if matched.empty or matched["strain_name"].isna().any():
        raise ThermalStressDataError("No strain definitions matched exposure systems")
    heat = _driver_values(matched, "heat_driver") / matched["heat_load_scale"].to_numpy(float)
    cold = _driver_values(matched, "cold_driver") / matched["cold_load_scale"].to_numpy(float)
    raw = (
        matched["intercept"].to_numpy(float)
        + matched["heat_coefficient"].to_numpy(float) * heat
        + matched["cold_coefficient"].to_numpy(float) * cold
    )
    matched["strain_value_raw"] = raw
    matched["strain_value"] = np.clip(
        raw,
        matched["lower_bound"].to_numpy(float),
        matched["upper_bound"].to_numpy(float),
    )
    matched["strain_clipped"] = ~np.isclose(
        matched["strain_value_raw"], matched["strain_value"]
    )
    wide = matched.pivot(
        index="_strain_exposure_id", columns="strain_name", values="strain_value"
    )
    wide.columns = [str(column) for column in wide.columns]
    out = left.merge(wide.reset_index(), on="_strain_exposure_id", how="left")
    return out.drop(columns=["_strain_exposure_id"])


def _match_response_rows(
    exposure: pd.DataFrame,
    response_registry: pd.DataFrame,
    *,
    commodity_map: Optional[pd.DataFrame] = None,
    require_complete: bool = False,
) -> pd.DataFrame:
    """Resolve role/system response overrides for every exposure row.

    ``production_role=all`` and ``production_system=all`` are independent
    fallbacks.  An exact role takes precedence over ``all`` and, within that
    role, an exact production system takes precedence over ``all``.  Resolving
    both dimensions before pivoting prevents a missing response from being
    silently converted to an identity multiplier.
    """
    left = exposure.reset_index(drop=True).copy()
    left["_exposure_id"] = np.arange(len(left), dtype=np.int64)
    if commodity_map is not None:
        roles = commodity_map[["species", "production_role"]].drop_duplicates()
    else:
        roles = response_registry.loc[
            ~response_registry["production_role"].astype(str).str.lower().eq("all"),
            ["species", "production_role"],
        ].drop_duplicates()
        if roles.empty:
            roles = response_registry[["species"]].drop_duplicates()
            roles["production_role"] = "all"
    desired = left.merge(roles, on="species", how="left", validate="many_to_many")
    if desired["production_role"].isna().any():
        species = sorted(
            desired.loc[desired["production_role"].isna(), "species"].unique()
        )
        raise ThermalStressDataError(
            f"No production roles are defined for exposure species: {species}"
        )

    right = response_registry.rename(
        columns={
            "production_role": "response_role",
            "production_system": "response_system",
        }
    ).copy()
    joined = desired.merge(right, on="species", how="left", validate="many_to_many")
    candidates = joined[
        joined["response_role"].isin(["all"])
        | joined["response_role"].eq(joined["production_role"])
    ].copy()
    candidates = candidates[
        candidates["response_system"].eq("all")
        | candidates["response_system"].eq(candidates["production_system"])
    ].copy()
    candidates["_role_rank"] = np.where(
        candidates["response_role"].eq(candidates["production_role"]), 0, 1
    )
    candidates["_system_rank"] = np.where(
        candidates["response_system"].eq(candidates["production_system"]), 0, 1
    )
    resolution_key = ["_exposure_id", "production_role", "impact"]
    candidates = candidates.sort_values(resolution_key + ["_role_rank", "_system_rank"])
    tied = candidates.duplicated(
        resolution_key + ["_role_rank", "_system_rank"], keep=False
    )
    if tied.any():
        ambiguous = candidates.loc[
            tied,
            resolution_key
            + ["species", "production_system", "response_role", "response_system"],
        ].drop_duplicates()
        raise ThermalStressDataError(
            "Response registry has ambiguous equal-priority overrides: "
            + repr(ambiguous.head(20).to_dict(orient="records"))
        )
    selected = candidates.drop_duplicates(resolution_key, keep="first")

    if require_complete:
        required = pd.DataFrame({"impact": list(SUPPORTED_IMPACTS)})
        expected = desired.assign(_join=1).merge(
            required.assign(_join=1), on="_join", how="inner"
        ).drop(columns="_join")
    else:
        available = response_registry[["species", "impact"]].drop_duplicates()
        expected = desired.merge(available, on="species", how="left")
    resolved = selected[resolution_key].drop_duplicates()
    missing = expected.merge(
        resolved,
        on=resolution_key,
        how="left",
        indicator=True,
    )
    missing = missing[missing["_merge"].eq("left_only")]
    if not missing.empty:
        columns = [
            column
            for column in (
                "m49",
                "year",
                "species",
                "production_role",
                "production_system",
                "scenario",
                "climate_model",
                "impact",
            )
            if column in missing.columns
        ]
        raise ThermalStressDataError(
            "Strict response registry is incomplete; it does not cover every "
            "exposure/role/system/impact: "
            + repr(missing[columns].head(20).to_dict(orient="records"))
        )
    return selected


def validate_response_registry_coverage(
    response_registry: pd.DataFrame,
    commodity_map: pd.DataFrame,
    *,
    settings: ThermalStressSettings,
    exposure: Optional[pd.DataFrame] = None,
) -> None:
    """Require explicit response rows, including intentional identity effects.

    Strict production runs cannot infer whether an absent row means "no effect"
    or "not yet parameterised".  Requiring every supported impact makes that
    distinction auditable; focused development tests may opt out explicitly.
    """
    if not settings.strict or not settings.require_complete_response_registry:
        return
    required_species = {
        canonical_species(item) for item in settings.required_species
    }
    required_species.discard(None)
    missing_map_species = sorted(required_species - set(commodity_map["species"]))
    if missing_map_species:
        raise ThermalStressDataError(
            "Commodity map is missing required thermal species: "
            + ", ".join(missing_map_species)
        )
    if exposure is None:
        raise ThermalStressDataError(
            "Strict response coverage validation requires exposure systems"
        )
    _match_response_rows(
        exposure,
        response_registry,
        commodity_map=commodity_map[commodity_map["species"].isin(required_species)],
        require_complete=True,
    )


def _calculate_response_value(rows: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    heat = _driver_values(rows, "heat_driver") / rows["heat_load_scale"].to_numpy(dtype=float)
    cold = _driver_values(rows, "cold_driver") / rows["cold_load_scale"].to_numpy(dtype=float)
    effect = (
        rows["heat_coefficient"].to_numpy(dtype=float) * heat
        + rows["cold_coefficient"].to_numpy(dtype=float) * cold
    )
    forms = rows["response_form"].astype(str).to_numpy()
    intercept = rows["intercept"].to_numpy(dtype=float)
    multiplier_default = np.where(np.isnan(intercept), 1.0, intercept)
    additive_default = np.where(np.isnan(intercept), 0.0, intercept)
    values = np.empty(len(rows), dtype=float)
    linear = forms == "linear_multiplier"
    exponential = forms == "exponential_multiplier"
    additive = forms == "additive_rate"
    values[linear] = multiplier_default[linear] + effect[linear]
    values[exponential] = multiplier_default[exponential] * np.exp(effect[exponential])
    values[additive] = additive_default[additive] + effect[additive]
    lower = rows["lower_bound"].to_numpy(dtype=float)
    upper = rows["upper_bound"].to_numpy(dtype=float)
    lower = np.where(np.isnan(lower), -np.inf, lower)
    upper = np.where(np.isnan(upper), np.inf, upper)
    return values, np.clip(values, lower, upper)


def calculate_thermal_impacts(
    exposure: pd.DataFrame,
    response_registry: pd.DataFrame,
    *,
    commodity_map: Optional[pd.DataFrame] = None,
    require_complete_response: bool = False,
) -> pd.DataFrame:
    """Calculate hazard -> strain -> impact multipliers by production system."""
    matches = _match_response_rows(
        exposure,
        response_registry,
        commodity_map=commodity_map,
        require_complete=require_complete_response,
    )
    if matches.empty:
        raise ThermalStressDataError("No production-system response rows matched exposure")
    matches["response_value_raw"], matches["response_value"] = _calculate_response_value(matches)
    matches["response_clipped"] = ~np.isclose(
        matches["response_value_raw"], matches["response_value"]
    )

    index_cols = [
        "_exposure_id",
        "m49",
        "year",
        "species",
        "production_role",
        "production_system",
        "scenario",
        "climate_model",
        "animal_weight",
        "source_grid_cells",
        "grid_resolution_km",
        "heat_load",
        "cold_load",
    ]
    provenance_columns = [
        "livestock_weight_year",
        "livestock_weight_source",
        "source_dataset_version",
        "animal_weight_relative_uncertainty",
        "weight_imputation_flag",
    ]
    index_cols.extend([column for column in provenance_columns if column in matches.columns])
    pivot = matches.pivot_table(
        index=index_cols,
        columns="impact",
        values="response_value",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    raw_pivot = matches.pivot_table(
        index=index_cols,
        columns="impact",
        values="response_value_raw",
        aggfunc="first",
    ).reset_index()
    raw_pivot.columns.name = None
    raw_pivot = raw_pivot.rename(
        columns={impact: f"{impact}_raw" for impact in SUPPORTED_IMPACTS}
    )
    clipped_pivot = matches.pivot_table(
        index=index_cols,
        columns="impact",
        values="response_clipped",
        aggfunc="max",
    ).reset_index()
    clipped_pivot.columns.name = None
    clipped_pivot = clipped_pivot.rename(
        columns={impact: f"{impact}_clipped" for impact in SUPPORTED_IMPACTS}
    )
    pivot = pivot.merge(raw_pivot, on=index_cols, how="left", validate="one_to_one")
    pivot = pivot.merge(clipped_pivot, on=index_cols, how="left", validate="one_to_one")
    for column in MULTIPLIER_IMPACTS:
        if column not in pivot.columns:
            if require_complete_response:
                raise ThermalStressDataError(
                    f"Strict response resolution omitted required impact {column!r}"
                )
            pivot[column] = 1.0
        values = pd.to_numeric(pivot[column], errors="coerce")
        if require_complete_response and values.isna().any():
            raise ThermalStressDataError(f"Strict response impact {column!r} is non-finite")
        pivot[column] = values.fillna(1.0)
    for column in ADDITIVE_IMPACTS:
        if column not in pivot.columns:
            if require_complete_response:
                raise ThermalStressDataError(
                    f"Strict response resolution omitted required impact {column!r}"
                )
            pivot[column] = 0.0
        values = pd.to_numeric(pivot[column], errors="coerce")
        if require_complete_response and values.isna().any():
            raise ThermalStressDataError(f"Strict response impact {column!r} is non-finite")
        pivot[column] = values.fillna(0.0)

    pivot = recalculate_activity_multipliers(pivot)
    return pivot.drop(columns=["_exposure_id"]).sort_values(
        ["year", "m49", "species", "production_role", "production_system"]
    ).reset_index(drop=True)


def recalculate_activity_multipliers(impacts: pd.DataFrame) -> pd.DataFrame:
    """Rebuild all derived activity totals after response/adaptation changes."""
    pivot = impacts.copy()
    for column in MULTIPLIER_IMPACTS:
        if column not in pivot.columns:
            pivot[column] = 1.0
        pivot[column] = pd.to_numeric(pivot[column], errors="coerce").fillna(1.0)
    for column in ADDITIVE_IMPACTS:
        if column not in pivot.columns:
            pivot[column] = 0.0
        pivot[column] = pd.to_numeric(pivot[column], errors="coerce").fillna(0.0)
    yield_inverse = 1.0 / pivot["production_yield_multiplier"].clip(lower=1e-9)
    cycle_basis = pivot["cycle_length_multiplier"].clip(lower=0.0)
    role = pivot["production_role"].astype(str)
    role_basis = np.where(role.isin(["dairy", "eggs"]), yield_inverse, cycle_basis)
    role_basis = np.where(role.eq("all"), np.maximum(yield_inverse, cycle_basis), role_basis)
    mortality = pd.to_numeric(pivot["mortality_rate_delta"], errors="coerce").fillna(0.0)
    if (mortality >= 1.0).any():
        raise ThermalStressDataError("mortality_rate_delta must remain below 1")
    mortality_activity = 1.0 / (1.0 - mortality).clip(lower=1e-9)
    pivot["mortality_activity_multiplier"] = mortality_activity
    pivot["activity_head_multiplier"] = (
        pivot["direct_stock_multiplier"]
        * np.asarray(role_basis, dtype=float)
        * pivot["replacement_multiplier"]
        * mortality_activity
    ).clip(lower=0.0)
    pivot["feed_efficiency_multiplier"] = (
        pivot["maintenance_energy_multiplier"]
        / pivot["digestibility_multiplier"].clip(lower=1e-9)
    )
    pivot["feed_per_output_multiplier"] = (
        pivot["activity_head_multiplier"]
        * pivot["dm_intake_multiplier"]
        * pivot["feed_efficiency_multiplier"]
    )
    pivot["enteric_ch4_total_multiplier"] = (
        pivot["activity_head_multiplier"] * pivot["enteric_ch4_ef_multiplier"]
    )
    pivot["manure_ch4_total_multiplier"] = (
        pivot["activity_head_multiplier"]
        * pivot["volatile_solids_multiplier"]
        * pivot["manure_ch4_ef_multiplier"]
    )
    pivot["manure_n2o_total_multiplier"] = (
        pivot["activity_head_multiplier"]
        * pivot["n_excretion_multiplier"]
        * pivot["manure_n2o_ef_multiplier"]
    )
    return pivot


def apply_thermal_adaptation(
    bundle: ThermalStressBundle,
    adaptation_multiplier_by: Mapping[Tuple[str, str, int], float],
) -> pd.DataFrame:
    """Apply residual-stress multipliers and rebuild derived ledger drivers.

    A value of 1 leaves stress unchanged; 0 removes the stress deviation from
    the neutral response.  Multiple adaptation levers should be multiplied by
    the scenario layer before entering this function.
    """
    if not adaptation_multiplier_by:
        return pd.DataFrame()
    impacts = bundle.commodity_impacts.copy()
    audit: list[Dict[str, Any]] = []
    lookup: Dict[Tuple[str, str, int], float] = {}
    for key, value in adaptation_multiplier_by.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise ThermalStressDataError(
                f"Thermal adaptation key must be (country, commodity, year): {key!r}"
            )
        m49 = normalize_m49(key[0])
        if m49 is None:
            raise ThermalStressDataError(f"Thermal adaptation country is not M49: {key[0]!r}")
        residual = float(value)
        if not np.isfinite(residual) or residual < 0.0 or residual > 1.0:
            raise ThermalStressDataError(
                f"Thermal residual-stress multiplier must be in [0, 1]: {value!r}"
            )
        normalized_key = (m49, str(key[1]).strip(), int(key[2]))
        if normalized_key in lookup:
            raise ThermalStressDataError(
                "Thermal adaptation contains duplicate normalized target: "
                f"{normalized_key!r}"
            )
        lookup[normalized_key] = residual
    response_columns = list(MULTIPLIER_IMPACTS) + list(ADDITIVE_IMPACTS)
    matched_keys: set[Tuple[str, str, int]] = set()
    for index, row in impacts.iterrows():
        key = (normalize_m49(row["m49"]), str(row["commodity"]), int(row["year"]))
        residual = lookup.get(key)
        if residual is None:
            continue
        matched_keys.add(key)
        for column in response_columns:
            if column not in impacts.columns:
                continue
            original = float(impacts.at[index, column])
            adapted = original * residual if column in ADDITIVE_IMPACTS else 1.0 + (original - 1.0) * residual
            impacts.at[index, column] = adapted
            audit.append(
                {
                    "m49": key[0],
                    "commodity": key[1],
                    "year": key[2],
                    "impact": column,
                    "original_value": original,
                    "residual_stress_multiplier": residual,
                    "adapted_value": adapted,
                }
            )
    unmatched_keys = sorted(set(lookup) - matched_keys)
    if bundle.settings.strict and unmatched_keys:
        raise ThermalStressDataError(
            "Thermal adaptation targets matched no commodity impacts: "
            + repr(unmatched_keys[:20])
        )
    bundle.commodity_impacts = recalculate_activity_multipliers(impacts)
    bundle.metadata["adaptation_rows"] = len(audit)
    return pd.DataFrame(audit)


def aggregate_impacts_for_model(impacts: pd.DataFrame) -> pd.DataFrame:
    """Collapse production systems using AGLW animal weights.

    The optimization model currently has no production-system index.  System
    detail is retained in ``impacts_by_system`` and only this explicitly
    weighted table is joined to model commodities.
    """
    if impacts.empty:
        return impacts.copy()
    keys = [
        "m49",
        "year",
        "species",
        "production_role",
        "scenario",
        "climate_model",
    ]
    numeric = [
        column
        for column in impacts.columns
        if column not in set(keys + ["production_system"])
        and pd.api.types.is_numeric_dtype(impacts[column])
        and column
        not in {
            "animal_weight",
            "source_grid_cells",
            "livestock_weight_year",
            "animal_weight_relative_uncertainty",
        }
    ]
    rows: List[Dict[str, Any]] = []
    for key, group in impacts.groupby(keys, dropna=False, sort=False):
        row = dict(zip(keys, key))
        row["animal_weight"] = float(group["animal_weight"].sum())
        row["source_grid_cells"] = int(group["source_grid_cells"].sum())
        row["production_system"] = "animal_weighted_all"
        if "animal_weight_relative_uncertainty" in group.columns:
            row["animal_weight_relative_uncertainty"] = _weighted_mean(
                group, "animal_weight_relative_uncertainty", "animal_weight"
            )
        if "livestock_weight_year" in group.columns:
            weight_years = sorted(
                pd.to_numeric(group["livestock_weight_year"], errors="coerce")
                .dropna()
                .astype(int)
                .unique()
            )
            row["livestock_weight_year"] = (
                weight_years[0] if len(weight_years) == 1 else pd.NA
            )
            row["livestock_weight_year_min"] = min(weight_years) if weight_years else pd.NA
            row["livestock_weight_year_max"] = max(weight_years) if weight_years else pd.NA
        for column in (
            "livestock_weight_source",
            "source_dataset_version",
            "weight_imputation_flag",
        ):
            if column in group.columns:
                row[column] = "|".join(
                    sorted({str(value) for value in group[column].dropna()})
                )
        for column in numeric:
            row[column] = _weighted_mean(group, column, "animal_weight")
        rows.append(row)
    return pd.DataFrame(rows).sort_values(keys).reset_index(drop=True)


def load_commodity_species_map(path: str | Path) -> pd.DataFrame:
    df = _read_tabular(path)
    df.columns = [str(c).strip() for c in df.columns]
    _require_columns(
        df,
        ["commodity", "production_commodity", "species", "production_role"],
        "thermal commodity map",
    )
    df = df.copy()
    df["commodity"] = df["commodity"].astype(str).str.strip()
    df["production_commodity"] = df["production_commodity"].astype(str).str.strip()
    df["species"] = df["species"].map(canonical_species)
    df["production_role"] = df["production_role"].astype(str).str.lower().str.strip()
    if df["species"].isna().any():
        raise ThermalStressDataError("Commodity map contains unsupported species")
    if not set(df["production_role"]).issubset(PRODUCTION_ROLES):
        bad = sorted(set(df["production_role"]) - set(PRODUCTION_ROLES))
        raise ThermalStressDataError(f"Commodity map contains unsupported roles: {bad}")
    if df["commodity"].duplicated().any():
        bad = sorted(df.loc[df["commodity"].duplicated(keep=False), "commodity"].unique())
        raise ThermalStressDataError(f"Commodity map has duplicate Item_Emis rows: {bad}")
    return df.drop_duplicates().reset_index(drop=True)


def map_impacts_to_commodities(
    impacts_model: pd.DataFrame,
    commodity_map: pd.DataFrame,
) -> pd.DataFrame:
    out = impacts_model.merge(
        commodity_map,
        on=["species", "production_role"],
        how="inner",
        validate="many_to_many",
    )
    if out.empty:
        raise ThermalStressDataError("Thermal impacts did not match any model commodity")
    key = ["m49", "year", "commodity", "scenario", "climate_model"]
    if out.duplicated(key).any():
        duplicates = out.loc[out.duplicated(key, keep=False), key]
        raise ThermalStressDataError(
            "Commodity impacts are not unique: "
            + duplicates.drop_duplicates().head(20).to_dict(orient="records").__repr__()
        )
    return out.sort_values(["year", "m49", "commodity"]).reset_index(drop=True)


def _load_optional_registry(path: Optional[str | Path], label: str) -> pd.DataFrame:
    if path is None or str(path).strip() == "":
        return pd.DataFrame()
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"{label} not found: {source}")
    df = _read_tabular(source)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_activity_factors(path: Optional[str | Path], *, strict: bool = True) -> pd.DataFrame:
    df = _load_optional_registry(path, "Thermal activity-factor registry")
    if df.empty:
        return df
    required = [
        "species",
        "production_role",
        "n_excretion_kg_per_head_year",
        "p_excretion_kg_per_head_year",
        "volatile_solids_kg_per_head_year",
        "housing_energy_kwh_per_head_year",
        "source_id",
        "parameter_status",
    ]
    _require_columns(df, required, "thermal activity-factor registry")
    df = df.copy()
    df["species"] = df["species"].map(canonical_species)
    df["production_role"] = df["production_role"].astype(str).str.lower().str.strip()
    if df["species"].isna().any():
        raise ThermalStressDataError(
            "Activity-factor registry contains unsupported species"
        )
    invalid_roles = sorted(set(df["production_role"]) - set(PRODUCTION_ROLES))
    if invalid_roles:
        raise ThermalStressDataError(
            f"Activity-factor registry contains unsupported roles: {invalid_roles}"
        )
    for column in required[2:6]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    required_values = df[required[2:6]].to_numpy(dtype=float)
    if not np.isfinite(required_values).all() or (required_values < 0.0).any():
        raise ThermalStressDataError("Activity factors must be finite and non-negative")
    optional_numeric_defaults = {
        "cycle_days_base": np.nan,
        "turnover_rate_base": np.nan,
        "producing_share": np.nan,
        "electricity_kwh_per_head_year": 0.0,
        "fuel_gj_per_head_year": 0.0,
    }
    for column, default in optional_numeric_defaults.items():
        if column not in df.columns:
            df[column] = default
        df[column] = pd.to_numeric(df[column], errors="coerce")
        present = df[column].dropna().to_numpy(dtype=float)
        if not np.isfinite(present).all() or (present < 0.0).any():
            raise ThermalStressDataError(
                f"Activity factor {column} must be finite and non-negative"
            )
    status = df["parameter_status"].fillna("").astype(str).str.lower().str.strip()
    if strict and (~status.eq("production")).any():
        raise ThermalStressDataError("Activity-factor registry contains non-production rows")
    production = df.loc[status.eq("production")].copy()
    key = ["species", "production_role"]
    if production.duplicated(key).any():
        duplicates = production.loc[
            production.duplicated(key, keep=False), key
        ].drop_duplicates()
        raise ThermalStressDataError(
            "Activity-factor registry has duplicate production keys: "
            + repr(duplicates.head(20).to_dict(orient="records"))
        )
    return production.reset_index(drop=True)


def load_pollutant_factors(path: Optional[str | Path], *, strict: bool = True) -> pd.DataFrame:
    df = _load_optional_registry(path, "Thermal pollutant-factor registry")
    if df.empty:
        return df
    required = [
        "species",
        "production_role",
        "pollutant",
        "pathway",
        "activity_basis",
        "factor_kg_per_activity_unit",
        "heat_ef_coefficient",
        "cold_ef_coefficient",
        "heat_load_scale",
        "cold_load_scale",
        "source_id",
        "parameter_status",
    ]
    _require_columns(df, required, "thermal pollutant-factor registry")
    df = df.copy()
    df["species"] = df["species"].map(canonical_species)
    df["production_role"] = df["production_role"].astype(str).str.lower().str.strip()
    if df["species"].isna().any():
        raise ThermalStressDataError(
            "Pollutant-factor registry contains unsupported species"
        )
    invalid_roles = sorted(set(df["production_role"]) - set(PRODUCTION_ROLES))
    if invalid_roles:
        raise ThermalStressDataError(
            f"Pollutant-factor registry contains unsupported roles: {invalid_roles}"
        )
    df["pollutant"] = df["pollutant"].astype(str).str.upper().str.strip()
    df["pathway"] = df["pathway"].astype(str).str.lower().str.strip()
    if df["pathway"].eq("").any():
        raise ThermalStressDataError(
            "Pollutant-factor registry pathway must not be blank"
        )
    bad_pollutants = sorted(set(df["pollutant"]) - set(POLLUTANT_GROUPS))
    if bad_pollutants:
        raise ThermalStressDataError(f"Unsupported pollutants: {bad_pollutants}")
    allowed_basis = {
        "effective_head_year",
        "feed_dm_t",
        "n_excreted_kg",
        "p_excreted_kg",
        "volatile_solids_kg",
        "housing_energy_kwh",
        "production_t",
    }
    df["activity_basis"] = df["activity_basis"].astype(str).str.lower().str.strip()
    bad_basis = sorted(set(df["activity_basis"]) - allowed_basis)
    if bad_basis:
        raise ThermalStressDataError(f"Unsupported pollutant activity bases: {bad_basis}")
    numeric = [
        "factor_kg_per_activity_unit",
        "heat_ef_coefficient",
        "cold_ef_coefficient",
        "heat_load_scale",
        "cold_load_scale",
    ]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    numeric_values = df[numeric].to_numpy(dtype=float)
    if not np.isfinite(numeric_values).all() or (
        df["factor_kg_per_activity_unit"] < 0.0
    ).any():
        raise ThermalStressDataError("Pollutant factors and stress coefficients must be finite")
    if (df[["heat_load_scale", "cold_load_scale"]] <= 0).any().any():
        raise ThermalStressDataError("Pollutant heat/cold load scales must be positive")
    status = df["parameter_status"].fillna("").astype(str).str.lower().str.strip()
    if strict and (~status.eq("production")).any():
        raise ThermalStressDataError("Pollutant-factor registry contains non-production rows")
    production = df.loc[status.eq("production")].copy()
    key = [
        "species",
        "production_role",
        "pollutant",
        "pathway",
        "activity_basis",
    ]
    if production.duplicated(key).any():
        duplicates = production.loc[
            production.duplicated(key, keep=False), key
        ].drop_duplicates()
        raise ThermalStressDataError(
            "Pollutant-factor registry has duplicate production keys: "
            + repr(duplicates.head(20).to_dict(orient="records"))
        )
    return production.reset_index(drop=True)


def build_thermal_stress_bundle(
    *,
    exposure_path: str | Path,
    response_registry_path: str | Path,
    commodity_map_path: str | Path,
    activity_factor_path: Optional[str | Path] = None,
    pollutant_factor_path: Optional[str | Path] = None,
    data_manifest_path: Optional[str | Path] = None,
    strain_registry_path: Optional[str | Path] = None,
    settings: Optional[ThermalStressSettings] = None,
    target_years: Optional[Iterable[int]] = None,
) -> ThermalStressBundle:
    cfg = settings or ThermalStressSettings(enabled=True)
    data_manifest = validate_exposure_manifest(
        data_manifest_path,
        exposure_path=exposure_path,
        required=bool(cfg.strict and cfg.require_data_manifest),
    )
    response = load_response_registry(
        response_registry_path,
        strict=cfg.strict,
        uncertainty_draw=cfg.uncertainty_draw,
        uncertainty_seed=cfg.uncertainty_seed,
    )
    strain_registry = load_strain_registry(strain_registry_path, strict=cfg.strict)
    strain_names = (
        set(strain_registry["strain_name"].astype(str))
        if not strain_registry.empty
        else set()
    )
    requested_exposure_drivers = {
        str(driver).strip()
        for column in ("heat_driver", "cold_driver")
        for driver in (
            strain_registry[column] if not strain_registry.empty else ()
        )
    }
    requested_exposure_drivers.update(
        str(driver).strip()
        for column in ("heat_driver", "cold_driver")
        for driver in response[column]
        if str(driver).strip() not in strain_names
    )
    exposure = load_thermal_exposure(
        exposure_path,
        cfg,
        target_years=target_years,
        required_driver_columns=requested_exposure_drivers,
    )
    commodity_map = load_commodity_species_map(commodity_map_path)
    validate_response_registry_coverage(
        response, commodity_map, settings=cfg, exposure=exposure
    )
    strain = calculate_thermal_strain(exposure, strain_registry)
    impacts_system = calculate_thermal_impacts(
        strain,
        response,
        commodity_map=commodity_map,
        require_complete_response=bool(
            cfg.strict and cfg.require_complete_response_registry
        ),
    )
    impacts_model = aggregate_impacts_for_model(impacts_system)
    commodity_impacts = map_impacts_to_commodities(impacts_model, commodity_map)
    activity_factors = load_activity_factors(activity_factor_path, strict=cfg.strict)
    pollutant_factors = load_pollutant_factors(pollutant_factor_path, strict=cfg.strict)
    metadata = {
        "schema_version": 2,
        "spatial_resolution_km": cfg.target_resolution_km,
        "historical_year_start": 1960,
        "historical_year_end": 2020,
        "future_years": list(FUTURE_YEARS),
        "species": list(SUPPORTED_SPECIES),
        "historical_emissions_mode": cfg.historical_emissions_mode,
        "exposure_rows": int(len(exposure)),
        "impact_system_rows": int(len(impacts_system)),
        "commodity_impact_rows": int(len(commodity_impacts)),
        "source_files": {
            "exposure": str(Path(exposure_path)),
            "response_registry": str(Path(response_registry_path)),
            "commodity_map": str(Path(commodity_map_path)),
            "activity_factors": str(activity_factor_path or ""),
            "pollutant_factors": str(pollutant_factor_path or ""),
            "data_manifest": str(data_manifest_path or ""),
            "strain_registry": str(strain_registry_path or ""),
        },
        "data_manifest": data_manifest,
        "uncertainty_draw": cfg.uncertainty_draw,
        "uncertainty_seed": cfg.uncertainty_seed,
        "response_clip_count": int(
            sum(
                impacts_system[column].fillna(False).astype(bool).sum()
                for column in impacts_system.columns
                if column.endswith("_clipped")
            )
        ),
    }
    return ThermalStressBundle(
        settings=cfg,
        exposure=exposure,
        impacts_by_system=impacts_system,
        impacts_model=impacts_model,
        commodity_map=commodity_map,
        commodity_impacts=commodity_impacts,
        activity_factors=activity_factors,
        pollutant_factors=pollutant_factors,
        strain=strain,
        metadata=metadata,
    )


def _normalise_activity_table(
    df: Optional[pd.DataFrame],
    *,
    value_column: str,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["m49", "year", "commodity", value_column])
    work = df.copy()
    if "m49" in work.columns:
        work["m49"] = work["m49"].map(normalize_m49)
    elif "m49_code" in work.columns:
        work["m49"] = work["m49_code"].map(normalize_m49)
    elif "M49_Country_Code" in work.columns:
        work["m49"] = work["M49_Country_Code"].map(normalize_m49)
    elif "country" in work.columns:
        work["m49"] = work["country"].map(normalize_m49)
    else:
        raise ThermalStressDataError(f"Activity table for {value_column} has no M49/country column")
    commodity_column = "commodity" if "commodity" in work.columns else "Item"
    _require_columns(work, [commodity_column, "year", value_column], f"activity {value_column}")
    work["commodity"] = work[commodity_column].astype(str).str.strip()
    work["year"] = pd.to_numeric(work["year"], errors="coerce")
    work[value_column] = pd.to_numeric(work[value_column], errors="coerce")
    work = work.dropna(subset=["m49", "year", "commodity", value_column])
    work["year"] = work["year"].astype(int)
    return work.groupby(["m49", "year", "commodity"], as_index=False)[value_column].sum()


def build_animal_activity_ledger(
    *,
    stock_df: pd.DataFrame,
    production_df: Optional[pd.DataFrame],
    feed_detail_df: Optional[pd.DataFrame],
    bundle: ThermalStressBundle,
) -> pd.DataFrame:
    """Build the authoritative activity ledger shared by Modules 3 and 4."""
    stock = _normalise_activity_table(stock_df, value_column="stock_head")
    if stock.empty:
        return pd.DataFrame()
    ledger = stock.merge(
        bundle.commodity_map,
        on="commodity",
        how="left",
        validate="many_to_one",
        indicator="_commodity_map_merge",
    )
    unmapped = ledger["_commodity_map_merge"].eq("left_only")
    if bundle.settings.strict and unmapped.any():
        missing = ledger.loc[
            unmapped, ["m49", "year", "commodity"]
        ].drop_duplicates()
        raise ThermalStressDataError(
            "Activity ledger stock rows have no thermal commodity mapping: "
            + repr(missing.head(20).to_dict(orient="records"))
        )
    ledger = ledger.loc[~unmapped].drop(columns=["_commodity_map_merge"])
    production_mapping = bundle.commodity_map[
        ["production_commodity", "commodity"]
    ].dropna().drop_duplicates()
    ambiguous_production = production_mapping.duplicated(
        "production_commodity", keep=False
    )
    if ambiguous_production.any():
        raise ThermalStressDataError(
            "Thermal commodity map has ambiguous production_commodity targets: "
            + repr(
                production_mapping.loc[ambiguous_production]
                .sort_values(["production_commodity", "commodity"])
                .head(20)
                .to_dict(orient="records")
            )
        )
    impact_keys = ["m49", "year", "commodity", "species", "production_role"]
    missing_impact_schema = sorted(
        set(impact_keys) - set(bundle.commodity_impacts.columns)
    )
    if missing_impact_schema:
        if bundle.settings.strict:
            raise ThermalStressDataError(
                "Thermal commodity impacts are unavailable for strict activity "
                f"ledger construction; missing columns: {missing_impact_schema}"
            )
    else:
        ledger = ledger.merge(
            bundle.commodity_impacts,
            on=impact_keys,
            how="left",
            suffixes=("", "_impact"),
            validate="many_to_one",
            indicator="_thermal_impact_merge",
        )
        missing_impacts = ledger["_thermal_impact_merge"].eq("left_only")
        if bundle.settings.strict and missing_impacts.any():
            missing = ledger.loc[
                missing_impacts, impact_keys
            ].drop_duplicates()
            raise ThermalStressDataError(
                "Activity ledger rows have no thermal commodity impacts: "
                + repr(missing.head(20).to_dict(orient="records"))
            )
        ledger = ledger.drop(columns=["_thermal_impact_merge"])
    multiplier_cols = list(MULTIPLIER_IMPACTS) + [
        "activity_head_multiplier",
        "feed_per_output_multiplier",
        "enteric_ch4_total_multiplier",
        "manure_ch4_total_multiplier",
        "manure_n2o_total_multiplier",
    ]
    for column in multiplier_cols:
        if column not in ledger.columns:
            if bundle.settings.strict:
                raise ThermalStressDataError(
                    f"Strict activity ledger is missing thermal multiplier {column!r}"
                )
            ledger[column] = 1.0
        values = pd.to_numeric(ledger[column], errors="coerce")
        if bundle.settings.strict and (
            values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all()
        ):
            raise ThermalStressDataError(
                f"Strict activity ledger has non-finite thermal multiplier {column!r}"
            )
        ledger[column] = values.fillna(1.0)
    if "mortality_rate_delta" not in ledger.columns:
        ledger["mortality_rate_delta"] = 0.0
    ledger["stock_head_base"] = ledger["stock_head"]
    ledger["stock_head_effective"] = ledger["stock_head_base"] * ledger["activity_head_multiplier"]

    if production_df is not None and not production_df.empty:
        production = production_df.copy()
        if "M49_Country_Code" in production.columns:
            production["m49"] = production["M49_Country_Code"].map(normalize_m49)
        elif "country" in production.columns:
            production["m49"] = production["country"].map(normalize_m49)
        else:
            production["m49"] = None
        source_comm = "Commodity" if "Commodity" in production.columns else "commodity"
        production["source_commodity"] = production[source_comm].astype(str).str.strip()
        production["year"] = pd.to_numeric(production["year"], errors="coerce")
        production["production_t"] = pd.to_numeric(production["production_t"], errors="coerce")
        production = production.dropna(subset=["m49", "year", "production_t"])
        production["year"] = production["year"].astype(int)
        production_map = production_mapping.set_index("production_commodity")[
            "commodity"
        ].to_dict()
        direct_commodities = set(bundle.commodity_map["commodity"])
        production["commodity"] = production["source_commodity"].map(production_map)
        direct_mask = production["source_commodity"].isin(direct_commodities)
        production.loc[direct_mask, "commodity"] = production.loc[
            direct_mask, "source_commodity"
        ]
        production = production.dropna(subset=["commodity"])
        production = production.groupby(["m49", "year", "commodity"], as_index=False)["production_t"].sum()
        ledger = ledger.merge(production, on=["m49", "year", "commodity"], how="left")
    if "production_t" not in ledger.columns:
        ledger["production_t"] = np.nan
    if bundle.settings.strict:
        production_values = pd.to_numeric(ledger["production_t"], errors="coerce")
        invalid_production = ~np.isfinite(production_values.to_numpy(dtype=float)) | (
            production_values.to_numpy(dtype=float) < 0.0
        )
        if invalid_production.any():
            missing = ledger.loc[
                invalid_production, ["m49", "year", "commodity"]
            ].drop_duplicates()
            raise ThermalStressDataError(
                "Strict activity ledger lacks finite non-negative production: "
                + repr(missing.head(20).to_dict(orient="records"))
            )

    ledger["feed_dm_base_t"] = np.nan
    feed_has_thermal_provenance = False
    if feed_detail_df is not None and not feed_detail_df.empty:
        feed = feed_detail_df.copy()
        feed_has_thermal_provenance = {
            "activity_head_multiplier",
            "dm_intake_multiplier",
        }.issubset(feed.columns)
        if "m49_code" in feed.columns:
            feed["m49"] = feed["m49_code"].map(normalize_m49)
        elif "M49_Country_Code" in feed.columns:
            feed["m49"] = feed["M49_Country_Code"].map(normalize_m49)
        else:
            feed["m49"] = feed.get("country", pd.Series(index=feed.index)).map(normalize_m49)
        _require_columns(feed, ["year", "commodity", "dm_total_kg"], "feed detail")
        feed["year"] = pd.to_numeric(feed["year"], errors="coerce")
        feed["dm_total_kg"] = pd.to_numeric(feed["dm_total_kg"], errors="coerce")
        has_explicit_base = "dm_total_kg_base" in feed.columns
        if has_explicit_base:
            feed["dm_total_kg_base"] = pd.to_numeric(
                feed["dm_total_kg_base"], errors="coerce"
            )
        else:
            feed["dm_total_kg_base"] = feed["dm_total_kg"]
        feed = feed.dropna(
            subset=["m49", "year", "commodity", "dm_total_kg", "dm_total_kg_base"]
        )
        feed["year"] = feed["year"].astype(int)
        feed["commodity"] = feed["commodity"].astype(str).str.strip()
        feed = feed.groupby(["m49", "year", "commodity"], as_index=False)[
            ["dm_total_kg_base", "dm_total_kg"]
        ].sum()
        feed["feed_dm_effective_t_input"] = feed["dm_total_kg"] / 1000.0
        feed["feed_dm_base_t"] = feed["dm_total_kg_base"] / 1000.0
        ledger = ledger.drop(columns=["feed_dm_base_t"]).merge(
            feed[
                [
                    "m49",
                    "year",
                    "commodity",
                    "feed_dm_base_t",
                    "feed_dm_effective_t_input",
                ]
            ],
            on=["m49", "year", "commodity"],
            how="left",
        )
    ledger["feed_dm_effective_t"] = (
        ledger["feed_dm_base_t"] * ledger["feed_per_output_multiplier"]
    )
    if "feed_dm_effective_t_input" in ledger.columns:
        supplied = pd.to_numeric(
            ledger["feed_dm_effective_t_input"], errors="coerce"
        )
        calculated = pd.to_numeric(
            ledger["feed_dm_effective_t"], errors="coerce"
        )
        both = supplied.notna() & calculated.notna()
        inconsistent = both & ~np.isclose(
            supplied.to_numpy(dtype=float),
            calculated.to_numpy(dtype=float),
            rtol=1e-9,
            atol=1e-9,
        )
        if (
            bundle.settings.strict
            and feed_has_thermal_provenance
            and inconsistent.any()
        ):
            bad = ledger.loc[
                inconsistent, ["m49", "year", "commodity"]
            ].copy()
            bad["feed_from_module3_t"] = supplied.loc[inconsistent].to_numpy()
            bad["feed_from_ledger_formula_t"] = calculated.loc[
                inconsistent
            ].to_numpy()
            raise ThermalStressDataError(
                "Module 3 DMI and activity-ledger feed mass do not conserve: "
                + repr(bad.head(20).to_dict(orient="records"))
            )
        ledger["feed_dm_effective_t"] = supplied.fillna(calculated)
        ledger = ledger.drop(columns=["feed_dm_effective_t_input"])
    if bundle.settings.strict:
        feed_columns = ["feed_dm_base_t", "feed_dm_effective_t"]
        feed_values = ledger[feed_columns].apply(pd.to_numeric, errors="coerce")
        invalid_feed = ~np.isfinite(feed_values.to_numpy(dtype=float)) | (
            feed_values.to_numpy(dtype=float) < 0.0
        )
        if invalid_feed.any():
            bad_rows = invalid_feed.any(axis=1)
            missing = ledger.loc[
                bad_rows, ["m49", "year", "commodity"]
            ].drop_duplicates()
            raise ThermalStressDataError(
                "Strict activity ledger lacks finite non-negative DMI/feed rows: "
                + repr(missing.head(20).to_dict(orient="records"))
            )

    factor_columns = [
        "n_excretion_kg_per_head_year",
        "p_excretion_kg_per_head_year",
        "volatile_solids_kg_per_head_year",
        "housing_energy_kwh_per_head_year",
        "cycle_days_base",
        "turnover_rate_base",
        "producing_share",
        "electricity_kwh_per_head_year",
        "fuel_gj_per_head_year",
    ]
    if not bundle.activity_factors.empty:
        ledger = ledger.merge(
            bundle.activity_factors[["species", "production_role"] + factor_columns],
            on=["species", "production_role"],
            how="left",
            validate="many_to_one",
        )
    for column in factor_columns:
        if column not in ledger.columns:
            ledger[column] = np.nan

    ledger["n_excreted_kg"] = (
        ledger["stock_head_effective"]
        * ledger["n_excretion_kg_per_head_year"]
        * ledger["n_excretion_multiplier"]
    )
    ledger["p_excreted_kg"] = (
        ledger["stock_head_effective"]
        * ledger["p_excretion_kg_per_head_year"]
        * ledger["p_excretion_multiplier"]
    )
    ledger["volatile_solids_kg"] = (
        ledger["stock_head_effective"]
        * ledger["volatile_solids_kg_per_head_year"]
        * ledger["volatile_solids_multiplier"]
    )
    ledger["housing_energy_kwh"] = (
        ledger["stock_head_effective"]
        * ledger["housing_energy_kwh_per_head_year"]
        * ledger["housing_energy_multiplier"]
    )
    role = ledger["production_role"].astype(str)
    default_producing_share = np.where(role.isin(["dairy", "eggs"]), 1.0, 0.0)
    ledger["producing_share"] = pd.to_numeric(
        ledger["producing_share"], errors="coerce"
    ).fillna(pd.Series(default_producing_share, index=ledger.index))
    ledger["producing_animals_head"] = (
        ledger["stock_head_effective"] * ledger["producing_share"].clip(0.0, 1.0)
    )
    ledger["cycle_days"] = (
        pd.to_numeric(ledger["cycle_days_base"], errors="coerce")
        * ledger["cycle_length_multiplier"]
    )
    turnover_from_cycle = 365.0 / ledger["cycle_days"].replace(0.0, np.nan)
    ledger["turnover_rate"] = pd.to_numeric(
        ledger["turnover_rate_base"], errors="coerce"
    ).fillna(turnover_from_cycle)
    ledger["slaughtered_head"] = np.where(
        role.eq("meat"),
        ledger["stock_head_effective"] * ledger["turnover_rate"].fillna(0.0),
        0.0,
    )
    ledger["stock_per_t_output"] = (
        ledger["stock_head_effective"]
        / pd.to_numeric(ledger["production_t"], errors="coerce").replace(0.0, np.nan)
    )
    ledger["dmi_t"] = ledger["feed_dm_effective_t"]
    ledger["housing_head_days"] = ledger["stock_head_effective"] * 365.0
    ledger["electricity_kwh"] = (
        ledger["stock_head_effective"]
        * ledger["electricity_kwh_per_head_year"].fillna(0.0)
        * ledger["housing_energy_multiplier"]
    )
    ledger["fuel_gj"] = (
        ledger["stock_head_effective"]
        * ledger["fuel_gj_per_head_year"].fillna(0.0)
        * ledger["housing_energy_multiplier"]
    )
    business_key = ["m49", "year", "commodity"]
    if ledger.duplicated(business_key).any():
        duplicates = ledger.loc[
            ledger.duplicated(business_key, keep=False), business_key
        ].drop_duplicates()
        raise ThermalStressDataError(
            "Animal activity ledger has duplicate business keys: "
            + repr(duplicates.head(20).to_dict(orient="records"))
        )
    return ledger.sort_values(["year", "m49", "commodity"]).reset_index(drop=True)


def calculate_pollutant_inventory(
    ledger: pd.DataFrame,
    pollutant_factors: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate non-GHG and optional energy/nutrient emissions from the ledger."""
    if ledger is None or ledger.empty or pollutant_factors is None or pollutant_factors.empty:
        return pd.DataFrame(
            columns=[
                "m49",
                "year",
                "commodity",
                "species",
                "production_role",
                "pollutant",
                "pollutant_group",
                "pathway",
                "activity_basis",
                "activity_value",
                "factor_kg_per_activity_unit",
                "stress_ef_multiplier",
                "emission_kg",
                "emission_kt",
                "source_id",
            ]
        )
    merged = ledger.merge(
        pollutant_factors,
        on=["species", "production_role"],
        how="inner",
        validate="many_to_many",
    )
    basis_to_column = {
        "effective_head_year": "stock_head_effective",
        "feed_dm_t": "feed_dm_effective_t",
        "n_excreted_kg": "n_excreted_kg",
        "p_excreted_kg": "p_excreted_kg",
        "volatile_solids_kg": "volatile_solids_kg",
        "housing_energy_kwh": "housing_energy_kwh",
        "production_t": "production_t",
    }
    merged["activity_column"] = merged["activity_basis"].map(basis_to_column)
    activity = np.full(len(merged), np.nan, dtype=float)
    for basis, column in basis_to_column.items():
        mask = merged["activity_basis"].eq(basis)
        if mask.any():
            activity[mask] = pd.to_numeric(merged.loc[mask, column], errors="coerce")
    merged["activity_value"] = activity
    heat_effect = (
        merged["heat_ef_coefficient"]
        * merged["heat_load"].fillna(0.0)
        / merged["heat_load_scale"]
    )
    cold_effect = (
        merged["cold_ef_coefficient"]
        * merged["cold_load"].fillna(0.0)
        / merged["cold_load_scale"]
    )
    merged["stress_ef_multiplier"] = (1.0 + heat_effect + cold_effect).clip(lower=0.0)
    merged["emission_kg"] = (
        merged["activity_value"]
        * merged["factor_kg_per_activity_unit"]
        * merged["stress_ef_multiplier"]
    )
    merged["emission_kt"] = merged["emission_kg"] / 1_000_000.0
    merged["pollutant_group"] = merged["pollutant"].map(POLLUTANT_GROUPS)
    columns = [
        "m49",
        "year",
        "commodity",
        "species",
        "production_role",
        "pollutant",
        "pollutant_group",
        "pathway",
        "activity_basis",
        "activity_value",
        "factor_kg_per_activity_unit",
        "stress_ef_multiplier",
        "emission_kg",
        "emission_kt",
        "source_id",
    ]
    return merged[columns].sort_values(
        ["year", "m49", "commodity", "pollutant", "pathway"]
    ).reset_index(drop=True)


def adjust_livestock_emission_frames(
    emissions: Mapping[str, pd.DataFrame],
    commodity_impacts: pd.DataFrame,
    *,
    hist_cutoff_year: int = 2020,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """Apply future-only thermal activity/EF multipliers to GLE frames.

    Historical inventories already embody realised weather and management, so
    rows through 2020 are retained unchanged.  Future frames are scaled once by
    process/gas-specific total multipliers.  The returned audit records every
    original and adjusted gas value.
    """
    if not emissions:
        return {}, pd.DataFrame()
    impact_cols = [
        "m49",
        "year",
        "commodity",
        "enteric_ch4_total_multiplier",
        "manure_ch4_total_multiplier",
        "manure_n2o_total_multiplier",
    ]
    impacts = commodity_impacts[impact_cols].copy()
    adjusted: Dict[str, pd.DataFrame] = {}
    audits: List[pd.DataFrame] = []
    for process, frame in emissions.items():
        if frame is None or frame.empty:
            adjusted[str(process)] = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame()
            continue
        work = frame.copy()
        work["_m49"] = work["M49_Country_Code"].map(normalize_m49)
        work["_commodity"] = work["Item"].astype(str).str.strip()
        work["year"] = pd.to_numeric(work["year"], errors="coerce").astype(int)
        work = work.merge(
            impacts,
            left_on=["_m49", "year", "_commodity"],
            right_on=["m49", "year", "commodity"],
            how="left",
            validate="many_to_one",
        )
        future = work["year"].gt(int(hist_cutoff_year))
        gas_rules: List[Tuple[str, str]] = []
        process_norm = str(process).strip().lower()
        if process_norm == "enteric fermentation":
            gas_rules.append(("CH4_kt", "enteric_ch4_total_multiplier"))
        elif process_norm == "manure management":
            gas_rules.extend(
                [
                    ("CH4_kt", "manure_ch4_total_multiplier"),
                    ("N2O_kt", "manure_n2o_total_multiplier"),
                ]
            )
        elif process_norm in {"manure applied to soils", "manure left on pasture"}:
            gas_rules.append(("N2O_kt", "manure_n2o_total_multiplier"))

        for gas_column, multiplier_column in gas_rules:
            if gas_column not in work.columns:
                continue
            multiplier = pd.to_numeric(work[multiplier_column], errors="coerce").fillna(1.0)
            original = pd.to_numeric(work[gas_column], errors="coerce").fillna(0.0)
            final_multiplier = np.where(future, multiplier, 1.0)
            adjusted_value = original * final_multiplier
            gas_name = gas_column.replace("_kt", "")
            audit = pd.DataFrame(
                {
                    "M49_Country_Code": work["_m49"],
                    "Item": work["_commodity"],
                    "year": work["year"],
                    "process": str(process),
                    "gas": gas_name,
                    "historical_inventory_preserved": ~future,
                    "thermal_multiplier": final_multiplier,
                    "emission_base_kt": original,
                    "emission_adjusted_kt": adjusted_value,
                    "thermal_delta_kt": adjusted_value - original,
                }
            )
            audits.append(audit)
            work[gas_column] = adjusted_value
        drop_cols = [
            "_m49",
            "_commodity",
            "m49",
            "commodity",
            "enteric_ch4_total_multiplier",
            "manure_ch4_total_multiplier",
            "manure_n2o_total_multiplier",
        ]
        adjusted[str(process)] = work.drop(columns=drop_cols, errors="ignore")
    audit_df = pd.concat(audits, ignore_index=True) if audits else pd.DataFrame()
    return adjusted, audit_df


def write_thermal_outputs(
    output_dir: str | Path,
    *,
    bundle: ThermalStressBundle,
    ledger: Optional[pd.DataFrame] = None,
    pollutant_inventory: Optional[pd.DataFrame] = None,
    emission_adjustment_audit: Optional[pd.DataFrame] = None,
    balance_diagnostics: Optional[pd.DataFrame] = None,
    adaptation_audit: Optional[pd.DataFrame] = None,
) -> Dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    outputs: Dict[str, str] = {}
    tables = {
        "thermal_exposure_country_species_system.csv": bundle.exposure,
        "thermal_impacts_by_system.csv": bundle.impacts_by_system,
        "thermal_impacts_model.csv": bundle.impacts_model,
        "thermal_impacts_by_commodity.csv": bundle.commodity_impacts,
        "animal_activity_ledger.csv": ledger,
        "thermal_pollutant_inventory.csv": pollutant_inventory,
        "thermal_gle_adjustment_audit.csv": emission_adjustment_audit,
        "thermal_tier2_balance_diagnostics.csv": balance_diagnostics,
        "thermal_adaptation_audit.csv": adaptation_audit,
    }
    generation = uuid.uuid4().hex
    staged: List[Tuple[Path, Path]] = []
    try:
        for filename, table in tables.items():
            if isinstance(table, pd.DataFrame) and not table.empty:
                path = target / filename
                temporary = target / f".{filename}.{generation}.tmp"
                staged.append((temporary, path))
                table.to_csv(temporary, index=False, encoding="utf-8-sig")
                outputs[filename] = str(path)
        metadata_path = target / "thermal_stress_run_metadata.json"
        metadata_temporary = target / f".{metadata_path.name}.{generation}.tmp"
        staged.append((metadata_temporary, metadata_path))
        metadata_temporary.write_text(
            json.dumps(bundle.metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        outputs[metadata_path.name] = str(metadata_path)
        # No final file is exposed until every table and the metadata have been
        # serialized successfully.  os.replace is atomic on the target volume.
        for temporary, path in staged:
            os.replace(temporary, path)
    except Exception:
        for temporary, _ in staged:
            try:
                temporary.unlink(missing_ok=True)
            except Exception:
                pass
        raise
    return outputs


__all__ = [
    "ADDITIVE_IMPACTS",
    "FUTURE_YEARS",
    "HISTORICAL_YEARS",
    "MODEL_YEARS",
    "MULTIPLIER_IMPACTS",
    "POLLUTANT_GROUPS",
    "STANDARD_EXPOSURE_DRIVER_COLUMNS",
    "SUPPORTED_SPECIES",
    "ThermalStressBundle",
    "ThermalStressDataError",
    "ThermalStressSettings",
    "adjust_livestock_emission_frames",
    "apply_thermal_adaptation",
    "aggregate_impacts_for_model",
    "build_animal_activity_ledger",
    "build_thermal_stress_bundle",
    "calculate_pollutant_inventory",
    "calculate_thermal_impacts",
    "canonical_species",
    "load_activity_factors",
    "load_commodity_species_map",
    "load_pollutant_factors",
    "load_response_registry",
    "load_thermal_exposure",
    "map_impacts_to_commodities",
    "normalize_m49",
    "recalculate_activity_multipliers",
    "validate_model_years",
    "write_thermal_outputs",
]
