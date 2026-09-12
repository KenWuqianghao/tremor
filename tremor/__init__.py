"""tremor -- confidence-weighted fusion detector for TSB-AD (CPU-only)."""
from .fusion import fuse, rank_norm, confidence
from .detector import Tremor, run_Tremor_Unsupervised, DEFAULT_HP
__version__ = '0.1.0'
