"""Confidence-weighted rank fusion (label-free).

Each component score is rank-normalised to [0, 1] and weighted by its own peakedness
(default: excess kurtosis of the score vector, clipped at 0).  A flat score -- no confident
anomaly -- gets a small weight, a sharply peaked one dominates:

    fused = sum_i w_i * rank(s_i) / sum_i w_i,   w_i = (prior_i + conf(s_i) + eps) ** power

In the hard-chooser mode (power='hard') a second, independent label-free signal gates the
override: a non-anchor component may replace the anchor (component 0) only if its kurtosis
beats the anchor's (prior included) AND the z-score of its maximum, (max - mean) / std, is at
least `zfloor` -- a peaked score whose peak does not stand out (e.g. z-max 0.5) does not win.

Only the series-derived scores are used: no labels, no dataset names.
"""
import numpy as np
from scipy.stats import rankdata, kurtosis

EPS = 1e-6


def rank_norm(s):
    s = np.asarray(s, dtype=float).ravel()
    if not np.isfinite(s).all():
        fill = np.nanmin(s[np.isfinite(s)]) if np.isfinite(s).any() else 0.0
        s = np.where(np.isfinite(s), s, fill)
    return rankdata(s, method='average') / len(s)


def confidence(s, stat='kurt'):
    """Label-free peakedness of a score vector; 0 for a constant / degenerate score."""
    s = np.asarray(s, dtype=float).ravel()
    s = s[np.isfinite(s)]
    if len(s) < 4 or np.std(s) == 0:
        return 0.0
    if stat in ('kurt', 'logkurt'):
        k = float(kurtosis(s, fisher=True, bias=True))
        k = max(k, 0.0) if np.isfinite(k) else 0.0
        return float(np.log1p(k)) if stat == 'logkurt' else k
    if stat == 'zmax':
        return float(max((s.max() - s.mean()) / s.std() - 1.0, 0.0))
    raise ValueError(stat)


def zmax(s):
    """z-score of the maximum of a score vector, (max - mean) / std; 0 if degenerate."""
    s = np.asarray(s, dtype=float).ravel()
    s = s[np.isfinite(s)]
    if len(s) < 2 or np.std(s) == 0:
        return 0.0
    return float((s.max() - s.mean()) / s.std())


def fuse(scores, stat='kurt', power='hard', prior=(1.0, 0.0), zfloor=3.0):
    """scores: list of equal-length 1-D arrays (component 0 = the anchor detector).
    zfloor: in hard mode, minimum z-max a non-anchor component needs to override the anchor
    (None = no gate).  Returns (fused score in [0, 1], info dict with weights/confidences)."""
    ranks = [rank_norm(s) for s in scores]
    conf = np.array([confidence(s, stat) for s in scores], dtype=float)
    pri = np.asarray(prior, dtype=float)[: len(scores)]
    if power == 'hard':
        total = conf + pri
        zs = np.array([zmax(s) for s in scores], dtype=float)
        if zfloor is not None:
            total = np.where(np.arange(len(scores)) == 0, total, np.where(zs >= float(zfloor), total, -np.inf))
        chosen = int(np.argmax(total)) if np.isfinite(total).any() else 0
        w = np.zeros(len(scores)); w[chosen] = 1.0
        out = ranks[chosen]
        return out, dict(weights=w.tolist(), confidence=conf.tolist(), zmax=zs.tolist())
    else:
        w = (pri + conf + EPS) ** float(power)
    w = w / w.sum()
    out = np.zeros_like(ranks[0])
    for wi, r in zip(w, ranks):
        out += wi * r
    return out, dict(weights=w.tolist(), confidence=conf.tolist())
