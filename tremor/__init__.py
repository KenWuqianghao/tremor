"""tremor -- confidence-weighted fusion detector for TSB-AD (CPU-only)."""
from .fusion import fuse, rank_norm, confidence
from .detector import Tremor, run_Tremor_Unsupervised, fuse_components, DEFAULT_HP
from .point import point_score
from .point_m import point_m_score, point_m_scores
__version__ = '0.1.0'
