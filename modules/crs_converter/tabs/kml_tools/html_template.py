"""HTML template builder for KML popup descriptions.

Generates inline-styled HTML tables with borders, compatible with Google Earth Mobile.
"""

import html as html_lib


class HtmlTemplateBuilder:
    """Builds HTML popup content for KML descriptions."""

    def __init__(self, config):
        self.config = config

    def build(self, feature_data):
        """Build complete HTML popup for a single feature."""
        header = self.config.get('header', {})
        desc_fields = self.config.get('description_fields', [])
        row_highlights = self.config.get('row_highlights', {})

        active_fields = [f for f in desc_fields if f.get('enabled', True)]
        active_fields.sort(key=lambda x: x.get('order', 999))

        lines = []
        lines.append(
            '<div style="font-family:sans-serif;min-width:240px;max-width:400px">')
        lines.append(
            '<table border="1" cellpadding="6" cellspacing="0" '
            'style="width:100%;border-collapse:collapse;background:white;'
            'border:1px solid #ccc">')

        # Header
        h_bg = header.get('bg_color', '#1B5E20')
        h_color = header.get('text_color', '#FFFFFF')
        h_bold = 'font-weight:bold;' if header.get('bold', True) else ''
        h_size = header.get('font_size', 14)
        h_title = self._escape(header.get('title', 'Thông tin'))

        lines.append(f'<tr style="background-color:{h_bg};color:{h_color}">')
        lines.append(f'<th colspan="2" style="text-align:center;padding:10px;'
                     f'{h_bold}font-size:{h_size}px;border:1px solid #999">')
        lines.append(f'{h_title}</th></tr>')

        # Data rows
        for field_cfg in active_fields:
            field_name = field_cfg.get('field', '')
            alias = field_cfg.get('alias', field_name)
            suffix = field_cfg.get('suffix', '')
            value = feature_data.get(field_name, None)

            if value is not None and str(value).strip() != '':
                display_value = self._escape(str(value))
                if suffix:
                    display_value = f'{display_value} {self._escape(suffix)}'
            else:
                display_value = '—'

            row_style = self._get_row_highlight_style(
                field_name, value, row_highlights)

            if row_style:
                txt_clr = row_style['text_color']
                bg_clr = row_style['bg_color']
                bold = 'font-weight:bold;' if row_style.get(
                    'bold', True) else ''
                italic = 'font-style:italic;' if row_style.get(
                    'italic', False) else ''
                tr_bg = f' style="background-color:{bg_clr}"'
                label_style = (f'color:{txt_clr};{bold}{italic}width:40%;'
                               f'border:1px solid #ddd;padding:6px')
                value_style = (f'color:{txt_clr};{bold}{italic}'
                               f'border:1px solid #ddd;padding:6px')
            else:
                tr_bg = ''
                label_style = ('color:#666;font-weight:bold;width:40%;'
                               'border:1px solid #eee;padding:6px')
                value_style = 'border:1px solid #eee;padding:6px'

            lines.append(f'<tr{tr_bg}>')
            lines.append(
                f'<td style="{label_style}">{self._escape(alias)}</td>')
            lines.append(f'<td style="{value_style}">{display_value}</td>')
            lines.append('</tr>')

        lines.append('</table></div>')
        return '\n'.join(lines)

    def _get_row_highlight_style(self, field_name, value, row_highlights):
        if not row_highlights.get('enabled', False):
            return None
        for rule in row_highlights.get('rules', []):
            if rule.get('field', '') != field_name:
                continue
            if self._evaluate_condition(value, rule.get(
                    'operator', '='), rule.get('value', '')):
                return {
                    'text_color': rule.get('text_color', '#C62828'),
                    'bg_color': rule.get('bg_color', '#FFF5F5'),
                    'bold': rule.get('bold', True),
                    'italic': rule.get('italic', False)
                }
        return None

    @staticmethod
    def _evaluate_condition(actual, operator, expected):
        if actual is None:
            return False
        actual_str = str(actual).strip()
        expected_str = str(expected).strip()
        if operator == '=':
            return actual_str == expected_str
        try:
            a_num, e_num = float(actual_str), float(expected_str)
            if operator == '>':
                return a_num > e_num
            elif operator == '<':
                return a_num < e_num
        except (ValueError, TypeError):
            if operator == '>':
                return actual_str > expected_str
            elif operator == '<':
                return actual_str < expected_str
        return False

    @staticmethod
    def _escape(text):
        return html_lib.escape(str(text))
