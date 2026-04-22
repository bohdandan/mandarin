from __future__ import annotations

import unittest

from scripts.update_chinese_advanced_template import (
    decode_notetype_config,
    decode_template_config,
    encode_notetype_config,
    encode_template_config,
    update_back_template,
    update_notetype_css,
)


class UpdateChineseAdvancedTemplateTests(unittest.TestCase):
    def test_update_back_template_replaces_afmt_and_preserves_other_fields(self) -> None:
        original = encode_template_config("front", "back", [(8, 0, 1234)])

        updated = update_back_template(original, "back with footer")
        qfmt, afmt, extra = decode_template_config(updated)

        self.assertEqual(qfmt, "front")
        self.assertEqual(afmt, "back with footer")
        self.assertEqual(extra, [(8, 0, 1234)])

    def test_update_notetype_css_replaces_css_and_preserves_other_fields(self) -> None:
        original = encode_notetype_config(".chinese { color: red; }", [(5, 2, b"latex"), (9, 0, 1)])

        updated = update_notetype_css(original, ".chinese { color: gray; }")
        css, extra = decode_notetype_config(updated)

        self.assertEqual(css, ".chinese { color: gray; }")
        self.assertEqual(extra, [(5, 2, b"latex"), (9, 0, 1)])


if __name__ == "__main__":
    unittest.main()
