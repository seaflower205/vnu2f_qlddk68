"""Merge multiple SHP files into a single KML/KMZ with per-layer styling.

Each SHP becomes a <Folder> inside a single <Document>.
Each layer gets its own independent style, label, and popup config.
"""

import os
import zipfile

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
)

from .color_utils import hex_to_kml_color
from .html_template import HtmlTemplateBuilder
from .merge_placemark_mixin import MergePlacemarkMixin


WKB_POINT_GEOMETRY = QgsWkbTypes.PointGeometry
WKB_LINE_GEOMETRY = QgsWkbTypes.LineGeometry
WKB_POLYGON_GEOMETRY = QgsWkbTypes.PolygonGeometry


class MergeKmlBuilder(MergePlacemarkMixin):
    """Build a single KML/KMZ from multiple SHP files with per-layer config."""

    GEOM_POINT = 'point'
    GEOM_LINE = 'line'
    GEOM_POLYGON = 'polygon'

    def build(self, layer_configs, output_path, output_format='kml'):
        """Build merged KML/KMZ.

        Args:
            layer_configs: list of (shp_path, config_dict).
                           Each config_dict has the same structure as before
                           (name_fields, description_fields, polygon_style, etc.)
            output_path: path for the output .kml or .kmz
            output_format: 'kml' or 'kmz'

        Returns:
            (success: bool, message: str)
        """
        try:
            target_crs = QgsCoordinateReferenceSystem('EPSG:4326')
            kml_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<kml xmlns="http://www.opengis.net/kml/2.2">',
                '<Document>',
                '<name>Merged SHP Layers</name>'
            ]

            # Pre-scan layers to build styles
            layer_infos = []
            errors = []
            for i, (shp_path, cfg) in enumerate(layer_configs):
                basename = os.path.splitext(
                    os.path.basename(shp_path))[0]
                layer = QgsVectorLayer(shp_path, basename, 'ogr')
                if not layer.isValid():
                    errors.append(f"Cannot load: {basename}")
                    layer_infos.append(None)
                    continue
                gtype = self._detect_geom_type(layer)
                if gtype is None:
                    errors.append(f"Unknown geometry: {basename}")
                    layer_infos.append(None)
                    continue
                layer_infos.append((layer, gtype, basename))
                # Build style for this layer
                style_id = f'style_{i}'
                kml_lines.extend(
                    self._build_layer_style(style_id, gtype, cfg))

            # Build placemarks
            loaded_count = 0
            for i, (shp_path, cfg) in enumerate(layer_configs):
                info = layer_infos[i]
                if info is None:
                    continue
                layer, gtype, basename = info
                style_id = f'style_{i}'

                transform = None
                if layer.crs() != target_crs:
                    transform = QgsCoordinateTransform(
                        layer.crs(), target_crs,
                        QgsProject.instance())

                name_cfg = cfg.get('name_fields', {})
                popup_on = cfg.get('popup_enabled', True)
                html_builder = (HtmlTemplateBuilder(cfg)
                                if popup_on else None)

                kml_lines.append('<Folder>')
                kml_lines.append(
                    f'<name>{self._esc(basename)}</name>')

                for feat in layer.getFeatures():
                    pm = self._build_placemark(
                        feat, gtype, name_cfg, transform,
                        style_id, html_builder)
                    if pm:
                        kml_lines.extend(pm)

                kml_lines.append('</Folder>')
                loaded_count += 1

            kml_lines.extend(['</Document>', '</kml>'])
            kml_content = '\n'.join(kml_lines)

            if loaded_count == 0:
                err_detail = (
                    '\n'.join(errors) if errors
                    else 'No valid layers')
                return False, f"No layers exported.\n{err_detail}"

            if output_format == 'kmz':
                ok, msg = self._write_kmz(kml_content, output_path)
            else:
                ok, msg = self._write_kml(kml_content, output_path)

            if ok and errors:
                msg += "\n\nWarnings:\n" + '\n'.join(errors)

            return ok, msg

        except Exception as e:  # noqa: BLE001 — intentional suppress
            return False, f"Error: {str(e)}"

    def _detect_geom_type(self, layer):
        """Detect geometry type of a vector layer."""
        gt = layer.geometryType()
        if gt == WKB_POINT_GEOMETRY:
            return self.GEOM_POINT
        elif gt == WKB_LINE_GEOMETRY:
            return self.GEOM_LINE
        elif gt == WKB_POLYGON_GEOMETRY:
            return self.GEOM_POLYGON
        return None



    def _build_name(self, feat, cfg):
        """Build display name from field config.

        Returns empty string when both fields are disabled.
        """
        f1 = cfg.get('field1', '')
        f2 = cfg.get('field2', '')
        f1_on = cfg.get('field1_enabled', True)
        f2_on = cfg.get('field2_enabled', True)
        sep = cfg.get('separator', ' - ')
        fnames = [f.name() for f in feat.fields()]
        v1 = (str(feat[f1])
              if f1_on and f1 in fnames and feat[f1] is not None
              else '')
        v2 = (str(feat[f2])
              if f2_on and f2 in fnames and feat[f2] is not None
              else '')
        if v1 and v2:
            return f"{v1}{sep}{v2}"
        return v1 or v2 or ''

    # ── Geometry writers ──────────────────────────────

    def _poly_kml(self, geom):
        lines = []
        if geom.isMultipart():
            lines.append('<MultiGeometry>')
            for part in geom.asMultiPolygon():
                lines.extend(self._single_poly(part))
            lines.append('</MultiGeometry>')
        else:
            p = geom.asPolygon()
            if p:
                lines.append('<MultiGeometry>')
                lines.extend(self._single_poly(p))
                lines.append('</MultiGeometry>')
        return lines

    def _single_poly(self, rings):
        lines = [
            '<Polygon>',
            '<outerBoundaryIs><LinearRing><coordinates>'
        ]
        lines.append(
            ' '.join(f'{p.x()},{p.y()},0' for p in rings[0]))
        lines.append(
            '</coordinates></LinearRing></outerBoundaryIs>')
        for i in range(1, len(rings)):
            lines.append(
                '<innerBoundaryIs><LinearRing><coordinates>')
            lines.append(
                ' '.join(
                    f'{p.x()},{p.y()},0' for p in rings[i]))
            lines.append(
                '</coordinates></LinearRing></innerBoundaryIs>')
        lines.append('</Polygon>')
        return lines

    def _line_kml(self, geom):
        lines = []
        if geom.isMultipart():
            lines.append('<MultiGeometry>')
            for part in geom.asMultiPolyline():
                lines.append('<LineString><coordinates>')
                lines.append(
                    ' '.join(
                        f'{p.x()},{p.y()},0' for p in part))
                lines.append('</coordinates></LineString>')
            lines.append('</MultiGeometry>')
        else:
            pl = geom.asPolyline()
            if pl:
                lines.append('<LineString><coordinates>')
                lines.append(
                    ' '.join(
                        f'{p.x()},{p.y()},0' for p in pl))
                lines.append('</coordinates></LineString>')
        return lines

    def _pt_kml(self, geom):
        lines = []
        if geom.isMultipart():
            lines.append('<MultiGeometry>')
            for pt in geom.asMultiPoint():
                lines.append(
                    f'<Point><coordinates>'
                    f'{pt.x()},{pt.y()},0'
                    '</coordinates></Point>')
            lines.append('</MultiGeometry>')
        else:
            pt = geom.asPoint()
            lines.append(
                f'<Point><coordinates>'
                f'{pt.x()},{pt.y()},0'
                '</coordinates></Point>')
        return lines

    # ── I/O helpers ───────────────────────────────────

    @staticmethod
    def _write_kml(content, path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"KML saved: {path}"
        except Exception as e:  # noqa: BLE001 — intentional suppress
            return False, str(e)

    @staticmethod
    def _write_kmz(kml_content, path):
        try:
            with zipfile.ZipFile(
                    path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('doc.kml', kml_content)
            return True, f"KMZ saved: {path}"
        except Exception as e:  # noqa: BLE001 — intentional suppress
            return False, str(e)

    @staticmethod
    def _esc(t):
        if t is None:
            return ''
        return str(t).replace('&', '&amp;').replace(
            '<', '&lt;').replace('>', '&gt;')
