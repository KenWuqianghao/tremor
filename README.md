# Tremor — a CPU-only chooser for TSB-AD

**Tremor** is an anomaly detector for the [TSB-AD](https://github.com/TheDatumOrg/TSB-AD)
benchmark.  It is not a new model: it is a **per-series, label-free chooser** over three cheap
score components that already exist, plus the rule that decides which of them to believe on each
series.  Everything it does runs on a CPU in numpy/scipy/scikit-learn; there is no training, no
pretraining, no GPU and no dependence on a dataset's name.

The components:

| | univariate path (D = 1) | multivariate path (D > 1) |
|---|---|---|
| **anchor** | **MMPAD** (`n_neighbor=5`) — the benchmark's strongest classical method, a k-NN matrix-profile discord detector | **MMPAD-M** (`n_dim=0.7`, `n_neighbor=15`) |
| **residual** | **Sub-PCA** (`periodicity=1`, all components) — PCA reconstruction error over sliding windows of the ACF period | — (the M-track PCA fusion costs 2.6x runtime for +0.002 and is off) |
| **point** | **point** (`tremor/point.py`) — robust z of the first differences, `\|dx - median(dx)\| / (1.4826·MAD)`, centred max-filter over the ACF period.  O(n), milliseconds | **point-M** (`tremor/point_m.py`) — that score on every channel, mean of the three largest per-channel z per timestamp |

The chooser reads only the three score arrays: their excess kurtosis, the z-score of their
maximum, the overlap of their top-1% positions, and how many separate runs each spends above a
z threshold.  **No labels, no dataset names, no per-dataset special-casing.**

The full experiment history, including every rejected alternative: **[EXPERIMENTS.md](EXPERIMENTS.md)**.

---

## Results

### Context: the published TSB-AD leaderboard (Eval VUS-PR)

Quoted from the TSB-AD leaderboard / `benchmark_exp/leaderboard_results/` at upstream commit
`6beac72` (2026-09-07), the commit this work reproduces against.  **These are the authors' own
full-Eval numbers on the complete 350 U / 180 M series.  Tremor is deliberately not in this
table — my numbers are the two tables below, on the file sets stated there.**

| # | TSB-AD-U (350 series) | VUS-PR | | TSB-AD-M (180 series) | VUS-PR |
|---|---|---|---|---|---|
| 1 | Time-RCD + MAFT (fine-tuned) | 0.5856 | | AxonAD | 0.4954 |
| 2 | TSPulse (fine-tuned) | 0.5516 | | StreamVAE | 0.4353 |
| 3 | Time-RCD | 0.5224 | | xLSTMAD | 0.3923 |
| 4 | CHARM | 0.5011 | | CHARM | 0.3914 |
| 5 | TSPulse (zero-shot) | 0.4801 | | TSPulse (fine-tuned) | 0.3866 |
| 6 | StreamVAE | 0.4508 | | TSPulse (zero-shot) | 0.3610 |
| 7 | **MMPAD** (Tremor's anchor) | **0.4399** | | **MMPAD** (Tremor's anchor) | **0.3539** |
| 8 | AxonAD | 0.4342 | | CNN | 0.3130 |
| 9 | **Sub-PCA** (Tremor's residual) | **0.4234** | | OmniAnomaly | 0.3122 |
| 10 | KShapeAD | 0.4008 | | PCA | 0.3096 |

Rows 1-5 on U are pretrained or fine-tuned foundation models.  **StreamVAE (0.4508 U) and AxonAD
(0.4954 M) are the best non-pretrained entries** — the class Tremor competes in: a CPU-only
method with no pretraining.  MMPAD, Sub-PCA, KShapeAD, CNN, OmniAnomaly and PCA are the classical
tier.

### Tremor, Tuning sets (where every decision was made)

| track | files | MMPAD | Sub-PCA / point | **Tremor** | per-file oracle |
|---|---|---|---|---|---|
| U | 47 of 48 Tuning series (cost cap 6e10; 174_MITDB excluded) | 0.4240 | 0.3320 / 0.4463 | **0.6713** | 0.6890 (3 components) |
| M | 15 of 20 Tuning series (cost cap 1e11 + priority queue) | 0.4368 | point-M 0.4245 | **0.6373** | 0.6388 (2 components) |

Runtime is **1.00-1.02x MMPAD** on both tracks: the extra components are milliseconds and the
chooser is an argmax over four statistics.

### Tremor, Eval sets — **read the coverage column**

| track | files run | share of the Eval list (files / MMPAD proxy cost) | **Tremor** | published MMPAD, same files | published 2nd ref, same files | published MMPAD, full list |
|---|---|---|---|---|---|---|
| **U** | **350 / 350 — the complete list** | **100% / 100%** | **0.6085** | 0.4399 (**+0.1686**) | Sub-PCA 0.4234 (+0.1851) | 0.4399 |
| M | **75 / 180** | 41.7% / **1.1%** | **0.4632** | 0.3276 (**+0.1357**) | PCA-M 0.3180 † | 0.3539 |

† The M track has no Sub-PCA row (Sub-PCA is univariate).  The authors' second M reference is
PCA-M, whose **published table I found not reproducible** with HEAD code — treat that cell as
indicative only.

Per-file on the full U list: **137 files higher than published MMPAD, 38 lower, 175 equal**
(differences larger than 1e-6, `Uni_Tremor.csv` vs `Uni_MMPAD.csv` in the TSB-AD pull request);
0 failures; 24.7 core-hours of detector time.  On the M subset: 45 / 14 / 16.

The U row is a **full-list** number on the authors' own 350-series Eval set, scored with the
benchmark's own `get_metrics` and compared against the authors' own published per-series values on
the same files.  It is above every published entry in the leaderboard table above, including the
fine-tuned foundation models.  **The M row is not**: see the next section.

<details>
<summary>U Eval per dataset, all 350 files (Tremor vs published MMPAD vs published Sub-PCA)</summary>

| dataset | n | Tremor | MMPAD | Sub-PCA | vs MMPAD |
|---|---|---|---|---|---|
| SMD | 33 | 0.721 | 0.170 | 0.449 | **+0.551** |
| NEK | 8 | 0.887 | 0.349 | 0.905 | +0.538 |
| OPPORTUNITY | 27 | 0.814 | 0.353 | 0.914 | +0.461 |
| Daphnet | 1 | 0.422 | 0.036 | 0.422 | +0.386 |
| WSD | 20 | 0.453 | 0.119 | 0.094 | +0.334 |
| MSL | 7 | 0.564 | 0.313 | 0.507 | +0.251 |
| IOPS | 15 | 0.283 | 0.063 | 0.227 | +0.220 |
| Exathlon | 30 | 0.853 | 0.643 | 0.927 | +0.209 |
| SMAP | 17 | 0.788 | 0.596 | 0.518 | +0.192 |
| YAHOO | 30 | 0.709 | 0.618 | 0.137 | +0.091 |
| Stock | 8 | 0.658 | 0.586 | 0.840 | +0.072 |
| NAB | 23 | 0.433 | 0.390 | 0.436 | +0.043 |
| TAO | 2 | 0.930 | 0.929 | 0.930 | +0.002 |
| MITDB | 7 | 0.632 | 0.632 | 0.363 | 0.000 |
| SED / MGAB / LTDB / Power | 2 / 8 / 8 / 1 | 0.714 / 0.308 / 0.630 / 0.185 | identical | 0.031 / 0.005 / 0.556 / 0.076 | 0.000 |
| SWaT | 1 | 0.070 | 0.070 | 0.393 | -0.000 |
| UCR | 70 | 0.463 | 0.473 | 0.124 | -0.010 |
| TODS | 13 | 0.720 | 0.733 | 0.540 | -0.013 |
| CATSv2 | 1 | 0.265 | 0.291 | 0.265 | -0.027 |
| SVDB | 18 | 0.526 | 0.581 | 0.522 | **-0.056** |

Worst files: 006_NAB 0.17 vs 0.87, 385/463_UCR 0.25 vs 0.92 (the same series twice), 780_YAHOO
0.43 vs 1.00, 856_OPPORTUNITY 0.08 vs 0.64.  Best: 657_YAHOO 1.00 vs 0.004, 537_SMAP 1.00 vs
0.02, 143_MSL 1.00 vs 0.05, 213_SMD 0.97 vs 0.005, 844_OPPORTUNITY 0.99 vs 0.05.

</details>

The M per-dataset table and the subset bias analysis are in [docs/eval-results.md](docs/eval-results.md).

---

## What this does **not** establish

The U number is a full-list number and carries no coverage caveat.  **The M number does:  Tremor
has not been run on the full TSB-AD-M Eval list, and the M number above is biased in Tremor's
favour.**  Stated precisely:

* The subset rule is label-free — a cap on the MMPAD proxy cost, a function of series length and
  dimensionality only, the same rule that defines the Tuning sets.  It is **not** independent of
  difficulty, and it excludes the most expensive files by construction.
* **M: 105 of 180 files are missing, and only 1.1% of the track's compute was actually run.**
  The kept 75 are dominated by the cheap low-dimension sensor datasets where Tremor's point-M
  override wins big (SMAP 25 files, MSL 14, TAO 11 = 67% of the subset vs 48% of the Eval list),
  while the cap removes **all 23 GHL, 23 of 28 SVDB, 20 of 25 Exathlon, 18 of 20 SMD and 7 of 11
  MITDB** — the high-dimension and long-ECG families.  Exathlon (-0.217) and OPPORTUNITY (-0.328)
  are already Tremor's two losing datasets *inside* the subset, and 20 more Exathlon and 5 more
  OPPORTUNITY files sit outside it.  MMPAD-M's own published mean is 0.3276 on the kept files vs
  0.3727 on the excluded ones.  **0.4632 must be read as an optimistic estimate.**  The
  conservative full-list-equivalent — published MMPAD-M substituted on the 105 missing files,
  i.e. assuming Tremor merely ties there — is **0.4104**, and the truth is very likely below that
  because Tremor loses on exactly the excluded families.  **It does not clear AxonAD (0.4954) on
  any honest reading.**
* The M track's second published reference, PCA-M, was found **not reproducible** with HEAD code
  during the reproduction step (0.654 vs a published 0.440 on the same files); treat that column
  as stale.
* **U has no coverage caveat left.**  All 350 files ran (24.7 core-hours, 0 failures).  The
  earlier 339-file cost-capped number was 0.6142; completing the 11 most expensive files (7 MITDB,
  2 UCR, CATSv2, SWaT — 3.1% of the files but **76.3% of the track's compute**) moved it to
  0.6085, exactly the value the subset bias analysis had predicted.  On those 11 Tremor scores
  0.4328 vs MMPAD 0.4352: **all seven MITDB files are identical to four decimals** (on long ECG
  the point component fires hundreds of times and the spike gate correctly holds it out, so the
  chooser keeps MMPAD), 331_UCR +0.0003, 525_UCR identical, 550_SWaT -0.0001, 286_CATSv2 -0.0266.
* **A leaderboard row requires the maintainers' own full run.**  Nothing here is a submitted or
  verified number.  See [docs/SUBMISSION.md](docs/SUBMISSION.md).
* The Tuning means come from 47 and **15** files.  The M rule in particular was decided on a
  two-target set (see the `cthr_m` caveat below).

Reproduction anchor, so the comparisons above are trustworthy: my MMPAD-U reproduction scored
**0.4749 vs the authors' published 0.4752** on the same 148 files (147/148 within 0.01).  All
Tremor scores come from `harness/common.evaluate`, which is the benchmark's own
`TSB_AD.evaluation.metrics.get_metrics` with `find_length_rank(data[:,0], rank=1)` — **VUS-PR is
never reimplemented here.**

---

## Design

### 1. The chooser (univariate)

Components are indexed `0 = MMPAD (anchor)`, `1 = Sub-PCA`, `2 = point`.  Each score is
rank-normalised to [0, 1]; the output is the winner's ranks, not a blend (blending was tried and
lost — see EXPERIMENTS.md, experiments 1, 2 and 4).

```
conf_i   = max(excess kurtosis of score i, 0)          # label-free peakedness
zmax_i   = (max(score i) - mean) / std                 # does the peak stand out?

if   max(conf_0, conf_1) <  tau            -> FLAT FALLBACK: argmax_i zmax_i  over {0, 1, 2}
else                                          chooser:      argmax_i (conf_i + prior_i)
                                                            over {0, 1}, and i != 0 may win
                                                            only if zmax_i >= zfloor
     then, if the winner is 0 or 1, the point component REPLACES it iff all three gates pass.
```

**The three override gates** (all read off the score arrays):

| gate | condition | what it means |
|---|---|---|
| `pz` | `zmax_2 >= pzmin` | the spike detector found something at all |
| `agree` | at most `athr` of the point score's top-`kfrac·n` positions lie in the winner's top-`kfrac·n` | the two detectors **disagree on where** — where they agree, the context-aware winner is kept |
| `spikes` | the point score has at most `cthr` separate runs above `sthr` | a few strong, *isolated* events, not a detector firing everywhere |

### 2. The chooser (multivariate)

The same machinery over `0 = MMPAD-M`, `1 = point-M`, with point-M as the flat-fallback member
(there is no Sub-PCA on M, so nothing contests the kurtosis).  The override gates are evaluated
**not** on the channel-aggregated point-M score — whose z scale is compressed by the aggregation,
so the U thresholds fire wrongly there — but on component `2`, a **gate-only series that can
never be chosen**: the point score of the single channel with the largest robust z-max
(`point_m.best_channel`).  In words: *one sensor with a few clear, isolated spikes that the
channel-pooling discord detector diluted.*

### 3. Every threshold, with its measured plateau

The acceptance rule for a threshold: the Tuning mean must be flat across a range of values that
spans several files' worth of variation — a constant that sits on a one-cell peak is a fitted
constant, not a rule.  Plateaus below are **exact**, computed from the cached component scores
(every chooser variant outputs one component's ranks, so the whole grid can be screened without
re-running a detector).

| parameter | value | what it gates | measured plateau (U, 47 files) | measured plateau (M, 15 files) |
|---|---|---|---|---|
| `prior` (anchor) | 1.0 | additive kurtosis prior for MMPAD | ties go to the anchor by construction | same |
| `zfloor` | 3.0 | Sub-PCA may override MMPAD only above this z-max | **(2.1, 3.49]** identical (no overriding file has z-max in that gap) | n/a |
| `tau` | 0.5 | below this kurtosis, both scores count as flat | **(0.29, 0.69]** identical (0.71 -> 0.6387) | **(0.2, 0.64]** identical |
| `zprior` | 0.0 | optional anchor bonus in the flat fallback | **[0, 1]** identical | **[0, 1]** (126_TAO is a z tie) |
| `pzmin` | 7.0 | point / gate-channel z-max floor for the override | **[5.8, 8.1]** identical; >= 0.6629 across [4.8, 10.5] | **(6.19, 10.58]** identical |
| `kfrac` | 0.01 | top-k fraction for the agreement test | **[0.005, 0.02]** identical | (inactive) |
| `athr` | 0.5 | maximum top-k overlap with the winner | **[0.4, 0.81]** identical | **[0, 1]** identical — inactive on M, every agreement is <= 0.10 |
| `sthr` | 10.0 | z level defining a "run" | **[10, 20]** 0.6713-0.6734 | **[5, 20]** identical |
| `cthr` (U) | 5 | maximum number of runs above `sthr` | **[5, 54]** 0.6713-0.6734 (>= 55 admits 864_OPPORTUNITY) | — |
| `cthr_m` (M) | 10 | same, on the gate channel | — | **[6, 153]** identical (154 admits 082_LTDB) |
| `point_window` | `'period'` | max-filter width for the point score | the benchmark's own `find_length_rank`, not a tuned number (window 1 -> 0.6013, half-period -> 0.6382) | same |
| `point_m_agg` | `'top3z'` | per-timestamp channel aggregation | — | best of three, alone and inside the chooser, on every subset tried |

**The one honest caveat on a threshold:** `cthr_m = 10` differs from the univariate `cthr = 5`
because both M target files have exactly **6** runs above z 10, so the U value never fires.  10
sits inside *both* the U plateau [5, 54] and the M plateau [6, 153], but the low edge of the M
plateau **is** the two target files — a one-sided plateau on a two-target set.  Recorded at the
time it was taken, in experiment 8 of EXPERIMENTS.md.

### 4. Where the remaining headroom is

On U the chooser is **0.0177 from its own three-component oracle** on the Tuning files, of which
300_TODS (0.0096) and 217_LTDB (0.0052) are cases where no label-free signal distinguishes right
from wrong.  On M it is **0.0015 from the two-component oracle**.  Further gains need better
*components* or more files, not a better rule.

---

## Install and use

```bash
pip install -e ".[components]"        # numpy, scipy + TSB-AD, scikit-learn, statsmodels, pandas
```

The distribution name is **`tremor-tsbad`** (the bare name `tremor` is taken on PyPI by an
unrelated placeholder project); the import name is `tremor`.

```bash
# score one CSV in the benchmark's layout (channels..., Label) and print VUS-PR
tremor-score data/TSB-AD-U/001_NAB_id_1_Facility_tr_1007_1st_2014.csv

# write the per-timestamp score array instead
tremor-score <file.csv> --scores out.npy --json
```

```python
from tremor import Tremor, run_Tremor_Unsupervised

scores = run_Tremor_Unsupervised(data)          # data: (n, D) float, no labels
clf = Tremor(); clf.fit(data); clf.info_        # which component won, and why
```

`Tremor` follows TSB-AD's model interface: `fit(X)` sets `decision_scores_`, one score per
timestamp.  `benchmark_exp/Run_Tremor.py` is the adapter in the layout the benchmark expects, and
carries the same hyper-parameters (a test asserts they cannot drift apart).

**Packaging note:** TSB-AD's `TSB_AD/models/MMPAD.py` does `import torch` at module scope even
though the CPU path never executes torch code.  This repository ships a numpy stub at
`harness/shims/torch` for that; if you install TSB-AD standalone, either install torch or put an
equivalent stub on the path.

---

## Reproduce

Everything below reads only the Tuning lists and cached artefacts; **no Eval label is ever read
while tuning.**

```bash
# 1. the tests: replay every decision and both Tuning means from cached component scores
python -m unittest discover -s tests -v              # 22 tests, ~3 s, TSB-AD not required
#   The component scores of the 47 U / 15 M Tuning files ship in tests/fixtures/ (12 MB,
#   lzma-compressed float32), so the suite runs on a clean clone.

# 2. the components on the U Tuning set (the benchmark's own scoring, ~30 min on 4 cores)
python harness/run.py --track U --split tuning --method MMPAD   --max-cost 6e10 --workers 4
python harness/run.py --track U --split tuning --method Sub_PCA --max-cost 6e10 --workers 4
python harness/run.py --track U --split tuning --method point --workers 4

# 3. the chooser on those cached component scores -> U Tuning 0.6713 on 47 files
python harness/fuse_eval.py --track U --split tuning \
    --components U_tuning_MMPAD,U_tuning_Sub_PCA,U_tuning_point --tag _default
#    a threshold sweep is the same call with --hp '{"pzmin": 6}' etc.; no detector is re-run

# 4. the M track -> M Tuning 0.6373 on 15 files
python harness/run.py --track M --split tuning --method MMPAD --max-cost 1e11 --workers 4
python harness/run.py --track M --split tuning --method point_m --workers 4
python harness/run.py --track M --split tuning --method point_m_gate --workers 4
python harness/fuse_eval.py --track M --split tuning \
    --components M_tuning_MMPAD,M_tuning_point_m,M_tuning_point_m_gate --tag _default

# 5. end-to-end Tremor on an Eval list (one process per file, the default hyper-parameters)
python harness/run.py --track U --split eval --method Tremor --workers 4
python harness/eval_compare.py runs/U_eval_Tremor --save

# 6. report any run directory against a published reference
python harness/report.py runs/<dir> --ref leaderboard:Uni_MMPAD
```

`harness/file_stats.py` writes `runs/file_stats.csv` (per-file length, dimensionality and MMPAD
proxy cost), which `--max-cost` and `eval_compare.py` read.  Data goes in `data/TSB-AD-U/` and
`data/TSB-AD-M/` (download links in `docs/benchmark-notes.md`); the upstream clone goes in
`upstream/`.  Both are gitignored.

---

## Repository map

| path | what |
|---|---|
| `tremor/` | the package: `fusion.py` (chooser + gates), `point.py`, `point_m.py`, `detector.py`, `cli.py` |
| `benchmark_exp/Run_Tremor.py` | the TSB-AD submission adapter, in the layout `benchmark_exp/README.md` asks for |
| `tests/` | 22 unittests, replayed entirely from the cached component scores in `tests/fixtures/` |
| `harness/` | the runner (the benchmark's own scoring), chooser screening on cached scores, reporting, Eval comparison |
| `EXPERIMENTS.md` | the worklog: every experiment, kept or dropped, with the plateau evidence and every rejection |
| `docs/benchmark-notes.md` | the benchmark's submission steps, model interface and VUS-PR code, quoted verbatim |
| `docs/methods.md` | what MMPAD, Sub-PCA, KShapeAD and MatrixProfile actually compute |
| `docs/tuning-profile.md` | the reference methods on the Tuning sets, and the reproduction against the published tables |
| `docs/eval-results.md` | the Eval runs in full: per-dataset tables for both tracks and the subset bias analysis |
| `docs/SUBMISSION.md` | the text and steps for the TSB-AD leaderboard PR (U track only) |

License: Apache-2.0, matching TSB-AD.  Per-dataset licences apply to the data.
