"""Point-anomaly component of Tremor for multivariate series: the univariate point score of
point.py on every channel, aggregated per timestamp.

For each channel j: z_j = robust z of the first differences, |dx - median| / (1.4826 MAD),
centred max-filter over that channel's own ACF period (the benchmark's find_length_rank).
Aggregation `agg`:
  'maxz'    : max over channels of the raw robust z (each channel is already in MAD
              units, so a spike in ANY one sensor is a point anomaly of the system)
  'maxrank' : max over channels of the per-channel rank-normalised score
  'top3z'   : mean of the three largest per-channel z at each timestamp (default: the best of the
              three on the M Tuning files, both alone and inside the chooser)
Channels whose score is constant are left out.  O(n D).  Series-derived only: no labels, no
dataset names.
"""
import numpy as np
from scipy.stats import rankdata
from .point import point_score


def channel_scores(X, window='period'):
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    out = []
    for j in range(X.shape[1]):
        z = point_score(X[:, j], window=window)
        if np.isfinite(z).all() and np.std(z) > 0:
            out.append(z)
    if not out:
        out = [np.zeros(X.shape[0])]
    return np.stack(out, axis=1)   # n x D'


def point_m_score(X, window='period', agg='maxz'):
    Z = channel_scores(X, window=window)
    if agg == 'maxz':
        return Z.max(axis=1)
    if agg == 'maxrank':
        R = np.stack([rankdata(Z[:, j], method='average') / Z.shape[0] for j in range(Z.shape[1])], axis=1)
        return R.max(axis=1)
    if agg == 'top3z':
        k = min(3, Z.shape[1])
        return np.sort(Z, axis=1)[:, -k:].mean(axis=1)
    raise ValueError(agg)
