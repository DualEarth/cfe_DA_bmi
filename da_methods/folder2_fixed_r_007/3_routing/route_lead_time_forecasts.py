#!/usr/bin/env python3
"""
route_lead_time_forecasts.py

Route the 20-member lead-time forecast ensemble (DA and open-loop) through
t-route Muskingum-Cunge to gauge 03463300 (South Toe River Near Celo, NC).

Reads per-catchment lead-time CSVs produced by run_lead_time_forecast_sweep.py,
routes each member's 18-lead forecast through the channel network, and writes
two routed parquets at the gauge outlet.

Input (per catchment, per scenario):
    <leadtime-dir>/<cat>/<cat>_lead_time_forecasts_da.csv
    <leadtime-dir>/<cat>/<cat>_lead_time_forecasts_openloop.csv
    Columns: issue_time, lead_hour, valid_time, member_00..member_19 (mm/h)

Output:
    <out-dir>/routed_leadtime_da_full.parquet
    <out-dir>/routed_leadtime_openloop_full.parquet
    Columns: issue_time, lead_hour, member_00..member_19 (Q in m3/s at gauge)

Usage:
    python3 route_lead_time_forecasts.py \\
        --gpkg /mnt/disk1/usgs_streamflow_allgauges/subdaily_15min/test/gage-03463300_subset.gpkg \\
        --leadtime-dir /mnt/disk2/suma_helen_poster/da_results/v2_lead_time_forecast_hardcoded_r \\
        --out-dir /mnt/disk2/suma_helen_poster/da_results/v2_lead_time_forecast_hardcoded_r_routed
"""

import argparse
import sqlite3
import os
import sys
import types as _types
from functools import partial

import numpy as np
import pandas as pd

# Patch coverage.types for numba/troute on Python 3.10
_stub = _types.ModuleType('coverage.types')
for _cls in ['Tracer', 'TTraceData', 'TShouldTraceFn', 'TFileDisposition',
             'TShouldStartContextFn', 'TWarnFn', 'TTraceFn']:
    setattr(_stub, _cls, type(_cls, (), {}))
sys.modules['coverage.types'] = _stub

import troute.nhd_network as nhd_network
from troute.routing.fast_reach.mc_reach import compute_network_structured

TERMINAL_INT     = 1016283
DT               = 3600.0
QTS_SUBDIVISIONS = 1
FORECAST_LEADS   = 18

CATS = [
    'cat-1016279', 'cat-1016280', 'cat-1016281', 'cat-1016282', 'cat-1016283',
    'cat-1016300', 'cat-1016301', 'cat-1016302', 'cat-1016303', 'cat-1016304',
    'cat-1016305', 'cat-1016306', 'cat-1016307', 'cat-1016308', 'cat-1016309',
    'cat-1016310', 'cat-1016311', 'cat-1016312', 'cat-1016313', 'cat-1016314',
    'cat-1016315',
]


def seg_int(wb_id):
    return int(wb_id[3:])


def read_network(gpkg):
    con = sqlite3.connect(gpkg)
    fp_attr = pd.read_sql(
        'SELECT link, "to", BtmWdth, TopWdth, TopWdthCC, n, nCC, ChSlp, So, Length_m '
        'FROM "flowpath-attributes"', con)
    fp = pd.read_sql('SELECT divide_id, areasqkm FROM flowpaths', con)
    con.close()
    return fp_attr, fp


def build_connections(fp_attr):
    link_set = {seg_int(r) for r in fp_attr['link']}
    connections = {}
    for _, row in fp_attr.iterrows():
        us = seg_int(row['link'])
        ds = int(row['to'][4:])
        connections[us] = [ds] if ds in link_set else []
    return connections


def build_param_df(fp_attr):
    rows = [{
        'seg_id': seg_int(r['link']),
        'dt': float(DT),
        'bw': float(r['BtmWdth']),    'tw': float(r['TopWdth']),
        'twcc': float(r['TopWdthCC']), 'dx': float(r['Length_m']),
        'n':  float(r['n']),           'ncc': float(r['nCC']),
        'cs': float(r['ChSlp']),       's0': float(r['So']),
        'alt': 0.0,
    } for _, r in fp_attr.iterrows()]
    df = pd.DataFrame(rows).set_index('seg_id').sort_index()
    return df.astype('float32')


def route_one(reaches_wTypes, upstreams, param_df, q0_df,
              qlat_arr, nts, n_segs, terminal_pos):
    e1i   = np.zeros(0, dtype='int32')
    e1f   = np.zeros(0, dtype='float32')
    e2f   = np.zeros((0, nts), dtype='float32')
    e00f32 = np.zeros((0, 0), dtype='float32')
    e00f64 = np.zeros((0, 0), dtype='float64')
    e00i32 = np.zeros((0, 0), dtype='int32')

    results = compute_network_structured(
        nts, DT, QTS_SUBDIVISIONS,
        reaches_wTypes, upstreams,
        param_df.index.values.astype('int64'),
        param_df.columns.values,
        param_df.values,
        q0_df.values.astype('float32'),
        qlat_arr.astype('float32'),
        [], e00f64, {}, e00i32, False,
        '2024-09-24_00:00:00',
        e2f, e1i, e1i, e1i, e1f, e1f, 0.0,
        e2f, e1i, e1f, e1f, e1f, e1f, e1f,
        e2f, e1i, e1f, e1f, e1f, e1f, e1f,
        e2f, e1i, e1i, [], e1i, e1i, e1f, e1i, e1i,
        e1i, e1i, e1f, e1i, e1f, e1i, e1i, e00f32,
    )
    seg_ids = np.asarray(results[0])
    fvd     = np.asarray(results[1])
    Q_var  = fvd[terminal_pos, :nts]
    Q_time = fvd[terminal_pos, 0::3]
    return Q_var if Q_var.max() > Q_time.max() else Q_time


def load_leadtime_csv(path):
    df = pd.read_csv(path, parse_dates=['issue_time', 'valid_time'])
    member_cols = sorted([c for c in df.columns if c.startswith('member_')])
    return df, member_cols


def route_scenario(scenario_label, cat_data, area_map,
                   reaches_wTypes, upstreams, param_df, q0_df,
                   seg_ids_sorted, terminal_pos, n_segs, out_path):
    """Route one scenario (DA or OL) and write parquet."""

    ref_cat = next(iter(cat_data.values()))
    ref_df, member_cols = ref_cat
    n_members = len(member_cols)
    issue_times = sorted(ref_df['issue_time'].unique())
    print(f"  [{scenario_label}] {len(issue_times)} issue times | {n_members} members | "
          f"{FORECAST_LEADS} leads")

    all_records = []

    for t_idx, t0 in enumerate(issue_times):

        qlat_cube = np.zeros((n_members, n_segs, FORECAST_LEADS), dtype='float32')

        for sid, (df, mcols) in cat_data.items():
            seg_pos_arr = np.where(seg_ids_sorted == sid)[0]
            if len(seg_pos_arr) == 0:
                continue
            seg_pos = int(seg_pos_arr[0])
            area = area_map.get(sid, 0.0)

            sub = df[df['issue_time'] == t0].sort_values('lead_hour')
            if sub.empty:
                continue

            mem_vals = sub[mcols].to_numpy(dtype='float32')   # (n_leads, n_members)
            mem_vals = mem_vals / 1000.0 / 3600.0 * area       # mm/h -> m3/s
            n_lead_avail = min(mem_vals.shape[0], FORECAST_LEADS)
            qlat_cube[:, seg_pos, :n_lead_avail] = mem_vals[:n_lead_avail].T

        Q_members = np.full((FORECAST_LEADS, n_members), np.nan, dtype='float32')
        for m in range(n_members):
            qlat_m = qlat_cube[m]   # (n_segs, FORECAST_LEADS)
            qlat_df_m = pd.DataFrame(
                qlat_m, index=param_df.index, columns=range(FORECAST_LEADS))
            qlat_df_m = qlat_df_m.reindex(param_df.index, fill_value=0.0)
            Q_t = route_one(reaches_wTypes, upstreams, param_df, q0_df,
                            qlat_df_m.values.astype('float32'),
                            FORECAST_LEADS, n_segs, terminal_pos)
            Q_members[:, m] = Q_t[:FORECAST_LEADS]

        t0_str = pd.Timestamp(t0).strftime('%Y-%m-%d %H:%M:%S')
        for lead in range(1, FORECAST_LEADS + 1):
            row = {'issue_time': t0_str, 'lead_hour': lead}
            for m, col in enumerate(member_cols):
                row[col] = float(Q_members[lead - 1, m])
            all_records.append(row)

        if (t_idx + 1) % 20 == 0 or (t_idx + 1) == len(issue_times):
            print(f"  [{scenario_label}] Routed {t_idx + 1}/{len(issue_times)} issue times")

    df_out = pd.DataFrame(all_records)
    df_out.to_parquet(out_path, index=False)
    print(f"  [{scenario_label}] Saved: {out_path}  shape={df_out.shape}")
    return df_out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpkg',         required=True)
    parser.add_argument('--leadtime-dir', required=True,
                        help='Dir with <cat>/<cat>_lead_time_forecasts_{da,openloop}.csv')
    parser.add_argument('--out-dir',      required=True)
    parser.add_argument('--da-suffix',    default='_lead_time_forecasts_da.csv')
    parser.add_argument('--ol-suffix',    default='_lead_time_forecasts_openloop.csv')
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # Network
    print('Reading network from GPKG...')
    fp_attr, fp = read_network(args.gpkg)
    connections = build_connections(fp_attr)
    rconn = nhd_network.reverse_network(connections)
    path_func = partial(nhd_network.split_at_junction, rconn)
    reach_list = nhd_network.dfs_decomposition(rconn, path_func)
    reaches_wTypes = [(r, 0) for r in reach_list]
    upstreams = dict(rconn)
    param_df = build_param_df(fp_attr)
    n_segs = len(param_df)

    area_map = {int(r['divide_id'][4:]): r['areasqkm'] * 1e6
                for _, r in fp.iterrows()
                if r['divide_id'] and str(r['divide_id']).startswith('cat-')}
    print(f'  {len(fp_attr)} segments | total area {sum(area_map.values())/1e6:.2f} km²')

    seg_ids_sorted = param_df.index.values
    terminal_pos = int(np.where(seg_ids_sorted == TERMINAL_INT)[0][0])
    print(f'  Terminal: wb-{TERMINAL_INT} at index {terminal_pos}')

    q0_df = pd.DataFrame(
        np.zeros((n_segs, 3), dtype='float32'),
        index=param_df.index, columns=['qu0', 'qd0', 'h0'])

    # Load per-catchment CSVs for each scenario
    print('Loading per-catchment lead-time CSVs...')
    da_cat_data = {}
    ol_cat_data = {}
    loaded = 0
    missing_da = []
    missing_ol = []

    for cat in CATS:
        sid = int(cat[4:])
        da_path = os.path.join(args.leadtime_dir, cat, f'{cat}{args.da_suffix}')
        ol_path = os.path.join(args.leadtime_dir, cat, f'{cat}{args.ol_suffix}')

        if os.path.exists(da_path):
            da_cat_data[sid] = load_leadtime_csv(da_path)
        else:
            missing_da.append(cat)

        if os.path.exists(ol_path):
            ol_cat_data[sid] = load_leadtime_csv(ol_path)
        else:
            missing_ol.append(cat)

        if os.path.exists(da_path) or os.path.exists(ol_path):
            loaded += 1

    print(f'  Loaded {len(da_cat_data)}/21 DA catchments, '
          f'{len(ol_cat_data)}/21 OL catchments')
    if missing_da:
        print(f'  Missing DA: {missing_da}  (zero inflow from these catchments)')
    if missing_ol:
        print(f'  Missing OL: {missing_ol}  (zero inflow from these catchments)')

    if not da_cat_data and not ol_cat_data:
        raise RuntimeError('No lead-time CSVs found — check --leadtime-dir')

    # Route DA scenario
    if da_cat_data:
        out_da = os.path.join(args.out_dir, 'routed_leadtime_da_full.parquet')
        route_scenario('DA', da_cat_data, area_map,
                       reaches_wTypes, upstreams, param_df, q0_df,
                       seg_ids_sorted, terminal_pos, n_segs, out_da)

    # Route open-loop scenario
    if ol_cat_data:
        out_ol = os.path.join(args.out_dir, 'routed_leadtime_openloop_full.parquet')
        route_scenario('OL', ol_cat_data, area_map,
                       reaches_wTypes, upstreams, param_df, q0_df,
                       seg_ids_sorted, terminal_pos, n_segs, out_ol)

    print('Done.')


if __name__ == '__main__':
    main()
