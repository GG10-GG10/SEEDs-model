# -*- coding: utf-8 -*-
"""Emission-module execution manifest helpers.

The main pipeline records every expected emissions module explicitly so a
completed run cannot silently omit a failed module and still be treated as a
complete scientific result.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

import pandas as pd


EMISSION_MODULE_MANIFEST_FILENAME = "emission_module_manifest.csv"
EMISSION_MODULE_NAMES = ("GFIRE", "LUC", "GSOIL", "GLE", "GFISH", "GCE")
EMISSION_MODULE_SUCCESS_STATUSES = {
    "completed",
    "completed_empty",
    "not_applicable",
}


def count_result_rows(value: Any) -> int:
    """Count DataFrame rows recursively in a module result container."""
    if isinstance(value, pd.DataFrame):
        return int(len(value))
    if isinstance(value, Mapping):
        return sum(count_result_rows(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return sum(count_result_rows(item) for item in value)
    return 0


def new_emission_module_records(
    *,
    required: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """Create the canonical module record mapping for one model run."""
    return {
        name: {
            "module": name,
            "required": bool(required),
            "status": "not_run",
            "rows": 0,
            "error": "",
            "notes": "",
        }
        for name in EMISSION_MODULE_NAMES
    }


def mark_emission_module(
    records: MutableMapping[str, Dict[str, Any]],
    name: str,
    *,
    status: Optional[str] = None,
    result: Any = None,
    required: Optional[bool] = None,
    error: Optional[Any] = None,
    notes: Optional[str] = None,
    allow_empty: bool = True,
) -> Dict[str, Any]:
    """Update one module record and return the normalized record."""
    module_name = str(name or "").strip().upper()
    if not module_name:
        raise ValueError("emission module name must be non-empty")
    record = dict(
        records.get(
            module_name,
            {
                "module": module_name,
                "required": True,
                "status": "not_run",
                "rows": 0,
                "error": "",
                "notes": "",
            },
        )
    )
    row_count = count_result_rows(result)
    if status is None:
        if row_count > 0:
            status_norm = "completed"
        elif allow_empty:
            status_norm = "completed_empty"
        else:
            status_norm = "failed"
            if error is None:
                error = (
                    f"{module_name} was expected to emit rows but returned "
                    "an empty result."
                )
    else:
        status_norm = str(status).strip().lower().replace("-", "_").replace(" ", "_")
    record.update(
        {
            "module": module_name,
            "status": status_norm,
            "rows": int(row_count),
        }
    )
    if required is not None:
        record["required"] = bool(required)
    if error is not None:
        record["error"] = str(error)
    if notes is not None:
        record["notes"] = str(notes)
    records[module_name] = record
    return record


def emission_module_records_complete(
    records: Optional[Mapping[str, Mapping[str, Any]]],
) -> bool:
    """Return whether all required emission modules completed acceptably."""
    if not isinstance(records, Mapping):
        return False
    required_records = [
        record
        for record in records.values()
        if isinstance(record, Mapping) and bool(record.get("required", False))
    ]
    if not required_records:
        return True
    return all(
        str(record.get("status", "")).strip().lower()
        in EMISSION_MODULE_SUCCESS_STATUSES
        for record in required_records
    )


def write_emission_module_manifest(
    outdir: Path,
    records: Mapping[str, Mapping[str, Any]],
    *,
    run_id: str,
    scenario_id: str,
) -> Path:
    """Write the durable per-run module manifest as UTF-8 CSV."""
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    ordered_names = list(EMISSION_MODULE_NAMES) + sorted(
        set(records).difference(EMISSION_MODULE_NAMES)
    )
    for name in ordered_names:
        record = records.get(name)
        if not isinstance(record, Mapping):
            continue
        rows.append(
            {
                "run_id": str(run_id),
                "scenario_id": str(scenario_id),
                "module": str(record.get("module", name)),
                "required": bool(record.get("required", False)),
                "status": str(record.get("status", "not_run")),
                "rows": int(record.get("rows", 0) or 0),
                "error": str(record.get("error", "") or ""),
                "notes": str(record.get("notes", "") or ""),
            }
        )
    path = output_dir / EMISSION_MODULE_MANIFEST_FILENAME
    temporary = output_dir / f".{path.name}.{os.getpid()}.tmp"
    try:
        pd.DataFrame(rows).to_csv(temporary, index=False, encoding="utf-8-sig")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return path
