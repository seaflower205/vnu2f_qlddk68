"""Mechanically extracted responsibilities from kml_to_shp.py."""

from qgis.PyQt.QtCore import QVariant
import os
import re
from qgis.core import (
    QgsVectorLayer, QgsVectorFileWriter, QgsCoordinateReferenceSystem,
    QgsField, QgsFields, QgsFeature, QgsProject
)


class KmlDiscoveryMixin:
    def _load_all_features(self, kml_path):
        """Load all features from all sub-layers in a KML/KMZ.

        Returns (feature_list, field_info, wkb_type) or (None, None, None).
        feature_list = [(QgsFeature, parsed_desc_dict), ...]
        field_info = {'original': QgsFields, 'html_fields': set, 'has_plain': bool}
        """
        # Try to discover sub-layers via OGR
        uris = self._get_layer_uris(kml_path)

        all_feats = []
        original_fields = None
        html_fields = set()
        has_plain_desc = False
        has_html_table = False
        wkb_type = None

        for uri in uris:
            layer = QgsVectorLayer(uri, "kml_temp", "ogr")
            if not layer.isValid():
                continue

            if original_fields is None:
                original_fields = layer.fields()
                wkb_type = layer.wkbType()

            for feat in layer.getFeatures():
                # Parse description
                desc = self._get_description(feat)
                parsed = {}

                if desc:
                    html_matches = re.findall(
                        r'<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>',
                        desc, re.IGNORECASE | re.DOTALL)

                    if html_matches:
                        has_html_table = True
                        for key, val in html_matches:
                            clean_key = self._clean_field_name(key)
                            if clean_key and clean_key.lower() not in [
                                    'th_ng_tin', 'field', 'attribute']:
                                clean_val = re.sub(r'<.*?>', '', val).strip()
                                parsed[clean_key] = clean_val
                                html_fields.add(clean_key)
                    else:
                        has_plain_desc = True
                        clean_desc = re.sub(r'<.*?>', '', desc).strip()
                        parsed['Desc'] = clean_desc[:254]

                all_feats.append((feat, parsed))

            del layer

        if original_fields is None:
            return None, None, None

        field_info = {
            'original': original_fields,
            'html_fields': html_fields,
            'has_plain': has_plain_desc and not has_html_table,
        }
        return all_feats, field_info, wkb_type
    def discover_fields(self, kml_path):
        """Public method for dialog to scan fields and metadata.

        Returns dict: {
            'fields': {field_name: sample_value, ...},
            'total_features': int,
            'geom_types': set of labels,
            'sub_layer_count': int,
        }
        """
        uris = self._get_layer_uris(kml_path)
        if not uris:
            return None

        all_fields = {}
        total = 0
        geom_types = set()

        remove_lower = [
            'description', 'timestamp', 'begin', 'end',
            'altitudemode', 'tessellate', 'extrude',
            'visibility', 'draworder', 'icon']

        for uri in uris:
            layer = QgsVectorLayer(uri, "scan", "ogr")
            if not layer.isValid():
                continue
            total += layer.featureCount()

            # Detect geometry type from URI or features
            if '|geometrytype=' in uri:
                gt = uri.split('|geometrytype=')[-1].lower()
                if 'point' in gt:
                    geom_types.add('point')
                elif 'line' in gt:
                    geom_types.add('line')
                elif 'polygon' in gt:
                    geom_types.add('polygon')

            # Collect OGR fields
            for f in layer.fields():
                if f.name().lower() not in remove_lower:
                    if f.name() not in all_fields:
                        all_fields[f.name()] = ""

            # Sample values + scan descriptions
            sampled = 0
            for feat in layer.getFeatures():
                # Detect geom type from actual features
                geom = feat.geometry()
                if geom and not geom.isEmpty():
                    gt = geom.type()
                    if gt == 0:
                        geom_types.add('point')
                    elif gt == 1:
                        geom_types.add('line')
                    elif gt == 2:
                        geom_types.add('polygon')

                # Sample OGR field values
                for fname in list(all_fields.keys()):
                    if not all_fields[fname]:
                        try:
                            val = feat[fname]
                            if val is not None and str(val).strip():
                                all_fields[fname] = str(val)[:50]
                        except Exception:  # noqa: BLE001 — intentional suppress
                            pass

                desc = self._get_description(feat)
                if desc:
                    html_matches = re.findall(
                        r'<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>',
                        desc, re.IGNORECASE | re.DOTALL)
                    if html_matches:
                        for key, val in html_matches:
                            ck = self._clean_field_name(key)
                            if ck and ck not in all_fields:
                                cv = re.sub(r'<.*?>', '', val).strip()
                                all_fields[ck] = cv[:50]
                    else:
                        if 'Desc' not in all_fields:
                            clean = re.sub(r'<.*?>', '', desc).strip()
                            all_fields['Desc'] = clean[:50]

                sampled += 1
                if sampled >= 20:
                    break

            del layer

        return {
            'fields': all_fields,
            'total_features': total,
            'geom_types': geom_types,
            'sub_layer_count': len(uris),
        }
