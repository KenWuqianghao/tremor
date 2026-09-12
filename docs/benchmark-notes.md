# TSB-AD benchmark notes (verbatim quotes from upstream, commit 6beac72e11d1155ade40870492c00d0d1cfdcaaf, 2026-09-07)

Everything below is quoted from the upstream clone in `upstream/` (gitignored), so the exact
wording of the protocol is in the repository without re-reading upstream. Section headers are
mine; the fenced blocks are verbatim.

## 1. Datasets and splits

From `README.md`:

> Due to limitations in the upload size on GitHub, we host the datasets at a different location. Please download the datasets using the following links:
> * TSB-AD-U: https://www.thedatum.org/datasets/TSB-AD-U.zip
> * TSB-AD-M: https://www.thedatum.org/datasets/TSB-AD-M.zip
> The split of Tuning and Eval set in our benchmark study is available at [[Link]](https://github.com/TheDatumOrg/TSB-AD/tree/main/Datasets/File_List/).

File lists (`Datasets/File_List/`): `TSB-AD-U-Tuning.csv` (48 series), `TSB-AD-U-Eva.csv`
(350 series), `TSB-AD-M-Tuning.csv` (20 series), `TSB-AD-M-Eva.csv` (180 series).
(`TSB-AD-U-Eva-Full.csv` has 822 series; the leaderboard uses the 350-series `TSB-AD-U-Eva.csv`.)

Local copies: `data/TSB-AD-U/` (870 csv) and `data/TSB-AD-M/` (200 csv), gitignored.
File name convention: `<id>_<Dataset>_id_<k>_<Domain>_tr_<train_index>_1st_<first_anomaly>.csv`;
columns = channels then `Label`.

## 2. Loading and scoring protocol (`benchmark_exp/Run_Detector_U.py`, identical in `_M.py`)

```python
file_list = pd.read_csv(args.file_lsit)['file_name'].values
Optimal_Det_HP = Optimal_Uni_algo_HP_dict[args.AD_Name]
...
    df = pd.read_csv(file_path).dropna()
    data = df.iloc[:, 0:-1].values.astype(float)
    label = df['Label'].astype(int).to_numpy()

    feats = data.shape[1]
    slidingWindow = find_length_rank(data[:,0].reshape(-1, 1), rank=1)
    train_index = filename.split('.')[0].split('_')[-3]
    data_train = data[:int(train_index), :]

    start_time = time.time()

    if args.AD_Name in Semisupervise_AD_Pool:
        output = run_Semisupervise_AD(args.AD_Name, data_train, data, **Optimal_Det_HP)
    elif args.AD_Name in Unsupervise_AD_Pool:
        output = run_Unsupervise_AD(args.AD_Name, data, **Optimal_Det_HP)
    else:
        raise Exception(f"{args.AD_Name} is not defined")

    end_time = time.time()
    run_time = end_time - start_time
    ...
            evaluation_result = get_metrics(output, label, slidingWindow=slidingWindow)
```

Seeding in the same script: `seed = 2024` (torch / numpy / random).

`run_Unsupervise_AD` (`TSB_AD/model_wrapper.py`) wraps the call in `try/except` and returns
an error *string* on failure; the runner then logs the error and (with `--save`) writes
`[0]*9` metrics for that file. A crash therefore scores 0 on that series.

## 3. Sliding window used by the metric (`TSB_AD/utils/slidingWindows.py`)

```python
# determine sliding window (period) based on ACF
def find_length_rank(data, rank=1):
    data = data.squeeze()
    if len(data.shape)>1: return 0
    if rank==0: return 1
    data = data[:min(20000, len(data))]

    base = 3
    auto_corr = acf(data, nlags=400, fft=True)[base:]
    local_max = argrelextrema(auto_corr, np.greater)[0]
    try:
        sorted_local_max = np.argsort([auto_corr[lcm] for lcm in local_max])[::-1]    # Ascending order
        max_local_max = sorted_local_max[0]     # Default
        if rank == 1: max_local_max = sorted_local_max[0]
        if rank == 2:
            for i in sorted_local_max[1:]:
                if i > sorted_local_max[0]:
                    max_local_max = i
                    break
        if rank == 3:
            ...
        final_period = local_max[max_local_max]+base
        if final_period>300:
            return 125
        return final_period
    except:
        return 125
```

## 4. Metric: VUS-PR (`TSB_AD/evaluation/metrics.py` + `basic_metrics.py`)

`get_metrics` (the only scoring entry point I call; `thre=250`, `version='opt'`):

```python
def get_metrics(score, labels, slidingWindow=100, pred=None, version='opt', thre=250):
    metrics = {}
    grader = basic_metricor()
    AUC_ROC = grader.metric_ROC(labels, score)
    AUC_PR = grader.metric_PR(labels, score)
    _, _, _, _, _, _,VUS_ROC, VUS_PR = generate_curve(labels.astype(int), score, slidingWindow, version, thre)
    PointF1 = grader.metric_PointF1(labels, score, preds=pred)
    PointF1PA = grader.metric_PointF1PA(labels, score, preds=pred)
    EventF1PA = grader.metric_EventF1PA(labels, score, preds=pred)
    RF1 = grader.metric_RF1(labels, score, preds=pred)
    Affiliation_F = grader.metric_Affiliation(labels, score, preds=pred)
    metrics['AUC-PR'] = AUC_PR
    metrics['AUC-ROC'] = AUC_ROC
    metrics['VUS-PR'] = VUS_PR
    metrics['VUS-ROC'] = VUS_ROC
    ...
    return metrics
```

```python
def generate_curve(label, score, slidingWindow, version='opt', thre=250):
    if version =='opt_mem':
        tpr_3d, fpr_3d, prec_3d, window_3d, avg_auc_3d, avg_ap_3d = basic_metricor().RangeAUC_volume_opt_mem(labels_original=label, score=score, windowSize=slidingWindow, thre=thre)
    else:
        tpr_3d, fpr_3d, prec_3d, window_3d, avg_auc_3d, avg_ap_3d = basic_metricor().RangeAUC_volume_opt(labels_original=label, score=score, windowSize=slidingWindow, thre=thre)
    ...
    return Y, Z, X, X_ap, W, Z_ap,avg_auc_3d, avg_ap_3d
```

The volume itself (`basic_metricor.RangeAUC_volume_opt`), verbatim:

```python
    def RangeAUC_volume_opt(self, labels_original, score, windowSize, thre=250):
        window_3d = np.arange(0, windowSize + 1, 1)
        P = np.sum(labels_original)
        seq = self.range_convers_new(labels_original)
        l = self.new_sequence(labels_original, seq, windowSize)

        score_sorted = -np.sort(-score)

        tpr_3d = np.zeros((windowSize + 1, thre + 2))
        fpr_3d = np.zeros((windowSize + 1, thre + 2))
        prec_3d = np.zeros((windowSize + 1, thre + 1))

        auc_3d = np.zeros(windowSize + 1)
        ap_3d = np.zeros(windowSize + 1)

        tp = np.zeros(thre)
        N_pred = np.zeros(thre)

        for k, i in enumerate(np.linspace(0, len(score) - 1, thre).astype(int)):
            threshold = score_sorted[i]
            pred = score >= threshold
            N_pred[k] = np.sum(pred)

        for window in window_3d:

            labels_extended = self.sequencing(labels_original, seq, window)
            L = self.new_sequence(labels_extended, seq, window)

            TF_list = np.zeros((thre + 2, 2))
            Precision_list = np.ones(thre + 1)
            j = 0

            for i in np.linspace(0, len(score) - 1, thre).astype(int):
                threshold = score_sorted[i]
                pred = score >= threshold
                labels = labels_extended.copy()
                existence = 0

                for seg in L:
                    labels[seg[0]:seg[1] + 1] = labels_extended[seg[0]:seg[1] + 1] * pred[seg[0]:seg[1] + 1]
                    if (pred[seg[0]:(seg[1] + 1)] > 0).any():
                        existence += 1
                for seg in seq:
                    labels[seg[0]:seg[1] + 1] = 1

                TP = 0
                N_labels = 0
                for seg in l:
                    TP += np.dot(labels[seg[0]:seg[1] + 1], pred[seg[0]:seg[1] + 1])
                    N_labels += np.sum(labels[seg[0]:seg[1] + 1])

                TP += tp[j]
                FP = N_pred[j] - TP

                existence_ratio = existence / len(L)

                P_new = (P + N_labels) / 2
                recall = min(TP / P_new, 1)

                TPR = recall * existence_ratio
                N_new = len(labels) - P_new
                FPR = FP / N_new

                Precision = TP / N_pred[j]

                j += 1
                TF_list[j] = [TPR, FPR]
                Precision_list[j] = Precision

            TF_list[j + 1] = [1, 1]  # otherwise, range-AUC will stop earlier than (1,1)

            tpr_3d[window] = TF_list[:, 0]
            fpr_3d[window] = TF_list[:, 1]
            prec_3d[window] = Precision_list

            width = TF_list[1:, 1] - TF_list[:-1, 1]
            height = (TF_list[1:, 0] + TF_list[:-1, 0]) / 2
            AUC_range = np.dot(width, height)
            auc_3d[window] = (AUC_range)

            width_PR = TF_list[1:-1, 0] - TF_list[:-2, 0]
            height_PR = Precision_list[1:]

            AP_range = np.dot(width_PR, height_PR)
            ap_3d[window] = AP_range

        return tpr_3d, fpr_3d, prec_3d, window_3d, sum(auc_3d) / len(window_3d), sum(ap_3d) / len(window_3d)
```

Label-smoothing helper (`sequencing`), verbatim:

```python
    def sequencing(self, x, L, window=5):
        label = x.copy().astype(float)
        length = len(label)

        for k in range(len(L)):
            s = L[k][0]
            e = L[k][1]

            x1 = np.arange(e + 1, min(e + window // 2 + 1, length))
            label[x1] += np.sqrt(1 - (x1 - e) / (window))

            x2 = np.arange(max(s - window // 2, 0), s)
            label[x2] += np.sqrt(1 - (s - x2) / (window))

        label = np.minimum(np.ones(length), label)
        return label
```

Practical consequences (mine, not quoted): VUS-PR is the average over buffer widths
0..slidingWindow of a range-aware average precision computed on only 250 score thresholds
(quantiles of the score). Only the *ranking* of scores matters; monotone rescaling has no
effect. Buffers extend each anomaly by up to slidingWindow/2 on each side with sqrt
decay, so a score peak that leads or lags the anomaly by less than half the ACF period
still earns credit. `existence_ratio` multiplies recall: detecting a piece of every
event matters more than covering long events fully.

`benchmark_eval_results/README.md`:

> Evaluation results computed based on the lasted version of [VUS](https://arxiv.org/abs/2502.13318).
> The implemention in [`get_metrics`](https://github.com/TheDatumOrg/TSB-AD/blob/dce9e5e5ec14ffb82787315dbf1a8564c7bb9f47/TSB_AD/evaluation/metrics.py#L3) is up-to-date.

## 5. Model interface (`benchmark_exp/README.md`)

> Your detector should subclass `BaseDetector` (`TSB_AD/models/base.py`) and expose:
> * `fit(X)` and `decision_function(X)`, where `X` has shape `(n_samples, n_features)`
> * a `decision_scores_` attribute (one anomaly score per timestamp; higher = more anomalous)
>
> and be wrapped by a runner that returns a 1-D score array the same length as the input:
> * `run_<Name>_Unsupervised(data, **HP)` — fits and scores the same series, **or**
> * `run_<Name>_Semisupervised(data_train, data_test, **HP)` — fits on the (anomaly-free) train prefix, scores the test series

`BaseDetector` (`TSB_AD/models/base.py`) attributes, verbatim from the docstring:

> decision_scores_ : numpy array of shape (n_samples,)
>     The outlier scores of the training data.
>     The higher, the more abnormal. Outliers tend to have higher
>     scores. This value is available once the detector is fitted.

Template `benchmark_exp/Run_Custom_Detector.py` (runner part):

```python
def run_Custom_AD_Unsupervised(data, HP):
    clf = Custom_AD(HP=HP)
    clf.fit(data)
    score = clf.decision_scores_
    score = MinMaxScaler(feature_range=(0,1)).fit_transform(score.reshape(-1,1)).ravel()
    return score

def run_Custom_AD_Semisupervised(data_train, data_test, HP):
    clf = Custom_AD(HP=HP)
    clf.fit(data_train)
    score = clf.decision_function(data_test)
    score = MinMaxScaler(feature_range=(0,1)).fit_transform(score.reshape(-1,1)).ravel()
    return score
```

## 6. Submission steps (`benchmark_exp/README.md`)

> ### The first way — submit a single self-contained script
>
> Add one `Run_Custom_Detector.py`-style file in this folder (see `Run_Custom_Detector.py` for a template):
> * **Step 1**: Implement the `Custom_AD` class
> * **Step 2**: Implement the runner `run_Custom_AD_Unsupervised` or `run_Custom_AD_Semisupervised`
> * **Step 3**: Specify the `Custom_AD_HP` hyper-parameter dict
>
> ### The second way — integrate into the repo (preferred for leaderboard inclusion)
>
> * **Step 1**: Add `Custom_AD.py` under `TSB_AD/models/`
> * **Step 2**: In `TSB_AD/model_wrapper.py`, add the runner `run_Custom_AD_Unsupervised` / `run_Custom_AD_Semisupervised`, **and** register the model name in `Unsupervise_AD_Pool` or `Semisupervise_AD_Pool` (the `Run_Detector_U/M.py` dispatcher raises if the name is in neither pool)
> * **Step 3**: In `TSB_AD/HP_list.py`, add the hyper-parameters:
>     * `Optimal_Uni_algo_HP_dict` / `Optimal_Multi_algo_HP_dict` — the single best config used by `Run_Detector_U/M.py` (required)
>     * `Uni_algo_HP_dict` / `Multi_algo_HP_dict` — the search grid used by `HP_Tuning_U/M.py` (optional)
> * **Step 4**: Apply a threshold to the anomaly score (if any)
> * **Step 5**: Verify with `Run_Detector_U.py`/`Run_Detector_M.py` and submit your evaluation results [here](https://github.com/thedatumorg/TSB-AD/tree/main/benchmark_exp/leaderboard_results); once verified we will add it to the [🏆 Leaderboard](https://thedatumorg.github.io/TSB-AD/#leaderboard)
>
> 💡 Models are imported lazily inside `model_wrapper.py` (e.g. `from .models.Custom_AD import Custom_AD`), so a heavy or optional dependency only loads when its detector is actually selected.
>
> 🪧 **How to contribute your algorithm to TSB-AD**: open a pull request to the `main` branch following the steps above. We will test and evaluate the algorithm and include it in our [leaderboard](https://thedatumorg.github.io/TSB-AD/).

Leaderboard result files (`benchmark_exp/leaderboard_results/Uni_<Name>.csv`,
`Multi_<Name>.csv`) are per-series rows with columns
`file,Time,AUC-PR,AUC-ROC,VUS-PR,VUS-ROC,Standard-F1,PA-F1,Event-based-F1,R-based-F1,Affiliation-F`
(some community files use a wide `file,<Name>,ts_len,...` layout).

## 7. Reference hyper-parameters reproduced here (`TSB_AD/HP_list.py`)

```python
Optimal_Uni_algo_HP_dict = {
    ...
    'MatrixProfile': {'periodicity': 1},
    'Sub_PCA': {'periodicity': 1, 'n_components': None},
    'KShapeAD': {'periodicity': 1},
    'MMPAD': {'n_neighbor': 5},
    ...
}
Optimal_Multi_algo_HP_dict = {
    ...
    'PCA': {'n_components': 0.25},
    'KShapeAD': {'n_clusters': 20, 'window_size': 40},
    'MMPAD': {'n_dim': 0.7, 'n_neighbor': 15},
    ...
}
```

`run_Sub_PCA(data, periodicity=1, n_components=None, n_jobs=1)` uses
`slidingWindow = find_length_rank(data, rank=periodicity)`; `run_PCA(data, slidingWindow=100,
n_components=None, n_jobs=1)` is the multivariate counterpart (there is no Sub-PCA row on the
M track; the paper's "PCA" on TSB-AD-M is this runner with slidingWindow=100).
`run_MMPAD(data, periodicity=1, n_dim=None, n_neighbor=1, sorting_place='pre', mode='discord',
post_processing=2, n_job=None, backend=None)`; `n_job=None` -> `cpu_count()-1`, and the
`MMPAD_DEFAULT_TIME_BUDGET = 1.142528e13` proxy-cost budget triggers 2x downsampling of a
series whose `(n_eff^2 * n_dim * log2(max(n_dim,2)))` exceeds it (comment in
`mmpad/util.py`: "corresponds to the current 24-hour runtime target on the c5.4xlarge setup
in use ... effective n_job=14").

## 8. The rules I hold myself to

* Tune only on the Tuning lists. Eval is scored once up front (to reproduce the reference
  methods) and afterwards only as a held-out check, never fed back into a decision.
* Use `get_metrics` exactly as in section 2 (slidingWindow from channel 0, rank 1). Never
  reimplement VUS-PR.
* No behaviour keyed on dataset name; adaptivity must be computed from the series.
