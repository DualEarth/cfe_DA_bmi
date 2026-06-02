#!/usr/bin/env bash
# F1 Vrugt (1 gauge holdout) — 4c reconstructed timeseries plots.
#
# Reads routed_leadtime_da_full.parquet + routed_leadtime_openloop_full.parquet
# from the F1 leadtime route dir and writes output PNGs there.
# Must run AFTER route_lead_time_forecasts.py.
#
# Usage:
#   bash run_4c_f1.sh

set -euo pipefail

TROUTE=/home/svyas/miniconda3/envs/troute/bin/python3
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

ROUTE_DIR=/mnt/disk2/suma_helen_poster/da_results_1gauge_heldout/folder1_vrugt_leadtime_routed
USGS_CSV=/mnt/disk2/suma_helen_poster/03463300_usgs_hourly_2018_2024.csv

echo "[F1-4c] Reconstructed timeseries from: $ROUTE_DIR"
$TROUTE "$SCRIPT_DIR/plot_lead_time_reconstructed_timeseries.py" \
    --route-dir "$ROUTE_DIR" \
    --usgs-csv  "$USGS_CSV"

echo "[F1-4c] Forecast spaghetti..."
$TROUTE "$SCRIPT_DIR/plot_forecast_spaghetti.py" \
    --route-dir "$ROUTE_DIR" \
    --usgs-csv  "$USGS_CSV"

echo "[F1-4c] Done. Outputs in: $ROUTE_DIR"
ls "$ROUTE_DIR"/*.png 2>/dev/null || echo "  (no PNGs found)"
