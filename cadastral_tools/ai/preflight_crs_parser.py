"""Pure WKT parsing helpers for preflight CRS validation."""
import re


def extract_wkt_params(wkt: str) -> dict:
    """Extract projection, datum, central meridian, and scale factor."""
    params: dict = {}
    central_meridian = re.search(
        r'PARAMETER\["(?:central_meridian|longitude_of_center|'
        r'Longitude of natural origin)"[,\s]+([\d.+-]+)',
        wkt,
        re.IGNORECASE,
    )
    if central_meridian:
        params["central_meridian"] = float(central_meridian.group(1))
    scale_factor = re.search(
        r'PARAMETER\["(?:scale_factor|Scale factor at natural origin)"'
        r'[,\s]+([\d.+-]+)',
        wkt,
        re.IGNORECASE,
    )
    if scale_factor:
        params["scale_factor"] = float(scale_factor.group(1))
    projection = re.search(r'PROJECTION\["([^"]+)"\]', wkt, re.IGNORECASE)
    if projection:
        params["projection"] = projection.group(1)
    datum = re.search(r'DATUM\["([^"]+)"\]', wkt, re.IGNORECASE)
    if datum:
        params["datum"] = datum.group(1)
    return params
