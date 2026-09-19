# Thermal-stress input templates

These files define the external interface for the 5 km cold/heat-stress extension.
They are schemas and mapping assets, not raw data downloads.

## Required model inputs

1. `thermal_exposure_5km.csv` or Parquet
   - Calculate nonlinear heat/cold indices at the 5 km grid before aggregation.
   - Join external AGLW livestock weights by grid cell and species.
   - Preserve `grid_id`, `grid_resolution_km=5`, `animal_weight`, climate model,
     scenario and production system.
   - Strict runs also require `livestock_weight_year`,
     `livestock_weight_source`, `source_dataset_version`,
     `animal_weight_relative_uncertainty` and `weight_imputation_flag`.
   - AGLW begins in 1961. The 1960 row must use `livestock_weight_year=1961`
     and `weight_imputation_flag=backcast_1961_to_1960`.
   - Historical years may be annual from 1960 through 2020. Future years must be
     2030, 2040, 2050, 2060, 2070 and 2080.
2. `thermal_response_registry.csv`
   - One source-backed response per species, production role, production system
     and impact.
   - Set `parameter_status=production` only after unit, sign, population and
     source verification.
   - Strict mode requires an explicit row for every supported impact for every
     mapped species/role. A source-backed identity row is valid; an absent row
     is not silently interpreted as no effect.
   - `thermal_response_evidence_template.csv` is the evidence input contract;
     build parameters with `STS_S0_02_prepare_thermal_response_registry.py`.
   - `thermal_strain_registry_template.csv` optionally maps hazard/recovery
     drivers to explicit animal-strain variables.
3. `thermal_activity_factors.csv`
   - Baseline N, P, volatile-solids and housing-energy activity factors.
4. `thermal_pollutant_factors.csv`
   - Supports NH3, NOx, PM2.5, PM10, NMVOC, H2S, N leaching/runoff, P loss and
     optional housing-energy CO2.
5. `thermal_species_commodity_map.csv`
   - Version-controlled bridge from model `Item_Emis` and FAOSTAT production
     names to the six canonical livestock groups.
6. `thermal_data_manifest.csv`
   - Copy `thermal_data_manifest_template.csv` and fill every version, licence,
     checksum, raw/processed path, processing script and QC field before a
     production run.
7. `thermal_tier2_parameters.csv`
   - Use `thermal_tier2_parameters_template.csv` and provide production-ready
     IPCC/GLEAM/nutrition/energy parameters for every mapped species/role.
   - Tier 2 runs stop when N/P retention exceeds intake, management fractions
     do not close, or N/P balance residuals exceed tolerance.

## Fail-closed behavior

The runtime defaults to `thermal_stress_enabled=False`. When enabled with strict
validation, missing files, non-5 km metadata, out-of-scope years, unsupported
species, duplicate response definitions and placeholder parameters stop the run.
No numerical response or pollutant factor is invented by the code.

## Avoiding double counting

- Grid indices are calculated before AGLW weighting.
- Dairy/egg activity uses inverse product yield; meat activity uses cycle length;
  mortality and replacement are then applied once.
- Feed per output combines activity, DMI, maintenance energy and digestibility
  exactly once.
- Future GLE emissions consume the authoritative activity ledger. They are not
  post-hoc scaled. Historical inventory rows are preserved for attribution.
- Direct PM is reported separately from atmospheric secondary PM2.5 formation.
