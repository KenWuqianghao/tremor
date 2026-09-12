"""Summarise a run directory: mean VUS-PR, per-dataset breakdown, and (optionally) per-file
comparison against a reference (upstream leaderboard_results / benchmark_eval_results).

    python harness/report.py runs/U_eval_MMPAD --ref leaderboard:Uni_MMPAD
    python harness/report.py runs/U_eval_Sub_PCA --ref merged:Sub-PCA
    python harness/report.py runs/U_eval_Tremor --ref leaderboard:Uni_MMPAD
"""
import os, sys, json, glob, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.common import *

LB = os.path.join(UPSTREAM, 'benchmark_exp', 'leaderboard_results')
MERGED = os.path.join(UPSTREAM, 'benchmark_exp', 'benchmark_eval_results')


def load_run(run_dir):
    rows = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(run_dir, '*.json'))) if not os.path.basename(p).startswith('000_')]
    df = pd.DataFrame(rows)
    return df


def load_ref(track, ref):
    """ref = 'leaderboard:<csv stem>' (long format, VUS-PR column) or 'merged:<column>'."""
    kind, name = ref.split(':', 1)
    if kind == 'leaderboard':
        d = pd.read_csv(os.path.join(LB, name + '.csv'))
        if 'VUS-PR' in d.columns:
            return d[['file', 'VUS-PR', 'Time']].rename(columns={'VUS-PR': 'ref_vus_pr', 'Time': 'ref_time_s'})
        return d[['file', name.split('_', 1)[1]]].rename(columns={name.split('_', 1)[1]: 'ref_vus_pr'})
    d = pd.read_csv(os.path.join(MERGED, ('uni' if track == 'U' else 'multi') + '_mergedTable_VUS-PR.csv'))
    return d[['file', name]].rename(columns={name: 'ref_vus_pr'})


def summarise(run_dir, ref=None, track=None):
    cfg = json.load(open(os.path.join(run_dir, '000_config.json')))
    track = track or cfg['track']
    df = load_run(run_dir)
    out = {'run': os.path.basename(run_dir), 'track': track, 'split': cfg['split'], 'method': cfg['method'],
           'hp': cfg['hp'], 'subset': cfg['subset'], 'n_done': int(len(df)), 'n_listed': cfg['n_files'],
           'vus_pr': float(df['VUS-PR'].mean()), 'auc_pr': float(df['AUC-PR'].mean()),
           'runtime_min': float(df['runtime_s'].sum() / 60), 'failures': int((~df['ok']).sum())}
    per_ds = df.groupby('dataset').agg(n=('file', 'count'), vus_pr=('VUS-PR', 'mean'), runtime_s=('runtime_s', 'sum')).sort_values('vus_pr')
    if ref:
        r = load_ref(track, ref)
        m = df.merge(r, on='file', how='left')
        out['ref'] = ref
        out['ref_vus_pr_same_files'] = float(m['ref_vus_pr'].mean())
        out['ref_vus_pr_full_list'] = float(r[r.file.isin(file_list(track, cfg['split']))]['ref_vus_pr'].mean())
        out['max_abs_file_diff'] = float((m['VUS-PR'] - m['ref_vus_pr']).abs().max())
        out['n_files_diff_gt_0.01'] = int(((m['VUS-PR'] - m['ref_vus_pr']).abs() > 0.01).sum())
        if 'ref_time_s' in m:
            out['ref_runtime_min_same_files'] = float(m['ref_time_s'].sum() / 60)
        per_ds = m.groupby('dataset').agg(n=('file', 'count'), vus_pr=('VUS-PR', 'mean'), ref_vus_pr=('ref_vus_pr', 'mean'),
                                          runtime_s=('runtime_s', 'sum')).sort_values('vus_pr')
        per_ds['diff'] = per_ds['vus_pr'] - per_ds['ref_vus_pr']
        out['worst_files'] = m.assign(d=(m['VUS-PR'] - m['ref_vus_pr'])).sort_values('d').head(5)[['file', 'VUS-PR', 'ref_vus_pr']].to_dict('records')
    return out, per_ds, df


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir'); ap.add_argument('--ref', default=None)
    a = ap.parse_args()
    out, per_ds, df = summarise(a.run_dir, a.ref)
    pd.set_option('display.width', 200)
    print(json.dumps(out, indent=1))
    print(per_ds.round(4).to_string())
    per_ds.round(5).to_csv(os.path.join(a.run_dir, '000_per_dataset.csv'))
    json.dump(out, open(os.path.join(a.run_dir, '000_summary.json'), 'w'), indent=1)
