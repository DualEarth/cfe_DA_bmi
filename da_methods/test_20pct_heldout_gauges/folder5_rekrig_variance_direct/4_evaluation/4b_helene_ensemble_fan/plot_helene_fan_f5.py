"""
plot_helene_fan_f5.py

Helene-window ensemble fan plot for F5 (re-kriged variance, 20% holdout)
at USGS gauge 03463300.

For each daily init time (issue_time) in Sep 24–30 2024:
  - shaded band = member min–max envelope
  - thin line   = ensemble median
Grand mean across all init times shown as thick line.
USGS obs = black solid. Open-loop grand median = black dashed.

Reads routed parquets produced by run_route_leadtime_forecasts.py.

Usage:
    python3 plot_helene_fan_f5.py
    python3 plot_helene_fan_f5.py --route-dir /path/to/routed --out-dir /path/to/out
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DEFAULT_ROUTE_DIR = "/mnt/disk2/suma_helen_poster/da_results/da_forecast_f5_rekrig_20pct/routed"
DEFAULT_USGS_CSV  = "/mnt/disk2/suma_helen_poster/03463300_usgs_hourly_2018_2024.csv"

HELENE_START = pd.Timestamp("2024-09-24 00:00:00")
HELENE_END   = pd.Timestamp("2024-09-30 23:00:00")

WATERSHED_AREA_KM2 = 113.18
MM_H_TO_M3S        = WATERSHED_AREA_KM2 * 1000.0 / 3600.0

# One colour per init date (7 days)
INIT_COLORS = [
    "#1f77b4",  # Sep-24  blue
    "#ff7f0e",  # Sep-25  orange
    "#2ca02c",  # Sep-26  green
    "#d62728",  # Sep-27  red
    "#9467bd",  # Sep-28  purple
    "#8c564b",  # Sep-29  brown
    "#e377c2",  # Sep-30  pink
]


# ── helpers ───────────────────────────────────────────────────────────────────

def load_parquet(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    df['issue_time'] = pd.to_datetime(df['issue_time'])

    if 'q_gauge_m3s' in df.columns and 'member' in df.columns:
        return df[['issue_time', 'lead_hour', 'member', 'q_gauge_m3s']]

    member_cols = sorted(c for c in df.columns if c.startswith('member_'))
    if not member_cols:
        raise ValueError(f"Cannot identify member columns in {path}. Columns: {df.columns.tolist()}")
    keep = ['issue_time', 'lead_hour']
    long = df[keep + member_cols].melt(
        id_vars=keep, value_vars=member_cols,
        var_name='member', value_name='q_gauge_m3s')
    return long


def load_usgs(usgs_csv):
    df = pd.read_csv(usgs_csv)
    date_col = next(c for c in df.columns if c.lower() in ('datetime', 'date', 'time', 'timestamp'))
    q_col    = next(c for c in df.columns if 'q' in c.lower() or 'flow' in c.lower()
                    or 'discharge' in c.lower())
    df[date_col] = pd.to_datetime(df[date_col])
    series = df.set_index(date_col)[q_col].astype(float)
    if 'mm' in q_col.lower():
        series = series * MM_H_TO_M3S
        print(f"  Converted obs from mm/h ('{q_col}') → m³/s (×{MM_H_TO_M3S:.4f})")
    return series


def add_valid_time(df):
    df = df.copy()
    df['valid_time'] = df['issue_time'] + pd.to_timedelta(df['lead_hour'], unit='h')
    return df


# ── main plot ─────────────────────────────────────────────────────────────────

def plot_fan(df_da, df_ol, obs, out_path):
    df_da = add_valid_time(df_da)
    df_ol = add_valid_time(df_ol)

    # Filter to issue_times in Sep 24-30; valid_times extend naturally up to +18 h
    da_h = df_da[
        (df_da['issue_time'] >= HELENE_START) &
        (df_da['issue_time'] <= HELENE_END)
    ].copy()
    ol_h = df_ol[
        (df_ol['issue_time'] >= HELENE_START) &
        (df_ol['issue_time'] <= HELENE_END)
    ].copy()
    plot_end = HELENE_END + pd.Timedelta(hours=18)
    obs_h = obs[(obs.index >= HELENE_START) & (obs.index <= plot_end)]

    # Group hourly issue_times into calendar days (Sep 24–30 only)
    da_h['init_day'] = da_h['issue_time'].dt.normalize()
    day_range = pd.date_range(HELENE_START.normalize(), HELENE_END.normalize(), freq='D')

    fig, ax = plt.subplots(figsize=(14, 5))

    # ---- per-day fan: pool all hourly inits within each calendar day ----
    all_mean_series = []
    legend_handles  = []
    for i, day in enumerate(day_range):
        color = INIT_COLORS[i % len(INIT_COLORS)]
        sub = da_h[da_h['init_day'] == day]
        if sub.empty:
            continue

        # pool all members + all hourly inits within the day → one time-series per member
        grp = sub.groupby(['valid_time', 'member'])['q_gauge_m3s'].mean().reset_index()
        piv = grp.pivot_table(index='valid_time', columns='member',
                              values='q_gauge_m3s', aggfunc='mean').sort_index()
        vt    = piv.index
        mn    = piv.min(axis=1).values
        mx    = piv.max(axis=1).values
        med   = piv.median(axis=1).values
        mean_ = piv.mean(axis=1).values

        shade = ax.fill_between(vt, mn, mx, color=color, alpha=0.22, linewidth=0)
        line, = ax.plot(vt, med, color=color, lw=1.4, alpha=0.9)
        legend_handles.append((shade, line, day.strftime("Init %Y-%m-%d")))

        all_mean_series.append(pd.Series(mean_, index=vt, name=day))

    # ---- grand mean (thick coloured line) ----
    if all_mean_series:
        grand = pd.concat(all_mean_series, axis=1).mean(axis=1).sort_index()
        h_grand, = ax.plot(grand.index, grand.values,
                           color='#2ca02c', lw=3.0, zorder=5)

    # ---- open loop grand median ----
    ol_grp = ol_h.groupby(['valid_time', 'member'])['q_gauge_m3s'].mean().reset_index()
    ol_piv = ol_grp.pivot_table(index='valid_time', columns='member',
                                values='q_gauge_m3s', aggfunc='mean').sort_index()
    ol_med = ol_piv.median(axis=1)
    h_ol, = ax.plot(ol_med.index, ol_med.values,
                    color='black', lw=1.8, linestyle='--', zorder=4)

    # ---- USGS obs ----
    h_obs, = ax.plot(obs_h.index, obs_h.values,
                     color='black', lw=2.4, zorder=6)

    # ---- Helene peak annotation ----
    if len(obs_h) > 0:
        peak_t = obs_h.idxmax()
        peak_v = obs_h.max()
        ax.annotate("Helene peak",
                    xy=(peak_t, peak_v),
                    xytext=(peak_t + pd.Timedelta(hours=8), peak_v * 0.97),
                    fontsize=9, color='#d62728',
                    arrowprops=dict(arrowstyle='->', color='#d62728', lw=1.2))

    # ---- clean legend (one entry per day + grand mean + OL + obs) ----
    import matplotlib.patches as mpatches
    day_entries = [mpatches.Patch(color=INIT_COLORS[i % len(INIT_COLORS)],
                                  alpha=0.7, label=label)
                   for i, (_, _, label) in enumerate(legend_handles)]
    extra = [
        plt.Line2D([0], [0], color='#2ca02c', lw=3.0, label="F5 DA — grand mean"),
        plt.Line2D([0], [0], color='black', lw=1.8, linestyle='--', label="Open loop — grand median"),
        plt.Line2D([0], [0], color='black', lw=2.4, label="USGS obs"),
    ]
    ax.legend(handles=day_entries + extra,
              fontsize=9, loc='upper left', framealpha=0.92, ncol=1)

    ax.set_ylabel("Discharge (m³/s)", fontsize=11)
    ax.set_xlabel("Date (UTC)", fontsize=11)
    ax.set_title(
        "F5 (re-kriged σ²) — ensemble forecast fan: initial state uncertainty  |  Sep 24–30 2024\n"
        "USGS 03463300  |  Shaded = member min–max  |  Line = median per init day  |  Thick = grand mean",
        fontsize=11)
    ax.set_xlim(HELENE_START, plot_end)
    ax.grid(True, alpha=0.22)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=20, ha='right', fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--route-dir', default=DEFAULT_ROUTE_DIR)
    parser.add_argument('--usgs-csv',  default=DEFAULT_USGS_CSV)
    parser.add_argument('--out-dir',   default=None)
    parser.add_argument('--da-name',   default='routed_leadtime_da_full.parquet')
    parser.add_argument('--ol-name',   default='routed_leadtime_openloop_full.parquet')
    args = parser.parse_args()

    out_dir = args.out_dir or args.route_dir
    os.makedirs(out_dir, exist_ok=True)

    print("Loading parquets...")
    df_da = load_parquet(os.path.join(args.route_dir, args.da_name))
    df_ol = load_parquet(os.path.join(args.route_dir, args.ol_name))
    obs   = load_usgs(args.usgs_csv)

    out_path = os.path.join(out_dir, "helene_ensemble_fan_f5.png")
    plot_fan(df_da, df_ol, obs, out_path)
    print("Done.")


if __name__ == "__main__":
    main()
