"""Mechanically extracted responsibilities from merge_builder.py."""

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


class MergePlacemarkMixin:
    def _build_layer_style(self, style_id, gtype, cfg):
        """Build KML <Style> for one layer."""
        lines = []
        name_cfg = cfg.get('name_fields', {})
        name_color = hex_to_kml_color(
            name_cfg.get('font_color', '#000000'), 100)
        name_size = name_cfg.get('font_size', 12)
        label_scale = round(max(0.5, name_size / 12.0), 1)

        if gtype == self.GEOM_POINT:
            pt_style = cfg.get('point_style', {})
            pt_color = hex_to_kml_color(
                pt_style.get('icon_color', '#FF4444'), 100)
            pt_scale = pt_style.get('icon_scale', 1.0)
            lines.append(f'<Style id="{style_id}">')
            lines.append(
                f'<IconStyle><color>{pt_color}</color>'
                f'<scale>{pt_scale}</scale></IconStyle>')
            lines.append(
                f'<LabelStyle><color>{name_color}</color>'
                f'<scale>{label_scale}</scale></LabelStyle>')
            lines.append('</Style>')

        elif gtype == self.GEOM_LINE:
            ln_style = cfg.get('line_style', {})
            ln_color = hex_to_kml_color(
                ln_style.get('line_color', '#0000FF'), 100)
            ln_width = ln_style.get('line_width', 2)
            lines.append(f'<Style id="{style_id}">')
            lines.append(
                '<IconStyle><scale>0</scale></IconStyle>')
            lines.append(
                f'<LabelStyle><color>{name_color}</color>'
                f'<scale>{label_scale}</scale></LabelStyle>')
            lines.append(
                f'<LineStyle><color>{ln_color}</color>'
                f'<width>{ln_width}</width></LineStyle>')
            lines.append('</Style>')

        elif gtype == self.GEOM_POLYGON:
            pg_style = cfg.get('polygon_style', {})
            pg_border = hex_to_kml_color(
                pg_style.get('border_color', '#FF0000'), 100)
            pg_fill = hex_to_kml_color(
                pg_style.get('fill_color', '#00FF00'),
                pg_style.get('fill_opacity', 50))
            pg_bw = pg_style.get('border_width', 2)
            lines.append(f'<Style id="{style_id}">')
            lines.append(
                '<IconStyle><scale>0</scale></IconStyle>')
            lines.append(
                f'<LabelStyle><color>{name_color}</color>'
                f'<scale>{label_scale}</scale></LabelStyle>')
            lines.append(
                f'<LineStyle><color>{pg_border}</color>'
                f'<width>{pg_bw}</width></LineStyle>')
            lines.append(
                f'<PolyStyle><color>{pg_fill}</color>'
                '</PolyStyle>')
            lines.append('</Style>')

        return lines
    def _build_placemark(self, feat, gtype, name_cfg,
                         transform, style_id, html_builder):
        """Build placemark XML lines for a feature."""
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            return []

        if transform:
            geom.transform(transform)

        name = self._build_name(feat, name_cfg)
        fdata = {f.name(): feat[f.name()] for f in feat.fields()}
        desc = html_builder.build(fdata) if html_builder else ''

        lines = []

        if gtype == self.GEOM_POLYGON:
            # Placemark 1: Polygon shape without label
            lines.extend([
                '<Placemark>', '<name></name>',
                f'<styleUrl>#{style_id}</styleUrl>',
                f'<description><![CDATA[{desc}]]></description>'
            ])
            lines.extend(self._poly_kml(geom))
            lines.append('</Placemark>')

            # Placemark 2: Centroid label point with Region
            if name:
                centroid = (geom.pointOnSurface()
                            if hasattr(geom, 'pointOnSurface')
                            else geom.centroid())
                if centroid and centroid.asPoint():
                    pt = centroid.asPoint()
                    north = pt.y() + 0.0002
                    south = pt.y() - 0.0002
                    east = pt.x() + 0.0002
                    west = pt.x() - 0.0002
                    lines.extend([
                        '<Placemark>',
                        f'<name>{self._esc(name)}</name>',
                        f'<styleUrl>#{style_id}</styleUrl>',
                        f'<description><![CDATA[{desc}]]>'
                        '</description>',
                        '<Region><LatLonAltBox>',
                        f'<north>{north}</north>'
                        f'<south>{south}</south>',
                        f'<east>{east}</east>'
                        f'<west>{west}</west>',
                        '</LatLonAltBox><Lod>'
                        '<minLodPixels>16</minLodPixels>'
                        '<maxLodPixels>-1</maxLodPixels>'
                        '</Lod></Region>',
                        f'<Point><coordinates>'
                        f'{pt.x()},{pt.y()},0'
                        '</coordinates></Point>',
                        '</Placemark>'
                    ])

        elif gtype == self.GEOM_LINE:
            lines.extend([
                '<Placemark>',
                f'<name>{self._esc(name)}</name>',
                f'<styleUrl>#{style_id}</styleUrl>',
                f'<description><![CDATA[{desc}]]></description>'
            ])
            lines.extend(self._line_kml(geom))
            lines.append('</Placemark>')

        elif gtype == self.GEOM_POINT:
            lines.extend([
                '<Placemark>',
                f'<name>{self._esc(name)}</name>',
                f'<styleUrl>#{style_id}</styleUrl>',
                f'<description><![CDATA[{desc}]]></description>'
            ])
            lines.extend(self._pt_kml(geom))
            lines.append('</Placemark>')

        return lines
