"""Shared localization and lazy Shapely access for topology components."""

from .tab_text import tab_text


def tx(key, **kwargs):
    return tab_text("topology", key, **kwargs)


_shapely_loads = None


def get_shapely():
    global _shapely_loads
    if _shapely_loads is None:
        from shapely.wkt import loads

        _shapely_loads = loads
    return _shapely_loads
