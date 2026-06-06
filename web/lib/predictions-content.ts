// AUTO-GENERATED from predictions/*.json by web/scripts/sync-predictions.mjs.
// Do not edit by hand. Run `pnpm sync:predictions` (or any typecheck/build)
// to regenerate. The JSON shape mirrors the schema documented in
// methodology/10-public-prediction-log.md.

export const PUBLIC_PREDICTIONS = [
  {
    "filename": "2026-06-03-divarasib-divarasib_nct06497556_2026_06.json",
    "schema_version": "1.1",
    "prediction_id": "divarasib-nct06497556-2026-06",
    "prediction_date": "2026-06-03",
    "asset": {
      "name": "divarasib",
      "sponsor": "Hoffmann-La Roche",
      "phase": "phase_3",
      "therapeutic_area": "oncology",
      "modality": "small_molecule",
      "capital_position": "well_capitalized",
      "mechanism": "KRAS G12C inhibitor (covalent, second-generation)",
      "target": "KRAS G12C",
      "indication": "Previously treated KRAS G12C+ advanced/metastatic NSCLC",
      "biomarker_enrichment": true,
      "target_validated": true,
      "num_competitors": 3,
      "regulatory_designations": []
    },
    "trial": {
      "nct_id": "NCT06497556",
      "title": "Divarasib Versus Sotorasib or Adagrasib in Previously Treated KRAS G12C+ Advanced or Metastatic NSCLC",
      "design": "Phase 3, randomized, open-label, 2-arm head-to-head",
      "enrollment": 338,
      "enrollment_status": "ACTUAL (recruitment complete as of 2026-06-03)",
      "primary_endpoint": "Progression-Free Survival (PFS)",
      "primary_completion_date": "2027-09-30",
      "primary_completion_type": "ESTIMATED",
      "source": "https://clinicaltrials.gov/study/NCT06497556 (fetched 2026-06-03)"
    },
    "framework": {
      "predicted_pos": 0.5929,
      "predicted_pos_ci_low": 0.5476,
      "predicted_pos_ci_high": 0.6341,
      "base_rate": 0.442,
      "reflexivity_multiplier": 1.08,
      "rnpv_base_usd_m": 948.2,
      "rnpv_low_usd_m": 636.7,
      "rnpv_high_usd_m": 1336.8,
      "monte_carlo_p25_usd_m": 636.7,
      "monte_carlo_p50_usd_m": 935.1,
      "monte_carlo_p75_usd_m": 1336.8,
      "monte_carlo_paths": 10000,
      "pos_adjustments": [
        {
          "name": "modality: small_molecule",
          "multiplier": 1,
          "rationale": "Reference modality. Most BIO/Informa base rates are computed on a small-molecule-dominant historical cohort."
        },
        {
          "name": "biomarker enrichment",
          "multiplier": 1.2,
          "rationale": "Trial enriches the population using a predictive biomarker, raising response rate and statistical power."
        },
        {
          "name": "target validated",
          "multiplier": 1.15,
          "rationale": "Target has prior clinical validation in this indication (e.g., a prior approved drug against the same target)."
        },
        {
          "name": "competitive density (3 competitors)",
          "multiplier": 0.9,
          "rationale": "Three or more direct competitors in the same indication raise the commercial bar required for approval and reduce enrollment speed."
        },
        {
          "name": "reflexivity: well_capitalized",
          "multiplier": 1.08,
          "rationale": "≥24 months runway, no near-term raise pressure. Enables adaptive trial design, biomarker-enriched populations, active-comparator trials, and proactive FDA engagement — all costly signals that capital-constrained sponsors cannot credibly emit. Spence-style separating equilibrium: only well-capitalized sponsors can afford the signal."
        }
      ]
    },
    "resolution_criteria": "outcome = 1 if Roche reports a statistically significant PFS benefit (or pre-specified non-inferiority threshold met) on the primary analysis at PCD or via a pre-specified interim, AND a regulatory submission follows within 12 months. outcome = 0 if the trial misses its primary endpoint or is terminated for futility/safety. Partial/ambiguous outcomes (sig PFS but no submission, etc.) noted in resolution.note and treated as 0.5 for Brier scoring.",
    "resolution": {
      "date": null,
      "outcome": null,
      "source": null,
      "note": "Awaiting catalyst — primary completion estimated 2027-09-30."
    },
    "methodology_writeup": "methodology/18-divarasib-live-forward-prediction.md"
  },
  {
    "filename": "2020-03-01-tisotumab_vedotin_combo_arm_gog_3023-seed_tisotumab_combo_p3_2020_03.json",
    "asset": {
      "capital_position": "well_capitalized",
      "modality": "antibody_drug_conjugate",
      "name": "tisotumab vedotin (combo arm, GOG-3023)",
      "phase": "phase_3",
      "therapeutic_area": "oncology"
    },
    "framework": {
      "predicted_pos": 0.42,
      "reflexivity_multiplier": 1.08
    },
    "prediction_date": "2020-03-01",
    "prediction_id": "seed-tisotumab-combo-p3-2020-03",
    "resolution": {
      "date": null,
      "outcome": null,
      "source": "Outcome pending: confirmatory Phase 3 readout in cervical cancer combo. Logged as unresolved to demonstrate the n_unresolved surface."
    },
    "schema_version": "1.0"
  },
  {
    "filename": "2022-06-01-adagrasib-seed_adagrasib_2022_06.json",
    "asset": {
      "capital_position": "adequate",
      "modality": "small_molecule",
      "name": "adagrasib",
      "phase": "phase_2",
      "therapeutic_area": "oncology"
    },
    "framework": {
      "predicted_pos": 0.161,
      "reflexivity_multiplier": 1
    },
    "prediction_date": "2022-06-01",
    "prediction_id": "seed-adagrasib-2022-06",
    "resolution": {
      "date": "2022-12-12",
      "outcome": 1,
      "source": "FDA accelerated approval (Krazati, NDA 216340), Dec 12 2022. Methodology framework retrospective backtest documented in 05-worked-example-adagrasib.md."
    },
    "schema_version": "1.0"
  },
  {
    "filename": "2020-04-01-sotorasib-seed_sotorasib_2020_04.json",
    "asset": {
      "capital_position": "well_capitalized",
      "modality": "small_molecule",
      "name": "sotorasib",
      "phase": "phase_2",
      "therapeutic_area": "oncology"
    },
    "framework": {
      "predicted_pos": 0.155,
      "reflexivity_multiplier": 1.08
    },
    "prediction_date": "2020-04-01",
    "prediction_id": "seed-sotorasib-2020-04",
    "resolution": {
      "date": "2021-05-28",
      "outcome": 1,
      "source": "FDA accelerated approval (Lumakras, NDA 214665), May 28 2021. Retrospective backtest; Amgen well-capitalized at cutoff."
    },
    "schema_version": "1.0"
  },
  {
    "filename": "2019-09-01-sintilimab_1l_nsclc_orient_11-seed_sintilimab_checkmate_1l_nsclc_2019_09.json",
    "asset": {
      "capital_position": "adequate",
      "modality": "monoclonal_antibody",
      "name": "sintilimab (1L NSCLC, ORIENT-11)",
      "phase": "phase_3",
      "therapeutic_area": "oncology"
    },
    "framework": {
      "predicted_pos": 0.38,
      "reflexivity_multiplier": 1
    },
    "prediction_date": "2019-09-01",
    "prediction_id": "seed-sintilimab-checkmate-1L-NSCLC-2019-09",
    "resolution": {
      "date": "2022-03-24",
      "outcome": 0,
      "source": "FDA CRL (Mar 24 2022). ODAC voted 14-1 against approval citing single-country trial. Counted as failure for US registration; sintilimab is approved in China. Demonstrates the framework's miss on cross-jurisdictional risk (documented limitation in 04-scorecard-pillars.md)."
    },
    "schema_version": "1.0"
  },
  {
    "filename": "2018-09-01-selpercatinib-seed_selpercatinib_2018_09.json",
    "asset": {
      "capital_position": "well_capitalized",
      "modality": "small_molecule",
      "name": "selpercatinib",
      "phase": "phase_2",
      "therapeutic_area": "oncology"
    },
    "framework": {
      "predicted_pos": 0.158,
      "reflexivity_multiplier": 1.08
    },
    "prediction_date": "2018-09-01",
    "prediction_id": "seed-selpercatinib-2018-09",
    "resolution": {
      "date": "2020-05-08",
      "outcome": 1,
      "source": "FDA accelerated approval (Retevmo, NDA 213246), May 8 2020. Loxo Oncology well-capitalized at cutoff per pre-Lilly-acquisition financials."
    },
    "schema_version": "1.0"
  },
  {
    "filename": "2018-06-01-debio_1347_fgfr_inhibitor-seed_debio_1347_fgfr_2018_06.json",
    "asset": {
      "capital_position": "constrained",
      "modality": "small_molecule",
      "name": "debio 1347 (FGFR inhibitor)",
      "phase": "phase_2",
      "therapeutic_area": "oncology"
    },
    "framework": {
      "predicted_pos": 0.089,
      "reflexivity_multiplier": 0.88
    },
    "prediction_date": "2018-06-01",
    "prediction_id": "seed-debio-1347-fgfr-2018-06",
    "resolution": {
      "date": "2021-07-15",
      "outcome": 0,
      "source": "Debiopharm discontinued FGFR program July 2021 (DBA-1347). Phase 2 hepatotoxicity signal; lower efficacy vs. competitors. Constrained capital position contributed to deprioritization — the reflexivity adjustment correctly captured this."
    },
    "schema_version": "1.0"
  },
  {
    "filename": "2017-04-01-larotrectinib-seed_larotrectinib_2017_04.json",
    "asset": {
      "capital_position": "well_capitalized",
      "modality": "small_molecule",
      "name": "larotrectinib",
      "phase": "phase_2",
      "therapeutic_area": "oncology"
    },
    "framework": {
      "predicted_pos": 0.142,
      "reflexivity_multiplier": 1.08
    },
    "prediction_date": "2017-04-01",
    "prediction_id": "seed-larotrectinib-2017-04",
    "resolution": {
      "date": "2018-11-26",
      "outcome": 1,
      "source": "FDA accelerated approval (Vitrakvi, NDA 210861), Nov 26 2018. Loxo Oncology / Bayer partnership; well-capitalized."
    },
    "schema_version": "1.0"
  },
  {
    "filename": "2014-11-01-encorafenib-seed_encorafenib_2014_11.json",
    "asset": {
      "capital_position": "adequate",
      "modality": "small_molecule",
      "name": "encorafenib",
      "phase": "phase_2",
      "therapeutic_area": "oncology"
    },
    "framework": {
      "predicted_pos": 0.118,
      "reflexivity_multiplier": 1
    },
    "prediction_date": "2014-11-01",
    "prediction_id": "seed-encorafenib-2014-11",
    "resolution": {
      "date": "2018-06-27",
      "outcome": 1,
      "source": "FDA approval (Braftovi, NDA 210496), Jun 27 2018. Array BioPharma at cutoff; later acquired by Pfizer."
    },
    "schema_version": "1.0"
  }
] as const;
