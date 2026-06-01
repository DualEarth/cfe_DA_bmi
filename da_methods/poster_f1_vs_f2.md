# Poster Content — F1 vs F2 EnKF DA Comparison

## Title
Observation Error Formulation Controls Ensemble Kalman Filter Performance During
Extreme Flooding: A Hurricane Helene Case Study

## Authors
Sonali Vyas, Suma Battula, Jonathan Frame
Department of Computer Science / Geological Sciences / Alabama Water Institute
The University of Alabama, Tuscaloosa, AL

---

## Background
- Process-based hydrological models carry structural and forcing uncertainties that
  are difficult to evaluate in ungauged locations
- Data assimilation (DA) via the Ensemble Kalman Filter (EnKF) can correct model
  states toward observations at each timestep — but performance depends critically
  on how observation error variance (R) is specified
- Hurricane Helene (September 2024) caused catastrophic flooding in western NC;
  USGS peak at South Toe River (03463300) reached 1885.7 m³/s — an extreme test
  for any DA system
- Two fundamentally different R formulations are evaluated: flow-scaled
  (heteroscedastic) vs constant — using a controlled experiment where only R differs

---

## Study Site & Model
- Gauge: USGS 03463300 — South Toe River Near Celo, NC
- Watershed: 21 NWM catchments · 113.18 km² · outlet reach wb-1016283
- Model: CFE (Conceptual Functional Equivalent) via BMI interface
- DA method: EnKF assimilating Qkrig kriged streamflow observations (hourly)
- Test period: October 2023 – October 2024 (13 months, includes Helene)
- Ensemble: 600 members (30 forcing × 20 hydro-state perturbations)
- Forecast: 18-hour rolling forecast cycles initialized every hour

---

## Approach

### EnKF Update
At each hourly timestep:
  K(t)  = P(t) / (P(t) + R(t))                   Kalman gain
  x̂(t)  = x(t) + K(t) · (y_obs(t) − H·x(t))     state update

P = ensemble state variance · y_obs = Qkrig · R = observation error variance

### Experiment F1 — Vrugt 2005 Heteroscedastic R
  R(t) = (0.10 × y_obs(t))² + 0.001 × σ²_krig(t)

R scales with flow magnitude. At Helene peak (~1886 m³/s): R ≈ 35,000.
Kalman gain K collapses to near zero — DA update is suppressed exactly when
correction matters most.

### Experiment F2 — Fixed R = 0.07
  R = 0.07 (constant)

K = P / (P + 0.07) stays near 1 throughout the simulation.
DA update is equally aggressive at low and high flows — including the Helene peak.

### Controlled Comparison
F1 and F2 share: same RNG seed (hash(cat_id)), same obs dataset (static σ²≈4.17),
same 21 catchments, same calibrated CFE parameters.
Only R formula differs — making F1 vs F2 a clean controlled experiment.

---

## Key Results

| Metric            | F1 — Vrugt   | F2 — Fixed R=0.07 |
|---|---|---|
| Full period KGE   | +0.277       | +0.503            |
| Full period NSE   | +0.555       | +0.163            |
| Helene KGE        | +0.213       | +0.439            |
| Helene NSE        | +0.459       | -0.009            |
| Helene peak       | 645.7 m³/s (34% of USGS) | 1227.1 m³/s (65% of USGS) |

USGS Helene peak: 1885.7 m³/s

---

## Figures

### Fig 1 — Ensemble vs USGS (F1, Vrugt)
File: pptx_figures/helene_ensemble_vs_usgs.png
Caption: 600-member ensemble streamflow vs USGS at gauge 03463300 during Hurricane
Helene. Ensemble spread captures variability but peak is suppressed (34% of USGS)
due to Kalman gain collapse under Vrugt R formula.

### Fig 2 — Ensemble vs USGS (two-panel comparison F1 vs F2)
File: pptx_figures/helene_ensemble_twopanel.png
Caption: Side-by-side comparison of F1 (Vrugt) and F2 (Fixed R) ensemble spread
during Helene. F2 tracks the rising limb and peak far more aggressively.

### Fig 3 — All 4 R formulas compared during Helene
File: pptx_figures/compare_all_folders_helene.png
Caption: Routed streamflow at outlet for all four R formulations. F2 (fixed R=0.07)
best captures the Helene peak. F1 (Vrugt), F3, and F4 all suppress the peak due
to high R at extreme flows.

### Fig 4 — 18-hour forecast lead time decay
File: pptx_figures/lead_time_reconstructed_timeseries_helene.png
Caption: Reconstructed timeseries from 18-hour rolling forecast cycles during
Helene. Shorter lead times track observations more closely; skill decays with lead
time as the ensemble spreads.

### Fig 5 — Ensemble forcing perturbation arm
File: pptx_figures/cat-1016300_2a_forcing_arm_helene.png
Caption: Forcing arm perturbation ensemble (30 members, DA on) for catchment
1016300 during Helene. Shaded = member spread; line = median per init time.
Illustrates ensemble design and spread at peak event.

---

## Key Findings
- Fixed R=0.07 (F2) outperforms Vrugt R (F1) for KGE and Helene peak capture
- Vrugt formula delivers the best NSE (+0.555) — better overall hydrograph shape —
  but collapses the Kalman gain at peak flows (R ≈ 35,000 at Helene peak)
- A fundamental tradeoff exists: heteroscedastic R improves low-to-mid flow fit
  but suppresses DA updates during extreme events when correction matters most
- F2 captures 65% of the Helene peak (1227 m³/s) vs 34% for F1 (646 m³/s) —
  nearly 2x improvement in peak capture from a single design choice
- 18-hour ensemble forecasts initialized with DA-analyzed states show measurable
  skill during Helene with spread that brackets the rising limb

---

## Future Work
- Re-run F3/F4 with hash-based seed and static obs dataset for a fully controlled
  4-way comparison of all R formulations
- Test adaptive R formulations that switch between heteroscedastic and fixed
  depending on flow regime or event classification
- Extend to multiple watersheds to assess generalizability of fixed vs flow-scaled R
- Integrate EnKF-DA with operational NRDS kriging stream for real-time ungauged
  basin forecasting

---

## Links & Data
- DA repository: https://github.com/DualEarth/cfe_DA_bmi
- PR (branch feature/da-v2-enkf): https://github.com/DualEarth/cfe_DA_bmi/pull/1
- Kriging observations (Qkrig): https://github.com/DualEarth/qkrig

---

## Figures to use (in order of priority)
1. helene_ensemble_twopanel.png       — F1 vs F2 side-by-side (main result)
2. compare_all_folders_helene.png     — all 4 R formulas, Helene period
3. lead_time_reconstructed_timeseries_helene.png — 18-hr forecast skill
4. helene_ensemble_vs_usgs.png        — 600-member ensemble detail
5. cat-1016300_2a_forcing_arm_helene.png — ensemble design
