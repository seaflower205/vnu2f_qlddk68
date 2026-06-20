# -*- coding: utf-8 -*-
"""Helper class for scanning layer codes and applying symbology safely."""

class ScannerApplier:
    @staticmethod
    def scan_layer_codes(layer, field_name: str) -> set[str]:
        """Scan active layer and return a set of unique normalized codes."""
        if not layer or not field_name:
            return set()
            
        code_idx = layer.fields().indexOf(field_name)
        if not isinstance(code_idx, int) or code_idx == -1:
            try:
                code_idx = int(layer.fields().indexFromName(field_name))
            except (TypeError, ValueError, AttributeError):
                code_idx = -1
        if code_idx == -1:
            return set()

        from qgis.core import QgsFeatureRequest

        request = QgsFeatureRequest()
        request.setFlags(QgsFeatureRequest.NoGeometry)
        request.setSubsetOfAttributes([code_idx])

        codes = set()
        for feature in layer.getFeatures(request):
            val = feature.attribute(code_idx)
            if val is not None and val != "":
                code = str(val).strip().upper()
                if code:
                    codes.add(code)
        return codes

    @staticmethod
    def apply_symbology(layer, field_name: str, configs: list[dict], scanned_codes: set[str]) -> tuple[int, int]:
        """Apply symbology for given configs that exist in scanned_codes.
        Returns:
            (applied_count, skipped_count)
        """
        from ...core import symbology_manager as sym_mgr
        
        filtered_configs = [cfg for cfg in configs if cfg["code"] in scanned_codes]
        
        if not filtered_configs:
            return 0, len(configs)

        sym_mgr.apply_to_layer(layer, field_name, filtered_configs)
        
        applied_count = len(filtered_configs)
        skipped_count = len(configs) - applied_count
        return applied_count, skipped_count

    @staticmethod
    def check_missing_codes(scanned_codes: set[str], configs: list[dict]) -> set[str]:
        """Return a set of scanned codes that are not present in configs."""
        configured = {cfg["code"] for cfg in configs}
        return {code for code in scanned_codes if code not in configured}
