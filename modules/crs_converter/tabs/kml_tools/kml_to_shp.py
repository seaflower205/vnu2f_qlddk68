from qgis.PyQt.QtCore import QVariant
import os
import re
from qgis.core import (
    QgsVectorLayer, QgsVectorFileWriter, QgsCoordinateReferenceSystem,
    QgsField, QgsFields, QgsFeature, QgsProject
)
from .kml_discovery_mixin import KmlDiscoveryMixin

class KmlToShpConverter(KmlDiscoveryMixin):
    def convert(self, kml_path, output_shp, target_crs_str='EPSG:4326',
                selected_fields=None):
        """
        Converts KML/KMZ to SHP.

        Strategy: Load KML, scan ALL features, group by geometry type,
        write separate SHPs per geometry type. This is GDAL-version
        independent and always works regardless of sub-layer format.
        """
        if not os.path.exists(kml_path):
            return False, "KML file not found"

        # 1. Load all features from KML (all sub-layers)
        all_features, all_fields, layer_wkb = self._load_all_features(kml_path)
        if all_features is None:
            return False, "Invalid KML file"
        if not all_features:
            return False, "No features found in KML"

        # 2. Setup Target CRS
        crs = QgsCoordinateReferenceSystem(target_crs_str)
        if not crs.isValid():
            crs = QgsCoordinateReferenceSystem('EPSG:4326')

        # 3. Group features by geometry type
        groups = {}  # geom_label -> [(feat, parsed_attrs)]
        for feat, parsed_attrs in all_features:
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            gt = geom.type()  # 0=Point, 1=Line, 2=Polygon
            if gt == 0:
                label = 'point'
            elif gt == 1:
                label = 'line'
            elif gt == 2:
                label = 'polygon'
            else:
                label = 'other'
            groups.setdefault(label, []).append((feat, parsed_attrs))

        if not groups:
            return False, "No valid geometries found (all empty)"

        # 4. Build output fields
        new_fields = self._build_fields(all_fields, all_features, selected_fields)

        # 5. Write each geometry group to separate SHP
        total_written = 0
        results = []
        for label, feat_list in groups.items():
            if len(groups) == 1:
                out_path = output_shp
            else:
                base, ext = os.path.splitext(output_shp)
                out_path = f"{base}_{label}{ext}"

            # Determine WKB type from first feature
            sample_geom = feat_list[0][0].geometry()
            wkb_type = sample_geom.wkbType()

            count = self._write_shp(out_path, new_fields, wkb_type, crs,
                                    feat_list, all_fields['original'])
            total_written += count
            results.append(f"{label}: {count}")

        summary = f"OK — {total_written} features"
        if len(groups) > 1:
            summary += f" ({', '.join(results)})"
        return True, summary


    def _get_layer_uris(self, kml_path):
        """Get all valid layer URIs from KML/KMZ.

        Uses QGIS sub-layer discovery, then falls back to geometry-type
        URIs if the KML contains mixed geometry types.
        """
        test = QgsVectorLayer(kml_path, "test", "ogr")
        if not test.isValid():
            return []

        sub_list = test.dataProvider().subLayers()
        del test

        if not sub_list:
            # Single-layer KML — try geometry-type split
            return self._try_geometry_split(kml_path)

        # Detect separator
        sample = sub_list[0]
        if '!!::!!' in sample:
            sep = '!!::!!'
        elif ':::' in sample:
            sep = ':::'
        else:
            sep = ':'

        uris = []
        for sl in sub_list:
            parts = sl.split(sep)
            if len(parts) < 2:
                continue

            layer_name = parts[1].strip()
            geom_type = parts[3].strip() if len(parts) > 3 else ''

            uri = f"{kml_path}|layername={layer_name}"
            if geom_type and geom_type.lower() not in ('unknown', 'none', ''):
                uri += f"|geometrytype={geom_type}"

            if uri not in uris:
                uris.append(uri)

        return uris if uris else self._try_geometry_split(kml_path)

    def _try_geometry_split(self, kml_path):
        """Try loading KML with explicit geometry type filters."""
        uris = []
        for gt in ('Point', 'LineString', 'Polygon',
                   'MultiPoint', 'MultiLineString', 'MultiPolygon'):
            uri = f"{kml_path}|geometrytype={gt}"
            test = QgsVectorLayer(uri, "test", "ogr")
            if test.isValid() and test.featureCount() > 0:
                uris.append(uri)
            del test

        if not uris:
            # Ultimate fallback: raw path
            uris = [kml_path]
        return uris

    def _build_fields(self, field_info, all_features, selected_fields):
        """Build the output QgsFields based on scanned data."""
        new_fields = QgsFields()
        original_fields = field_info['original']

        # Fields to strip (OGR noise)
        remove_lower = [
            'description', 'timestamp', 'begin', 'end',
            'altitudemode', 'tessellate', 'extrude',
            'visibility', 'draworder', 'icon']

        for f in original_fields:
            if f.name().lower() not in remove_lower:
                new_fields.append(f)

        # Add Desc field for plain-text descriptions
        if field_info['has_plain']:
            if 'Desc' not in [f.name() for f in new_fields]:
                new_fields.append(QgsField('Desc', QVariant.String, len=254))

        # Add HTML-parsed fields
        for fname in field_info['html_fields']:
            if fname.lower() not in [f.name().lower() for f in new_fields]:
                new_fields.append(QgsField(fname, QVariant.String, len=254))

        # Filter by selected_fields
        if selected_fields is not None:
            sel_lower = [s.lower() for s in selected_fields]
            filtered = QgsFields()
            for i in range(new_fields.count()):
                f = new_fields.at(i)
                if f.name().lower() in sel_lower:
                    filtered.append(f)
            new_fields = filtered

        return new_fields

    def _write_shp(self, output_path, fields, wkb_type, crs,
                   feat_list, original_fields):
        """Write a list of features to a Shapefile."""
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"

        writer = QgsVectorFileWriter.create(
            output_path, fields, wkb_type, crs,
            QgsProject.instance().transformContext(), options)

        if writer.hasError():
            del writer
            return 0

        remove_lower = [
            'description', 'timestamp', 'begin', 'end',
            'altitudemode', 'tessellate', 'extrude',
            'visibility', 'draworder', 'icon']

        written = 0
        for feat, parsed_attrs in feat_list:
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue

            new_feat = QgsFeature(fields)
            new_feat.setGeometry(geom)

            # Copy original attributes
            for i in range(original_fields.count()):
                fname = original_fields.at(i).name()
                if fname.lower() not in remove_lower:
                    idx = fields.indexFromName(fname)
                    if idx != -1:
                        try:
                            new_feat.setAttribute(idx, feat.attributes()[i])
                        except (IndexError, KeyError):
                            pass

            # Set parsed description attributes
            for key, val in parsed_attrs.items():
                idx = fields.indexFromName(key)
                if idx != -1:
                    new_feat.setAttribute(idx, val)

            writer.addFeature(new_feat)
            written += 1

        del writer
        return written

    # ------------------------------------------------------------------
    # Utilities (public — used by dialog._scan_kml_fields)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_description(feat):
        """Safely get description from a feature."""
        field_names = feat.fields().names()
        for name in ['description', 'Description']:
            if name in field_names:
                val = feat[name]
                if val and str(val).strip():
                    return str(val).strip()
        return ""

    @staticmethod
    def _clean_field_name(name):
        """Clean field name for SHP compatibility (max 10 chars)."""
        clean = re.sub(r'<.*?>', '', name).strip()
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', clean)
        return clean[:10] if clean else ""
