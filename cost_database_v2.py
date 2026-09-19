# -*- coding: utf-8 -*-
"""Strict runtime loader for the versioned food mitigation cost database.

The runtime artifact is JSON with two top-level members::

    {
      "metadata": {
        "database_version": "v2.0-...",
        "schema_version": "food_mitigation_cost_database.v2",
        "cost_unit": "USD/tCO2e",
        "target_year": 2080,
        "record_count": 1710,
        "source": "...",
        "source_sha256": "<64 hex characters>",
        "strategy_mapping": {"ruminant_reduction": "RuminantReduction", ...}
      },
      "solver_export": [...]
    }

This module deliberately fails closed.  The solver must never silently run with
an incomplete, differently versioned, or differently dimensioned cost table.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Mapping, Tuple


VERSION_PREFIX = "v2.0"
SCHEMA_VERSION = "food_mitigation_cost_database.v2"
COST_UNIT = "USD/tCO2e"
TARGET_YEAR = 2080
FULL_COUNTRY_COUNT = 190

STRATEGY_KIND_TO_MODEL_PROCESS_KEY: Dict[str, str] = {
    "ruminant_reduction": "RuminantReduction",
    "losses_ratio": "LossWaste",
    "yield_rate": "YieldRate",
    "feed_intensity": "FeedEfficiency",
    "enteric_fermentation_management": "EntericF",
    "manure_management": "Manure",
    "crop_residue_soil_management": "Residue",
    "rice_management": "Rice",
    "fertilizer_efficiency": "Fertilizer",
}
MODEL_PROCESS_KEY_TO_STRATEGY_KIND: Dict[str, str] = {
    model_key: strategy_kind
    for strategy_kind, model_key in STRATEGY_KIND_TO_MODEL_PROCESS_KEY.items()
}

SYSTEM_STRATEGY_KEYS: Tuple[str, ...] = (
    "RuminantReduction",
    "LossWaste",
    "YieldRate",
    "FeedEfficiency",
)
PROCESS_KEYS: Tuple[str, ...] = (
    "EntericF",
    "Manure",
    "Residue",
    "Rice",
    "Fertilizer",
)
ALL_STRATEGY_KEYS: Tuple[str, ...] = SYSTEM_STRATEGY_KEYS + PROCESS_KEYS

# Explicit aliases make the public contract easy to discover for callers that
# use "cost" terminology rather than the workbook's "process" terminology.
STRATEGY_TO_PROCESS_KEY = STRATEGY_KIND_TO_MODEL_PROCESS_KEY
PROCESS_KEY_TO_STRATEGY = MODEL_PROCESS_KEY_TO_STRATEGY_KIND
STRATEGY_KIND_TO_KEY = STRATEGY_KIND_TO_MODEL_PROCESS_KEY
KEY_TO_STRATEGY_KIND = MODEL_PROCESS_KEY_TO_STRATEGY_KIND
SYSTEM_STRATEGY_KINDS: Tuple[str, ...] = tuple(
    MODEL_PROCESS_KEY_TO_STRATEGY_KIND[key] for key in SYSTEM_STRATEGY_KEYS
)
PROCESS_STRATEGY_KINDS: Tuple[str, ...] = tuple(
    MODEL_PROCESS_KEY_TO_STRATEGY_KIND[key] for key in PROCESS_KEYS
)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_MISSING = object()


class CostDatabaseValidationError(ValueError):
    """Raised when a v2 runtime artifact violates its data contract."""


@dataclass(frozen=True)
class MitigationCostDatabase:
    """Validated, solver-ready mitigation costs.

    ``unit_costs`` is keyed by ``("'004", "RuminantReduction")``-style
    pairs.  Zero costs are intentionally retained.  ``strategy_metadata`` is
    keyed by model process key and records both the strategy kind and cost
    layer, so callers do not need to duplicate the mapping contract.
    """

    version: str
    schema: str
    source: Any
    sha256: str
    records: Tuple[Mapping[str, Any], ...]
    unit_costs: Mapping[Tuple[str, str], float]
    strategy_metadata: Mapping[str, Mapping[str, Any]]
    unit: str
    target_year: int
    metadata: Mapping[str, Any]

    @property
    def schema_version(self) -> str:
        """Compatibility alias for callers using the metadata field name."""

        return self.schema

    @property
    def source_sha256(self) -> str:
        """Return the declared source hash, distinct from this JSON's hash."""

        raw = self.metadata.get("source_sha256", "")
        return str(raw)

    @property
    def strategy_kind_to_key(self) -> Mapping[str, str]:
        """Return the validated strategy-kind to solver-key bijection."""

        return dict(STRATEGY_KIND_TO_MODEL_PROCESS_KEY)

    @property
    def key_to_strategy_kind(self) -> Mapping[str, str]:
        """Return the inverse solver-key to strategy-kind bijection."""

        return dict(MODEL_PROCESS_KEY_TO_STRATEGY_KIND)


def file_sha256(path: str | Path) -> str:
    """Return the lowercase SHA-256 digest of *path* without loading it whole."""

    source_path = Path(path)
    digest = hashlib.sha256()
    with source_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pick(
    data: Mapping[str, Any],
    aliases: Tuple[str, ...],
    *,
    context: str,
    required: bool = True,
) -> Any:
    present = [name for name in aliases if name in data]
    if not present:
        if required:
            raise CostDatabaseValidationError(
                f"{context}: missing required field {aliases[0]!r}"
            )
        return _MISSING
    first_value = data[present[0]]
    for name in present[1:]:
        if data[name] != first_value:
            raise CostDatabaseValidationError(
                f"{context}: conflicting aliases {present!r}"
            )
    return first_value


def _require_nonempty_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CostDatabaseValidationError(f"metadata.{field} must be non-empty text")
    return value.strip()


def _require_integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CostDatabaseValidationError(f"{field} must be an integer")
    return int(value)


def _require_finite_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CostDatabaseValidationError(f"{field} must be a JSON number")
    result = float(value)
    if not math.isfinite(result):
        raise CostDatabaseValidationError(f"{field} must be finite")
    return result


def _canonical_m49(value: Any, *, context: str) -> str:
    if isinstance(value, bool):
        raise CostDatabaseValidationError(f"{context}: M49 must be a three-digit code")
    if isinstance(value, int):
        numeric = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise CostDatabaseValidationError(
                f"{context}: M49 must be an integer-valued code"
            )
        numeric = int(value)
    elif isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith("'"):
            cleaned = cleaned[1:]
        if not cleaned.isdigit() or len(cleaned) > 3:
            raise CostDatabaseValidationError(
                f"{context}: M49 must contain at most three digits"
            )
        numeric = int(cleaned)
    else:
        raise CostDatabaseValidationError(f"{context}: unsupported M49 value {value!r}")
    if not 0 <= numeric <= 999:
        raise CostDatabaseValidationError(f"{context}: M49 is outside 000..999")
    return f"'{numeric:03d}"


def _normalise_expected_m49(expected_m49: Iterable[Any]) -> Tuple[str, ...]:
    result = tuple(
        _canonical_m49(value, context="expected_m49") for value in expected_m49
    )
    if not result:
        raise CostDatabaseValidationError("expected_m49 must not be empty")
    if len(result) != len(set(result)):
        raise CostDatabaseValidationError(
            "expected_m49 contains duplicate codes after M49 normalisation"
        )
    return result


def _read_strategy_mapping(metadata: Mapping[str, Any]) -> Dict[str, str]:
    raw = _pick(
        metadata,
        ("strategy_mapping", "strategy_kind_to_model_process_key"),
        context="metadata",
    )
    if isinstance(raw, Mapping):
        mapping = {str(key): str(value) for key, value in raw.items()}
    elif isinstance(raw, list):
        mapping = {}
        for index, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise CostDatabaseValidationError(
                    f"metadata.strategy_mapping[{index}] must be an object"
                )
            strategy_kind = _pick(
                item,
                ("strategy_kind", "Strategy_kind"),
                context=f"metadata.strategy_mapping[{index}]",
            )
            model_key = _pick(
                item,
                ("model_process_key", "Model_process_key", "Process"),
                context=f"metadata.strategy_mapping[{index}]",
            )
            if str(strategy_kind) in mapping:
                raise CostDatabaseValidationError(
                    "metadata.strategy_mapping contains duplicate strategy kinds"
                )
            mapping[str(strategy_kind)] = str(model_key)
    else:
        raise CostDatabaseValidationError(
            "metadata.strategy_mapping must be an object or a list of objects"
        )

    if mapping != STRATEGY_KIND_TO_MODEL_PROCESS_KEY:
        raise CostDatabaseValidationError(
            "metadata.strategy_mapping does not match the required nine-strategy bijection"
        )
    if len(set(mapping.values())) != len(mapping):
        raise CostDatabaseValidationError(
            "metadata.strategy_mapping is not one-to-one"
        )
    return mapping


def _validate_key_partition(metadata: Mapping[str, Any]) -> None:
    raw_system_keys = _pick(
        metadata,
        ("system_strategy_keys",),
        context="metadata",
    )
    raw_process_keys = _pick(
        metadata,
        ("process_keys", "process_cost_keys"),
        context="metadata",
    )
    if not isinstance(raw_system_keys, list) or tuple(raw_system_keys) != SYSTEM_STRATEGY_KEYS:
        raise CostDatabaseValidationError(
            "metadata.system_strategy_keys must match the ordered four-key v2 contract"
        )
    if not isinstance(raw_process_keys, list) or tuple(raw_process_keys) != PROCESS_KEYS:
        raise CostDatabaseValidationError(
            "metadata.process_keys must match the ordered five-key v2 contract"
        )


def _strategy_metadata(metadata: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {
        model_key: {
            "strategy_kind": strategy_kind,
            "model_process_key": model_key,
            "cost_layer": (
                "strategy_incremental"
                if model_key in SYSTEM_STRATEGY_KEYS
                else "process_abatement"
            ),
        }
        for strategy_kind, model_key in STRATEGY_KIND_TO_MODEL_PROCESS_KEY.items()
    }

    raw = metadata.get("strategy_metadata")
    if raw is None:
        return result
    if isinstance(raw, Mapping):
        entries = []
        for key, value in raw.items():
            if not isinstance(value, Mapping):
                raise CostDatabaseValidationError(
                    "metadata.strategy_metadata values must be objects"
                )
            entry = dict(value)
            entry.setdefault("model_process_key", key)
            entries.append(entry)
    elif isinstance(raw, list):
        entries = raw
    else:
        raise CostDatabaseValidationError(
            "metadata.strategy_metadata must be an object or list"
        )

    seen = set()
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, Mapping):
            raise CostDatabaseValidationError(
                f"metadata.strategy_metadata[{index}] must be an object"
            )
        entry = dict(raw_entry)
        model_key = str(
            _pick(
                entry,
                ("model_process_key", "Model_process_key", "Process"),
                context=f"metadata.strategy_metadata[{index}]",
            )
        )
        strategy_kind = str(
            _pick(
                entry,
                ("strategy_kind", "Strategy_kind"),
                context=f"metadata.strategy_metadata[{index}]",
            )
        )
        if model_key in seen:
            raise CostDatabaseValidationError(
                "metadata.strategy_metadata contains duplicate model keys"
            )
        seen.add(model_key)
        if STRATEGY_KIND_TO_MODEL_PROCESS_KEY.get(strategy_kind) != model_key:
            raise CostDatabaseValidationError(
                f"metadata.strategy_metadata[{index}] has an invalid strategy mapping"
            )
        expected_layer = (
            "strategy_incremental"
            if model_key in SYSTEM_STRATEGY_KEYS
            else "process_abatement"
        )
        supplied_layer = entry.get("cost_layer", expected_layer)
        if supplied_layer != expected_layer:
            raise CostDatabaseValidationError(
                f"metadata.strategy_metadata[{index}] has cost_layer "
                f"{supplied_layer!r}; expected {expected_layer!r}"
            )
        entry["strategy_kind"] = strategy_kind
        entry["model_process_key"] = model_key
        entry["cost_layer"] = expected_layer
        result[model_key] = entry

    if seen != set(ALL_STRATEGY_KEYS):
        missing = sorted(set(ALL_STRATEGY_KEYS) - seen)
        extra = sorted(seen - set(ALL_STRATEGY_KEYS))
        raise CostDatabaseValidationError(
            "metadata.strategy_metadata must cover exactly nine model keys; "
            f"missing={missing}, extra={extra}"
        )
    return result


def _normalise_record(
    raw: Mapping[str, Any],
    index: int,
    *,
    expected_version: str,
) -> Dict[str, Any]:
    context = f"solver_export[{index}]"
    row_version = str(
        _pick(raw, ("database_version",), context=context)
    ).strip()
    if row_version != expected_version:
        raise CostDatabaseValidationError(
            f"{context}.database_version must equal metadata.database_version "
            f"{expected_version!r}; got {row_version!r}"
        )
    m49 = _canonical_m49(
        _pick(
            raw,
            ("M49_Country_Code", "m49_country_code", "m49"),
            context=context,
        ),
        context=context,
    )
    strategy_kind = str(
        _pick(raw, ("strategy_kind", "Strategy_kind"), context=context)
    ).strip()
    model_key = str(
        _pick(
            raw,
            ("model_process_key", "Model_process_key", "Process"),
            context=context,
        )
    ).strip()
    expected_model_key = STRATEGY_KIND_TO_MODEL_PROCESS_KEY.get(strategy_kind)
    if expected_model_key is None or model_key != expected_model_key:
        raise CostDatabaseValidationError(
            f"{context}: invalid strategy mapping {strategy_kind!r} -> {model_key!r}"
        )
    cost_layer = _pick(raw, ("cost_layer",), context=context)
    expected_cost_layer = (
        "strategy_incremental"
        if model_key in SYSTEM_STRATEGY_KEYS
        else "process_abatement"
    )
    if cost_layer != expected_cost_layer:
        raise CostDatabaseValidationError(
            f"{context}.cost_layer must equal {expected_cost_layer!r}"
        )

    preferred = _require_finite_number(
        _pick(
            raw,
            (
                "preferred_cost_usd_tco2e",
                "Preferred_cost_USD_per_tCO2e",
                "Preferred_Cost",
                "preferred_cost",
            ),
            context=context,
        ),
        field=f"{context}.preferred_cost",
    )
    final = _require_finite_number(
        _pick(
            raw,
            (
                "final_unit_cost_usd_tco2e",
                "model_cost_usd_tco2e",
                "Model_cost_USD_per_tCO2e",
                "Final_Unit_Cost",
                "final_unit_cost",
            ),
            context=context,
        ),
        field=f"{context}.final_unit_cost",
    )
    if final < 0:
        raise CostDatabaseValidationError(
            f"{context}.final_unit_cost must be non-negative"
        )
    expected_final = max(0.0, preferred)
    if not math.isclose(final, expected_final, rel_tol=0.0, abs_tol=1e-9):
        raise CostDatabaseValidationError(
            f"{context}: final_unit_cost must equal max(0, preferred_cost); "
            f"got {final!r} versus {expected_final!r}"
        )

    row_target_year = _pick(
        raw,
        ("target_year", "Target_year"),
        context=context,
        required=False,
    )
    if row_target_year is not _MISSING:
        if _require_integer(row_target_year, field=f"{context}.target_year") != TARGET_YEAR:
            raise CostDatabaseValidationError(
                f"{context}.target_year must equal {TARGET_YEAR}"
            )
    row_unit = _pick(
        raw,
        ("cost_unit", "unit"),
        context=context,
        required=False,
    )
    if row_unit is not _MISSING and row_unit != COST_UNIT:
        raise CostDatabaseValidationError(
            f"{context}.cost_unit must equal {COST_UNIT!r}"
        )

    normalised = dict(raw)
    normalised.update(
        {
            "M49_Country_Code": m49,
            "strategy_kind": strategy_kind,
            "model_process_key": model_key,
            "cost_layer": expected_cost_layer,
            "preferred_cost_usd_tco2e": preferred,
            "final_unit_cost_usd_tco2e": final,
        }
    )
    return normalised


def load_cost_database_v2(
    path: str | Path,
    expected_m49: Iterable[Any] | None = None,
) -> MitigationCostDatabase:
    """Load and fully validate a v2 solver JSON artifact.

    When ``expected_m49`` is omitted, the production contract of 190 countries
    and 1,710 rows is enforced.  Tests and deliberately smaller model domains
    may pass an explicit country iterable; the loader still requires all nine
    strategies for every supplied country.
    """

    json_path = Path(path)
    if not json_path.is_file():
        raise FileNotFoundError(f"Cost database JSON does not exist: {json_path}")
    try:
        with json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CostDatabaseValidationError(
            f"Cost database is not valid UTF-8 JSON: {json_path}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise CostDatabaseValidationError("Cost database root must be a JSON object")

    metadata = payload.get("metadata")
    records_raw = payload.get("solver_export")
    if not isinstance(metadata, Mapping):
        raise CostDatabaseValidationError("metadata must be a JSON object")
    if not isinstance(records_raw, list):
        raise CostDatabaseValidationError("solver_export must be a JSON array")

    version = _require_nonempty_text(
        _pick(
            metadata,
            ("database_version", "version"),
            context="metadata",
        ),
        field="database_version",
    )
    if not version.startswith(VERSION_PREFIX):
        raise CostDatabaseValidationError(
            f"metadata.database_version must start with {VERSION_PREFIX!r}; got {version!r}"
        )
    schema = _require_nonempty_text(
        _pick(
            metadata,
            ("schema_version", "schema"),
            context="metadata",
        ),
        field="schema_version",
    )
    if schema != SCHEMA_VERSION:
        raise CostDatabaseValidationError(
            f"metadata.schema_version must equal {SCHEMA_VERSION!r}; got {schema!r}"
        )
    unit = _require_nonempty_text(
        _pick(metadata, ("cost_unit", "unit"), context="metadata"),
        field="cost_unit",
    )
    if unit != COST_UNIT:
        raise CostDatabaseValidationError(
            f"metadata.cost_unit must equal {COST_UNIT!r}; got {unit!r}"
        )
    target_year = _require_integer(
        _pick(metadata, ("target_year",), context="metadata"),
        field="metadata.target_year",
    )
    if target_year != TARGET_YEAR:
        raise CostDatabaseValidationError(
            f"metadata.target_year must equal {TARGET_YEAR}; got {target_year}"
        )
    declared_count = _require_integer(
        _pick(
            metadata,
            ("record_count", "solver_export_rows"),
            context="metadata",
        ),
        field="metadata.record_count",
    )
    if declared_count != len(records_raw):
        raise CostDatabaseValidationError(
            "metadata.record_count does not match solver_export length"
        )

    source = _pick(
        metadata,
        ("source", "source_database", "source_path"),
        context="metadata",
    )
    if not isinstance(source, (str, Mapping)) or not source:
        raise CostDatabaseValidationError(
            "metadata.source must be a non-empty string or object"
        )
    source_sha256 = _require_nonempty_text(
        _pick(metadata, ("source_sha256",), context="metadata"),
        field="source_sha256",
    )
    if not _SHA256_RE.fullmatch(source_sha256):
        raise CostDatabaseValidationError(
            "metadata.source_sha256 must contain exactly 64 hexadecimal characters"
        )

    _read_strategy_mapping(metadata)
    _validate_key_partition(metadata)
    strategy_metadata = _strategy_metadata(metadata)

    expected_codes = (
        _normalise_expected_m49(expected_m49)
        if expected_m49 is not None
        else tuple()
    )
    expected_country_count = len(expected_codes) if expected_codes else FULL_COUNTRY_COUNT
    expected_row_count = expected_country_count * len(ALL_STRATEGY_KEYS)
    if len(records_raw) != expected_row_count:
        raise CostDatabaseValidationError(
            f"solver_export must contain {expected_row_count} records "
            f"({expected_country_count} countries x {len(ALL_STRATEGY_KEYS)} strategies); "
            f"got {len(records_raw)}"
        )

    records = []
    unit_costs: Dict[Tuple[str, str], float] = {}
    seen_strategy_keys = set()
    strategies_by_country: Dict[str, set[str]] = {}
    kinds_by_country: Dict[str, set[str]] = {}
    for index, raw in enumerate(records_raw):
        if not isinstance(raw, Mapping):
            raise CostDatabaseValidationError(
                f"solver_export[{index}] must be a JSON object"
            )
        row = _normalise_record(raw, index, expected_version=version)
        m49 = str(row["M49_Country_Code"])
        strategy_kind = str(row["strategy_kind"])
        model_key = str(row["model_process_key"])
        strategy_key = (m49, strategy_kind)
        process_key = (m49, model_key)
        if strategy_key in seen_strategy_keys or process_key in unit_costs:
            raise CostDatabaseValidationError(
                f"duplicate country-strategy record for {m49}/{strategy_kind}/{model_key}"
            )
        seen_strategy_keys.add(strategy_key)
        unit_costs[process_key] = float(row["final_unit_cost_usd_tco2e"])
        strategies_by_country.setdefault(m49, set()).add(model_key)
        kinds_by_country.setdefault(m49, set()).add(strategy_kind)
        records.append(row)

    actual_codes = set(strategies_by_country)
    if expected_codes:
        expected_code_set = set(expected_codes)
        if actual_codes != expected_code_set:
            missing = sorted(expected_code_set - actual_codes)
            extra = sorted(actual_codes - expected_code_set)
            raise CostDatabaseValidationError(
                f"country coverage mismatch; missing={missing}, extra={extra}"
            )
    elif len(actual_codes) != FULL_COUNTRY_COUNT:
        raise CostDatabaseValidationError(
            f"solver_export must contain exactly {FULL_COUNTRY_COUNT} countries; "
            f"got {len(actual_codes)}"
        )

    required_model_keys = set(ALL_STRATEGY_KEYS)
    required_strategy_kinds = set(STRATEGY_KIND_TO_MODEL_PROCESS_KEY)
    for m49 in sorted(actual_codes):
        country_model_keys = strategies_by_country[m49]
        country_strategy_kinds = kinds_by_country[m49]
        if country_model_keys != required_model_keys:
            missing = sorted(required_model_keys - country_model_keys)
            extra = sorted(country_model_keys - required_model_keys)
            raise CostDatabaseValidationError(
                f"{m49} does not contain exactly nine model keys; "
                f"missing={missing}, extra={extra}"
            )
        if country_strategy_kinds != required_strategy_kinds:
            missing = sorted(required_strategy_kinds - country_strategy_kinds)
            extra = sorted(country_strategy_kinds - required_strategy_kinds)
            raise CostDatabaseValidationError(
                f"{m49} does not contain exactly nine strategy kinds; "
                f"missing={missing}, extra={extra}"
            )

    return MitigationCostDatabase(
        version=version,
        schema=schema,
        source=source,
        sha256=file_sha256(json_path),
        records=tuple(records),
        unit_costs=unit_costs,
        strategy_metadata=strategy_metadata,
        unit=unit,
        target_year=target_year,
        metadata=dict(metadata),
    )


__all__ = [
    "ALL_STRATEGY_KEYS",
    "COST_UNIT",
    "CostDatabaseValidationError",
    "FULL_COUNTRY_COUNT",
    "KEY_TO_STRATEGY_KIND",
    "MODEL_PROCESS_KEY_TO_STRATEGY_KIND",
    "MitigationCostDatabase",
    "PROCESS_KEYS",
    "PROCESS_KEY_TO_STRATEGY",
    "PROCESS_STRATEGY_KINDS",
    "SCHEMA_VERSION",
    "STRATEGY_KIND_TO_MODEL_PROCESS_KEY",
    "STRATEGY_KIND_TO_KEY",
    "STRATEGY_TO_PROCESS_KEY",
    "SYSTEM_STRATEGY_KEYS",
    "SYSTEM_STRATEGY_KINDS",
    "TARGET_YEAR",
    "VERSION_PREFIX",
    "file_sha256",
    "load_cost_database_v2",
]

