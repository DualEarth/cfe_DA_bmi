#!/usr/bin/env python3
"""
plot_forecast_all_gauges.py -- Spaghetti-fan forecast figures for all 12 Alabama
storm gauges.  Style matches the Helene 03456500 reference figure:
  - Oct 1–Oct 9: DA analysis period (routed full trajectory, shaded ensemble band)
  - Oct 8–Oct 10: 18h ensemble forecast fans, one fan per issue, colored cool→warm
  - DA ensemble mean  (solid black)
  - open-loop mean    (dashed black)
  - USGS obs          (black filled circles)
  - vertical dashed line at first forecast issue (transition marker)
  - white background, colorbar on right

Reads (in <OUT_BASE>/<gauge>/)
  routed_analysis_da.parquet          columns: time, member_0000..  (m3/s)
  routed_analysis_ol.parquet          same (optional)
  routed_forecast_leadtime_da.parquet columns: issue_time, lead_hour, member_0000..
  routed_forecast_leadtime_openloop.parquet (optional)
  gauge_<gauge>_forecast18h.parquet   fallback legacy format

Writes
  <OUT_BASE>/<gauge>/gauge_<gauge>_spaghetti.png
  <OUT_BASE>/all_gauges_spaghetti.png

MULTIPLE ISSUE TIMES
  Forecast parquets with issue_time + lead_hour are used directly; they are
  grouped by issue_time and colored cool→warm (early→late).
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import matplotlib.cm as mcm

OUT_BASE = Path("/mnt/disk2/svyas_clean_run/da_al_storm_2026_v3_ext/routed")
USGS_DIR = Path("/mnt/disk2/al_storm_2026/usgs_obs_12_20261012_raw")

AL_GAUGES = [
    "02361000", "02369800", "02371500", "02372250", "02374500", "02408540",
    "02422500", "02450250", "02464000", "02465493", "02469800", "03574500",
]

# ── Color map (matches Helene figure: cool=early issue, warm=late issue) ──────
ISSUE_CMAP        = matplotlib.colormaps["rainbow"]
MEAN_KW           = dict(color="black", lw=2.2, zorder=10)
OL_MEAN_KW        = dict(color="black", lw=2.2, ls="--", zorder=9)
OBS_KW            = dict(color="black", s=22, zorder=11, linewidths=0)
MEMBER_LW         = 0.18
MEMBER_ALPHA      = 0.28       # thin hairline strands on white background
MAX_MEMBERS       = 600
ANALYSIS_DA_COLOR = "#1a6faf"   # blue for DA analysis band
ANALYSIS_OL_COLOR = "#888888"   # grey for OL analysis band
PLOT_START        = pd.Timestamp("2026-10-01")   # extend x-axis back to Oct 1


def load_analysis_parquet(gauge_dir: Path, tag: str):
    """
    Load routed_analysis_{tag}.parquet → (times, values_array).
    Returns (dates, mean, p5, p95) or None if file missing.
    tag: 'da' or 'ol'
    """
    pq = gauge_dir / f"routed_analysis_{tag}.parquet"
    if not pq.exists():
        return None
    df = pd.read_parquet(pq)
    dates  = pd.to_datetime(df["time"])
    mcols  = [c for c in df.columns if c.startswith("member_")]
    vals   = df[mcols].values.astype(float)
    return dates, vals.mean(axis=1), np.percentile(vals, 5, axis=1), np.percentile(vals, 95, axis=1)


def load_issue_parquets(gauge_dir: Path, gauge: str):
    """
    Return list of (issue_label, df) sorted oldest→newest.
    Checks for timestamped files first, then routed_forecast_leadtime_da.parquet,
    then falls back to plain gauge_<gauge>_forecast18h.parquet.
    """
    stamped = sorted(gauge_dir.glob(f"gauge_{gauge}_forecast18h_*.parquet"))
    if stamped:
        pairs = []
        for p in stamped:
            label = p.stem.split("_")[-1]
            try:
                ts = pd.Timestamp(label)
            except Exception:
                ts = pd.Timestamp("1900-01-01")
            pairs.append((ts, label, p))
        pairs.sort(key=lambda x: x[0])
        return [(lbl, pd.read_parquet(p)) for _, lbl, p in pairs]

    routed = gauge_dir / "routed_forecast_leadtime_da.parquet"
    if routed.exists():
        df = pd.read_parquet(routed)
        df["valid_time"] = pd.to_datetime(df["issue_time"]) + pd.to_timedelta(df["lead_hour"], unit="h")
        mcols = [c for c in df.columns if c.startswith("member_")]
        pairs = []
        for it, grp in df.groupby("issue_time"):
            lbl = pd.Timestamp(it).strftime("%Y-%m-%dT%H")
            sub = grp[["valid_time"] + mcols].reset_index(drop=True)
            pairs.append((pd.Timestamp(it), lbl, sub))
        pairs.sort(key=lambda x: x[0])
        return [(lbl, sub) for _, lbl, sub in pairs]

    plain = gauge_dir / f"gauge_{gauge}_forecast18h.parquet"
    if plain.exists():
        return [("2026-10-08T12", pd.read_parquet(plain))]
    return []


def plot_one_gauge(gauge, ax=None, standalone=False, no_analysis=False):
    """
    Draw the spaghetti figure for one gauge.
    ax=None → create a new figure (standalone per-gauge mode).
    Returns (fig, ax) or (None, ax) in multi-panel mode.
    """
    gauge_dir = OUT_BASE / gauge
    issues = load_issue_parquets(gauge_dir, gauge)
    if not issues:
        if ax is not None:
            ax.set_title(f"{gauge}  (no data)", fontsize=9, color="#888888")
            ax.axis("off")
        return None, ax

    n_issues = len(issues)
    norm = mcolors.Normalize(vmin=0, vmax=max(n_issues - 1, 1))

    if ax is None:
        fig, ax = plt.subplots(figsize=(18, 7))
        standalone = True
    else:
        fig = ax.figure

    ax.set_facecolor("white")

    # ── analysis period Oct 1–Oct 9: shaded band + mean ─────────────────────
    an_da = None if no_analysis else load_analysis_parquet(gauge_dir, "da")
    an_ol = None if no_analysis else load_analysis_parquet(gauge_dir, "ol")

    if an_ol is not None:
        t_ol, mean_ol, p5_ol, p95_ol = an_ol
        ax.fill_between(t_ol, p5_ol, p95_ol,
                        color=ANALYSIS_OL_COLOR, alpha=0.12, zorder=1)
        ax.plot(t_ol, mean_ol,
                color=ANALYSIS_OL_COLOR, lw=1.6, ls="--", zorder=5,
                label="OL analysis (ens mean)")

    if an_da is not None:
        t_da, mean_da, p5_da, p95_da = an_da
        ax.fill_between(t_da, p5_da, p95_da,
                        color=ANALYSIS_DA_COLOR, alpha=0.15, zorder=2)
        ax.plot(t_da, mean_da,
                color=ANALYSIS_DA_COLOR, lw=2.0, zorder=6,
                label="DA analysis (ens mean)")

    # ── vertical line at first forecast issue time ───────────────────────────
    first_issue = pd.to_datetime(issues[0][1]["valid_time"].iloc[0])
    ax.axvline(first_issue, color="#666666", lw=0.8, ls=":", zorder=4, alpha=0.7)

    # ── member spaghetti lines — one fan per issue time ──────────────────────
    for issue_idx, (issue_label, df) in enumerate(issues):
        dates = pd.to_datetime(df["valid_time"])
        mcols = [c for c in df.columns if c.startswith("member_")]
        q     = df[mcols].values.astype(float)   # (n_leads, n_members)

        color = ISSUE_CMAP(norm(issue_idx))

        stride = max(1, q.shape[1] // MAX_MEMBERS)
        for mi in range(0, q.shape[1], stride):
            ax.plot(dates, q[:, mi],
                    color=color, lw=MEMBER_LW, alpha=MEMBER_ALPHA,
                    zorder=3, solid_capstyle="round", rasterized=True)

    # ── DA ensemble mean (use last / latest issue) ────────────────────────────
    _, last_df = issues[-1]
    dates_last = pd.to_datetime(last_df["valid_time"])
    mcols_last = [c for c in last_df.columns if c.startswith("member_")]
    da_mean = last_df[mcols_last].values.mean(axis=1)
    ax.plot(dates_last, da_mean, label="DA (routed, ens mean)", **MEAN_KW)

    # ── open-loop mean (optional) ─────────────────────────────────────────────
    ol_pq = gauge_dir / "routed_forecast_leadtime_openloop.parquet"
    if not ol_pq.exists():
        ol_pq = gauge_dir / f"gauge_{gauge}_openloop18h.parquet"
    if ol_pq.exists():
        ol_df = pd.read_parquet(ol_pq)
        if "valid_time" not in ol_df.columns:
            ol_df["valid_time"] = pd.to_datetime(ol_df["issue_time"]) + pd.to_timedelta(ol_df["lead_hour"], unit="h")
            # use last issue time only for the mean line
            last_it = ol_df["issue_time"].max()
            ol_df = ol_df[ol_df["issue_time"] == last_it]
        ol_dates = pd.to_datetime(ol_df["valid_time"])
        ol_cols  = [c for c in ol_df.columns if c.startswith("member_")]
        ol_mean  = ol_df[ol_cols].values.mean(axis=1)
        ax.plot(ol_dates, ol_mean, label="open loop (routed, ens mean)", **OL_MEAN_KW)

    # ── USGS obs (dotted line, extended through latest available data) ─────────
    obs_csv = USGS_DIR / f"{gauge}.csv"
    obs_end = None
    if obs_csv.exists():
        obs = pd.read_csv(obs_csv, parse_dates=["time"]).set_index("time")
        obs.index = obs.index.tz_localize(None) if obs.index.tz else obs.index
        obs_w = obs["q_m3s"].loc[PLOT_START:]
        if len(obs_w):
            obs_end = obs_w.index.max()
            ax.plot(obs_w.index, obs_w.values,
                    color="black", lw=1.5, ls=":", zorder=11,
                    label="USGS obs (hourly)")

    # ── axes ──────────────────────────────────────────────────────────────────
    # x-axis: from Oct 1 (if analysis parquet exists) else from first forecast
    if an_da is not None:
        x_left = PLOT_START
    else:
        x_left = pd.to_datetime(issues[0][1]["valid_time"]).iloc[0]
    x_right = pd.to_datetime(issues[-1][1]["valid_time"]).iloc[-1]
    if obs_end is not None:
        x_right = max(x_right, obs_end)

    ax.set_ylabel("Discharge (m³/s)", fontsize=9)
    ax.set_ylim(bottom=0)
    ax.set_xlim(x_left, x_right)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%Mh"))
    # widen tick interval when plotting Oct 1-Oct 10 (>48 h span)
    span_h = (x_right - x_left).total_seconds() / 3600
    tick_h = 24 if span_h > 120 else 12 if span_h > 48 else 6
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=tick_h))
    ax.tick_params(labelsize=8)
    ax.grid(True, lw=0.4, alpha=0.4, color="#dddddd", zorder=0)
    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")
        spine.set_linewidth(0.6)

    sample_df   = issues[0][1]
    n_mem_fc    = len([c for c in sample_df.columns if c.startswith("member_")])
    analysis_str = "  |  analysis Oct 1–Oct 9" if an_da is not None else ""
    title = (f"Gauge {gauge}  ·  {n_issues} issue{'s' if n_issues > 1 else ''}"
             f"  ×  {n_mem_fc} members  ·  DA-init CFE + T-Route{analysis_str}")
    ax.set_title(title, fontsize=9 if standalone else 7.5, pad=5)

    # ── legend (standalone only — too cluttered in multi-panel) ───────────────
    if standalone:
        ax.legend(loc="upper left", fontsize=9, framealpha=0.9,
                  edgecolor="#cccccc", handlelength=2.0)

    # ── colorbar (standalone only) ────────────────────────────────────────────
    if standalone:
        sm = mcm.ScalarMappable(cmap=ISSUE_CMAP, norm=norm)
        sm.set_array([])
        if n_issues == 1:
            label_lo = issues[0][0]
            label_hi = issues[0][0]
        else:
            label_lo = issues[0][0]
            label_hi = issues[-1][0]
        cbar = fig.colorbar(sm, ax=ax, pad=0.01, shrink=0.95)
        cbar.set_label(
            f"forecast issue (hourly, {label_lo}, {label_hi})",
            fontsize=8)
        cbar.set_ticks([0, max(n_issues - 1, 1)])
        cbar.set_ticklabels([label_lo, label_hi])
        cbar.ax.tick_params(labelsize=7)

    return fig, ax


# ── 12-panel grid ─────────────────────────────────────────────────────────────
def plot_all_grid():
    fig, axes = plt.subplots(3, 4, figsize=(26, 14))
    fig.patch.set_facecolor("white")
    axes_flat = axes.flatten()

    for ax, gauge in zip(axes_flat, AL_GAUGES):
        plot_one_gauge(gauge, ax=ax, standalone=False)

    # shared legend
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=ANALYSIS_DA_COLOR, alpha=0.3, label="DA analysis (5–95 %)"),
        Line2D([0], [0], color=ANALYSIS_DA_COLOR, lw=2.0, label="DA analysis (ens mean)"),
        Patch(facecolor=ANALYSIS_OL_COLOR, alpha=0.2, label="OL analysis (5–95 %)"),
        Line2D([0], [0], color=ANALYSIS_OL_COLOR, lw=1.6, ls="--", label="OL analysis (ens mean)"),
        Line2D([0], [0], color="black", lw=1.5, ls=":", label="USGS obs"),
        Line2D([0], [0], color=ISSUE_CMAP(0.15), lw=1.5, alpha=0.7, label="early fc issue"),
        Line2D([0], [0], color=ISSUE_CMAP(1.0),  lw=1.5, alpha=0.7, label="late fc issue"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=7,
               fontsize=8.5, frameon=True, framealpha=0.95,
               edgecolor="#cccccc", bbox_to_anchor=(0.5, -0.01))

    fig.suptitle(
        "Alabama storm 2026  ·  DA analysis Oct 1–Oct 9  +  18 h ensemble forecast  ·  "
        "NWM-DA assimilation  ·  HRRR-initialized  ·  100 members  ·  CFE + T-Route",
        fontsize=12, fontweight="bold", y=1.005)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = OUT_BASE / "all_gauges_spaghetti.png"
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Saved grid: {out}")


# ── per-gauge standalone figures ──────────────────────────────────────────────
def plot_all_standalone():
    for gauge in AL_GAUGES:
        fig, ax = plot_one_gauge(gauge, standalone=True)
        if fig is None:
            print(f"  {gauge}: skipped (no data)")
            continue
        plt.tight_layout()
        out = OUT_BASE / gauge / f"gauge_{gauge}_spaghetti.png"
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  {gauge}: saved -> {out.name}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--gauge", default=None, help="single gauge (standalone)")
    parser.add_argument("--grid-only", action="store_true")
    parser.add_argument("--standalone-only", action="store_true")
    parser.add_argument("--no-analysis", action="store_true",
                        help="skip Oct 1 analysis band; pure forecast fans from issue start (matches Helene style)")
    args = parser.parse_args()

    if args.gauge:
        fig, _ = plot_one_gauge(args.gauge, standalone=True, no_analysis=args.no_analysis)
        if fig:
            plt.tight_layout()
            out = OUT_BASE / args.gauge / f"gauge_{args.gauge}_spaghetti.png"
            fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            print(f"Saved: {out}")
    elif args.grid_only:
        plot_all_grid()
    elif args.standalone_only:
        plot_all_standalone()
    else:
        print("── per-gauge standalone figures ──")
        plot_all_standalone()
        print("── 3×4 combined grid ──")
        plot_all_grid()
