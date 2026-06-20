import pytest

def test_stats_and_label_importable():
    from vnu2f_qlddk68.cadastral_tools.ui import stats_tab, label_tab
    from vnu2f_qlddk68.cadastral_tools.ui import stats_calculator, stats_exporter, label_configurator
    
    assert hasattr(stats_calculator, 'StatsCalculator')
    assert hasattr(stats_exporter, 'StatsExporter')
    assert hasattr(label_configurator, 'LabelConfigurator')
    
    assert hasattr(stats_tab, 'StatsTab')
    assert hasattr(label_tab, 'LabelTab')
