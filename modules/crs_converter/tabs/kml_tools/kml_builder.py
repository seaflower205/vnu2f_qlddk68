"""KML/KMZ builder engine with configurable label size."""

import zipfile

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsWkbTypes,
)

from .color_utils import hex_to_kml_color
from .html_template import HtmlTemplateBuilder


WKB_POINT_GEOMETRY = QgsWkbTypes.PointGeometry
WKB_LINE_GEOMETRY = QgsWkbTypes.LineGeometry
WKB_POLYGON_GEOMETRY = QgsWkbTypes.PolygonGeometry


class KmlBuilder:
    def __init__(self, config):
        self.config = config
        self.html_builder = HtmlTemplateBuilder(config)

    def build(self, layer, output_path, output_format='kml'):
        try:
            target_crs = QgsCoordinateReferenceSystem('EPSG:4326')
            source_crs = layer.crs()
            transform = None
            if source_crs != target_crs:
                transform = QgsCoordinateTransform(
                    source_crs, target_crs, QgsProject.instance())
            kml_content = self._build_kml_document(layer, transform)
            if output_format == 'kmz':
                return self._write_kmz(kml_content, output_path)
            return self._write_kml(kml_content, output_path)
        except Exception as e:  # noqa: BLE001 — intentional suppress
            return False, f"Error: {str(e)}"

    def _build_kml_document(self, layer, transform):
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<kml xmlns="http://www.opengis.net/kml/2.2">',
                 '<Document>',
                 f'<name>{self._esc(layer.name())}</name>']
        lines.extend(self._build_styles())
        name_cfg = self.config.get('name_fields', {})
        cond_cfg = self.config.get('conditional_colors', {})
        for feat in layer.getFeatures():
            pm = self._build_placemark(feat, name_cfg, cond_cfg, transform)
            if pm:
                lines.extend(pm)
        lines.extend(['</Document>', '</kml>'])
        return '\n'.join(lines)

    def _build_styles(self):
        lines = []
        poly = self.config.get('polygon_style', {})
        border_kml = hex_to_kml_color(poly.get('border_color', '#FF0000'), 100)
        fill_kml = hex_to_kml_color(
            poly.get(
                'fill_color', '#00FF00'), poly.get(
                'fill_opacity', 50))
        bw = poly.get('border_width', 2)
        name_cfg = self.config.get('name_fields', {})
        name_size = name_cfg.get('font_size', 12)
        label_scale = round(max(0.5, name_size / 12.0), 1)
        name_color = hex_to_kml_color(
            name_cfg.get('font_color', '#FFFFFF'), 100)

        lines.append('<Style id="style_default">')
        lines.append('<IconStyle><scale>0</scale></IconStyle>')
        lines.append(
            f'<LabelStyle><color>{name_color}</color><scale>{label_scale}</scale></LabelStyle>')
        lines.append(
            f'<LineStyle><color>{border_kml}</color><width>{bw}</width></LineStyle>')
        lines.append(f'<PolyStyle><color>{fill_kml}</color></PolyStyle>')
        lines.append('</Style>')

        cond = self.config.get('conditional_colors', {})
        if cond.get('enabled', False):
            for i, rule in enumerate(cond.get('rules', [])):
                rb = hex_to_kml_color(rule.get('border_color', '#FF0000'), 100)
                rf = hex_to_kml_color(
                    rule.get(
                        'fill_color', '#FF0000'), poly.get(
                        'fill_opacity', 50))
                lines.append(f'<Style id="style_rule_{i}">')
                lines.append('<IconStyle><scale>0</scale></IconStyle>')
                lines.append(
                    f'<LabelStyle><color>{name_color}</color><scale>{label_scale}</scale></LabelStyle>')
                lines.append(
                    f'<LineStyle><color>{rb}</color><width>{bw}</width></LineStyle>')
                lines.append(f'<PolyStyle><color>{rf}</color></PolyStyle>')
                lines.append('</Style>')
        return lines

    def _build_placemark(self, feat, name_cfg, cond_cfg, transform):
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            return []
        if transform:
            geom.transform(transform)
        name = self._build_name(feat, name_cfg)
        fdata = {f.name(): feat[f.name()] for f in feat.fields()}
        desc = self.html_builder.build(fdata)
        sid = self._determine_style(feat, cond_cfg)

        lines = []
        gt = QgsWkbTypes.geometryType(geom.wkbType())

        if gt == WKB_POLYGON_GEOMETRY:
            # Placemark 1: Polygon without name
            lines.extend(['<Placemark>', '<name></name>',
                          f'<styleUrl>#{sid}</styleUrl>',
                          f'<description><![CDATA[{desc}]]></description>'])
            lines.extend(self._poly_kml_geom_only(geom))
            lines.append('</Placemark>')

            # Placemark 2: Point with Name and Region
            centroid = geom.pointOnSurface() if hasattr(
                geom, 'pointOnSurface') else geom.centroid()
            if centroid and centroid.asPoint():
                pt = centroid.asPoint()
                north, south = pt.y() + 0.0002, pt.y() - 0.0002
                east, west = pt.x() + 0.0002, pt.x() - 0.0002
                lines.extend(['<Placemark>',
                              f'<name>{self._esc(name)}</name>',
                              f'<styleUrl>#{sid}</styleUrl>',
                              f'<description><![CDATA[{desc}]]></description>'])
                lines.extend([
                    '<Region><LatLonAltBox>',
                    f'<north>{north}</north><south>{south}</south>',
                    f'<east>{east}</east><west>{west}</west>',
                    '</LatLonAltBox><Lod><minLodPixels>16</minLodPixels><maxLodPixels>-1</maxLodPixels></Lod></Region>'
                ])
                lines.append(
                    f'<Point><coordinates>{pt.x()},{pt.y()},0</coordinates></Point>')
                lines.append('</Placemark>')
        elif gt == WKB_LINE_GEOMETRY:
            lines.extend(['<Placemark>',
                          f'<name>{self._esc(name)}</name>',
                          f'<styleUrl>#{sid}</styleUrl>',
                          f'<description><![CDATA[{desc}]]></description>'])
            lines.extend(self._line_kml(geom))
            lines.append('</Placemark>')
        elif gt == WKB_POINT_GEOMETRY:
            lines.extend(['<Placemark>',
                          f'<name>{self._esc(name)}</name>',
                          f'<styleUrl>#{sid}</styleUrl>',
                          f'<description><![CDATA[{desc}]]></description>'])
            lines.extend(self._pt_kml(geom))
            lines.append('</Placemark>')

        return lines

    def _build_name(self, feat, cfg):
        f1, f2 = cfg.get('field1', ''), cfg.get('field2', '')
        f1_on = cfg.get('field1_enabled', True)
        f2_on = cfg.get('field2_enabled', True)
        sep = cfg.get('separator', ' - ')
        fnames = [f.name() for f in feat.fields()]
        v1 = str(feat[f1]) if f1_on and f1 in fnames and feat[f1] is not None else ''
        v2 = str(feat[f2]) if f2_on and f2 in fnames and feat[f2] is not None else ''
        if v1 and v2:
            return f"{v1}{sep}{v2}"
        return v1 or v2 or 'Unnamed'

    def _determine_style(self, feat, cond_cfg):
        if not cond_cfg.get('enabled', False):
            return 'style_default'
        field = cond_cfg.get('field', '')
        if not field:
            return 'style_default'
        fnames = [f.name() for f in feat.fields()]
        val = feat[field] if field in fnames else None
        for i, rule in enumerate(cond_cfg.get('rules', [])):
            if HtmlTemplateBuilder._evaluate_condition(
                    val, rule.get('operator', '='), rule.get('value', '')):
                return f'style_rule_{i}'
        return 'style_default'

    def _poly_kml_geom_only(self, geom):
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
        lines = ['<Polygon>', '<outerBoundaryIs><LinearRing><coordinates>']
        lines.append(' '.join(f'{p.x()},{p.y()},0' for p in rings[0]))
        lines.append('</coordinates></LinearRing></outerBoundaryIs>')
        for i in range(1, len(rings)):
            lines.append('<innerBoundaryIs><LinearRing><coordinates>')
            lines.append(' '.join(f'{p.x()},{p.y()},0' for p in rings[i]))
            lines.append('</coordinates></LinearRing></innerBoundaryIs>')
        lines.append('</Polygon>')
        return lines

    def _line_kml(self, geom):
        lines = []
        if geom.isMultipart():
            lines.append('<MultiGeometry>')
            for part in geom.asMultiPolyline():
                lines.append('<LineString><coordinates>')
                lines.append(' '.join(f'{p.x()},{p.y()},0' for p in part))
                lines.append('</coordinates></LineString>')
            lines.append('</MultiGeometry>')
        else:
            pl = geom.asPolyline()
            if pl:
                lines.append('<LineString><coordinates>')
                lines.append(' '.join(f'{p.x()},{p.y()},0' for p in pl))
                lines.append('</coordinates></LineString>')
        return lines

    def _pt_kml(self, geom):
        lines = []
        if geom.isMultipart():
            lines.append('<MultiGeometry>')
            for pt in geom.asMultiPoint():
                lines.append(
                    f'<Point><coordinates>{pt.x()},{pt.y()},0</coordinates></Point>')
            lines.append('</MultiGeometry>')
        else:
            pt = geom.asPoint()
            lines.append(
                f'<Point><coordinates>{pt.x()},{pt.y()},0</coordinates></Point>')
        return lines

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
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
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
