# -*- coding: utf-8 -*-
"""STS versioned tabular pipeline for 5 km livestock thermal exposure.

This module does not download, invent, or statistically downscale climate data.
It converts an already aligned hourly climate table plus an explicit livestock
weight table into the grid-year contract consumed by ``STS_thermal_stress_model``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from STS_thermal_stress_model import (
    ThermalStressDataError,
    canonical_species,
    normalize_m49,
)


PIPELINE_VERSION = "1.2.0"


@dataclass(frozen=True)
class ExposurePipelineConfig:
    target_resolution_km: float = 5.0
    resolution_tolerance_km: float = 0.25
    heat_event_min_hours: int = 6
    cold_event_min_hours: int = 6
    night_start_hour: int = 0
    night_end_hour: int = 6
    wet_cold_precip_threshold_mm: float = 0.1
    wet_cold_penalty_c: float = 2.0


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_table(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(source)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    raise ThermalStressDataError(
        f"Exposure pipeline supports CSV/Parquet tables, not {suffix!r}: {source}"
    )


def write_table(frame: pd.DataFrame, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    if suffix in {".csv", ".txt"}:
        frame.to_csv(target, index=False)
    elif suffix in {".parquet", ".pq"}:
        frame.to_parquet(target, index=False)
    else:
        raise ThermalStressDataError(
            f"Exposure pipeline output must be CSV/Parquet, not {suffix!r}"
        )


def relative_humidity_from_dewpoint(temp_c: pd.Series, dewpoint_c: pd.Series) -> pd.Series:
    """Magnus-form relative humidity, clipped to the physical 0--100% range."""
    t = pd.to_numeric(temp_c, errors="coerce")
    td = pd.to_numeric(dewpoint_c, errors="coerce")
    numerator = np.exp((17.625 * td) / (243.04 + td))
    denominator = np.exp((17.625 * t) / (243.04 + t))
    return pd.Series(100.0 * numerator / denominator, index=t.index).clip(0.0, 100.0)


def temperature_humidity_index(temp_c: pd.Series, rh_percent: pd.Series) -> pd.Series:
    """Common temperature-humidity index; retained alongside raw drivers."""
    t_f = 1.8 * pd.to_numeric(temp_c, errors="coerce") + 32.0
    rh = pd.to_numeric(rh_percent, errors="coerce")
    return t_f - (0.55 - 0.0055 * rh) * (t_f - 58.0)


def wind_chill_temperature(temp_c: pd.Series, wind_m_s: pd.Series) -> pd.Series:
    """Wind-chill diagnostic with the standard formula's validity guard."""
    t = pd.to_numeric(temp_c, errors="coerce")
    wind_kmh = pd.to_numeric(wind_m_s, errors="coerce").clip(lower=0.0) * 3.6
    v16 = np.power(wind_kmh, 0.16)
    chill = 13.12 + 0.6215 * t - 11.37 * v16 + 0.3965 * t * v16
    valid = t.le(10.0) & wind_kmh.ge(4.8)
    return pd.Series(np.where(valid, chill, t), index=t.index)


def _longest_true_run(values: Iterable[bool]) -> int:
    longest = current = 0
    for value in values:
        if bool(value):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _qualified_event_mask(
    values: pd.Series, minimum_hours: int
) -> pd.Series:
    """Keep only continuous true runs meeting the configured duration."""
    flags = values.astype(bool).to_numpy()
    qualified = np.zeros(len(flags), dtype=bool)
    start = 0
    while start < len(flags):
        if not flags[start]:
            start += 1
            continue
        end = start + 1
        while end < len(flags) and flags[end]:
            end += 1
        if end - start >= minimum_hours:
            qualified[start:end] = True
        start = end
    return pd.Series(qualified, index=values.index)


def _validate_inputs(
    climate: pd.DataFrame,
    weights: pd.DataFrame,
    config: ExposurePipelineConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    climate_required = {
        "grid_id",
        "timestamp",
        "m49",
        "temperature_c",
        "wind_speed_m_s",
        "grid_resolution_km",
        "scenario",
        "climate_model",
        "source_dataset_version",
    }
    weight_required = {
        "grid_id",
        "year",
        "species",
        "production_system",
        "animal_weight",
        "livestock_weight_year",
        "livestock_weight_source",
        "source_dataset_version",
        "animal_weight_relative_uncertainty",
        "weight_imputation_flag",
        "lct_c",
        "heat_thi_threshold",
    }
    missing_climate = sorted(climate_required - set(climate.columns))
    missing_weights = sorted(weight_required - set(weights.columns))
    if missing_climate or missing_weights:
        raise ThermalStressDataError(
            f"Exposure pipeline missing columns: climate={missing_climate}, "
            f"weights={missing_weights}"
        )
    if "relative_humidity_percent" not in climate.columns and "dewpoint_c" not in climate.columns:
        raise ThermalStressDataError(
            "Climate table requires relative_humidity_percent or dewpoint_c"
        )
    for field in ("heat_event_min_hours", "cold_event_min_hours"):
        raw_value = getattr(config, field)
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ThermalStressDataError(
                f"{field} must be a positive integer"
            ) from exc
        if not np.isfinite(value) or value < 1.0 or not value.is_integer():
            raise ThermalStressDataError(f"{field} must be a positive integer")
    c = climate.copy()
    w = weights.copy()
    c["timestamp"] = pd.to_datetime(c["timestamp"], errors="coerce", utc=True)
    if c["timestamp"].isna().any():
        raise ThermalStressDataError("Climate timestamps must be parseable and timezone aware")
    c["year"] = c["timestamp"].dt.year.astype(int)
    c["m49"] = c["m49"].map(normalize_m49)
    w["species"] = w["species"].map(canonical_species)
    c["grid_id"] = c["grid_id"].astype(str).str.strip()
    w["grid_id"] = w["grid_id"].astype(str).str.strip()
    numeric_c = ["temperature_c", "wind_speed_m_s", "grid_resolution_km"]
    if "relative_humidity_percent" in c.columns:
        numeric_c.append("relative_humidity_percent")
    if "dewpoint_c" in c.columns:
        numeric_c.append("dewpoint_c")
    if "precipitation_mm" in c.columns:
        numeric_c.append("precipitation_mm")
    if "timezone_offset_hours" in c.columns:
        numeric_c.append("timezone_offset_hours")
    numeric_w = [
        "year",
        "animal_weight",
        "livestock_weight_year",
        "animal_weight_relative_uncertainty",
        "lct_c",
        "heat_thi_threshold",
    ]
    for column in numeric_c:
        c[column] = pd.to_numeric(c[column], errors="coerce")
    for column in numeric_w:
        w[column] = pd.to_numeric(w[column], errors="coerce")
    if not np.isfinite(c[numeric_c].to_numpy(dtype=float)).all() or not np.isfinite(
        w[numeric_w].to_numpy(dtype=float)
    ).all():
        raise ThermalStressDataError(
            "Climate/weight fields must contain finite numeric values"
        )
    if c["m49"].isna().any() or w["species"].isna().any():
        raise ThermalStressDataError("Climate M49 or livestock species is invalid")
    if c["grid_id"].eq("").any() or w["grid_id"].eq("").any():
        raise ThermalStressDataError("Climate/weight grid_id must not be blank")
    if not np.equal(w["year"].to_numpy(dtype=float), np.floor(w["year"])).all():
        raise ThermalStressDataError("Livestock weight years must be integers")
    w["year"] = w["year"].astype(int)
    if (w["animal_weight"] < 0).any():
        raise ThermalStressDataError("animal_weight must be non-negative")
    resolution_bad = (
        c["grid_resolution_km"] - float(config.target_resolution_km)
    ).abs().gt(float(config.resolution_tolerance_km))
    if resolution_bad.any():
        raise ThermalStressDataError("Climate grid is outside the declared 5 km tolerance")
    duplicate_weight_key = ["grid_id", "year", "species", "production_system"]
    if w.duplicated(duplicate_weight_key).any():
        raise ThermalStressDataError("Livestock weights have duplicate grid/year/species/system rows")
    climate_time_key = ["grid_id", "timestamp", "scenario", "climate_model"]
    duplicate_climate = c.duplicated(climate_time_key, keep=False)
    if duplicate_climate.any():
        duplicates = c.loc[duplicate_climate, climate_time_key].drop_duplicates()
        raise ThermalStressDataError(
            "Climate has duplicate grid/timestamp/scenario/model rows: "
            + repr(duplicates.head(20).to_dict(orient="records"))
        )
    cadence_keys = ["grid_id", "year", "scenario", "climate_model"]
    cadence_errors: list[Dict[str, Any]] = []
    for key, group in c.groupby(cadence_keys, dropna=False, sort=False):
        differences = group["timestamp"].sort_values().diff().dropna()
        invalid = differences.ne(pd.Timedelta(hours=1))
        if invalid.any():
            cadence_errors.append(
                {
                    **dict(zip(cadence_keys, key)),
                    "invalid_intervals_hours": sorted(
                        {
                            float(value / pd.Timedelta(hours=1))
                            for value in differences.loc[invalid]
                        }
                    )[:10],
                }
            )
            if len(cadence_errors) >= 20:
                break
    if cadence_errors:
        raise ThermalStressDataError(
            "Climate timestamps must have continuous one-hour cadence within "
            "each grid/year/scenario/model series: "
            + repr(cadence_errors)
        )
    return c, w


def prepare_thermal_exposure(
    climate: pd.DataFrame,
    livestock_weights: pd.DataFrame,
    *,
    config: Optional[ExposurePipelineConfig] = None,
) -> pd.DataFrame:
    """Build annual grid-level exposure without losing event/recovery metrics."""
    cfg = config or ExposurePipelineConfig()
    climate, weights = _validate_inputs(climate, livestock_weights, cfg)
    if "relative_humidity_percent" not in climate.columns:
        climate["relative_humidity_percent"] = relative_humidity_from_dewpoint(
            climate["temperature_c"], climate["dewpoint_c"]
        )
    climate["relative_humidity_percent"] = climate[
        "relative_humidity_percent"
    ].clip(0.0, 100.0)
    climate["thi"] = temperature_humidity_index(
        climate["temperature_c"], climate["relative_humidity_percent"]
    )
    climate["wind_chill_c"] = wind_chill_temperature(
        climate["temperature_c"], climate["wind_speed_m_s"]
    )
    if "precipitation_mm" not in climate.columns:
        climate["precipitation_mm"] = pd.Series(
            0.0, index=climate.index, dtype=float
        )
    if "timezone_offset_hours" not in climate.columns:
        climate["timezone_offset_hours"] = pd.Series(
            0.0, index=climate.index, dtype=float
        )
    weight_grids = weights[["grid_id", "year"]].drop_duplicates()
    climate_members = climate[["year", "scenario", "climate_model"]].drop_duplicates()
    required_coverage = weight_grids.merge(
        climate_members,
        on="year",
        how="left",
        validate="many_to_many",
        indicator="_climate_year_merge",
    )
    missing_climate_years = required_coverage["_climate_year_merge"].eq("left_only")
    if missing_climate_years.any():
        missing = required_coverage.loc[
            missing_climate_years, ["grid_id", "year"]
        ].drop_duplicates()
        raise ThermalStressDataError(
            "Livestock weight grid/year rows have no climate member: "
            + repr(missing.head(20).to_dict(orient="records"))
        )
    required_coverage = required_coverage.drop(columns="_climate_year_merge")
    available_coverage = climate[
        ["grid_id", "year", "scenario", "climate_model"]
    ].drop_duplicates()
    coverage = required_coverage.merge(
        available_coverage,
        on=["grid_id", "year", "scenario", "climate_model"],
        how="left",
        validate="one_to_one",
        indicator="_grid_coverage_merge",
    )
    missing_grid_coverage = coverage["_grid_coverage_merge"].eq("left_only")
    if missing_grid_coverage.any():
        missing = coverage.loc[
            missing_grid_coverage,
            ["grid_id", "year", "scenario", "climate_model"],
        ]
        raise ThermalStressDataError(
            "Livestock weight grids lack climate coverage for ensemble members: "
            + repr(missing.head(20).to_dict(orient="records"))
        )
    joined = climate.merge(
        weights,
        on=["grid_id", "year"],
        how="inner",
        suffixes=("_climate", "_weight"),
        validate="many_to_many",
    )
    if joined.empty:
        raise ThermalStressDataError("No exact grid/year matches between climate and livestock weights")
    joined["wet_cold"] = joined["precipitation_mm"].gt(
        cfg.wet_cold_precip_threshold_mm
    )
    joined["cold_effective_c"] = joined["wind_chill_c"] - np.where(
        joined["wet_cold"], cfg.wet_cold_penalty_c, 0.0
    )
    joined["heat_excess"] = (
        joined["thi"] - joined["heat_thi_threshold"]
    ).clip(lower=0.0)
    joined["cold_excess"] = (
        joined["lct_c"] - joined["cold_effective_c"]
    ).clip(lower=0.0)
    # Rolling loads are properties of one climate ensemble member.  Sorting or
    # grouping without the member keys interleaves identical timestamps from
    # different GCMs/scenarios and contaminates every lagged response driver.
    member_keys = ["scenario", "climate_model"]
    joined = joined.sort_values(
        member_keys
        + ["grid_id", "year", "species", "production_system", "timestamp"]
    )
    lag_keys = member_keys + ["grid_id", "year", "species", "production_system"]
    joined["heat_load_24h"] = joined.groupby(lag_keys, sort=False)["heat_excess"].transform(
        lambda series: series.rolling(24, min_periods=1).sum()
    )
    joined["heat_load_72h"] = joined.groupby(lag_keys, sort=False)["heat_excess"].transform(
        lambda series: series.rolling(72, min_periods=1).sum()
    )
    joined["cold_load_24h"] = joined.groupby(lag_keys, sort=False)["cold_excess"].transform(
        lambda series: series.rolling(24, min_periods=1).sum()
    )
    local_hour = (
        joined["timestamp"].dt.hour + joined["timezone_offset_hours"]
    ) % 24
    joined["night_heat_excess"] = np.where(
        local_hour.ge(cfg.night_start_hour) & local_hour.lt(cfg.night_end_hour),
        joined["heat_excess"],
        0.0,
    )

    group_columns = [
        "grid_id",
        "m49",
        "year",
        "species",
        "production_system",
        "scenario",
        "climate_model",
    ]
    rows: list[Dict[str, Any]] = []
    for key, group in joined.groupby(group_columns, dropna=False, sort=False):
        group = group.sort_values("timestamp")
        row = dict(zip(group_columns, key))
        heat_mask = group["heat_excess"].gt(0.0)
        cold_mask = group["cold_excess"].gt(0.0)
        heat_event_mask = _qualified_event_mask(
            heat_mask, int(cfg.heat_event_min_hours)
        )
        cold_event_mask = _qualified_event_mask(
            cold_mask, int(cfg.cold_event_min_hours)
        )
        row.update(
            {
                "grid_resolution_km": float(group["grid_resolution_km"].iloc[0]),
                "animal_weight": float(group["animal_weight"].iloc[0]),
                "livestock_weight_year": int(group["livestock_weight_year"].iloc[0]),
                "livestock_weight_source": str(group["livestock_weight_source"].iloc[0]),
                "source_dataset_version": (
                    str(group["source_dataset_version_climate"].iloc[0])
                    + "|"
                    + str(group["source_dataset_version_weight"].iloc[0])
                ),
                "animal_weight_relative_uncertainty": float(
                    group["animal_weight_relative_uncertainty"].iloc[0]
                ),
                "weight_imputation_flag": str(group["weight_imputation_flag"].iloc[0]),
                "heat_load": float(group["heat_excess"].sum()),
                "cold_load": float(group["cold_excess"].sum()),
                "heat_event_hours": int(heat_event_mask.sum()),
                "cold_event_hours": int(cold_event_mask.sum()),
                "heat_event_days": int(
                    group.loc[heat_event_mask, "timestamp"].dt.floor("D").nunique()
                ),
                "cold_event_days": int(
                    group.loc[cold_event_mask, "timestamp"].dt.floor("D").nunique()
                ),
                "longest_heat_event_hours": _longest_true_run(heat_event_mask),
                "longest_cold_event_hours": _longest_true_run(cold_event_mask),
                "nocturnal_recovery_deficit": float(group["night_heat_excess"].sum()),
                "mean_thi": float(group["thi"].mean()),
                "mean_cei": float(group["cold_excess"].mean()),
                "heat_load_p95": float(group["heat_load_24h"].quantile(0.95)),
                "cold_load_p95": float(group["cold_load_24h"].quantile(0.95)),
                "heat_load_72h_max": float(group["heat_load_72h"].max()),
                "wet_cold_hours": int((cold_mask & group["wet_cold"]).sum()),
                "source_hour_rows": int(len(group)),
            }
        )
        rows.append(row)
    output = pd.DataFrame(rows)
    # Fractions must sum to one independently for every ensemble member; a
    # pooled denominator would make weights depend on the number of GCMs.
    weight_keys = [
        "m49",
        "year",
        "species",
        "production_system",
        "scenario",
        "climate_model",
    ]
    totals = output.groupby(weight_keys)["animal_weight"].transform("sum")
    output["country_species_weight_fraction"] = np.where(
        totals.gt(0.0), output["animal_weight"] / totals, np.nan
    )
    if output["country_species_weight_fraction"].isna().any():
        raise ThermalStressDataError("Country/species/system animal weights sum to zero")
    return output.sort_values(["year", "m49", "species", "production_system", "grid_id"]).reset_index(drop=True)


def build_data_manifest(
    *,
    climate_path: str | Path,
    livestock_weights_path: str | Path,
    exposure_path: str | Path,
    config: ExposurePipelineConfig,
    row_counts: Mapping[str, int],
) -> Dict[str, Any]:
    files = {}
    for role, raw_path in {
        "climate": climate_path,
        "livestock_weights": livestock_weights_path,
        "exposure": exposure_path,
    }.items():
        path = Path(raw_path).resolve()
        files[role] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "size_bytes": int(path.stat().st_size),
            "rows": int(row_counts.get(role, 0)),
        }
    return {
        "schema_version": 1,
        "pipeline": "STS_thermal_exposure_pipeline",
        "pipeline_version": PIPELINE_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config),
        "files": files,
        "qc_status": "passed",
    }


def run_exposure_pipeline(
    *,
    climate_path: str | Path,
    livestock_weights_path: str | Path,
    output_path: str | Path,
    manifest_path: str | Path,
    config: Optional[ExposurePipelineConfig] = None,
) -> pd.DataFrame:
    cfg = config or ExposurePipelineConfig()
    climate = read_table(climate_path)
    weights = read_table(livestock_weights_path)
    output = prepare_thermal_exposure(climate, weights, config=cfg)
    output_target = Path(output_path)
    target = Path(manifest_path)
    output_target.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    generation = uuid.uuid4().hex
    output_temporary = output_target.parent / (
        f".{output_target.stem}.{generation}{output_target.suffix}"
    )
    manifest_temporary = target.parent / f".{target.name}.{generation}.tmp"
    try:
        write_table(output, output_temporary)
        manifest = build_data_manifest(
            climate_path=climate_path,
            livestock_weights_path=livestock_weights_path,
            exposure_path=output_temporary,
            config=cfg,
            row_counts={
                "climate": len(climate),
                "livestock_weights": len(weights),
                "exposure": len(output),
            },
        )
        manifest["files"]["exposure"]["path"] = str(output_target.resolve())
        manifest_temporary.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        os.replace(output_temporary, output_target)
        os.replace(manifest_temporary, target)
    except Exception:
        output_temporary.unlink(missing_ok=True)
        manifest_temporary.unlink(missing_ok=True)
        raise
    return output


__all__: Sequence[str] = (
    "ExposurePipelineConfig",
    "PIPELINE_VERSION",
    "build_data_manifest",
    "prepare_thermal_exposure",
    "relative_humidity_from_dewpoint",
    "run_exposure_pipeline",
    "sha256_file",
    "temperature_humidity_index",
    "wind_chill_temperature",
)
