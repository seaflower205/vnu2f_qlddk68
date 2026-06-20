"""Script tạo các file DXF mẫu dùng để test."""
import ezdxf
from pathlib import Path

OUTPUT_DIR = Path("tests/fixtures/dxf")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def create_simple_polyline_dxf():
    """DXF có polyline khép kín — test FIX #1 (import Shapely)."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    # Polyline khép kín (hình vuông)
    points = [(0,0), (10,0), (10,10), (0,10), (0,0)]
    msp.add_lwpolyline(points, close=True)
    path = OUTPUT_DIR / "simple_polygon.dxf"
    doc.saveas(path)
    print(f"Created: {path}")
    return path

def create_tcvn3_text_dxf():
    """DXF có text TCVN3 — test FIX #6 (TCVN3 decoder)."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0,0),(10,0),(10,10),(0,10)], close=True)
    # Text giả lập TCVN3: byte \xf0 = 'đ', \xe0 = 'à'
    msp.add_text(
        "\xf0\xe1t n\xf4ng nghi\xeap",  # "đất nông nghiệp" dạng TCVN3
        dxfattribs={"height": 2.5, "insert": (1, 5)}
    )
    path = OUTPUT_DIR / "tcvn3_text.dxf"
    doc.saveas(path)
    print(f"Created: {path}")
    return path

def create_nested_block_dxf():
    """DXF có nested block — test FIX nested block extractor."""
    doc = ezdxf.new("R2010")
    # Tạo block cha chứa block con
    inner_block = doc.blocks.new("INNER_BLOCK")
    inner_block.add_attdef("MA_TUA", (0, 0), dxfattribs={"height": 1})
    
    outer_block = doc.blocks.new("OUTER_BLOCK")
    outer_block.add_blockref("INNER_BLOCK", (0, 0))
    
    msp = doc.modelspace()
    msp.add_blockref("OUTER_BLOCK", (5, 5))
    
    path = OUTPUT_DIR / "nested_block.dxf"
    doc.saveas(path)
    print(f"Created: {path}")
    return path

def create_large_polygon_dxf(n=500):
    """DXF có nhiều polygon — test performance topology."""
    import math
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for i in range(n):
        x = (i % 20) * 15
        y = (i // 20) * 15
        pts = [(x,y),(x+10,y),(x+10,y+10),(x,y+10),(x,y)]
        msp.add_lwpolyline(pts, close=True)
    path = OUTPUT_DIR / f"large_{n}_polygons.dxf"
    doc.saveas(path)
    print(f"Created: {path} ({n} polygons)")
    return path

if __name__ == "__main__":
    create_simple_polyline_dxf()
    create_tcvn3_text_dxf()
    create_nested_block_dxf()
    create_large_polygon_dxf(500)
    print("\nDone. All test fixtures created.")
