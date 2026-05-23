# DA Experiment Index

Four experiments comparing observation error variance (R) formulations for CFE + EnKF
data assimilation at USGS gauge 03463300 (South Toe River Near Celo, NC).

All shared scripts are in `1_calibrate/`, `2_assimilation/`, `3_routing/`, `4_evaluation/`.
Calibrated parameters (best_params.json) are shared across all folders from the
external `calibrate-cfe` repo — R formula is irrelevant at calibration time.

---

## Results Summary

| Folder | R Formula | Full KGE | Helene KGE | Helene peak % USGS |
|---|---|---|---|---|
| [1 — Variance scaled Vrugt](folder1_variance_scaled_vrugt/) | `(0.10·y)² + 0.001·σ²_krig` | **+0.277** | **+0.213** | ~40% |
| [2 — Fixed R=0.07](folder2_fixed_r_007/) | `0.07` (constant) | +0.261 | +0.189 | 37% |
| [3 — Dynamic Vrugt seeded](folder3_dynamic_vrugt_seeded/) | `(0.10·y)² + 0.001·σ²_krig` (seed=42, spliced obs) | +0.261 | +0.189 | 37% |
| [4 — Dynamic variance direct](folder4_dynamic_variance_direct/) | `σ²_krig` directly (seed=42) | +0.200 | +0.132 | 35% |

**Finding:** Vrugt formula (Folder 1) gives the best gauge-level KGE. Using raw σ²_krig
directly (Folder 4) is the worst — large kriging variance during Helene weakens DA
updates exactly when they are most needed.

---

## Completeness Matrix

| Step | Folder 1 | Folder 2 | Folder 3 | Folder 4 |
|---|---|---|---|---|
| 1. Calibrate | ✅ shared | ✅ shared | ✅ shared | ✅ shared |
| 2a. Forcing arm figures | ✅ | ✅ (same as F1) | ❌ | ❌ |
| 2b. Hydro-state arm figures | ✅ | ✅ (same as F1) | ❌ | ❌ |
| 2. 18hr forecast cycles | ✅ | ✅ | ❌ | ❌ |
| 2. 600-member ensemble | ✅ | ✅ | ❌ | ❌ |
| 3. Route analysis trajectory | ✅ | ✅ | ✅ | ✅ |
| 3. Route 18hr forecast cycles | ✅ | ✅ | ❌ | ❌ |
| 4a. Error decay | ✅ | ✅ | ❌ | ❌ |
| 4b. Ensemble vs obs | ✅ | ✅ | ❌ | ❌ |
| 4c. Reconstructed timeseries | ✅ | ✅ | ❌ | ❌ |

---

## Server Data Paths

| Folder | Analysis results | Routed output |
|---|---|---|
| 1 | `suma_helen_poster/da_results/v2_true_enkf_vrugt/` | `vrugt_dynamic_routed/` |
| 2 | `suma_helen_poster/da_results/v2_lead_time_forecast_hardcoded_r/` | `v2_lead_time_forecast_hardcoded_r_routed/` |
| 3 | `1400_sites_helene/da_results_dynamic_vrugt_seeded/` | `dynamic_vrugt_seeded_routed/` |
| 4 | `1400_sites_helene/da_results_dynamic_novrugt_seeded/` | `dynamic_novrugt_seeded_routed/` |
