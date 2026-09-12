"""Evaluate the chooser on CACHED component scores with the benchmark's own scoring.

    python harness/fuse_eval.py --track U --split tuning \
        --components U_tuning_MMPAD,U_tuning_Sub_PCA --hp '{"power": "hard"}' --tag _hard

Components are the run dirs written by run.py, in the order the chooser expects (the anchor
first).  `--hp` is a JSON dict of keyword arguments for tremor.fusion.fuse, so a threshold
sweep is a shell loop over this script that never re-runs a detector.  Only files present (ok=True, .npy saved) in ALL component run dirs are scored.
Output goes to runs/<track>_<split>_tremor<tag>/ in the same per-file JSON format as run.py,
so report.py works unchanged.  runtime_s per file = sum of the component detector runtimes +
fusion time (the honest cost of the fused detector).  Tuning lists only: this script refuses
to score an Eval list.
"""
import os, sys, json, time, argparse, glob
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.common import *


def one(args):
    track, fn, comp_dirs, hp, out_dir = args
    jpath = os.path.join(out_dir, fn.replace('.csv', '.json'))
    if os.path.exists(jpath):
        return json.load(open(jpath))
    setup_paths()
    import warnings; warnings.filterwarnings('ignore')
    from tremor.fusion import fuse
    row = dict(file=fn, dataset=dataset_of(fn), method='tremor')
    try:
        data, label = load_series(track, fn)
        scores, comp_rt, comp_vus = [], 0.0, []
        for d in comp_dirs:
            r = json.load(open(os.path.join(d, fn.replace('.csv', '.json'))))
            comp_rt += float(r['runtime_s']); comp_vus.append(float(r['VUS-PR']))
            scores.append(np.load(os.path.join(d, fn.replace('.csv', '.npy'))).astype(float))
        t0 = time.time()
        out, info = fuse(scores, **hp)
        row['fuse_s'] = time.time() - t0
        row['runtime_s'] = comp_rt + row['fuse_s']
        row.update(info); row['component_vus_pr'] = comp_vus
        if len(out) != len(label):
            raise RuntimeError(f'score length {len(out)} != {len(label)}')
        m = evaluate(out, data, label)
        row.update({k: float(v) for k, v in m.items()})
        row['n'] = int(len(label)); row['dims'] = int(data.shape[1]); row['ok'] = True
        np.save(os.path.join(out_dir, fn.replace('.csv', '.npy')), out.astype(np.float32))
    except Exception as e:
        import traceback
        row['ok'] = False; row['error'] = f'{type(e).__name__}: {e}'; row['traceback'] = traceback.format_exc()[-2000:]
        row.setdefault('runtime_s', float('nan'))
        for k in ('AUC-PR', 'AUC-ROC', 'VUS-PR', 'VUS-ROC'):
            row[k] = 0.0
    json.dump(row, open(jpath, 'w'), indent=1)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--track', required=True, choices=['U', 'M'])
    ap.add_argument('--split', required=True, choices=['tuning'])  # never eval from here
    ap.add_argument('--components', required=True, help='comma-separated run dir names under runs/')
    ap.add_argument('--hp', default='{}', help='JSON dict of keyword arguments for tremor.fusion.fuse')
    ap.add_argument('--tag', default='')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    hp = json.loads(a.hp)
    comp_dirs = [os.path.join(RUNS, c) for c in a.components.split(',')]
    listed = file_list(a.track, a.split)
    have = None
    for d in comp_dirs:
        ok = {os.path.basename(p).replace('.json', '.csv') for p in glob.glob(os.path.join(d, '*.json'))
              if not os.path.basename(p).startswith('000_') and json.load(open(p)).get('ok')
              and os.path.exists(p.replace('.json', '.npy'))}
        have = ok if have is None else have & ok
    files = sorted(f for f in listed if f in have)
    name = f'{a.track}_{a.split}_tremor{a.tag}'
    out_dir = os.path.join(RUNS, name); os.makedirs(out_dir, exist_ok=True)
    json.dump(dict(track=a.track, split=a.split, method='tremor', hp=hp, subset='cached:' + a.components,
                   n_files=len(files), files=files, components=a.components,
                   started=time.strftime('%Y-%m-%dT%H:%M:%S')), open(os.path.join(out_dir, '000_config.json'), 'w'), indent=1)
    print(f'{name}: {len(files)} files, hp={hp}', flush=True)
    t0 = time.time(); rows = []
    with Pool(a.workers) as p:
        for r in p.imap_unordered(one, [(a.track, f, comp_dirs, hp, out_dir) for f in files]):
            rows.append(r)
            cv = ' '.join(f'{v:.3f}' for v in r.get('component_vus_pr', []))
            print(f"  {r['file'][:45]:45s} VUS-PR={r.get('VUS-PR', 0):.4f} comps=[{cv}] w={np.round(r.get('weights', []), 2).tolist()} ok={r['ok']}", flush=True)
    df = pd.DataFrame(rows); df.to_csv(os.path.join(out_dir, '000_results.csv'), index=False)
    comp = np.array(df['component_vus_pr'].tolist()) if len(df) else np.zeros((0, 2))
    print(f"DONE {len(df)}/{len(files)} files, mean VUS-PR={df['VUS-PR'].mean():.4f} | components "
          f"{np.round(comp.mean(0), 4).tolist()} | oracle max {comp.max(1).mean():.4f} | sum runtime={df['runtime_s'].sum():.0f}s "
          f"wall={time.time()-t0:.0f}s failures={(~df['ok']).sum()}")


if __name__ == '__main__':
    main()
