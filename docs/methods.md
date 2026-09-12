# What the reference methods do

Read from the upstream source at commit 6beac72, before writing any code of my own.

## MMPAD (`TSB_AD/models/MMPAD.py`, `TSB_AD/models/mmpad/`) — Yeh, arXiv 2604.02445
Matrix-profile discord detector with three additions over the plain `MatrixProfile` baseline.
1. **Window**: `sub_len = max(64, find_length_rank(zscore(channel0), rank=1))` (ACF period of the
   first channel, floor 64). Series are z-scored per channel (ddof=0) before profiling.
2. **Multidimensional profile with pre-sorting** (`sorting_place='pre'`): for every query
   subsequence the z-normalised *correlation* profile is computed per channel (MASS / STOMP
   update), the per-channel profiles are sorted at each position across channels, and the
   `n_dim`-th best (with `n_dim = ceil(0.7 * D)` on M, 1 on U) is used, i.e. an
   order-statistic aggregation over channels rather than a sum.
3. **k-NN with exclusion zones** (`n_neighbor` = 5 on U, 15 on M; `find_knn_2`): the score of a
   subsequence is the correlation to its k-th nearest neighbour, with an exclusion zone of
   `0.5 * sub_len` around each chosen neighbour and around the query (self-join). A pattern
   that repeats fewer than k times still scores as anomalous ("repeated anomalies").
4. **Post-processing** (`post_processing=2`): score = -corr (so higher = more anomalous),
   min-max scaled over finite entries, then a *forward-looking moving average of length
   sub_len* over the padded subsequence scores (`nanmean(score[i:i+sub_len])`), which spreads
   each subsequence score over all the points it covers.
5. **Budget**: if `n_eff^2 * n_dim * log2(max(n_dim,2)) > 1.142528e13` the series is
   downsampled 2x (repeatedly) and the score linearly upsampled; only one Eval series
   (M) triggers it.
Complexity O(n^2 * D) with a Python loop over n subsequences; measured 16.5 ns per proxy-cost
unit single-core on my 4-core box (n=59k univariate: 59 s; n_job=4 gives only 2x).

## Sub-PCA / PCA (`TSB_AD/models/PCA.py`, pyod-style)
Sliding windows of length `slidingWindow` (Sub_PCA: ACF period via `find_length_rank(rank=1)`;
multivariate PCA: 100) are flattened into vectors (`feature.Window.convert`), z-scored
(univariate: per column over windows; multivariate: per row), zero columns pruned, then
sklearn PCA with all components (U) or 25% variance (M). Score = sum over the *selected*
components (all, by default) of `cdist(X, component) / explained_variance_ratio`, i.e. a
distance to each eigenvector weighted by 1/variance — dominated by low-variance directions,
so it is a reconstruction-residual-like detector. Scores are padded to full length by
repeating the first/last value. Runtime is negligible (seconds).

## KShapeAD (`run_KShapeAD` -> `SAND.fit(online=False)`)
Offline SAND: subsequences of length `4 * period` (period from ACF), k-Shape clustering
(tslearn, shape-based distance) into k=6 clusters over a batch of subsequences, weighted
centroids form the "normal model" Theta, and each subsequence's anomaly score is its
shape-based distance to the nearest weighted centroid. Runtime is dominated by tslearn
k-Shape (numpy backend here): ~50 s for a 4k-point series, minutes for long series.

## MatrixProfile (`run_MatrixProfile` -> `stumpy.stump`)
Plain self-join matrix profile (Euclidean, z-normalised) with window = ACF period, nearest
neighbour only, score = profile value centred on the window. This is the 0.35 baseline;
MMPAD's +0.09 on U comes from k-NN, the length-64 floor, and the moving-average smoothing.
