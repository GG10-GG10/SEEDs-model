# 全模型逐文件功能说明

版本：2026-09-19；范围：`Code/bin/new_TS_clear` 文档编写前的 218 个文件。

## 导航

- [1. 数据结构、主流程、求解和共享支持（18 个）](#group-1)
- [2. 分部门排放与土地碳核算（12 个）](#group-2)
- [3. S0 输入准备、校准及历史结果加工（59 个）](#group-3)
- [4. STS 热应激完整功能链（8 个）](#group-4)
- [5. S5 敏感性、策略和批次后处理（41 个）](#group-5)
- [6. SP 论文图及配套数据准备（36 个）](#group-6)
- [7. SA / SC 分析与一致性检查（7 个）](#group-7)
- [8. 仍被生产工作流引用的验证代码（2 个）](#group-8)
- [9. Slurm 提交脚本（10 个）](#group-9)
- [10. SQL 报告查询（1 个）](#group-10)
- [11. 模板、配置和其他辅助文件（24 个）](#group-11)

## 文件速查

| 文件 | 所属部分 |
|---|---|
| [config_paths.py](#file-config-paths-py) | 1 |
| [cost_database_v2.py](#file-cost-database-v2-py) | 1 |
| [emission_module_manifest.py](#file-emission-module-manifest-py) | 1 |
| [figure5_production_ef_report_source.sql](#file-figure5-production-ef-report-source-sql) | 10 |
| [gce_emissions_complete.py](#file-gce-emissions-complete-py) | 2 |
| [gce_emissions_module_fao_legacy.py](#file-gce-emissions-module-fao-legacy-py) | 2 |
| [gfe_emissions_module_fao_legacy.py](#file-gfe-emissions-module-fao-legacy-py) | 2 |
| [gfire_emission_fixed_module.py](#file-gfire-emission-fixed-module-py) | 2 |
| [gfish_emission_module_complete.py](#file-gfish-emission-module-complete-py) | 2 |
| [gle_emissions_complete.py](#file-gle-emissions-complete-py) | 2 |
| [gle_emissions_module_fao_legacy.py](#file-gle-emissions-module-fao-legacy-py) | 2 |
| [gos_emissions_module_fao_legacy.py](#file-gos-emissions-module-fao-legacy-py) | 2 |
| [gsoil_emission_complete.py](#file-gsoil-emission-complete-py) | 2 |
| [lme_manure_module_fao.py](#file-lme-manure-module-fao-py) | 2 |
| [luc_emission_module.py](#file-luc-emission-module-py) | 2 |
| [luc_historical_module.py](#file-luc-historical-module-py) | 2 |
| [market_balance_diagnostics.py](#file-market-balance-diagnostics-py) | 1 |
| [run_reproducibility_manifest.py](#file-run-reproducibility-manifest-py) | 1 |
| [runtime_data_cache.py](#file-runtime-data-cache-py) | 1 |
| [S0_01_elasticity_processor.py](#file-s0-01-elasticity-processor-py) | 3 |
| [S0_02_elasticity_region_fill.py](#file-s0-02-elasticity-region-fill-py) | 3 |
| [S0_03_feed_system_cal.py](#file-s0-03-feed-system-cal-py) | 3 |
| [S0_04_world_price_perUnit_cal.py](#file-s0-04-world-price-perunit-cal-py) | 3 |
| [S0_05_convert_price_to_usd.py](#file-s0-05-convert-price-to-usd-py) | 3 |
| [S0_06_build_world_price_for_forestry.py](#file-s0-06-build-world-price-for-forestry-py) | 3 |
| [S0_07_fill_fish_prices_with_regionAvg.py](#file-s0-07-fill-fish-prices-with-regionavg-py) | 3 |
| [S0_08_make_LUC_mask_WGS.py](#file-s0-08-make-luc-mask-wgs-py) | 3 |
| [S0_09_make_pasture_yield_mask_WGS.py](#file-s0-09-make-pasture-yield-mask-wgs-py) | 3 |
| [S0_10_recal_ef_livestock_country_item.py](#file-s0-10-recal-ef-livestock-country-item-py) | 3 |
| [S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py](#file-s0-11-fao-production-livestock-dairy-producingheadratio-prepare-py) | 3 |
| [S0_12_compute_pasture_DMyield_by_country.py](#file-s0-12-compute-pasture-dmyield-by-country-py) | 3 |
| [S0_13_extract_crop_grass_feed_ratio.py](#file-s0-13-extract-crop-grass-feed-ratio-py) | 3 |
| [S0_14_SSPDB_GDP_change_refill.py](#file-s0-14-sspdb-gdp-change-refill-py) | 3 |
| [S0_15_manure_treatment_ratio_refill.py](#file-s0-15-manure-treatment-ratio-refill-py) | 3 |
| [S0_15_manure_treatment_ratio_refill_2.py](#file-s0-15-manure-treatment-ratio-refill-2-py) | 3 |
| [S0_16_gce_crop_parameters.py](#file-s0-16-gce-crop-parameters-py) | 3 |
| [S0_17_LUH2_data_analysis.py](#file-s0-17-luh2-data-analysis-py) | 3 |
| [S0_18_soil_drained_EF_refill.py](#file-s0-18-soil-drained-ef-refill-py) | 3 |
| [S0_19_historical_max_production.py](#file-s0-19-historical-max-production-py) | 3 |
| [S0_20_analysis_maskID_missing_country.py](#file-s0-20-analysis-maskid-missing-country-py) | 3 |
| [S0_21_Landuse_historical_refill.py](#file-s0-21-landuse-historical-refill-py) | 3 |
| [S0_22_Forest_EF_recal.py](#file-s0-22-forest-ef-recal-py) | 3 |
| [S0_23_MACC_build.py](#file-s0-23-macc-build-py) | 3 |
| [S0_24_Reduction_cost_2080.py](#file-s0-24-reduction-cost-2080-py) | 3 |
| [S0_24_Reduction_cost_allYear.py](#file-s0-24-reduction-cost-allyear-py) | 3 |
| [S0_24_Reduction_cost_country_process_2080.py](#file-s0-24-reduction-cost-country-process-2080-py) | 3 |
| [S0_25_Dairy_NonDairy_emis_split.py](#file-s0-25-dairy-nondairy-emis-split-py) | 3 |
| [S0_26_feed_info_refill.py](#file-s0-26-feed-info-refill-py) | 3 |
| [S0_27_grassfeed_ratio_refill.py](#file-s0-27-grassfeed-ratio-refill-py) | 3 |
| [S0_28_dairy_yield_refill.py](#file-s0-28-dairy-yield-refill-py) | 3 |
| [S0_29_production_baseYear_fill_placeholder.py](#file-s0-29-production-baseyear-fill-placeholder-py) | 3 |
| [S0_30_Nutrition_base_build.py](#file-s0-30-nutrition-base-build-py) | 3 |
| [S0_31_Nutrition_base_supp.py](#file-s0-31-nutrition-base-supp-py) | 3 |
| [S0_32_Nutrition_base_rescale.py](#file-s0-32-nutrition-base-rescale-py) | 3 |
| [S0_33_build_fish_seafood_country_panel.py](#file-s0-33-build-fish-seafood-country-panel-py) | 3 |
| [S0_34_build_country_minimum_nutrition_requirement.py](#file-s0-34-build-country-minimum-nutrition-requirement-py) | 3 |
| [S0_35_Elasticity_signs_revise.py](#file-s0-35-elasticity-signs-revise-py) | 3 |
| [S0_36_make_armington_from_gtap10.py](#file-s0-36-make-armington-from-gtap10-py) | 3 |
| [S0_37_FBS_Demand_base_refill.py](#file-s0-37-fbs-demand-base-refill-py) | 3 |
| [S0_38_Nutrition_profile_recalculated_fromD0.py](#file-s0-38-nutrition-profile-recalculated-fromd0-py) | 3 |
| [S0_38_Nutrition_profile_recalculated_fromD0_food.py](#file-s0-38-nutrition-profile-recalculated-fromd0-food-py) | 3 |
| [S0_39_calibrate_gce_synthetic_fert_ef_2020.py](#file-s0-39-calibrate-gce-synthetic-fert-ef-2020-py) | 3 |
| [S0_40_LUCE_parameter_gen.py](#file-s0-40-luce-parameter-gen-py) | 3 |
| [S0_41_Scenario_multiplier_bestHisValue_extract.py](#file-s0-41-scenario-multiplier-besthisvalue-extract-py) | 3 |
| [S0_42_Nutrition_scenario_gen.py](#file-s0-42-nutrition-scenario-gen-py) | 3 |
| [S0_43_EAT_LANCET_nutrition_profile_gen.py](#file-s0-43-eat-lancet-nutrition-profile-gen-py) | 3 |
| [S0_44_AR6_harmonize_baseyear.py](#file-s0-44-ar6-harmonize-baseyear-py) | 3 |
| [S0_45_slice_LUH2_subset.py](#file-s0-45-slice-luh2-subset-py) | 3 |
| [S0_46_AR6_SCI_scenario_combine.py](#file-s0-46-ar6-sci-scenario-combine-py) | 3 |
| [S0_47_SCI_harmonization_pooled_fallback_fix.py](#file-s0-47-sci-harmonization-pooled-fallback-fix-py) | 3 |
| [S0_48_history_emission_summary.py](#file-s0-48-history-emission-summary-py) | 3 |
| [S0_49_emission_result_summary.py](#file-s0-49-emission-result-summary-py) | 3 |
| [S0_50_prepare_bioenergy_history.py](#file-s0-50-prepare-bioenergy-history-py) | 3 |
| [S0_51_prepare_bioenergy_feedstock_bridge.py](#file-s0-51-prepare-bioenergy-feedstock-bridge-py) | 3 |
| [S0_52_prepare_bioenergy_resource_constraints.py](#file-s0-52-prepare-bioenergy-resource-constraints-py) | 3 |
| [S0_53_prepare_bioenergy_scenarios.py](#file-s0-53-prepare-bioenergy-scenarios-py) | 3 |
| [S0_54_prepare_bioenergy_eligible_land_mask.py](#file-s0-54-prepare-bioenergy-eligible-land-mask-py) | 3 |
| [S0_55_prepare_bioenergy_noncrop_availability.py](#file-s0-55-prepare-bioenergy-noncrop-availability-py) | 3 |
| [S1_0_schema.py](#file-s1-0-schema-py) | 1 |
| [S2_0_load_data.py](#file-s2-0-load-data-py) | 1 |
| [S3_0_ds_emis_mc_full.py](#file-s3-0-ds-emis-mc-full-py) | 1 |
| [S3_0_ds_linear_regional.py](#file-s3-0-ds-linear-regional-py) | 1 |
| [S3_1_emissions_orchestrator_fao.py](#file-s3-1-emissions-orchestrator-fao-py) | 1 |
| [S3_2_feed_demand.py](#file-s3-2-feed-demand-py) | 1 |
| [S3_3_bioenergy.py](#file-s3-3-bioenergy-py) | 1 |
| [S3_5_land_use_change.py](#file-s3-5-land-use-change-py) | 1 |
| [S3_6_scenarios.py](#file-s3-6-scenarios-py) | 1 |
| [S4_0_main.py](#file-s4-0-main-py) | 1 |
| [S4_1_results.py](#file-s4-1-results-py) | 1 |
| [S4_3_results_summary_only.py](#file-s4-3-results-summary-only-py) | 1 |
| [S5_0_1_diagnose_small_variable_importance.py](#file-s5-0-1-diagnose-small-variable-importance-py) | 5 |
| [S5_0_1_sensitivity_mc_levels.py](#file-s5-0-1-sensitivity-mc-levels-py) | 5 |
| [S5_0_1_sensitivity_mc_levels_batches.py](#file-s5-0-1-sensitivity-mc-levels-batches-py) | 5 |
| [S5_0_2_merge_sensitivity_mc_levels_batches.py](#file-s5-0-2-merge-sensitivity-mc-levels-batches-py) | 5 |
| [S5_1_1_sensitivity_mc_variable_effect.py](#file-s5-1-1-sensitivity-mc-variable-effect-py) | 5 |
| [S5_1_1_sensitivity_mc_variable_effect_batches.py](#file-s5-1-1-sensitivity-mc-variable-effect-batches-py) | 5 |
| [S5_1_2_rebuild_fig_effect_sensivity_data.py](#file-s5-1-2-rebuild-fig-effect-sensivity-data-py) | 5 |
| [S5_1_3_merge_variable_effect_batches.py](#file-s5-1-3-merge-variable-effect-batches-py) | 5 |
| [S5_3_1_forest_area_fixed_sensitivity.py](#file-s5-3-1-forest-area-fixed-sensitivity-py) | 5 |
| [S5_3_1_sensitivity_panel_yield_ef.py](#file-s5-3-1-sensitivity-panel-yield-ef-py) | 5 |
| [S5_3_1_sensitivity_panel_yield_ef_batches.py](#file-s5-3-1-sensitivity-panel-yield-ef-batches-py) | 5 |
| [S5_3_1_sensitivity_panel_yield_ef_batches_v2.py](#file-s5-3-1-sensitivity-panel-yield-ef-batches-v2-py) | 5 |
| [S5_3_1_sensitivity_panel_yield_ef_v2.py](#file-s5-3-1-sensitivity-panel-yield-ef-v2-py) | 5 |
| [S5_3_2_panel_data_summary.py](#file-s5-3-2-panel-data-summary-py) | 5 |
| [S5_3_2_panel_data_summary_v2.py](#file-s5-3-2-panel-data-summary-v2-py) | 5 |
| [S5_3_3_merge_panel_yield_ef_batches.py](#file-s5-3-3-merge-panel-yield-ef-batches-py) | 5 |
| [S5_3_3_merge_panel_yield_ef_batches_v2.py](#file-s5-3-3-merge-panel-yield-ef-batches-v2-py) | 5 |
| [S5_4_1_monte_carlo_full_variables.py](#file-s5-4-1-monte-carlo-full-variables-py) | 5 |
| [S5_4_1_monte_carlo_full_variables_batches.py](#file-s5-4-1-monte-carlo-full-variables-batches-py) | 5 |
| [S5_4_2_merge_batches.py](#file-s5-4-2-merge-batches-py) | 5 |
| [S5_4_3_extreme_robustness_test.py](#file-s5-4-3-extreme-robustness-test-py) | 5 |
| [S5_5_0_Region-Item-Process_Importance_extract_previous.py](#file-s5-5-0-region-item-process-importance-extract-previous-py) | 5 |
| [S5_5_1_Region-Item-Process_Importance_Gen.py](#file-s5-5-1-region-item-process-importance-gen-py) | 5 |
| [S5_5_2_Region-Item-Process_Importance_Gen_batches.py](#file-s5-5-2-region-item-process-importance-gen-batches-py) | 5 |
| [S5_5_3_Region-Item-Process_Importance_merge_batches.py](#file-s5-5-3-region-item-process-importance-merge-batches-py) | 5 |
| [S5_6_1_max_emission_reduction_potential.py](#file-s5-6-1-max-emission-reduction-potential-py) | 5 |
| [S5_6_1_max_emission_reduction_potential_batches.py](#file-s5-6-1-max-emission-reduction-potential-batches-py) | 5 |
| [S5_6_2_merge_batches.py](#file-s5-6-2-merge-batches-py) | 5 |
| [S5_6_4_max_reduction_impend.py](#file-s5-6-4-max-reduction-impend-py) | 5 |
| [S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](#file-s5-7-1-strategy-endpoint-rerun-max-reduction-potential-py) | 5 |
| [S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py](#file-s5-7-1-strategy-endpoint-rerun-max-reduction-potential-batches-py) | 5 |
| [S5_7_2_strategy_endpoint_rerun_merge_batches.py](#file-s5-7-2-strategy-endpoint-rerun-merge-batches-py) | 5 |
| [S5_7_3_strategy_macc_cdr_price.py](#file-s5-7-3-strategy-macc-cdr-price-py) | 5 |
| [S5_8_1_country_strategy_map_sensitivity.py](#file-s5-8-1-country-strategy-map-sensitivity-py) | 5 |
| [S5_8_1_country_strategy_map_sensitivity_batches.py](#file-s5-8-1-country-strategy-map-sensitivity-batches-py) | 5 |
| [S5_8_2_country_strategy_map_merge_batches.py](#file-s5-8-2-country-strategy-map-merge-batches-py) | 5 |
| [S5_8_3_prepare_country_dominant_mitigation_intervention.py](#file-s5-8-3-prepare-country-dominant-mitigation-intervention-py) | 5 |
| [S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](#file-s5-9-1-bioenergy-scenario-marginal-abatement-cost-curves-py) | 5 |
| [S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py](#file-s5-9-1-bioenergy-scenario-marginal-abatement-cost-curves-batches-py) | 5 |
| [S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py](#file-s5-9-2-bioenergy-scenario-marginal-abatement-cost-curves-merge-batches-py) | 5 |
| [S5_cost_summary_outputs.py](#file-s5-cost-summary-outputs-py) | 5 |
| [SA0_1_Population_analysis.py](#file-sa0-1-population-analysis-py) | 7 |
| [SA1_1_GHG_emis_map.py](#file-sa1-1-ghg-emis-map-py) | 7 |
| [SC0_1_Nutrition_check.py](#file-sc0-1-nutrition-check-py) | 7 |
| [SC0_2_Nutrition_production_check.py](#file-sc0-2-nutrition-production-check-py) | 7 |
| [SC0_3_Item_Demand_Category.py](#file-sc0-3-item-demand-category-py) | 7 |
| [SC0_4_Item_Demand_Supply_Trade.py](#file-sc0-4-item-demand-supply-trade-py) | 7 |
| [SC1_1_regression_output_compare.py](#file-sc1-1-regression-output-compare-py) | 7 |
| [SP_M1a_Figure_pie_structure_plot.py](#file-sp-m1a-figure-pie-structure-plot-py) | 6 |
| [SP_M1a_Figure_pie_structure_plot_v2.1.py](#file-sp-m1a-figure-pie-structure-plot-v2-1-py) | 6 |
| [SP_M1a_Figure_pie_structure_plot_v2.py](#file-sp-m1a-figure-pie-structure-plot-v2-py) | 6 |
| [SP_M1a_Figure_pie_structure_pre.py](#file-sp-m1a-figure-pie-structure-pre-py) | 6 |
| [SP_M1a_Figure_pie_structure_pre_v2.py](#file-sp-m1a-figure-pie-structure-pre-v2-py) | 6 |
| [SP_M1aSI_Figure_bar2_structure_plot.py](#file-sp-m1asi-figure-bar2-structure-plot-py) | 6 |
| [SP_M1aSI_Figure_bar_structure_plot.py](#file-sp-m1asi-figure-bar-structure-plot-py) | 6 |
| [SP_M1b_Figure_AR6_scenario_plot.py](#file-sp-m1b-figure-ar6-scenario-plot-py) | 6 |
| [SP_M1b_Figure_AR6_scenario_plot_2.py](#file-sp-m1b-figure-ar6-scenario-plot-2-py) | 6 |
| [SP_M1b_Figure_AR6_scenario_plot_v2.py](#file-sp-m1b-figure-ar6-scenario-plot-v2-py) | 6 |
| [SP_M1b_Figure_AR6_scenario_prep.py](#file-sp-m1b-figure-ar6-scenario-prep-py) | 6 |
| [SP_M1b_Figure_SCI_scenario_plot_v2.py](#file-sp-m1b-figure-sci-scenario-plot-v2-py) | 6 |
| [SP_M1b_Figure_SCI_scenario_prep.py](#file-sp-m1b-figure-sci-scenario-prep-py) | 6 |
| [SP_M2_Figure_contour.py](#file-sp-m2-figure-contour-py) | 6 |
| [SP_M2_Figure_contour_v2.py](#file-sp-m2-figure-contour-v2-py) | 6 |
| [SP_M3a_Figure_macc_stock.py](#file-sp-m3a-figure-macc-stock-py) | 6 |
| [SP_M3a_Figure_macc_stock_v2.py](#file-sp-m3a-figure-macc-stock-v2-py) | 6 |
| [SP_M3a_Figure_macc_stock_v3.1.py](#file-sp-m3a-figure-macc-stock-v3-1-py) | 6 |
| [SP_M3a_Figure_macc_stock_v3.py](#file-sp-m3a-figure-macc-stock-v3-py) | 6 |
| [SP_M3b_Figure_map_reduction_cost_potential.py](#file-sp-m3b-figure-map-reduction-cost-potential-py) | 6 |
| [SP_M3b_Figure_map_reduction_cost_potential_v2.1.py](#file-sp-m3b-figure-map-reduction-cost-potential-v2-1-py) | 6 |
| [SP_M3b_Figure_map_reduction_cost_potential_v2.py](#file-sp-m3b-figure-map-reduction-cost-potential-v2-py) | 6 |
| [SP_M3d_Figure_country_dominant_mitigation_intervention.py](#file-sp-m3d-figure-country-dominant-mitigation-intervention-py) | 6 |
| [SP_M4a_Figure_sensitivity_stock.py](#file-sp-m4a-figure-sensitivity-stock-py) | 6 |
| [SP_M4b_Figure_yield_ef_effect_line.py](#file-sp-m4b-figure-yield-ef-effect-line-py) | 6 |
| [SP_M4b_Figure_yield_ef_effect_line_targetrange.py](#file-sp-m4b-figure-yield-ef-effect-line-targetrange-py) | 6 |
| [SP_M4b_Figure_yield_ef_effect_line_targetrange_v2.py](#file-sp-m4b-figure-yield-ef-effect-line-targetrange-v2-py) | 6 |
| [SP_M4b_Figure_yield_ef_effect_line_targetval.py](#file-sp-m4b-figure-yield-ef-effect-line-targetval-py) | 6 |
| [SP_M4e_Figure_sensitivity_Item-Region-Process_stock.py](#file-sp-m4e-figure-sensitivity-item-region-process-stock-py) | 6 |
| [SP_M4f_Figure_structure_importance_targetrange_v1.py](#file-sp-m4f-figure-structure-importance-targetrange-v1-py) | 6 |
| [SP_M4f_Figure_structure_importance_targetrange_v2.py](#file-sp-m4f-figure-structure-importance-targetrange-v2-py) | 6 |
| [SP_M4f_Figure_structure_importance_targetrange_v3.py](#file-sp-m4f-figure-structure-importance-targetrange-v3-py) | 6 |
| [SP_SI1_Figure_prod_trend_region_fb.py](#file-sp-si1-figure-prod-trend-region-fb-py) | 6 |
| [SP_SI2_Figure_ruminateIntakeRatio_map.py](#file-sp-si2-figure-ruminateintakeratio-map-py) | 6 |
| [SP_SI3_Figure_emis_reduction_disaggregate.py](#file-sp-si3-figure-emis-reduction-disaggregate-py) | 6 |
| [SP_SI4_Figure_emission_per_kcal_item.py](#file-sp-si4-figure-emission-per-kcal-item-py) | 6 |
| [ST_bioenergy_full_run_smoke.py](#file-st-bioenergy-full-run-smoke-py) | 8 |
| [ST_bioenergy_mvp_test.py](#file-st-bioenergy-mvp-test-py) | 8 |
| [STS_S0_01_prepare_thermal_exposure.py](#file-sts-s0-01-prepare-thermal-exposure-py) | 4 |
| [STS_S0_02_prepare_thermal_response_registry.py](#file-sts-s0-02-prepare-thermal-response-registry-py) | 4 |
| [STS_S0_05_validate_and_summarize.py](#file-sts-s0-05-validate-and-summarize-py) | 4 |
| [STS_thermal_exposure_pipeline.py](#file-sts-thermal-exposure-pipeline-py) | 4 |
| [STS_thermal_nutrient_emissions.py](#file-sts-thermal-nutrient-emissions-py) | 4 |
| [STS_thermal_response_evidence.py](#file-sts-thermal-response-evidence-py) | 4 |
| [STS_thermal_stress_model.py](#file-sts-thermal-stress-model-py) | 4 |
| [STS_thermal_uncertainty_validation.py](#file-sts-thermal-uncertainty-validation-py) | 4 |
| [submit_sbatch_S5_0_mclevels.sh](#file-submit-sbatch-s5-0-mclevels-sh) | 9 |
| [submit_sbatch_S5_1_1_variable_effect.sh](#file-submit-sbatch-s5-1-1-variable-effect-sh) | 9 |
| [submit_sbatch_S5_3_1_panel_yield_ef.sh](#file-submit-sbatch-s5-3-1-panel-yield-ef-sh) | 9 |
| [submit_sbatch_S5_3_1_panel_yield_ef_v2.sh](#file-submit-sbatch-s5-3-1-panel-yield-ef-v2-sh) | 9 |
| [submit_sbatch_S5_4_fullmc.sh](#file-submit-sbatch-s5-4-fullmc-sh) | 9 |
| [submit_sbatch_S5_5_RIP_importance.sh](#file-submit-sbatch-s5-5-rip-importance-sh) | 9 |
| [submit_sbatch_S5_6_max_reduction.sh](#file-submit-sbatch-s5-6-max-reduction-sh) | 9 |
| [submit_sbatch_S5_7_strategy_endpoint_rerun.sh](#file-submit-sbatch-s5-7-strategy-endpoint-rerun-sh) | 9 |
| [submit_sbatch_S5_8_country_strategy_map.sh](#file-submit-sbatch-s5-8-country-strategy-map-sh) | 9 |
| [submit_sbatch_S5_9_bioenergy_macc.sh](#file-submit-sbatch-s5-9-bioenergy-macc-sh) | 9 |

<a id="group-1"></a>
## 1. 数据结构、主流程、求解和共享支持

<a id="file-config-paths-py"></a>
### `config_paths.py`

统一寻找 Code 根目录和 input、src、output、LUH2 路径，支持 NZF_* 环境变量；供运行、前处理与绘图共用。没有自动同步代码的功能。

源码：[config_paths.py](../../config_paths.py)；80 行。

主要接口：[`get_code_root`](../../config_paths.py#L15)、[`get_input_base`](../../config_paths.py#L35)、[`get_src_base`](../../config_paths.py#L48)、[`get_results_base`](../../config_paths.py#L61)、[`get_luh2_data_base`](../../config_paths.py#L75)。

本目录调用/引用者：[S0_03_feed_system_cal.py](../../S0_03_feed_system_cal.py)、[S0_08_make_LUC_mask_WGS.py](../../S0_08_make_LUC_mask_WGS.py)、[S0_12_compute_pasture_DMyield_by_country.py](../../S0_12_compute_pasture_DMyield_by_country.py)、[S0_16_gce_crop_parameters.py](../../S0_16_gce_crop_parameters.py)、[S0_17_LUH2_data_analysis.py](../../S0_17_LUH2_data_analysis.py)、[S0_18_soil_drained_EF_refill.py](../../S0_18_soil_drained_EF_refill.py)；另 82 个引用者。

<a id="file-cost-database-v2-py"></a>
### `cost_database_v2.py`

读取并严格校验九措施 v2.0 成本 JSON，检查版本、单位、2080 年、国家覆盖、唯一键、策略层次和最终成本规则；输出带来源元数据的 MitigationCostDatabase 及国家—措施单位成本映射。

源码：[cost_database_v2.py](../../cost_database_v2.py)；733 行。

主要接口：[`CostDatabaseValidationError`](../../cost_database_v2.py#L89)、[`MitigationCostDatabase`](../../cost_database_v2.py#L94)、[`file_sha256`](../../cost_database_v2.py#L140)、[`load_cost_database_v2`](../../cost_database_v2.py#L515)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)、[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)。

<a id="file-emission-module-manifest-py"></a>
### `emission_module_manifest.py`

维护必需/可选排放模块的执行记录、行数、异常与完成情况，输出模块清单，防止某个部门未算成功却发布不完整总量。

源码：[emission_module_manifest.py](../../emission_module_manifest.py)；174 行。

主要接口：[`count_result_rows`](../../emission_module_manifest.py#L27)、[`new_emission_module_records`](../../emission_module_manifest.py#L38)、[`mark_emission_module`](../../emission_module_manifest.py#L56)、[`emission_module_records_complete`](../../emission_module_manifest.py#L116)、[`write_emission_module_manifest`](../../emission_module_manifest.py#L136)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。

文件线索：`emission_module_manifest.csv`。

<a id="file-market-balance-diagnostics-py"></a>
### `market_balance_diagnostics.py`

按求解器实际平衡关系整理国家/商品供需、净进口、显式生物能源用途、短缺和过剩，生成可供 S4/S5 判断有效性的市场诊断。

源码：[market_balance_diagnostics.py](../../market_balance_diagnostics.py)；462 行。

主要接口：[`build_market_balance_diagnostics`](../../market_balance_diagnostics.py#L132)、[`summarize_market_balance_frame`](../../market_balance_diagnostics.py#L246)、[`read_market_balance_summary`](../../market_balance_diagnostics.py#L416)、[`validate_market_balance_gap`](../../market_balance_diagnostics.py#L437)。

本目录调用/引用者：[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S4_0_main.py](../../S4_0_main.py)、[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)、[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)、[ST_bioenergy_full_run_smoke.py](../../ST_bioenergy_full_run_smoke.py)。

文件线索：`commodity_balance_by_commodity.csv`。

<a id="file-run-reproducibility-manifest-py"></a>
### `run_reproducibility_manifest.py`

记录配置、输入与代码来源、哈希和最终运行状态，生成可重复运行清单；与运行状态及产物完整性机制配合，不能只靠目录名识别实验。

源码：[run_reproducibility_manifest.py](../../run_reproducibility_manifest.py)；358 行。

主要接口：[`sha256_file`](../../run_reproducibility_manifest.py#L57)、[`hash_object`](../../run_reproducibility_manifest.py#L68)、[`inventory_code`](../../run_reproducibility_manifest.py#L84)、[`inventory_inputs`](../../run_reproducibility_manifest.py#L106)、[`capture_run_provenance`](../../run_reproducibility_manifest.py#L156)、[`build_business_key_coverage`](../../run_reproducibility_manifest.py#L189)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。

文件线索：`module_business_key_coverage.csv`；`run_reproducibility_manifest.json`；`run_status.json`。

<a id="file-runtime-data-cache-py"></a>
### `runtime_data_cache.py`

对 CSV、Excel 和其他表格提供缓存读取，利用文件签名及读取参数控制复用，并提供清除接口；供 S2、S4、排放模块等减少重复 I/O。

源码：[runtime_data_cache.py](../../runtime_data_cache.py)；296 行。

主要接口：[`get_runtime_cache_dir`](../../runtime_data_cache.py#L69)、[`read_excel_cached`](../../runtime_data_cache.py#L215)、[`read_csv_cached`](../../runtime_data_cache.py#L247)、[`read_pickle_cached`](../../runtime_data_cache.py#L256)、[`read_excel_sidecar_cached`](../../runtime_data_cache.py#L265)、[`read_tabular_cached`](../../runtime_data_cache.py#L281)。

本目录调用/引用者：[S0_50_prepare_bioenergy_history.py](../../S0_50_prepare_bioenergy_history.py)、[S0_51_prepare_bioenergy_feedstock_bridge.py](../../S0_51_prepare_bioenergy_feedstock_bridge.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S3_2_feed_demand.py](../../S3_2_feed_demand.py)、[S3_3_bioenergy.py](../../S3_3_bioenergy.py)；另 4 个引用者。

<a id="file-s1-0-schema-py"></a>
### `S1_0_schema.py`

定义 Node、Universe、ScenarioConfig、ScenarioData；统一国家—商品—年份数据载体、映射和传统时间轴默认值，不执行物理求解。

源码：[S1_0_schema.py](../../S1_0_schema.py)；102 行。

主要接口：[`Node`](../../S1_0_schema.py#L10)、[`Universe`](../../S1_0_schema.py#L39)、[`ScenarioConfig`](../../S1_0_schema.py#L89)、[`ScenarioData`](../../S1_0_schema.py#L99)。

本目录调用/引用者：[S0_38_Nutrition_profile_recalculated_fromD0.py](../../S0_38_Nutrition_profile_recalculated_fromD0.py)、[S0_38_Nutrition_profile_recalculated_fromD0_food.py](../../S0_38_Nutrition_profile_recalculated_fromD0_food.py)、[S0_48_history_emission_summary.py](../../S0_48_history_emission_summary.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S3_2_feed_demand.py](../../S3_2_feed_demand.py)；另 14 个引用者。

<a id="file-s2-0-load-data-py"></a>
### `S2_0_load_data.py`

集中定义 DataPaths，读取并映射字典、生产、FBS、人口收入、价格贸易、营养、土地和成本，构造模型范围、节点和参数字典；是输入层核心。

源码：[S2_0_load_data.py](../../S2_0_load_data.py)；4,646 行。

主要接口：[`DataPaths`](../../S2_0_load_data.py#L72)、[`build_universe_from_dict_v3`](../../S2_0_load_data.py#L1050)、[`EmisItemMappings`](../../S2_0_load_data.py#L3740)、[`build_demand_total_from_fbs_domestic_supply`](../../S2_0_load_data.py#L1505)、[`load_population_wpp`](../../S2_0_load_data.py#L2427)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[config_paths.py](../../config_paths.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

本目录调用/引用者：[S0_38_Nutrition_profile_recalculated_fromD0.py](../../S0_38_Nutrition_profile_recalculated_fromD0.py)、[S0_38_Nutrition_profile_recalculated_fromD0_food.py](../../S0_38_Nutrition_profile_recalculated_fromD0_food.py)、[S0_41_Scenario_multiplier_bestHisValue_extract.py](../../S0_41_Scenario_multiplier_bestHisValue_extract.py)、[S0_48_history_emission_summary.py](../../S0_48_history_emission_summary.py)、[S0_49_emission_result_summary.py](../../S0_49_emission_result_summary.py)、[S0_50_prepare_bioenergy_history.py](../../S0_50_prepare_bioenergy_history.py)；另 18 个引用者。

文件线索：`Armington_elasticity.xlsx`；`CommodityBalances_(non-food)_(2010-)_E_All_Data_NOFLAG.csv`；`Elasticity_v3_processed_filled_by_region.xlsx`；`Emissions_Land_Use_Fires_E_All_Data_NOFLAG.csv`；`Environment_Bioenergy_E_All_Data_NOFLAG.csv`；`Environment_LivestockManure_E_All_Data_NOFLAG.csv`；`Environment_LivestockManure_with_ratio.csv`。

<a id="file-s3-0-ds-emis-mc-full-py"></a>
### `S3_0_ds_emis_mc_full.py`

PWL 替代求解后端，构建对数近似、排放和 MACC 等表达式，并提供模型缓存/MC；不支持当前 unit_cost 路径，不能视为默认线性后端的完全等价替换。

源码：[S3_0_ds_emis_mc_full.py](../../S3_0_ds_emis_mc_full.py)；1,250 行。

主要接口：[`build_model`](../../S3_0_ds_emis_mc_full.py#L174)、[`SolveOpt`](../../S3_0_ds_emis_mc_full.py#L938)、[`ModelCache`](../../S3_0_ds_emis_mc_full.py#L947)、[`build_model_cache`](../../S3_0_ds_emis_mc_full.py#L980)、[`apply_sample_updates`](../../S3_0_ds_emis_mc_full.py#L1026)、[`run_mc`](../../S3_0_ds_emis_mc_full.py#L1157)。

代码内导入：[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。

本目录缺失的引用：`mc_bound_utils.py`、`mc_sample_utils.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`Demand_composition.xlsx`；`Nutrition_profile_rescaled.xlsx`；`__samples.csv`；`__summary.csv`；`dict_v3.xlsx`。

<a id="file-s3-0-ds-linear-regional-py"></a>
### `S3_0_ds_linear_regional.py`

默认线性求解后端：营养/弹性需求、贸易、饲料、耕地草地森林、减排和成本约束，提供单次/滚动/迭代求解、诊断及缓存 MC；nutrition 下未来供给采用需求驱动配置。

源码：[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)；14,822 行。

主要接口：[`build_linear_regional_model`](../../S3_0_ds_linear_regional.py#L5101)、[`solve_linear_regional`](../../S3_0_ds_linear_regional.py#L11690)、[`solve_with_luc_iteration`](../../S3_0_ds_linear_regional.py#L820)、[`LinearModelCache`](../../S3_0_ds_linear_regional.py#L2314)、[`apply_linear_sample_updates`](../../S3_0_ds_linear_regional.py#L13368)、[`run_linear_mc`](../../S3_0_ds_linear_regional.py#L13814)、[`build_nutrition_demand_map`](../../S3_0_ds_linear_regional.py#L1868)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_2_feed_demand.py](../../S3_2_feed_demand.py)、[S3_5_land_use_change.py](../../S3_5_land_use_change.py)、[config_paths.py](../../config_paths.py)、[gle_emissions_complete.py](../../gle_emissions_complete.py)、[luc_emission_module.py](../../luc_emission_module.py)、[market_balance_diagnostics.py](../../market_balance_diagnostics.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

本目录调用/引用者：[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_0_ds_emis_mc_full.py](../../S3_0_ds_emis_mc_full.py)、[S4_0_main.py](../../S4_0_main.py)、[S5_0_1_sensitivity_mc_levels.py](../../S5_0_1_sensitivity_mc_levels.py)、[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[ST_bioenergy_mvp_test.py](../../ST_bioenergy_mvp_test.py)。

本目录缺失的引用：`mc_bound_utils.py`、`mc_sample_utils.py`、`model_run_status.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`Demand_composition.xlsx`；`Nutrition_profile_rescaled.xlsx`；`__samples.csv`；`__summary.csv`；`balance_clear_diagnosis.csv`；`constraint_residuals.csv`；`demand_equation_check.csv`。

<a id="file-s3-1-emissions-orchestrator-fao-py"></a>
### `S3_1_emissions_orchestrator_fao.py`

历史 FAO 编排接口和输出结构适配器；部分输出为零占位，不能独立替代当前完整 GCE/GLE/GSOIL 实际计算。

源码：[S3_1_emissions_orchestrator_fao.py](../../S3_1_emissions_orchestrator_fao.py)；52 行。

主要接口：[`FAOPaths`](../../S3_1_emissions_orchestrator_fao.py#L12)、[`EmissionsFAO`](../../S3_1_emissions_orchestrator_fao.py#L19)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。

<a id="file-s3-2-feed-demand-py"></a>
### `S3_2_feed_demand.py`

存栏→每头干物质→草料/作物饲料→商品吨数和草地面积，输出总量与物种细分表；支持情景转换效率及 STS 活动/采食乘数。

源码：[S3_2_feed_demand.py](../../S3_2_feed_demand.py)；691 行。

主要接口：[`FeedDemandOutputs`](../../S3_2_feed_demand.py#L42)、[`build_feed_demand_from_stock`](../../S3_2_feed_demand.py#L49)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

本目录调用/引用者：[S0_48_history_emission_summary.py](../../S0_48_history_emission_summary.py)、[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S4_0_main.py](../../S4_0_main.py)。

<a id="file-s3-3-bioenergy-py"></a>
### `S3_3_bioenergy.py`

构建 BioenergyBundle：能源—原料转换、历史扣除、作物市场需求、资源可行量、专用作物土地、副产品饲料、残余物管理与排放接口，输出求解前后诊断。

源码：[S3_3_bioenergy.py](../../S3_3_bioenergy.py)；2,497 行。

主要接口：[`BioenergyBundle`](../../S3_3_bioenergy.py#L240)、[`build_bioenergy_bundle`](../../S3_3_bioenergy.py#L2167)、[`build_baseline_reconciliation`](../../S3_3_bioenergy.py#L2292)、[`build_bioenergy_postsolve_assessment`](../../S3_3_bioenergy.py#L1546)、[`write_bioenergy_bundle`](../../S3_3_bioenergy.py#L2417)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

本目录调用/引用者：[S0_50_prepare_bioenergy_history.py](../../S0_50_prepare_bioenergy_history.py)、[S0_51_prepare_bioenergy_feedstock_bridge.py](../../S0_51_prepare_bioenergy_feedstock_bridge.py)、[S4_0_main.py](../../S4_0_main.py)、[ST_bioenergy_full_run_smoke.py](../../ST_bioenergy_full_run_smoke.py)、[ST_bioenergy_mvp_test.py](../../ST_bioenergy_mvp_test.py)。

本目录缺失的引用：`model_run_status.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`bioenergy_coproduct_feed_handoff.csv`；`bioenergy_crop_demand.csv`；`bioenergy_diagnostics.csv`；`bioenergy_emissions_handoff.csv`；`bioenergy_energy_balance.csv`；`bioenergy_energy_physical_consistency_diagnostics.csv`；`bioenergy_feedstock_use.csv`。

<a id="file-s3-5-land-use-change-py"></a>
### `S3_5_land_use_change.py`

根据生产/需求、单产、草地需求及基期面积计算逐期土地面积和变化，定义 LUCConfig；属于土地需求/兼容路径，年度碳簿记由 luc_emission_module 执行。

源码：[S3_5_land_use_change.py](../../S3_5_land_use_change.py)；400 行。

主要接口：[`LUCConfig`](../../S3_5_land_use_change.py#L16)、[`compute_luc_areas`](../../S3_5_land_use_change.py#L32)、[`get_luc_emis`](../../S3_5_land_use_change.py#L396)。

本目录调用/引用者：[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S4_0_main.py](../../S4_0_main.py)。

<a id="file-s3-6-scenarios-py"></a>
### `S3_6_scenarios.py`

读取情景和 MC 规格，解析国家/区域、商品、过程/气体选择器和 rate/multiplier/absolute/Y2020 边界，形成并应用 ScenarioEffect；需要 mc_bound_utils。

源码：[S3_6_scenarios.py](../../S3_6_scenarios.py)；1,135 行。

主要接口：[`ScenarioEffect`](../../S3_6_scenarios.py#L127)、[`load_scenario_config`](../../S3_6_scenarios.py#L250)、[`apply_scenario_to_data`](../../S3_6_scenarios.py#L290)、[`load_scenarios`](../../S3_6_scenarios.py#L854)、[`load_mc_specs`](../../S3_6_scenarios.py#L889)、[`draw_mc_to_params`](../../S3_6_scenarios.py#L904)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)、[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)、[S5_3_1_sensitivity_panel_yield_ef_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_v2.py)、[ST_bioenergy_mvp_test.py](../../ST_bioenergy_mvp_test.py)。

本目录缺失的引用：`mc_bound_utils.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`Scenario_variable_historical_range.xlsx`。

<a id="file-s4-0-main-py"></a>
### `S4_0_main.py`

全模型调度器：运行模式、基期构造、情景、饲料/土地/生物能源/热应激连接、求解、活动量重建、各部门排放、成本、诊断和运行记录；S5 主要复用 run_one_pipeline。

源码：[S4_0_main.py](../../S4_0_main.py)；23,465 行。

主要接口：[`main`](../../S4_0_main.py#L23136)、[`run_one_pipeline`](../../S4_0_main.py#L22923)、[`_run_one_pipeline_impl`](../../S4_0_main.py#L10464)、[`_run_thermal_mc`](../../S4_0_main.py#L23037)、[`build_run_baseline_cache`](../../S4_0_main.py#L10289)、[`build_production_summary`](../../S4_0_main.py#L7634)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_0_ds_emis_mc_full.py](../../S3_0_ds_emis_mc_full.py)、[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S3_1_emissions_orchestrator_fao.py](../../S3_1_emissions_orchestrator_fao.py)、[S3_2_feed_demand.py](../../S3_2_feed_demand.py)、[S3_3_bioenergy.py](../../S3_3_bioenergy.py)、[S3_5_land_use_change.py](../../S3_5_land_use_change.py)、[S3_6_scenarios.py](../../S3_6_scenarios.py)、[S4_1_results.py](../../S4_1_results.py)；另 15 个见静态索引。

动态文件引用线索：[lme_manure_module_fao.py](../../lme_manure_module_fao.py)。

本目录调用/引用者：[S5_0_1_sensitivity_mc_levels.py](../../S5_0_1_sensitivity_mc_levels.py)、[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)、[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)、[S5_6_1_max_emission_reduction_potential.py](../../S5_6_1_max_emission_reduction_potential.py)、[S5_6_4_max_reduction_impend.py](../../S5_6_4_max_reduction_impend.py)；另 1 个引用者。

本目录缺失的引用：`model_run_status.py`、`unit_cost_calculation.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`Country-Item-noTradeConstraint-list.xlsx`；`Demand_composition.xlsx`；`Emission_LULUCF_Historical_updated.xlsx`；`Emissions_Drained_Organic_Soils_E_All_Data_NOFLAG.csv`；`Emissions_crops_E_All_Data_NOFLAG.csv`；`Emissions_livestock_dairy_split.csv`；`Environment_LivestockManure_with_ratio.csv`。

<a id="file-s4-1-results-py"></a>
### `S4_1_results.py`

统一市场和排放明细、单位/GWP 与字典映射，输出国家—商品—过程—气体及聚合结果；生成物理/计价减排成本和国家/全球措施成本汇总。

源码：[S4_1_results.py](../../S4_1_results.py)；3,301 行。

主要接口：[`summarize_emissions`](../../S4_1_results.py#L1682)、[`summarize_market`](../../S4_1_results.py#L2209)、[`generate_cost_summary`](../../S4_1_results.py#L2860)、[`build_measure_cost_summaries`](../../S4_1_results.py#L2706)、[`write_summary_tables_from_detail_long`](../../S4_1_results.py#L1648)。

代码内导入：[config_paths.py](../../config_paths.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

本目录调用/引用者：[S0_48_history_emission_summary.py](../../S0_48_history_emission_summary.py)、[S4_0_main.py](../../S4_0_main.py)、[S4_3_results_summary_only.py](../../S4_3_results_summary_only.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[ST_bioenergy_mvp_test.py](../../ST_bioenergy_mvp_test.py)。

文件线索：`cost_summary_by_country_measure.csv`；`cost_summary_by_global_measure.csv`；`debug_sample.log`；`dict_v3.xlsx`；`duplicate_emission_rows_raw.csv`；`s4_1_debug.log`；`s4_1_debug_sample.log`。

<a id="file-s4-3-results-summary-only-py"></a>
### `S4_3_results_summary_only.py`

从已保存的排放长表重新生成汇总和快速排放结果，不重新求解供需；适用于只调整汇总口径或补齐导出的情况。

源码：[S4_3_results_summary_only.py](../../S4_3_results_summary_only.py)；176 行。

主要接口：[`main`](../../S4_3_results_summary_only.py#L77)。

代码内导入：[S4_1_results.py](../../S4_1_results.py)、[config_paths.py](../../config_paths.py)。

文件线索：`dict_v3.xlsx`；`emissions_fast_summary.csv`；`emissions_summary_Detail_Long.csv`。


<a id="group-2"></a>
## 2. 分部门排放与土地碳核算

<a id="file-gce-emissions-complete-py"></a>
### `gce_emissions_complete.py`

当前完整作物排放引擎：从产量、收获面积、残余物和肥料参数计算作物残余物、焚烧、稻作和合成氮肥过程，返回可供 S4.1 汇总的分气体结果。

源码：[gce_emissions_complete.py](../../gce_emissions_complete.py)；1,344 行。

主要接口：[`CropEmissionsCalculator`](../../gce_emissions_complete.py#L213)、[`run_crop_emissions`](../../gce_emissions_complete.py#L1302)。

代码内导入：[config_paths.py](../../config_paths.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。

<a id="file-gce-emissions-module-fao-legacy-py"></a>
### `gce_emissions_module_fao_legacy.py`

历史作物过程函数库，包含残余物直接/间接 N2O、焚烧、稻作 CH4 和化肥直接/间接排放；保留独立接口，不应与当前完整作物模块重复汇总。

源码：[gce_emissions_module_fao_legacy.py](../../gce_emissions_module_fao_legacy.py)；551 行。

主要接口：[`load_params_wide`](../../gce_emissions_module_fao_legacy.py#L78)、[`get_param_wide`](../../gce_emissions_module_fao_legacy.py#L96)、[`compute_crop_residues_direct`](../../gce_emissions_module_fao_legacy.py#L241)、[`compute_crop_residues_indirect`](../../gce_emissions_module_fao_legacy.py#L285)、[`compute_burning`](../../gce_emissions_module_fao_legacy.py#L325)、[`compute_synth_fert_direct`](../../gce_emissions_module_fao_legacy.py#L371)。

<a id="file-gfe-emissions-module-fao-legacy-py"></a>
### `gfe_emissions_module_fao_legacy.py`

历史森林剩余森林（FL–FL）碳排放/汇核算，使用森林碳存量变化等参数；其 GFE 指森林模块，不是当前 GFISH 水产模块，且不包含全部土地转换流程。

源码：[gfe_emissions_module_fao_legacy.py](../../gfe_emissions_module_fao_legacy.py)；253 行。

主要接口：[`get_param`](../../gfe_emissions_module_fao_legacy.py#L77)、[`compute_forest_fl_fl_biomass`](../../gfe_emissions_module_fao_legacy.py#L132)、[`compute_forest_fl_fl_soil_tier1_zero`](../../gfe_emissions_module_fao_legacy.py#L182)、[`run_gfe_forest_only`](../../gfe_emissions_module_fao_legacy.py#L208)、[`run_gfe`](../../gfe_emissions_module_fao_legacy.py#L234)。

<a id="file-gfire-emission-fixed-module-py"></a>
### `gfire_emission_fixed_module.py`

读取并规范化 Savanna fire、Peatlands fire 历史气体排放，形成固定参考火灾排放；不模拟未来火灾气象和燃烧发生过程。

源码：[gfire_emission_fixed_module.py](../../gfire_emission_fixed_module.py)；180 行。

主要接口：[`load_fixed_gfire_emissions`](../../gfire_emission_fixed_module.py#L92)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。

<a id="file-gfish-emission-module-complete-py"></a>
### `gfish_emission_module_complete.py`

水产排放模块：历史从国家—年份面板读取，未来按养殖份额、养殖产量/面积及 CH4/N2O 因子计算；与陆生畜牧 GLE 分开。

源码：[gfish_emission_module_complete.py](../../gfish_emission_module_complete.py)；584 行。

主要接口：[`run_fish_emissions`](../../gfish_emission_module_complete.py#L342)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。

<a id="file-gle-emissions-complete-py"></a>
### `gle_emissions_complete.py`

当前畜牧排放引擎：将求解产量换算存栏和生产头数，计算肠道发酵、粪便管理、粪便施土和放牧排放；可接收 STS 权威活动台账并调用 Tier 2 核算。

源码：[gle_emissions_complete.py](../../gle_emissions_complete.py)；3,656 行。

主要接口：[`LivestockEmissionsCalculator`](../../gle_emissions_complete.py#L73)、[`calculate_stock_from_optimized_production`](../../gle_emissions_complete.py#L3368)、[`run_livestock_emissions`](../../gle_emissions_complete.py#L3567)。

代码内导入：[STS_thermal_nutrient_emissions.py](../../STS_thermal_nutrient_emissions.py)、[config_paths.py](../../config_paths.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

本目录调用/引用者：[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S4_0_main.py](../../S4_0_main.py)。

<a id="file-gle-emissions-module-fao-legacy-py"></a>
### `gle_emissions_module_fao_legacy.py`

文件明确标注弃用的历史畜牧实现，保留屠宰—存栏回归、抽样和过程排放接口供对照；当前主流程使用 gle_emissions_complete.py。

源码：[gle_emissions_module_fao_legacy.py](../../gle_emissions_module_fao_legacy.py)；880 行。

主要接口：[`load_params_wide`](../../gle_emissions_module_fao_legacy.py#L117)、[`get_param_wide`](../../gle_emissions_module_fao_legacy.py#L173)、[`prepare_regression_data_from_fao`](../../gle_emissions_module_fao_legacy.py#L243)、[`fit_stock_from_slaughter`](../../gle_emissions_module_fao_legacy.py#L296)、[`mc_animals_from_production`](../../gle_emissions_module_fao_legacy.py#L404)、[`mc_predict_stock`](../../gle_emissions_module_fao_legacy.py#L491)。

<a id="file-gos-emissions-module-fao-legacy-py"></a>
### `gos_emissions_module_fao_legacy.py`

历史排水有机土壤过程函数库，读取宽表参数并计算 CO2/N2O，支持气候分类和缺失回退；与当前 gsoil_emission_complete.py 区分。

源码：[gos_emissions_module_fao_legacy.py](../../gos_emissions_module_fao_legacy.py)；332 行。

主要接口：[`load_params_wide`](../../gos_emissions_module_fao_legacy.py#L50)、[`get_param_wide`](../../gos_emissions_module_fao_legacy.py#L114)、[`compute_gv_n2o`](../../gos_emissions_module_fao_legacy.py#L215)、[`compute_gv_co2`](../../gos_emissions_module_fao_legacy.py#L263)、[`run_gv`](../../gos_emissions_module_fao_legacy.py#L312)。

<a id="file-gsoil-emission-complete-py"></a>
### `gsoil_emission_complete.py`

当前排水有机土壤排放模块：历史读 FAO 清单，未来用耕地/草地活动面积及对应参数计算 CO2/N2O，输出部门结果。

源码：[gsoil_emission_complete.py](../../gsoil_emission_complete.py)；619 行。

主要接口：[`normalize_m49`](../../gsoil_emission_complete.py#L20)、[`DrainedOrganicSoilsEmissions`](../../gsoil_emission_complete.py#L173)、[`run_drained_organic_soils_emissions`](../../gsoil_emission_complete.py#L594)。

本目录调用/引用者：[S0_48_history_emission_summary.py](../../S0_48_history_emission_summary.py)、[S4_0_main.py](../../S4_0_main.py)。

<a id="file-lme-manure-module-fao-py"></a>
### `lme_manure_module_fao.py`

独立的牲畜粪便氮流与处理系统计算工具，读取统一宽表中的排泄、系统份额、损失、挥发及淋洗系数；当前 S4 主链的粪便排放主要由 GLE/STS 对接。

源码：[lme_manure_module_fao.py](../../lme_manure_module_fao.py)；405 行。

主要接口：[`load_parameters_wide`](../../lme_manure_module_fao.py#L96)、[`get_param`](../../lme_manure_module_fao.py#L172)、[`get_share`](../../lme_manure_module_fao.py#L246)、[`get_loss_frac`](../../lme_manure_module_fao.py#L251)、[`get_frac_scalar`](../../lme_manure_module_fao.py#L256)、[`compute_record`](../../lme_manure_module_fao.py#L265)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。

<a id="file-luc-emission-module-py"></a>
### `luc_emission_module.py`

土地碳簿记引擎：读取土地转换、木材采伐和轮耕活动，追踪生物量、土壤及木制品等碳库；支持 LUH2 网格驱动和求解器汇总土地状态产生的未来输入。

源码：[luc_emission_module.py](../../luc_emission_module.py)；2,264 行。

主要接口：[`load_params_from_excel`](../../luc_emission_module.py#L101)、[`estimate_area_ha`](../../luc_emission_module.py#L492)、[`discover_transitions`](../../luc_emission_module.py#L574)、[`allocate_coarse_transitions_for_year`](../../luc_emission_module.py#L613)、[`allocate_roundwood_for_year`](../../luc_emission_module.py#L667)、[`aggregate_country_year`](../../luc_emission_module.py#L709)。

代码内导入：[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S4_0_main.py](../../S4_0_main.py)。

文件线索：`LUCE_parameter.xlsx`；`dict_v3.xlsx`；`model.log`；`将诊断信息写入model.log`。

<a id="file-luc-historical-module-py"></a>
### `luc_historical_module.py`

读取历史 LULUCF 工作簿中的森林、木材采伐、耕地/草地毁林和恢复等过程，统一格式后与未来 LUC 结果对接。

源码：[luc_historical_module.py](../../luc_historical_module.py)；177 行。

主要接口：[`read_luc_historical_emissions`](../../luc_historical_module.py#L18)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)。


<a id="group-3"></a>
## 3. S0 输入准备、校准及历史结果加工

<a id="file-s0-01-elasticity-processor-py"></a>
### `S0_01_elasticity_processor.py`

将原始弹性观测经商品多对多和区域映射整理为国家—商品弹性宽表；区分供给/需求、自身/交叉价格及温度/收入等，交叉商品列按白名单建立。

源码：[S0_01_elasticity_processor.py](../../S0_01_elasticity_processor.py)；439 行。

主要接口：[`lc`](../../S0_01_elasticity_processor.py#L65)、[`find_col`](../../S0_01_elasticity_processor.py#L69)、[`build_maps_many_to_many`](../../S0_01_elasticity_processor.py#L81)、[`classify_element_ds`](../../S0_01_elasticity_processor.py#L106)、[`agg_stats`](../../S0_01_elasticity_processor.py#L240)、[`fetch_non_cross`](../../S0_01_elasticity_processor.py#L257)。

文件线索：`../../src/bakup/Elasticity_v3.xlsx`；`../../src/bakup/Elasticity_v3_processed_out3.1.xlsx`。

<a id="file-s0-02-elasticity-region-fill-py"></a>
### `S0_02_elasticity_region_fill.py`

填补 S0.01 弹性结果：先区域×商品均值，再按适用规则用商品大类回退；交叉弹性按区域处理，并保留工作簿其他 sheet。

源码：[S0_02_elasticity_region_fill.py](../../S0_02_elasticity_region_fill.py)；238 行。

主要接口：[`find_col`](../../S0_02_elasticity_region_fill.py#L54)、[`load_mappings`](../../S0_02_elasticity_region_fill.py#L71)、[`fill_non_cross_with_region_and_cat`](../../S0_02_elasticity_region_fill.py#L102)、[`fill_cross_mean_with_region`](../../S0_02_elasticity_region_fill.py#L160)。

文件线索：`../../src/bakup/Elasticity_v3_processed_filled_by_region_.xlsx`；`../../src/bakup/Elasticity_v3_processed_out3.1.xlsx`；`../../src/dict_v3.xlsx`。

<a id="file-s0-03-feed-system-cal-py"></a>
### `S0_03_feed_system_cal.py`

结合 FAOSTAT 生产/存栏、FBS 和 GLEAM 参数构建国家—畜种—生产系统饲料矩阵、每头需求和草料比例，是运行时饲料参数的上游准备工具。

源码：[S0_03_feed_system_cal.py](../../S0_03_feed_system_cal.py)；706 行。

主要接口：[`to_head_df`](../../S0_03_feed_system_cal.py#L72)、[`auto_region`](../../S0_03_feed_system_cal.py#L81)、[`default_system_shares`](../../S0_03_feed_system_cal.py#L97)、[`seed_rations`](../../S0_03_feed_system_cal.py#L139)、[`aggregate_rations`](../../S0_03_feed_system_cal.py#L234)、[`load_inputs`](../../S0_03_feed_system_cal.py#L254)、[`main`](../../S0_03_feed_system_cal.py#L475)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`FoodBalanceSheets_E_All_Data_NOFLAG.csv`；`GLEAM_3.0_Supplement_S1.xlsx`；`Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv`；`dict_v3.xlsx`；`unit_feed_crops_per_head_region_system_2010_2020_v3.xlsx`。

<a id="file-s0-04-world-price-perunit-cal-py"></a>
### `S0_04_world_price_perUnit_cal.py`

将全球生产总价值按货币和千/百万等单位换算后除以产量，形成世界单位产值表；当前输入含历史 test 命名路径、输出为 World_Production_Value_per_Unit2.csv，运行前核对路径。

源码：[S0_04_world_price_perUnit_cal.py](../../S0_04_world_price_perUnit_cal.py)；139 行。

主要接口：[`keep_and_numeric`](../../S0_04_world_price_perUnit_cal.py#L45)、[`parse_value_unit`](../../S0_04_world_price_perUnit_cal.py#L72)、[`build_output_unit`](../../S0_04_world_price_perUnit_cal.py#L100)。

文件线索：`../../input/Price_Cost/Price/Value_of_Production_E_All_Data_NOFLAG_test.csv`；`../../input/Price_Cost/Price/World_Production_Value_per_Unit2.csv`；`../../input/Production_Trade/Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv`。

<a id="file-s0-05-convert-price-to-usd-py"></a>
### `S0_05_convert_price_to_usd.py`

根据汇率方向和价格单位将本币生产者价格换为美元，并结合世界价格形成补齐表；保留 /mnt/data 固定路径，需要按实际平台设置后使用。

源码：[S0_05_convert_price_to_usd.py](../../S0_05_convert_price_to_usd.py)；243 行。

主要接口：[`fx_direction`](../../S0_05_convert_price_to_usd.py#L15)、[`to_usd`](../../S0_05_convert_price_to_usd.py#L22)、[`is_usd_per_tonne`](../../S0_05_convert_price_to_usd.py#L26)、[`is_lcu_per_tonne`](../../S0_05_convert_price_to_usd.py#L30)、[`is_slc_per_tonne`](../../S0_05_convert_price_to_usd.py#L34)、[`to_long`](../../S0_05_convert_price_to_usd.py#L107)。

文件线索：`/mnt/data/Exchange_rate_E_All_Data_NOFLAG.csv`；`/mnt/data/Prices_E_All_Data_NOFLAG.csv`；`/mnt/data/Prices_with_USDtrans_USDfinal_SUPERSET_Y2002_2022.csv`；`/mnt/data/World_Production_Value_per_Unit.xlsx`；`/mnt/data/dict_v3.xlsx`。

<a id="file-s0-06-build-world-price-for-forestry-py"></a>
### `S0_06_build_world_price_for_forestry.py`

从 FAOSTAT 林产品贸易数量和价值计算工业圆木/薪材的出口、进口及平均世界单位价值（USD/m³），提供命令行输入输出接口。

源码：[S0_06_build_world_price_for_forestry.py](../../S0_06_build_world_price_for_forestry.py)；108 行。

主要接口：[`load_wide_and_melt`](../../S0_06_build_world_price_for_forestry.py#L38)、[`build_world_uv`](../../S0_06_build_world_price_for_forestry.py#L63)、[`main`](../../S0_06_build_world_price_for_forestry.py#L89)。

<a id="file-s0-07-fill-fish-prices-with-regionavg-py"></a>
### `S0_07_fill_fish_prices_with_regionAvg.py`

对水产价格按 Region_agg5、Region_agg2 逐年均值补缺，向前滑动均值回填早年，再追加世界参考行并导出表格。

源码：[S0_07_fill_fish_prices_with_regionAvg.py](../../S0_07_fill_fish_prices_with_regionAvg.py)；157 行。

主要接口：[`ensure_year_cols`](../../S0_07_fill_fish_prices_with_regionAvg.py#L28)、[`region_mean_fill`](../../S0_07_fill_fish_prices_with_regionAvg.py#L36)、[`backward_moving_average`](../../S0_07_fill_fish_prices_with_regionAvg.py#L47)、[`add_world_row`](../../S0_07_fill_fish_prices_with_regionAvg.py#L60)、[`main`](../../S0_07_fill_fish_prices_with_regionAvg.py#L83)。

<a id="file-s0-08-make-luc-mask-wgs-py"></a>
### `S0_08_make_LUC_mask_WGS.py`

将含国家 ID 的矢量边界栅格化到 LUH2 的经纬度网格，生成国家掩膜 NetCDF，供土地面积和排放按国家聚合。

源码：[S0_08_make_LUC_mask_WGS.py](../../S0_08_make_LUC_mask_WGS.py)；220 行。

主要接口：[`get_lat_lon`](../../S0_08_make_LUC_mask_WGS.py#L60)、[`geotransform_from_centers`](../../S0_08_make_LUC_mask_WGS.py#L71)、[`main`](../../S0_08_make_LUC_mask_WGS.py#L91)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`LUH2_GCB2019_states.nc4`；`mask_LUH2_025d.nc`。

<a id="file-s0-09-make-pasture-yield-mask-wgs-py"></a>
### `S0_09_make_pasture_yield_mask_WGS.py`

将国家边界栅格化到参考牧草 GeoTIFF 的坐标系、分辨率和范围，生成草地产量聚合用掩膜；实际输出格式按代码处理，不仅按文件扩展名判断。

源码：[S0_09_make_pasture_yield_mask_WGS.py](../../S0_09_make_pasture_yield_mask_WGS.py)；213 行。

主要接口：[`main`](../../S0_09_make_pasture_yield_mask_WGS.py#L124)。

文件线索：`..\\..\\input\\Land\\Feed_pasture\\pastures_coi_Area_ha.tif`；`..\\..\\src\\mask_pastureYield_0083d.nc`。

<a id="file-s0-10-recal-ef-livestock-country-item-py"></a>
### `S0_10_recal_ef_livestock_country_item.py`

以历史牲畜排放/存栏反算国家—畜种过程因子，按行内时间插补、区域均值、世界均值顺序修复缺失，规范气体及单位。

源码：[S0_10_recal_ef_livestock_country_item.py](../../S0_10_recal_ef_livestock_country_item.py)；316 行。

主要接口：[`pick_cols`](../../S0_10_recal_ef_livestock_country_item.py#L39)、[`detect_year_cols`](../../S0_10_recal_ef_livestock_country_item.py#L43)、[`mass_to_kg_factor`](../../S0_10_recal_ef_livestock_country_item.py#L47)、[`n_to_kgN_factor`](../../S0_10_recal_ef_livestock_country_item.py#L62)、[`stock_to_animal_factor`](../../S0_10_recal_ef_livestock_country_item.py#L65)、[`convert_by_unit_groups`](../../S0_10_recal_ef_livestock_country_item.py#L76)、[`main`](../../S0_10_recal_ef_livestock_country_item.py#L211)。

文件线索：`../../input/Emission/Emissions_livestock_E_All_Data_NOFLAG.csv`；`../../input/Manure_Stock/Environment_LivestockManure_E_All_Data_NOFLAG.csv`；`../../src/dict_v3.xlsx`；`../../src/retired_and_raw/EF_recalculated_filled_2000_2022_livestock.csv`。

<a id="file-s0-11-fao-production-livestock-dairy-producingheadratio-prepare-py"></a>
### `S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py`

预处理 FAOSTAT 畜牧生产：拆分奶用/非奶用动物、补齐国家—畜种记录，构建生产头数及比例和相应产量/存栏基础表。

源码：[S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py](../../S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py)；455 行。

主要接口：[`detect_year_cols`](../../S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py#L45)、[`normalize_m49`](../../S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py#L51)、[`typical_unit`](../../S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py#L61)、[`make_rows_from_wide`](../../S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py#L68)、[`build_area_year_matrix`](../../S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py#L101)、[`main`](../../S0_11_FAO_production_livestock_dairy_producingHeadRatio_prepare.py#L131)。

文件线索：`../../input/Production_Trade/Production_Crops_Livestock_E_All_Data_NOFLAG.csv`；`../../input/Production_Trade/retired-unused-raw/Production_Crops_Livestock_E_All_Data_NOFLAG_2.csv`；`../../src/dict_v3.xlsx`。

<a id="file-s0-12-compute-pasture-dmyield-by-country-py"></a>
### `S0_12_compute_pasture_DMyield_by_country.py`

用国家掩膜和草地生物量/面积栅格计算国家平均牧草干物质产量，导出 Pasture_DM_yield_by_country.xlsx。

源码：[S0_12_compute_pasture_DMyield_by_country.py](../../S0_12_compute_pasture_DMyield_by_country.py)；152 行。

主要接口：[`main`](../../S0_12_compute_pasture_DMyield_by_country.py#L141)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Pasture_DM_yield_by_country.xlsx`；`mask_pastureYield_0083d.nc`；`pastures_coi_AGB_kg_ha.tif`；`pastures_coi_Area_ha.tif`。

<a id="file-s0-13-extract-crop-grass-feed-ratio-py"></a>
### `S0_13_extract_crop_grass_feed_ratio.py`

从 GLEAM 补充材料指定表格提取生产系统饲料构成、国家映射和畜群权重，计算加权区域/国家草料与作物饲料比例。

源码：[S0_13_extract_crop_grass_feed_ratio.py](../../S0_13_extract_crop_grass_feed_ratio.py)；423 行。

主要接口：[`extract_text_range`](../../S0_13_extract_crop_grass_feed_ratio.py#L47)、[`parse_table_s10`](../../S0_13_extract_crop_grass_feed_ratio.py#L56)、[`fill_regions_with_wrd`](../../S0_13_extract_crop_grass_feed_ratio.py#L124)、[`parse_table_s4_mapping`](../../S0_13_extract_crop_grass_feed_ratio.py#L143)、[`parse_table_s11`](../../S0_13_extract_crop_grass_feed_ratio.py#L214)、[`build_schema_codebook`](../../S0_13_extract_crop_grass_feed_ratio.py#L265)。

文件线索：`/mnt/data/TableS10_p60_70_combined_with_country_weighted.xlsx`。

<a id="file-s0-14-sspdb-gdp-change-refill-py"></a>
### `S0_14_SSPDB_GDP_change_refill.py`

计算 SSP GDP 相对 2020 年变化比，将情景—区域结果按字典和收入分类扩展/填补至国家，输出运行期收入驱动工作簿。

源码：[S0_14_SSPDB_GDP_change_refill.py](../../S0_14_SSPDB_GDP_change_refill.py)；274 行。

主要接口：[`is_year_col`](../../S0_14_SSPDB_GDP_change_refill.py#L31)、[`year_to_int`](../../S0_14_SSPDB_GDP_change_refill.py#L45)。

文件线索：`../../input/Driver/Income/SSPDB_future_GDP_with_change_ratio.xlsx`；`../../input/Driver/Income/retired_unused_raw/SSPDB_future_GDP.xlsx`；`../../src/dict_v3.xlsx`。

<a id="file-s0-15-manure-treatment-ratio-refill-py"></a>
### `S0_15_manure_treatment_ratio_refill.py`

计算粪便管理、施土、留在牧场比例，按时间、区域和全球规则补缺并纠正比例冲突，输出比例表与日志。

源码：[S0_15_manure_treatment_ratio_refill.py](../../S0_15_manure_treatment_ratio_refill.py)；170 行。

主要接口：[`sel`](../../S0_15_manure_treatment_ratio_refill.py#L33)、[`safe_div`](../../S0_15_manure_treatment_ratio_refill.py#L47)、[`fill_all_nan_rows`](../../S0_15_manure_treatment_ratio_refill.py#L68)、[`to_rows`](../../S0_15_manure_treatment_ratio_refill.py#L131)。

文件线索：`../../input/Manure_Stock/Environment_LivestockManure_with_ratios_v2.csv`；`../../input/Manure_Stock/retired-unused-raw/Environment_LivestockManure_E_All_Data_NOFLAG.csv`；`../../input/Manure_Stock/retired-unused-raw/Environment_LivestockManure_ratios_logs.xlsx`；`../../src/dict_v3.xlsx`。

<a id="file-s0-15-manure-treatment-ratio-refill-2-py"></a>
### `S0_15_manure_treatment_ratio_refill_2.py`

对粪便三类比例做补齐和规范化的另一加工入口，围绕 Environment_LivestockManure_with_ratio.csv 工作；不应仅因编号相近就将两版连续重复处理。

源码：[S0_15_manure_treatment_ratio_refill_2.py](../../S0_15_manure_treatment_ratio_refill_2.py)；263 行。

主要接口：[`main`](../../S0_15_manure_treatment_ratio_refill_2.py#L113)。

文件线索：`Environment_LivestockManure_with_ratio.csv`；`dict_v3.xlsx`。

<a id="file-s0-16-gce-crop-parameters-py"></a>
### `S0_16_gce_crop_parameters.py`

从历史作物排放与生产数据反算残余物含氮量、焚烧干物质、稻作和肥料等参数，生成国家—作物 GCE 参数辅助表。

源码：[S0_16_gce_crop_parameters.py](../../S0_16_gce_crop_parameters.py)；573 行。

主要接口：[`ensure_exists`](../../S0_16_gce_crop_parameters.py#L55)、[`main`](../../S0_16_gce_crop_parameters.py#L402)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Emissions_crops_E_All_Data_NOFLAG.csv`；`Fertilizer_efficiency.xlsx`；`GCE_crop_parameters_country_item_S0_16.csv`；`Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv`；`dict_v3.xlsx`。

<a id="file-s0-17-luh2-data-analysis-py"></a>
### `S0_17_LUH2_data_analysis.py`

结合 LUH2 状态、转换和国家掩膜，汇总 2010—2020 国家耕地/草地/森林面积及粗分类转换，写 LUH2_data_summary.xlsx。

源码：[S0_17_LUH2_data_analysis.py](../../S0_17_LUH2_data_analysis.py)；301 行。

主要接口：[`estimate_area_ha`](../../S0_17_LUH2_data_analysis.py#L72)、[`ensure_year_dim`](../../S0_17_LUH2_data_analysis.py#L90)、[`load_mask_array`](../../S0_17_LUH2_data_analysis.py#L107)、[`load_mask_lookup`](../../S0_17_LUH2_data_analysis.py#L119)、[`reindex_years`](../../S0_17_LUH2_data_analysis.py#L147)、[`aggregate_by_mask`](../../S0_17_LUH2_data_analysis.py#L152)、[`main`](../../S0_17_LUH2_data_analysis.py#L277)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`LUH2_GCB2019_states_2010_2020.nc4`；`LUH2_GCB2019_transitions_2010_2020.nc4`；`LUH2_data_summary.xlsx`；`dict_v3.xlsx`；`mask_LUH2_025d.nc`。

<a id="file-s0-18-soil-drained-ef-refill-py"></a>
### `S0_18_soil_drained_EF_refill.py`

以历史排水有机土壤排放和面积反算 CO2/N2O 因子与面积关联比例，按区域等规则补缺，导出 soil_drained_parameters.xlsx。

源码：[S0_18_soil_drained_EF_refill.py](../../S0_18_soil_drained_EF_refill.py)；213 行。

主要接口：[`parse_args`](../../S0_18_soil_drained_EF_refill.py#L38)、[`melt_years`](../../S0_18_soil_drained_EF_refill.py#L54)、[`load_region_map`](../../S0_18_soil_drained_EF_refill.py#L65)、[`load_emission_data`](../../S0_18_soil_drained_EF_refill.py#L72)、[`compute_emission_factors`](../../S0_18_soil_drained_EF_refill.py#L82)、[`compute_area_correlation`](../../S0_18_soil_drained_EF_refill.py#L115)、[`main`](../../S0_18_soil_drained_EF_refill.py#L183)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Emissions_Drained_Organic_Soils_E_All_Data_NOFLAG.csv`；`Inputs_LandUse_E_All_Data_NOFLAG_with_Pasture.csv`；`dict_v3.xlsx`；`soil_drained_parameters.xlsx`。

<a id="file-s0-19-historical-max-production-py"></a>
### `S0_19_historical_max_production.py`

依据字典商品映射和有效国家提取历史最大产量，形成求解器历史产能锚定输入；不能把历史最高值误当情景预测。

源码：[S0_19_historical_max_production.py](../../S0_19_historical_max_production.py)；243 行。

主要接口：[`main`](../../S0_19_historical_max_production.py#L140)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`S0_19_historical_max_production.csv`；`dict_v3.xlsx`。

<a id="file-s0-20-analysis-maskid-missing-country-py"></a>
### `S0_20_analysis_maskID_missing_country.py`

诊断 LUH2 国家掩膜中的 ID/缺失国家，并包含地理位置查询辅助逻辑；是空间数据检查工具，不参与每次 S4 求解。

源码：[S0_20_analysis_maskID_missing_country.py](../../S0_20_analysis_maskID_missing_country.py)；99 行。

主要接口：[`get_location_name`](../../S0_20_analysis_maskID_missing_country.py#L29)、[`main`](../../S0_20_analysis_maskID_missing_country.py#L44)。

文件线索：`..\..\src\mask_LUH2_025d.nc`。

<a id="file-s0-21-landuse-historical-refill-py"></a>
### `S0_21_Landuse_historical_refill.py`

合并 LUH2 国家土地汇总与 FAO 土地统计，补齐历史/基期土地覆盖，生成 Land_cover_base_refill.xlsx。

源码：[S0_21_Landuse_historical_refill.py](../../S0_21_Landuse_historical_refill.py)；123 行。

执行形式：主要为脚本顶层处理；导入时也可能触发读写，使用前检查配置。

文件线索：`../../input/Land/Inputs_LandUse_E_All_Data_NOFLAG_with_Pasture.csv`；`../../input/Land/LUH2_data_summary.xlsx`；`../../input/Land/Land_cover_base_refill.xlsx`；`../../src/dict_v3.xlsx`。

<a id="file-s0-22-forest-ef-recal-py"></a>
### `S0_22_Forest_EF_recal.py`

依据历史森林排放/碳汇和森林面积反算国家森林因子，输出 Forest_EF_recal.csv，供参数整理和土地核算使用。

源码：[S0_22_Forest_EF_recal.py](../../S0_22_Forest_EF_recal.py)；142 行。

主要接口：[`recal_forest_ef`](../../S0_22_Forest_EF_recal.py#L10)。

文件线索：`../../input/Emission/Emission_LULUCF_Historical_updated.xlsx`；`../../input/Land/Land_cover_base_refill.xlsx`；`../../src/Forest_EF_recal.csv`；`../../src/dict_v3.xlsx`。

<a id="file-s0-23-macc-build-py"></a>
### `S0_23_MACC_build.py`

将原始农业技术 MACC 数据按过程匹配、年份筛选和成本曲线整理，导出 MACC_Final_Data.csv 与检查图；属于旧 MACC 输入准备链。

源码：[S0_23_MACC_build.py](../../S0_23_MACC_build.py)；230 行。

主要接口：[`match_ag_tech`](../../S0_23_MACC_build.py#L83)。

文件线索：`../../input/Price_Cost/Cost/MACC_Final_Data.csv`；`../../input/Price_Cost/Cost/PNG/MACC_Agriculture_Final.png`；`../../input/Price_Cost/Cost/macc_results_raw_AGRICULTURE.csv`。

<a id="file-s0-24-reduction-cost-2080-py"></a>
### `S0_24_Reduction_cost_2080.py`

围绕 2080 目标年按相邻年份优先级填补原始 MACC 技术成本，生成 2080 成本分析工作簿。

源码：[S0_24_Reduction_cost_2080.py](../../S0_24_Reduction_cost_2080.py)；188 行。

主要接口：[`match_ag_tech`](../../S0_24_Reduction_cost_2080.py#L47)、[`get_species`](../../S0_24_Reduction_cost_2080.py#L55)、[`fill_data_with_priority`](../../S0_24_Reduction_cost_2080.py#L74)。

文件线索：`../../input/Price_Cost/Cost/MACC_2080_Optimized_Analysis.xlsx`；`../../input/Price_Cost/Cost/macc_results_raw_AGRICULTURE.csv`。

<a id="file-s0-24-reduction-cost-allyear-py"></a>
### `S0_24_Reduction_cost_allYear.py`

将农业 MACC 原始技术按过程/畜种匹配并计算各年份加权成本，输出跨年成本工作簿。

源码：[S0_24_Reduction_cost_allYear.py](../../S0_24_Reduction_cost_allYear.py)；159 行。

主要接口：[`match_ag_tech`](../../S0_24_Reduction_cost_allYear.py#L37)、[`get_species`](../../S0_24_Reduction_cost_allYear.py#L45)。

文件线索：`../../input/Price_Cost/Cost/MACC_Weighted_Cost_by_Species_AllYears.xlsx`；`../../input/Price_Cost/Cost/macc_results_raw_AGRICULTURE.csv`。

<a id="file-s0-24-reduction-cost-country-process-2080-py"></a>
### `S0_24_Reduction_cost_country_process_2080.py`

将 2080 技术成本映射并填补为国家—过程成本表，输出旧兼容 MACC_2080_GapFilled_Final_overZero.xlsx；不是当前 v2 JSON 的运行时加载器。

源码：[S0_24_Reduction_cost_country_process_2080.py](../../S0_24_Reduction_cost_country_process_2080.py)；311 行。

主要接口：[`read_csv_robust`](../../S0_24_Reduction_cost_country_process_2080.py#L49)、[`match_ag_tech`](../../S0_24_Reduction_cost_country_process_2080.py#L84)、[`process_data`](../../S0_24_Reduction_cost_country_process_2080.py#L95)。

文件线索：`../../input/Price_Cost/Cost/MACC_2080_GapFilled_Final_overZero.xlsx`；`../../input/Price_Cost/Cost/macc_results_raw_AGRICULTURE.csv`；`../../src/dict_v3.xlsx`。

<a id="file-s0-25-dairy-nondairy-emis-split-py"></a>
### `S0_25_Dairy_NonDairy_emis_split.py`

按奶用与非奶用存栏等关系拆分指定畜种的历史肠道/粪便排放，输出 Emissions_livestock_dairy_split.csv，为当前 GLE 历史链提供输入。

源码：[S0_25_Dairy_NonDairy_emis_split.py](../../S0_25_Dairy_NonDairy_emis_split.py)；195 行。

主要接口：[`split_emissions`](../../S0_25_Dairy_NonDairy_emis_split.py#L111)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Emissions_livestock_E_All_Data_NOFLAG.csv`；`Emissions_livestock_dairy_split.csv`；`Environment_LivestockManure_with_ratio.csv`。

<a id="file-s0-26-feed-info-refill-py"></a>
### `S0_26_feed_info_refill.py`

依据字典中的分层区域映射补齐国家—牲畜每头饲料需求及相关系数，生成 Feed_need_per_head_by_country_livestcok_refilled.xlsx。

源码：[S0_26_feed_info_refill.py](../../S0_26_feed_info_refill.py)；216 行。

主要接口：[`clean_m49_code`](../../S0_26_feed_info_refill.py#L13)、[`fill_hierarchy`](../../S0_26_feed_info_refill.py#L19)、[`apply_proxies`](../../S0_26_feed_info_refill.py#L48)。

文件线索：`../../input/Land/Feed_pasture/Feed_need_per_head_by_country_livestcok.xlsx`；`../../input/Land/Feed_pasture/Feed_need_per_head_by_country_livestcok_refilled.xlsx`；`../../src/dict_v3.xlsx`。

<a id="file-s0-27-grassfeed-ratio-refill-py"></a>
### `S0_27_grassfeed_ratio_refill.py`

补齐牲畜作物饲料/草料比例并保留国家和物种对应关系，输出 Grass_feed_ratio_by_country_livestock_refilled.xlsx。

源码：[S0_27_grassfeed_ratio_refill.py](../../S0_27_grassfeed_ratio_refill.py)；154 行。

主要接口：[`clean_m49_code`](../../S0_27_grassfeed_ratio_refill.py#L12)、[`fill_crop_with_means`](../../S0_27_grassfeed_ratio_refill.py#L19)、[`main`](../../S0_27_grassfeed_ratio_refill.py#L57)。

文件线索：`../../input/Land/Feed_pasture/Grass_feed_ratio_by_country_livestock.xlsx`；`../../input/Land/Feed_pasture/Grass_feed_ratio_by_country_livestock_refilled.xlsx`；`../../src/dict_v3.xlsx`。

<a id="file-s0-28-dairy-yield-refill-py"></a>
### `S0_28_dairy_yield_refill.py`

补齐水牛、骆驼、山羊和绵羊奶等产品的单产数据，形成运行期补齐后的 FAOSTAT 生产文件。

源码：[S0_28_dairy_yield_refill.py](../../S0_28_dairy_yield_refill.py)；228 行。

主要接口：[`clean_m49_to_string`](../../S0_28_dairy_yield_refill.py#L27)、[`fill_with_means`](../../S0_28_dairy_yield_refill.py#L35)、[`main`](../../S0_28_dairy_yield_refill.py#L67)。

文件线索：`../../input/Production_Trade/Production_Crops_Livestock_E_All_Data_NOFLAG.csv`；`../../input/Production_Trade/Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv`；`../../src/dict_v3.xlsx`。

<a id="file-s0-29-production-baseyear-fill-placeholder-py"></a>
### `S0_29_production_baseYear_fill_placeholder.py`

检查字典目标国家—商品的 Y2020 单产或胴体重等缺口并构建补齐记录，输出带 baseYearFilled 标记的派生表；属于基期数据加工，不是占位测试脚本。

源码：[S0_29_production_baseYear_fill_placeholder.py](../../S0_29_production_baseYear_fill_placeholder.py)；185 行。

主要接口：[`format_m49`](../../S0_29_production_baseYear_fill_placeholder.py#L14)、[`load_dict`](../../S0_29_production_baseYear_fill_placeholder.py#L28)、[`build_combos`](../../S0_29_production_baseYear_fill_placeholder.py#L42)、[`build_templates`](../../S0_29_production_baseYear_fill_placeholder.py#L54)、[`create_row`](../../S0_29_production_baseYear_fill_placeholder.py#L64)、[`ensure_production`](../../S0_29_production_baseYear_fill_placeholder.py#L73)、[`main`](../../S0_29_production_baseYear_fill_placeholder.py#L165)。

文件线索：`../../input/Production_Trade/Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled.csv`；`../../src/dict_v3.xlsx`；`Production_Crops_Livestock_E_All_Data_NOFLAG.csv`；`_baseYearFilled.csv`。

<a id="file-s0-30-nutrition-base-build-py"></a>
### `S0_30_Nutrition_base_build.py`

将 FBS 营养供给和生产统计整理为国家—商品营养基准，生成 Nutrition_profile.xlsx，供后续补缺/重标度使用。

源码：[S0_30_Nutrition_base_build.py](../../S0_30_Nutrition_base_build.py)；254 行。

主要接口：[`run`](../../S0_30_Nutrition_base_build.py#L9)。

文件线索：`..\..\input\Driver\retired_unused_raw\FoodBalanceSheets_E_All_Data_NOFLAG.csv`；`..\..\input\Production_Trade\Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv`；`Nutrition_profile.xlsx`。

<a id="file-s0-31-nutrition-base-supp-py"></a>
### `S0_31_Nutrition_base_supp.py`

根据 nutrition_missing_report 给已有营养表补充缺失国家/商品记录，写更新版本；为历史定向修补脚本，输入路径需核对。

源码：[S0_31_Nutrition_base_supp.py](../../S0_31_Nutrition_base_supp.py)；65 行。

执行形式：主要为脚本顶层处理；导入时也可能触发读写，使用前检查配置。

文件线索：`../../input/Driver/retired_unused_raw/Nutrition_profile_updated.csv`；`../../input/Driver/retired_unused_raw/Nutrition_profile_updated2.csv`；`../../input/Driver/retired_unused_raw/nutrition_missing_report.csv`；`处理完成，文件已保存为 Nutrition_profile_updated2.csv`。

<a id="file-s0-32-nutrition-base-rescale-py"></a>
### `S0_32_Nutrition_base_rescale.py`

按 Intake_constraint 重标度营养结构；能量基期使用 Y2020 与最低能量要求的较大值，输出营养派生工作簿及诊断。

源码：[S0_32_Nutrition_base_rescale.py](../../S0_32_Nutrition_base_rescale.py)；236 行。

主要接口：[`run`](../../S0_32_Nutrition_base_rescale.py#L104)。

文件线索：`..\..\input\Constraint\Intake_constraint.xlsx`；`..\..\input\Driver\retired_unused_raw\Nutrition_profile_updated2.csv`；`Nutrition_profile_rescaled2.xlsx`；`debug_dump.txt`。

<a id="file-s0-33-build-fish-seafood-country-panel-py"></a>
### `S0_33_build_fish_seafood_country_panel.py`

读取已下载的水产统计，构建国家—年份捕捞/养殖产量、份额、养殖单产和 CH4/N2O 因子面板及日志；脚本不在内部下载原始数据。

源码：[S0_33_build_fish_seafood_country_panel.py](../../S0_33_build_fish_seafood_country_panel.py)；1,307 行。

主要接口：[`build_panel`](../../S0_33_build_fish_seafood_country_panel.py#L988)、[`write_outputs`](../../S0_33_build_fish_seafood_country_panel.py#L1180)、[`main`](../../S0_33_build_fish_seafood_country_panel.py#L1270)。

文件线索：`../../src/dict_v3.xlsx`；`Aquaculture_Quantity.csv`；`Aquaculture_Value.csv`；`CL_FI_SPECIES_GROUPS.csv`；`FAO_FBS_aquatic_products.csv`；`FAO_global_aquatic_processed_production_statistics.csv`；`FAO_global_aquatic_production_quantity.csv`。

<a id="file-s0-34-build-country-minimum-nutrition-requirement-py"></a>
### `S0_34_build_country_minimum_nutrition_requirement.py`

结合有效国家字典、最低膳食能量和食品安全营养统计构建国家最低营养需求表；包含数据下载辅助函数和地区回退处理。

源码：[S0_34_build_country_minimum_nutrition_requirement.py](../../S0_34_build_country_minimum_nutrition_requirement.py)；503 行。

主要接口：[`download`](../../S0_34_build_country_minimum_nutrition_requirement.py#L53)、[`download_first_working`](../../S0_34_build_country_minimum_nutrition_requirement.py#L62)、[`clean_m49`](../../S0_34_build_country_minimum_nutrition_requirement.py#L72)、[`safe_mean`](../../S0_34_build_country_minimum_nutrition_requirement.py#L80)、[`pick_latest_3yr_window`](../../S0_34_build_country_minimum_nutrition_requirement.py#L87)、[`standardize_region_df`](../../S0_34_build_country_minimum_nutrition_requirement.py#L100)、[`main`](../../S0_34_build_country_minimum_nutrition_requirement.py#L487)。

文件线索：`../../src/dict_v3.xlsx`；`/mnt/data/region_with_MDER_protein_fat.xlsx`；`RegionM49.json`；`https://codelists.codeforiati.org/api/json/en/RegionM49.json`。

<a id="file-s0-35-elasticity-signs-revise-py"></a>
### `S0_35_Elasticity_signs_revise.py`

按商品供需交叉价格符号矩阵修改弹性工作簿的两个交叉表，保留其他 sheet；行表示数量响应商品，列表示价格变化商品。

源码：[S0_35_Elasticity_signs_revise.py](../../S0_35_Elasticity_signs_revise.py)；295 行。

主要接口：[`read_sign_matrix`](../../S0_35_Elasticity_signs_revise.py#L53)、[`build_sign_dict`](../../S0_35_Elasticity_signs_revise.py#L90)、[`find_header_row_and_col_map`](../../S0_35_Elasticity_signs_revise.py#L104)、[`revise_sheet_inplace`](../../S0_35_Elasticity_signs_revise.py#L152)、[`main`](../../S0_35_Elasticity_signs_revise.py#L238)。

文件线索：`../../input/Driver/Elasticity/Elasticity_v3_processed_filled_by_region.xlsx`；`../../input/Driver/Elasticity/Item_demand_supplu_cross_prodchain_signs.xlsx`；`../../input/Driver/Elasticity/retired_raw_unused/Elasticity_v3_processed_filled_by_region.xlsx`。

<a id="file-s0-36-make-armington-from-gtap10-py"></a>
### `S0_36_make_armington_from_gtap10.py`

提取 GTAP10 包中的替代弹性并映射到模型商品，生成 Armington_elasticity.xlsx，支持 regional_armington 贸易路径。

源码：[S0_36_make_armington_from_gtap10.py](../../S0_36_make_armington_from_gtap10.py)；369 行。

主要接口：[`load_gtap_esub`](../../S0_36_make_armington_from_gtap10.py#L160)、[`item_to_gtap_code`](../../S0_36_make_armington_from_gtap10.py#L179)、[`choose_sigma`](../../S0_36_make_armington_from_gtap10.py#L254)、[`main`](../../S0_36_make_armington_from_gtap10.py#L265)。

文件线索：`Armington_elasticity.xlsx`；`dict_v3.xlsx`。

<a id="file-s0-37-fbs-demand-base-refill-py"></a>
### `S0_37_FBS_Demand_base_refill.py`

按字典和生产统计补齐基期 FBS 国内供给/用途数据，生成 FoodBalanceSheets_E_All_Data_NOFLAG_demand_refilled.xlsx。

源码：[S0_37_FBS_Demand_base_refill.py](../../S0_37_FBS_Demand_base_refill.py)；195 行。

主要接口：[`main`](../../S0_37_FBS_Demand_base_refill.py#L120)。

文件线索：`FoodBalanceSheets_E_All_Data_NOFLAG.csv`；`FoodBalanceSheets_E_All_Data_NOFLAG_demand_refilled.xlsx`；`Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv`；`dict_v3.xlsx`。

<a id="file-s0-38-nutrition-profile-recalculated-fromd0-py"></a>
### `S0_38_Nutrition_profile_recalculated_fromD0.py`

从 S2 构造的 D0、FBS 和人口重新计算人均营养结构，输出 Nutrition_profile_recalculated_fromD0.xlsx，并提供食物拆分辅助函数。

源码：[S0_38_Nutrition_profile_recalculated_fromD0.py](../../S0_38_Nutrition_profile_recalculated_fromD0.py)；322 行。

主要接口：[`run`](../../S0_38_Nutrition_profile_recalculated_fromD0.py#L132)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)。

本目录调用/引用者：[S0_38_Nutrition_profile_recalculated_fromD0_food.py](../../S0_38_Nutrition_profile_recalculated_fromD0_food.py)。

文件线索：`Nutrition_profile_recalculated_fromD0.xlsx`。

<a id="file-s0-38-nutrition-profile-recalculated-fromd0-food-py"></a>
### `S0_38_Nutrition_profile_recalculated_fromD0_food.py`

复用上一脚本的映射与食物提取，以食物用途而非全部国内需求构建营养基准，输出当前历史营养路径使用的 food_demand 工作簿。

源码：[S0_38_Nutrition_profile_recalculated_fromD0_food.py](../../S0_38_Nutrition_profile_recalculated_fromD0_food.py)；189 行。

主要接口：[`run`](../../S0_38_Nutrition_profile_recalculated_fromD0_food.py#L20)。

代码内导入：[S0_38_Nutrition_profile_recalculated_fromD0.py](../../S0_38_Nutrition_profile_recalculated_fromD0.py)、[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)。

文件线索：`Nutrition_profile_recalculated_fromD0_food_demand.xlsx`。

<a id="file-s0-39-calibrate-gce-synthetic-fert-ef-2020-py"></a>
### `S0_39_calibrate_gce_synthetic_fert_ef_2020.py`

用 2020 年肥料效率/历史强度校准 GCE 参数中的 Synthetic fertilizers 排放因子，只调整指定参数的 Y2020；会写派生参数工作簿。

源码：[S0_39_calibrate_gce_synthetic_fert_ef_2020.py](../../S0_39_calibrate_gce_synthetic_fert_ef_2020.py)；327 行。

主要接口：[`main`](../../S0_39_calibrate_gce_synthetic_fert_ef_2020.py#L185)。

文件线索：`Fertilizer_efficiency.xlsx`；`GCE_parameters.xlsx`；`dict_v3.xlsx`。

<a id="file-s0-40-luce-parameter-gen-py"></a>
### `S0_40_LUCE_parameter_gen.py`

根据国家空间信息、气候生态区、土壤和作物类别构建 Tier 1 土地碳参数匹配键并写增强工作簿；含固定路径与外部数据查询辅助逻辑。

源码：[S0_40_LUCE_parameter_gen.py](../../S0_40_LUCE_parameter_gen.py)；638 行。

主要接口：[`parse_idrisi_rdc`](../../S0_40_LUCE_parameter_gen.py#L82)、[`load_adm0_geoms`](../../S0_40_LUCE_parameter_gen.py#L96)、[`wdi_fetch_indicator`](../../S0_40_LUCE_parameter_gen.py#L134)、[`wdi_latest_by_iso3`](../../S0_40_LUCE_parameter_gen.py#L156)、[`DominantResult`](../../S0_40_LUCE_parameter_gen.py#L201)、[`dominant_code_in_geom`](../../S0_40_LUCE_parameter_gen.py#L216)、[`main`](../../S0_40_LUCE_parameter_gen.py#L438)。

文件线索：`/mnt/data/LUCE_parameter_Tier1_LUH2_mapping.xlsx`；`/mnt/data/LUCE_parameter_Tier1_LUH2_mapping_with_country_keys.xlsx`；`/mnt/data/countries_codes_and_coordinates.csv`；`/mnt/data/region.xlsx`；`/mnt/data/region_with_Tier1_keys.xlsx`；`AG.LND.ARBL.ZS.json`；`AG.LND.CROP.ZS.json`。

<a id="file-s0-41-scenario-multiplier-besthisvalue-extract-py"></a>
### `S0_41_Scenario_multiplier_bestHisValue_extract.py`

汇集作物、畜牧、土壤、水产与需求数据的历史范围，生成 Scenario_variable_historical_range.xlsx，供 Y2020 引用及情景边界解释使用。

源码：[S0_41_Scenario_multiplier_bestHisValue_extract.py](../../S0_41_Scenario_multiplier_bestHisValue_extract.py)；812 行。

主要接口：[`main`](../../S0_41_Scenario_multiplier_bestHisValue_extract.py#L699)。

代码内导入：[S2_0_load_data.py](../../S2_0_load_data.py)、[config_paths.py](../../config_paths.py)。

文件线索：`Demand_composition.xlsx`；`GCE_parameters.xlsx`；`GLE_parameters.xlsx`；`Scenario_variable_historical_range.xlsx`；`Soil_parameters.xlsx`；`dict_v3.xlsx`；`fish_seafood_country_panel_2000_present.xlsx`。

<a id="file-s0-42-nutrition-scenario-gen-py"></a>
### `S0_42_Nutrition_scenario_gen.py`

在历史 food_demand 营养工作簿中生成反刍份额上限、增减和替代饮食结构等情景表/列，包括 low_land_new 相关方案。

源码：[S0_42_Nutrition_scenario_gen.py](../../S0_42_Nutrition_scenario_gen.py)；918 行。

主要接口：[`main`](../../S0_42_Nutrition_scenario_gen.py#L825)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`EAT_Lancet_energy_share.xlsx`；`Nutrition_profile_recalculated_fromD0_food_demand.xlsx`；`Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv`；`dict_v3.xlsx`。

<a id="file-s0-43-eat-lancet-nutrition-profile-gen-py"></a>
### `S0_43_EAT_LANCET_nutrition_profile_gen.py`

构建按模型 Item_Nutrition_Map 对齐的 EAT-Lancet 2500 kcal/日营养/能量份额向量，导出 Excel、CSV、JSON，供饮食情景使用。

源码：[S0_43_EAT_LANCET_nutrition_profile_gen.py](../../S0_43_EAT_LANCET_nutrition_profile_gen.py)；260 行。

主要接口：[`main`](../../S0_43_EAT_LANCET_nutrition_profile_gen.py#L28)。

文件线索：`../../src/dict_v3.xlsx`；`EAT_Lancet_energy_share_vector_via_EmisItem.csv`；`EAT_Lancet_energy_share_vector_via_EmisItem.json`；`EAT_Lancet_energy_share_vector_via_EmisItem.xlsx`。

<a id="file-s0-44-ar6-harmonize-baseyear-py"></a>
### `S0_44_AR6_harmonize_baseyear.py`

将 AR6/SCI 情景序列与历史目标基期协调并输出诊断；当前配置实际指向 SCI 数据库，文件名不等于固定处理 AR6。

源码：[S0_44_AR6_harmonize_baseyear.py](../../S0_44_AR6_harmonize_baseyear.py)；461 行。

主要接口：[`harmonize_sheet`](../../S0_44_AR6_harmonize_baseyear.py#L236)、[`main`](../../S0_44_AR6_harmonize_baseyear.py#L397)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`SCI_Database.xlsx`。

<a id="file-s0-45-slice-luh2-subset-py"></a>
### `S0_45_slice_LUH2_subset.py`

从大型 LUH2 states/transitions NetCDF 截取 2010—2020 子集，减少后续读取量；写新子集文件而不是每次求解都重读全时段。

源码：[S0_45_slice_LUH2_subset.py](../../S0_45_slice_LUH2_subset.py)；82 行。

主要接口：[`main`](../../S0_45_slice_LUH2_subset.py#L55)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`LUH2_GCB2019_states.nc4`；`LUH2_GCB2019_transitions.nc4`。

<a id="file-s0-46-ar6-sci-scenario-combine-py"></a>
### `S0_46_AR6_SCI_scenario_combine.py`

比较协调后的 AR6 和 SCI 情景键，将 SCI 尚未包含的 AR6 行导出为补充工作簿，按模型—情景、区域、变量及单位判断重复。

源码：[S0_46_AR6_SCI_scenario_combine.py](../../S0_46_AR6_SCI_scenario_combine.py)；117 行。

主要接口：[`main`](../../S0_46_AR6_SCI_scenario_combine.py#L79)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`AR6_scenario_prepared_harmonization.xlsx`；`SCI_Database_harmonization.xlsx`；`SCI_added_harmonization_from_AR6.xlsx`。

<a id="file-s0-47-sci-harmonization-pooled-fallback-fix-py"></a>
### `S0_47_SCI_harmonization_pooled_fallback_fix.py`

对已协调 SCI 中采用回退历史目标的行重新构造跨温控组汇总目标，写修正版及诊断；不会完整重跑原始协调步骤。

源码：[S0_47_SCI_harmonization_pooled_fallback_fix.py](../../S0_47_SCI_harmonization_pooled_fallback_fix.py)；262 行。

主要接口：[`main`](../../S0_47_SCI_harmonization_pooled_fallback_fix.py#L223)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`SCI_Database_harmonization.xlsx`；`SCI_Database_harmonization_pooled_fallback_fix.xlsx`。

<a id="file-s0-48-history-emission-summary-py"></a>
### `S0_48_history_emission_summary.py`

整合历史农业、土地、水产等排放及参数映射，构建 1961—2020 排放历史汇总工作簿，供结构图和情景基期比较。

源码：[S0_48_history_emission_summary.py](../../S0_48_history_emission_summary.py)；2,260 行。

主要接口：[`build_history_emission_summary`](../../S0_48_history_emission_summary.py#L2109)、[`main`](../../S0_48_history_emission_summary.py#L2254)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_2_feed_demand.py](../../S3_2_feed_demand.py)、[S4_1_results.py](../../S4_1_results.py)、[config_paths.py](../../config_paths.py)、[gsoil_emission_complete.py](../../gsoil_emission_complete.py)。

文件线索：`Emission_LULUCF_Historical_updated_Select1_Y1961_Y1999_backfilled.xlsx`；`Emission_history_1961-2020_summary.xlsx`；`Emissions_Drained_Organic_Soils_E_All_Data_NOFLAG.csv`；`Emissions_crops_E_All_Data_NOFLAG.csv`；`Emissions_livestock_E_All_Data_NOFLAG.csv`；`Environment_LivestockManure_with_ratio.csv`；`Fertilizer_efficiency.xlsx`。

<a id="file-s0-49-emission-result-summary-py"></a>
### `S0_49_emission_result_summary.py`

读取指定运行的详细排放、产量和营养/市场结果，整理 2080 年排放与商品指标，输出 Y2080_Emission_result_summary.xlsx，供后续分解和单位热量图。

源码：[S0_49_emission_result_summary.py](../../S0_49_emission_result_summary.py)；435 行。

主要接口：[`build_emission_result_summary`](../../S0_49_emission_result_summary.py#L389)、[`main`](../../S0_49_emission_result_summary.py#L418)。

代码内导入：[S2_0_load_data.py](../../S2_0_load_data.py)、[SP_M1a_Figure_pie_structure_pre.py](../../SP_M1a_Figure_pie_structure_pre.py)、[config_paths.py](../../config_paths.py)。

文件线索：`Emis/emissions_summary_By_Country_Process_Item.csv`；`Emis/emissions_summary_By_Country_Process_Item.xlsx`；`Y2080_Emission_result_summary.xlsx`；`commodity_balance_by_commodity.csv`；`dict_v3.xlsx`；`market_summary.csv`；`production_summary.csv`。

<a id="file-s0-50-prepare-bioenergy-history-py"></a>
### `S0_50_prepare_bioenergy_history.py`

将 FAOSTAT 生物能源历史标准化为国家—载体时间序列、国家份额和覆盖诊断，为历史原料桥接与未来分配提供参考。

源码：[S0_50_prepare_bioenergy_history.py](../../S0_50_prepare_bioenergy_history.py)；186 行。

主要接口：[`prepare_history`](../../S0_50_prepare_bioenergy_history.py#L43)、[`build_country_profiles`](../../S0_50_prepare_bioenergy_history.py#L121)、[`main`](../../S0_50_prepare_bioenergy_history.py#L151)。

代码内导入：[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_3_bioenergy.py](../../S3_3_bioenergy.py)、[config_paths.py](../../config_paths.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

文件线索：`bioenergy_country_profiles.csv`；`bioenergy_history_country_carrier.csv`；`bioenergy_history_coverage.csv`。

<a id="file-s0-51-prepare-bioenergy-feedstock-bridge-py"></a>
### `S0_51_prepare_bioenergy_feedstock_bridge.py`

利用载体—原料份额和热值/转换参数，将能源历史转换为物理原料需求，输出 bioenergy_historical_feedstock.csv 及覆盖表。

源码：[S0_51_prepare_bioenergy_feedstock_bridge.py](../../S0_51_prepare_bioenergy_feedstock_bridge.py)；364 行。

主要接口：[`prepare_historical_feedstocks`](../../S0_51_prepare_bioenergy_feedstock_bridge.py#L177)、[`main`](../../S0_51_prepare_bioenergy_feedstock_bridge.py#L306)。

代码内导入：[S0_53_prepare_bioenergy_scenarios.py](../../S0_53_prepare_bioenergy_scenarios.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_3_bioenergy.py](../../S3_3_bioenergy.py)、[config_paths.py](../../config_paths.py)、[runtime_data_cache.py](../../runtime_data_cache.py)。

本目录调用/引用者：[ST_bioenergy_mvp_test.py](../../ST_bioenergy_mvp_test.py)。

文件线索：`bioenergy_feedstock_bridge_coverage.csv`；`bioenergy_historical_feedstock.csv`；`bioenergy_history_country_carrier.csv`。

<a id="file-s0-52-prepare-bioenergy-resource-constraints-py"></a>
### `S0_52_prepare_bioenergy_resource_constraints.py`

综合残余物、非作物技术潜力、能源作物产量和可用土地，生成 bioenergy_resource_constraints.csv 及派生参数/诊断，供资源与土地限制。

源码：[S0_52_prepare_bioenergy_resource_constraints.py](../../S0_52_prepare_bioenergy_resource_constraints.py)；1,169 行。

主要接口：[`build_residue_quality_lookup`](../../S0_52_prepare_bioenergy_resource_constraints.py#L326)、[`build_crop_residue_constraints`](../../S0_52_prepare_bioenergy_resource_constraints.py#L378)、[`build_li2020_country_yields`](../../S0_52_prepare_bioenergy_resource_constraints.py#L508)、[`build_energy_crop_constraints`](../../S0_52_prepare_bioenergy_resource_constraints.py#L653)、[`build_noncrop_feedstock_constraints`](../../S0_52_prepare_bioenergy_resource_constraints.py#L780)、[`write_outputs`](../../S0_52_prepare_bioenergy_resource_constraints.py#L972)、[`main`](../../S0_52_prepare_bioenergy_resource_constraints.py#L1007)。

代码内导入：[S2_0_load_data.py](../../S2_0_load_data.py)、[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S0_54_prepare_bioenergy_eligible_land_mask.py](../../S0_54_prepare_bioenergy_eligible_land_mask.py)。

文件线索：`Bioenergy_crop_yields.nc`；`Crop residues.csv`；`Land_cover_base_refill.xlsx`；`Readme file.csv`；`Residue quality_12_05_24.csv`；`bioenergy_country_profiles.csv`；`bioenergy_energy_crop_country_yields.csv`。

<a id="file-s0-53-prepare-bioenergy-scenarios-py"></a>
### `S0_53_prepare_bioenergy_scenarios.py`

根据 AR6/SCI 生物质初级能源轨迹分位数、国家历史份额和资源约束构造低中高需求，输出情景原料表、全球目标与分配审核。

源码：[S0_53_prepare_bioenergy_scenarios.py](../../S0_53_prepare_bioenergy_scenarios.py)；1,599 行。

主要接口：[`FeedstockSpec`](../../S0_53_prepare_bioenergy_scenarios.py#L362)、[`normalize_m49`](../../S0_53_prepare_bioenergy_scenarios.py#L547)、[`parse_years`](../../S0_53_prepare_bioenergy_scenarios.py#L566)、[`ramp_to_target`](../../S0_53_prepare_bioenergy_scenarios.py#L577)、[`trajectory_value`](../../S0_53_prepare_bioenergy_scenarios.py#L593)、[`trajectory_from_points`](../../S0_53_prepare_bioenergy_scenarios.py#L616)、[`main`](../../S0_53_prepare_bioenergy_scenarios.py#L1578)。

本目录调用/引用者：[S0_51_prepare_bioenergy_feedstock_bridge.py](../../S0_51_prepare_bioenergy_feedstock_bridge.py)、[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py)。

文件线索：`Land_cover_base_refill.xlsx`；`bioenergy_country_profiles.csv`；`bioenergy_energy_crop_country_yields.csv`；`bioenergy_resource_constraints.csv`；`bioenergy_scenario_targets.csv`；`dict_v3.xlsx`。

<a id="file-s0-54-prepare-bioenergy-eligible-land-mask-py"></a>
### `S0_54_prepare_bioenergy_eligible_land_mask.py`

将 WorldCover 与可选保护地/适宜性数据对齐 LUH2 网格，生成能源作物适宜土地栅格、国家面积表和诊断，作为 S0.52 上游。

源码：[S0_54_prepare_bioenergy_eligible_land_mask.py](../../S0_54_prepare_bioenergy_eligible_land_mask.py)；508 行。

主要接口：[`build_mask`](../../S0_54_prepare_bioenergy_eligible_land_mask.py#L356)、[`parse_args`](../../S0_54_prepare_bioenergy_eligible_land_mask.py#L474)、[`main`](../../S0_54_prepare_bioenergy_eligible_land_mask.py#L499)。

代码内导入：[S0_52_prepare_bioenergy_resource_constraints.py](../../S0_52_prepare_bioenergy_resource_constraints.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[config_paths.py](../../config_paths.py)。

文件线索：`_Map.tif`；`bioenergy_energy_crop_eligible_land_mask.csv`；`bioenergy_energy_crop_eligible_land_mask.tif`；`bioenergy_energy_crop_eligible_land_mask_diagnostics.csv`；`mask_LUH2_025d.nc`。

<a id="file-s0-55-prepare-bioenergy-noncrop-availability-py"></a>
### `S0_55_prepare_bioenergy_noncrop_availability.py`

从 OMD 非作物残余物/副产品汇总国家技术潜力，保留总潜力与保守可用量，供 S0.52 资源限制输入。

源码：[S0_55_prepare_bioenergy_noncrop_availability.py](../../S0_55_prepare_bioenergy_noncrop_availability.py)；499 行。

主要接口：[`build_availability`](../../S0_55_prepare_bioenergy_noncrop_availability.py#L375)、[`parse_args`](../../S0_55_prepare_bioenergy_noncrop_availability.py#L473)、[`main`](../../S0_55_prepare_bioenergy_noncrop_availability.py#L485)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Agroprocessing residues.csv`；`Coffee cocoa and oilpalm residues.csv`；`Fish processing byproducts.csv`；`Manure.csv`；`Meat processing residues.csv`；`Poultry slaughterhouse residues.csv`；`Sugarcane bagase.csv`。


<a id="group-4"></a>
## 4. STS 热应激完整功能链

<a id="file-sts-s0-01-prepare-thermal-exposure-py"></a>
### `STS_S0_01_prepare_thermal_exposure.py`

STS 暴露命令行入口，接收 climate、livestock-weights、output、manifest 参数并调用 exposure_pipeline；不自动执行响应拟合或供需求解。

源码：[STS_S0_01_prepare_thermal_exposure.py](../../STS_S0_01_prepare_thermal_exposure.py)；31 行。

主要接口：[`main`](../../STS_S0_01_prepare_thermal_exposure.py#L10)。

代码内导入：[STS_thermal_exposure_pipeline.py](../../STS_thermal_exposure_pipeline.py)。

<a id="file-sts-s0-02-prepare-thermal-response-registry-py"></a>
### `STS_S0_02_prepare_thermal_response_registry.py`

STS 响应参数命令行入口，从 evidence 调用 response_evidence，输出注册表和留出研究验证预测。

源码：[STS_S0_02_prepare_thermal_response_registry.py](../../STS_S0_02_prepare_thermal_response_registry.py)；27 行。

主要接口：[`main`](../../STS_S0_02_prepare_thermal_response_registry.py#L10)。

代码内导入：[STS_thermal_response_evidence.py](../../STS_thermal_response_evidence.py)。

<a id="file-sts-s0-05-validate-and-summarize-py"></a>
### `STS_S0_05_validate_and_summarize.py`

读取已有 draws CSV，按指定 metric 汇总国家—年份—商品样本，可选与 observations 对比并写 JSON 报告；不自动生成集合或重跑 S4。

源码：[STS_S0_05_validate_and_summarize.py](../../STS_S0_05_validate_and_summarize.py)；50 行。

主要接口：[`main`](../../STS_S0_05_validate_and_summarize.py#L17)。

代码内导入：[STS_thermal_uncertainty_validation.py](../../STS_thermal_uncertainty_validation.py)。

<a id="file-sts-thermal-exposure-pipeline-py"></a>
### `STS_thermal_exposure_pipeline.py`

验证逐小时气候/畜牧权重，先在 5 km 网格计算冷热暴露、持续事件、恢复和滞后等指标，再输出暴露表与来源/QC/哈希清单。

源码：[STS_thermal_exposure_pipeline.py](../../STS_thermal_exposure_pipeline.py)；566 行。

主要接口：[`ExposurePipelineConfig`](../../STS_thermal_exposure_pipeline.py#L33)、[`sha256_file`](../../STS_thermal_exposure_pipeline.py#L44)、[`read_table`](../../STS_thermal_exposure_pipeline.py#L55)、[`write_table`](../../STS_thermal_exposure_pipeline.py#L69)、[`relative_humidity_from_dewpoint`](../../STS_thermal_exposure_pipeline.py#L83)、[`temperature_humidity_index`](../../STS_thermal_exposure_pipeline.py#L92)。

代码内导入：[STS_thermal_stress_model.py](../../STS_thermal_stress_model.py)。

本目录调用/引用者：[STS_S0_01_prepare_thermal_exposure.py](../../STS_S0_01_prepare_thermal_exposure.py)。

<a id="file-sts-thermal-nutrient-emissions-py"></a>
### `STS_thermal_nutrient_emissions.py`

以统一台账和 Tier 2 参数计算能量、甲烷、氮磷摄入留存排泄与污染物排放，验证质量平衡，将清单映射回 GLE 标准过程。

源码：[STS_thermal_nutrient_emissions.py](../../STS_thermal_nutrient_emissions.py)；666 行。

主要接口：[`Tier2EmissionsResult`](../../STS_thermal_nutrient_emissions.py#L23)、[`load_tier2_parameters`](../../STS_thermal_nutrient_emissions.py#L71)、[`calculate_tier2_livestock_emissions`](../../STS_thermal_nutrient_emissions.py#L234)、[`tier2_inventory_to_gle_frames`](../../STS_thermal_nutrient_emissions.py#L618)。

代码内导入：[STS_thermal_stress_model.py](../../STS_thermal_stress_model.py)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)、[gle_emissions_complete.py](../../gle_emissions_complete.py)。

<a id="file-sts-thermal-response-evidence-py"></a>
### `STS_thermal_response_evidence.py`

校验证据数据，按物种/角色/生产系统拟合响应函数并做留出研究预测，输出运行时可加载的响应注册表及验证文件。

源码：[STS_thermal_response_evidence.py](../../STS_thermal_response_evidence.py)；252 行。

主要接口：[`EvidenceFitConfig`](../../STS_thermal_response_evidence.py#L36)、[`validate_evidence_table`](../../STS_thermal_response_evidence.py#L42)、[`build_response_registry_from_evidence`](../../STS_thermal_response_evidence.py#L142)、[`prepare_response_registry_files`](../../STS_thermal_response_evidence.py#L231)。

代码内导入：[STS_thermal_stress_model.py](../../STS_thermal_stress_model.py)。

本目录调用/引用者：[STS_S0_02_prepare_thermal_response_registry.py](../../STS_S0_02_prepare_thermal_response_registry.py)。

<a id="file-sts-thermal-stress-model-py"></a>
### `STS_thermal_stress_model.py`

STS 核心：严格加载暴露、响应/strain 注册表和商品映射，构造生理影响、适应措施和活动/饲料乘数，建立动物活动台账并输出影响/清单。

源码：[STS_thermal_stress_model.py](../../STS_thermal_stress_model.py)；2,483 行。

主要接口：[`ThermalStressSettings`](../../STS_thermal_stress_model.py#L156)、[`ThermalStressBundle`](../../STS_thermal_stress_model.py#L182)、[`build_thermal_stress_bundle`](../../STS_thermal_stress_model.py#L1746)、[`build_animal_activity_ledger`](../../STS_thermal_stress_model.py#L1885)、[`apply_thermal_adaptation`](../../STS_thermal_stress_model.py#L1396)、[`write_thermal_outputs`](../../STS_thermal_stress_model.py#L2397)。

本目录调用/引用者：[S4_0_main.py](../../S4_0_main.py)、[STS_thermal_exposure_pipeline.py](../../STS_thermal_exposure_pipeline.py)、[STS_thermal_nutrient_emissions.py](../../STS_thermal_nutrient_emissions.py)、[STS_thermal_response_evidence.py](../../STS_thermal_response_evidence.py)、[STS_thermal_uncertainty_validation.py](../../STS_thermal_uncertainty_validation.py)。

文件线索：`animal_activity_ledger.csv`；`thermal_adaptation_audit.csv`；`thermal_exposure_country_species_system.csv`；`thermal_gle_adjustment_audit.csv`；`thermal_impacts_by_commodity.csv`；`thermal_impacts_by_system.csv`；`thermal_impacts_model.csv`。

<a id="file-sts-thermal-uncertainty-validation-py"></a>
### `STS_thermal_uncertainty_validation.py`

构建多气候/响应及显式映射、EF、适应效率扰动的集合，多次调用 stress_model 形成影响样本并校验扰动实际生效；另提供统计汇总和观测误差指标。

源码：[STS_thermal_uncertainty_validation.py](../../STS_thermal_uncertainty_validation.py)；612 行。

主要接口：[`build_uncertainty_design`](../../STS_thermal_uncertainty_validation.py#L130)、[`run_thermal_bundle_ensemble`](../../STS_thermal_uncertainty_validation.py#L207)、[`summarize_ensemble`](../../STS_thermal_uncertainty_validation.py#L501)、[`validate_against_observations`](../../STS_thermal_uncertainty_validation.py#L531)、[`write_validation_report`](../../STS_thermal_uncertainty_validation.py#L578)。

代码内导入：[STS_thermal_stress_model.py](../../STS_thermal_stress_model.py)。

本目录调用/引用者：[STS_S0_05_validate_and_summarize.py](../../STS_S0_05_validate_and_summarize.py)。


<a id="group-5"></a>
## 5. S5 敏感性、策略和批次后处理

<a id="file-s5-0-1-diagnose-small-variable-importance-py"></a>
### `S5_0_1_diagnose_small_variable_importance.py`

检查 S5.0 某些变量的重要性偏小是否来自取值未激活、分布或多元回归归因，读取 samples/importance 和情景表，导出诊断工作簿。

源码：[S5_0_1_diagnose_small_variable_importance.py](../../S5_0_1_diagnose_small_variable_importance.py)；500 行。

主要接口：[`main`](../../S5_0_1_diagnose_small_variable_importance.py#L451)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`S5_0_1_small_variable_importance_diagnostics.xlsx`；`Scenario_config_new.xlsx`；`importance_by_variable.csv`；`samples.csv`。

<a id="file-s5-0-1-sensitivity-mc-levels-py"></a>
### `S5_0_1_sensitivity_mc_levels.py`

对情景变量进行 MC 抽样并逐样本运行完整 S4，按排放水平/目标生成变量重要性及样本统计；当前默认样本数为 2000。

源码：[S5_0_1_sensitivity_mc_levels.py](../../S5_0_1_sensitivity_mc_levels.py)；2,278 行。

主要接口：[`SampleResult`](../../S5_0_1_sensitivity_mc_levels.py#L75)、[`main`](../../S5_0_1_sensitivity_mc_levels.py#L1825)。

代码内导入：[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S4_0_main.py](../../S4_0_main.py)、[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S5_0_1_sensitivity_mc_levels_batches.py](../../S5_0_1_sensitivity_mc_levels_batches.py)、[S5_0_2_merge_sensitivity_mc_levels_batches.py](../../S5_0_2_merge_sensitivity_mc_levels_batches.py)。

本目录缺失的引用：`model_run_status.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`Demand_composition.xlsx`；`GCE_parameters.xlsx`；`GLE_parameters.xlsx`；`Soil_parameters.xlsx`；`commodity_balance_by_commodity.csv`；`dict_v3.xlsx`；`emissions_fast_global_detail.csv`。

<a id="file-s5-0-1-sensitivity-mc-levels-batches-py"></a>
### `S5_0_1_sensitivity_mc_levels_batches.py`

读取批次环境变量，将 S5.0 全体样本分配至一个批次并调用原运行器，保持抽样编号和输出布局一致。

源码：[S5_0_1_sensitivity_mc_levels_batches.py](../../S5_0_1_sensitivity_mc_levels_batches.py)；103 行。

主要接口：[`main`](../../S5_0_1_sensitivity_mc_levels_batches.py#L75)。

代码内导入：[S5_0_1_sensitivity_mc_levels.py](../../S5_0_1_sensitivity_mc_levels.py)。

<a id="file-s5-0-2-merge-sensitivity-mc-levels-batches-py"></a>
### `S5_0_2_merge_sensitivity_mc_levels_batches.py`

汇总 S5.0 批次结果，复用核心统计逻辑重建全样本重要性和摘要；不提供新的物理模型。

源码：[S5_0_2_merge_sensitivity_mc_levels_batches.py](../../S5_0_2_merge_sensitivity_mc_levels_batches.py)；144 行。

主要接口：[`main`](../../S5_0_2_merge_sensitivity_mc_levels_batches.py#L104)。

代码内导入：[S5_0_1_sensitivity_mc_levels.py](../../S5_0_1_sensitivity_mc_levels.py)、[config_paths.py](../../config_paths.py)。

<a id="file-s5-1-1-sensitivity-mc-variable-effect-py"></a>
### `S5_1_1_sensitivity_mc_variable_effect.py`

针对单产、EF、反刍份额等指定变量水平开展条件 MC，输出全链排放样本与分布；提供被多个 S5 共用的抽样、单位和边界处理函数。

源码：[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)；3,668 行。

主要接口：[`resolve_mc_effect_sheet`](../../S5_1_1_sensitivity_mc_variable_effect.py#L79)、[`main`](../../S5_1_1_sensitivity_mc_variable_effect.py#L3267)。

代码内导入：[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S3_6_scenarios.py](../../S3_6_scenarios.py)、[S4_0_main.py](../../S4_0_main.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[config_paths.py](../../config_paths.py)、[market_balance_diagnostics.py](../../market_balance_diagnostics.py)。

本目录调用/引用者：[S5_0_1_sensitivity_mc_levels.py](../../S5_0_1_sensitivity_mc_levels.py)、[S5_1_1_sensitivity_mc_variable_effect_batches.py](../../S5_1_1_sensitivity_mc_variable_effect_batches.py)、[S5_1_3_merge_variable_effect_batches.py](../../S5_1_3_merge_variable_effect_batches.py)、[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)、[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)。

本目录缺失的引用：`model_run_status.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`Demand_composition.xlsx`；`GCE_parameters.xlsx`；`GLE_parameters.xlsx`；`Soil_parameters.xlsx`；`commodity_balance_by_commodity.csv`；`emissions_fast_global_detail.csv`；`emissions_fast_summary.csv`。

<a id="file-s5-1-1-sensitivity-mc-variable-effect-batches-py"></a>
### `S5_1_1_sensitivity_mc_variable_effect_batches.py`

S5.1 条件 MC 的单批次包装，解析批号/总批数/续跑设置并调用主运行器。

源码：[S5_1_1_sensitivity_mc_variable_effect_batches.py](../../S5_1_1_sensitivity_mc_variable_effect_batches.py)；107 行。

主要接口：[`main`](../../S5_1_1_sensitivity_mc_variable_effect_batches.py#L78)。

代码内导入：[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)。

<a id="file-s5-1-2-rebuild-fig-effect-sensivity-data-py"></a>
### `S5_1_2_rebuild_fig_effect_sensivity_data.py`

从已有 S5.1 样本和运行排放重建 Fig5 samples、histogram、summary、targets 及审核表；不重新做全球情景求解。

源码：[S5_1_2_rebuild_fig_effect_sensivity_data.py](../../S5_1_2_rebuild_fig_effect_sensivity_data.py)；483 行。

主要接口：[`main`](../../S5_1_2_rebuild_fig_effect_sensivity_data.py#L274)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`emissions_fast_summary.csv`；`emissions_summary.xlsx`；`emissions_summary_By_Country.csv`；`emissions_summary_By_Country.xlsx`；`fig5_rebuild_audit.csv`；`histogram.csv`；`histogram_rebuilt_from_runs.csv`。

<a id="file-s5-1-3-merge-variable-effect-batches-py"></a>
### `S5_1_3_merge_variable_effect_batches.py`

验证并合并 S5.1 各批 samples、状态和元数据，重建分组结果及实验级成本汇总。

源码：[S5_1_3_merge_variable_effect_batches.py](../../S5_1_3_merge_variable_effect_batches.py)；485 行。

主要接口：[`main`](../../S5_1_3_merge_variable_effect_batches.py#L203)。

代码内导入：[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[config_paths.py](../../config_paths.py)。

文件线索：`run_meta.csv`；`run_status.csv`；`samples.csv`。

<a id="file-s5-3-1-forest-area-fixed-sensitivity-py"></a>
### `S5_3_1_forest_area_fixed_sensitivity.py`

固定单产、EF 与反刍上限，仅扫描森林目标，复用 S5.3 面板计算，输出森林单因素敏感性及全球分过程结果。

源码：[S5_3_1_forest_area_fixed_sensitivity.py](../../S5_3_1_forest_area_fixed_sensitivity.py)；105 行。

主要接口：[`parse_args`](../../S5_3_1_forest_area_fixed_sensitivity.py#L34)、[`main`](../../S5_3_1_forest_area_fixed_sensitivity.py#L77)。

代码内导入：[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)。

文件线索：`forest_area_fixed_global_emissions_detail.csv`；`forest_area_fixed_sensitivity.csv`。

<a id="file-s5-3-1-sensitivity-panel-yield-ef-py"></a>
### `S5_3_1_sensitivity_panel_yield_ef.py`

按单产×EF 网格及森林/反刍份额组合重复运行 S4，写面板长表、实现后营养/土地/排放指标和诊断，供等值线图。

源码：[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)；2,044 行。

主要接口：[`main`](../../S5_3_1_sensitivity_panel_yield_ef.py#L1344)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_6_scenarios.py](../../S3_6_scenarios.py)、[S4_0_main.py](../../S4_0_main.py)、[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[config_paths.py](../../config_paths.py)、[market_balance_diagnostics.py](../../market_balance_diagnostics.py)。

本目录调用/引用者：[S5_3_1_forest_area_fixed_sensitivity.py](../../S5_3_1_forest_area_fixed_sensitivity.py)、[S5_3_1_sensitivity_panel_yield_ef_batches.py](../../S5_3_1_sensitivity_panel_yield_ef_batches.py)、[S5_3_1_sensitivity_panel_yield_ef_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_v2.py)、[S5_3_3_merge_panel_yield_ef_batches.py](../../S5_3_3_merge_panel_yield_ef_batches.py)。

本目录缺失的引用：`model_run_status.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`DS/country_year_summary.csv`；`DS/luc_land_area_solver_period.csv`；`DS/nutrition_per_capita.csv`；`Emis/emissions_fast_global_detail.csv`；`commodity_balance_by_commodity.csv`；`country_year_summary.csv`；`crop_pasture_land_balance.csv`。

<a id="file-s5-3-1-sensitivity-panel-yield-ef-batches-py"></a>
### `S5_3_1_sensitivity_panel_yield_ef_batches.py`

按命令行/环境设置划分 S5.3 场景网格，运行一个批次并传递配置覆盖。

源码：[S5_3_1_sensitivity_panel_yield_ef_batches.py](../../S5_3_1_sensitivity_panel_yield_ef_batches.py)；156 行。

主要接口：[`main`](../../S5_3_1_sensitivity_panel_yield_ef_batches.py#L123)。

代码内导入：[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)。

本目录调用/引用者：[S5_3_1_sensitivity_panel_yield_ef_batches_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_batches_v2.py)。

<a id="file-s5-3-1-sensitivity-panel-yield-ef-batches-v2-py"></a>
### `S5_3_1_sensitivity_panel_yield_ef_batches_v2.py`

组合原版批次接口和 v2 面板设置/轴别名，执行 v2 的一个批次。

源码：[S5_3_1_sensitivity_panel_yield_ef_batches_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_batches_v2.py)；44 行。

主要接口：[`main`](../../S5_3_1_sensitivity_panel_yield_ef_batches_v2.py#L9)。

代码内导入：[S5_3_1_sensitivity_panel_yield_ef_batches.py](../../S5_3_1_sensitivity_panel_yield_ef_batches.py)、[S5_3_1_sensitivity_panel_yield_ef_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_v2.py)。

<a id="file-s5-3-1-sensitivity-panel-yield-ef-v2-py"></a>
### `S5_3_1_sensitivity_panel_yield_ef_v2.py`

面板实验的联动轴版本：E/L 横轴令 EF、肥料、作物土壤参数同向变化，粪便管理反向；L/A 纵轴令单产同向、饲料强度反向；复用原面板，但坐标语义不同。

源码：[S5_3_1_sensitivity_panel_yield_ef_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_v2.py)；372 行。

主要接口：[`apply_v2_axis_aliases`](../../S5_3_1_sensitivity_panel_yield_ef_v2.py#L228)、[`postprocess_v2_outputs`](../../S5_3_1_sensitivity_panel_yield_ef_v2.py#L318)、[`main`](../../S5_3_1_sensitivity_panel_yield_ef_v2.py#L339)。

代码内导入：[S3_6_scenarios.py](../../S3_6_scenarios.py)、[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)。

本目录调用/引用者：[S5_3_1_sensitivity_panel_yield_ef_batches_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_batches_v2.py)、[S5_3_2_panel_data_summary_v2.py](../../S5_3_2_panel_data_summary_v2.py)、[S5_3_3_merge_panel_yield_ef_batches_v2.py](../../S5_3_3_merge_panel_yield_ef_batches_v2.py)。

文件线索：`figure_panel_dataset_long.csv`；`figure_panel_global_emissions_detail_long.csv`；`run_meta.csv`。

<a id="file-s5-3-2-panel-data-summary-py"></a>
### `S5_3_2_panel_data_summary.py`

只读合并后的批次级面板表，检查和重建绘图字段、缺失点及全球排放明细，输出 plot_ready 和审核表，不复制运行目录。

源码：[S5_3_2_panel_data_summary.py](../../S5_3_2_panel_data_summary.py)；1,424 行。

主要接口：[`main`](../../S5_3_2_panel_data_summary.py#L1153)。

代码内导入：[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S5_3_2_panel_data_summary_v2.py](../../S5_3_2_panel_data_summary_v2.py)。

文件线索：`figure_panel_data_summary.csv`；`figure_panel_dataset_long.csv`；`figure_panel_dataset_long_plot_ready.csv`；`figure_panel_dataset_long_rebuilt.csv`；`figure_panel_global_emissions_detail_long.csv`；`figure_panel_global_emissions_detail_long_rebuilt.csv`；`figure_panel_missing_points_audit.csv`。

<a id="file-s5-3-2-panel-data-summary-v2-py"></a>
### `S5_3_2_panel_data_summary_v2.py`

将原面板汇总流程应用于 v2 输出和坐标语义，生成对应 v2 plot_ready 数据及缺失诊断。

源码：[S5_3_2_panel_data_summary_v2.py](../../S5_3_2_panel_data_summary_v2.py)；202 行。

主要接口：[`main`](../../S5_3_2_panel_data_summary_v2.py#L168)。

代码内导入：[S5_3_1_sensitivity_panel_yield_ef_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_v2.py)、[S5_3_2_panel_data_summary.py](../../S5_3_2_panel_data_summary.py)。

文件线索：`figure_panel_dataset_long.csv`；`figure_panel_dataset_long_plot_ready.csv`；`figure_panel_dataset_long_rebuilt.csv`；`figure_panel_global_emissions_detail_long.csv`；`figure_panel_global_emissions_detail_long_rebuilt.csv`；`figure_panel_missing_points_audit.csv`。

<a id="file-s5-3-3-merge-panel-yield-ef-batches-py"></a>
### `S5_3_3_merge_panel_yield_ef_batches.py`

严格验证批次覆盖、场景唯一性及状态后合并面板 CSV，写 batch_completion_audit 和汇总成本；保留各运行目录原位。

源码：[S5_3_3_merge_panel_yield_ef_batches.py](../../S5_3_3_merge_panel_yield_ef_batches.py)；729 行。

主要接口：[`main`](../../S5_3_3_merge_panel_yield_ef_batches.py#L432)。

代码内导入：[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)。

本目录调用/引用者：[S5_3_3_merge_panel_yield_ef_batches_v2.py](../../S5_3_3_merge_panel_yield_ef_batches_v2.py)。

文件线索：`bash submit_sbatch_S5_3_1_panel_yield_ef.sh`；`batch_completion_audit.csv`；`figure_panel_dataset_long.csv`；`figure_panel_global_emissions_detail_long.csv`；`run_meta.csv`。

<a id="file-s5-3-3-merge-panel-yield-ef-batches-v2-py"></a>
### `S5_3_3_merge_panel_yield_ef_batches_v2.py`

复用原面板合并器并切换 v2 运行模块/输出根，提供 v2 合并入口。

源码：[S5_3_3_merge_panel_yield_ef_batches_v2.py](../../S5_3_3_merge_panel_yield_ef_batches_v2.py)；47 行。

主要接口：[`main`](../../S5_3_3_merge_panel_yield_ef_batches_v2.py#L24)。

代码内导入：[S5_3_1_sensitivity_panel_yield_ef_v2.py](../../S5_3_1_sensitivity_panel_yield_ef_v2.py)、[S5_3_3_merge_panel_yield_ef_batches.py](../../S5_3_3_merge_panel_yield_ef_batches.py)。

文件线索：`bash submit_sbatch_S5_3_1_panel_yield_ef_v2.sh`。

<a id="file-s5-4-1-monte-carlo-full-variables-py"></a>
### `S5_4_1_monte_carlo_full_variables.py`

全变量 MC：复用 S5.1 抽样并逐样本运行完整 S4，记录成功/失败、抽样长表、快速排放、全球过程量、加权变量以及实际饮食和土地指标。

源码：[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)；2,698 行。

主要接口：[`main`](../../S5_4_1_monte_carlo_full_variables.py#L1825)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S4_0_main.py](../../S4_0_main.py)、[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[config_paths.py](../../config_paths.py)、[market_balance_diagnostics.py](../../market_balance_diagnostics.py)。

本目录调用/引用者：[S5_4_1_monte_carlo_full_variables_batches.py](../../S5_4_1_monte_carlo_full_variables_batches.py)、[S5_4_3_extreme_robustness_test.py](../../S5_4_3_extreme_robustness_test.py)、[S5_5_1_Region-Item-Process_Importance_Gen.py](../../S5_5_1_Region-Item-Process_Importance_Gen.py)、[S5_6_1_max_emission_reduction_potential.py](../../S5_6_1_max_emission_reduction_potential.py)、[S5_6_4_max_reduction_impend.py](../../S5_6_4_max_reduction_impend.py)、[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)。

本目录缺失的引用：`model_run_status.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`commodity_balance_by_commodity.csv`；`crop_pasture_land_balance.csv`；`emissions_fast_global_detail.csv`；`emissions_fast_summary.csv`；`emissions_summary_By_Country_Process_Item.csv`；`mc_draws_long.csv`；`mc_sample_status.csv`。

<a id="file-s5-4-1-monte-carlo-full-variables-batches-py"></a>
### `S5_4_1_monte_carlo_full_variables_batches.py`

将全变量 MC 样本确定性分批，支持批次、续跑和清理设置，调用 S5.4 主运行器。

源码：[S5_4_1_monte_carlo_full_variables_batches.py](../../S5_4_1_monte_carlo_full_variables_batches.py)；173 行。

主要接口：[`main`](../../S5_4_1_monte_carlo_full_variables_batches.py#L140)。

代码内导入：[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)。

<a id="file-s5-4-2-merge-batches-py"></a>
### `S5_4_2_merge_batches.py`

验证 S5.4 批次与样本来源，按有效运行键合并成功排放、变量、土地及饮食表并输出成本汇总，避免失败样本混入成功集合。

源码：[S5_4_2_merge_batches.py](../../S5_4_2_merge_batches.py)；592 行。

主要接口：[`main`](../../S5_4_2_merge_batches.py#L476)。

代码内导入：[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[config_paths.py](../../config_paths.py)。

文件线索：`mc_draws_long.csv`；`mc_sample_status.csv`；`mc_success_crop_pasture_land_balance.csv`；`mc_success_fast_summary.csv`；`mc_success_global_process_co2eq.csv`；`mc_success_realized_ruminant_share.csv`；`mc_success_weighted_elements.csv`。

<a id="file-s5-4-3-extreme-robustness-test-py"></a>
### `S5_4_3_extreme_robustness_test.py`

将 S5.4 的随机 U 矩阵替换为五个固定端点/压力场景，检查极端参数组合下的可行性和输出；保留的模型稳健性分析入口。

源码：[S5_4_3_extreme_robustness_test.py](../../S5_4_3_extreme_robustness_test.py)；343 行。

主要接口：[`build_extreme_unit_matrix`](../../S5_4_3_extreme_robustness_test.py#L117)、[`parse_args`](../../S5_4_3_extreme_robustness_test.py#L299)、[`main`](../../S5_4_3_extreme_robustness_test.py#L317)。

代码内导入：[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)、[config_paths.py](../../config_paths.py)。

文件线索：`extreme_draws_preview_long.csv`；`extreme_scenario_design.csv`；`extreme_scenario_status.csv`；`mc_sample_status.csv`。

<a id="file-s5-5-0-region-item-process-importance-extract-previous-py"></a>
### `S5_5_0_Region-Item-Process_Importance_extract_previous.py`

审核旧 S5.1/S5.3/S5.4 结果是否保留足够结构明细，从可用结果重建区域/商品/过程归因辅助表；不足时不能凭全局总量反推国家细节。

源码：[S5_5_0_Region-Item-Process_Importance_extract_previous.py](../../S5_5_0_Region-Item-Process_Importance_extract_previous.py)；1,378 行。

主要接口：[`build_region_item_process_importance`](../../S5_5_0_Region-Item-Process_Importance_extract_previous.py#L1263)、[`main`](../../S5_5_0_Region-Item-Process_Importance_extract_previous.py#L1371)。

代码内导入：[SP_M1a_Figure_pie_structure_pre.py](../../SP_M1a_Figure_pie_structure_pre.py)、[config_paths.py](../../config_paths.py)。

文件线索：`EmissionIntensity_Importance.xlsx`；`aggregated_scenario_emissions.csv`；`coverage_by_level.csv`；`emissions_summary_By_Country_Process_Item.csv`；`emissions_summary_By_Country_Process_Item.xlsx`；`failed_runs_audit.csv`；`figure_panel_dataset_long.csv`。

<a id="file-s5-5-1-region-item-process-importance-gen-py"></a>
### `S5_5_1_Region-Item-Process_Importance_Gen.py`

专门生成结构重要性数据：复用全变量 MC，但保留细分排放，按统一区域/商品/过程定义输出结构排放、总量、份额和分位数相关表。

源码：[S5_5_1_Region-Item-Process_Importance_Gen.py](../../S5_5_1_Region-Item-Process_Importance_Gen.py)；1,496 行。

主要接口：[`main`](../../S5_5_1_Region-Item-Process_Importance_Gen.py#L1474)。

代码内导入：[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[SP_M1a_Figure_pie_structure_pre.py](../../SP_M1a_Figure_pie_structure_pre.py)、[config_paths.py](../../config_paths.py)。

动态文件引用线索：[SP_M1a_Figure_pie_structure_pre.py](../../SP_M1a_Figure_pie_structure_pre.py)。

本目录调用/引用者：[S5_5_2_Region-Item-Process_Importance_Gen_batches.py](../../S5_5_2_Region-Item-Process_Importance_Gen_batches.py)、[S5_5_3_Region-Item-Process_Importance_merge_batches.py](../../S5_5_3_Region-Item-Process_Importance_merge_batches.py)、[SP_M4f_Figure_structure_importance_targetrange_v3.py](../../SP_M4f_Figure_structure_importance_targetrange_v3.py)。

文件线索：`emissions_summary_By_Country_Process_Item.csv`；`emissions_summary_By_Country_Process_Item.xlsx`；`item_allocation_diagnostics.csv`；`luc_item_allocation_diagnostics.csv`；`mc_sample_status.csv`；`mc_success_crop_pasture_land_balance.csv`；`mc_success_realized_ruminant_share.csv`。

<a id="file-s5-5-2-region-item-process-importance-gen-batches-py"></a>
### `S5_5_2_Region-Item-Process_Importance_Gen_batches.py`

通过动态加载处理带连字符的 S5.5 主脚本名，包装成一个集群批次，保持 MC 抽样与后处理一致。

源码：[S5_5_2_Region-Item-Process_Importance_Gen_batches.py](../../S5_5_2_Region-Item-Process_Importance_Gen_batches.py)；157 行。

主要接口：[`main`](../../S5_5_2_Region-Item-Process_Importance_Gen_batches.py#L133)。

动态文件引用线索：[S5_5_1_Region-Item-Process_Importance_Gen.py](../../S5_5_1_Region-Item-Process_Importance_Gen.py)。

<a id="file-s5-5-3-region-item-process-importance-merge-batches-py"></a>
### `S5_5_3_Region-Item-Process_Importance_merge_batches.py`

检查 S5.5 批次集合并从各批详细结果构建 merged_structure 聚合表，不复制原始运行输出树。

源码：[S5_5_3_Region-Item-Process_Importance_merge_batches.py](../../S5_5_3_Region-Item-Process_Importance_merge_batches.py)；114 行。

主要接口：[`main`](../../S5_5_3_Region-Item-Process_Importance_merge_batches.py#L92)。

动态文件引用线索：[S5_5_1_Region-Item-Process_Importance_Gen.py](../../S5_5_1_Region-Item-Process_Importance_Gen.py)。

<a id="file-s5-6-1-max-emission-reduction-potential-py"></a>
### `S5_6_1_max_emission_reduction_potential.py`

运行基准、全球全措施/单措施以及单国行动情景，计算相对基准的减排及已测试措施排名；端点由 CONFIG 指定，不是连续政策空间的全局最优证明。

源码：[S5_6_1_max_emission_reduction_potential.py](../../S5_6_1_max_emission_reduction_potential.py)；1,057 行。

主要接口：[`ScenarioPlan`](../../S5_6_1_max_emission_reduction_potential.py#L183)、[`parse_args`](../../S5_6_1_max_emission_reduction_potential.py#L918)、[`main`](../../S5_6_1_max_emission_reduction_potential.py#L985)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S4_0_main.py](../../S4_0_main.py)、[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S5_6_1_max_emission_reduction_potential_batches.py](../../S5_6_1_max_emission_reduction_potential_batches.py)、[S5_6_2_merge_batches.py](../../S5_6_2_merge_batches.py)、[S5_6_4_max_reduction_impend.py](../../S5_6_4_max_reduction_impend.py)、[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)、[S5_8_1_country_strategy_map_sensitivity.py](../../S5_8_1_country_strategy_map_sensitivity.py)。

本目录缺失的引用：`model_run_status.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`country_best_tested_strategy_long.csv`；`country_best_tested_strategy_summary.csv`；`country_max_strategy_long.csv`；`country_own_max_reduction_summary.csv`；`country_own_max_strategy_long.csv`；`country_reduction_under_global_strategy.csv`；`country_single_actor_potential.csv`。

<a id="file-s5-6-1-max-emission-reduction-potential-batches-py"></a>
### `S5_6_1_max_emission_reduction_potential_batches.py`

按国家子集分配 S5.6；第一批额外计算参考和全球场景，其他批运行分配的国家场景。

源码：[S5_6_1_max_emission_reduction_potential_batches.py](../../S5_6_1_max_emission_reduction_potential_batches.py)；262 行。

主要接口：[`main`](../../S5_6_1_max_emission_reduction_potential_batches.py#L233)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S5_6_1_max_emission_reduction_potential.py](../../S5_6_1_max_emission_reduction_potential.py)。

<a id="file-s5-6-2-merge-batches-py"></a>
### `S5_6_2_merge_batches.py`

合并 S5.6 设计和状态，以合并后的统一参考重算各国家/全球减排列，写 merged 结果和批次清单。

源码：[S5_6_2_merge_batches.py](../../S5_6_2_merge_batches.py)；301 行。

主要接口：[`main`](../../S5_6_2_merge_batches.py#L217)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S5_6_1_max_emission_reduction_potential.py](../../S5_6_1_max_emission_reduction_potential.py)。

文件线索：`batch_merge_manifest.csv`；`scenario_status.csv`；`strategy_design_long.csv`。

<a id="file-s5-6-4-max-reduction-impend-py"></a>
### `S5_6_4_max_reduction_impend.py`

从最强组合端点出发，按预定顺序逐步放松措施直至找到可行方案，输出首个可行点的参数、排放与成本；属于贪心可行性搜索。

源码：[S5_6_4_max_reduction_impend.py](../../S5_6_4_max_reduction_impend.py)；921 行。

主要接口：[`parse_args`](../../S5_6_4_max_reduction_impend.py#L737)、[`main`](../../S5_6_4_max_reduction_impend.py#L778)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S4_0_main.py](../../S4_0_main.py)、[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)、[S5_6_1_max_emission_reduction_potential.py](../../S5_6_1_max_emission_reduction_potential.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)。

文件线索：`cost_summary.csv`；`emissions_fast_global_detail.csv`；`first_feasible_cost_by_process.csv`；`first_feasible_cost_detail.csv`；`first_feasible_cost_summary.csv`；`first_feasible_effects_applied.csv`；`first_feasible_emissions_by_process.csv`。

<a id="file-s5-7-1-strategy-endpoint-rerun-max-reduction-potential-py"></a>
### `S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py`

用 S5_7_strategy_process_config.json 将措施映射为九类，重跑单措施和组合，计算归一化/精确 Shapley 贡献及 MACC；将物理措施种类和成本键分开。

源码：[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)；2,527 行。

主要接口：[`parse_args`](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py#L1302)、[`main`](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py#L2409)。

代码内导入：[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)、[S5_6_1_max_emission_reduction_potential.py](../../S5_6_1_max_emission_reduction_potential.py)、[config_paths.py](../../config_paths.py)、[cost_database_v2.py](../../cost_database_v2.py)。

本目录调用/引用者：[S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py)、[S5_7_2_strategy_endpoint_rerun_merge_batches.py](../../S5_7_2_strategy_endpoint_rerun_merge_batches.py)、[S5_7_3_strategy_macc_cdr_price.py](../../S5_7_3_strategy_macc_cdr_price.py)、[S5_8_1_country_strategy_map_sensitivity.py](../../S5_8_1_country_strategy_map_sensitivity.py)、[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py)、[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py)。

文件线索：`S5_7_strategy_process_config.json`；`batch_plan_manifest.csv`；`cost_summary.csv`；`food_mitigation_cost_database_v2.0.json`；`global_strategy_interaction_residual.csv`；`global_strategy_potential_normalized.csv`；`macc_generation_status.csv`。

<a id="file-s5-7-1-strategy-endpoint-rerun-max-reduction-potential-batches-py"></a>
### `S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py`

按策略组合场景计划分批，包含保证参考对齐的逻辑；九措施独特组合共 512 个，不按国家直接切分。

源码：[S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py)；260 行。

主要接口：[`main`](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py#L229)。

代码内导入：[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)。

<a id="file-s5-7-2-strategy-endpoint-rerun-merge-batches-py"></a>
### `S5_7_2_strategy_endpoint_rerun_merge_batches.py`

合并并去重 S5.7 场景、成本与来源，重建归一化贡献或 exact Shapley，输出 MACC 所需曲线和成本配置。

源码：[S5_7_2_strategy_endpoint_rerun_merge_batches.py](../../S5_7_2_strategy_endpoint_rerun_merge_batches.py)；518 行。

主要接口：[`run_merge`](../../S5_7_2_strategy_endpoint_rerun_merge_batches.py#L367)、[`main`](../../S5_7_2_strategy_endpoint_rerun_merge_batches.py#L512)。

代码内导入：[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)。

本目录调用/引用者：[S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py](../../S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py)。

文件线索：`batch_merge_manifest.csv`；`batch_plan_manifest.csv`；`cost_summary.csv`；`macc_singleton_cost_detail.csv`；`scenario_status.csv`；`strategy_design_long.csv`。

<a id="file-s5-7-3-strategy-macc-cdr-price-py"></a>
### `S5_7_3_strategy_macc_cdr_price.py`

读取 S5.7 每个成本水平的措施实施比例，重新运行组合并扫描/细化土地碳价，估计达到目标排放所需价格及剩余排放响应。

源码：[S5_7_3_strategy_macc_cdr_price.py](../../S5_7_3_strategy_macc_cdr_price.py)；619 行。

主要接口：[`parse_args`](../../S5_7_3_strategy_macc_cdr_price.py#L476)、[`main`](../../S5_7_3_strategy_macc_cdr_price.py#L517)。

代码内导入：[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)。

本目录调用/引用者：[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py)。

文件线索：`cdr_land_price_response.csv`；`cdr_required_land_carbon_price.csv`；`macc_strategy_cost_profiles.csv`；`macc_strategy_curve_totals.csv`；`macc_strategy_curve_with_cdr_price.csv`。

<a id="file-s5-8-1-country-strategy-map-sensitivity-py"></a>
### `S5_8_1_country_strategy_map_sensitivity.py`

对每国分别实施九类单措施并保持其他国家为参考，计算本国与全球效果以及可计价成本，输出主导措施/最低成本候选和完整长表。

源码：[S5_8_1_country_strategy_map_sensitivity.py](../../S5_8_1_country_strategy_map_sensitivity.py)；1,138 行。

主要接口：[`ensure_output_child`](../../S5_8_1_country_strategy_map_sensitivity.py#L61)、[`main`](../../S5_8_1_country_strategy_map_sensitivity.py#L991)。

代码内导入：[S5_6_1_max_emission_reduction_potential.py](../../S5_6_1_max_emission_reduction_potential.py)、[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)、[S5_8_3_prepare_country_dominant_mitigation_intervention.py](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)、[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S5_8_1_country_strategy_map_sensitivity_batches.py](../../S5_8_1_country_strategy_map_sensitivity_batches.py)、[S5_8_2_country_strategy_map_merge_batches.py](../../S5_8_2_country_strategy_map_merge_batches.py)。

文件线索：`Figure3.csv`；`cost_summary.csv`；`country_max_reduction_strategy.csv`；`country_min_unit_cost_strategy.csv`；`country_strategy_argmax.csv`；`country_strategy_argmin_cost.csv`；`country_strategy_long.csv`。

<a id="file-s5-8-1-country-strategy-map-sensitivity-batches-py"></a>
### `S5_8_1_country_strategy_map_sensitivity_batches.py`

按国家划分 S5.8，每批先跑一个独立详细参考，再跑分配国家的单措施，使批次可独立完成严格基准对齐。

源码：[S5_8_1_country_strategy_map_sensitivity_batches.py](../../S5_8_1_country_strategy_map_sensitivity_batches.py)；239 行。

主要接口：[`main`](../../S5_8_1_country_strategy_map_sensitivity_batches.py#L213)。

代码内导入：[S5_8_1_country_strategy_map_sensitivity.py](../../S5_8_1_country_strategy_map_sensitivity.py)。

<a id="file-s5-8-2-country-strategy-map-merge-batches-py"></a>
### `S5_8_2_country_strategy_map_merge_batches.py`

验证国家×措施覆盖、状态和各批参考一致性，合并长表和排名结果，并列出无可用策略的国家。

源码：[S5_8_2_country_strategy_map_merge_batches.py](../../S5_8_2_country_strategy_map_merge_batches.py)；700 行。

主要接口：[`main`](../../S5_8_2_country_strategy_map_merge_batches.py#L373)。

代码内导入：[S5_8_1_country_strategy_map_sensitivity.py](../../S5_8_1_country_strategy_map_sensitivity.py)、[S5_8_3_prepare_country_dominant_mitigation_intervention.py](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py)、[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)。

文件线索：`Figure3.csv`；`batch_merge_manifest.csv`；`countries_without_selected_strategy.csv`；`country_max_reduction_strategy.csv`；`country_min_unit_cost_strategy.csv`；`country_strategy_argmax.csv`；`country_strategy_argmin_cost.csv`。

<a id="file-s5-8-3-prepare-country-dominant-mitigation-intervention-py"></a>
### `S5_8_3_prepare_country_dominant_mitigation_intervention.py`

将 S5.8 完整长表转换为 Figure 3d 可追溯数据：按本国减排等选定指标排序、处理并列/近并列、检查覆盖，输出标准类别表和质量报告。

源码：[S5_8_3_prepare_country_dominant_mitigation_intervention.py](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py)；974 行。

主要接口：[`Figure3dSettings`](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py#L102)、[`ensure_output_child`](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py#L148)、[`rank_country_interventions`](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py#L271)、[`build_validation_table`](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py#L508)、[`write_figure3d_outputs`](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py#L692)、[`main`](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py#L923)。

代码内导入：[SP_M3d_Figure_country_dominant_mitigation_intervention.py](../../SP_M3d_Figure_country_dominant_mitigation_intervention.py)。

本目录调用/引用者：[S5_8_1_country_strategy_map_sensitivity.py](../../S5_8_1_country_strategy_map_sensitivity.py)、[S5_8_2_country_strategy_map_merge_batches.py](../../S5_8_2_country_strategy_map_merge_batches.py)、[SP_M3d_Figure_country_dominant_mitigation_intervention.py](../../SP_M3d_Figure_country_dominant_mitigation_intervention.py)。

文件线索：`Figure3d_country_dominant_intervention_source_data.xlsx`；`country_strategy_long.csv`；`figure3d_category_summary.csv`；`figure3d_country_dominant_intervention.csv`；`figure3d_country_strategy_ranked.csv`；`figure3d_data_quality.csv`；`figure3d_manifest.json`。

<a id="file-s5-9-1-bioenergy-scenario-marginal-abatement-cost-curves-py"></a>
### `S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py`

协调低/中/高生物能源的 S5.7 归因及 MACC，提供 preflight/quick/exact；校验成本数据库版本/哈希、物理可行性和输出位置，生成三面板曲线及图。

源码：[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py)；992 行。

主要接口：[`PanelCase`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py#L78)、[`resolve_output_root`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py#L126)、[`parse_cases`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py#L138)、[`build_arg_parser`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py#L796)、[`run_full_chain`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py#L828)、[`main`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py#L986)。

代码内导入：[S0_53_prepare_bioenergy_scenarios.py](../../S0_53_prepare_bioenergy_scenarios.py)、[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)、[S5_7_3_strategy_macc_cdr_price.py](../../S5_7_3_strategy_macc_cdr_price.py)、[ST_bioenergy_full_run_smoke.py](../../ST_bioenergy_full_run_smoke.py)。

动态文件引用线索：[SP_M3a_Figure_macc_stock_v3.1.py](../../SP_M3a_Figure_macc_stock_v3.1.py)。

本目录调用/引用者：[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py)、[S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py](../../S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py)。

文件线索：`_v2.xlsx`；`bioenergy_feedstock_use.csv`；`bioenergy_postsolve_assessment.csv`；`bioenergy_scenario_allocation_audit.csv`；`bioenergy_scenario_global_targets.csv`；`cdr_land_price_response.csv`；`cdr_required_land_carbon_price.csv`。

<a id="file-s5-9-1-bioenergy-scenario-marginal-abatement-cost-curves-batches-py"></a>
### `S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py`

在每个生物能源面板内执行同一 S5.7 批号，按计划配套本批参考和情景；持久结果必须位于 Code/output 子目录。

源码：[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py)；302 行。

主要接口：[`BatchSettings`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py#L39)、[`build_arg_parser`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py#L93)、[`resolve_settings`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py#L113)、[`run_batch`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py#L226)、[`main`](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py#L284)。

代码内导入：[S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py](../../S5_7_1_strategy_endpoint_rerun_max_reduction_potential.py)、[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py)。

本目录调用/引用者：[S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py](../../S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py)。

文件线索：`batch_plan_manifest.csv`；`scenario_status.csv`。

<a id="file-s5-9-2-bioenergy-scenario-marginal-abatement-cost-curves-merge-batches-py"></a>
### `S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py`

逐生物能源面板复用 S5.7 严格合并/成本来源检查，再合并三面板工作簿并重绘 PNG/SVG。

源码：[S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py](../../S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py)；345 行。

主要接口：[`build_arg_parser`](../../S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py#L48)、[`run_merge`](../../S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py#L207)、[`main`](../../S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py#L339)。

代码内导入：[S5_7_2_strategy_endpoint_rerun_merge_batches.py](../../S5_7_2_strategy_endpoint_rerun_merge_batches.py)、[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py)、[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py)。

文件线索：`batch_merge_manifest.json`。

<a id="file-s5-cost-summary-outputs-py"></a>
### `S5_cost_summary_outputs.py`

收集各次运行国家/全球措施成本，计算实验级汇总及未计价/缺失审计；被 S5 运行器和合并器共用。

源码：[S5_cost_summary_outputs.py](../../S5_cost_summary_outputs.py)；313 行。

主要接口：[`write_sensitivity_cost_summaries`](../../S5_cost_summary_outputs.py#L181)。

代码内导入：[S4_1_results.py](../../S4_1_results.py)。

本目录调用/引用者：[S5_0_1_sensitivity_mc_levels.py](../../S5_0_1_sensitivity_mc_levels.py)、[S5_1_1_sensitivity_mc_variable_effect.py](../../S5_1_1_sensitivity_mc_variable_effect.py)、[S5_1_3_merge_variable_effect_batches.py](../../S5_1_3_merge_variable_effect_batches.py)、[S5_3_1_sensitivity_panel_yield_ef.py](../../S5_3_1_sensitivity_panel_yield_ef.py)、[S5_3_3_merge_panel_yield_ef_batches.py](../../S5_3_3_merge_panel_yield_ef_batches.py)、[S5_4_1_monte_carlo_full_variables.py](../../S5_4_1_monte_carlo_full_variables.py)；另 7 个引用者。

文件线索：`cost_summary.csv`；`sensitivity_cost_summary_audit.csv`；`sensitivity_cost_summary_by_country_measure.csv`；`sensitivity_cost_summary_by_global_measure.csv`。


<a id="group-6"></a>
## 6. SP 论文图及配套数据准备

<a id="file-sp-m1a-figure-pie-structure-plot-py"></a>
### `SP_M1a_Figure_pie_structure_plot.py`

读取 2020 结构工作簿，绘制各类排放结构饼图/构成图并导出 PNG/SVG，是基础绘图版本。

源码：[SP_M1a_Figure_pie_structure_plot.py](../../SP_M1a_Figure_pie_structure_plot.py)；296 行。

主要接口：[`save_process_legend_svg`](../../SP_M1a_Figure_pie_structure_plot.py#L203)、[`plot_y2020_emis_structure`](../../SP_M1a_Figure_pie_structure_plot.py#L225)、[`main`](../../SP_M1a_Figure_pie_structure_plot.py#L287)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Y2020_Emis_structure_summary.xlsx`。

<a id="file-sp-m1a-figure-pie-structure-plot-v2-1-py"></a>
### `SP_M1a_Figure_pie_structure_plot_v2.1.py`

复用 v2 绘图实现并读取 v2 结构预处理结果，形成特定布局/配色版本；文件名含点号，其他脚本常通过 runpy 加载。

源码：[SP_M1a_Figure_pie_structure_plot_v2.1.py](../../SP_M1a_Figure_pie_structure_plot_v2.1.py)；198 行。

主要接口：[`plot_y2020_emis_structure_v2_1`](../../SP_M1a_Figure_pie_structure_plot_v2.1.py#L141)、[`main`](../../SP_M1a_Figure_pie_structure_plot_v2.1.py#L191)。

代码内导入：[SP_M1a_Figure_pie_structure_plot_v2.py](../../SP_M1a_Figure_pie_structure_plot_v2.py)。

本目录调用/引用者：[SP_M4f_Figure_structure_importance_targetrange_v2.py](../../SP_M4f_Figure_structure_importance_targetrange_v2.py)、[SP_SI3_Figure_emis_reduction_disaggregate.py](../../SP_SI3_Figure_emis_reduction_disaggregate.py)、[SP_SI4_Figure_emission_per_kcal_item.py](../../SP_SI4_Figure_emission_per_kcal_item.py)。

文件线索：`Y2020_Emis_structure_summary_v2.xlsx`。

<a id="file-sp-m1a-figure-pie-structure-plot-v2-py"></a>
### `SP_M1a_Figure_pie_structure_plot_v2.py`

2020 结构图的另一布局和配色实现，同时提供后续绘图复用的配置/绘制函数。

源码：[SP_M1a_Figure_pie_structure_plot_v2.py](../../SP_M1a_Figure_pie_structure_plot_v2.py)；476 行。

主要接口：[`plot_y2020_emis_structure_v2`](../../SP_M1a_Figure_pie_structure_plot_v2.py#L423)、[`main`](../../SP_M1a_Figure_pie_structure_plot_v2.py#L469)。

代码内导入：[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[SP_M1a_Figure_pie_structure_plot_v2.1.py](../../SP_M1a_Figure_pie_structure_plot_v2.1.py)、[SP_SI3_Figure_emis_reduction_disaggregate.py](../../SP_SI3_Figure_emis_reduction_disaggregate.py)、[SP_SI4_Figure_emission_per_kcal_item.py](../../SP_SI4_Figure_emission_per_kcal_item.py)。

文件线索：`Y2020_Emis_structure_summary.xlsx`。

<a id="file-sp-m1a-figure-pie-structure-pre-py"></a>
### `SP_M1a_Figure_pie_structure_pre.py`

将国家—商品—过程历史排放映射到图用区域/商品/过程分类，生成 Y2020_Emis_structure_summary.xlsx，统一多张结构图的分类。

源码：[SP_M1a_Figure_pie_structure_pre.py](../../SP_M1a_Figure_pie_structure_pre.py)；462 行。

主要接口：[`build_y2020_emis_structure_summary`](../../SP_M1a_Figure_pie_structure_pre.py#L434)、[`main`](../../SP_M1a_Figure_pie_structure_pre.py#L456)。

代码内导入：[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S0_49_emission_result_summary.py](../../S0_49_emission_result_summary.py)、[S5_5_0_Region-Item-Process_Importance_extract_previous.py](../../S5_5_0_Region-Item-Process_Importance_extract_previous.py)、[S5_5_1_Region-Item-Process_Importance_Gen.py](../../S5_5_1_Region-Item-Process_Importance_Gen.py)、[SP_M1a_Figure_pie_structure_pre_v2.py](../../SP_M1a_Figure_pie_structure_pre_v2.py)。

文件线索：`Emission_history_1961-2020_summary.xlsx`；`Y2020_Emis_structure_summary.xlsx`；`dict_v3.xlsx`；`emissions_summary_By_Country_Process_Item.csv`；`emissions_summary_By_Country_Process_Item.xlsx`。

<a id="file-sp-m1a-figure-pie-structure-pre-v2-py"></a>
### `SP_M1a_Figure_pie_structure_pre_v2.py`

复用原结构预处理并调整森林净过程等聚合表达，输出 Y2020_Emis_structure_summary_v2.xlsx，供对应布局使用。

源码：[SP_M1a_Figure_pie_structure_pre_v2.py](../../SP_M1a_Figure_pie_structure_pre_v2.py)；52 行。

主要接口：[`build_y2020_emis_structure_summary_v2`](../../SP_M1a_Figure_pie_structure_pre_v2.py#L23)、[`main`](../../SP_M1a_Figure_pie_structure_pre_v2.py#L46)。

代码内导入：[SP_M1a_Figure_pie_structure_pre.py](../../SP_M1a_Figure_pie_structure_pre.py)。

文件线索：`Y2020_Emis_structure_summary_v2.xlsx`。

<a id="file-sp-m1asi-figure-bar2-structure-plot-py"></a>
### `SP_M1aSI_Figure_bar2_structure_plot.py`

历史结构柱图的第二布局版本；与上一文件一样存在旧名称配色/过程模块的导入缺口。

源码：[SP_M1aSI_Figure_bar2_structure_plot.py](../../SP_M1aSI_Figure_bar2_structure_plot.py)；263 行。

主要接口：[`plot_y2020_emis_structure_bar2`](../../SP_M1aSI_Figure_bar2_structure_plot.py#L182)、[`main`](../../SP_M1aSI_Figure_bar2_structure_plot.py#L256)。

代码内导入：[config_paths.py](../../config_paths.py)。

本目录缺失的引用：`SP1_8_2_Figure_pie_structure_plot.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`Y2020_Emis_structure_summary.xlsx`。

<a id="file-sp-m1asi-figure-bar-structure-plot-py"></a>
### `SP_M1aSI_Figure_bar_structure_plot.py`

将历史结构汇总表绘制为补充柱状图；仍从当前目录缺失的旧名 SP1_8_2_Figure_pie_structure_plot 导入过程/配色常量。

源码：[SP_M1aSI_Figure_bar_structure_plot.py](../../SP_M1aSI_Figure_bar_structure_plot.py)；218 行。

主要接口：[`plot_y2020_emis_structure_bar`](../../SP_M1aSI_Figure_bar_structure_plot.py#L164)、[`main`](../../SP_M1aSI_Figure_bar_structure_plot.py#L211)。

代码内导入：[config_paths.py](../../config_paths.py)。

本目录缺失的引用：`SP1_8_2_Figure_pie_structure_plot.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`Y2020_Emis_structure_summary.xlsx`。

<a id="file-sp-m1b-figure-ar6-scenario-plot-py"></a>
### `SP_M1b_Figure_AR6_scenario_plot.py`

读取协调后的 AR6 统计表绘制情景比较面板；脚本/输出保留历史 Figure6 编号。

源码：[SP_M1b_Figure_AR6_scenario_plot.py](../../SP_M1b_Figure_AR6_scenario_plot.py)；440 行。

主要接口：[`main`](../../SP_M1b_Figure_AR6_scenario_plot.py#L424)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`AR6_scenario_prepared_harmonization.xlsx`。

<a id="file-sp-m1b-figure-ar6-scenario-plot-2-py"></a>
### `SP_M1b_Figure_AR6_scenario_plot_2.py`

以 AR6 的 summary_amount 绝对量表比较 1.5D/2D，为不同变量分别输出图。

源码：[SP_M1b_Figure_AR6_scenario_plot_2.py](../../SP_M1b_Figure_AR6_scenario_plot_2.py)；318 行。

主要接口：[`main`](../../SP_M1b_Figure_AR6_scenario_plot_2.py#L264)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`AR6_scenario_prepared_harmonization.xlsx`。

<a id="file-sp-m1b-figure-ar6-scenario-plot-v2-py"></a>
### `SP_M1b_Figure_AR6_scenario_plot_v2.py`

将 1.5D 和 2D 的 AR6 汇总置于同组面板，输出组合版 PNG/SVG。

源码：[SP_M1b_Figure_AR6_scenario_plot_v2.py](../../SP_M1b_Figure_AR6_scenario_plot_v2.py)；526 行。

主要接口：[`main`](../../SP_M1b_Figure_AR6_scenario_plot_v2.py#L510)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`AR6_scenario_prepared_harmonization.xlsx`；`Figure6_AR6_summary_v2.png`；`Figure6_AR6_summary_v2.svg`。

<a id="file-sp-m1b-figure-ar6-scenario-prep-py"></a>
### `SP_M1b_Figure_AR6_scenario_prep.py`

整理 AR6 情景分组、相对基准比例、分位数和绝对量统计，准备温控情景比较工作簿。

源码：[SP_M1b_Figure_AR6_scenario_prep.py](../../SP_M1b_Figure_AR6_scenario_prep.py)；420 行。

主要接口：[`main`](../../SP_M1b_Figure_AR6_scenario_prep.py#L362)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`AR6_scenario.xlsx`；`AR6_scenario_prepared_harmonization.xlsx`；`AR6_scenarios.xlsx`。

<a id="file-sp-m1b-figure-sci-scenario-plot-v2-py"></a>
### `SP_M1b_Figure_SCI_scenario_plot_v2.py`

绘制 SCI 温控组的比例/绝对量对比及组合主图，读取对应协调后的汇总 sheet。

源码：[SP_M1b_Figure_SCI_scenario_plot_v2.py](../../SP_M1b_Figure_SCI_scenario_plot_v2.py)；999 行。

主要接口：[`main`](../../SP_M1b_Figure_SCI_scenario_plot_v2.py#L928)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure6_SCI_summary_main_combined.png`；`Figure6_SCI_summary_main_combined.svg`；`SCI_Database.xlsx`；`SCI_Database_harmonization.xlsx`。

<a id="file-sp-m1b-figure-sci-scenario-prep-py"></a>
### `SP_M1b_Figure_SCI_scenario_prep.py`

读取 SCI 协调工作簿并生成/更新比例、汇总和绝对量统计 sheet，供 SCI 情景对比图。

源码：[SP_M1b_Figure_SCI_scenario_prep.py](../../SP_M1b_Figure_SCI_scenario_prep.py)；536 行。

主要接口：[`main`](../../SP_M1b_Figure_SCI_scenario_prep.py#L482)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`SCI_Database.xlsx`；`SCI_Database_harmonization.xlsx`。

<a id="file-sp-m2-figure-contour-py"></a>
### `SP_M2_Figure_contour.py`

从 S5.3 plot_ready/rebuilt/原始长表按优先级读取面板，绘制 AFOLU 等值线/热图，导出实际绘图数据与诊断。

源码：[SP_M2_Figure_contour.py](../../SP_M2_Figure_contour.py)；1,830 行。

主要接口：[`main`](../../SP_M2_Figure_contour.py#L1737)。

代码内导入：[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[SP_M2_Figure_contour_v2.py](../../SP_M2_Figure_contour_v2.py)。

文件线索：`Figure1_AFOLU_contour_diagnostics.csv`；`Figure1_AFOLU_contour_plot_data.csv`；`_base.png`；`_base.svg`；`_combined.svg`；`_legend.svg`；`_target_lines.svg`。

<a id="file-sp-m2-figure-contour-v2-py"></a>
### `SP_M2_Figure_contour_v2.py`

用面板实现后的 P、A/P、L/A、LUC/L 和农业排放/A 因子构造 PALE 分解视角图，不能将其横纵轴直接视作原版单产/EF 参数轴。

源码：[SP_M2_Figure_contour_v2.py](../../SP_M2_Figure_contour_v2.py)；441 行。

主要接口：[`plot_pale_figure`](../../SP_M2_Figure_contour_v2.py#L273)、[`main`](../../SP_M2_Figure_contour_v2.py#L416)。

代码内导入：[SP_M2_Figure_contour.py](../../SP_M2_Figure_contour.py)、[config_paths.py](../../config_paths.py)。

文件线索：`_plot_data.csv`；`_summary.csv`；`figure_panel_dataset_long.csv`；`figure_panel_dataset_long_plot_ready.csv`；`figure_panel_dataset_long_rebuilt.csv`。

<a id="file-sp-m3a-figure-macc-stock-py"></a>
### `SP_M3a_Figure_macc_stock.py`

读取旧 global_macc 工作表绘制剩余排放堆叠/MACC 基础图，输出保留 Figure4 命名。

源码：[SP_M3a_Figure_macc_stock.py](../../SP_M3a_Figure_macc_stock.py)；165 行。

主要接口：[`main`](../../SP_M3a_Figure_macc_stock.py#L85)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure4.xlsx`；`Figure4_global_macc.png`；`Figure4_global_macc.svg`。

<a id="file-sp-m3a-figure-macc-stock-v2-py"></a>
### `SP_M3a_Figure_macc_stock_v2.py`

旧 global_macc 图的第二布局版本，输入契约仍为单工作表，区别于三生物能源面板版本。

源码：[SP_M3a_Figure_macc_stock_v2.py](../../SP_M3a_Figure_macc_stock_v2.py)；200 行。

主要接口：[`main`](../../SP_M3a_Figure_macc_stock_v2.py#L107)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure4.xlsx`；`Figure4_global_macc.png`；`Figure4_global_macc.svg`。

<a id="file-sp-m3a-figure-macc-stock-v3-1-py"></a>
### `SP_M3a_Figure_macc_stock_v3.1.py`

三生物能源面板的当前工作流绘图入口，支持指定输入工作簿和输出路径，被 S5.9 调用生成 Figure 3a–c 对应图。

源码：[SP_M3a_Figure_macc_stock_v3.1.py](../../SP_M3a_Figure_macc_stock_v3.1.py)；325 行。

主要接口：[`main`](../../SP_M3a_Figure_macc_stock_v3.1.py#L264)。

代码内导入：[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py)、[SP_M4f_Figure_structure_importance_targetrange_v2.py](../../SP_M4f_Figure_structure_importance_targetrange_v2.py)。

文件线索：`Figure4_v2.xlsx`。

<a id="file-sp-m3a-figure-macc-stock-v3-py"></a>
### `SP_M3a_Figure_macc_stock_v3.py`

读取 low_Bio、medium_Bio、high_Bio 工作表，绘制三生物能源情景 MACC/剩余排放堆叠图。

源码：[SP_M3a_Figure_macc_stock_v3.py](../../SP_M3a_Figure_macc_stock_v3.py)；249 行。

主要接口：[`main`](../../SP_M3a_Figure_macc_stock_v3.py#L199)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure4_global_macc_v3.png`；`Figure4_global_macc_v3.svg`；`Figure4_v2.xlsx`。

<a id="file-sp-m3b-figure-map-reduction-cost-potential-py"></a>
### `SP_M3b_Figure_map_reduction_cost_potential.py`

旧过程主导减排/成本地图兼容绘图器，读取 Figure3 工作簿/CSV；当前 Figure 3d 的定义由 SP_M3d 实现。

源码：[SP_M3b_Figure_map_reduction_cost_potential.py](../../SP_M3b_Figure_map_reduction_cost_potential.py)；259 行。

主要接口：[`main`](../../SP_M3b_Figure_map_reduction_cost_potential.py#L211)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure3.csv`；`Figure3.xlsx`；`Figure3_legend.svg`；`Figure3_missing_countries.txt`；`_map.png`；`dict_v3.xlsx`。

<a id="file-sp-m3b-figure-map-reduction-cost-potential-v2-1-py"></a>
### `SP_M3b_Figure_map_reduction_cost_potential_v2.1.py`

旧地图兼容增强版，支持显式输入及缺失填充控制；不能替代 Figure 3d 标准化九干预排名定义。

源码：[SP_M3b_Figure_map_reduction_cost_potential_v2.1.py](../../SP_M3b_Figure_map_reduction_cost_potential_v2.1.py)；318 行。

主要接口：[`main`](../../SP_M3b_Figure_map_reduction_cost_potential_v2.1.py#L260)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure3.csv`；`Figure3.xlsx`；`Figure3_legend_v2.1.svg`；`Figure3_missing_countries_v2.1.txt`；`_map2.1.png`；`dict_v3.xlsx`。

<a id="file-sp-m3b-figure-map-reduction-cost-potential-v2-py"></a>
### `SP_M3b_Figure_map_reduction_cost_potential_v2.py`

旧过程主导地图的 v2 布局，保留历史数据格式和独立图例导出。

源码：[SP_M3b_Figure_map_reduction_cost_potential_v2.py](../../SP_M3b_Figure_map_reduction_cost_potential_v2.py)；268 行。

主要接口：[`main`](../../SP_M3b_Figure_map_reduction_cost_potential_v2.py#L220)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure3.csv`；`Figure3.xlsx`；`Figure3_legend.svg`；`Figure3_missing_countries.txt`；`_map2.png`；`dict_v3.xlsx`。

<a id="file-sp-m3d-figure-country-dominant-mitigation-intervention-py"></a>
### `SP_M3d_Figure_country_dominant_mitigation_intervention.py`

读取 S5.8.3 标准化国家主导干预表绘制 Figure 3d；缺失排名/几何保持灰色并输出匹配审核和图清单。

源码：[SP_M3d_Figure_country_dominant_mitigation_intervention.py](../../SP_M3d_Figure_country_dominant_mitigation_intervention.py)；481 行。

主要接口：[`prepare_geometry_join`](../../SP_M3d_Figure_country_dominant_mitigation_intervention.py#L154)、[`plot_figure3d`](../../SP_M3d_Figure_country_dominant_mitigation_intervention.py#L307)、[`main`](../../SP_M3d_Figure_country_dominant_mitigation_intervention.py#L420)。

代码内导入：[S5_8_3_prepare_country_dominant_mitigation_intervention.py](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py)、[config_paths.py](../../config_paths.py)。

本目录调用/引用者：[S5_8_3_prepare_country_dominant_mitigation_intervention.py](../../S5_8_3_prepare_country_dominant_mitigation_intervention.py)。

文件线索：`dict_v3.xlsx`；`figure3d_country_dominant_intervention.csv`；`figure3d_geometry_join_audit.csv`；`figure3d_plot_manifest.json`。

<a id="file-sp-m4a-figure-sensitivity-stock-py"></a>
### `SP_M4a_Figure_sensitivity_stock.py`

从 S5.0 重要性表重建图用工作簿并绘制策略重要性堆叠图；输出历史名 Figure2，与现稿编号需区分。

源码：[SP_M4a_Figure_sensitivity_stock.py](../../SP_M4a_Figure_sensitivity_stock.py)；449 行。

主要接口：[`main`](../../SP_M4a_Figure_sensitivity_stock.py#L430)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure2_sensitivity_stack_v3.png`；`Figure2_sensitivity_stack_v3.svg`；`Figure2_v3.xlsx`；`importance_by_variable.csv`；`importance_detail.csv`；`run_meta.csv`；`samples.csv`。

<a id="file-sp-m4b-figure-yield-ef-effect-line-py"></a>
### `SP_M4b_Figure_yield_ef_effect_line.py`

从早期 Fig5 samples/histogram/targets 绘制单产和 EF 敏感性曲线，适配 S5.1 旧数据链。

源码：[SP_M4b_Figure_yield_ef_effect_line.py](../../SP_M4b_Figure_yield_ef_effect_line.py)；198 行。

主要接口：[`main`](../../SP_M4b_Figure_yield_ef_effect_line.py#L155)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure5_yield_ef_effect_line.png`；`Figure5_yield_ef_effect_line.svg`；`histogram.csv`；`samples.csv`；`targets.csv`。

<a id="file-sp-m4b-figure-yield-ef-effect-line-targetrange-py"></a>
### `SP_M4b_Figure_yield_ef_effect_line_targetrange.py`

从 S5.4 合并成功样本构造目标排放区间对应的变量面板，输出面板样本、直方图和均值等派生数据。

源码：[SP_M4b_Figure_yield_ef_effect_line_targetrange.py](../../SP_M4b_Figure_yield_ef_effect_line_targetrange.py)；794 行。

主要接口：[`main`](../../SP_M4b_Figure_yield_ef_effect_line_targetrange.py#L732)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`emission_means_v3.csv`；`histogram_v3.csv`；`mc_draws_long.csv`；`mc_sample_status.csv`；`mc_success_fast_summary.csv`；`mc_success_realized_ruminant_share.csv`；`mc_success_weighted_elements.csv`。

<a id="file-sp-m4b-figure-yield-ef-effect-line-targetrange-v2-py"></a>
### `SP_M4b_Figure_yield_ef_effect_line_targetrange_v2.py`

当前四分位分布入口：按实现后的单产、生产 EF 强度、反刍摄入和土地强度排序分组；输出绘图样本、当前基准值和强度审计，支撑 Figure 4e–h。

源码：[SP_M4b_Figure_yield_ef_effect_line_targetrange_v2.py](../../SP_M4b_Figure_yield_ef_effect_line_targetrange_v2.py)；2,817 行。

主要接口：[`main`](../../SP_M4b_Figure_yield_ef_effect_line_targetrange_v2.py#L2668)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Nutrition_profile_recalculated_fromD0_food_demand.xlsx`；`current_metrics_2020_v2.csv`；`dict_v3.xlsx`；`ef_production_intensity_audit_v2.csv`；`emissions_summary_By_Country_Process_Item.csv`；`histogram_quartile_v2.csv`；`mc_draws_long.csv`。

<a id="file-sp-m4b-figure-yield-ef-effect-line-targetval-py"></a>
### `SP_M4b_Figure_yield_ef_effect_line_targetval.py`

按指定目标值绘制单产、EF 和反刍摄入的敏感性分布/曲线，读取 S5.1 或 Fig5 汇总。

源码：[SP_M4b_Figure_yield_ef_effect_line_targetval.py](../../SP_M4b_Figure_yield_ef_effect_line_targetval.py)；537 行。

主要接口：[`main`](../../SP_M4b_Figure_yield_ef_effect_line_targetval.py#L488)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`_effect_line_v2.png`；`_effect_line_v2.svg`；`histogram.csv`；`samples.csv`；`targets.csv`。

<a id="file-sp-m4e-figure-sensitivity-item-region-process-stock-py"></a>
### `SP_M4e_Figure_sensitivity_Item-Region-Process_stock.py`

从 S5.5 merged_structure 原始长表计算区域/商品/过程结构图用数据并绘图，生成 Figure9_structure_importance_v3.xlsx 等历史命名产物。

源码：[SP_M4e_Figure_sensitivity_Item-Region-Process_stock.py](../../SP_M4e_Figure_sensitivity_Item-Region-Process_stock.py)；696 行。

主要接口：[`main`](../../SP_M4e_Figure_sensitivity_Item-Region-Process_stock.py#L649)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Figure9_structure_importance_v3.xlsx`；`_stack_v3.png`；`_stack_v3.svg`；`importance_by_variable.csv`；`importance_detail.csv`；`mc_success_structure_emissions.csv`；`mc_success_structure_totals.csv`。

<a id="file-sp-m4f-figure-structure-importance-targetrange-v1-py"></a>
### `SP_M4f_Figure_structure_importance_targetrange_v1.py`

读取 S5.5 已生成的结构份额和四分位分布表，绘制堆叠与分布网格，是早期结构图入口。

源码：[SP_M4f_Figure_structure_importance_targetrange_v1.py](../../SP_M4f_Figure_structure_importance_targetrange_v1.py)；753 行。

主要接口：[`main`](../../SP_M4f_Figure_structure_importance_targetrange_v1.py#L665)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`FigureS5_5_structure_importance_v1.xlsx`；`_quartile_grid_v1.png`；`_quartile_grid_v1.svg`；`_stack_v1.png`；`_stack_v1.svg`；`structure_quartile_histogram_top.csv`；`structure_quartile_panel_samples.csv`。

<a id="file-sp-m4f-figure-structure-importance-targetrange-v2-py"></a>
### `SP_M4f_Figure_structure_importance_targetrange_v2.py`

从 Figure9 结构工作簿绘制区域/商品/过程份额堆叠；主要指标为组排放占总排放比例，不是 v3 的回归重要性。

源码：[SP_M4f_Figure_structure_importance_targetrange_v2.py](../../SP_M4f_Figure_structure_importance_targetrange_v2.py)；769 行。

主要接口：[`main`](../../SP_M4f_Figure_structure_importance_targetrange_v2.py#L757)。

代码内导入：[config_paths.py](../../config_paths.py)。

动态文件引用线索：[SP_M1a_Figure_pie_structure_plot_v2.1.py](../../SP_M1a_Figure_pie_structure_plot_v2.1.py)、[SP_M3a_Figure_macc_stock_v3.1.py](../../SP_M3a_Figure_macc_stock_v3.1.py)。

本目录调用/引用者：[SP_M4f_Figure_structure_importance_targetrange_v3.py](../../SP_M4f_Figure_structure_importance_targetrange_v3.py)。

文件线索：`Figure9_structure_importance_v3.xlsx`；`_v2.1.png`；`_v2.1.svg`。

<a id="file-sp-m4f-figure-structure-importance-targetrange-v3-py"></a>
### `SP_M4f_Figure_structure_importance_targetrange_v3.py`

当前回归重要性图入口：结合 S5.5 结构排放和 S5.0 策略重要性构造分组回归贡献，输出可审计源表和图，支撑 Figure 4a–d。

源码：[SP_M4f_Figure_structure_importance_targetrange_v3.py](../../SP_M4f_Figure_structure_importance_targetrange_v3.py)；1,881 行。

主要接口：[`main`](../../SP_M4f_Figure_structure_importance_targetrange_v3.py#L1822)。

代码内导入：[SP_M4f_Figure_structure_importance_targetrange_v2.py](../../SP_M4f_Figure_structure_importance_targetrange_v2.py)、[config_paths.py](../../config_paths.py)。

动态文件引用线索：[S5_5_1_Region-Item-Process_Importance_Gen.py](../../S5_5_1_Region-Item-Process_Importance_Gen.py)。

文件线索：`Figure9_regression_importance_v3.1.xlsx`；`_regression_v3.1.png`；`_regression_v3.1.svg`；`emissions_summary_By_Country_Process_Item.csv`；`importance_by_variable.csv`；`importance_detail.csv`；`mc_success_structure_emissions.csv`。

<a id="file-sp-si1-figure-prod-trend-region-fb-py"></a>
### `SP_SI1_Figure_prod_trend_region_fb.py`

从 production_summary 和字典聚合区域/商品生产趋势，导出图用汇总 CSV 与 PNG/SVG。

源码：[SP_SI1_Figure_prod_trend_region_fb.py](../../SP_SI1_Figure_prod_trend_region_fb.py)；289 行。

主要接口：[`plot_prod_trend_region_fb`](../../SP_SI1_Figure_prod_trend_region_fb.py#L194)、[`main`](../../SP_SI1_Figure_prod_trend_region_fb.py#L272)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`_agg.csv`；`dict_v3.xlsx`；`production_summary.csv`。

<a id="file-sp-si2-figure-ruminateintakeratio-map-py"></a>
### `SP_SI2_Figure_ruminateIntakeRatio_map.py`

用食物用途和营养/商品映射计算国家反刍食品摄入比例，结合地理边界绘制地图。

源码：[SP_SI2_Figure_ruminateIntakeRatio_map.py](../../SP_SI2_Figure_ruminateIntakeRatio_map.py)；308 行。

主要接口：[`build_or_load_cache`](../../SP_SI2_Figure_ruminateIntakeRatio_map.py#L136)、[`plot_map_2020`](../../SP_SI2_Figure_ruminateIntakeRatio_map.py#L203)、[`main`](../../SP_SI2_Figure_ruminateIntakeRatio_map.py#L300)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`FoodBalanceSheets_E_All_Data_NOFLAG_demand_refilled.xlsx`；`dict_v3.xlsx`。

<a id="file-sp-si3-figure-emis-reduction-disaggregate-py"></a>
### `SP_SI3_Figure_emis_reduction_disaggregate.py`

读取 S0.49 的 2080 排放汇总，将减排按过程/商品拆分为瀑布等图，复用结构图配色并保存绘图数据。

源码：[SP_SI3_Figure_emis_reduction_disaggregate.py](../../SP_SI3_Figure_emis_reduction_disaggregate.py)；414 行。

主要接口：[`build_fig10_emission_reduction_waterfalls`](../../SP_SI3_Figure_emis_reduction_disaggregate.py#L364)、[`main`](../../SP_SI3_Figure_emis_reduction_disaggregate.py#L407)。

代码内导入：[SP_M1a_Figure_pie_structure_plot_v2.py](../../SP_M1a_Figure_pie_structure_plot_v2.py)、[config_paths.py](../../config_paths.py)。

动态文件引用线索：[SP_M1a_Figure_pie_structure_plot_v2.1.py](../../SP_M1a_Figure_pie_structure_plot_v2.1.py)。

文件线索：`Figure10_emis_reduction_waterfall_data.xlsx`；`Figure10_emis_reduction_waterfall_item_data.csv`；`Figure10_emis_reduction_waterfall_process_data.csv`；`Y2080_Emission_result_summary.xlsx`。

<a id="file-sp-si4-figure-emission-per-kcal-item-py"></a>
### `SP_SI4_Figure_emission_per_kcal_item.py`

读取 2080 排放和能量指标，构造商品单位热量排放与相关展示图，输出强度和作图源数据。

源码：[SP_SI4_Figure_emission_per_kcal_item.py](../../SP_SI4_Figure_emission_per_kcal_item.py)；642 行。

主要接口：[`build_fig11_emission_per_kcal_item`](../../SP_SI4_Figure_emission_per_kcal_item.py#L609)。

代码内导入：[SP_M1a_Figure_pie_structure_plot_v2.py](../../SP_M1a_Figure_pie_structure_plot_v2.py)、[config_paths.py](../../config_paths.py)。

动态文件引用线索：[SP_M1a_Figure_pie_structure_plot_v2.1.py](../../SP_M1a_Figure_pie_structure_plot_v2.1.py)。

文件线索：`Figure11_emission_per_kcal_item_data.xlsx`；`Y2080_Emission_result_summary.xlsx`；`_data.csv`。


<a id="group-7"></a>
## 7. SA / SC 分析与一致性检查

<a id="file-sa0-1-population-analysis-py"></a>
### `SA0_1_Population_analysis.py`

按模型国家映射整理人口时间序列与区域聚合，输出人口分析工作簿，辅助解释未来需求驱动。

源码：[SA0_1_Population_analysis.py](../../SA0_1_Population_analysis.py)；143 行。

主要接口：[`build_population_growth_table`](../../SA0_1_Population_analysis.py#L38)、[`parse_args`](../../SA0_1_Population_analysis.py#L91)、[`main`](../../SA0_1_Population_analysis.py#L123)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[config_paths.py](../../config_paths.py)。

文件线索：`SA0_1_Population_analysis.xlsx`。

<a id="file-sa1-1-ghg-emis-map-py"></a>
### `SA1_1_GHG_emis_map.py`

读取 BASE 排放、人口和地理边界，绘制 2020 年国家总量与人均 GHG 地图；属于辅助展示脚本。

源码：[SA1_1_GHG_emis_map.py](../../SA1_1_GHG_emis_map.py)；194 行。

主要接口：[`get_optimized_norm_cmap`](../../SA1_1_GHG_emis_map.py#L97)、[`plot_map`](../../SA1_1_GHG_emis_map.py#L146)。

文件线索：`../../input/Driver/Population/WPP/Population_E_All_Data_NOFLAG.csv`；`../../output/BASE/Emis/emissions_summary.xlsx`；`../../src/dict_v3.xlsx`；`Global_GHG_2020_PerCapita_Optimized.png`；`Global_GHG_2020_Total_Optimized_Gt.png`。

<a id="file-sc0-1-nutrition-check-py"></a>
### `SC0_1_Nutrition_check.py`

核对模型节点需求与营养因子/最低摄入，输出国家—年份营养检查工作簿，定位覆盖或数量口径差异。

源码：[SC0_1_Nutrition_check.py](../../SC0_1_Nutrition_check.py)；210 行。

主要接口：[`parse_args`](../../SC0_1_Nutrition_check.py#L128)、[`main`](../../SC0_1_Nutrition_check.py#L154)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[config_paths.py](../../config_paths.py)。

文件线索：`SC0_1_Nutrition_check.xlsx`；`detailed_node_summary.csv`。

<a id="file-sc0-2-nutrition-production-check-py"></a>
### `SC0_2_Nutrition_production_check.py`

比较基期生产和营养结构所需数量/供给，生成 2020 年营养—生产检查表，辅助基期一致性判断。

源码：[SC0_2_Nutrition_production_check.py](../../SC0_2_Nutrition_production_check.py)；122 行。

主要接口：[`main`](../../SC0_2_Nutrition_production_check.py#L74)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Nutrition_production_check_2020.xlsx`；`Nutrition_profile_rescaled.xlsx`；`Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv`；`dict_v3.xlsx`。

<a id="file-sc0-3-item-demand-category-py"></a>
### `SC0_3_Item_Demand_Category.py`

从 FBS 按模型商品整理食物、饲料、种子、加工、损失等用途的数量和比例，生成 Demand_composition.xlsx，供残余需求和损失情景使用。

源码：[SC0_3_Item_Demand_Category.py](../../SC0_3_Item_Demand_Category.py)；254 行。

主要接口：[`main`](../../SC0_3_Item_Demand_Category.py#L118)。

代码内导入：[config_paths.py](../../config_paths.py)。

文件线索：`Demand_composition.xlsx`；`FoodBalanceSheets_E_All_Data_NOFLAG_demand_refilled.xlsx`；`dict_v3.xlsx`。

<a id="file-sc0-4-item-demand-supply-trade-py"></a>
### `SC0_4_Item_Demand_Supply_Trade.py`

按 M49 和模型商品汇总 2010—2020 需求、供给、进口、出口及用途关系，支持基期贸易/平衡检查。

源码：[SC0_4_Item_Demand_Supply_Trade.py](../../SC0_4_Item_Demand_Supply_Trade.py)；253 行。

主要接口：[`main`](../../SC0_4_Item_Demand_Supply_Trade.py#L179)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[config_paths.py](../../config_paths.py)。

文件线索：`dict_v3.xlsx`。

<a id="file-sc1-1-regression-output-compare-py"></a>
### `SC1_1_regression_output_compare.py`

比较两个情景输出目录的非日志表，按键和数值容差检查语义一致性，导出差异；是可复用结果比较工具。

源码：[SC1_1_regression_output_compare.py](../../SC1_1_regression_output_compare.py)；348 行。

主要接口：[`TableCompareResult`](../../SC1_1_regression_output_compare.py#L31)、[`main`](../../SC1_1_regression_output_compare.py#L261)。

代码内导入：[config_paths.py](../../config_paths.py)。


<a id="group-8"></a>
## 8. 仍被生产工作流引用的验证代码

<a id="file-st-bioenergy-full-run-smoke-py"></a>
### `ST_bioenergy_full_run_smoke.py`

保留的分层生物能源检查运行器，支持 unit、module_integration、solver_micro、full_regression；S5.9 仍调用它做接口/微型求解检查。

源码：[ST_bioenergy_full_run_smoke.py](../../ST_bioenergy_full_run_smoke.py)；692 行。

主要接口：[`run_smoke`](../../ST_bioenergy_full_run_smoke.py#L627)、[`parse_args`](../../ST_bioenergy_full_run_smoke.py#L659)、[`main`](../../ST_bioenergy_full_run_smoke.py#L685)。

代码内导入：[S1_0_schema.py](../../S1_0_schema.py)、[S2_0_load_data.py](../../S2_0_load_data.py)、[S3_3_bioenergy.py](../../S3_3_bioenergy.py)、[S4_0_main.py](../../S4_0_main.py)、[ST_bioenergy_mvp_test.py](../../ST_bioenergy_mvp_test.py)、[config_paths.py](../../config_paths.py)、[market_balance_diagnostics.py](../../market_balance_diagnostics.py)。

本目录调用/引用者：[S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py](../../S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves.py)。

本目录缺失的引用：`model_run_status.py`；是否阻止入口执行取决于导入所在分支，见总说明。

文件线索：`DS/market_summary.csv`；`Diagnostics/commodity_balance_by_commodity.csv`；`bioenergy_crop_demand.csv`；`bioenergy_diagnostics.csv`；`bioenergy_feedstock_use.csv`；`bioenergy_full_run_smoke_summary.csv`；`bioenergy_full_run_smoke_summary.json`。

<a id="file-st-bioenergy-mvp-test-py"></a>
### `ST_bioenergy_mvp_test.py`

保留的生物能源最小验证与微型算例集合，提供 smoke 运行器仍引用的测试/构造函数；不是当前清理可以直接删去的独立文件。

源码：[ST_bioenergy_mvp_test.py](../../ST_bioenergy_mvp_test.py)；622 行。

主要接口：[`test_bundle_and_residual_reconciliation`](../../ST_bioenergy_mvp_test.py#L43)、[`test_scenario_profile_effect`](../../ST_bioenergy_mvp_test.py#L146)、[`test_carrier_feedstock_bridge_fallback`](../../ST_bioenergy_mvp_test.py#L164)、[`test_market_summary_separates_food_and_bioenergy`](../../ST_bioenergy_mvp_test.py#L210)、[`test_solver_source_contains_explicit_bioenergy_balance`](../../ST_bioenergy_mvp_test.py#L253)、[`test_resource_constraints_and_handoffs`](../../ST_bioenergy_mvp_test.py#L261)、[`main`](../../ST_bioenergy_mvp_test.py#L607)。

代码内导入：[S0_51_prepare_bioenergy_feedstock_bridge.py](../../S0_51_prepare_bioenergy_feedstock_bridge.py)、[S1_0_schema.py](../../S1_0_schema.py)、[S3_0_ds_linear_regional.py](../../S3_0_ds_linear_regional.py)、[S3_3_bioenergy.py](../../S3_3_bioenergy.py)、[S3_6_scenarios.py](../../S3_6_scenarios.py)、[S4_1_results.py](../../S4_1_results.py)。

本目录调用/引用者：[ST_bioenergy_full_run_smoke.py](../../ST_bioenergy_full_run_smoke.py)。

文件线索：`historical.csv`；`params.csv`；`resources.csv`；`scenario.csv`。


<a id="group-9"></a>
## 9. Slurm 提交脚本

<a id="file-submit-sbatch-s5-0-mclevels-sh"></a>
### `submit_sbatch_S5_0_mclevels.sh`

生成并提交 S5.0 Slurm 批次，默认 10 批；默认 WORKDIR 仍指向集群 bin/new，调用 mclevels_batches 并提示合并命令。

源码：[submit_sbatch_S5_0_mclevels.sh](../../submit_sbatch_S5_0_mclevels.sh)；69 行。

当前脚本配置：

```bash
TOTAL_BATCHES=10
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_0_1_sensitivity_mc_levels_batches.py"
```

<a id="file-submit-sbatch-s5-1-1-variable-effect-sh"></a>
### `submit_sbatch_S5_1_1_variable_effect.sh`

生成并提交 S5.1 条件 MC 作业，默认 100 批；默认 WORKDIR 为集群 bin/new，传递批号、总批数和续跑设置。

源码：[submit_sbatch_S5_1_1_variable_effect.sh](../../submit_sbatch_S5_1_1_variable_effect.sh)；71 行。

当前脚本配置：

```bash
TOTAL_BATCHES=100
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_1_1_sensitivity_mc_variable_effect_batches.py"
```

<a id="file-submit-sbatch-s5-3-1-panel-yield-ef-sh"></a>
### `submit_sbatch_S5_3_1_panel_yield_ef.sh`

提交 S5.3 原版面板网格，默认 200 批；从 BASH_SOURCE 取得自身目录，支持 WORKDIR/输出及场景配置，运行批次包装器。

源码：[submit_sbatch_S5_3_1_panel_yield_ef.sh](../../submit_sbatch_S5_3_1_panel_yield_ef.sh)；187 行。

当前脚本配置：

```bash
TOTAL_BATCHES=200
WORKDIR="${WORKDIR:-${SCRIPT_DIR}}"
PYTHON_SCRIPT="S5_3_1_sensitivity_panel_yield_ef_batches.py"
```

<a id="file-submit-sbatch-s5-3-1-panel-yield-ef-v2-sh"></a>
### `submit_sbatch_S5_3_1_panel_yield_ef_v2.sh`

提交 v2 面板实验，默认 200 批并支持环境覆盖；WORKDIR 默认仍为集群 bin/new，需显式确认实际代码树。

源码：[submit_sbatch_S5_3_1_panel_yield_ef_v2.sh](../../submit_sbatch_S5_3_1_panel_yield_ef_v2.sh)；204 行。

当前脚本配置：

```bash
TOTAL_BATCHES=${TOTAL_BATCHES:-200}
WORKDIR=${WORKDIR:-"/lustre/home/2606194130/Food/Code/bin/new"}
PYTHON_SCRIPT=${PYTHON_SCRIPT:-"S5_3_1_sensitivity_panel_yield_ef_batches_v2.py"}
```

<a id="file-submit-sbatch-s5-4-fullmc-sh"></a>
### `submit_sbatch_S5_4_fullmc.sh`

提交 S5.4 全变量 MC，默认 200 批；从自身目录确定默认工作目录，传递样本/批次/续跑设置并给出严格合并命令。

源码：[submit_sbatch_S5_4_fullmc.sh](../../submit_sbatch_S5_4_fullmc.sh)；81 行。

当前脚本配置：

```bash
TOTAL_BATCHES=200
WORKDIR="${WORKDIR:-${SCRIPT_DIR}}"
PYTHON_SCRIPT="S5_4_1_monte_carlo_full_variables_batches.py"
```

<a id="file-submit-sbatch-s5-5-rip-importance-sh"></a>
### `submit_sbatch_S5_5_RIP_importance.sh`

提交 S5.5 结构重要性 MC，默认 200 批，支持起始批、样本和后处理设置；默认 WORKDIR 仍为集群 bin/new。

源码：[submit_sbatch_S5_5_RIP_importance.sh](../../submit_sbatch_S5_5_RIP_importance.sh)；82 行。

当前脚本配置：

```bash
TOTAL_BATCHES=200
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_5_2_Region-Item-Process_Importance_Gen_batches.py"
```

<a id="file-submit-sbatch-s5-6-max-reduction-sh"></a>
### `submit_sbatch_S5_6_max_reduction.sh`

提交 S5.6 国家最大端点实验，默认 10 批；首批承担全球参考等任务，默认工作目录仍为集群 bin/new。

源码：[submit_sbatch_S5_6_max_reduction.sh](../../submit_sbatch_S5_6_max_reduction.sh)；115 行。

当前脚本配置：

```bash
TOTAL_BATCHES=10
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_6_1_max_emission_reduction_potential_batches.py"
```

<a id="file-submit-sbatch-s5-7-strategy-endpoint-rerun-sh"></a>
### `submit_sbatch_S5_7_strategy_endpoint_rerun.sh`

提交 S5.7 策略组合重跑，默认 32 批；围绕组合计划而非国家切分，默认工作目录仍为集群 bin/new。

源码：[submit_sbatch_S5_7_strategy_endpoint_rerun.sh](../../submit_sbatch_S5_7_strategy_endpoint_rerun.sh)；145 行。

当前脚本配置：

```bash
TOTAL_BATCHES=32
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py"
```

<a id="file-submit-sbatch-s5-8-country-strategy-map-sh"></a>
### `submit_sbatch_S5_8_country_strategy_map.sh`

提交国家×九措施独立干预实验，默认 32 批，并编排合并/源数据后处理；默认 WORKDIR 仍为集群 bin/new。

源码：[submit_sbatch_S5_8_country_strategy_map.sh](../../submit_sbatch_S5_8_country_strategy_map.sh)；139 行。

当前脚本配置：

```bash
TOTAL_BATCHES=32
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
OUTPUT_ROOT="/lustre/home/2606194130/Food/Code/output/Country_Dominant_Mitigation_Intervention"
BATCH_SCRIPT="S5_8_1_country_strategy_map_sensitivity_batches.py"
```

<a id="file-submit-sbatch-s5-9-bioenergy-macc-sh"></a>
### `submit_sbatch_S5_9_bioenergy_macc.sh`

提交三生物能源面板的策略 MACC 批次，默认 32 批，支持 quick/exact、独立输出和合并任务；默认从自身目录运行。

源码：[submit_sbatch_S5_9_bioenergy_macc.sh](../../submit_sbatch_S5_9_bioenergy_macc.sh)；195 行。

当前脚本配置：

```bash
TOTAL_BATCHES=32             # recommended: quick=3, exact=32
WORKDIR="${WORKDIR:-${SCRIPT_DIR}}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${CODE_ROOT}/output/Bioenergy_Scenario_MACC_Exact_TS}"
BATCH_SCRIPT="S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py"
```


<a id="group-10"></a>
## 10. SQL 报告查询

<a id="file-figure5-production-ef-report-source-sql"></a>
### `figure5_production_ef_report_source.sql`

DuckDB 报告查询：从 Fig5 EF 审计、当前指标和四分位摘要 CSV 建视图，提取生产排放/总生产热量强度和分组统计；相对路径要求从 Code 目录执行。

源码：[figure5_production_ef_report_source.sql](../../figure5_production_ef_report_source.sql)；57 行。


<a id="group-11"></a>
## 11. 模板、配置和其他辅助文件

| 文件 | 功能与使用边界 |
|---|---|
| [bioenergy_external_spatial_data_manifest.csv](../../bioenergy_external_spatial_data_manifest.csv) | 生物能源外部空间数据来源/获取与用途登记；不是可直接用于求解的全球资源量。 |
| [biomass_data_templates/bioenergy_carrier_feedstock_share.csv](../../biomass_data_templates/bioenergy_carrier_feedstock_share.csv) | 能源载体到物理原料的份额桥接模板，供 S0.51 使用。 |
| [biomass_data_templates/bioenergy_energy_crop_eligible_land_mask.csv](../../biomass_data_templates/bioenergy_energy_crop_eligible_land_mask.csv) | 国家能源作物适宜/可用土地面积接口模板。 |
| [biomass_data_templates/bioenergy_feedstock_parameters.csv](../../biomass_data_templates/bioenergy_feedstock_parameters.csv) | 原料类别、市场映射、干物质、热值、效率及相关系数模板。 |
| [biomass_data_templates/bioenergy_historical_feedstock.csv](../../biomass_data_templates/bioenergy_historical_feedstock.csv) | 历史物理原料需求模板，用于识别已嵌入 FBS 的能源用途。 |
| [biomass_data_templates/bioenergy_resource_constraints.csv](../../biomass_data_templates/bioenergy_resource_constraints.csv) | 残余物、非作物原料、能源作物资源/土地限制模板。 |
| [biomass_data_templates/bioenergy_scenario_targets.csv](../../biomass_data_templates/bioenergy_scenario_targets.csv) | 多情景、国家、年份与原料能源/数量目标模板。 |
| [biomass_data_templates/README.md](../../biomass_data_templates/README.md) | 生物能源输入契约、单位换算、资源接口和避免重复计数说明；部分文字保留历史实现阶段。 |
| [biomass_energy_system_flow.mmd](../../biomass_energy_system_flow.mmd) | 已有生物能源系统流程的 Mermaid 源图；可辅助理解设计，实际实现边界以本说明和代码为准。 |
| [biomass_energy_system_flow.svg](../../biomass_energy_system_flow.svg) | 上述系统流程的 SVG 渲染图。 |
| [biomass_parameter_requirements.csv](../../biomass_parameter_requirements.csv) | 生物能源参数需求、字段及数据准备清单。 |
| [linear_model_iis.ilp](../../linear_model_iis.ilp) | 已有求解不可行诊断 IIS 输出，记录一组冲突约束；不是输入参数或模型源码。 |
| [linear_model_infeasible.lp](../../linear_model_infeasible.lp) | 已有不可行模型的 LP 导出，用于检查当时求解方程；不代表当前全部配置的状态。 |
| [net-zero-food.new.code-workspace](../../net-zero-food.new.code-workspace) | VS Code 工作区配置；工作区名称或路径可能保留旧目录，需要与实际打开目录核对。 |
| [thermal_stress_templates/README.md](../../thermal_stress_templates/README.md) | STS 数据、覆盖、质量平衡与去重要求；须区分模板登记 CSV 与运行时 JSON manifest。 |
| [thermal_stress_templates/thermal_activity_factors_template.csv](../../thermal_stress_templates/thermal_activity_factors_template.csv) | 每头/活动相关的养分、VS、能源等系数模板。 |
| [thermal_stress_templates/thermal_data_manifest_template.csv](../../thermal_stress_templates/thermal_data_manifest_template.csv) | 外部数据来源、版本、许可、路径和 QC 的人工登记模板，不替代 exposure_pipeline 输出的 JSON。 |
| [thermal_stress_templates/thermal_exposure_5km_example.csv](../../thermal_stress_templates/thermal_exposure_5km_example.csv) | 5 km 暴露数据结构示例，用于说明字段和元数据；不是正式气候输入。 |
| [thermal_stress_templates/thermal_pollutant_factors_template.csv](../../thermal_stress_templates/thermal_pollutant_factors_template.csv) | 各物种/角色/活动的污染物因子模板。 |
| [thermal_stress_templates/thermal_response_evidence_template.csv](../../thermal_stress_templates/thermal_response_evidence_template.csv) | 文献/试验响应证据字段模板，供 STS.02 拟合。 |
| [thermal_stress_templates/thermal_response_registry_template.csv](../../thermal_stress_templates/thermal_response_registry_template.csv) | 物种、生产角色/系统、影响指标和响应系数注册表模板。 |
| [thermal_stress_templates/thermal_species_commodity_map.csv](../../thermal_stress_templates/thermal_species_commodity_map.csv) | 运行代码默认引用的物种—畜产品映射资产；不同于占位效应系数。 |
| [thermal_stress_templates/thermal_strain_registry_template.csv](../../thermal_stress_templates/thermal_strain_registry_template.csv) | 可选 hazard/recovery 指标到动物 strain 变量转换规则模板。 |
| [thermal_stress_templates/thermal_tier2_parameters_template.csv](../../thermal_stress_templates/thermal_tier2_parameters_template.csv) | Tier 2 能量、消化率、甲烷及 N/P 平衡参数模板；正式运行需生产级参数。 |

