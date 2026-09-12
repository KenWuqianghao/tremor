"""Shared plumbing for the harness: paths, sys.path setup, file lists, evaluation."""
import os, sys, importlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM = os.path.join(ROOT, "upstream")
DATA = os.path.join(ROOT, "data")
RUNS = os.path.join(ROOT, "runs")
FILE_LISTS = os.path.join(UPSTREAM, "Datasets", "File_List")

TRACK_DIR = {"U": os.path.join(DATA, "TSB-AD-U"), "M": os.path.join(DATA, "TSB-AD-M")}
LIST_FILE = {
    ("U", "tuning"): "TSB-AD-U-Tuning.csv",
    ("U", "eval"): "TSB-AD-U-Eva.csv",
    ("M", "tuning"): "TSB-AD-M-Tuning.csv",
    ("M", "eval"): "TSB-AD-M-Eva.csv",
}


def setup_paths():
    """Make `TSB_AD` (upstream clone) importable; fall back to a torch stub if PyTorch
    is absent (the CPU methods run here never execute torch code)."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    if UPSTREAM not in sys.path:
        sys.path.insert(0, UPSTREAM)
    try:
        importlib.import_module("torch")
        return
    except ImportError:
        pass
    if getattr(setup_paths, "_stubbed", False):
        return
    # Bind the stub only while importing the two TSB_AD modules that `import torch` at
    # module level, then remove it again so that tslearn (KShapeAD) sees "no torch" and
    # picks its numpy backend.
    # Warm up the scientific stack first so its own torch-detection sees "no torch".
    for m in ("numpy", "scipy", "scipy.stats", "sklearn", "pandas", "statsmodels.tsa.stattools",
              "stumpy", "tslearn", "tslearn.clustering", "tslearn.metrics"):
        try:
            importlib.import_module(m)
        except ImportError:
            pass
    shim = os.path.join(ROOT, "harness", "shims")
    sys.path.insert(0, shim)
    stub = importlib.import_module("torch")
    try:
        importlib.import_module("TSB_AD.utils.utility")
        importlib.import_module("TSB_AD.models.MMPAD")
    finally:
        sys.path.remove(shim)
        for k in [k for k in sys.modules if k == "torch" or k.startswith("torch.")]:
            del sys.modules[k]
    setup_paths._stubbed = True


def file_list(track, split):
    import pandas as pd
    return list(pd.read_csv(os.path.join(FILE_LISTS, LIST_FILE[(track, split)]))["file_name"].values)


def dataset_of(filename):
    # e.g. 001_NAB_id_1_Facility_tr_1007_1st_2014.csv -> NAB
    return filename.split("_")[1]


def load_series(track, filename):
    """Exactly as upstream benchmark_exp/Run_Detector_U.py / Run_Detector_M.py."""
    import pandas as pd
    df = pd.read_csv(os.path.join(TRACK_DIR[track], filename)).dropna()
    data = df.iloc[:, 0:-1].values.astype(float)
    label = df["Label"].astype(int).to_numpy()
    return data, label


def evaluate(output, data, label):
    """Benchmark's own scoring, exactly as in upstream Run_Detector_U/M.py (slidingWindow
    from the first channel's ACF period, rank=1)."""
    setup_paths()
    from TSB_AD.evaluation.metrics import get_metrics
    from TSB_AD.utils.slidingWindows import find_length_rank
    slidingWindow = find_length_rank(data[:, 0].reshape(-1, 1), rank=1)
    return get_metrics(output, label, slidingWindow=slidingWindow)
