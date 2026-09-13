# Experiments

The worklog behind Tremor: one block per experiment, in the order I ran them (2026-09-12 to
2026-09-13).  Every number is a **Tuning** mean VUS-PR produced by the benchmark's own
`TSB_AD.evaluation.metrics.get_metrics`, unless a line says Eval.

**Read the file sizes, not just the deltas.** The evaluation sets grew twice on each track, and
a mean is only comparable to another mean on the *same* file set:

| track | set | files | when | why it changed |
|---|---|---|---|---|
| U | cap 3e9 | 38 of 48 Tuning files | experiments 1-3 | initial cost cap (MMPAD proxy cost in `runs/file_stats.csv`) |
| U | cap 6e10 | **47 of 48** | experiment 4 onwards | widened for measurement validity; only 174_MITDB (4.2e11, ~55 min) stays out |
| M | cap 3e9 | 6 of 20 | experiments 1-6 | initial cap; MMPAD-M is 10-100x more expensive than MMPAD-U |
| M | cap 1e11 + priority queue | 14 of 20 | experiment 7 | widened for the first M hypothesis |
| M | + 107_SVDB | **15 of 20** | experiment 8 onwards | the five > 1e12 files (178_Exathlon, 131_OPPORTUNITY, 040/049_GHL, 140_CATSv2: 3-23 h each) remain out |

**Acceptance rule, applied at every step:** a change is kept only if the mean Tuning VUS-PR
improves on the target track, the other track does not drop by more than 0.01, and runtime does
not exceed 2x the previous best; then I re-ask whether the change uses information a deployed
detector would not have.  A single-step gain above 0.05 triggers a re-read of the diff as a
suspected label leak.  A threshold is accepted only if it sits on a measured plateau.

## Summary

| # | experiment | what changed | Tuning U | Tuning M | kept? | why |
|---|---|---|---|---|---|---|
| 1 | Reproduction | harness around the benchmark's own scoring; MMPAD and Sub-PCA reproduced | 0.4346 (MMPAD, 38 files) | 0.5057 (MMPAD-M, 6 files) | baseline | MMPAD-U 0.4749 vs published 0.4752 on 148 Eval files; oracle max(MMPAD, Sub-PCA) 0.6295 set the direction |
| 2 | Kurtosis chooser | argmax of (prior + excess kurtosis) over MMPAD and Sub-PCA | 0.4346 -> **0.5748** | 0.5057 (unchanged) | kept | +0.14; the hard chooser beat every soft weighting; M fusion rejected on runtime (2.56x for +0.002) |
| 3 | z-max floor | Sub-PCA may override MMPAD only if its z-max >= 3 | 0.5748 -> **0.5976** | unchanged | kept | one file (012_NAB 0.13 -> 1.00); floor mid-plateau (2.1, 3.49] |
| 4 | Widen U to 47 files; flat fallback | re-score everything; when both kurtoses < tau, take the higher z-max | 0.5725 -> **0.5843** (47 files) | unchanged | kept | +0.0118, 4 up / 3 down; tau plateau (0.29, 4.62); the chooser picked right on 9/9 unseen files |
| 5 | Point component | robust z of first differences, max-filtered over the ACF period, flat fallback only | 0.5843 -> **0.6421** | unchanged | kept | +0.0578, exactly 5 files change, all up; the component alone (0.4463) beats MMPAD |
| 6 | Override gates | point replaces a peaked winner iff z-max >= 7, top-1% disagreement <= 0.5, <= 5 runs above z 10 | 0.6421 -> **0.6713** | unchanged | kept | +0.0292, exactly 4 files change, all up; every threshold on a plateau |
| 7 | Widen M to 14 files; point-M | per-channel point score, mean of the top-3 channel z, flat fallback only | unchanged (verified on 47 files) | 0.4193 -> **0.5217** (14 files) | kept | +0.1024, changes exactly the 6 files where MMPAD-M is flat |
| 8 | Widen M to 15 files; strongest-channel gate | the U gates evaluated on the strongest channel's own point score | unchanged | 0.5324 -> **0.6373** (15 files) | kept | +0.1049, exactly 2 files change, both up; 0.0015 from the oracle |
| 9 | Eval, cost-capped subsets | no code change | Eval 0.6142 on 339/350 | Eval 0.4632 on 75/180 (biased) | — | held-out check; nothing changed on the basis of it |
| 10 | Eval, full U list | no code change; the 11 expensive files run | Eval **0.6085 on 350/350** | unchanged | — | matched the 0.6085 the bias analysis had predicted |

---

## 1. Reproduction (2026-09-12, morning)

**What:** clone TSB-AD (HEAD 6beac72, 2026-09-07), download both tracks, build `harness/`
around the benchmark's own scoring, reproduce MMPAD and Sub-PCA.

**Result (the one Eval run at this stage, fixed-seed cost-capped subsets):** MMPAD-U **0.4749
vs the authors' 0.4752** on the same 148 files (PASS, 147/148 within 0.01); Sub-PCA-U 0.4592 vs
0.4706 (133/148 identical, 15 window-4/5 files differ); MMPAD-M 0.3521 vs 0.3792 on 9 files
(6/9 identical, 3 MSL files precision-sensitive).  Tuning profile (U, 38 files): MMPAD 0.4346,
KShapeAD 0.388 (25 files), Sub-PCA 0.3631, MatrixProfile 0.3549; **per-file oracle max(MMPAD,
Sub-PCA) 0.6295** — the number that set the whole direction.

**Rejected here:** naive (unweighted) rank fusion of MMPAD and Sub-PCA, 0.324 / 0.428 vs MMPAD
0.4346 — averaging two detectors that disagree is worse than either.  *Reason: the oracle gap is
a **selection** problem, not a blending one.*

**Also found:** the leaderboard had moved (fine-tuned foundation models above MMPAD), so the
target became "best non-pretrained CPU method": StreamVAE 0.4508 on U, AxonAD 0.4954 on M.

---

## 2. Kurtosis chooser: weight each component by its own peakedness

**Hypothesis:** rank-normalise MMPAD and Sub-PCA and weight each by the clipped excess kurtosis
of its own score vector (a label-free confidence), `w_i = (prior_i + conf_i) ** power`, MMPAD
holding an additive prior of 1 so ties go to the anchor.

**Tuning U (38 files): 0.4346 -> 0.5748.  M: 0.5057 unchanged** (the M path stayed MMPAD-M alone).
Runtime 1.08x.

**KEPT** (`power='hard'`, the argmax of prior + kurtosis).  *Reason: +0.14 on the track, and the
hard chooser beat every soft power on the same files.*

**Rejected alternatives (all scored on the same 38 files):** soft weighting p1 0.5117, p2 0.5601,
p4 0.5663 (*below the hard chooser; blending still dilutes the right component*); `zmax` as the
confidence statistic p1 0.4364, p2 0.5363 (*z-max alone does not separate a peaked score from a
flat one*); `logkurt` p1 0.4408 (*the compression removes exactly the signal*); kurtosis with no
anchor prior 0.5291 (*ties then go to Sub-PCA, which is the weaker detector*).  **M-side fusion
of MMPAD-M with PCA-M: 0.5075 vs 0.5057 at 2.56x runtime — rejected on the runtime rule**
(`fuse_multivariate=False` ever since).

**Known losses it introduced:** 300_TODS 0.90 -> 0.45 and 012_NAB 1.00 -> 0.13, both synthetic
series where Sub-PCA's kurtosis is higher but MMPAD is right.  These set the next hypothesis.

---

## 3. z-max floor: a second, independent gate on the override

**Hypothesis:** Sub-PCA may override MMPAD only if its kurtosis wins **and** the z-score of its
maximum, `(max - mean) / std`, is high — a peaked score whose peak does not stand out (012_NAB:
Sub-PCA kurtosis 9.4 > 7.8 but z-max 0.5) should not win.

**Tuning U (38 files): 0.5748 -> 0.5976.  M: 0.5057 unchanged.**  Runtime 1.00x.

**KEPT** (`zfloor=3.0`, floor only).  *Reason: one file changes (012_NAB 0.133 -> 1.000) and the
floor sits mid-plateau — no overriding file has z-max in (2.1, 3.49).*

**Rejected alternatives:** the rule as first written, `z >= max(anchor z-max, 3)`: 0.5843 — it
*also* loses 852_OPPORTUNITY 0.995 -> 0.490 (*comparing the z-maxes of two differently shaped
score distributions is not apples-to-apples, and it is the more complex rule*); `zfloor` 4:
0.5843 (*above the plateau, drops a right override*); `zfloor` 2: 0.5976, identical (*inside the
plateau, no reason to prefer the edge*).  300_TODS stayed lost: both signals point the wrong way
there, so it is a genuine disagreement, not a flatness artefact.

---

## 4. Measurement widening + flat fallback when both scores are flat

**Step 0 correction (before the hypothesis):** the last two gains were one file each on 38 files.
I widened the U Tuning set to **47 of 48 files** (cap 3e9 -> 6e10, 27.5 min wall) and re-scored
everything: MMPAD 0.4346 -> **0.4240**, Sub-PCA 0.3631 -> **0.3320**, the kurtosis chooser
0.5748 -> 0.5541, the chooser with the z-max floor (the then-current Tremor) 0.5976 -> **0.5725**,
two-component oracle 0.6295 -> **0.5987**.  On the 9 unseen files the chooser picked the better
component **9 times out of 9** — the experiment 2-3 gains were not subset artefacts.

**Hypothesis:** when *both* kurtoses are below `tau` the kurtosis signal is uninformative, yet
Sub-PCA was the better component on 3 of the 5 known flat files.  Fall back to the component
whose maximum stands out most (highest z-max).

**Tuning U (47 files): 0.5725 -> 0.5843.  M: 0.5057 unchanged.**  Runtime 1.02x MMPAD.

**KEPT** (`tau=0.5`, `flat='zmax'`, `zprior=0.0`).  *Reason: +0.0118 with 4 files up / 3 down,
and the tau plateau (0.29, 4.62) is wide enough that the threshold is not doing the work.*

**Rejected alternatives (47 files):** (a) "when flat, take Sub-PCA" 0.5843 — identical score but
a much narrower tau plateau, (0.29, 0.61) (*it is right by luck on this set: tau 0.75 -> 0.5721,
tau 2 -> 0.5635, because Sub-PCA is wrong on 021_NAB, 291_TODS, 568_YAHOO*); (b) **mean of the two
rank-normalised scores** when flat, 0.5817 at tau 0.5 / 0.5790 at tau 1.0 (*one genuine synergy,
053_WSD 0.01 -> 0.19, but it loses 142_MSL; blending loses again*); (c) z-max fallback **with an
anchor z prior 0.5**: 0.5891, i.e. +0.005 *better* than what was kept — **rejected anyway**
because the difference is a single file (070_WSD, 0.0044 of the mean) and it costs an extra
hyper-parameter (*fewer parameters preferred; the zprior plateau [0, 0.33) vs (0.33, 0.75)
straddles that one file*).

---

## 5. Point component: a third component for the series neither detector sees

**Hypothesis:** many Tuning files (WSD, IOPS, YAHOO 583/643, 142_MSL, 182/200_SMD) are point
anomalies that both a discord detector and a subsequence-residual detector miss.  Add an O(n)
point component: robust z of the first differences, `|dx - median(dx)| / (1.4826 MAD)`, centred
max-filter over the benchmark's own ACF period, and let it enter **the flat fallback only**.

**Component alone on the 47 files: 0.4463 — the spike detector by itself beats MMPAD (0.4240).**

**Tuning U (47 files): 0.5843 -> 0.6421.  M: 0.5057 unchanged.**  Runtime 1.00x (milliseconds).

**KEPT** (`point_window='period'`, `flat_only=(2,)`).  *Reason: +0.0578, exactly 5 files change
and all 5 go up (033_WSD 0.001 -> 0.382, 053_WSD 0.009 -> 0.782, 070_WSD 0.026 -> 0.530, 142_MSL
0.205 -> 0.974, 270_IOPS 0.027 -> 0.315); no dataset already at its oracle moves.*  The gain
crossed the 0.05 too-good-to-be-true threshold, so I re-read the diff: the component reads the
series and its own ACF period, nothing else.

**Rejected alternatives:** max-filter window **1 (no filter)** 0.6013 and **half the period**
0.6382 (*an isolated spike must cover its event; the period is the benchmark's own window, not a
tuned value*).  **Letting the point component override peaked scores by a plain z floor:** best
cell 0.6688 at `pzfloor=8` — **rejected because it is a one-cell peak** (5 -> 0.6417, 8 ->
0.6688, 10 -> 0.6637, 12 -> 0.6478, 30 -> 0.6421), made of single files in both directions (wins
182_SMD and 583_YAHOO, loses 210_SMD 0.958 -> 0.802 and 003_NAB).  *Reason: the point score's own
kurtosis is huge on nearly every file, so its peakedness is not a usable confidence signal — a
gate needs a different signal.*  That became the next hypothesis.

---

## 6. Override gates: gate the point override on **disagreement** and **specificity**

**Hypothesis:** find a label-free gate *with a plateau* under which the point component may
replace a peaked winner.  Screened exactly from the cached score arrays (no re-running):
47 files x {6 kfrac x 10 athr in both directions, 7 sthr x 8 cthr, 15 zthr}, then every pair and
triple.

**Tuning U (47 files): 0.6421 -> 0.6713.  M: 0.5057 unchanged.**  Runtime 1.00x.

**KEPT** — three gates, all read off the score arrays: point z-max >= `pzmin` 7; at most `athr`
0.5 of the point score's top-1% (`kfrac` 0.01) positions lie in the winner's top-1%; at most
`cthr` 5 separate runs above `sthr` 10.  *Reason: exactly 4 files change and all 4 go up
(182_SMD 0.115 -> 0.845, 583_YAHOO 0.052 -> 0.446, 045_WSD 0.211 -> 0.424, 200_SMD 0.137 ->
0.176), and every threshold sits inside a plateau: pzmin [5.8, 8.1] identical, athr [0.4, 0.81]
identical, cthr [5, 54] 0.6713-0.6734, sthr [10, 20], kfrac [0.005, 0.02] identical.*

**Rejected alternatives:** every **single** gate without a z floor, 0.44-0.65 (*the point
component then overrides files where it found nothing — z-max 1-3 on MGAB, SED, UCR, SVDB*);
**'zanchor' (the winner's own z-max is low)** — useless even with the floor, because
852/864_OPPORTUNITY and 280_NEK are weakly held *and* wrong for the point component (*"weakly
held" is not "wrong"*); **agreement in the direction I had first assumed** (override where the
two detectors *agree*) — backwards: where the top-1% sets coincide (210_SMD 0.86, 535_SMAP 0.82,
004_NAB 0.82) the context-aware winner is as good or better, and every right override is a
*disagreement* (583_YAHOO 0.00, 182_SMD 0.03, 045_WSD 0.24); the **2-gate rule** (z floor +
spike count, no disagreement test) **0.6716, marginally higher than what was kept** — rejected
because it flips 535_SMAP 0.882 -> 0.881 on a dataset already at its oracle, and the
disagreement gate is the hypothesis the data actually supports; the **low edge of every plateau
at once** (pzmin 6, athr 0.3, cthr 3) 0.6705 (*-0.0008: the plateau is real and the kept cell is
not on its edge*).

**Sensitivity cells recorded afterwards:** 3-gate low edge 0.6705, 2-gate rule 0.6716 vs kept
0.6713.

**Where this left U:** gap to the three-component oracle 0.0177, of which 300_TODS 0.0096 and
217_LTDB 0.0052 — both indistinguishable without labels.  **The U chooser is saturated on the
Tuning files; further U gains need better components or more files.**

---

## 7. Point-M: carry the idea to the M track

**Step 0 widening:** M Tuning 6 -> **14 files** (~110 min wall).  Re-scored: **MMPAD-M 0.4193**
(the 6-file value had been 0.5057 — the added files are hard).

**Hypothesis:** the same point idea per channel.  `point_m`: the univariate point score on every
channel, degenerate channels dropped, aggregated per timestamp; it enters the chooser as the
flat-fallback member (there is no Sub-PCA on M).

**Tuning M (14 files): 0.4193 -> 0.5217.  U: 0.6713 unchanged by construction** (verified: the
promoted `fuse` reproduces the experiment-6 output on all 47 cached U files).  Runtime 1.00x.

**KEPT** (`point_m_agg='top3z'` = the mean of the three largest per-channel z, `flat_only_m=(1,)`,
**`override_m=None`**).  *Reason: +0.1024, and it changes exactly the 6 files where MMPAD-M is
flat (5 up, 1 down by 0.03); the 8 peaked files are untouched.*  Over the 0.05 threshold, so I
re-read the diff: per-channel differences, median/MAD and per-channel ACF period, nothing else.

**Rejected alternatives (14 files):** aggregation **`maxrank`** (max over channels of the
per-channel *rank-normalised* score — my first wording of the idea) 0.4512 inside the chooser,
0.4022 alone (*rank-normalising per channel destroys the z scale, so the aggregate's z-max is
1-2 and the flat fallback almost never picks it*); aggregation **`maxz`** 0.4959 / 0.3909 (*a
single noisy channel dominates*); **the U override gates transplanted verbatim onto M** 0.5046 —
they never fire on 13 of the 14 files (the channel-aggregated z-max on peaked files is 0.1-4.1,
because max/top-3 over channels raises the score floor) and on 195_Exathlon they fire
**wrongly**, 0.946 -> 0.706 (*the U thresholds do not transfer to an aggregated scale*);
**lowering pzmin to 4 on `maxz`** 0.5489 — it would win 164_SMAP 0.010 -> 0.751 but is a
**one-file plateau** (no file has z in (2.6, 4.6)), with `top3z` the equivalent pzmin 3 admits
023_MITDB 0.653 -> 0.004, and it keeps the Exathlon loss.  *Reason: a threshold with no plateau
is a fitted constant.*  Logged as a hypothesis instead.

---

## 8. Strongest-channel gate: gate the M override on the **strongest channel**, not the aggregate

**Step 0 widening:** M Tuning 14 -> **15 files** (107_SVDB finished in the background queue).
Re-scored: **MMPAD-M 0.4368**, the experiment-7 rule (control) **0.5324**, point-M 0.4245,
two-component oracle 0.6388.

**Hypothesis:** experiment 7 showed the aggregated z-max cannot separate the right overrides
(011_MSL, 164_SMAP) from the wrong one (195_Exathlon).  Evaluate the *same three U gates* on the
**strongest single channel's own point score** (`point_m.best_channel`, the channel with the
largest robust z-max), passed to `fuse` as a gate-only component that can never be chosen.

**Tuning M (15 files): 0.5324 -> 0.6373.  U: 0.6713 unchanged by construction.**  Runtime 1.00x.

**KEPT** (`override_m=('pz','agree','spikes')`, `gate_m=2`, pzmin 7 and sthr 10 = the U values,
`cthr_m=10`).  *Reason: exactly 2 files change and both go up — 011_MSL 0.038 -> 0.870 (channel
z 10.6, 6 runs) and 164_SMAP 0.010 -> 0.751 (11.0, 6 runs) — the 6 other peaked files keep
MMPAD-M, and the chooser then sits 0.0015 from the two-component oracle on these files.*

**Plateaus (exact, 15 files):** pzmin (6.19, 10.58] identical; cthr [6, 153] identical; sthr
[5, 20]; athr [0, 1] (inactive on M: every agreement is <= 0.10); tau (0.2, 0.64].

**Rejected alternatives:** the **U value cthr 5 verbatim** — never fires, because both target
files have exactly 6 runs above 10, so it equals the control 0.5324 (`cthr_m=10` was chosen
inside *both* the U plateau [5, 54] and the M plateau [6, 153]); **pzmin 6** 0.5940 (*below the
plateau: 023_MITDB enters at channel z 6.19 and drops 0.653 -> 0.004*); **cthr 50** 0.6373,
identical (*inside the plateau; the next file to enter is 082_LTDB at 154 runs*); **clipped
(5-1000) and log per-channel z aggregates** — no separation at all, dead on arrival (*the
quantised-channel z blow-up they were meant to tame is not what distinguishes the targets*);
**the fraction of channels firing <= 0.6 instead of the spike count** — *identical* 0.6373 on the
15 files with its own plateau [0.45, 0.85], and **rejected only on out-of-sample behaviour**: on
the 5 files with no MMPAD-M score yet it would also admit 131_OPPORTUNITY (0.38) and 140_CATSv2
(0.53), where the spike gate admits only 040/049_GHL.

**Sensitivity cells recorded afterwards (15 files):** frac gate 0.6373 identical, cthr 5 =
control 0.5324, cthr 50 0.6373, pzmin 6 0.5940 (= 023_MITDB admitted).

**Honest caveat recorded at the time:** the cthr low edge *is* the two target files — a one-sided
plateau on a two-target set.

---

## 9. Held-out check: Eval on cost-capped subsets (no code change)

Ran Tremor on **cost-capped subsets** of both Eval lists (3 h 57 min wall on 4 cores) and
compared with the authors' published per-series scores on exactly the same files.

| track | subset | files | share of the Eval list (files / MMPAD proxy cost) | Tremor | MMPAD same files | 2nd reference same files |
|---|---|---|---|---|---|---|
| U | `--max-cost 6e10` | 339 / 350 | 96.9% / 23.7% | **0.6142** | 0.4400 | Sub-PCA 0.4277 |
| M | `--max-cost 1e11` | 75 / 180 | 41.7% / **1.1%** | **0.4632** | 0.3276 | PCA-M 0.3180 (stale table) |

**Nothing was changed on the basis of these numbers**, and the open-hypothesis list was left as
it was.  The U subset is close to unbiased (MMPAD's own published mean is 0.4352 on the 11
excluded files vs 0.4400 on the 339).  **The M subset is biased in Tremor's favour** and is
reported that way everywhere — see README.md, "What this does not establish", and
`docs/eval-results.md`.

---

## 10. The full U Eval list (no code change)

The 11 U files above the 6e10 cost cap (7 MITDB, 2 UCR, CATSv2, SWaT — 3.1% of the files but
**76.3% of the U track's proxy cost**, 18.9 of 24.7 core-hours) were run with the cap lifted,
completing the **full 350-file U Eval list** in 5 h 37 min wall with 0 failures.

| track | files | share of the Eval list (files / cost) | **Tremor** | MMPAD same files | Sub-PCA same files |
|---|---|---|---|---|---|
| U | **350 / 350** | **100% / 100%** | **0.6085** | 0.4399 (**+0.1686**) | 0.4234 (+0.1851) |

204 files up / 51 down / 95 identical.  The experiment-9 bias analysis had *predicted* a
full-list-equivalent of **0.6085**; the measured value is **0.6085**.  On the 11 newly run files
Tremor scores 0.4328 vs MMPAD 0.4352 — all seven MITDB files identical to four decimals (the spike
gate correctly keeps the point component out of long ECG, so the chooser keeps MMPAD), 331_UCR
+0.0003, 525_UCR identical, 550_SWaT -0.0001, 286_CATSv2 -0.0266.  **The M track was not touched
and remains a biased 41.7%-of-files / 1.1%-of-cost subset.**  Full tables in
`docs/eval-results.md`.

Packaging work (`pyproject.toml`, `tremor/cli.py`, `tests/`, `README.md`, this file) landed
alongside; **no scoring code, hyper-parameter or decision was touched.**

---

## What is still open

1. **Cheaper MMPAD-M** — the M chooser is *at* its two-component oracle on the 15 Tuning files,
   so the M track is blocked on component cost and coverage, not on the chooser.
2. **Window floor / multi-window MMPAD on U** — `sub_len >= 64` smears point anomalies on
   003/007_NAB, 200_SMD, 643_YAHOO.  Stake ~+0.02 U.
3. **Better M components for the ECG files** — 028_MITDB 0.10, 113_SVDB 0.20 are MMPAD-M's own
   failures.
4. **174_MITDB** would complete the U Tuning set at 48/48.
