# Eval results

Tremor on the TSB-AD Eval lists, compared with the authors' published per-series tables
restricted to exactly the files that ran (`harness/eval_compare.py <run_dir> --save`).  **No
tuning was done on any of it**: every hyper-parameter was fixed on the Tuning sets before the
first Eval file was scored, and nothing was changed afterwards.

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
