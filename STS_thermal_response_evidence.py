# -*- coding: utf-8 -*-
"""STS auditable evidence-to-response-registry preparation for Phase 2."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from STS_thermal_stress_model import (
    ADDITIVE_IMPACTS,
    PRODUCTION_ROLES,
    SUPPORTED_IMPACTS,
    ThermalStressDataError,
    canonical_species,
)


EVIDENCE_SCHEMA_VERSION = 1

DESIGN_WEIGHTS = {
    "randomized": 1.0,
    "crossover": 1.0,
    "pair_fed": 1.0,
    "multi_farm_panel": 0.75,
    "single_farm_observational": 0.5,
    "mechanistic_prior": 0.35,
}
RISK_WEIGHTS = {"low": 1.0, "some_concerns": 0.7, "high": 0.35}
TRANSFER_WEIGHTS = {"high": 1.0, "medium": 0.7, "low": 0.4}


@dataclass(frozen=True)
class EvidenceFitConfig:
    minimum_studies_for_production: int = 3
    minimum_rows: int = 3
    ridge: float = 1e-10


def validate_evidence_table(evidence: pd.DataFrame) -> pd.DataFrame:
    required = [
        "study_id",
        "doi_or_standard",
        "species",
        "production_role",
        "production_system",
        "impact",
        "study_design",
        "risk_of_bias",
        "transferability",
        "heat_load",
        "cold_load",
        "response_value",
        "response_sd",
        "sample_size",
    ]
    missing = [column for column in required if column not in evidence.columns]
    if missing:
        raise ThermalStressDataError(f"Thermal response evidence missing columns: {missing}")
    df = evidence.copy()
    for column in ("study_id", "doi_or_standard", "production_system"):
        df[column] = df[column].fillna("").astype(str).str.strip()
        if df[column].eq("").any():
            raise ThermalStressDataError(f"Evidence {column} must not be blank")
    df["species"] = df["species"].map(canonical_species)
    if df["species"].isna().any():
        raise ThermalStressDataError("Evidence contains unsupported species")
    df["production_role"] = df["production_role"].astype(str).str.lower().str.strip()
    if not set(df["production_role"]).issubset(PRODUCTION_ROLES):
        raise ThermalStressDataError("Evidence contains unsupported production roles")
    df["impact"] = df["impact"].astype(str).str.strip()
    if not set(df["impact"]).issubset(SUPPORTED_IMPACTS):
        raise ThermalStressDataError("Evidence contains unsupported impacts")
    for column, allowed in (
        ("study_design", DESIGN_WEIGHTS),
        ("risk_of_bias", RISK_WEIGHTS),
        ("transferability", TRANSFER_WEIGHTS),
    ):
        df[column] = df[column].astype(str).str.lower().str.strip()
        invalid = sorted(set(df[column]) - set(allowed))
        if invalid:
            raise ThermalStressDataError(f"Evidence {column} has invalid values: {invalid}")
    numeric = ["heat_load", "cold_load", "response_value", "response_sd", "sample_size"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if df[numeric].isna().any().any():
        raise ThermalStressDataError("Evidence response fields must be numeric")
    if (df[["heat_load", "cold_load", "response_sd"]] < 0.0).any().any():
        raise ThermalStressDataError("Evidence loads/response_sd must be non-negative")
    if (df["sample_size"] <= 0.0).any():
        raise ThermalStressDataError("Evidence sample_size must be positive")
    multiplier = ~df["impact"].isin(ADDITIVE_IMPACTS)
    if (df.loc[multiplier, "response_value"] <= 0.0).any():
        raise ThermalStressDataError("Multiplier response values must be positive")
    return df.reset_index(drop=True)


def _fit_weighted_response(
    group: pd.DataFrame,
    *,
    ridge: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    additive = str(group["impact"].iloc[0]) in ADDITIVE_IMPACTS
    y = group["response_value"].to_numpy(float)
    if not additive:
        y = np.log(y)
    x = np.column_stack(
        [
            np.ones(len(group), dtype=float),
            group["heat_load"].to_numpy(float),
            group["cold_load"].to_numpy(float),
        ]
    )
    variance = np.square(group["response_sd"].to_numpy(float)) / group[
        "sample_size"
    ].to_numpy(float)
    variance = np.maximum(variance, 1e-12)
    quality = (
        group["study_design"].map(DESIGN_WEIGHTS).to_numpy(float)
        * group["risk_of_bias"].map(RISK_WEIGHTS).to_numpy(float)
        * group["transferability"].map(TRANSFER_WEIGHTS).to_numpy(float)
    )
    weights = quality / variance
    xtwx = x.T @ (weights[:, None] * x) + np.eye(3) * float(ridge)
    if np.linalg.matrix_rank(xtwx) < 3:
        raise ThermalStressDataError(
            "Evidence design cannot identify intercept, heat and cold coefficients"
        )
    inverse = np.linalg.inv(xtwx)
    beta = inverse @ (x.T @ (weights * y))
    residual = y - x @ beta
    dof = max(1, len(y) - 3)
    residual_variance = float(np.sum(weights * residual**2) / dof) / max(
        float(np.mean(weights)), 1e-12
    )
    covariance = inverse * max(residual_variance, 1e-12)
    return beta, covariance, residual


def build_response_registry_from_evidence(
    evidence: pd.DataFrame,
    *,
    config: Optional[EvidenceFitConfig] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit weighted response rows and study-held-out diagnostics.

    This is a transparent linear meta-regression, not a substitute for the
    planned hierarchical species/stage model.  Rows remain ``candidate`` until
    the configured independent-study gate is satisfied.
    """
    cfg = config or EvidenceFitConfig()
    data = validate_evidence_table(evidence)
    keys = ["species", "production_role", "production_system", "impact"]
    registry_rows: list[Dict[str, Any]] = []
    validation_rows: list[Dict[str, Any]] = []
    for key, group in data.groupby(keys, dropna=False, sort=True):
        studies = sorted(group["study_id"].unique())
        if len(group) < cfg.minimum_rows:
            raise ThermalStressDataError(f"Too few evidence rows for {key}: {len(group)}")
        beta, covariance, residual = _fit_weighted_response(group, ridge=cfg.ridge)
        additive = str(key[3]) in ADDITIVE_IMPACTS
        intercept = float(beta[0] if additive else np.exp(beta[0]))
        source_ids = sorted(group["doi_or_standard"].unique())
        status = (
            "production"
            if len(studies) >= cfg.minimum_studies_for_production
            else "candidate_insufficient_independent_studies"
        )
        registry_rows.append(
            {
                **dict(zip(keys, key)),
                "response_form": "additive_rate" if additive else "exponential_multiplier",
                "intercept": intercept,
                "heat_coefficient": float(beta[1]),
                "cold_coefficient": float(beta[2]),
                "heat_load_scale": 1.0,
                "cold_load_scale": 1.0,
                "lower_bound": -1.0 if additive else 0.01,
                "upper_bound": 0.95 if additive else 10.0,
                "heat_driver": "heat_load",
                "cold_driver": "cold_load",
                "intercept_sd": float(np.sqrt(max(covariance[0, 0], 0.0))),
                "heat_coefficient_sd": float(np.sqrt(max(covariance[1, 1], 0.0))),
                "cold_coefficient_sd": float(np.sqrt(max(covariance[2, 2], 0.0))),
                "study_count": len(studies),
                "evidence_row_count": len(group),
                "source_id": "|".join(source_ids),
                "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
                "parameter_status": status,
            }
        )
        for study_id in studies:
            train = group[~group["study_id"].eq(study_id)]
            test = group[group["study_id"].eq(study_id)]
            if len(train) < cfg.minimum_rows or len(train) < 3:
                continue
            try:
                loo_beta, _, _ = _fit_weighted_response(train, ridge=cfg.ridge)
            except ThermalStressDataError:
                continue
            x_test = np.column_stack(
                [
                    np.ones(len(test)),
                    test["heat_load"].to_numpy(float),
                    test["cold_load"].to_numpy(float),
                ]
            )
            prediction = x_test @ loo_beta
            observed = test["response_value"].to_numpy(float)
            if not additive:
                prediction = np.exp(prediction)
            for obs, pred in zip(observed, prediction):
                validation_rows.append(
                    {
                        **dict(zip(keys, key)),
                        "held_out_study_id": study_id,
                        "observed": float(obs),
                        "predicted": float(pred),
                        "residual": float(obs - pred),
                    }
                )
    registry = pd.DataFrame(registry_rows)
    validation = pd.DataFrame(validation_rows)
    if not validation.empty:
        validation["squared_error"] = validation["residual"] ** 2
    return registry, validation


def prepare_response_registry_files(
    *,
    evidence_path: str | Path,
    registry_output_path: str | Path,
    validation_output_path: str | Path,
    config: Optional[EvidenceFitConfig] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    evidence = pd.read_csv(evidence_path)
    registry, validation = build_response_registry_from_evidence(evidence, config=config)
    Path(registry_output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(validation_output_path).parent.mkdir(parents=True, exist_ok=True)
    registry.to_csv(registry_output_path, index=False)
    validation.to_csv(validation_output_path, index=False)
    return registry, validation


__all__ = [
    "EvidenceFitConfig",
    "build_response_registry_from_evidence",
    "prepare_response_registry_files",
    "validate_evidence_table",
]
