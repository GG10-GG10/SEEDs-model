# Bioenergy input templates

Copy the CSV files to `input/Bioenergy/` before enabling:

```python
CFG["bioenergy_enabled"] = True
CFG["bioenergy_scenario"] = "current_policy"
```

## Historical feedstock table

`bioenergy_historical_feedstock.csv` supplies the physical crop feedstock
quantity already embedded in historical FBS Domestic Supply Quantity. The
latest record at or before the historical end year is subtracted from residual
demand.

Use `feedstock_demand_t` for the wet/raw commodity mass consistent with the
model's production tonnes. Use `feedstock_demand_tdm` for dry matter. If both
are blank, the module derives mass from `energy_target_tj`, LHV, conversion
efficiency, and dry-matter fraction.

## Scenario table

`bioenergy_scenario_targets.csv` supports multiple scenario names. Rows are
linearly interpolated between supplied years. `World` rows are downscaled using
historical country shares for the same feedstock; unresolved rows are reported
instead of being allocated uniformly.

## Feedstock parameter table

Set `market_link=true` only when the feedstock is an existing commodity in
`dict_v3.xlsx`. Residues, manure, forest biomass, waste, and dedicated energy
crops should remain `market_link=false` until their dedicated resource/land
constraints are implemented.

Energy conversion:

```text
feedstock_demand_tdm
  = energy_target_tj * 1000
    / (lhv_gj_per_tdm * conversion_efficiency)

feedstock_demand_t
  = feedstock_demand_tdm / dry_matter_fraction
```

The templates intentionally contain no assumed production data.

`bioenergy_carrier_feedstock_share.csv` is used by
`S0_51_prepare_bioenergy_feedstock_bridge.py` to turn FAOSTAT carrier energy
into physical crop/feedstock rows. Exact country-year shares are preferred;
the preprocessor then falls back to the latest country share and finally to a
`World` share.

## P1 resource constraints

`bioenergy_resource_constraints.csv` is optional but recommended for all
non-market biomass feedstocks:

- crop residues;
- manure biogas;
- forest/wood biomass;
- municipal/food/organic waste;
- dedicated energy crops.

The model matches this table by `M49_Country_Code`, `year`, and `feedstock`.
Absolute quantities such as `resource_available_tdm`, `competing_use_tdm`,
and `eligible_land_area_ha` are used only for exact country-year matches.
`World` rows are used only as default rates/factors such as
`sustainable_fraction`, `yield_tdm_per_ha`, and GHG factors, so global
resource potential is not accidentally copied into every country.

Resource accounting:

```text
sustainable_supply_tdm
  = resource_available_tdm * sustainable_fraction
    - competing_use_tdm

feasible_feedstock_demand_tdm
  = min(feedstock_demand_tdm, sustainable_supply_tdm)
```

For `market_link=true` crop feedstocks, the resource table is diagnostic only:
crop demand still enters the commodity market and land/emissions effects are
handled through the existing solver. For `market_link=false` feedstocks, the
resource table creates:

- `bioenergy_resource_balance.csv`;
- `bioenergy_emissions_handoff.csv`;
- `bioenergy_land_handoff.csv`.

The handoff tables do not yet alter crop, livestock, LUC, or forest emissions
internally. They are stable interfaces for the next integration stage.
