# -*- coding: utf-8 -*-
"""Reproducibility provenance and business-key coverage for S4 runs."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Dict, Mapping, Optional
import uuid

import numpy as np
import pandas as pd


RUN_MANIFEST_FILENAME = "run_reproducibility_manifest.json"
BUSINESS_KEY_COVERAGE_FILENAME = "module_business_key_coverage.csv"


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, set):
        return sorted((_canonical(item) for item in value), key=str)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return [_canonical(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "__dict__"):
        return _canonical(vars(value))
    return repr(value)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def hash_object(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _combined_file_hash(records: list[Dict[str, Any]]) -> str:
    stable = [
        {
            "name": record.get("name") or record.get("path"),
            "sha256": record.get("sha256"),
            "missing": record.get("missing", False),
        }
        for record in records
    ]
    return hash_object(stable)


def inventory_code(code_root: str | Path) -> Dict[str, Any]:
    root = Path(code_root).resolve()
    records: list[Dict[str, Any]] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts or not path.is_file():
            continue
        records.append(
            {
                "name": str(path.relative_to(root)),
                "path": str(path),
                "size_bytes": int(path.stat().st_size),
                "sha256": sha256_file(path),
            }
        )
    return {
        "root": str(root),
        "file_count": len(records),
        "combined_sha256": _combined_file_hash(records),
        "files": records,
    }


def inventory_inputs(paths: Any, cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """Hash every declared file input without recursively hashing base folders."""
    candidates: Dict[str, str] = {}
    for key, value in vars(paths).items():
        if value is None or key in {"base", "luh2_data_dir"}:
            continue
        if isinstance(value, (str, os.PathLike)):
            candidates[f"DataPaths.{key}"] = str(value)
    for key, value in cfg.items():
        if value is None or not isinstance(value, (str, os.PathLike)):
            continue
        if key.endswith(("_path", "_xlsx", "_csv", "_file")):
            candidates[f"CFG.{key}"] = str(value)
    records: list[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for name, raw_path in sorted(candidates.items()):
        path = Path(raw_path).expanduser()
        identity = (name, str(path))
        if identity in seen:
            continue
        seen.add(identity)
        record: Dict[str, Any] = {"name": name, "path": str(path.resolve())}
        if path.is_file():
            stat = path.stat()
            record.update(
                {
                    "missing": False,
                    "size_bytes": int(stat.st_size),
                    "mtime_ns": int(stat.st_mtime_ns),
                    "sha256": sha256_file(path),
                }
            )
        else:
            record.update(
                {
                    "missing": True,
                    "kind": "directory" if path.is_dir() else "absent",
                    "sha256": None,
                }
            )
        records.append(record)
    return {
        "declared_file_count": len(records),
        "present_file_count": sum(not row["missing"] for row in records),
        "missing_file_count": sum(bool(row["missing"]) for row in records),
        "combined_sha256": _combined_file_hash(records),
        "files": records,
    }


def capture_run_provenance(
    *,
    code_root: str | Path,
    cfg: Mapping[str, Any],
    paths: Any,
    run_arguments: Mapping[str, Any],
) -> Dict[str, Any]:
    cfg_snapshot = _canonical(dict(cfg))
    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "cfg": cfg_snapshot,
        "cfg_sha256": hash_object(cfg_snapshot),
        "code": inventory_code(code_root),
        "inputs": inventory_inputs(paths, cfg_snapshot),
        "run_arguments": _canonical(run_arguments),
        "runtime": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
    }


def _find_column(frame: pd.DataFrame, names: tuple[str, ...]) -> Optional[str]:
    lookup = {str(column).lower(): str(column) for column in frame.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def build_business_key_coverage(
    sources: Mapping[str, Optional[pd.DataFrame]],
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    aliases = {
        "m49": ("m49", "M49", "M49_Country_Code", "m49_code"),
        "commodity": ("commodity", "Item", "Item_Emis", "Commodity"),
        "year": ("year", "Year"),
        "process": ("process", "Process", "pathway"),
        "ghg": ("ghg", "GHG", "pollutant", "gas"),
    }
    for module, frame in sources.items():
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        normalized = pd.DataFrame(index=frame.index)
        for key, names in aliases.items():
            column = _find_column(frame, names)
            normalized[key] = frame[column] if column else ""
        normalized = normalized.fillna("")
        module_column = _find_column(frame, ("module", "Module", "source_module"))
        if module_column:
            normalized["module"] = frame[module_column].fillna(str(module)).astype(str)
        else:
            normalized["module"] = str(module)
        for column in ("m49", "commodity", "year", "process", "ghg", "module"):
            normalized[column] = normalized[column].astype(str)
        key_columns = ["module", "m49", "commodity", "year", "process", "ghg"]
        grouped = normalized.groupby(key_columns, dropna=False, as_index=False).size()
        grouped = grouped.rename(columns={"size": "row_count"})
        grouped["duplicate_business_key"] = grouped["row_count"].gt(1)
        grouped["missing_m49"] = grouped["m49"].astype(str).str.strip().eq("")
        grouped["missing_year"] = grouped["year"].astype(str).str.strip().eq("")
        rows.append(grouped)
    columns = [
        "module",
        "m49",
        "commodity",
        "year",
        "process",
        "ghg",
        "row_count",
        "duplicate_business_key",
        "missing_m49",
        "missing_year",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.concat(rows, ignore_index=True)[columns].sort_values(
        ["module", "year", "m49", "commodity", "process", "ghg"]
    ).reset_index(drop=True)


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        frame.to_csv(temporary, index=False, encoding="utf-8-sig")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_json(payload: Mapping[str, Any], path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(_canonical(payload), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def inventory_outputs(output_dir: str | Path) -> Dict[str, Any]:
    root = Path(output_dir).resolve()
    excluded = {RUN_MANIFEST_FILENAME, "run_status.json"}
    records: list[Dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or path.name in excluded
            or path.name.startswith(".")
            or (relative.parts and relative.parts[0].lower() == "log")
        ):
            continue
        records.append(
            {
                "name": str(path.relative_to(root)),
                "path": str(path),
                "size_bytes": int(path.stat().st_size),
                "sha256": sha256_file(path),
            }
        )
    return {
        "file_count": len(records),
        "combined_sha256": _combined_file_hash(records),
        "files": records,
    }


def finalize_run_manifest(
    output_dir: str | Path,
    *,
    run_id: str,
    scenario_id: str,
    provenance: Mapping[str, Any],
    coverage_sources: Mapping[str, Optional[pd.DataFrame]],
    solver: Mapping[str, Any],
    emission_modules: Mapping[str, Any],
) -> Dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    coverage = build_business_key_coverage(coverage_sources)
    coverage_path = target / BUSINESS_KEY_COVERAGE_FILENAME
    _atomic_csv(coverage, coverage_path)
    coverage_block = {
        "path": str(coverage_path),
        "sha256": sha256_file(coverage_path),
        "rows": int(len(coverage)),
        "duplicate_key_rows": int(coverage["duplicate_business_key"].sum())
        if not coverage.empty
        else 0,
        "missing_m49_rows": int(coverage["missing_m49"].sum())
        if not coverage.empty
        else 0,
        "missing_year_rows": int(coverage["missing_year"].sum())
        if not coverage.empty
        else 0,
    }
    payload = {
        "schema_version": 1,
        "run_id": str(run_id),
        "scenario_id": str(scenario_id),
        "finalized_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": dict(provenance),
        "business_key_coverage": coverage_block,
        "solver": _canonical(solver),
        "emission_modules": _canonical(emission_modules),
        "outputs": inventory_outputs(target),
    }
    payload["manifest_content_sha256"] = hash_object(payload)
    path = target / RUN_MANIFEST_FILENAME
    _atomic_json(payload, path)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "cfg_sha256": provenance.get("cfg_sha256"),
        "code_sha256": provenance.get("code", {}).get("combined_sha256"),
        "input_sha256": provenance.get("inputs", {}).get("combined_sha256"),
        "output_sha256": payload["outputs"]["combined_sha256"],
        "business_key_coverage": coverage_block,
    }


__all__ = [
    "BUSINESS_KEY_COVERAGE_FILENAME",
    "RUN_MANIFEST_FILENAME",
    "build_business_key_coverage",
    "capture_run_provenance",
    "finalize_run_manifest",
    "hash_object",
    "inventory_code",
    "inventory_inputs",
    "inventory_outputs",
    "sha256_file",
]
