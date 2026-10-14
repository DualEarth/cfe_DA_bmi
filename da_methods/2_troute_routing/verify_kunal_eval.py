#!/usr/bin/env python3
"""
verify_kunal_eval.py -- Independently replicate Kunal's eval_da_vs_usgs_v3_ext.csv
and report any discrepancies > tolerance.

Reads:
  /mnt/disk2/svyas_clean_run/da_al_storm_2026_v3_ext/routed/<gauge>/
      routed_forecast_leadtime_da.parquet
      routed_forecast_leadtime_openloop.parquet
  /mnt/disk2/al_storm_2026/usgs_obs_12_20261012_raw/<gauge>.csv
  /home/svyas/Downloads/eval_da_vs_usgs_v3_ext.csv   (Kunal's reference)

Outputs:
  /tmp/verify_kunal_eval.csv    (our replication)
  /tmp/verify_kunal_diff.csv    (rows where |delta_kge| > 0.05 or |delta_nse| > 0.05)
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROUTED_DIR  = Path("/mnt/disk2/svyas_clean_run/da_al_storm_2026_v3_ext/routed")
USGS_DIR    = Path("/mnt/disk2/al_storm_2026/usgs_obs_12_20261012_raw")
KUNAL_CSV   = Path("/home/svyas/Downloads/eval_da_vs_usgs_v3_ext.csv")
OUT_CSV     = Path("/tmp/verify_kunal_eval.csv")
DIFF_CSV    = Path("/tmp/verify_kunal_diff.csv")

AL_GAUGES = [
    "02361000","02369800","02371500","02372250","02374500","02408540",
    "02422500","02450250","02464000","02465493","02469800","03574500",
]

KGE_TOL = 0.05
NSE_TOL = 0.05


# ── metric helpers ────────────────────────────────────────────────────────────
def nse(sim, obs):
    return 1.0 - np.sum((obs - sim)**2) / np.sum((obs - np.mean(obs))**2)

def kge(sim, obs):
    r     = np.corrcoef(sim, obs)[0, 1]
    alpha = sim.std() / obs.std()
    beta  = sim.mean() / obs.mean()
    return 1.0 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2)

def mape(sim, obs):
    mask = obs > 0
    return float(np.mean(np.abs((obs[mask] - sim[mask]) / obs[mask])) * 100)

def bias(sim, obs):
    return float(sim.mean() / obs.mean()) if obs.mean() > 0 else np.nan

def cover_5_95(ens_vals, obs_vals):
    """ens_vals: (n_times, n_members), obs_vals: (n_times,)"""
    lo = np.percentile(ens_vals, 5,  axis=1)
    hi = np.percentile(ens_vals, 95, axis=1)
    return float(np.mean((obs_vals >= lo) & (obs_vals <= hi)))


# ── load data for one gauge ───────────────────────────────────────────────────
def load_gauge_data(gauge):
    gdir = ROUTED_DIR / gauge

    def load_fc(tag):
        pq = gdir / f"routed_forecast_leadtime_{tag}.parquet"
        if not pq.exists():
            return None
        df = pd.read_parquet(pq)
        df["issue_time"] = pd.to_datetime(df["issue_time"])
        df["valid_time"] = df["issue_time"] + pd.to_timedelta(df["lead_hour"], unit="h")
        return df

    da = load_fc("da")
    ol = load_fc("openloop")

    obs_csv = USGS_DIR / f"{gauge}.csv"
    if not obs_csv.exists():
        return None, None, None
    obs = (pd.read_csv(obs_csv, parse_dates=["time"])
             .set_index("time")["q_m3s"])
    obs.index = obs.index.tz_localize(None) if obs.index.tz else obs.index
    obs.index = obs.index.floor("h")
    return da, ol, obs


# ── eval one gauge / one lead / one period ────────────────────────────────────
def eval_block(df, obs, issue_mask):
    """
    df       : full forecast parquet (all issues, all leads already filtered to one lead)
    obs      : Series indexed by hourly timestamps (q_m3s)
    issue_mask : boolean mask on df rows selecting the period
    """
    sub = df[issue_mask].copy()
    mcols = [c for c in sub.columns if c.startswith("member_")]
    sub["valid_time"] = sub["valid_time"].dt.floor("h")

    sub = sub.join(obs.rename("q_obs"), on="valid_time").dropna(subset=["q_obs"])
    if len(sub) < 3:
        return None

    sim_arr = sub[mcols].values.astype(float)       # (n, 100)
    sim_mean = sim_arr.mean(axis=1)
    obs_arr  = sub["q_obs"].values.astype(float)

    if obs_arr.std() < 1e-9 or sim_mean.std() < 1e-9:
        return None

    return {
        "n":          len(sub),
        "nse":        nse(sim_mean, obs_arr),
        "kge":        kge(sim_mean, obs_arr),
        "mape":       mape(sim_mean, obs_arr),
        "bias":       bias(sim_mean, obs_arr),
        "cover_5_95": cover_5_95(sim_arr, obs_arr),
    }


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    rows = []

    for gauge in AL_GAUGES:
        da, ol, obs = load_gauge_data(gauge)
        if da is None:
            print(f"  {gauge}: skipped (no data)")
            continue

        # infer storm period: last 14 unique issue_times
        all_issues  = sorted(da["issue_time"].unique())
        storm_issues = set(all_issues[-14:])

        for lead in range(1, 19):
            da_lead = da[da["lead_hour"] == lead]
            ol_lead = ol[ol["lead_hour"] == lead] if ol is not None else None

            for period, mask_fn in [
                ("all",   lambda df: pd.Series([True] * len(df), index=df.index)),
                ("storm", lambda df: df["issue_time"].isin(storm_issues)),
            ]:
                for tag, fc_df in [("DA", da_lead),
                                   ("open loop", ol_lead),
                                   ("persistence", da_lead)]:
                    if fc_df is None or len(fc_df) == 0:
                        continue

                    mask = mask_fn(fc_df)
                    sub = fc_df[mask].copy()
                    mcols = [c for c in sub.columns if c.startswith("member_")]
                    sub["valid_time"] = sub["valid_time"].dt.floor("h")
                    sub = sub.join(obs.rename("q_obs"), on="valid_time").dropna(subset=["q_obs"])

                    if len(sub) < 3:
                        continue

                    obs_arr = sub["q_obs"].values.astype(float)

                    if tag == "persistence":
                        # persistence = obs at issue_time (lead-0 value)
                        issue_obs = sub["issue_time"].dt.floor("h").map(
                            obs.reindex(sub["issue_time"].dt.floor("h")).values
                            if False else obs
                        )
                        # map each row's issue_time to obs value
                        pers_vals = sub["issue_time"].dt.floor("h").apply(
                            lambda t: obs.get(t, np.nan)
                        ).values.astype(float)
                        valid = ~np.isnan(pers_vals) & ~np.isnan(obs_arr)
                        if valid.sum() < 3:
                            continue
                        sim_mean = pers_vals[valid]
                        obs_arr2 = obs_arr[valid]
                        sim_arr  = sim_mean[:, None]
                    else:
                        sim_arr  = sub[mcols].values.astype(float)
                        sim_mean = sim_arr.mean(axis=1)
                        obs_arr2 = obs_arr

                    if obs_arr2.std() < 1e-9 or sim_mean.std() < 1e-9:
                        continue

                    rows.append({
                        "gauge":       gauge,
                        "period":      period,
                        "lead":        lead,
                        "product":     tag,
                        "n":           len(obs_arr2),
                        "nse":         nse(sim_mean, obs_arr2),
                        "kge":         kge(sim_mean, obs_arr2),
                        "mape":        mape(sim_mean, obs_arr2),
                        "bias":        bias(sim_mean, obs_arr2),
                        "cover_5_95":  cover_5_95(sim_arr, obs_arr2),
                    })

        print(f"  {gauge}: done")

    our = pd.DataFrame(rows)
    our.to_csv(OUT_CSV, index=False)
    print(f"\nWrote: {OUT_CSV}  ({len(our)} rows)")

    # ── diff against Kunal ───────────────────────────────────────────────────
    if not KUNAL_CSV.exists():
        print(f"Kunal CSV not found at {KUNAL_CSV} — skipping diff")
        return

    ref = pd.read_csv(KUNAL_CSV, dtype={"gauge": str})
    ref["gauge"] = ref["gauge"].str.zfill(8)   # restore leading zeros
    # rename Kunal columns to match ours
    ref = ref.rename(columns={"kge": "kge_ref", "nse": "nse_ref", "bias": "bias_ref",
                               "mape": "mape_ref", "cover_5_95": "cover_ref",
                               "n": "n_ref"})

    merged = our.merge(ref, on=["gauge","period","lead","product"], how="outer",
                       suffixes=("","_ref"))
    merged["delta_kge"] = (merged["kge"] - merged["kge_ref"]).abs()
    merged["delta_nse"] = (merged["nse"] - merged["nse_ref"]).abs()
    merged["delta_n"]   = (merged["n"]   - merged["n_ref"]).abs()

    diffs = merged[(merged["delta_kge"] > KGE_TOL) |
                   (merged["delta_nse"] > NSE_TOL) |
                   (merged["delta_n"]   > 0)]
    diffs.to_csv(DIFF_CSV, index=False)
    print(f"Diffs (|ΔKGE|>{KGE_TOL} or |ΔNSE|>{NSE_TOL} or Δn>0): {len(diffs)} rows → {DIFF_CSV}")

    if len(diffs) == 0:
        print("  ✓ All metrics match within tolerance — Kunal's eval verified.")
    else:
        print("\n  Top discrepancies:")
        cols = ["gauge","period","lead","product","n","n_ref","kge","kge_ref","delta_kge","delta_n"]
        print(diffs[cols].sort_values("delta_kge", ascending=False).head(20).to_string(index=False))


if __name__ == "__main__":
    main()
