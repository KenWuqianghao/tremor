"""Point-anomaly component of Tremor: robust z-score of the first differences.

    z_t = |dx_t - median(dx)| / (1.4826 * MAD(dx)),   dx_t = x_t - x_{t-1}

optionally after a short moving-average pre-smoothing of x (`presmooth` points), then a
centred max-filter of `window` points so an isolated spike covers its event:
window='period' uses the benchmark's own ACF period estimate (find_length_rank, computed
from the series -- exactly what Sub-PCA / the scorer use), 'half' = period // 2, an int is
taken as is, 1 = no filter.  If the MAD is 0 (integer-valued / mostly constant series) the
scaled mean absolute deviation is used, then the std, then 1.  Cost: O(n).  Series-derived
only: no labels, no dataset names.  Multivariate input: the first channel only (the M path of
Tremor does not use this component).
"""
import numpy as np
from scipy.ndimage import maximum_filter1d, uniform_filter1d


def period_of(x):
    from TSB_AD.utils.slidingWindows import find_length_rank
    return int(find_length_rank(np.asarray(x, float).reshape(-1, 1), rank=1))


def resolve_window(x, window):
    if window in (None, 1, '1', 'none'):
        return 1
    if window == 'period':
        return max(int(period_of(x)), 1)
    if window == 'half':
        return max(int(period_of(x)) // 2, 1)
    return max(int(window), 1)


def point_score(x, window='period', presmooth=0):
    x = np.asarray(x, dtype=float).ravel()
    if len(x) < 3:
        return np.zeros(len(x))
    xs = uniform_filter1d(x, int(presmooth), mode='nearest') if presmooth and int(presmooth) > 1 else x
    dx = np.diff(xs, prepend=xs[0])
    med = np.median(dx)
    dev = np.abs(dx - med)
    scale = 1.4826 * np.median(dev)
    if not scale > 0:
        scale = 1.2533 * np.mean(dev)
    if not scale > 0:
        scale = np.std(dx)
    if not scale > 0:
        scale = 1.0
    z = dev / scale
    w = resolve_window(x, window)
    if w > 1:
        z = maximum_filter1d(z, size=w, mode='nearest')
    return z


def run(data, window='period', presmooth=0, **_):
    data = np.asarray(data, dtype=float)
    if data.ndim == 2:
        data = data[:, 0]
    return point_score(data, window=window, presmooth=presmooth)
