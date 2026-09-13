# Tuning-set profile of the reference methods

Per-dataset VUS-PR and runtime of the reference methods on the TSB-AD Tuning lists (48 U / 20 M
series), from `runs/`, before any of Tremor's own components existed.  Mean over series in each
dataset; `n` = series count; runtimes are per-file sums in seconds (single core per file, 4 files
in parallel).  Files above the MMPAD cost cap were skipped (see the notes at the bottom).

## TSB-AD-U Tuning (38 series with at least one result)

| dataset | n | MMPAD | Sub_PCA | MatrixProfile | KShapeAD | MMPAD s | Sub_PCA s | MatrixProfile s | KShapeAD s |
|---|---|---|---|---|---|---|---|---|---|
| NEK | 1 | 0.086 | 0.949 | 0.062 | - | 0 | 0 | 0 | 0 |
| OPPORTUNITY | 2 | 0.324 | 0.971 | 0.156 | 0.289 | 8 | 1 | 1 | 45 |
| MSL | 2 | 0.026 | 0.572 | 0.031 | - | 1 | 0 | 0 | 0 |
| SMAP | 2 | 0.500 | 0.645 | 0.842 | 0.517 | 2 | 1 | 1 | 26 |
| Exathlon | 2 | 0.611 | 0.836 | 0.509 | 0.415 | 73 | 0 | 59 | 129 |
| TAO | 1 | 0.433 | 0.656 | 0.172 | 0.240 | 2 | 0 | 1 | 17 |
| Stock | 2 | 0.545 | 0.721 | 0.524 | 0.518 | 11 | 1 | 2 | 60 |
| WSD | 5 | 0.053 | 0.209 | 0.005 | 0.036 | 27 | 1 | 5 | 99 |
| TODS | 2 | 0.878 | 0.512 | 0.878 | 0.906 | 2 | 1 | 1 | 39 |
| SMD | 5 | 0.409 | 0.196 | 0.341 | 0.414 | 60 | 4 | 60 | 292 |
| SED | 1 | 0.936 | 0.028 | 0.747 | 0.934 | 2 | 1 | 1 | 34 |
| NAB | 5 | 0.363 | 0.215 | 0.299 | 0.077 | 7 | 2 | 2 | 16 |
| YAHOO | 5 | 0.489 | 0.076 | 0.333 | - | 1 | 0 | 1 | 0 |
| UCR | 3 | 0.907 | 0.055 | 0.577 | 0.456 | 6 | 4 | 2 | 29 |
| **mean (files scored)** | 38 | **0.435** (38) | **0.363** (38) | **0.355** (38) | **0.388** (25) | 201 | 17 | 137 | 786 |
| **mean on common files** | 25 | **0.448** | **0.411** | **0.377** | **0.388** |  |  |  |  |

Largest per-series MMPAD losses vs. the best other method:

| file | n | MMPAD | best other | loss |
|---|---|---|---|---|
| 146_MSL_id_7_Sensor_tr_554_1st_1172.csv | 2217 | 0.032 | 0.939 | 0.907 |
| 535_SMAP_id_5_Sensor_tr_1113_1st_1890.csv | 4453 | 0.006 | 0.882 | 0.876 |
| 280_NEK_id_4_WebService_tr_500_1st_231.csv | 1073 | 0.086 | 0.949 | 0.863 |
| 038_WSD_id_10_WebService_tr_4042_1st_4142.csv | 18084 | 0.004 | 0.799 | 0.795 |
| 864_OPPORTUNITY_id_23_HumanActivity_tr_895_1st_995.csv | 14751 | 0.158 | 0.947 | 0.789 |
| 186_SMD_id_9_Facility_tr_5925_1st_17580.csv | 23703 | 0.006 | 0.700 | 0.694 |
| 583_YAHOO_id_33_WebService_tr_500_1st_1616.csv | 1680 | 0.052 | 0.627 | 0.575 |
| 852_OPPORTUNITY_id_11_HumanActivity_tr_500_1st_566.csv | 15653 | 0.490 | 0.995 | 0.506 |
| 813_Exathlon_id_4_Facility_tr_10766_1st_12590.csv | 43066 | 0.339 | 0.691 | 0.352 |
| 161_Stock_id_13_Finance_tr_500_1st_3.csv | 10000 | 0.168 | 0.519 | 0.350 |

This table is where the whole project came from: the per-file oracle max(MMPAD, Sub-PCA) is
0.630 against MMPAD's 0.435, and the losses are concentrated on files where one detector is
confidently right and the other confidently wrong.

## TSB-AD-M Tuning (6 series with at least one result)

| dataset | n | MMPAD | PCA | MMPAD s | PCA s |
|---|---|---|---|---|---|
| TAO | 2 | 0.963 | 0.953 | 29 | 3 |
| MSL | 1 | 0.072 | 0.054 | 32 | 97 |
| SMAP | 2 | 0.073 | - | 57 | 0 |
| SVDB | 1 | 0.889 | - | 56 | 0 |
| **mean (files scored)** | 6 | **0.506** (6) | **0.653** (3) | 174 | 100 |
| **mean on common files** | 3 | **0.666** | **0.653** |  |  |

Largest per-series MMPAD losses vs. the best other method:

| file | n | MMPAD | best other | loss |
|---|---|---|---|---|
| 126_TAO_id_11_Environment_tr_500_1st_7.csv | 10000 | 0.963 | 0.953 | -0.009 |
| 120_TAO_id_5_Environment_tr_500_1st_3.csv | 10000 | 0.964 | 0.952 | -0.012 |
| 004_MSL_id_3_Sensor_tr_530_1st_630.csv | 2430 | 0.072 | 0.054 | -0.017 |
| 090_SVDB_id_7_Medical_tr_12157_1st_12257.csv | 50000 | 0.889 | - | - |
| 149_SMAP_id_6_Sensor_tr_2128_1st_5000.csv | 8512 | 0.137 | - | - |
| 164_SMAP_id_21_Sensor_tr_1976_1st_4200.csv | 7907 | 0.010 | - | - |

The M Tuning set was later widened to 14 and then 15 files (`EXPERIMENTS.md`, experiments 7
and 8); the widened MMPAD-M means are 0.4193 (14 files) and 0.4368 (15 files).

## Eval reproduction (the one Eval run made before any tuning)

| track | method | files scored / listed | my VUS-PR | reference on same files | reference full list | max per-file abs diff | runtime (min) |
|---|---|---|---|---|---|---|---|
| U | MMPAD | 148 / 148 (subset=half) | 0.4749 | 0.4752 | 0.4399 | 0.0315 | 20.6 |
| U | Sub_PCA | 148 / 148 (subset=half) | 0.4592 | 0.4706 | 0.4234 | 0.3524 | 1.8 |
| M | MMPAD | 9 / 9 (subset=half) | 0.3521 | 0.3792 | 0.3539 | 0.2848 | 4.1 |
| M | PCA | 9 / 9 (subset=half) | 0.6544 | 0.4400 | 0.3096 | 0.7699 | 24.2 |

## Notes

* **Subsets.** All runs use `--max-cost 3e9` (MMPAD proxy cost `n_eff^2 * D * log2(max(D,2))`,
  ~ n > 55k univariate) except M-tuning MMPAD (`1e10`); Eval runs additionally use the fixed
  random half (`harness/run.py --subset half`, seed 20260912).  U: 148/350 Eval, 38/48 Tuning.
  M: 9/180 Eval (the M track is ~600 core-hours with the author's CPU code), 6/20 Tuning for
  MMPAD and 3/20 for PCA.  The "reference full list" column is the published mean over the
  whole list; "reference on same files" is what my number must match.
* **MMPAD-U reproduces**: 0.4749 vs 0.4752 on the same 148 files (147/148 within 0.01, one
  MSL file 0.68 vs 0.71).  Runtime 20.6 core-min here vs 22.8 min reported by the authors for
  the same files on a 16-vCPU box.
* **Sub-PCA-U**: 133/148 files identical; 15 files differ (both directions, mean -0.011).
  All 15 have an ACF window of 4-5 points (`find_length_rank` returns 4-5), where Sub-PCA
  with all components is numerically fragile; the published `uni_mergedTable` predates the
  current `PCA.py`.  The harness is not at fault (MMPAD on the same files matches).
* **MMPAD-M**: 6/9 files identical (all TAO and SMAP files, two MSL); 3 MSL files (55
  channels, many flat) differ by up to 0.28 in both directions and no HP variant
  (n_dim 0.5/0.7/1, n_neighbor 10/15) reproduces them: the pre-sorted per-channel
  correlation with EPS-flattened channels is tie/precision sensitive (the authors' run may
  have used the GPU backend).  Mean on the 9 files 0.3521 vs 0.3792 — the 0.005 criterion is
  met on U but not on this tiny M subset.
* **PCA-M**: the published multivariate PCA numbers are not reproducible with HEAD code
  (8/9 files differ, mine 0.654 vs 0.440): `PCA.py` at HEAD z-scores multivariate windows
  per row and prunes zero columns, unlike whatever produced `multi_mergedTable`.  Treat the
  published PCA-M row (0.3096) as stale; my own PCA-M numbers are the baseline from here on.
* **KShapeAD** (tslearn k-Shape, numpy backend) is slow: 25/38 Tuning files in the 5-minute
  cap (13 core-min); a reference only, never inside the detector.
* Quick probe on cached Tuning scores (not a kept change): per-file oracle
  max(MMPAD, Sub-PCA) = 0.630 (vs MMPAD 0.435), but naive rank fusion does not capture it
  (mean of ranks 0.324, max of ranks 0.428).  The gap must be won by a label-free chooser or
  a gated fusion, not by averaging.
