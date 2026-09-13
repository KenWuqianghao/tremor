"""Compare an Eval run with the published per-series tables on exactly the files it
completed (a run may be cost-capped or interrupted).

    python harness/eval_compare.py runs/U_eval_Tremor --save

Prints, for the completed files only: Tremor's mean VUS-PR, the published per-file means of
MMPAD and of the authors' second reference (Sub-PCA on U, PCA on M -- there is no Sub-PCA row
on the M track) averaged over the SAME files, the per-dataset breakdown, and the coverage of
the track's Eval list in files and in MMPAD proxy cost.  Reference tables come from the
authors' per-series files in upstream/ (leaderboard_results + benchmark_eval_results), the
same loader the MMPAD reproduction was checked with.  No labels, no evaluation code touched.
"""
import os, sys, json, glob, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.common import ROOT, RUNS, file_list
from harness.report import load_run, load_ref

REF2 = {'U': ('Sub-PCA', 'merged:Sub-PCA'), 'M': ('PCA', 'merged:PCA')}


def compare(run_dir):
    cfg = json.load(open(os.path.join(run_dir, '000_config.json')))
    track, split = cfg['track'], cfg['split']
    df = load_run(run_dir)
    done = sorted(df['file'].tolist())
    full = file_list(track, split)

    mm = load_ref(track, 'leaderboard:' + ('Uni_MMPAD' if track == 'U' else 'Multi_MMPAD')).rename(
        columns={'ref_vus_pr': 'MMPAD'})[['file', 'MMPAD']]
    r2name, r2ref = REF2[track]
    r2 = load_ref(track, r2ref).rename(columns={'ref_vus_pr': r2name})[['file', r2name]]
    m = df.merge(mm, on='file', how='left').merge(r2, on='file', how='left')
    m = m.rename(columns={'VUS-PR': 'Tremor'})

    stats = pd.read_csv(os.path.join(RUNS, 'file_stats.csv'))
    stats = stats[(stats.track == track) & (stats.split == split)][['file', 'mmpad_proxy_cost']]
    cost_all = float(stats.mmpad_proxy_cost.sum())
    cost_done = float(stats[stats.file.isin(done)].mmpad_proxy_cost.sum())
    listed = cfg.get('files', done)
    cost_listed = float(stats[stats.file.isin(listed)].mmpad_proxy_cost.sum())

    per_ds = m.groupby('dataset').agg(n=('file', 'count'), Tremor=('Tremor', 'mean'),
                                      MMPAD=('MMPAD', 'mean'), **{r2name: (r2name, 'mean')},
                                      runtime_s=('runtime_s', 'sum'))
    per_ds['vsMMPAD'] = per_ds['Tremor'] - per_ds['MMPAD']
    per_ds = per_ds.sort_values('vsMMPAD')

    out = {
        'run': os.path.basename(run_dir.rstrip('/')), 'track': track, 'split': split,
        'method': cfg['method'], 'subset_rule': cfg['subset'], 'n_listed_in_run': cfg['n_files'],
        'n_done': len(df), 'n_eval_list': len(full),
        'file_share_of_eval_list': len(df) / len(full),
        'cost_share_of_eval_list': cost_done / cost_all,
        'n_listed_capped_subset': len(listed), 'max_cost': cfg.get('max_cost'),
        'file_share_of_capped_subset': len(df) / len(listed),
        'cost_share_of_capped_subset': cost_done / cost_listed,
        'mmpad_proxy_cost_done': cost_done, 'mmpad_proxy_cost_eval_list': cost_all,
        'failures': int((~df['ok']).sum()),
        'detector_time_h': float(df['runtime_s'].sum() / 3600),
        'Tremor': float(m['Tremor'].mean()),
        'MMPAD_same_files': float(m['MMPAD'].mean()),
        r2name + '_same_files': float(m[r2name].mean()),
        'MMPAD_full_eval_list': float(mm[mm.file.isin(full)]['MMPAD'].mean()),
        r2name + '_full_eval_list': float(r2[r2.file.isin(full)][r2name].mean()),
        'n_files_missing_MMPAD_ref': int(m['MMPAD'].isna().sum()),
        'n_files_missing_%s_ref' % r2name: int(m[r2name].isna().sum()),
        'wins_vs_MMPAD': int((m['Tremor'] > m['MMPAD']).sum()),
        'losses_vs_MMPAD': int((m['Tremor'] < m['MMPAD']).sum()),
    }
    return out, per_ds, m


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir', nargs='+')
    ap.add_argument('--save', action='store_true')
    a = ap.parse_args()
    pd.set_option('display.width', 200)
    for rd in a.run_dir:
        out, per_ds, m = compare(rd)
        print(json.dumps(out, indent=1))
        print(per_ds.round(4).to_string())
        worst = m.assign(d=m['Tremor'] - m['MMPAD']).sort_values('d')
        print('\n5 worst vs MMPAD:\n' + worst.head(5)[['file', 'Tremor', 'MMPAD']].round(4).to_string(index=False))
        print('\n5 best vs MMPAD:\n' + worst.tail(5)[['file', 'Tremor', 'MMPAD']].round(4).to_string(index=False))
        if a.save:
            per_ds.round(5).to_csv(os.path.join(rd, '000_eval_compare_per_dataset.csv'))
            m.round(5).to_csv(os.path.join(rd, '000_eval_compare_per_file.csv'), index=False)
            json.dump(out, open(os.path.join(rd, '000_eval_compare.json'), 'w'), indent=1)
        print('=' * 100)
