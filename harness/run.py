"""Run one detector over one (track, split) list with the benchmark's own scoring.

    python harness/run.py --track U --split tuning --method MMPAD --workers 4
    python harness/run.py --track U --split eval --method Sub_PCA --subset half
    python harness/run.py --track U --split eval --method Tremor --workers 4

Per-file results are written as JSON under runs/<track>_<split>_<method><tag>/ so an
interrupted run resumes where it stopped.  Scores are saved as float32 .npy next to them, so
the chooser can later be screened on cached component scores (harness/fuse_eval.py).

Methods: the upstream names (MMPAD, Sub_PCA, PCA, KShapeAD, MatrixProfile, ...) run through
TSB_AD.model_wrapper with the upstream optimal hyper-parameters; the names below run the
pieces of this package:
    Tremor        the whole detector (tremor.run_Tremor_Unsupervised, tremor.DEFAULT_HP)
    point         the univariate point component (tremor.point)
    point_m       the multivariate point component, top-3 channel mean (tremor.point_m)
    point_m_gate  the strongest channel's own point score, the M override's gate series
"""
import os, sys, json, time, argparse, traceback
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.common import *

SUBSET_SEED = 20260912


def select_subset(files, subset):
    files = sorted(files)
    if subset in (None, 'all'):
        return files
    if subset == 'half':
        rng = np.random.default_rng(SUBSET_SEED)
        idx = rng.permutation(len(files))[: (len(files) + 1) // 2]
        return sorted(files[i] for i in idx)
    if subset.startswith('first:'):
        return files[: int(subset.split(':')[1])]
    if subset.startswith('files:'):
        want = set(subset.split(':', 1)[1].split(','))
        return [f for f in files if f in want]
    raise ValueError(subset)


def default_hp(track, method):
    setup_paths()
    if method == 'Tremor':
        from tremor import DEFAULT_HP
        return dict(DEFAULT_HP)
    if method in ('point', 'point_m', 'point_m_gate'):
        return {}
    from TSB_AD.HP_list import Optimal_Uni_algo_HP_dict, Optimal_Multi_algo_HP_dict
    d = Optimal_Uni_algo_HP_dict if track == 'U' else Optimal_Multi_algo_HP_dict
    return dict(d.get(method, {}))


def get_runner(method):
    setup_paths()
    if method == 'Tremor':
        from tremor import run_Tremor_Unsupervised
        return lambda data, hp: run_Tremor_Unsupervised(np.asarray(data, dtype=float), **hp)
    if method == 'point':
        from tremor.point import run as point_run
        return lambda data, hp: point_run(data, **hp)
    if method == 'point_m':
        from tremor.point_m import point_m_score
        return lambda data, hp: point_m_score(data, **hp)
    if method == 'point_m_gate':
        from tremor.point_m import point_m_scores
        return lambda data, hp: point_m_scores(data, **hp)[1]
    import TSB_AD.model_wrapper as mw
    fn = getattr(mw, 'run_' + method)
    return lambda data, hp: fn(data, **hp)


def one(args):
    track, fn, method, hp, out_dir, n_job, save_scores = args
    jpath = os.path.join(out_dir, fn.replace('.csv', '.json'))
    if os.path.exists(jpath):
        return json.load(open(jpath))
    setup_paths()
    import warnings; warnings.filterwarnings('ignore')
    row = dict(file=fn, dataset=dataset_of(fn), method=method)
    try:
        data, label = load_series(track, fn)
        hp = dict(hp)
        if method in ('MMPAD', 'Tremor'):
            hp['n_job'] = n_job
        run = get_runner(method)
        t0 = time.time()
        out = run(data, hp)
        row['runtime_s'] = time.time() - t0
        if not isinstance(out, np.ndarray):
            raise RuntimeError(str(out))
        out = np.asarray(out, dtype=float).ravel()
        if len(out) != len(label):
            raise RuntimeError(f'score length {len(out)} != {len(label)}')
        m = evaluate(out, data, label)
        row.update({k: float(v) for k, v in m.items()})
        row['n'] = int(len(label)); row['dims'] = int(data.shape[1]); row['ok'] = True
        if save_scores:
            np.save(os.path.join(out_dir, fn.replace('.csv', '.npy')), out.astype(np.float32))
    except Exception as e:
        row['ok'] = False; row['error'] = f'{type(e).__name__}: {e}'
        row['traceback'] = traceback.format_exc()[-2000:]
        row.setdefault('runtime_s', float('nan'))
        for k in ('AUC-PR', 'AUC-ROC', 'VUS-PR', 'VUS-ROC'):
            row[k] = 0.0  # benchmark convention: a failed run scores 0
    json.dump(row, open(jpath, 'w'), indent=1)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--track', required=True, choices=['U', 'M'])
    ap.add_argument('--split', required=True, choices=['tuning', 'eval'])
    ap.add_argument('--method', required=True)
    ap.add_argument('--hp', default=None, help='JSON dict overriding the upstream optimal HP')
    ap.add_argument('--tag', default='')
    ap.add_argument('--subset', default='all')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--big-cost', type=float, default=2.5e9,
                    help='files with MMPAD proxy cost above this run one at a time with n_job=workers')
    ap.add_argument('--no-scores', action='store_true')
    ap.add_argument('--max-minutes', type=float, default=None, help='stop launching new files after this')
    ap.add_argument('--max-cost', type=float, default=None,
                    help='skip files whose MMPAD proxy cost (runs/file_stats.csv, from harness/file_stats.py) exceeds this; they are listed in 000_config.json')
    a = ap.parse_args()

    hp = default_hp(a.track, a.method)
    if a.hp:
        hp.update(json.loads(a.hp))
    name = a.method + a.tag
    out_dir = os.path.join(RUNS, f'{a.track}_{a.split}_{name}')
    os.makedirs(out_dir, exist_ok=True)
    files = select_subset(file_list(a.track, a.split), a.subset)
    json.dump(dict(track=a.track, split=a.split, method=a.method, hp=hp, subset=a.subset, n_files=len(files),
                   files=files, started=time.strftime('%Y-%m-%dT%H:%M:%S')), open(os.path.join(out_dir, '000_config.json'), 'w'), indent=1)

    # cost-ordered scheduling (largest first) using runs/file_stats.csv when present
    cost = {}
    sp = os.path.join(RUNS, 'file_stats.csv')
    if os.path.exists(sp):
        st = pd.read_csv(sp)
        st = st[(st.track == a.track)]
        cost = dict(zip(st.file, st.mmpad_proxy_cost))
    files = sorted(files, key=lambda f: -cost.get(f, 0))
    skipped = []
    if a.max_cost is not None:
        skipped = [f for f in files if cost.get(f, 0) > a.max_cost]
        files = [f for f in files if f not in set(skipped)]
        cfg = json.load(open(os.path.join(out_dir, '000_config.json')))
        cfg.update(max_cost=a.max_cost, skipped_over_cost=skipped, files=files, n_files=len(files))
        json.dump(cfg, open(os.path.join(out_dir, '000_config.json'), 'w'), indent=1)
        print(f'skipping {len(skipped)} files over cost cap {a.max_cost:g}', flush=True)
    big = [f for f in files if a.method in ('MMPAD', 'Tremor') and cost.get(f, 0) > a.big_cost]
    small = [f for f in files if f not in set(big)]
    print(f'{a.track}/{a.split}/{name}: {len(files)} files ({len(big)} big), hp={hp}', flush=True)

    t0 = time.time(); rows = []
    for f in big:  # one at a time, MMPAD internal parallelism
        if a.max_minutes and (time.time() - t0) / 60 > a.max_minutes: break
        r = one((a.track, f, a.method, hp, out_dir, a.workers, not a.no_scores)); rows.append(r)
        print(f"  {f} VUS-PR={r.get('VUS-PR', 0):.4f} t={r.get('runtime_s', 0):.1f}s ok={r['ok']}", flush=True)
    if small:
        args = [(a.track, f, a.method, hp, out_dir, 1, not a.no_scores) for f in small]
        with Pool(a.workers) as p:
            for r in p.imap_unordered(one, args):
                rows.append(r)
                print(f"  {r['file']} VUS-PR={r.get('VUS-PR', 0):.4f} t={r.get('runtime_s', 0):.1f}s ok={r['ok']}", flush=True)
                if a.max_minutes and (time.time() - t0) / 60 > a.max_minutes:
                    print('max-minutes reached; terminating pool', flush=True); p.terminate(); break
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, '000_results.csv'), index=False)
    print(f"DONE {len(df)}/{len(files)} files, mean VUS-PR={df['VUS-PR'].mean():.4f}, "
          f"sum runtime={df['runtime_s'].sum()/60:.1f} min, wall={(time.time()-t0)/60:.1f} min, failures={(~df['ok']).sum()}")


if __name__ == '__main__':
    main()
