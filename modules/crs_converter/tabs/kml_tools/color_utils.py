"""Color utility functions for HEX <-> KML color conversion.

KML uses aaBBGGRR format (alpha-Blue-Green-Red),
while HTML/CSS uses #RRGGBB.
"""


def hex_to_kml_color(hex_color, opacity_percent=100):
    """Convert HTML #RRGGBB + opacity percentage to KML aaBBGGRR format.

    Args:
        hex_color: HTML color string like '#FF0000' or 'FF0000'
        opacity_percent: 0-100, where 0=transparent, 100=opaque

    Returns:
        KML color string like '7dff0000'
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        hex_color = '000000'

    r = hex_color[0:2].lower()
    g = hex_color[2:4].lower()
    b = hex_color[4:6].lower()

    alpha = int(255 * max(0, min(100, opacity_percent)) / 100)
    aa = format(alpha, '02x')

    return f"{aa}{b}{g}{r}"


def kml_color_to_hex(kml_color):
    """Convert KML aaBBGGRR to HTML (#RRGGBB, opacity_percent).

    Args:
        kml_color: KML color string like '7dff0000'

    Returns:
        Tuple of (hex_color, opacity_percent)
    """
    kml_color = kml_color.lower()
    if len(kml_color) != 8:
        return '#000000', 100

    aa = kml_color[0:2]
    b = kml_color[2:4]
    g = kml_color[4:6]
    r = kml_color[6:8]

    hex_color = f"#{r}{g}{b}".upper()
    opacity = round(int(aa, 16) / 255 * 100)

    return hex_color, opacity
