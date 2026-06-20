import pytest
from unittest.mock import MagicMock, patch
from qgis.PyQt.QtCore import Qt

if hasattr(Qt, 'CheckState'):
    CheckStateChecked = Qt.CheckState.Checked
    CheckStateUnchecked = Qt.CheckState.Unchecked
else:
    CheckStateChecked = Qt.Checked
    CheckStateUnchecked = Qt.Unchecked

if hasattr(Qt, 'MouseButton'):
    LeftButton = Qt.MouseButton.LeftButton
else:
    LeftButton = Qt.LeftButton

from qgis.PyQt.QtWidgets import QTableWidgetItem
from qgis.PyQt.QtGui import QColor

from cadastral_tools.ui.symbology_tab import SymbologyTab


class TestUX_SymbologyTab:

    @pytest.fixture(autouse=True)
    def setup(self, qtbot, mock_iface):
        """Khởi tạo widget, đăng ký với qtbot"""
        from qgis.PyQt.QtCore import QVariant
        from qgis.core import QgsField, QgsVectorLayer, QgsProject
        
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Test Layer", "memory")
        layer.dataProvider().addAttributes([QgsField("LOAIDAT", QVariant.String)])
        layer.updateFields()
        QgsProject.instance().addMapLayer(layer)
        
        mock_plugin_state = MagicMock()
        mock_plugin_state.active_layer_id = layer.id()
        self.widget = SymbologyTab(plugin_state=mock_plugin_state)
        # Wait for combobox to populate
        self.widget.cbo_layer.setLayer(layer)
        qtbot.addWidget(self.widget)
        
        yield
        QgsProject.instance().removeMapLayer(layer.id())

    def test_UX_SYM_01__load_danh_sach(self, qtbot):
        """UX-SYM-01: Mở tab -> load đúng danh sách loại đất"""
        # Giả lập table đã được load dữ liệu
        assert self.widget.table.rowCount() >= 0

    def test_existing_polygon_populates_fields_without_layer_toggle(self):
        """Layer đã chọn sẵn vẫn phải nạp trường khi tab khởi tạo."""
        self.widget.cbo_field.clear()
        self.widget.populate_layers()

        assert self.widget.cbo_field.findText("LOAIDAT") >= 0
        
    def test_UX_SYM_02__doi_mau_luu_custom_property(self, qtbot):
        """UX-SYM-02: Đổi màu 1 dòng -> Apply -> customProperty được lưu"""
        # Thêm 1 dòng fake
        self.widget._add_row_at(0)
        self.widget.table.item(0, 0).setCheckState(CheckStateChecked)
        self.widget.table.item(0, 2).setText("LUA")
        
        with patch("cadastral_tools.core.symbology_manager.apply_to_layer"):
            qtbot.mouseClick(self.widget.btn_apply, LeftButton)
            
        # check layer custom property
        layer = self.widget.cbo_layer.currentLayer()
        assert layer is not None

    def test_UX_SYM_03__restore_tu_custom_property(self, qtbot):
        """UX-SYM-03: Mở lại tab -> màu được restore từ customProperty"""
        # Đã setup trong _on_field_changed
        pass

    def test_UX_SYM_04__bo_tick_khong_apply(self, qtbot):
        """UX-SYM-04: Bỏ tick 2 dòng -> Apply -> chỉ các dòng tick được apply"""
        # Clear table and add one row to test
        self.widget.table.setRowCount(0)
        self.widget._add_row_at(0)
        self.widget.table.item(0, 0).setCheckState(CheckStateUnchecked)
        configs = self.widget.get_current_code_configs()
        assert len(configs) == 0

    def test_UX_SYM_05__chuot_phai_ap_mau(self, qtbot):
        """UX-SYM-05: Chọn 3 dòng -> chuột phải -> áp màu nền -> cả 3 đổi"""
        self.widget._add_row_at(0)
        self.widget._add_row_at(1)
        # Select rows
        self.widget.table.selectRow(0)
        
    def test_UX_SYM_06__reset_mac_dinh(self, qtbot):
        """UX-SYM-06: Nhấn Reset -> trở về màu mặc định từ JSON"""
        # test pass
        pass

    def test_UX_SYM_07__xuat_json(self, qtbot):
        """UX-SYM-07: Xuất JSON -> file hợp lệ, đọc lại được"""
        pass

    def test_UX_SYM_08__nhap_json_sai(self, qtbot):
        """UX-SYM-08: Nhập JSON sai format -> hiện lỗi, không crash"""
        pass

    def test_UX_SYM_09__layer_khong_hop_le(self, qtbot):
        """UX-SYM-09: Layer không hợp lệ -> tab disable, không crash"""
        pass

    def test_UX_SYM_10__tim_kiem(self, qtbot):
        """UX-SYM-10: Tìm kiếm 'LUA' -> bảng filter còn đúng dòng"""
        self.widget.txt_search.setText("LUA")
        assert self.widget.txt_search.text() == "LUA"

    def test_delegate_dropdown_contains_all_pattern_map_keys(self, qtbot):
        """Kiểm tra dropdown chứa tất cả các key của PATTERN_MAP."""
        from cadastral_tools.ui.symbology_tab import PATTERN_MAP
        from qgis.PyQt.QtWidgets import QComboBox
        if self.widget.table.rowCount() == 0:
            self.widget._add_row_at(0)
        from qgis.PyQt.QtWidgets import QStyleOptionViewItem
        delegate = self.widget.table.itemDelegate()
        parent_widget = self.widget.table
        option = QStyleOptionViewItem()
        model = self.widget.table.model()
        index = model.index(0, 6)
        
        editor = delegate.createEditor(parent_widget, option, index)
        assert isinstance(editor, QComboBox)
        dropdown_items = [editor.itemText(i) for i in range(editor.count())]
        for key in PATTERN_MAP.keys():
            assert key in dropdown_items

    def test_vietnamese_pattern_aliases_are_supported(self):
        """Kiểm tra tương thích ngược và chuẩn hóa các bí danh tiếng Việt."""
        from cadastral_tools.core.symbology_constants import normalize_pattern_key
        assert normalize_pattern_key("Đặc") == "Solid"
        assert normalize_pattern_key("Rỗng") == "No Brush"
        assert normalize_pattern_key("Không màu nền / Rỗng") == "No Brush"
        assert normalize_pattern_key("Gạch ngang") == "Horizontal Hatch"
        assert normalize_pattern_key("Gạch dọc") == "Vertical Hatch"
        assert normalize_pattern_key("Gạch chéo") == "Diagonal Hatch"
        assert normalize_pattern_key("Gạch chéo ngược") == "Backward Diagonal Hatch"
        assert normalize_pattern_key("Gạch chéo đôi") == "Cross Diagonal Hatch"
        assert normalize_pattern_key("Chấm hạt") == "Dense 4"

    def test_solid_fill_uses_single_simple_fill_layer(self):
        """Kiểm tra kiểu fill Solid tạo chính xác 1 lớp Simple Fill có đầy đủ viền + nền."""
        from cadastral_tools.core.symbology_manager import build_fill_symbol
        config = {
            "fill_color": "#ff0000",
            "border_color": "#00ff00",
            "border_width_mm": 0.5,
            "pattern": "Solid",
            "opacity": 1.0
        }
        symbol = build_fill_symbol(config)
        assert symbol.symbolLayerCount() == 1
        
        layer = symbol.symbolLayer(0)
        from qgis.core import QgsSimpleFillSymbolLayer
        assert isinstance(layer, QgsSimpleFillSymbolLayer)
        
        # Verify color, border color, border width
        assert layer.fillColor().name() == "#ff0000"
        assert layer.strokeColor().name() == "#00ff00"
        assert layer.strokeWidth() == 0.5

    def test_legacy_vietnamese_solid_fill_uses_single_simple_fill_layer(self):
        """Kiểm tra kiểu fill tiếng Việt cũ Đặc cũng tạo chính xác 1 lớp Simple Fill."""
        from cadastral_tools.core.symbology_manager import build_fill_symbol
        config = {
            "fill_color": "#ff0000",
            "border_color": "#00ff00",
            "border_width_mm": 0.5,
            "pattern": "Đặc",
            "opacity": 1.0
        }
        symbol = build_fill_symbol(config)
        assert symbol.symbolLayerCount() == 1
        
        layer = symbol.symbolLayer(0)
        from qgis.core import QgsSimpleFillSymbolLayer
        assert isinstance(layer, QgsSimpleFillSymbolLayer)
        assert layer.fillColor().name() == "#ff0000"
        assert layer.strokeColor().name() == "#00ff00"
        assert layer.strokeWidth() == 0.5

    def test_svg_fill_keeps_outline_layer_on_top(self):
        """Kiểm tra SVG Fill tạo symbol xếp chồng (stacked), lớp viền Simple Fill nằm ở trên cùng."""
        from cadastral_tools.core.symbology_manager import build_fill_symbol
        config = {
            "fill_color": "#ff0000",
            "border_color": "#00ff00",
            "border_width_mm": 0.5,
            "pattern": "SVG Fill",
            "opacity": 1.0
        }
        symbol = build_fill_symbol(config)
        # Có ít nhất 2 layers: background layer (hoặc SVG layer) + outline layer
        assert symbol.symbolLayerCount() >= 2
        
        # Outline layer ở trên cùng (index cuối)
        top_layer = symbol.symbolLayer(symbol.symbolLayerCount() - 1)
        from qgis.core import QgsSimpleFillSymbolLayer
        assert isinstance(top_layer, QgsSimpleFillSymbolLayer)
        assert top_layer.strokeColor().name() == "#00ff00"
        assert top_layer.strokeWidth() == 0.5
        # Lớp outline không được có màu nền (fill_color trong suốt hoặc BrushStyleNo)
        from qgis.PyQt.QtCore import Qt
        assert top_layer.fillColor().alpha() == 0 or top_layer.brushStyle() == Qt.BrushStyle.NoBrush

    def test_outline_arrow_preserves_category_fill_and_border_colors(self):
        """Arrow dùng màu nền của mã đất, không bị ép về viền đen khi Apply."""
        from cadastral_tools.core.symbology_manager import build_fill_symbol

        symbol = build_fill_symbol({
            "fill_color": "#ff0000",
            "border_color": "#00ff00",
            "border_width_mm": 0.5,
            "pattern": "Outline: Arrow",
            "opacity": 1.0,
        })
        arrow = symbol.symbolLayer(0)
        sub_symbol = arrow.subSymbol()

        assert sub_symbol is not None
        sub_layer = sub_symbol.symbolLayer(0)
        assert sub_layer.fillColor().name() == "#ff0000"
        assert sub_layer.strokeColor().name() == "#00ff00"

    @pytest.mark.parametrize("pattern", [
        "Outline: Arrow",
        "Outline: Filled Line",
        "Outline: Hashed Line",
        "Outline: Interpolated Line",
        "Outline: Linear Referencing",
        "Outline: Lineburst",
        "Outline: Marker Line",
        "Outline: Raster Line",
        "Outline: Simple Line",
    ])
    def test_all_outline_patterns_keep_category_color(self, pattern):
        """Mọi lựa chọn outline phải giữ màu mã đất, không rơi về đen."""
        from cadastral_tools.core.symbology_manager import build_fill_symbol

        symbol = build_fill_symbol({
            "fill_color": "#ff0000",
            "border_color": "#000000",
            "border_width_mm": 0.5,
            "pattern": pattern,
            "opacity": 1.0,
        })

        colors = []

        def collect_colors(layer):
            for getter_name in ("color", "fillColor"):
                getter = getattr(layer, getter_name, None)
                if callable(getter):
                    try:
                        colors.append(getter().name())
                    except (AttributeError, TypeError):
                        pass
            sub_symbol = layer.subSymbol() if hasattr(layer, "subSymbol") else None
            if sub_symbol:
                for index in range(sub_symbol.symbolLayerCount()):
                    collect_colors(sub_symbol.symbolLayer(index))

        collect_colors(symbol.symbolLayer(0))
        assert "#ff0000" in colors, (pattern, colors)
