"""Defer importing umap-learn (~175 MB with numba/sklearn) until a citation plot is
actually drawn. Kotaemon imports it at start-up for the optional "citation
visualisation" (off by default), which alone keeps small Railway plans from booting."""
import importlib
import sys
import types


class _LazyUMAP:
    def __new__(cls, *args, **kwargs):
        shim = sys.modules.pop("umap")
        try:
            real = importlib.import_module("umap")
        except Exception:
            sys.modules["umap"] = shim
            raise
        return real.UMAP(*args, **kwargs)


def install():
    if "umap" not in sys.modules:
        mod = types.ModuleType("umap")
        mod.UMAP = _LazyUMAP
        sys.modules["umap"] = mod
