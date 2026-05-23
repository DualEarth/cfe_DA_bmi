# Folder 4 — Dynamic Variance Used Directly

## R Formula
```
R(t) = σ²_krig(t)
```
Raw kriging variance used directly as observation error — no flow-magnitude scaling.
σ²_krig from dynamic-spliced obs: `/mnt/disk2/1400_sites_helene/catchment_ts_03463300_spliced_dyn_helene/`
RNG seed = 42.

## Pipeline

### 1. Calibrate
Shared best_params.json from external `calibrate-cfe` repo.
Per-catchment json exists at: `da_results_dynamic_novrugt_seeded/{cat}/{cat}_best_params.json`

### 2. Assimilation
| Sub-step | Status |
|---|---|
| DA analysis trajectory | ✅ `da_results_dynamic_novrugt_seeded/{cat}/{cat}_test_results.csv` |
| 2a/2b arms | ❌ not run |
| 18hr forecast cycles | ❌ not run |
| 600-member ensemble | ❌ not run |

### 3. Route
| Script | Input | Output | Status |
|---|---|---|---|
| `run_route.py` | `da_results_dynamic_novrugt_seeded/` | `dynamic_novrugt_seeded_routed/routed_Q_test.csv` | ✅ |

### 4. Evaluate
| Sub-step | Status |
|---|---|
| 4a. Error decay | ❌ no forecast data |
| 4b. 600-member ensemble | ❌ no ensemble data |
| 4c. Ensemble mean + spread | ❌ no forecast data |

## Key Results (deterministic analysis routing)
- Full period KGE: **+0.200**  NSE: **+0.428**
- Helene KGE: **+0.132**  NSE: **+0.303**
- Helene peak: 667.9 m³/s (35% of USGS 1885.7 m³/s)

## Data Source
`/mnt/disk2/1400_sites_helene/da_results_dynamic_novrugt_seeded/`
