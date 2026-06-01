# Poster Content v2 — Kriging + T-route (Suma's feedback)
# Source: ciroh_hub_qkirg_troute_052526_final.pdf + 4 slides from Battula_CIWRO_CIROH_workshop.pptx

## TITLE
Continental-Scale Streamflow Simulation Using Kriging in the NGIAB-NRDS NextGen Ecosystem

## AUTHORS
Suma Battula¹ · Kunal Sarna² · Sonali Vyas² · Harsha Vemula³ · Arpita Patel³ · Jonathan Frame¹,³
¹Geological Sciences · ²Computer Science · ³Alabama Water Institute — The University of Alabama

---

## BACKGROUND
- The vast majority of the river network remains ungauged — process-based models
  can only be evaluated where USGS gauges exist
- A data-driven, observation-based framework is needed that provides spatially
  complete streamflow estimates with well-characterized uncertainty
- Kriging interpolation between USGS gauged locations is scalable and accurate
  for producing spatially complete streamflow fields (Farmer et al., 2019)
- As a pure data-driven method, kriging serves as a "pseudo-observation" for
  streamflow analysis, NWM calibration, and data assimilation in ungauged basins

---

## APPROACH

### Hourly Streamflow Kriging Across CONUS (from PDF)
- ~7,300 active USGS gauges; instantaneous values aggregated to hourly means
- Spherical variogram model fit at each hour
- Outputs: gridded hourly runoff + kriging error variance fields across CONUS
- Sampled at every catchment centroid in NextGen v2.2 hydrofabric (831,777 catchments)

### NRDS Integration — Operational Pipeline (from PDF)
- Nightly at 00:30 ET: fetches USGS IV discharge → fits kriging field → delivers
  ~13 MB BROTLI-compressed Parquet (all catchments × 24 hours)
- Published at: s3://ciroh-community-ngen-datastream/outputs/qkrig/
- Tracked on NRDS status dashboard alongside other operational datastreams

### Two Evaluation Approaches — South Toe River, Hurricane Helene (from slides)
Both approaches withhold 20% of USGS gauges affected by Hurricane Helene (Sep 2024)
and compare routed streamflow at outlet gauge 03463300 (near Celo, NC):

**Approach A — T-route initialized directly with Qkrig (held-out)**
  Qkrig (held-out) → T-route Muskingum-Cunge → routed Q at 03463300
  Cal KGE=0.607, NSE=0.527 | Test KGE=0.248, NSE=0.416
  Helene routed peak = 554 m³/s (29% of USGS 1886 m³/s)

**Approach B — CFE calibrated on Qkrig, then T-route**
  Qkrig (held-out) → calibrate CFE → CFE runoff → T-route → routed Q
  CFE initialized with NWM operational forcings
  Cal KGE=0.359, NSE=0.372 | Test NSE=0.417
  Helene routed peak = 688 m³/s (36% of USGS 1886 m³/s)

---

## FIGURES

### Fig 1 — CONUS Hourly Kriged Flow + Variogram
Source: PDF Figure 1 / NRDS dashboard screenshot
(https://datastream.ciroh.org/#outputs/qkrig/qkrig.20260519/plots/kriging/)
Caption: Hourly kriged streamflow map and spherical variogram for CONUS —
2026-05-19 00:00 UTC. Hour mean: 0.033 mm/hr. Updated nightly for all
831,777 NextGen catchments.

### Fig 2 — South Toe River: Kriged Runoff Spatial Distribution (held-out)
Source: Slide 1 — "South Toe River Kriged Runoff (held-out)"
Caption: Daily peak kriged flow at each sub-catchment of the South Toe River
hydrofabric, Sep 25–30 2024 (Hurricane Helene). 20% of gauges held out.
Marker = USGS gauge 03463300 (outlet). Landfall/peak on Sep 27.
Color scale: peak flow hour per day (mm/hr).

### Fig 3 — T-route Initialized with Qkrig: Catchment Maps
Source: Slide 3 — "Troute simulated streamflow initialized with Qkrig"
Caption: Routed streamflow per reach (m³/s) from T-route initialized with
held-out kriged runoff, Sep 25–30 2024. Sep 27 outlet peak = 554 m³/s.
Cal KGE=0.607 | Test KGE=0.248 | USGS peak=1886 m³/s.

### Fig 4 — CFE Calibrated on Qkrig + T-route: Catchment Maps
Source: Slide 2 — "CFE calibrated on Qkrig and Troute simulated streamflow"
Caption: Routed streamflow per reach (m³/s) from CFE (calibrated on Qkrig,
initialized with NWM forcings) + T-route, Sep 25–30 2024.
Sep 27 outlet peak = 688 m³/s. Cal KGE=0.359 | Helene routed peak=688 m³/s.

### Fig 5 — Comparison: Qkrig→T-route vs CFE→T-route vs USGS (time series)
Source: Slide 4 — "(Troute_init Qkrig) v/s (CFE cal Qkrig and Troute) simulated Q"
Caption: Hurricane Helene streamflow at gauge 03463300, Sep 20–Oct 4 2024.
Top panel: Routed Qkrig (t-route MC, peak=554 m³/s) vs area-weighted Qkrig
(peak=761 m³/s) vs USGS obs (peak=1886 m³/s).
Bottom panel: CFE + t-route Muskingum-Cunge (peak=688 m³/s) vs Qkrig vs USGS.
Both approaches capture peak timing and recession; magnitude underestimated.

---

## KEY FINDINGS
- Hourly streamflow kriging is operational on NRDS — spatially complete estimates
  for all 831,777 NextGen catchments delivered nightly
- Qkrig (held-out) can serve as pseudo-observations to calibrate CFE in ungauged
  regions and enable data assimilation for ungauged streamflow prediction
- Both approaches capture Helene peak TIMING and recession behavior:
    · Qkrig → T-route: Test KGE=0.248, peak=554 m³/s (29% of USGS)
    · CFE + T-route:   peak=688 m³/s (36% of USGS), better magnitude capture
- CFE simulations with T-route show promise — combining process-based modeling
  with kriging pseudo-observations improves peak magnitude over direct kriging
- Viable framework for streamflow simulation (lag 1–24 hrs) in ungauged basins
  within the NextGen water resources modeling framework

---

## ONGOING WORK
- Conditioning CFE model states on Qkrig using **Ensemble Kalman Filter (EnKF)**:
  · Update hydrologic states (groundwater storage, soil moisture)
  · Perturb precipitation forcing
- Improve peak flow prediction at ungauged locations
- Quantify streamflow forecast uncertainty during extreme events

---

## FUTURE WORK (from PDF)
- Integrate kriged streamflow into NextGen and evaluate ensemble forecasts
  during Helene
- Dynamic variogram parameter calibration
- Calibrate kriging variance vs observed residuals
- Publish 1979–2025 hourly historical reanalysis (consistent sill=1.5, grid=100)

---

## LINKS & DATA
- Kriging repo:     github.com/DualEarth/qkrig
- T-route repo:     github.com/sonalivyascse19-stack/t-route
- Live NRDS:        datastream.ciroh.org/#outputs/qkrig/
- Reanalysis data:  streamflow-interpolation-noaa14.s3.amazonaws.com/

---

## LAYOUT SUGGESTION (5-column Alabama template)
Col 1: Background + Approach text
Col 2: Fig 1 (CONUS map) + Fig 2 (Kriged runoff spatial maps)
Col 3: Fig 3 (Qkrig→T-route maps) + Fig 4 (CFE→T-route maps)
Col 4: Fig 5 (time series comparison — this is the main result, give it space)
Col 5: Key Findings + Ongoing Work + Future Work + Links

## NOTES FOR POSTER MAKER
- The 4 slides from Suma are Figures 2, 3, 4, and 5
- Fig 5 (time series, Slide 4) is the MAIN RESULT — give it the most space
- Use Alabama template: crimson header, NOAA + CIROH logos at bottom
- Funding: "This research was supported by CIROH with funding under award
  NA22NWS4320003 from the NOAA Cooperative Institute Program."
- Do NOT use the cat-1016300 DA forcing arm figure — wrong project
