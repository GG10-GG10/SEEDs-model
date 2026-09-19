# -*- coding: utf-8 -*-
"""STS CLI for the versioned thermal-exposure preprocessing contract."""
from __future__ import annotations

import argparse

from STS_thermal_exposure_pipeline import ExposurePipelineConfig, run_exposure_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare 5 km grid-year livestock thermal exposure from aligned tabular inputs."
    )
    parser.add_argument("--climate", required=True, help="Hourly climate CSV/Parquet")
    parser.add_argument("--livestock-weights", required=True, help="AGLW/system weights CSV/Parquet")
    parser.add_argument("--output", required=True, help="Exposure CSV/Parquet")
    parser.add_argument("--manifest", required=True, help="Output JSON data manifest")
    parser.add_argument("--wet-cold-penalty-c", type=float, default=2.0)
    args = parser.parse_args()
    result = run_exposure_pipeline(
        climate_path=args.climate,
        livestock_weights_path=args.livestock_weights,
        output_path=args.output,
        manifest_path=args.manifest,
        config=ExposurePipelineConfig(wet_cold_penalty_c=args.wet_cold_penalty_c),
    )
    print(f"thermal exposure rows={len(result)} output={args.output} manifest={args.manifest}")


if __name__ == "__main__":
    main()
