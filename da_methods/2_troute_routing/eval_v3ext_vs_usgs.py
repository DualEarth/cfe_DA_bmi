#!/usr/bin/env python3
"""
eval_v3ext_vs_usgs.py -- Evaluate v3-ext routed forecasts against USGS obs.

For each gauge:
  - Loads routed_forecast_leadtime_da.parquet (ensemble mean over all issues)
  - Loads USGS obs from usgs_obs_12_20261012_raw
  - Computes KGE (ensemble mean vs obs) over the overlapping period
  - Prints a per-gauge summary table

Also computes skill vs open-loop (CRPSS proxy using KGE).

USAGE
  python eval_v3ext_vs_usgs.py
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROUTED_DIR = Path("/mnt/disk2/svyas_clean_run/da_al_storm_2026_v3_ext/routed")
USGS_DIR   = Path("/mnt/disk2/al_storm_2026/usgs_obs_12_20261012_raw")

AL_GAUGES = [
    "02361000", "02369800", "02371500", "02372250", "02374500", "02408540",
    "02422500", "02450250", "02464000", "02465493", "02469800", "03574500",
]


def kge(sim, obs):
    """Kling-Gupta Efficiency (Gupta 2009). Returns scalar."""
    r = np.corrcoef(sim, obs)[0, 1]
    alpha = sim.std() / obs.std()
    beta  = sim.mean() / obs.mean()
    return 1.0 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2)


def eval_gauge(gauge):
    gdir = ROUTED_DIR / gauge

    # ── load DA forecast (all issue times combined into one timeseries) ───────
    da_pq = gdir / "routed_forecast_leadtime_da.parquet"
    ol_pq = gdir / "routed_forecast_leadtime_openloop.parquet"
    if not da_pq.exists():
        return gauge, None, None, None, "no DA parquet"

    da = pd.read_parquet(da_pq)
    da["valid_time"] = pd.to_datetime(da["issue_time"]) + pd.to_timedelta(da["lead_hour"], unit="h")
    mcols = [c for c in da.columns if c.startswith("member_")]

    # ensemble mean per valid_time (deduplicate: keep earliest issue = most lead)
    da = da.sort_values(["valid_time", "lead_hour"])
    da_mean = (da.groupby("valid_time")[mcols]
                 .first()
                 .mean(axis=1)
                 .rename("q_da"))

    # open-loop ensemble mean
    ol_mean = None
    if ol_pq.exists():
        ol = pd.read_parquet(ol_pq)
        ol["valid_time"] = pd.to_datetime(ol["issue_time"]) + pd.to_timedelta(ol["lead_hour"], unit="h")
        ol_cols = [c for c in ol.columns if c.startswith("member_")]
        ol = ol.sort_values(["valid_time", "lead_hour"])
        ol_mean = (ol.groupby("valid_time")[ol_cols]
                     .first()
                     .mean(axis=1)
                     .rename("q_ol"))

    # ── load USGS obs ─────────────────────────────────────────────────────────
    obs_csv = USGS_DIR / f"{gauge}.csv"
    if not obs_csv.exists():
        return gauge, None, None, None, "no USGS csv"

    obs = pd.read_csv(obs_csv, parse_dates=["time"]).set_index("time")
    obs.index = obs.index.tz_localize(None) if obs.index.tz else obs.index
    obs = obs["q_m3s"].rename("q_obs")

    # ── align on hourly timestamps ────────────────────────────────────────────
    da_mean.index = da_mean.index.floor("h")
    obs.index     = obs.index.floor("h")

    merged = pd.concat([da_mean, obs], axis=1, join="inner").dropna()
    if len(merged) < 5:
        return gauge, None, None, None, f"too few overlap rows ({len(merged)})"

    sim_vals = merged["q_da"].values
    obs_vals = merged["q_obs"].values

    if obs_vals.std() < 1e-6 or sim_vals.std() < 1e-6:
        return gauge, None, None, None, "zero variance"

    kge_da = kge(sim_vals, obs_vals)

    # open-loop KGE (skill denominator)
    kge_ol = None
    if ol_mean is not None:
        ol_mean.index = ol_mean.index.floor("h")
        m2 = pd.concat([ol_mean, obs], axis=1, join="inner").dropna()
        if len(m2) >= 5 and m2["q_obs"].std() > 1e-6 and m2["q_ol"].std() > 1e-6:
            kge_ol = kge(m2["q_ol"].values, m2["q_obs"].values)

    return gauge, kge_da, kge_ol, len(merged), "ok"


if __name__ == "__main__":
    rows = []
    for g in AL_GAUGES:
        gauge, kge_da, kge_ol, n, status = eval_gauge(g)
        rows.append({"gauge": gauge, "KGE_DA": kge_da, "KGE_OL": kge_ol,
                     "n_pairs": n, "status": status})
        tag = f"  KGE_DA={kge_da:.3f}" if kge_da is not None else ""
        tag += f"  KGE_OL={kge_ol:.3f}" if kge_ol is not None else ""
        print(f"  {gauge}: {status}{tag}  (n={n})")

    df = pd.DataFrame(rows)
    valid = df[df["KGE_DA"].notna()]
    if len(valid):
        print(f"\n── Summary (n={len(valid)} gauges) ──────────────────────────")
        print(f"  DA   KGE  median={valid['KGE_DA'].median():.3f}  "
              f"mean={valid['KGE_DA'].mean():.3f}  "
              f"min={valid['KGE_DA'].min():.3f}  max={valid['KGE_DA'].max():.3f}")
        if valid["KGE_OL"].notna().any():
            ol = valid["KGE_OL"].dropna()
            print(f"  OL   KGE  median={ol.median():.3f}  "
                  f"mean={ol.mean():.3f}  "
                  f"min={ol.min():.3f}  max={ol.max():.3f}")
        print()
        print(df[["gauge", "KGE_DA", "KGE_OL", "n_pairs"]].to_string(index=False))
