# Folder 3 — Dynamic Variance Scaled Using Vrugt Formula (Seeded)

## R Formula
```
R(t) = (0.10 × y_obs(t))² + 0.001 × σ²_krig(t)
```
Same Vrugt formula as Folder 1 but:
- RNG seed = 42 (reproducible)
- σ²_krig from dynamic-spliced obs: `/mnt/disk2/1400_sites_helene/catchment_ts_03463300_spliced_dyn_helene/`

## Pipeline

### 1. Calibrate
Shared best_params.json from external `calibrate-cfe` repo.
Per-catchment json exists at: `da_results_dynamic_vrugt_seeded/{cat}/{cat}_best_params.json`

### 2. Assimilation
| Sub-step | Status |
|---|---|
| DA analysis trajectory | ✅ `da_results_dynamic_vrugt_seeded/{cat}/{cat}_test_results.csv` |
| 2a/2b arms | ❌ not run (would need new compute with spliced obs + seed=42) |
| 18hr forecast cycles | ❌ not run |
| 600-member ensemble | ❌ not run |

### 3. Route
| Script | Input | Output | Status |
|---|---|---|---|
| `run_route.py` | `da_results_dynamic_vrugt_seeded/` | `dynamic_vrugt_seeded_routed/routed_Q_test.csv` | ✅ |

### 4. Evaluate
| Sub-step | Status |
|---|---|
| 4a. Error decay | ❌ no forecast data |
| 4b. 600-member ensemble | ❌ no ensemble data |
| 4c. Ensemble mean + spread | ❌ no forecast data |

## Key Results (deterministic analysis routing)
- Full period KGE: **+0.261**  NSE: **+0.485**
- Helene KGE: **+0.189**  NSE: **+0.372**
- Helene peak: 693.8 m³/s (37% of USGS 1885.7 m³/s)

## Data Source
`/mnt/disk2/1400_sites_helene/da_results_dynamic_vrugt_seeded/`
