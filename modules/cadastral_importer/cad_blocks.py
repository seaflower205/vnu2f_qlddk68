# -*- coding: utf-8 -*-
"""Block expansion and affine transforms for parsed CAD entities."""
from __future__ import annotations
import math

def flatten_entities(doc: dict) -> list[dict]:
    """Recursively expand blocks (Insert entities) and transform geometries to Model Space."""
    entity_index = doc.get("entity_index", {})
    block_records = doc.get("block_records", {}).get("entries", {})

    def transform_pt(pt: dict, ins_pt: tuple[float, float], scale: tuple[float, float], rotation_deg: float) -> dict:
        x = pt.get("x", 0.0)
        y = pt.get("y", 0.0)
        # 1. Scale
        xs, ys = scale[0], scale[1]
        x_s = x * xs
        y_s = y * ys
        # 2. Rotate
        rad = math.radians(rotation_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        x_r = x_s * cos_a - y_s * sin_a
        y_r = x_s * sin_a + y_s * cos_a
        # 3. Translate
        return {"x": x_r + ins_pt[0], "y": y_r + ins_pt[1], "z": pt.get("z", 0.0)}

    def process_entity(ent_wrapper: dict, ins_pt: tuple[float, float], scale: tuple[float, float], rotation_deg: float, parent_layer: str | None = None):
        import copy
        ent_type = list(ent_wrapper.keys())[0]
        ent = copy.deepcopy(ent_wrapper[ent_type])
        common = ent.get("common", {})
        
        # Inherit layer from parent block insert if child is on layer '0'
        child_layer = common.get("layer", "0")
        if (child_layer == "0" or not child_layer) and parent_layer:
            common["layer"] = parent_layer
            ent["common"] = common

        if ent_type == "Line":
            ent["start"] = transform_pt(ent["start"], ins_pt, scale, rotation_deg)
            ent["end"] = transform_pt(ent["end"], ins_pt, scale, rotation_deg)
            yield {"Line": ent}

        elif ent_type == "LwPolyline":
            for v in ent.get("vertices", []):
                v["location"] = transform_pt(v["location"], ins_pt, scale, rotation_deg)
            yield {"LwPolyline": ent}

        elif ent_type == "Circle":
            ent["center"] = transform_pt(ent["center"], ins_pt, scale, rotation_deg)
            avg_scale = (scale[0] + scale[1]) / 2.0
            ent["radius"] = ent["radius"] * avg_scale
            yield {"Circle": ent}

        elif ent_type == "Arc":
            ent["center"] = transform_pt(ent["center"], ins_pt, scale, rotation_deg)
            avg_scale = (scale[0] + scale[1]) / 2.0
            ent["radius"] = ent["radius"] * avg_scale
            ent["start_angle"] = (ent["start_angle"] + rotation_deg) % 360
            ent["end_angle"] = (ent["end_angle"] + rotation_deg) % 360
            yield {"Arc": ent}

        elif ent_type == "Ellipse":
            ent["center"] = transform_pt(ent["center"], ins_pt, scale, rotation_deg)
            # Transform major_axis vector (no translation)
            mx = ent["major_axis"].get("x", 0.0) * scale[0]
            my = ent["major_axis"].get("y", 0.0) * scale[1]
            rad = math.radians(rotation_deg)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            mx_r = mx * cos_a - my * sin_a
            my_r = mx * sin_a + my * cos_a
            ent["major_axis"] = {"x": mx_r, "y": my_r, "z": ent["major_axis"].get("z", 0.0)}
            yield {"Ellipse": ent}

        elif ent_type == "Point":
            ent["location"] = transform_pt(ent["location"], ins_pt, scale, rotation_deg)
            yield {"Point": ent}

        elif ent_type == "Text":
            ent["insertion_point"] = transform_pt(ent["insertion_point"], ins_pt, scale, rotation_deg)
            if ent.get("alignment_point"):
                ent["alignment_point"] = transform_pt(ent["alignment_point"], ins_pt, scale, rotation_deg)
            ent["rotation"] = ent.get("rotation", 0.0) + math.radians(rotation_deg)
            yield {"Text": ent}

        elif ent_type == "MText":
            ent["insertion_point"] = transform_pt(ent["insertion_point"], ins_pt, scale, rotation_deg)
            ent["rotation"] = ent.get("rotation", 0.0) + math.radians(rotation_deg)
            yield {"MText": ent}

        elif ent_type == "Insert":
            block_name = ent.get("block_name")
            block_name_upper = block_name.upper() if block_name else ""
            if block_name_upper and block_name_upper in block_records:
                b_record = block_records[block_name_upper]
                # Combine affine transformations
                ins_pt_new = transform_pt(ent["insert_point"], ins_pt, scale, rotation_deg)
                ins_pt_new_tuple = (ins_pt_new["x"], ins_pt_new["y"])
                scale_new = (scale[0] * ent.get("x_scale", 1.0), scale[1] * ent.get("y_scale", 1.0))
                rotation_new = (rotation_deg + math.degrees(ent.get("rotation", 0.0))) % 360

                insert_layer = common.get("layer", "0")
                next_parent_layer = parent_layer if (insert_layer == "0" or not insert_layer) else insert_layer

                for h in b_record.get("entity_handles", []):
                    h_str = str(h)
                    if h_str in entity_index:
                        ent_idx = entity_index[h_str]
                        child_wrapper = doc["entities"][ent_idx]
                        yield from process_entity(child_wrapper, ins_pt_new_tuple, scale_new, rotation_new, next_parent_layer)

    for ent_wrapper in doc.get("entities", []):
        yield from process_entity(ent_wrapper, (0.0, 0.0), (1.0, 1.0), 0.0)


