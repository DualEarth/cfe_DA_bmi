# DA Methods — Qkrig CFE Data Assimilation for Hurricane Helene Forecasting

Gauge: **03463300** (South Toe River Near Celo, NC)  
Watershed: 21 catchments, 113.18 km², outlet wb-1016283

---

## Folder Structure

```
da_methods/
├── README.md
├── 1_calibrate/          # Step 1: CFE calibration with Qkrig
├── 2_assimilation/       # Step 2: DA scripts, ensemble design, batch runners
├── 3_routing/            # Step 3: t-route ensemble routing to gauge
└── 4_evaluation/         # Step 4: all evaluation and diagnostic plots
```

Note: `run_route.py` (deterministic Muskingum routing via tx-fast-hydrology) lives in
`catchment_run/` — it routes the dynamic-Vrugt DA results to the gauge.

---

## 1. Calibrate CFE with Qkrig

| Script | Description |
|---|---|
| `1_calibrate/calibrate_catchment_cfe_da_v2.py` | Per-catchment CFE calibration using Qkrig streamflow observations. Outputs `{cat-id}_best_params.json` used by all downstream DA steps. |

Calibration results (all 21 catchments) are in `v2_true_enkf_pn/` (NC kriging, held-out gauge run 3).

---

## 2. Assimilation Script for CFE

### 2a — Update Met Forcings (forcing uncertainty arm)
Perturbs precipitation and PET with lognormal (sigma=15%) and normal (sigma=10%) noise.
30 members; each starts from the same DA-corrected state, forced with independent
stochastic draws.

### 2b — Update Hydro States with Vrugt R (hydro uncertainty arm)
Updates soil moisture and other CFE states via EnKF using Qkrig observations.
Observation error variance uses the dynamic Vrugt R formula:
`R = (alpha * y)^2 + 0.001 * sigma^2_krig`
20 members; deterministic forcing, 5% multiplicative state perturbation after each DA update.

### 18-hour Forecast Cycle
DA is applied at each initialization timestep. After assimilation the model runs
freely (DA off) for 18 hours. At the next timestep a new 18-hour cycle begins
with fresh DA. Each cycle's output is saved separately.

### Ensemble Design (600 members)
The 30 forcing draws and 20 hydro-state draws are crossed to produce
600 = 30 x 20 members for probabilistic forecasting.

| Script | Description |
|---|---|
| `2_assimilation/run_perturbation_da_on.py` | Runs DA-on cycles for one catchment; produces forcing-arm CSV (30 members) and hydro-arm CSV (20 members). |
| `2_assimilation/run_crossed_ensemble.py` | Crosses the 30 x 20 arms to build the 600-member ensemble; outputs `{cat-id}_crossed_ensemble.parquet`. |
| `2_assimilation/batch_run_da_on_all_cats.sh` | Batch runner: runs `run_perturbation_da_on.py` for all 21 catchments. |
| `2_assimilation/batch_run_crossed_all_cats.sh` | Batch runner: runs `run_crossed_ensemble.py` for all 21 catchments. Stages `best_params` directly from `v2_true_enkf_pn`. |
| `4_evaluation/plot_da_perturbation_arms.py` | Plots 2a and 2b spaghetti ensemble spread figures; outputs `{cat-id}_2a_forcing_arm_helene.png`, `{cat-id}_2b_hydro_arm_helene.png`, `{cat-id}_2ab_arms_comparison.png`. |

---

## 3. Routing — run_route.py with DA

Routes per-catchment runoff through the channel network (Muskingum-Cunge) to
gauge 03463300 at every hour in the 18-hour forecast cycle.

| Script | Description |
|---|---|
| `catchment_run/run_route.py` | Muskingum routing (tx-fast-hydrology) for deterministic DA results (Vrugt or no-Vrugt). Reads `{cat-id}_test_results.csv`. |
| `3_routing/run_route_crossed_ensemble.py` | Routes all 600 members of the crossed ensemble through t-route Muskingum-Cunge. Reads all 21 catchment parquets; outputs `routed_crossed_ensemble.parquet` at the gauge. |

**Routed results:**

| Run | Results dir | Peak Q | KGE vs Qkrig | KGE vs USGS |
|---|---|---|---|---|
| Vrugt (dynamic R) | `vrugt_dynamic_routed/` | 645.7 m³/s | 0.869 | 0.277 |
| No-Vrugt (const R) | `novrugt_dynamic_routed/` | 622.5 m³/s | 0.789 | 0.222 |
| USGS gauge (truth) | — | 1885.7 m³/s | — | — |

Dynamic Vrugt R improves KGE by +0.08 vs Qkrig and +0.055 vs USGS gauge.

---

## 4. Evaluate at the Gauge

### 4a — Error Converging: DA vs Open Loop over 18-hour Lead Time

| Script | Description |
|---|---|
| `2_assimilation/run_lead_time_forecast_sweep.py` | Runs 18-hour free forecasts from each DA-corrected state; stores per-lead-hour error. |
| `4_evaluation/plot_lead_time_decay.py` | Plots RMSE/KGE vs lead hour: DA-corrected states decaying toward open-loop skill. |
| `4_evaluation/plot_lead_time_decay_gauge.py` | Same as above but evaluated at the routed gauge discharge. |
| `4_evaluation/plot_lead_time_reconstructed_timeseries.py` | Reconstructed timeseries from all 18-hour cycles concatenated end-to-end. |
| `4_evaluation/plot_forecast_error_fixed_target.py` | Forecast error vs Helene peak as fixed verification target. |
| `4_evaluation/plot_forecast_error_per_init.py` | Per-initialization-time forecast error breakdown. |

### 4b — 600-Member Ensemble vs Observations During Helene

| Script | Description |
|---|---|
| `4_evaluation/plot_crossed_ensemble.py` | Catchment-level percentile envelope (5/25/50/75/95th pct) for `cat-1016300`. |
| `4_evaluation/plot_routed_ensemble_combined.py` | **Main poster panel.** Routed 600-member ensemble envelope at the gauge vs USGS obs + deterministic Vrugt/no-Vrugt lines. USGS peak (1886 m³/s) is bracketed by the 5-95th percentile band. |
| `4_evaluation/plot_vrugt_comparison.py` | Vrugt vs no-Vrugt deterministic comparison: full period + Helene zoom. |

### 4c — Ensemble Mean + Spread: All 18-hour Forecast Cycles During Helene

| Script | Description |
|---|---|
| `4_evaluation/plot_helene_issue_time_hydrograph.py` | All 18-hour forecast cycle traces during Helene overlaid; shows ensemble mean and spread evolving across initialization times. |
| `4_evaluation/plot_forecast_spaghetti.py` | Spaghetti plot of all member traces from every forecast cycle during Helene. |

---

## Data Flow Summary

```
v2_true_enkf_pn/{cat-id}_best_params.json        [calibration results, all 21 cats]
         |
         v
run_perturbation_da_on.py   -->  {cat-id}_da_forcing_arm.csv  (30 members)
                                 {cat-id}_da_hydro_arm.csv    (20 members)
                                         |
                                         v (diagnostic 2a/2b figures only)
                                 plot_da_perturbation_arms.py

run_crossed_ensemble.py     -->  {cat-id}_crossed_ensemble.parquet  (600 members, mm/h)
         |
         v
run_route_crossed_ensemble.py  -->  routed_crossed_ensemble.parquet  (600 members, m3/s at gauge)
         |
         v
plot_routed_ensemble_combined.py  -->  helene_ensemble_vs_usgs.png  [4b poster panel]

run_route.py (Vrugt/no-Vrugt)  -->  routed_Q_test.csv  (deterministic, m3/s at gauge)
         |
         v
plot_vrugt_comparison.py  -->  vrugt_vs_novrugt_helene_zoom.png  [Vrugt impact figure]
```

---

## Run Order (all 21 catchments)

```bash
# 1. Calibration (already done for all 21 catchments)

# 2. DA-on perturbation arms (2a/2b diagnostics)
bash batch_run_da_on_all_cats.sh

# 2. Crossed ensemble (600 members per catchment)
bash batch_run_crossed_all_cats.sh

# 3. Route deterministic DA (Vrugt / no-Vrugt)
python3 run_route.py --results-dir da_results_dynamic_vrugt_seeded --period test ...
python3 run_route.py --results-dir da_results_dynamic_novrugt_seeded --period test ...

# 3. Route 600-member ensemble to gauge
python3 run_route_crossed_ensemble.py --ensemble-dir v2_crossed_ensemble ...

# 4. Generate evaluation plots
python3 plot_routed_ensemble_combined.py ...
python3 plot_vrugt_comparison.py ...
python3 plot_da_perturbation_arms.py ...
```
