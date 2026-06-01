# Poster Content — Kriging + T-route (CIROH Hub)

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
- Kriging interpolation between USGS gauged locations is scalable and accurate for
  producing spatially complete streamflow fields
- As a pure data-driven method, kriging cannot forecast directly — but serves as a
  valuable pseudo-observation for analysis, reconstruction, and data assimilation

---

## APPROACH

### Hourly Streamflow Kriging Across CONUS
- ~7,300 active USGS gauges, instantaneous values aggregated to hourly means
- Spherical variogram model fit at each hour
- Outputs: gridded hourly runoff + kriging error variance fields across CONUS
- Sampled at every catchment centroid in the NextGen v2.2 hydrofabric (831,777 catchments)

### Integration into the NextGen Research Data Stream (NRDS)
- Nightly pipeline at 00:30 ET — fetches USGS IV discharge, fits kriging field,
  delivers ~13 MB Parquet (all 831,777 catchments × 24 hours)
- Published at: s3://ciroh-community-ngen-datastream/outputs/qkrig/
- Tracked on the NRDS status dashboard alongside other operational datastreams

### T-route Streamflow Simulation with Held-Out Kriging
- To test utility in ungauged basins: 20% of USGS gauges in the South Toe River
  watershed withheld during Hurricane Helene (September 2024)
- Kriged runoff from held-out configuration used to initialize T-route
  (NOAA Office of Water Prediction, Muskingum-Cunge routing)
- Routed streamflow compared against USGS at gauge 03463300 (near Celo, NC)
- Result: peak timing and recession captured during Helene

---

## FIGURES

### Figure 1 — CONUS Kriging Map + Variogram
Source: Screenshot from NRDS dashboard (PDF page 2)
(https://datastream.ciroh.org/#outputs/qkrig/qkrig.20260519/plots/kriging/)
Caption: Hourly kriged streamflow and spherical variogram for CONUS — 2026-05-19
00:00 UTC. Hour mean: 0.033 mm/hr. Each night this map updates for all 831,777
NextGen catchments.

### Figure 2 — T-route South Toe River (Held-Out, Hurricane Helene)
Source: Screenshot from PDF page 3
Caption: T-route simulation initialized from held-out kriged runoff at the South
Toe River hydrofabric during Hurricane Helene, Sep 25–30, 2024. Outlet gauge
03463300 (near Celo, NC). Peak timing and recession captured; magnitude
underestimated (routed peak 554 m³/s vs USGS 1886 m³/s).
Metrics: Cal KGE=0.407, NSE=0.527 | Test KGE=0.248, NSE=0.416

---

## KEY FINDINGS
- Hourly streamflow kriging is now operational in the NRDS — delivering spatially
  complete estimates for all 831,777 NextGen hydrofabric catchments nightly
- Kriging + T-route captures peak timing and recession during Hurricane Helene in
  a 20% held-out gauge configuration (ungauged basin simulation)
- Test KGE = 0.248 for the held-out South Toe River outlet
- Viable approach for streamflow simulation (lag times 1–24 hours) in ungauged
  basins within the NextGen water resources modeling framework

---

## FUTURE WORK
- Integrate kriged streamflow into NextGen Water Resources Modeling Framework and
  evaluate ensemble forecasts during Helene
- Improve peak flow prediction and generalization at ungauged locations
- Enhance peak flow capture for downstream decision support
- Quantify streamflow forecast uncertainty during extreme events
- Extend DA benchmarking with EnKF using kriged pseudo-observations

---

## LINKS & DATA
- Kriging repo:     https://github.com/DualEarth/qkrig
- T-route repo:     https://github.com/sonalivyascse19-stack/t-route
- Live NRDS stream: https://datastream.ciroh.org/#outputs/qkrig/
- Reanalysis data:  https://streamflow-interpolation-noaa14.s3.amazonaws.com/

---

## NOTES FOR POSTER MAKER
- Use Alabama template (crimson header, NOAA + CIROH logos at bottom)
- Two figures only: CONUS map (left/center) + T-route South Toe panels (right)
- Do NOT include the cat-1016300 DA forcing arm figure — that is from a
  different project (EnKF data assimilation) and does not belong here
- Funding line: "This research was supported by CIROH with funding under award
  NA22NWS4320003 from the NOAA Cooperative Institute Program."
