"""Tremor: confidence-weighted fusion of a discord detector (MMPAD) and a residual
detector (Sub-PCA) for the TSB-AD benchmark.  CPU-only, numpy/scipy/scikit-learn.

Univariate series (D == 1): rank-fuse MMPAD (n_neighbor=5) and Sub-PCA (period window,
all components): per series the detector whose score has the larger (prior + clipped excess
kurtosis) wins (hard chooser, prior 1 for MMPAD; power=2..4 gives a soft weighted mean of ranks),
and Sub-PCA may override MMPAD only if the z-score of its maximum is >= zfloor (3): a second
label-free signal that stops a peaked-but-flat residual score from winning.
Multivariate series (D > 1): MMPAD (n_dim=0.7, n_neighbor=15) alone -- the fusion with PCA
gained only +0.003 VUS-PR on the M Tuning subset at 2.6x runtime, so it is off by default
(`fuse_multivariate=True` turns it on).  Adaptivity comes from the series (dimensionality,
score shape); nothing depends on a dataset name or on labels.
"""
import numpy as np
from .fusion import fuse

DEFAULT_HP = dict(stat='kurt', power='hard', prior=(1.0, 0.0), zfloor=3.0, fuse_multivariate=False, n_job=1)


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
        else:
            s0 = mw.run_MMPAD(X, n_dim=0.7, n_neighbor=15, n_job=self.HP['n_job'])
            if not self.HP['fuse_multivariate']:
                return [np.asarray(s0, float).ravel()]
            s1 = mw.run_PCA(X, n_components=0.25)
        return [np.asarray(s0, float).ravel(), np.asarray(s1, float).ravel()]

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        comps = self._components(X)
        if len(comps) == 1:
            self.decision_scores_ = comps[0]; self.info_ = dict(weights=[1.0], confidence=[None])
        else:
            self.decision_scores_, self.info_ = fuse(comps, stat=self.HP['stat'], power=self.HP['power'], prior=self.HP['prior'], zfloor=self.HP['zfloor'])
        return self

    def decision_function(self, X):
        return self.fit(X).decision_scores_


def run_Tremor_Unsupervised(data, **HP):
    clf = Tremor(HP=HP)
    clf.fit(data)
    return np.asarray(clf.decision_scores_, dtype=float).ravel()
