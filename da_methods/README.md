# DA Methods — Qkrig CFE Data Assimilation for Hurricane Helene Forecasting

**Gauge:** 03463300 — South Toe River Near Celo, NC  
**Watershed:** 21 catchments · 113.18 km² · outlet wb-1016283  
**Event:** Hurricane Helene, September 24–29, 2024  
**Model:** CFE (Conceptual Functional Equivalent) hydrological model via BMI interface  
**DA method:** Ensemble Kalman Filter (EnKF) assimilating Qkrig streamflow observations

---

## Scientific Overview

The pipeline corrects CFE model states every hour using kriging-interpolated streamflow
observations (Qkrig), then launches 18-hour free-running forecasts from each corrected
state. Two uncertainty arms are maintained separately and crossed to form a 600-member
probabilistic ensemble:

- **Forcing arm (30 members):** stochastic precip/PET draws — represents meteorological
  uncertainty in the forecast
- **Hydro-state arm (20 members):** perturbed soil moisture and routing store initial
  conditions — represents uncertainty in the catchment state at initialization

The 600-member crossed ensemble (30 × 20) is routed through the channel network to
USGS gauge 03463300 to produce probabilistic streamflow forecasts at the outlet.

### Observation error variance — Vrugt 2005 heteroscedastic R

```
R(t) = (alpha × y_obs(t))² + scale × sigma²_krig(t)
       alpha = 0.10   (10% relative error)
       scale = 0.001
```

The flow-magnitude term keeps R small at low flow (DA fires aggressively) and larger
at peak flow (where the observation is also more uncertain). The kriging variance
`sigma²_krig` brings per-hour, per-catchment observational uncertainty into R.

### 18-hour forecast cycle

At each initialization time t0:
1. DA analyses the ensemble state using Qkrig
2. The analyzed state is snapshotted (saved to `_da_snapshots.parquet`)
3. DA is switched off — the ensemble free-runs 18 hours
4. At t0+1, DA resumes on the live ensemble; a new 18-hour fork begins

This means the model can be **restarted** from any saved snapshot with DA on or off.

---

## Folder Structure

```
da_methods/
├── README.md
├── 1_calibrate/          # Step 1: CFE parameter calibration with Qkrig
├── 2_assimilation/       # Step 2: DA, ensemble design, lead-time sweep
├── 3_routing/            # Step 3: t-route ensemble routing to gauge
└── 4_evaluation/         # Step 4: evaluation and diagnostic plots
```

Note: `catchment_run/run_route.py` (tx-fast-hydrology Muskingum) routes the
deterministic Vrugt/no-Vrugt DA results to the gauge separately from the ensemble.

---

## Step 1 — Calibrate CFE with Qkrig

| Script | Description |
|---|---|
| `1_calibrate/calibrate_catchment_cfe_da_v2.py` | Per-catchment CFE calibration using Qkrig observations. Outputs `{cat-id}_best_params.json` used by all downstream steps. Also runs the full DA test period when `--enkf-enabled` is passed. |

Calibrated parameters for all 21 catchments are in `v2_true_enkf_pn/`.

**Key CLI flags:**

| Flag | Default | Purpose |
|---|---|---|
| `--enkf-enabled` | off | Turn DA on |
| `--enkf-members 20` | 20 | Ensemble size |
| `--no-vrugt-r` | off | Revert to raw kriging variance (not recommended) |
| `--vrugt-alpha 0.10` | 0.10 | Relative error fraction in Vrugt R |
| `--vrugt-scale 0.001` | 0.001 | Kriging variance scaling in Vrugt R |

---

## Step 2 — Assimilation and Ensemble Design

### 2a — Forcing uncertainty arm (30 members)

DA analyses states every hour using Qkrig. At each issue time, 30 members are forked
with independent stochastic precip/PET draws; all share the same DA-analyzed state.
Free-run 18 hours, no further DA.

- Precip: lognormal multiplier, σ = 0.15 (mean-preserving)
- PET: Gaussian multiplier, σ = 0.10, clipped at 0

### 2b — Hydro-state uncertainty arm (20 members)

Same DA analysis. At each issue time, 20 members are forked with perturbed initial
states (5% multiplicative noise on soil/GW/Nash reservoirs); all use deterministic
forcing. Free-run 18 hours.

### 2c — 18-hour forecast cycle

DA is applied at every hourly initialization throughout the test period. The lead-time
sweep runs two parallel trajectories simultaneously:

- `da` — full EnKF on, states corrected every hour
- `openloop` — no DA ever fires; same forcing perturbations

At each issue time both are forked into 18-hour free forecasts. This produces the
data for the 4a (skill decay) and 4c (reconstructed timeseries) evaluation plots.

### 2d — 600-member crossed ensemble

The 30 forcing draws and 20 hydro-state draws are crossed:
```
member_k  →  forcing draw  k // 20   (0–29)
          →  hydro draw    k % 20    (0–19)
```

Four provenance files are saved alongside `{cat-id}_crossed_ensemble.parquet`:

| File | Contents |
|---|---|
| `{cat-id}_da_snapshots.parquet` | DA-analyzed state at every issue time — enables restart |
| `{cat-id}_member_manifest.csv` | Decoder ring: member_k → (forcing_draw_i, hydro_draw_j) |
| `{cat-id}_hydro_draw_states.parquet` | Actual perturbed initial states for each of 20 hydro draws |
| `{cat-id}_forcing_draw_sequences.parquet` | Actual P/PET values and scale factors for each of 30 forcing draws |

| Script | Description |
|---|---|
| `2_assimilation/run_perturbation_da_on.py` | DA-on perturbation arms for one catchment; outputs forcing-arm CSV (30 members) and hydro-arm CSV (20 members). |
| `2_assimilation/run_crossed_ensemble.py` | Crosses the arms → 600-member parquet + 4 provenance files. |
| `2_assimilation/run_lead_time_forecast_sweep.py` | 18-hour forecast sweep across full test period; outputs per-lead-hour DA and open-loop CSVs. |
| `2_assimilation/run_sweep_all_21_hardcoded_r.py` | Launches `run_lead_time_forecast_sweep.py` for all 21 catchments in parallel (configurable concurrency). |
| `2_assimilation/batch_run_da_on_all_cats.sh` | Batch runner for `run_perturbation_da_on.py` across all 21 catchments. |
| `2_assimilation/batch_run_crossed_all_cats.sh` | Batch runner for `run_crossed_ensemble.py` across all 21 catchments. |

---

## Step 3 — Routing to Gauge

Routes per-catchment runoff (mm/h) through the channel network (t-route
Muskingum-Cunge) to USGS gauge 03463300 at every lead hour for each initialization.

| Script | Description |
|---|---|
| `3_routing/run_route_crossed_ensemble.py` | Routes all 600 members of the crossed ensemble through t-route. Reads 21-catchment parquets; outputs `routed_crossed_ensemble.parquet` (m³/s at gauge). |
| `3_routing/route_lead_time_forecasts.py` | Routes 20-member DA and open-loop lead-time forecast CSVs through t-route. Outputs `routed_leadtime_da_full.parquet` and `routed_leadtime_openloop_full.parquet` for 4c plots. |
| `catchment_run/run_route.py` | Deterministic Muskingum routing (tx-fast-hydrology) for Vrugt and no-Vrugt DA results. |

**Routed results at gauge 03463300:**

| Run | Peak Q (m³/s) | KGE vs Qkrig | KGE vs USGS |
|---|---|---|---|
| DA dynamic Vrugt R | 645.7 | 0.869 | 0.277 |
| DA constant R | 622.5 | 0.789 | 0.222 |
| USGS gauge (truth) | **1885.7** | — | — |
| 600-member p95 | 755.6 | — | — |

The ~2.5× gap between the routed ensemble p95 and the USGS peak is due to Qkrig
underestimating the true gauge during this extreme event — the ensemble captures
uncertainty conditional on the quality of the Qkrig observation.

---

## Step 4 — Evaluate at the Gauge

### 4a — DA skill converging to open loop over 18-hour lead time

| Script | Description |
|---|---|
| `4_evaluation/plot_lead_time_decay.py` | Catchment-level RMSE/KGE vs lead hour: DA starts below open-loop, skill converges by lead 3–6. |
| `4_evaluation/plot_lead_time_decay_gauge.py` | Gauge-level decay curve using routed parquets. |
| `4_evaluation/plot_forecast_error_fixed_target.py` | Error decay viewed from a fixed verification time — shows how skill improves as initialization approaches the target. |
| `4_evaluation/plot_forecast_error_per_init.py` | Per-initialization-time error breakdown across all Helene issue times. |

### 4b — 600-member ensemble vs observations during Helene

| Script | Description |
|---|---|
| `4_evaluation/plot_routed_ensemble_combined.py` | **Main poster panel.** Routed 600-member envelope (5/25/50/75/95th pct) vs USGS obs + Vrugt/no-Vrugt deterministic lines. |
| `4_evaluation/plot_crossed_ensemble.py` | Catchment-level percentile envelope for cat-1016300. |
| `4_evaluation/plot_vrugt_comparison.py` | Vrugt vs no-Vrugt comparison: full test period + Helene zoom. |
| `4_evaluation/plot_da_perturbation_arms.py` | 2a/2b arm spaghetti figures showing ensemble spread by source. |

### 4c — Ensemble mean + spread across all 18-hour forecast cycles during Helene

| Script | Description |
|---|---|
| `4_evaluation/plot_lead_time_reconstructed_timeseries.py` | Pools all forecasts landing on each valid_time; plots median + 5/95th pct for DA and open-loop vs USGS obs. Two outputs: full window and Helene zoom. |
| `4_evaluation/plot_forecast_spaghetti.py` | All forecast trajectories during Helene colored by initialization date (Sep 24–30); DA shaded band + mean, OL dashed mean. |
| `4_evaluation/plot_helene_issue_time_hydrograph.py` | Side-by-side panel comparing one Helene-peak and one low-flow initialization time hydrograph. |

**Evaluation results (gauge 03463300):**

| Metric | DA | Open-loop | Improvement |
|---|---|---|---|
| NSE (Sep 10 – Oct 10 window) | 0.437 | 0.318 | +0.119 |
| NSE (Helene zoom, Sep 24–29) | 0.339 | 0.198 | +0.141 |
| Mean catchment KGE (21 cats) | 0.817 | 0.692 | +0.125 |
| Catchments improving | 21/21 | — | — |

---

## Data Flow

```
v2_true_enkf_pn/{cat-id}_best_params.json   (calibration, all 21 cats)
        |
        v
run_perturbation_da_on.py  -->  {cat-id}_da_forcing_arm.csv   (30 members, mm/h)
                                {cat-id}_da_hydro_arm.csv     (20 members, mm/h)
                                        |
                                        v
                                plot_da_perturbation_arms.py  -->  2a/2b spread figures

run_crossed_ensemble.py    -->  {cat-id}_crossed_ensemble.parquet  (600 members, mm/h)
                                {cat-id}_da_snapshots.parquet      (restart states)
                                {cat-id}_member_manifest.csv       (traceability)
                                {cat-id}_hydro_draw_states.parquet
                                {cat-id}_forcing_draw_sequences.parquet
        |
        v
run_route_crossed_ensemble.py  -->  routed_crossed_ensemble.parquet  (600 members, m³/s)
        |
        v
plot_routed_ensemble_combined.py  -->  helene_ensemble_vs_usgs.png  [4b poster panel]

run_lead_time_forecast_sweep.py  -->  {cat-id}_lead_time_forecasts_da.csv      (20 members)
                                      {cat-id}_lead_time_forecasts_openloop.csv (20 members)
        |
        v
route_lead_time_forecasts.py  -->  routed_leadtime_da_full.parquet       (m³/s at gauge)
                                   routed_leadtime_openloop_full.parquet  (m³/s at gauge)
        |
        v
plot_lead_time_reconstructed_timeseries.py  -->  lead_time_reconstructed_timeseries.png [4c]
plot_forecast_spaghetti.py                  -->  forecast_spaghetti_helene.png           [4c]

run_route.py (Vrugt / no-Vrugt)  -->  routed_Q_test.csv  (deterministic, m³/s)
        |
        v
plot_vrugt_comparison.py  -->  vrugt_vs_novrugt_helene_zoom.png
```

---

## Full Run Order

```bash
# 1. Calibration — run once per catchment; results staged in v2_true_enkf_pn/
python3 1_calibrate/calibrate_catchment_cfe_da_v2.py \
    --cat-id cat-1016300 \
    --forcing-dir  <retro forcing dir> \
    --obs-dir      <kriging obs dir with variance> \
    --cfe-dir      <cfe_py dir> \
    --config-file  <BMI config JSON> \
    --param-bounds <CFE parameter bounds JSON> \
    --out-dir      <output dir>

# 2a/2b. DA-on perturbation arms (all 21 catchments)
bash 2_assimilation/batch_run_da_on_all_cats.sh

# 2d. Crossed 600-member ensemble (all 21 catchments)
bash 2_assimilation/batch_run_crossed_all_cats.sh

# 2c. Lead-time forecast sweep (all 21 catchments, ~overnight)
nohup python3 2_assimilation/run_sweep_all_21_hardcoded_r.py --concurrent 5 \
    > ~/sweep_all_21_master.log 2>&1 &

# 3. Route 600-member ensemble to gauge
nohup python3 3_routing/run_route_crossed_ensemble.py \
    --gpkg    <gage-03463300_subset.gpkg> \
    --ensemble-dir <v2_crossed_ensemble dir> \
    --out-dir <v2_crossed_ensemble_routed dir> \
    > ~/route_crossed.log 2>&1 &

# 3. Route lead-time forecasts to gauge (for 4c plots)
nohup python3 3_routing/route_lead_time_forecasts.py \
    --gpkg        <gage-03463300_subset.gpkg> \
    --leadtime-dir <v2_lead_time_forecast_hardcoded_r dir> \
    --out-dir      <v2_lead_time_forecast_hardcoded_r_routed dir> \
    > ~/route_leadtime.log 2>&1 &

# 3. Route deterministic DA results (Vrugt and no-Vrugt)
python3 catchment_run/run_route.py \
    --gpkg <gage-03463300_subset.gpkg> \
    --results-dir <vrugt DA results dir> \
    --period test --obs-csv <usgs_hourly.csv> --out-dir <out>
python3 catchment_run/run_route.py \
    --gpkg <gage-03463300_subset.gpkg> \
    --results-dir <novrugt DA results dir> \
    --period test --obs-csv <usgs_hourly.csv> --out-dir <out>

# 4. Evaluation plots
python3 4_evaluation/plot_routed_ensemble_combined.py \
    --vrugt-csv <vrugt routed Q> --novrugt-csv <novrugt routed Q> \
    --ensemble-pq <routed_crossed_ensemble.parquet> --out-dir <out>

python3 4_evaluation/plot_lead_time_reconstructed_timeseries.py \
    --route-dir <v2_lead_time_forecast_hardcoded_r_routed> \
    --usgs-csv  <usgs_hourly.csv>

python3 4_evaluation/plot_forecast_spaghetti.py \
    --route-dir <v2_lead_time_forecast_hardcoded_r_routed> \
    --usgs-csv  <usgs_hourly.csv>

python3 4_evaluation/plot_lead_time_decay.py \
    --cat-id cat-1016300 \
    --leadtime-dir <v2_lead_time_forecast dir> \
    --da-dir       <v2_true_enkf_vrugt dir>

python3 4_evaluation/plot_da_perturbation_arms.py \
    --cat-id cat-1016300 \
    --arm-dir  <v2_perturbation_da_on dir> \
    --usgs-csv <usgs_hourly.csv>

python3 4_evaluation/plot_vrugt_comparison.py \
    --vrugt-csv   <vrugt routed Q> \
    --novrugt-csv <novrugt routed Q> \
    --out-dir     <out>
```

---

## Ensemble Traceability

Any member of the 600-member ensemble can be fully traced back to its source:

```python
member_k → forcing_draw_i = k // 20   # which of the 30 met perturbation draws
         → hydro_draw_j   = k % 20    # which of the 20 initial-state draws
```

Look up `(issue_time, hydro_draw_j)` in `_hydro_draw_states.parquet` to get the
exact initial soil moisture, groundwater, and Nash routing states that member used.

Look up `(issue_time, forcing_draw_i, lead_hour)` in `_forcing_draw_sequences.parquet`
to get the exact precip and PET values that member experienced during its forecast.

Load `_da_snapshots.parquet` and call `set_state()` on any row to restart a CFE
model from the exact DA-analyzed state at that initialization time.
