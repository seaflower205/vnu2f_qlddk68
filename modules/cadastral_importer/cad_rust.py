# -*- coding: utf-8 -*-
"""Rust CAD reader adapter."""
from __future__ import annotations
import json
import math
import os
import subprocess
import tempfile

from .cad_blocks import flatten_entities
from .cad_models import CadImportIssue, CadImportResult
from .layer_runtime import add_generated_layer, remove_previous_generated_layers
from .texts import cadastral_text as tx
from .cad_ogr import _create_output_layer, _make_output_fields

def _import_cad_via_rust_engine(
    cad_path: str,
    crs_authid: str,
    project=None,
    original_cad_path: str | None = None,
    add_to_project: bool = True,
    is_canceled_cb=None
) -> CadImportResult:
    """Load DWG/DXF files using our compiled Rust binary for 100% precision."""
    from qgis.PyQt.QtCore import QVariant
    from qgis.core import (
        QgsFeature,
        QgsField,
        QgsFields,
        QgsGeometry,
        QgsProject,
        QgsVectorLayer,
        QgsPointXY,
    )
    from ..crs_converter.font_utils import convert_tcvn3_to_unicode
    from ..common.bin_utils import get_cad_reader_path
    exe_path = get_cad_reader_path()
    display_path = original_cad_path or cad_path
    extension = os.path.splitext(display_path)[1].lower()
    result = CadImportResult(
        cad_path=display_path,
        cad_format=extension.lstrip(".").upper(),
        crs_authid=crs_authid,
    )
    if not exe_path:
        result.issues.append(
            CadImportIssue("error", "Không tìm thấy file thực thi bộ phân tích CAD.")
        )
        return result
    if not os.path.exists(cad_path):
        result.issues.append(CadImportIssue("error", tx("cad.error.file_missing"), cad_path))
        return result
    project = project or QgsProject.instance()
    base_name = os.path.splitext(os.path.basename(display_path))[0]
    remove_previous_generated_layers(
        project,
        display_path,
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
    def has_non_ascii(s: str) -> bool:
        try:
            s.encode("ascii")
            return False
        except UnicodeEncodeError:
            return True
    temp_cad_path = None
    work_cad_path = cad_path
    if has_non_ascii(cad_path):
        import shutil
        import uuid
        try:
            temp_cad_name = f"vnu2f_{uuid.uuid4().hex}{extension}"
            temp_cad_path = os.path.join(tempfile.gettempdir(), temp_cad_name)
            shutil.copy2(cad_path, temp_cad_path)
            work_cad_path = temp_cad_path
        except Exception as err:  # noqa: BLE001 — intentional suppress
            result.issues.append(
                CadImportIssue("warning", f"Lỗi tạo tệp tạm cho đường dẫn tiếng Việt: {str(err)}. Thử dùng tệp gốc.")
            )
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "cad_out.json")
            try:
                env = os.environ.copy()
                gcc_bin = os.environ.get("GCC_BIN_DIR", "")
                if gcc_bin and os.path.exists(gcc_bin):
                    env["PATH"] = gcc_bin + os.pathsep + env.get("PATH", "")
                cmd = [exe_path, work_cad_path, json_path]
                subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
                with open(json_path, "r", encoding="utf-8") as f:
                    doc = json.load(f)
            except subprocess.CalledProcessError as err:
                result.issues.append(
                    CadImportIssue("error", f"Lỗi chạy bộ phân tích CAD: {err.stderr or err.stdout}")
                )
                return result
            except Exception as err:  # noqa: BLE001 — intentional suppress
                result.issues.append(
                    CadImportIssue("error", f"Lỗi xử lý kết quả JSON từ parser: {str(err)}")
                )
                return result
    finally:
        if temp_cad_path and os.path.exists(temp_cad_path):
            try:
                os.remove(temp_cad_path)
            except OSError:
                pass
    layers_info = doc.get("layers", {}).get("entries", {})
    def get_color_index(common: dict) -> int:
        col = common.get("color")
        if isinstance(col, dict) and "Index" in col:
            return col["Index"]
        elif isinstance(col, str) and col.lower() == "bylayer":
            layer_name = common.get("layer")
            layer_name_upper = layer_name.upper() if layer_name else ""
            layer_ent = layers_info.get(layer_name_upper)
            if layer_ent and "color" in layer_ent:
                l_col = layer_ent["color"]
                if isinstance(l_col, dict) and "Index" in l_col:
                    return l_col["Index"]
        return 7
    def get_linetype(common: dict) -> str:
        lt = common.get("linetype")
        if lt and lt.lower() not in ("bylayer", "byblock"):
            return lt
        layer_name = common.get("layer")
        layer_name_upper = layer_name.upper() if layer_name else ""
        layer_ent = layers_info.get(layer_name_upper)
        if layer_ent and "line_type" in layer_ent:
            return layer_ent["line_type"]
        return "Continuous"
    output_fields = _make_output_fields(QgsFields, QgsField, QVariant)
    outputs = {}
    pending_features = {}
    counts = {"point": 0, "line": 0, "polygon": 0}
    all_entities = list(flatten_entities(doc))
    for idx, ent_wrapper in enumerate(all_entities):
        if is_canceled_cb and is_canceled_cb():
            result.issues.append(CadImportIssue("warning", "Tác vụ bị hủy bởi người dùng."))
            break
        ent_type = list(ent_wrapper.keys())[0]
        ent = ent_wrapper[ent_type]
        common = ent.get("common", {})
        qgs_geom = None
        target_key = None
        if ent_type == "Line":
            start = ent["start"]
            end = ent["end"]
            qgs_geom = QgsGeometry.fromPolylineXY([
                QgsPointXY(start["x"], start["y"]),
                QgsPointXY(end["x"], end["y"])
            ])
            target_key = "line"
        elif ent_type == "LwPolyline":
            vertices = ent.get("vertices", [])
            if not vertices:
                continue
            pts = [QgsPointXY(v["location"]["x"], v["location"]["y"]) for v in vertices]
            if ent.get("is_closed") and len(pts) > 2:
                pts.append(pts[0])
                qgs_geom = QgsGeometry.fromPolygonXY([pts])
                target_key = "polygon"
            else:
                qgs_geom = QgsGeometry.fromPolylineXY(pts)
                target_key = "line"
        elif ent_type == "Circle":
            center = ent["center"]
            radius = ent["radius"]
            pts = []
            for i in range(65):
                angle = i * 2 * math.pi / 64
                pts.append(QgsPointXY(
                    center["x"] + radius * math.cos(angle),
                    center["y"] + radius * math.sin(angle)
                ))
            qgs_geom = QgsGeometry.fromPolygonXY([pts])
            target_key = "polygon"
        elif ent_type == "Arc":
            center = ent["center"]
            radius = ent["radius"]
            start_angle = ent.get("start_angle", 0.0)
            end_angle = ent.get("end_angle", 360.0)
            pts = []
            theta_start = math.radians(start_angle)
            theta_end = math.radians(end_angle)
            if theta_end < theta_start:
                theta_end += 2 * math.pi
            steps = 32
            for i in range(steps + 1):
                theta = theta_start + i * (theta_end - theta_start) / steps
                pts.append(QgsPointXY(
                    center["x"] + radius * math.cos(theta),
                    center["y"] + radius * math.sin(theta)
                ))
            qgs_geom = QgsGeometry.fromPolylineXY(pts)
            target_key = "line"
        elif ent_type == "Ellipse":
            center = ent["center"]
            major_axis = ent["major_axis"]
            minor_ratio = ent["minor_axis_ratio"]
            start_param = ent.get("start_parameter", 0.0)
            end_param = ent.get("end_parameter", 2 * math.pi)
            a = math.sqrt(major_axis["x"]**2 + major_axis["y"]**2)
            if a == 0:
                continue
            ux = major_axis["x"] / a
            uy = major_axis["y"] / a
            wx = -uy
            wy = ux
            b = a * minor_ratio
            pts = []
            steps = 64
            for i in range(steps + 1):
                t = start_param + i * (end_param - start_param) / steps
                x = center["x"] + a * math.cos(t) * ux + b * math.sin(t) * wx
                y = center["y"] + a * math.cos(t) * uy + b * math.sin(t) * wy
                pts.append(QgsPointXY(x, y))
            if abs(end_param - start_param - 2 * math.pi) < 0.01:
                qgs_geom = QgsGeometry.fromPolygonXY([pts])
                target_key = "polygon"
            else:
                qgs_geom = QgsGeometry.fromPolylineXY(pts)
                target_key = "line"
        elif ent_type == "Point":
            loc = ent["location"]
            qgs_geom = QgsGeometry.fromPointXY(QgsPointXY(loc["x"], loc["y"]))
            target_key = "point"
        elif ent_type in ("Text", "MText"):
            loc = ent["insertion_point"]
            qgs_geom = QgsGeometry.fromPointXY(QgsPointXY(loc["x"], loc["y"]))
            target_key = "point"
        if qgs_geom is None or target_key is None:
            continue
        target_layer = outputs.get(target_key)
        if target_layer is None:
            target_layer = _create_output_layer(
                target_key,
                crs_authid,
                output_fields,
                QgsVectorLayer,
                display_path,
            )
            outputs[target_key] = target_layer
            pending_features[target_key] = []
        raw_text = ent.get("value") or ent.get("text") or ""
        unicode_text = convert_tcvn3_to_unicode(raw_text)
        color_idx = get_color_index(common)
        linetype = get_linetype(common)
        output_feature = QgsFeature(target_layer.fields())
        output_feature.setGeometry(qgs_geom)
        output_feature.setAttributes([
            os.path.basename(display_path),
            display_path,
            result.cad_format,
            common.get("layer", "0"),
            idx,
            common.get("layer", "0"),
            unicode_text if unicode_text else None,
            str(color_idx),
            linetype,
            str(common.get("handle", "")),
            ent_type.upper(),
            json.dumps(ent, ensure_ascii=False),
        ])
        pending_features[target_key].append(output_feature)
        counts[target_key] += 1
    for key, layer in outputs.items():
        if counts[key] <= 0:
            continue
        layer.dataProvider().addFeatures(pending_features.get(key, []))
        if add_to_project:
            add_generated_layer(project, layer, display_path, f"cad_raw_{key}", counts[key])
        else:
            from .layer_runtime import prepare_generated_layer
            prepare_generated_layer(layer, display_path, f"cad_raw_{key}", counts[key])
            result.output_layers.append(layer)
        result.output_layer_names.append(layer.name())
    result.feature_counts = counts
    if not result.output_layer_names and not result.output_layers:
        result.issues.append(
            CadImportIssue("warning", tx("cad.warning.no_output_geometry"))
        )
    return result
