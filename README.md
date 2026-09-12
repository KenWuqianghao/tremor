# Tremor

Experiments towards a CPU-only anomaly detector for the [TSB-AD](https://github.com/TheDatumOrg/TSB-AD)
benchmark, starting from its strongest classical methods (MMPAD, Sub-PCA).

So far this is the harness: `harness/run.py` runs one detector over one (track, split) file list
with the benchmark's own scoring (`TSB_AD.evaluation.metrics.get_metrics` with
`find_length_rank(data[:,0], rank=1)`, exactly as `Run_Detector_U.py` does), writes one JSON
result per file so an interrupted run resumes, and caches the float32 score arrays;
`harness/report.py` compares a run with the authors' published per-series tables.
`harness/shims/torch` is a numpy stub so the upstream CPU code imports without PyTorch.

Data goes in `data/TSB-AD-U/` and `data/TSB-AD-M/` (download links in `docs/benchmark-notes.md`);
the upstream clone goes in `upstream/`.  Both are gitignored.

```bash
python harness/file_stats.py                                   # per-file length / cost table
python harness/run.py --track U --split tuning --method MMPAD --workers 4
python harness/report.py runs/U_tuning_MMPAD --ref leaderboard:Uni_MMPAD
```

License: Apache-2.0, matching TSB-AD.
