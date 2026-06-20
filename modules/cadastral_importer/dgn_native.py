"""Mechanically extracted functions from dgn_reader.py."""
from __future__ import annotations
import json
import os
import struct
import sys
import zlib
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsFeature, QgsField, QgsFields, QgsGeometry, QgsPointXY, QgsProject,
    QgsVectorLayer,
)
from ..common.common_utils import log_warning
from ..crs_converter.font_utils import convert_tcvn3_to_unicode
from .dgn_loader import _load_dgn_json_into_layers
from .layer_runtime import add_generated_layer, remove_previous_generated_layers
from .cad_models import CadImportIssue, CadImportResult

def import_dgn_v8_native(cad_path: str, crs_authid: str, project=None) -> 'CadImportResult':  # noqa: F821
    """Import DGN V8 natively using bundled olefile and zlib decompression."""
    from .cad_ogr import _make_output_fields, _create_output_layer
    from .texts import cadastral_text as tx

    # 1. Add vendor to sys.path to load olefile
    vendor_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "vendor"))
    if vendor_dir not in sys.path:
        sys.path.insert(0, vendor_dir)
    
    try:
        import olefile
    except ImportError as err:
        result = CadImportResult(cad_path=cad_path, cad_format="DGN", crs_authid=crs_authid)
        result.issues.append(
            CadImportIssue("error", f"Không tìm thấy thư viện olefile trong thư mục vendor: {str(err)}")
        )
        return result

    result = CadImportResult(cad_path=cad_path, cad_format="DGN", crs_authid=crs_authid)
    project = project or QgsProject.instance()
    base_name = os.path.splitext(os.path.basename(cad_path))[0]

    # Remove previous layers
    remove_previous_generated_layers(
        project,
        cad_path,
        ("cad_raw_point", "cad_raw_line", "cad_raw_polygon"),
        (
            "cad_raw_point",
            "cad_raw_line",
            "cad_raw_polygon",
            f"cad_raw_point_{base_name}",
            f"cad_raw_line_{base_name}",
            f"cad_raw_polygon_{base_name}",
        ),
    )

    if not os.path.exists(cad_path):
        result.issues.append(CadImportIssue("error", tx("cad.error.file_missing"), cad_path))
        return result

    from ..common.bin_utils import get_cad_reader_path

    # Try calling Rust CLI first
    exe_path = get_cad_reader_path()
    
    if exe_path:
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "dgn_out.json")
            try:
                env = os.environ.copy()
                gcc_bin = os.environ.get("GCC_BIN_DIR", "")
                if gcc_bin and os.path.exists(gcc_bin):
                    env["PATH"] = gcc_bin + os.pathsep + env.get("PATH", "")
                
                cmd = [exe_path, "dgn-parse", cad_path, json_path]
                subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
                
                with open(json_path, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                
                return _load_dgn_json_into_layers(doc, cad_path, crs_authid, project, result)
            except Exception as err:
                log_warning(f"Lỗi chạy Rust DGN parser: {str(err)}. Tự động fallback sang Python native parser.")

    try:
        # Open OLE container
        ole = olefile.OleFileIO(cad_path)
    except Exception as e:  # noqa: BLE001 — intentional suppress
        result.issues.append(CadImportIssue("error", f"Không thể mở file DGN dạng OLE: {str(e)}"))
        return result

    # 2. Find and read Model Header to load coordinate translation/scale parameters
    scale = 1000.0
    go_x = -500000000.0
    go_y = -1000000000.0

    stream_paths = ole.listdir()
    mh_stream_path = None
    for path in stream_paths:
        stream_name = "_".join(path)
        if stream_name.startswith("Dgn-Md_#") and stream_name.endswith("_Dgn~Mh"):
            mh_stream_path = path
            break

    if mh_stream_path:
        try:
            raw_mh = ole.openstream(mh_stream_path).read()
            decompressed_mh = None
            for offset in range(0, min(64, len(raw_mh) - 2)):
                if raw_mh[offset] == 0x78 and raw_mh[offset+1] in (0x01, 0x5E, 0x9C, 0xDA):
                    decompressed_mh = zlib.decompress(raw_mh[offset:])
                    break
            if decompressed_mh is None:
                decompressed_mh = raw_mh
            
            if len(decompressed_mh) >= 4236:
                d_scale = struct.unpack("<d", decompressed_mh[4196:4204])[0]
                if d_scale > 0.0:
                    scale = d_scale
                go_x = struct.unpack("<d", decompressed_mh[4212:4220])[0]
                go_y = struct.unpack("<d", decompressed_mh[4220:4228])[0]
        except Exception as e:  # noqa: BLE001 — intentional suppress
            result.issues.append(CadImportIssue("warning", f"Không thể đọc thông số Model Header: {str(e)}. Sử dụng thông số mặc định."))

    # 3. Find all Graphic streams (containing geometry elements)
    g_stream_paths = []
    for path in stream_paths:
        stream_name = "_".join(path)
        if stream_name.startswith("Dgn-Md_#") and "_Dgn^G_" in stream_name:
            g_stream_paths.append(path)

    output_fields = _make_output_fields(QgsFields, QgsField, QVariant)
    outputs = {}
    pending_features = {}
    counts = {"point": 0, "line": 0, "polygon": 0}
    feature_index = 0

    for path in g_stream_paths:
        stream_name = "_".join(path)
        try:
            raw_g = ole.openstream(path).read()
            decompressed_g = None
            for offset in range(0, min(64, len(raw_g) - 2)):
                if raw_g[offset] == 0x78 and raw_g[offset+1] in (0x01, 0x5E, 0x9C, 0xDA):
                    decompressed_g = zlib.decompress(raw_g[offset:])
                    break
            if decompressed_g is None:
                decompressed_g = raw_g

            total_size = len(decompressed_g)
            offset = 4  # Skip the 4-byte zero prefix
            
            while offset < total_size:
                if offset + 8 > total_size:
                    break
                
                type_flags = struct.unpack("<I", decompressed_g[offset:offset+4])[0]
                el_type = type_flags & 0xFF
                length_words = struct.unpack("<I", decompressed_g[offset+4:offset+8])[0]
                el_size = 4 + length_words * 2
                
                if el_size < 8:
                    offset += 4
                    continue
                    
                if offset + el_size > total_size:
                    break
                    
                el_data = decompressed_g[offset : offset + el_size]
                
                level_id = 0
                element_id = 0
                if len(el_data) >= 20:
                    level_id = struct.unpack("<I", el_data[12:16])[0]
                    element_id = struct.unpack("<I", el_data[16:20])[0]

                qgs_geom = None
                target_key = None
                text_val = None
                ent_type_str = f"TYPE_{el_type}"

                if el_type == 17:  # Text element
                    if len(el_data) >= 168:
                        dgn_x = struct.unpack("<d", el_data[152:160])[0]
                        dgn_y = struct.unpack("<d", el_data[160:168])[0]
                        x_real = (dgn_x - go_x) / scale
                        y_real = (dgn_y - go_y) / scale
                        qgs_geom = QgsGeometry.fromPointXY(QgsPointXY(x_real, y_real))
                        target_key = "point"
                        ent_type_str = "TEXT"
                        
                    # Extract text content
                    text_len = struct.unpack("<I", el_data[110:114])[0]
                    if len(el_data) >= 170 + text_len:
                        text_bytes = el_data[170 : 170 + text_len]
                        raw_text = text_bytes.decode('ansi', errors='ignore').strip()
                        text_val = convert_tcvn3_to_unicode(raw_text)

                elif el_type == 3:  # Line
                    if len(el_data) >= 136:
                        x1 = struct.unpack("<d", el_data[104:112])[0]
                        y1 = struct.unpack("<d", el_data[112:120])[0]
                        x2 = struct.unpack("<d", el_data[120:128])[0]
                        y2 = struct.unpack("<d", el_data[128:136])[0]
                        
                        x1_real = (x1 - go_x) / scale
                        y1_real = (y1 - go_y) / scale
                        x2_real = (x2 - go_x) / scale
                        y2_real = (y2 - go_y) / scale
                        
                        qgs_geom = QgsGeometry.fromPolylineXY([
                            QgsPointXY(x1_real, y1_real),
                            QgsPointXY(x2_real, y2_real)
                        ])
                        target_key = "line"
                        ent_type_str = "LINE"

                elif el_type == 4:  # LineString
                    if len(el_data) >= 108:
                        v_count = struct.unpack("<I", el_data[104:108])[0]
                        if v_count > 0 and len(el_data) >= 112 + v_count * 16:
                            pts = []
                            for i in range(v_count):
                                x = struct.unpack("<d", el_data[112 + i*16 : 112 + i*16 + 8])[0]
                                y = struct.unpack("<d", el_data[112 + i*16 + 8 : 112 + i*16 + 16])[0]
                                pts.append(QgsPointXY((x - go_x) / scale, (y - go_y) / scale))
                            qgs_geom = QgsGeometry.fromPolylineXY(pts)
                            target_key = "line"
                            ent_type_str = "LINESTRING"

                elif el_type == 6:  # Shape (Polygon)
                    if len(el_data) >= 108:
                        v_count = struct.unpack("<I", el_data[104:108])[0]
                        if v_count > 0 and len(el_data) >= 112 + v_count * 16:
                            pts = []
                            for i in range(v_count):
                                x = struct.unpack("<d", el_data[112 + i*16 : 112 + i*16 + 8])[0]
                                y = struct.unpack("<d", el_data[112 + i*16 + 8 : 112 + i*16 + 16])[0]
                                pts.append(QgsPointXY((x - go_x) / scale, (y - go_y) / scale))
                            if pts and pts[0] != pts[-1]:
                                pts.append(pts[0])
                            qgs_geom = QgsGeometry.fromPolygonXY([pts])
                            target_key = "polygon"
                            ent_type_str = "SHAPE"

                if qgs_geom and target_key:
                    target_layer = outputs.get(target_key)
                    if target_layer is None:
                        target_layer = _create_output_layer(
                            target_key,
                            crs_authid,
                            output_fields,
                            QgsVectorLayer,
                            cad_path,
                        )
                        outputs[target_key] = target_layer
                        pending_features[target_key] = []
                        
                    output_feature = QgsFeature(target_layer.fields())
                    output_feature.setGeometry(qgs_geom)
                    output_feature.setAttributes([
                        os.path.basename(cad_path),
                        cad_path,
                        "DGN",
                        f"Level {level_id}", # source_layer
                        feature_index,       # source_fid
                        f"Level {level_id}", # cad_level
                        text_val,            # cad_text
                        "7",                 # cad_color
                        "Continuous",        # cad_linetype
                        f"handle_{element_id}", # cad_handle
                        ent_type_str,        # cad_entity
                        json.dumps({"type": el_type, "level": level_id, "id": element_id, "stream": stream_name}),
                    ])
                    pending_features[target_key].append(output_feature)
                    counts[target_key] += 1
                    feature_index += 1
                    
                offset += el_size
        except Exception as e:  # noqa: BLE001 — intentional suppress
            result.issues.append(CadImportIssue("warning", f"Lỗi đọc stream {stream_name}: {str(e)}"))

    ole.close()

    # 4. Save features to memory layers and add to QGIS project
    for key, layer in outputs.items():
        if counts[key] <= 0:
            continue
        layer.dataProvider().addFeatures(pending_features.get(key, []))
        add_generated_layer(project, layer, cad_path, f"cad_raw_{key}", counts[key])
        result.output_layer_names.append(layer.name())

    result.feature_counts = counts
    if not result.output_layer_names:
        result.issues.append(CadImportIssue("warning", tx("cad.warning.no_output_geometry")))
        
    return result
