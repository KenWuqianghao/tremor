"""Console script: score ONE TSB-AD-format CSV with Tremor.

    tremor-score data/TSB-AD-U/001_NAB_id_1_Facility_tr_1007_1st_2014.csv
    tremor-score <file.csv> --scores out.npy --quiet          # write the score array only
    tremor-score <file.csv> --hp '{"n_job": 4}' --json

Input layout is the benchmark's own (upstream benchmark_exp/Run_Detector_U.py):
the last column is `Label` (0/1 per timestamp), every other column is a channel.
A file with no `Label` column is scored but not evaluated (use --scores).

The metric is the benchmark's own: TSB_AD.evaluation.metrics.get_metrics with
slidingWindow = TSB_AD.utils.slidingWindows.find_length_rank(first channel, rank=1).
Nothing here reimplements VUS-PR.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

from . import __version__
from .detector import DEFAULT_HP, run_Tremor_Unsupervised


def load_csv(path):
    """(data [n, D] float, label [n] int or None) -- the benchmark's own reader."""
    import pandas as pd
    df = pd.read_csv(path).dropna()
    if 'Label' in df.columns:
        label = df['Label'].astype(int).to_numpy()
        data = df.drop(columns=['Label']).values.astype(float)
    else:
        label = None
        data = df.values.astype(float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    return data, label


def score(path, hp=None):
    """(score array, data, label) for one benchmark CSV."""
    data, label = load_csv(path)
    out = run_Tremor_Unsupervised(data, **(hp or {}))
    return np.asarray(out, dtype=float).ravel(), data, label


def evaluate(out, data, label):
    """The benchmark's own metrics dict for a score array (needs TSB-AD installed)."""
    from TSB_AD.evaluation.metrics import get_metrics
    from TSB_AD.utils.slidingWindows import find_length_rank
    sliding = find_length_rank(np.asarray(data, float)[:, 0].reshape(-1, 1), rank=1)
    return {k: float(v) for k, v in get_metrics(out, label, slidingWindow=sliding).items()}


def write_scores(out, path):
    if path.endswith('.npy'):
        np.save(path, out.astype(np.float32))
    else:
        np.savetxt(path, out, fmt='%.6g', delimiter=',', header='score', comments='')
    return path


def build_parser():
    p = argparse.ArgumentParser(prog='tremor-score', description=__doc__.splitlines()[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument('csv', help='one CSV in the TSB-AD layout (channels..., Label)')
    p.add_argument('--scores', metavar='PATH', default=None,
                   help='write the per-timestamp score array here (.npy = float32, else CSV)')
    p.add_argument('--hp', default=None, metavar='JSON',
                   help='JSON dict overriding tremor.DEFAULT_HP (e.g. \'{"n_job": 4}\')')
    p.add_argument('--metric', default='VUS-PR', help='metric to print (default VUS-PR; "all" prints every one)')
    p.add_argument('--json', action='store_true', help='print one JSON object instead of a line of text')
    p.add_argument('--quiet', action='store_true', help='print nothing (use with --scores)')
    p.add_argument('--version', action='version', version='tremor %s' % __version__)
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    hp = json.loads(a.hp) if a.hp else {}
    unknown = set(hp) - set(DEFAULT_HP)
    if unknown:
        raise SystemExit('unknown hyper-parameter(s): %s' % ', '.join(sorted(unknown)))
    t0 = time.time()
    out, data, label = score(a.csv, hp)
    runtime = time.time() - t0

    res = {'file': os.path.basename(a.csv), 'n': int(len(out)), 'dims': int(data.shape[1]),
           'runtime_s': round(runtime, 3), 'tremor_version': __version__}
    if a.scores:
        res['scores'] = write_scores(out, a.scores)
    if label is not None:
        try:
            res.update(evaluate(out, data, label))
        except ImportError as e:               # TSB-AD not installed: scores still usable
            res['metrics_error'] = str(e)
    else:
        res['metrics_error'] = 'no Label column'

    if a.quiet:
        return 0
    if a.json:
        print(json.dumps(res, indent=1))
    elif a.metric == 'all':
        print(res['file'], ' '.join('%s=%.4f' % (k, v) for k, v in res.items() if isinstance(v, float)))
    elif a.metric in res:
        print('%s\t%s=%.4f\t(%d points, %dD, %.1fs)' % (res['file'], a.metric, res[a.metric],
                                                        res['n'], res['dims'], res['runtime_s']))
    else:
        print(json.dumps(res, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
