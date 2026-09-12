"""Minimal stand-in for `torch` so that TSB_AD's model_wrapper / utility modules import
without PyTorch. Only used when the real torch is absent (see harness/common.py).
Nothing here is ever executed by the methods run here (MMPAD CPU backend, PCA, SAND)."""
import sys as _sys, types as _types

class _Cuda:
    @staticmethod
    def is_available():
        return False
    @staticmethod
    def manual_seed(*a, **k):
        pass
    @staticmethod
    def manual_seed_all(*a, **k):
        pass

cuda = _Cuda()

def manual_seed(*a, **k):
    pass

class _Stub:
    def __init__(self, *a, **k):
        pass
    def __call__(self, *a, **k):
        raise RuntimeError("torch stub: PyTorch is not installed in this environment")

nn = _types.ModuleType("torch.nn")
for _name in ("Module", "ReLU", "Sigmoid", "Tanh", "LeakyReLU", "Linear", "Parameter"):
    setattr(nn, _name, type(_name, (_Stub,), {}))
_sys.modules["torch.nn"] = nn

class _Backends:
    class cudnn:
        benchmark = False
        deterministic = True
        @staticmethod
        def version():
            return None
backends = _Backends()
class Tensor: pass

__version__ = "0.0.0-stub"
