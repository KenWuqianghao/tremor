# Submitting Tremor to the TSB-AD leaderboard (U track only)

The upstream steps are quoted in `docs/benchmark-notes.md`, section 6: "the second way —
integrate into the repo (preferred for leaderboard inclusion)".  This file is the concrete
version of them for Tremor, plus the PR text.  **Only TSB-AD-U is claimed.  The M path ships in
the package but no M number is submitted** — see the last section for why.

## Steps

```bash
# 1. fork and clone TSB-AD, on a branch
gh repo fork TheDatumOrg/TSB-AD --clone --remote
cd TSB-AD && git checkout -b tremor

# 2. the detector itself: copy the package in as a model module
cp -r /path/to/tremor/tremor TSB_AD/models/tremor
#    (tremor/ has no TSB_AD-relative imports except the lazy ones in detector.py and
#     point.py, which resolve the same way from inside the package)

# 3. TSB_AD/model_wrapper.py -- add the runner and REGISTER the name in the pool
#    (Run_Detector_U.py raises if the name is in neither pool):
#      Unsupervise_AD_Pool = [..., 'Tremor']
#      def run_Tremor(data, **HP):
#          from .models.tremor import run_Tremor_Unsupervised
#          return run_Tremor_Unsupervised(data, **HP)

# 4. TSB_AD/HP_list.py -- the single best config used by Run_Detector_U.py:
#      Optimal_Uni_algo_HP_dict['Tremor']   = Tremor_HP    # verbatim from benchmark_exp/Run_Tremor.py
#      Optimal_Multi_algo_HP_dict['Tremor'] = Tremor_HP    # same dict; the M path is the D > 1 branch

# 5. the self-contained script the submission guide also asks for
cp /path/to/tremor/benchmark_exp/Run_Tremor.py benchmark_exp/Run_Tremor.py

# 6. verify with the benchmark's own runner before opening anything
python benchmark_exp/Run_Detector_U.py --AD_Name Tremor \
    --file_lsit Datasets/File_List/TSB-AD-U-Eva.csv --save True
#    (the flag really is spelled --file_lsit upstream)

# 7. the per-series results file the maintainers ask for
#    benchmark_exp/leaderboard_results/Uni_Tremor.csv
#    columns: file,Time,AUC-PR,AUC-ROC,VUS-PR,VUS-ROC,Standard-F1,PA-F1,Event-based-F1,R-based-F1,Affiliation-F
#    A run made with this repository's harness already has every one of those per file:
python /path/to/tremor/harness/report.py /path/to/tremor/runs/U_eval_Tremor --ref leaderboard:Uni_MMPAD

git add -A && git commit -m "Add Tremor (CPU-only chooser over MMPAD, Sub-PCA and a point detector)"
git push -u origin tremor
gh pr create --repo TheDatumOrg/TSB-AD --base main \
    --title "Add Tremor: a CPU-only chooser over MMPAD, Sub-PCA and a point-anomaly detector"
```

## PR text

> ### Add Tremor: a CPU-only chooser over MMPAD, Sub-PCA and a point-anomaly detector
>
> **What it is.**  Tremor is a per-series, label-free chooser over three existing CPU
> components: MMPAD (`n_neighbor=5`) as the anchor, Sub-PCA (`periodicity=1`) as the residual
> detector, and an O(n) point-anomaly score (robust z of the first differences, max-filtered over
> the benchmark's own ACF period).  On each series it outputs the rank-normalised score of one of
> the three; the choice uses only the excess kurtosis and z-max of the detectors' own score
> arrays, the top-1% overlap between them, and a run count.  No training, no pretraining, no
> GPU, no dataset-name special-casing.  Runtime is 1.00-1.02x MMPAD.
>
> **The number.**  On the full TSB-AD-U Eval list (350/350 files, 0 failures), Tremor's mean
> VUS-PR is **0.6085**, next to the published MMPAD 0.4399 (+0.1686) and Sub-PCA 0.4234
> (+0.1851) on the same files.  Per file: 137 higher than MMPAD, 38 lower, 175 equal.  Scores
> were produced by `TSB_AD.evaluation.metrics.get_metrics` with
> `find_length_rank(data[:,0], rank=1)`, exactly as `Run_Detector_U.py` does; the reference
> values are the per-series files in `benchmark_exp/leaderboard_results/` and
> `benchmark_eval_results/` at commit 6beac72.
>
> **Reproduction anchor.**  My MMPAD-U reproduction with the upstream CPU code scored 0.4749 vs
> the published 0.4752 on the same 148 series (147/148 within 0.01), so the comparison above is
> like-for-like.
>
> **Where the hyper-parameters come from.**  The 47-of-48-file TSB-AD-U Tuning set only, with
> every threshold sitting on a measured plateau (table in the repository README, full history in
> its EXPERIMENTS.md).  The Eval list was scored as a held-out check and never fed back into a
> decision.  The Eval mean (0.6085) is below the Tuning mean (0.6713), as expected of an honest
> held-out number.
>
> **The M track is not claimed in this PR.**  Tremor has a multivariate path (MMPAD-M plus a
> per-channel point score, gated on the strongest channel) and it looks strong on a subset, but
> the only M evidence I have is a 75-of-180-file, 1.1%-of-compute cost-capped subset that is
> biased in Tremor's favour: the cap drops all 23 GHL, 23 of 28 SVDB, 20 of 25 Exathlon, 18 of 20
> SMD and 7 of 11 MITDB — exactly the families Tremor loses on — and the M hyper-parameters were
> chosen on 15 Tuning files.  The M path is present in the code for you to run if you wish; I am
> not asking for an M row.
>
> **Files.**  `TSB_AD/models/tremor/` (the package), `run_Tremor` in `model_wrapper.py`, the
> `Tremor` entries in `HP_list.py`, `benchmark_exp/Run_Tremor.py`, and
> `benchmark_exp/leaderboard_results/Uni_Tremor.csv`.  Repository, tests and worklog:
> https://github.com/KenWuqianghao/tremor.  Apache-2.0, matching TSB-AD.

## What the PR must not say

* No M number in the title, the abstract or a leaderboard row.  Offer the M path as
  present-but-unclaimed and let the maintainers decide whether to run it.
* No claim of a leaderboard position.  The maintainers re-run submissions themselves; the U
  number is my own full-list run, not a verified row.

## Why M is left out

The full M Eval is 1.3e14 MMPAD proxy units — 200-700 core-hours with the author's CPU code.  A
4-core machine ran 1.1% of it in 4 hours.  An M submission waits for either a full 180-file M run
on a bigger machine or a cheaper MMPAD-M anchor that makes one affordable (`EXPERIMENTS.md`,
"What is still open").
