"""Confidence-weighted rank fusion (label-free).

Each component score is rank-normalised to [0, 1] and weighted by its own peakedness
(default: excess kurtosis of the score vector, clipped at 0).  A flat score -- no confident
anomaly -- gets a small weight, a sharply peaked one dominates:

    fused = sum_i w_i * rank(s_i) / sum_i w_i,   w_i = (prior_i + conf(s_i) + eps) ** power

In the hard-chooser mode (power='hard') a second, independent label-free signal gates the
override: a non-anchor component may replace the anchor (component 0) only if its kurtosis
beats the anchor's (prior included) AND the z-score of its maximum, (max - mean) / std, is at
least `zfloor` -- a peaked score whose peak does not stand out (e.g. z-max 0.5) does not win.
When the kurtosis signal is uninformative -- every component's kurtosis is below `tau`, both
scores flat -- the chooser falls back to the `flat` rule: 'zmax' takes the component whose
maximum stands out most (highest z-max, the anchor's raised by `zprior`), 'residual' takes
component 1, 'mean' averages the ranks, 'none' keeps the anchor.
Components listed in `flat_only` (the point-anomaly component, index 2) do not count towards
flatness and never win the kurtosis contest: they take part in the flat fallback, where their
z-max competes with the others', and may replace the peaked winner only
through the `override` gates, all computed from the score arrays: 'pz' the point z-max is at
least `pzmin` (it found something), 'agree' at most `athr` of the point score's top-k positions
(k = `kfrac` * n) lie in the winner's top-k (the two detectors DISAGREE on where -- when they
agree, the context-aware winner is kept), 'spikes' the point score has at most `cthr` separate
runs above `sthr` (specific, not firing everywhere).  `override=None` disables the gates.

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


def topk_agreement(s_a, s_b, kfrac=0.01):
    """Fraction of s_a's top-k positions (k = kfrac * n, at least 1) that are in s_b's top-k."""
    def topk(s):
        s = np.nan_to_num(np.asarray(s, dtype=float).ravel(), nan=-np.inf)
        k = max(int(round(kfrac * len(s))), 1)
        return set(np.argpartition(-s, k - 1)[:k].tolist())
    a = topk(s_a)
    return len(a & topk(s_b)) / max(len(a), 1)


def spike_runs(s, sthr=10.0):
    """Number of separate contiguous runs of a score above sthr."""
    above = np.nan_to_num(np.asarray(s, dtype=float).ravel(), nan=-np.inf) > float(sthr)
    if not above.any():
        return 0
    return int(np.sum(above & ~np.concatenate([[False], above[:-1]])))


def override_gate(scores, zs, chosen, point, override, pzmin, kfrac, athr, sthr, cthr):
    """True iff every gate in `override` lets component `point` replace `chosen`."""
    for g in override or ():
        if g == 'pz':
            ok = zs[point] >= float(pzmin)
        elif g == 'agree':
            ok = topk_agreement(scores[point], scores[chosen], kfrac) <= float(athr)
        elif g == 'spikes':
            ok = spike_runs(scores[point], sthr) <= int(cthr)
        else:
            raise ValueError(g)
        if not ok:
            return False
    return True


def zmax(s):
    """z-score of the maximum of a score vector, (max - mean) / std; 0 if degenerate."""
    s = np.asarray(s, dtype=float).ravel()
    s = s[np.isfinite(s)]
    if len(s) < 2 or np.std(s) == 0:
        return 0.0
    return float((s.max() - s.mean()) / s.std())


def fuse(scores, stat='kurt', power='hard', prior=(1.0, 0.0, 0.0), zfloor=3.0, tau=0.5, flat='zmax', zprior=0.0, flat_only=(2,),
         override=('pz', 'agree', 'spikes'), pzmin=7.0, kfrac=0.01, athr=0.5, sthr=10.0, cthr=5):
    """scores: list of equal-length 1-D arrays (component 0 = the anchor detector).
    zfloor: in hard mode, minimum z-max a non-anchor component needs to override the anchor
    (None = no gate).  tau / flat / zprior: hard-mode fallback when every kurtosis < tau (see
    module docstring).  flat_only: indices of components that only enter the flat fallback (hard
    mode).  override / pzmin / kfrac / athr / sthr / cthr: gates under which the first flat_only
    component replaces the non-flat winner (see module docstring; override=None or () = never).
    Returns (fused score in [0, 1], info dict with weights/confidences)."""
    ranks = [rank_norm(s) for s in scores]
    conf = np.array([confidence(s, stat) for s in scores], dtype=float)
    pri = np.asarray(prior, dtype=float)[: len(scores)]
    if len(pri) < len(scores):
        pri = np.concatenate([pri, np.zeros(len(scores) - len(pri))])
    if power == 'hard':
        total = conf + pri
        zs = np.array([zmax(s) for s in scores], dtype=float)
        main = np.array([i not in set(flat_only or ()) for i in range(len(scores))])
        if not main.any():
            main[0] = True
        is_flat = bool(tau is not None and conf[main].max() < float(tau))
        if is_flat and flat == 'mean':
            w = np.ones(len(scores)) / len(scores)
            out = np.zeros_like(ranks[0])
            for wi, r in zip(w, ranks):
                out += wi * r
            return out, dict(weights=w.tolist(), confidence=conf.tolist(), zmax=zs.tolist(), flat=True)
        if is_flat and flat in ('residual', 'zmax'):
            if flat == 'residual':
                chosen = 1 if len(scores) > 1 else 0
            else:
                zz = zs.copy(); zz[0] += float(zprior)
                chosen = int(np.argmax(zz))
            w = np.zeros(len(scores)); w[chosen] = 1.0
            return ranks[chosen], dict(weights=w.tolist(), confidence=conf.tolist(), zmax=zs.tolist(), flat=True)
        if zfloor is not None:
            total = np.where(np.arange(len(scores)) == 0, total, np.where(zs >= float(zfloor), total, -np.inf))
        total = np.where(main, total, -np.inf)
        chosen = int(np.argmax(total)) if np.isfinite(total).any() else 0
        overridden = False
        pts = [i for i in (flat_only or ()) if i < len(scores)]
        if override and pts and chosen not in pts and override_gate(scores, zs, chosen, pts[0], override, pzmin, kfrac, athr, sthr, cthr):
            chosen, overridden = pts[0], True
        w = np.zeros(len(scores)); w[chosen] = 1.0
        out = ranks[chosen]
        return out, dict(weights=w.tolist(), confidence=conf.tolist(), zmax=zs.tolist(), flat=is_flat, override=overridden)
    else:
        w = (pri + conf + EPS) ** float(power)
    w = w / w.sum()
    out = np.zeros_like(ranks[0])
    for wi, r in zip(w, ranks):
        out += wi * r
    return out, dict(weights=w.tolist(), confidence=conf.tolist())
