"""Components used by :mod:`cadastral_tools.ui.symbology_tab`."""

__all__ = ["SymbologyTab"]


def __getattr__(name):
    if name == "SymbologyTab":
        from ..symbology_tab import SymbologyTab

        return SymbologyTab
    raise AttributeError(name)
