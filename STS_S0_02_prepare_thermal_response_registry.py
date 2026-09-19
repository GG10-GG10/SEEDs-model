# -*- coding: utf-8 -*-
"""STS CLI for the Phase 2 evidence-to-parameter build."""
from __future__ import annotations

import argparse

from STS_thermal_response_evidence import EvidenceFitConfig, prepare_response_registry_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit an auditable thermal response registry")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--registry-output", required=True)
    parser.add_argument("--validation-output", required=True)
    parser.add_argument("--minimum-studies", type=int, default=3)
    args = parser.parse_args()
    registry, validation = prepare_response_registry_files(
        evidence_path=args.evidence,
        registry_output_path=args.registry_output,
        validation_output_path=args.validation_output,
        config=EvidenceFitConfig(minimum_studies_for_production=args.minimum_studies),
    )
    print(f"response rows={len(registry)} held-out predictions={len(validation)}")


if __name__ == "__main__":
    main()
