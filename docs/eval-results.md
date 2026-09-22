# Eval results

Tremor on the TSB-AD Eval lists, compared with the authors' published per-series tables
restricted to exactly the files that ran (`harness/eval_compare.py <run_dir> --save`).  **No
tuning was done on any of it**: every hyper-parameter was fixed on the Tuning sets before the
first Eval file was scored, and nothing was changed afterwards.

## The full U Eval list (350/350), no cost cap

Launched 2026-09-13T02:34 UTC (4 workers on 4 cores, resuming the cost-capped run below with the
cap removed); finished 2026-09-13T08:11 UTC, **wall 5 h 37 min**, 0 failures.  It ran the 11
files the earlier cap had excluded — 7 MITDB, 2 UCR, 286_CATSv2, 550_SWaT — which carry only
3.1% of the file count but **76.3% of the track's MMPAD proxy cost** (18.9 of the 24.7 core-hours
the whole track took).  The **U track is complete: 350/350 files, 100% of the Eval list and 100%
of its proxy cost.**

| track | subset rule | files | share of Eval list | share of its MMPAD proxy cost | **Tremor** | MMPAD same files | 2nd ref same files | MMPAD published full list |
|---|---|---|---|---|---|---|---|---|
| U | **none (full list)** | **350 / 350** | **100%** | **100%** | **0.6085** | 0.4399 (**+0.1686**) | Sub-PCA 0.4234 (+0.1851) | 0.4399 |
| U (cost-capped, superseded) | `--max-cost 6e10` | 339 / 350 | 96.9% | 23.7% | 0.6142 | 0.4400 | Sub-PCA 0.4277 | 0.4399 |
| M (cost-capped, still the only M number) | `--max-cost 1e11` | **75 / 180** | 41.7% | **1.1%** | 0.4632 | 0.3276 | PCA-M 0.3180 | 0.3539 |

Per-file on the full U list: **150 up / 45 down / 155 identical** vs published MMPAD.

### The cost-capped subset was nearly unbiased — now measured, not argued

The bias analysis below predicted a **full-list-equivalent of 0.6085** by substituting published
MMPAD on the 11 missing files (i.e. assuming Tremor merely ties there).  The measured full-list
value is **0.6085**.  On those 11 files Tremor scores **0.4328 vs MMPAD 0.4352** — a tie to
0.0024:

| file | n | Tremor | MMPAD | Sub-PCA | vs MMPAD | detector time |
|---|---|---|---|---|---|---|
| 170/171/172/173/175/176/177_MITDB | 500k-650k | 0.7238 / 0.7060 / 0.7738 / 0.3450 / 0.7442 / 0.3335 / 0.7947 | identical to 4 dp | 0.02-0.86 | **0.0000 each** | 1.2-2.1 h each |
| 331_UCR | 900k | 0.0020 | 0.0016 | 0.0021 | +0.0003 | 3.8 h |
| 525_UCR | 300k | 0.0030 | 0.0030 | 0.0067 | 0.0000 | 0.4 h |
| 550_SWaT | 420k | 0.0698 | 0.0699 | 0.3929 | -0.0001 | 0.8 h |
| 286_CATSv2 | 300k | 0.2646 | 0.2912 | 0.2647 | **-0.0266** | 0.4 h |

On all seven MITDB files the chooser keeps MMPAD (the point component fires hundreds of times on
an ECG and the spike gate holds it out — exactly the 217_LTDB behaviour seen on the Tuning set),
so the long-ECG risk flagged in the bias analysis did not materialise: it costs nothing rather
than gaining anything.  The only real loss among the 11 is 286_CATSv2 (-0.027, one file = 0.00008
of the mean).

### U per dataset, full 350 files (Tremor vs published MMPAD vs published Sub-PCA)

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
| **MITDB** | **7** | **0.632** | **0.632** | 0.363 | **0.000** |
| SED / MGAB / LTDB / Power | 2/8/8/1 | 0.714/0.308/0.630/0.185 | identical | 0.031/0.005/0.556/0.076 | 0.000 |
| SWaT | 1 | 0.070 | 0.070 | 0.393 | -0.000 |
| UCR | 70 | 0.463 | 0.473 | 0.124 | -0.010 |
| TODS | 13 | 0.720 | 0.733 | 0.540 | -0.013 |
| CATSv2 | 1 | 0.265 | 0.291 | 0.265 | -0.027 |
| SVDB | 18 | 0.526 | 0.581 | 0.522 | **-0.056** |

Worst files vs MMPAD: 006_NAB 0.17 vs 0.87, 385/463_UCR 0.25 vs 0.92 (the same series twice),
780_YAHOO 0.43 vs 1.00, 856_OPPORTUNITY 0.08 vs 0.64.  Best: 657_YAHOO 1.00 vs 0.004, 537_SMAP
1.00 vs 0.02, 143_MSL 1.00 vs 0.05, 213_SMD 0.97 vs 0.005, 844_OPPORTUNITY 0.99 vs 0.05.

### What this changes, and what it does not

* **U is no longer a subset claim.**  0.6085 is Tremor on the authors' own 350-series Eval list,
  scored with the benchmark's own `get_metrics`, next to the authors' own published per-series
  MMPAD and Sub-PCA numbers on the same files.  It is above every published entry on that
  leaderboard including the fine-tuned foundation models (Time-RCD+MAFT 0.5856) and far above the
  non-pretrained target StreamVAE 0.4508.  **It is still not a leaderboard row**: the maintainers
  re-run submissions themselves (`docs/SUBMISSION.md`).
* **M is unchanged and still a biased 41.7% / 1.1%-of-cost subset.**  Nothing in this pass touched
  the M track.  The honest M reading remains 0.4632 optimistic / 0.4104 conservative, below
  AxonAD 0.4954.  A cheaper MMPAD-M is still the coverage blocker.
* **The too-good-to-be-true check**, re-applied: the +0.169 U margin is not a single-step gain but
  the sum of 7 Tuning-gated changes (each re-read for label use when it was made); the Eval mean
  0.6085 sits below the Tuning mean 0.6713 on a disjoint 350-file set (no overfitting signal); the
  detector code is byte-identical to the tree the Tuning numbers were produced with (`tests/`
  replays every decision and both Tuning means from cached scores); and the reference values come
  from the authors' per-series tables via the loader the MMPAD reproduction validated.

## Cost-capped subsets, both tracks — NOT full-Eval numbers

Launched 2026-09-12T20:54 UTC (U and M concurrently, 2 workers each on 4 cores), both finished
2026-09-13T00:51 UTC: **wall 3 h 57 min for the pair** (U 213.4 min, M 237.2 min), 0 failures,
803 core-min of detector time.  The cost model over-estimated U by ~4x (the proxy cost is
quadratic in n, but Sub-PCA/point and the scoring dominate on the many small files), so the whole
capped U subset fit inside the 6 h budget instead of the predicted 12 h.

**Nothing below was used to change any code, hyper-parameter or decision.**

| track | subset rule | files | share of Eval list | share of its MMPAD proxy cost | **Tremor** | MMPAD same files | 2nd ref same files | MMPAD published full list |
|---|---|---|---|---|---|---|---|---|
| U | `--max-cost 6e10` | **339 / 350** | 96.9% | 23.7% | **0.6142** | 0.4400 (**+0.1742**) | Sub-PCA 0.4277 (+0.1865) | 0.4399 |
| M | `--max-cost 1e11` | **75 / 180** | 41.7% | **1.1%** | **0.4632** | 0.3276 (**+0.1357**) | PCA-M 0.3180 (+0.1452) | 0.3539 |

Per-file: U 201 up / 47 down / 91 identical vs MMPAD; M 45 up / 14 down / 16 identical.  The M
track has no Sub-PCA row in the authors' tables (Sub-PCA is univariate); the second reference is
PCA-M, which I found **not reproducible** with HEAD code — treat the published PCA-M column as
stale and the +0.1452 as indicative only.

### U-Eval-339 per dataset (Tremor vs published MMPAD vs published Sub-PCA, same files)

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
| LTDB / SED / MGAB / Power | 8/2/8/1 | 0.630/0.714/0.308/0.185 | identical | 0.556/0.031/0.005/0.076 | 0.000 |
| UCR | 68 | 0.477 | 0.487 | 0.127 | -0.010 |
| TODS | 13 | 0.720 | 0.733 | 0.540 | -0.013 |
| SVDB | 18 | 0.526 | 0.581 | 0.522 | **-0.056** |

### M-Eval-75 per dataset (Tremor vs published MMPAD-M vs published PCA-M, same files)

| dataset | n (kept / in Eval list) | Tremor | MMPAD-M | PCA-M | vs MMPAD-M |
|---|---|---|---|---|---|
| SMD | 2 / 20 | 0.458 | 0.096 | 0.284 | **+0.362** |
| MSL | 14 / 27 | 0.397 | 0.103 | 0.149 | +0.295 |
| SMAP | 25 / 47 | 0.352 | 0.070 | 0.093 | +0.282 |
| TAO | 11 / 13 | 0.784 | 0.772 | 1.000 | +0.012 |
| SVDB | 5 / 28 | 0.738 | 0.738 | 0.049 | 0.000 |
| LTDB | 4 / 4 | 0.600 | 0.600 | 0.244 | 0.000 |
| Daphnet / Genesis | 1 / 1 each | 0.038 / 0.006 | identical | 0.130 / 0.019 | 0.000 |
| SWaT | 1 / 2 | 0.230 | 0.251 | 0.241 | -0.021 |
| MITDB | 4 / 11 | 0.308 | 0.329 | 0.085 | -0.021 |
| Exathlon | 5 / 25 | 0.583 | 0.800 | 0.960 | **-0.217** |
| OPPORTUNITY | 2 / 7 | 0.169 | 0.497 | 0.565 | **-0.328** |

Not represented at all (dropped by the cap): all 23 GHL, all 5 CATSv2, PSM, GECCO, CreditCard.

### Is the subset biased?  Yes on M, essentially no on U

The cap is label-free (a function of n and D only), but it is **not** independent of difficulty,
and it excludes the most expensive files **by construction**.

* **U (11 files dropped: 7 MITDB, 2 UCR, CATSv2, SWaT).**  MMPAD's own published mean is 0.4352
  on the excluded 11 vs 0.4400 on the kept 339 — the cap is nearly neutral, and the kept-file
  MMPAD mean (0.4400) reproduces the published full-list mean (0.4399) to 4 decimals.  The 339
  files carry 96.9% of the list and 23.7% of its cost.  Substituting published MMPAD on the 11
  missing files (i.e. assuming Tremor only ties there) gives a **full-list-equivalent 0.6085**.
  The residual risk is that 7 of the 11 are MITDB, and SVDB (-0.056) is already Tremor's worst
  dataset in the subset, so long ECG is where the true full-Eval number would fall furthest — but
  11 files can move the mean by at most 0.4399 x 11/350 = 0.014 in the worst case.
* **M (105 files dropped).**  Biased, and in the direction that flatters Tremor.  The kept 75 are
  dominated by the cheap low-n sensor datasets where Tremor's point-M override wins big (SMAP 25
  files, MSL 14, TAO 11 = 67% of the subset vs 48% of the Eval list), while the cap removes all
  23 GHL, 23 of 28 SVDB, 20 of 25 Exathlon, 18 of 20 SMD and 7 of 11 MITDB — the high-D and
  long-ECG files.  Exathlon (-0.217) and OPPORTUNITY (-0.328) are already Tremor's two losing
  datasets *inside* the subset, and 20 more Exathlon and 5 more OPPORTUNITY files sit outside it.
  MMPAD-M's own published mean is 0.3276 on the kept files vs 0.3727 on the excluded ones, so the
  kept files are also the ones MMPAD-M itself scores lower on.  **0.4632 must be read as an
  optimistic estimate**; the conservative full-list-equivalent (published MMPAD-M on the 105
  missing, i.e. Tremor ties there) is **0.4104**, and the truth is very likely below that because
  Tremor loses on exactly the excluded families.  1.1% of the track's proxy cost was actually run.

### Where this leaves the targets

U: above every published entry including the fine-tuned foundation models (Time-RCD+MAFT 0.5856)
and far above the non-pretrained target StreamVAE 0.4508 — a leaderboard row still needs the
authors' own full run.  M: 0.4632 on a biased 41.7% subset is below AxonAD 0.4954 and above
MMPAD-M 0.3539; the honest full-Eval estimate (0.41 or lower) does not clear AxonAD.  **The gap
between "my subset number" and "a publishable row" on M is a compute problem, not a method
problem**: the full M Eval is 1.3e14 proxy units, 200-700 core-hours with the author's CPU code,
and this 4-core box ran 1.1% of it in 4 hours.

## Reproduction of the reference methods (before any of the above)

| track | method | files scored / listed | my VUS-PR | reference on same files | reference full list | max per-file abs diff | runtime (min) |
|---|---|---|---|---|---|---|---|
| U | MMPAD | 148 / 148 (subset=half) | 0.4749 | 0.4752 | 0.4399 | 0.0315 | 20.6 |
| U | Sub_PCA | 148 / 148 (subset=half) | 0.4592 | 0.4706 | 0.4234 | 0.3524 | 1.8 |
| M | MMPAD | 9 / 9 (subset=half) | 0.3521 | 0.3792 | 0.3539 | 0.2848 | 4.1 |
| M | PCA | 9 / 9 (subset=half) | 0.6544 | 0.4400 | 0.3096 | 0.7699 | 24.2 |

Notes on these rows are in `docs/tuning-profile.md`.
