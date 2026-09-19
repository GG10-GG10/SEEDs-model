# -*- coding: utf-8 -*-
"""STS Phase 5 climate/parameter ensemble and external-validation utilities."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from STS_thermal_stress_model import (
    ThermalStressDataError,
    ThermalStressSettings,
    apply_thermal_adaptation,
    build_thermal_stress_bundle,
    validate_exposure_manifest,
)


ExposureIndexTransform = Callable[[pd.DataFrame], pd.DataFrame]
FrameSampler = Callable[[pd.DataFrame, int, np.random.Generator], pd.DataFrame]
AdaptationKey = Tuple[str, str, int]
AdaptationSampler = Callable[
    [Mapping[AdaptationKey, float], int, np.random.Generator],
    Mapping[AdaptationKey, float],
]


def _read_ensemble_table(path: str | Path, label: str) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"{label} not found: {source}")
    suffix = source.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(source)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(source)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    raise ThermalStressDataError(
        f"Unsupported {label} format {suffix!r}: {source}"
    )


def _functional_frame_fingerprint(
    frame: pd.DataFrame, columns: Sequence[str]
) -> str:
    selected_columns = [column for column in columns if column in frame.columns]
    if not selected_columns:
        raise ThermalStressDataError(
            "Cannot fingerprint ensemble input without functional columns"
        )
    normalized = frame[selected_columns].copy()
    for column in selected_columns:
        normalized[column] = normalized[column].map(
            lambda value: "<NA>" if pd.isna(value) else repr(value)
        )
    normalized = normalized.sort_values(selected_columns).reset_index(drop=True)
    payload = normalized.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _adaptation_fingerprint(values: Mapping[AdaptationKey, float]) -> str:
    normalized: list[tuple[str, str, int, float]] = []
    for key, value in values.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise ThermalStressDataError(
                "Adaptation ensemble keys must be (country, commodity, year)"
            )
        country, commodity, year = key
        try:
            normalized.append(
                (str(country), str(commodity), int(year), float(value))
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise ThermalStressDataError(
                f"Invalid adaptation ensemble value for {key!r}: {value!r}"
            ) from exc
    normalized.sort()
    return hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _require_frame(result: Any, label: str) -> pd.DataFrame:
    if not isinstance(result, pd.DataFrame) or result.empty:
        raise ThermalStressDataError(
            f"{label} must return a non-empty pandas DataFrame"
        )
    return result.copy()


def _dimension_rng(seed: int, dimension_code: int, draw: int) -> np.random.Generator:
    if seed < 0 or draw < 0:
        raise ThermalStressDataError("Ensemble seed and draw indices must be non-negative")
    return np.random.default_rng(np.random.SeedSequence([seed, dimension_code, draw]))


def _dimension_is_active(values: pd.Series) -> bool:
    numeric = pd.to_numeric(values, errors="coerce")
    return bool(numeric.nunique(dropna=False) > 1 or numeric.ne(0).any())


def _validate_dimension_propagation(
    metadata: pd.DataFrame,
    *,
    dimension: str,
    fingerprint: str,
) -> None:
    distinct_draws = metadata[dimension].nunique(dropna=False)
    if distinct_draws <= 1:
        return
    mapping = metadata[[dimension, fingerprint]].drop_duplicates()
    if mapping.groupby(dimension, dropna=False)[fingerprint].nunique().max() != 1:
        raise ThermalStressDataError(
            f"Ensemble {dimension} sampler is not deterministic for each draw"
        )
    if mapping[fingerprint].nunique() != distinct_draws:
        raise ThermalStressDataError(
            f"Ensemble {dimension} remains label-only after applying its sampler"
        )


def build_uncertainty_design(
    exposure: pd.DataFrame,
    *,
    response_draws: int,
    seed: int = 0,
    exposure_index_names: Optional[Iterable[str]] = None,
    livestock_mapping_draws: int = 1,
    emission_factor_draws: int = 1,
    adaptation_efficiency_draws: int = 1,
) -> pd.DataFrame:
    """Cross climate structure with named parameter-uncertainty dimensions."""
    validated_counts: Dict[str, int] = {}
    for label, count in (
        ("response_draws", response_draws),
        ("livestock_mapping_draws", livestock_mapping_draws),
        ("emission_factor_draws", emission_factor_draws),
        ("adaptation_efficiency_draws", adaptation_efficiency_draws),
    ):
        try:
            numeric_count = float(count)
        except (TypeError, ValueError) as exc:
            raise ThermalStressDataError(
                f"{label} must be a positive integer"
            ) from exc
        if (
            not np.isfinite(numeric_count)
            or numeric_count < 1.0
            or not numeric_count.is_integer()
        ):
            raise ThermalStressDataError(f"{label} must be a positive integer")
        validated_counts[label] = int(numeric_count)
    try:
        validated_seed = int(seed)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ThermalStressDataError("seed must be a non-negative integer") from exc
    if validated_seed < 0 or float(seed) != float(validated_seed):
        raise ThermalStressDataError("seed must be a non-negative integer")
    required = {"year", "scenario", "climate_model"}
    missing = sorted(required - set(exposure.columns))
    if missing:
        raise ThermalStressDataError(f"Uncertainty design exposure missing: {missing}")
    future = exposure[pd.to_numeric(exposure["year"], errors="coerce").gt(2020)]
    climates = future[["scenario", "climate_model"]].drop_duplicates()
    if climates.empty:
        climates = pd.DataFrame([{"scenario": "historical", "climate_model": "observed"}])
    indices = [str(value).strip() for value in (exposure_index_names or ["default_heat_cold"])]
    if not indices or any(not value for value in indices) or len(indices) != len(set(indices)):
        raise ThermalStressDataError(
            "Exposure index names must be non-empty and unique"
        )
    rows: list[Dict[str, Any]] = []
    draw_id = 0
    for climate in climates.itertuples(index=False):
        for exposure_index in indices:
            for response_draw in range(validated_counts["response_draws"]):
                for mapping_draw in range(validated_counts["livestock_mapping_draws"]):
                    for ef_draw in range(validated_counts["emission_factor_draws"]):
                        for adaptation_draw in range(
                            validated_counts["adaptation_efficiency_draws"]
                        ):
                            rows.append(
                                {
                                    "ensemble_draw": draw_id,
                                    "scenario": str(climate.scenario),
                                    "climate_model": str(climate.climate_model),
                                    "exposure_index": str(exposure_index),
                                    "response_draw": response_draw,
                                    "livestock_mapping_draw": mapping_draw,
                                    "emission_factor_draw": ef_draw,
                                    "adaptation_efficiency_draw": adaptation_draw,
                                    "seed": validated_seed,
                                }
                            )
                            draw_id += 1
    return pd.DataFrame(rows)


def run_thermal_bundle_ensemble(
    design: pd.DataFrame,
    *,
    exposure_path: str | Path,
    response_registry_path: str | Path,
    commodity_map_path: str | Path,
    target_years: Iterable[int],
    base_settings: ThermalStressSettings,
    data_manifest_path: Optional[str | Path] = None,
    strain_registry_path: Optional[str | Path] = None,
    activity_factor_path: Optional[str | Path] = None,
    pollutant_factor_path: Optional[str | Path] = None,
    exposure_index_transforms: Optional[
        Mapping[str, ExposureIndexTransform]
    ] = None,
    livestock_mapping_sampler: Optional[FrameSampler] = None,
    emission_factor_sampler: Optional[FrameSampler] = None,
    adaptation_efficiency_sampler: Optional[AdaptationSampler] = None,
    adaptation_multiplier_by: Optional[Mapping[AdaptationKey, float]] = None,
) -> pd.DataFrame:
    """Run an auditable ensemble whose declared dimensions alter real inputs.

    Non-default exposure indices and non-neutral mapping, emission-factor or
    adaptation draws require explicit caller-supplied transforms. This avoids
    inventing scientific uncertainty distributions inside the runtime.
    """
    required = {"ensemble_draw", "scenario", "climate_model", "response_draw", "seed"}
    missing = sorted(required - set(design.columns))
    if missing:
        raise ThermalStressDataError(f"Ensemble design missing columns: {missing}")
    if design.empty:
        raise ThermalStressDataError("Ensemble design must not be empty")
    design_work = design.copy()
    optional_defaults: Dict[str, Any] = {
        "exposure_index": "default_heat_cold",
        "livestock_mapping_draw": 0,
        "emission_factor_draw": 0,
        "adaptation_efficiency_draw": 0,
    }
    for column, default in optional_defaults.items():
        if column not in design_work.columns:
            design_work[column] = default
    if design_work["ensemble_draw"].duplicated().any():
        raise ThermalStressDataError("Ensemble design has duplicate ensemble_draw values")
    for column in (
        "ensemble_draw",
        "response_draw",
        "livestock_mapping_draw",
        "emission_factor_draw",
        "adaptation_efficiency_draw",
        "seed",
    ):
        values = pd.to_numeric(design_work[column], errors="coerce")
        numeric = values.to_numpy(dtype=float)
        if (
            not np.isfinite(numeric).all()
            or (numeric < 0.0).any()
            or not np.equal(numeric, np.floor(numeric)).all()
        ):
            raise ThermalStressDataError(
                f"Ensemble {column} values must be finite non-negative integers"
            )
        design_work[column] = values.astype(int)
    for column in ("scenario", "climate_model", "exposure_index"):
        if design_work[column].isna().any():
            raise ThermalStressDataError(f"Ensemble {column} values must not be missing")
        design_work[column] = design_work[column].astype(str).str.strip()
        if design_work[column].eq("").any():
            raise ThermalStressDataError(f"Ensemble {column} values must not be blank")

    index_transforms = dict(exposure_index_transforms or {})
    missing_index_transforms = sorted(
        {
            value
            for value in design_work["exposure_index"].unique()
            if value != "default_heat_cold" and value not in index_transforms
        }
    )
    label_only: list[str] = []
    if missing_index_transforms:
        label_only.append(
            "exposure_index=" + repr(missing_index_transforms)
        )
    if _dimension_is_active(design_work["livestock_mapping_draw"]) and (
        livestock_mapping_sampler is None
    ):
        label_only.append("livestock_mapping_draw")
    if _dimension_is_active(design_work["emission_factor_draw"]) and (
        emission_factor_sampler is None
    ):
        label_only.append("emission_factor_draw")
    if _dimension_is_active(design_work["adaptation_efficiency_draw"]) and (
        adaptation_efficiency_sampler is None
    ):
        label_only.append("adaptation_efficiency_draw")
    if label_only:
        raise ThermalStressDataError(
            "Ensemble design contains label-only dimensions without concrete "
            "input transforms: "
            + ", ".join(label_only)
        )
    if emission_factor_sampler is not None and pollutant_factor_path is None:
        raise ThermalStressDataError(
            "emission_factor_sampler requires pollutant_factor_path"
        )
    base_adaptation = dict(adaptation_multiplier_by or {})
    if adaptation_efficiency_sampler is not None and not base_adaptation:
        raise ThermalStressDataError(
            "adaptation_efficiency_sampler requires adaptation_multiplier_by"
        )

    base_exposure = _read_ensemble_table(exposure_path, "ensemble exposure")
    base_pollutant = (
        _read_ensemble_table(pollutant_factor_path, "ensemble pollutant factors")
        if pollutant_factor_path is not None
        else None
    )
    validate_exposure_manifest(
        data_manifest_path,
        exposure_path=exposure_path,
        required=bool(base_settings.strict and base_settings.require_data_manifest),
    )
    target_year_list = tuple(int(year) for year in target_years)
    exposure_index_columns = [
        "grid_id",
        "m49",
        "year",
        "species",
        "production_system",
        "scenario",
        "climate_model",
        "heat_load",
        "cold_load",
    ]
    livestock_mapping_columns = [
        "grid_id",
        "m49",
        "year",
        "species",
        "production_system",
        "scenario",
        "climate_model",
        "animal_weight",
        "livestock_weight_year",
        "animal_weight_relative_uncertainty",
        "weight_imputation_flag",
    ]
    emission_factor_columns = [
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
    ]
    outputs: list[pd.DataFrame] = []
    metadata_rows: list[Dict[str, Any]] = []
    with TemporaryDirectory(prefix="sts_thermal_ensemble_") as temp_directory:
        temp_root = Path(temp_directory)
        for row in design_work.itertuples(index=False):
            exposure_index = str(row.exposure_index)
            exposure_for_index = base_exposure.copy()
            index_transform = index_transforms.get(exposure_index)
            if index_transform is not None:
                exposure_for_index = _require_frame(
                    index_transform(exposure_for_index.copy()),
                    f"Exposure index transform {exposure_index!r}",
                )
            exposure_fingerprint = _functional_frame_fingerprint(
                exposure_for_index, exposure_index_columns
            )

            exposure_for_draw = exposure_for_index
            if livestock_mapping_sampler is not None:
                exposure_for_draw = _require_frame(
                    livestock_mapping_sampler(
                        exposure_for_index.copy(),
                        int(row.livestock_mapping_draw),
                        _dimension_rng(
                            int(row.seed), 1, int(row.livestock_mapping_draw)
                        ),
                    ),
                    "Livestock mapping sampler",
                )
            mapping_fingerprint = _functional_frame_fingerprint(
                exposure_for_draw, livestock_mapping_columns
            )
            transformed_exposure_path = (
                temp_root / f"exposure_{int(row.ensemble_draw)}.csv"
            )
            exposure_for_draw.to_csv(transformed_exposure_path, index=False)

            pollutant_for_draw = base_pollutant.copy() if base_pollutant is not None else None
            transformed_pollutant_path: Optional[Path] = None
            if pollutant_for_draw is not None:
                if emission_factor_sampler is not None:
                    pollutant_for_draw = _require_frame(
                        emission_factor_sampler(
                            pollutant_for_draw.copy(),
                            int(row.emission_factor_draw),
                            _dimension_rng(
                                int(row.seed), 2, int(row.emission_factor_draw)
                            ),
                        ),
                        "Emission factor sampler",
                    )
                emission_fingerprint = _functional_frame_fingerprint(
                    pollutant_for_draw, emission_factor_columns
                )
                transformed_pollutant_path = (
                    temp_root / f"pollutant_{int(row.ensemble_draw)}.csv"
                )
                pollutant_for_draw.to_csv(transformed_pollutant_path, index=False)
            else:
                emission_fingerprint = "not_supplied"

            adaptation_for_draw: Mapping[AdaptationKey, float] = base_adaptation.copy()
            if adaptation_efficiency_sampler is not None:
                sampled_adaptation = adaptation_efficiency_sampler(
                    base_adaptation.copy(),
                    int(row.adaptation_efficiency_draw),
                    _dimension_rng(
                        int(row.seed), 3, int(row.adaptation_efficiency_draw)
                    ),
                )
                if not isinstance(sampled_adaptation, Mapping) or not sampled_adaptation:
                    raise ThermalStressDataError(
                        "Adaptation efficiency sampler must return a non-empty mapping"
                    )
                adaptation_for_draw = dict(sampled_adaptation)
            adaptation_fingerprint = _adaptation_fingerprint(adaptation_for_draw)

            settings = replace(
                base_settings,
                enabled=True,
                future_scenario=str(row.scenario),
                climate_model=str(row.climate_model),
                uncertainty_draw=int(row.response_draw),
                uncertainty_seed=int(row.seed),
                require_data_manifest=False,
            )
            bundle = build_thermal_stress_bundle(
                exposure_path=transformed_exposure_path,
                response_registry_path=response_registry_path,
                commodity_map_path=commodity_map_path,
                data_manifest_path=None,
                strain_registry_path=strain_registry_path,
                activity_factor_path=activity_factor_path,
                pollutant_factor_path=transformed_pollutant_path,
                settings=settings,
                target_years=target_year_list,
            )
            if adaptation_for_draw:
                apply_thermal_adaptation(bundle, adaptation_for_draw)
            fingerprints = {
                "exposure_index_input_fingerprint": exposure_fingerprint,
                "livestock_mapping_draw_input_fingerprint": mapping_fingerprint,
                "emission_factor_draw_input_fingerprint": emission_fingerprint,
                "adaptation_efficiency_draw_input_fingerprint": adaptation_fingerprint,
            }
            impacts = bundle.commodity_impacts.copy()
            impacts["ensemble_draw"] = int(row.ensemble_draw)
            impacts["response_draw"] = int(row.response_draw)
            impacts["ensemble_scenario"] = str(row.scenario)
            impacts["ensemble_climate_model"] = str(row.climate_model)
            for dimension in optional_defaults:
                impacts[dimension] = getattr(row, dimension)
            for column, fingerprint in fingerprints.items():
                impacts[column] = fingerprint
            outputs.append(impacts)
            metadata_rows.append(
                {
                    "ensemble_draw": int(row.ensemble_draw),
                    **{
                        dimension: getattr(row, dimension)
                        for dimension in optional_defaults
                    },
                    **fingerprints,
                }
            )
    metadata = pd.DataFrame(metadata_rows)
    for dimension in optional_defaults:
        _validate_dimension_propagation(
            metadata,
            dimension=dimension,
            fingerprint=f"{dimension}_input_fingerprint",
        )
    return pd.concat(outputs, ignore_index=True) if outputs else pd.DataFrame()


def summarize_ensemble(
    draws: pd.DataFrame,
    *,
    value_columns: Sequence[str],
    group_columns: Sequence[str] = ("m49", "year", "commodity"),
    quantiles: Sequence[float] = (0.05, 0.5, 0.95),
) -> pd.DataFrame:
    missing = sorted(set(group_columns).union(value_columns) - set(draws.columns))
    if missing:
        raise ThermalStressDataError(f"Ensemble summary missing columns: {missing}")
    rows: list[Dict[str, Any]] = []
    for key, group in draws.groupby(list(group_columns), dropna=False, sort=True):
        base = dict(zip(group_columns, key if isinstance(key, tuple) else (key,)))
        for value_column in value_columns:
            values = pd.to_numeric(group[value_column], errors="coerce").dropna()
            if values.empty:
                continue
            row = {
                **base,
                "metric": value_column,
                "draw_count": int(len(values)),
                "mean": float(values.mean()),
                "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            }
            for quantile in quantiles:
                row[f"q{int(round(quantile * 100)):02d}"] = float(values.quantile(quantile))
            rows.append(row)
    return pd.DataFrame(rows)


def validate_against_observations(
    modeled: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    key_columns: Sequence[str],
    modeled_value: str,
    observed_value: str,
    group_columns: Sequence[str] = (),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_model = set(key_columns) | {modeled_value}
    required_observed = set(key_columns) | {observed_value}
    if not required_model.issubset(modeled.columns) or not required_observed.issubset(observed.columns):
        raise ThermalStressDataError("Modeled/observed validation schema is incomplete")
    model = modeled[list(key_columns) + [modeled_value]].copy()
    obs = observed[list(key_columns) + [observed_value]].copy()
    paired = model.merge(obs, on=list(key_columns), how="inner", validate="many_to_one")
    paired[modeled_value] = pd.to_numeric(paired[modeled_value], errors="coerce")
    paired[observed_value] = pd.to_numeric(paired[observed_value], errors="coerce")
    paired = paired.dropna(subset=[modeled_value, observed_value])
    if paired.empty:
        raise ThermalStressDataError("No modeled/observed validation pairs matched")
    paired["error"] = paired[modeled_value] - paired[observed_value]
    paired["absolute_error"] = paired["error"].abs()
    paired["squared_error"] = paired["error"] ** 2
    groups = list(group_columns)
    iterator = paired.groupby(groups, dropna=False, sort=True) if groups else [((), paired)]
    metrics: list[Dict[str, Any]] = []
    for key, group in iterator:
        key_tuple = key if isinstance(key, tuple) else (key,)
        correlation = (
            float(group[[modeled_value, observed_value]].corr().iloc[0, 1])
            if len(group) > 1
            else float("nan")
        )
        metrics.append(
            {
                **dict(zip(groups, key_tuple)),
                "n": int(len(group)),
                "bias": float(group["error"].mean()),
                "mae": float(group["absolute_error"].mean()),
                "rmse": float(np.sqrt(group["squared_error"].mean())),
                "correlation": correlation,
            }
        )
    return paired, pd.DataFrame(metrics)


def write_validation_report(
    output_path: str | Path,
    *,
    ensemble_summary: pd.DataFrame,
    validation_metrics: Optional[pd.DataFrame] = None,
    provenance: Optional[Dict[str, Any]] = None,
) -> None:
    payload = {
        "schema_version": 1,
        "ensemble_summary_rows": int(len(ensemble_summary)),
        "validation_available": bool(
            validation_metrics is not None and not validation_metrics.empty
        ),
        "validation_metrics": (
            validation_metrics.to_dict(orient="records")
            if validation_metrics is not None and not validation_metrics.empty
            else []
        ),
        "provenance": provenance or {},
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


__all__ = [
    "AdaptationSampler",
    "ExposureIndexTransform",
    "FrameSampler",
    "build_uncertainty_design",
    "run_thermal_bundle_ensemble",
    "summarize_ensemble",
    "validate_against_observations",
    "write_validation_report",
]
