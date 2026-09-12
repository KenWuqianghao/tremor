"""Per-file statistics for every list (length, dims, anomaly stats, MMPAD's inferred
sub_len / downsample factor / proxy cost) -> runs/file_stats.csv.  Used to estimate
MMPAD runtime and to build the fixed-seed Eval subset when a full run is infeasible."""
import os, sys, json
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.common import *


def one(args):
    track, split, fn = args
    setup_paths()
    from TSB_AD.models.mmpad.util import resolve_mmpad_budget_state, compute_mmpad_proxy_cost
    from TSB_AD.utils.slidingWindows import find_length_rank
    data, label = load_series(track, fn)
    st = resolve_mmpad_budget_state(data, periodicity=1, budget_mode='downsample')
    n_eff, cost = compute_mmpad_proxy_cost(st['data'].shape[0], data.shape[1], st['sub_len'])
    d = np.diff(np.concatenate([[0], label, [0]]))
    n_events = int((d == 1).sum())
    return dict(track=track, split=split, file=fn, dataset=dataset_of(fn), n=data.shape[0], dims=data.shape[1],
                train_index=int(fn.split('.')[0].split('_')[-3]),
                anomaly_ratio=float(label.mean()), n_events=n_events,
                eval_window=int(find_length_rank(data[:, 0].reshape(-1, 1), rank=1)),
                mmpad_sub_len=int(st['sub_len']), mmpad_ds=int(st['downsample_factor']),
                mmpad_n_work=int(st['data'].shape[0]), mmpad_proxy_cost=float(cost))


if __name__ == '__main__':
    jobs = [(t, s, f) for t in ('U', 'M') for s in ('tuning', 'eval') for f in file_list(t, s)]
    with Pool(4) as p:
        rows = p.map(one, jobs, chunksize=4)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RUNS, 'file_stats.csv'), index=False)
    print(df.groupby(['track', 'split']).agg(n_files=('file', 'count'), total_len=('n', 'sum'),
          max_len=('n', 'max'), proxy=('mmpad_proxy_cost', 'sum'), ds_gt1=('mmpad_ds', lambda x: (x > 1).sum())))
