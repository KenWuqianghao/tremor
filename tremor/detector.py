"""Tremor: confidence-weighted fusion of a discord detector (MMPAD), a residual
detector (Sub-PCA) and a point-anomaly detector for the TSB-AD benchmark.  CPU-only, numpy/scipy/scikit-learn.

Univariate series (D == 1): rank-fuse MMPAD (n_neighbor=5) and Sub-PCA (period window,
all components): per series the detector whose score has the larger (prior + clipped excess
kurtosis) wins (hard chooser, prior 1 for MMPAD; power=2..4 gives a soft weighted mean of ranks),
and Sub-PCA may override MMPAD only if the z-score of its maximum is >= zfloor (3): a second
label-free signal that stops a peaked-but-flat residual score from winning.  When neither score
is peaked (both kurtoses < tau, 0.5) the kurtosis prior is uninformative and the detector whose
maximum stands out most (higher z-max) is taken instead (`flat='zmax'`).  A third, O(n) point-anomaly
component (`point.py`: robust z-score of the first differences, max-filtered over the ACF period,
`point_window='period'`) takes part in that flat fallback (`flat_only=(2,)`): where neither
MMPAD nor Sub-PCA found anything, the spike detector wins if its maximum stands out most.  It may
also replace a peaked winner, but only through three label-free gates (`override`): its z-max is
>= pzmin (7), at most athr (0.5) of its top-1% positions lie in the winner's top-1% (the detectors
disagree on where), and it has at most cthr (5) separate runs above sthr (10) -- a few strong,
isolated spikes the context-aware detectors missed.
Multivariate series (D > 1): the same chooser over two components, MMPAD-M
(n_dim=0.7, n_neighbor=15, the anchor) and point-M (`point_m.py`: the point score of every
channel, mean of the three largest per-channel robust z per timestamp, `point_m_agg='top3z'`),
with point-M as the flat_only member (`flat_only_m=(1,)`): it never wins the kurtosis contest
(no Sub-PCA on M) and it takes part in the flat fallback (MMPAD-M's kurtosis < tau -> the higher
z-max wins).  The univariate override gates are OFF on M (`override_m=None`): the channel
aggregation compresses the point-M z scale, so the univariate thresholds do not transfer (on the
M Tuning files they fired once, wrongly).  `point_m_agg=None` restores MMPAD-M alone.  The earlier MMPAD-M + PCA fusion (`fuse_multivariate=True`, +0.003 at 2.6x runtime)
stays off.  Adaptivity comes from the series (dimensionality, score shape); nothing depends on
a dataset name or on labels.
"""
import numpy as np
from .fusion import fuse
from .point import point_score
from .point_m import point_m_score

DEFAULT_HP = dict(stat='kurt', power='hard', prior=(1.0, 0.0, 0.0), zfloor=3.0, tau=0.5, flat='zmax', zprior=0.0,
                  point_window='period', flat_only=(2,), override=('pz', 'agree', 'spikes'), pzmin=7.0, kfrac=0.01, athr=0.5,
                  sthr=10.0, cthr=5, fuse_multivariate=False, point_m_agg='top3z', flat_only_m=(1,), override_m=None, n_job=1)


class Tremor:
    """TSB-AD-style detector: fit(X) sets decision_scores_ (one score per timestamp)."""

    def __init__(self, HP=None, **kw):
        hp = dict(DEFAULT_HP); hp.update(HP or {}); hp.update(kw)
        self.HP = hp
        self.decision_scores_ = None
        self.info_ = None

    def _components(self, X):
        import TSB_AD.model_wrapper as mw   # lazy: heavy import
        if X.shape[1] == 1:
            s0 = mw.run_MMPAD(X, n_neighbor=5, n_job=self.HP['n_job'])
            s1 = mw.run_Sub_PCA(X, periodicity=1, n_components=None)
            if self.HP['point_window'] is not None:
                s2 = point_score(X[:, 0], window=self.HP['point_window'])
                return [np.asarray(s0, float).ravel(), np.asarray(s1, float).ravel(), np.asarray(s2, float).ravel()]
        else:
            s0 = mw.run_MMPAD(X, n_dim=0.7, n_neighbor=15, n_job=self.HP['n_job'])
            if self.HP['fuse_multivariate']:
                s1 = mw.run_PCA(X, n_components=0.25)
            elif self.HP['point_m_agg'] is not None:
                s1 = point_m_score(X, window=self.HP['point_window'] or 'period', agg=self.HP['point_m_agg'])
            else:
                return [np.asarray(s0, float).ravel()]
        return [np.asarray(s0, float).ravel(), np.asarray(s1, float).ravel()]

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        comps = self._components(X)
        uni = X.shape[1] == 1 or self.HP['fuse_multivariate']
        flat_only = self.HP['flat_only'] if uni else self.HP['flat_only_m']
        override = self.HP['override'] if uni else self.HP['override_m']
        if len(comps) == 1:
            self.decision_scores_ = comps[0]; self.info_ = dict(weights=[1.0], confidence=[None])
        else:
            self.decision_scores_, self.info_ = fuse(comps, stat=self.HP['stat'], power=self.HP['power'], prior=self.HP['prior'], zfloor=self.HP['zfloor'],
                                                       tau=self.HP['tau'], flat=self.HP['flat'], zprior=self.HP['zprior'], flat_only=flat_only,
                                                       override=override, pzmin=self.HP['pzmin'], kfrac=self.HP['kfrac'], athr=self.HP['athr'],
                                                       sthr=self.HP['sthr'], cthr=self.HP['cthr'])
        return self

    def decision_function(self, X):
        return self.fit(X).decision_scores_


def run_Tremor_Unsupervised(data, **HP):
    clf = Tremor(HP=HP)
    clf.fit(data)
    return np.asarray(clf.decision_scores_, dtype=float).ravel()
