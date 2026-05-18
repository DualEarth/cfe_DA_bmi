"""
Per-member input/output diagnostic for ONE catchment.

For each ensemble member, show side-by-side the INPUTS it actually received
(perturbed precipitation, perturbed PET) and the OUTPUT it produced
(simulated streamflow), plus its initial-state values as an annotation.

This is the diagnostic that answers 'why did THIS member produce THIS forecast'
by tracing the inputs that fed into CFE and the corresponding output.

Layout: 20 rows x 4 columns figure. Each row is one member.
    col 1: perturbed precipitation (bars)
    col 2: perturbed PET (line)
    col 3: simulated streamflow + Qkrig obs (line)
    col 4: text panel with initial-state values

Inputs (all from run_production_per_member.py):
    <PROD-DIR>/<CAT>/<CAT>_production_per_member.csv               (Q per member)
    <PROD-DIR>/<CAT>/<CAT>_production_per_member_precip.csv        (precip per member)
    <PROD-DIR>/<CAT>/<CAT>_production_per_member_pet.csv           (PET per member)
    <PROD-DIR>/<CAT>/<CAT>_production_per_member_initial_states.json
    <DA-DIR>/<CAT>/<CAT>_test_results.csv                          (Qkrig obs)

Output:
    <PROD-DIR>/<CAT>/<CAT>_per_member_io_diagnostic.png
"""
import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec

# ----- Configuration -----
CAT = "cat-1016300"

PROD_DIR = "/mnt/disk2/suma_helen_poster/da_results/v2_production_per_member"
DA_DIR   = "/mnt/disk2/suma_helen_poster/da_results/v2_true_enkf_vrugt"
OUT_PNG  = os.path.join(PROD_DIR, CAT, f"{CAT}_per_member_io_diagnostic.png")

# Plot window (Helene 4-day zoom)
ZOOM_START = pd.Timestamp("2024-09-24")
ZOOM_END   = pd.Timestamp("2024-09-28")

PRECIP_COLOR = "tab:blue"
PET_COLOR    = "tab:orange"
Q_COLOR      = "tab:purple"
OBS_COLOR    = "black"


def load_member_csv(path):
    if not os.path.exists(path):
        return None, None
    df = pd.read_csv(path, parse_dates=["date"])
    member_cols = sorted([c for c in df.columns if c.startswith("member_")])
    return df["date"].values, df[member_cols]


def main():
    q_dates,      q_df      = load_member_csv(os.path.join(PROD_DIR, CAT, f"{CAT}_production_per_member.csv"))
    precip_dates, precip_df = load_member_csv(os.path.join(PROD_DIR, CAT, f"{CAT}_production_per_member_precip.csv"))
    pet_dates,    pet_df    = load_member_csv(os.path.join(PROD_DIR, CAT, f"{CAT}_production_per_member_pet.csv"))

    init_states_path = os.path.join(PROD_DIR, CAT, f"{CAT}_production_per_member_initial_states.json")
    if os.path.exists(init_states_path):
        with open(init_states_path) as f:
            init_states = json.load(f)["members"]
    else:
        init_states = {}

    obs_path = os.path.join(DA_DIR, CAT, f"{CAT}_test_results.csv")
    if os.path.exists(obs_path):
        obs_df = pd.read_csv(obs_path, parse_dates=["date"])
        obs_dates = pd.to_datetime(obs_df["date"].values)
        obs_vals  = obs_df["obs_mm_h"].values
    else:
        obs_dates = None
        obs_vals  = None

    if q_df is None or precip_df is None or pet_df is None:
        raise FileNotFoundError(
            "Missing one of the per-member CSVs. Run run_production_per_member.py "
            "with the updated script that saves precip + PET + initial states.")

    member_cols = list(q_df.columns)
    N = len(member_cols)

    qd = pd.to_datetime(q_dates)
    pd_ = pd.to_datetime(precip_dates)
    ed = pd.to_datetime(pet_dates)
    qmask  = (qd  >= ZOOM_START) & (qd  <= ZOOM_END)
    pmask  = (pd_ >= ZOOM_START) & (pd_ <= ZOOM_END)
    emask  = (ed  >= ZOOM_START) & (ed  <= ZOOM_END)
    if obs_dates is not None:
        omask = (obs_dates >= ZOOM_START) & (obs_dates <= ZOOM_END)

    fig = plt.figure(figsize=(22, 3 * N))
    gs = gridspec.GridSpec(N, 4, width_ratios=[3, 3, 3, 1.5],
                           hspace=0.55, wspace=0.30)

    for i in range(N):
        col = member_cols[i]

        # --- Precipitation panel ---
        ax_p = fig.add_subplot(gs[i, 0])
        ax_p.bar(pd_[pmask], precip_df[col].values[pmask],
                 width=0.04, color=PRECIP_COLOR, alpha=0.85)
        ax_p.set_ylabel("P (mm/h)", fontsize=8)
        ax_p.set_title(f"{col} - precip", fontsize=8.5, loc="left")
        ax_p.tick_params(labelsize=7)
        ax_p.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax_p.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))

        # --- PET panel ---
        ax_e = fig.add_subplot(gs[i, 1])
        ax_e.plot(ed[emask], pet_df[col].values[emask],
                  color=PET_COLOR, lw=1.0)
        ax_e.set_ylabel("PET (mm/h)", fontsize=8)
        ax_e.set_title(f"{col} - PET", fontsize=8.5, loc="left")
        ax_e.tick_params(labelsize=7)
        ax_e.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax_e.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))

        # --- Simulated Q + obs panel ---
        ax_q = fig.add_subplot(gs[i, 2])
        ax_q.plot(qd[qmask], q_df[col].values[qmask],
                  color=Q_COLOR, lw=1.6, label=col)
        if obs_dates is not None:
            ax_q.plot(obs_dates[omask], obs_vals[omask],
                      color=OBS_COLOR, lw=1.2, linestyle="--", label="Qkrig (obs)")
        ax_q.set_ylabel("Q (mm/h)", fontsize=8)
        ax_q.set_title(f"{col} - simulated Q vs obs", fontsize=8.5, loc="left")
        ax_q.tick_params(labelsize=7)
        ax_q.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax_q.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        if i == 0:
            ax_q.legend(fontsize=7, loc="upper left")

        # --- Initial-state text panel ---
        ax_s = fig.add_subplot(gs[i, 3])
        ax_s.axis("off")
        s = init_states.get(col, {})
        text = (
            f"Initial states (t=0):\n"
            f"  soil  = {s.get('soil_m',  float('nan')):.4f} m  "
            f"(cap {s.get('soil_max_m', float('nan')):.4f})\n"
            f"  GW    = {s.get('gw_m',    float('nan')):.4f} m  "
            f"(cap {s.get('gw_max_m',    float('nan')):.4f})\n"
            f"  Nash[0] = {s.get('nash0_m', float('nan')):.6f} m\n"
            f"  Nash[1] = {s.get('nash1_m', float('nan')):.6f} m"
        )
        ax_s.text(0.0, 0.5, text, fontsize=8.5, family="monospace",
                  va="center", ha="left",
                  bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow",
                            edgecolor="0.7", alpha=0.85))

    fig.suptitle(
        f"Per-member input/output diagnostic - {CAT} - Hurricane Helene peak (Sep 24-28, 2024)\n"
        "Each row = one of 20 production ensemble members. "
        "Columns: perturbed P | perturbed PET | simulated Q (purple) vs Qkrig obs (black dashed) | initial states (text)",
        fontsize=12, y=0.995,
    )
    plt.savefig(OUT_PNG, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"Saved: {OUT_PNG}")


if __name__ == "__main__":
    main()
