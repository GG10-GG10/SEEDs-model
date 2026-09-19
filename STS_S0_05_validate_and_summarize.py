# -*- coding: utf-8 -*-
"""STS CLI to summarize ensemble draws and optionally score external observations."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from STS_thermal_uncertainty_validation import (
    summarize_ensemble,
    validate_against_observations,
    write_validation_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize thermal ensemble and validation")
    parser.add_argument("--draws", required=True)
    parser.add_argument("--metric", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--observations")
    parser.add_argument("--observed-value", default="observed")
    args = parser.parse_args()
    draws = pd.read_csv(args.draws)
    summary = summarize_ensemble(draws, value_columns=[args.metric])
    Path(args.summary_output).parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    metrics = None
    if args.observations:
        observations = pd.read_csv(args.observations)
        _, metrics = validate_against_observations(
            draws,
            observations,
            key_columns=["m49", "year", "commodity"],
            modeled_value=args.metric,
            observed_value=args.observed_value,
        )
    write_validation_report(
        args.report_output,
        ensemble_summary=summary,
        validation_metrics=metrics,
        provenance={"draws": args.draws, "observations": args.observations or ""},
    )
    print(f"summary rows={len(summary)} validation={metrics is not None}")


if __name__ == "__main__":
    main()
