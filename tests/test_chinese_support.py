import re
import unittest

from scripts.chinese_support import (
    build_display_tone_fields,
    build_tone_fields,
    bulk_latin_guide_syllables,
    chinese_advanced_back_template,
    primary_citation_pinyin,
    reconcile_generated_tags,
    updated_chinese_advanced_css,
    written_chinese_footer_placeholder_html,
    written_chinese_url,
)
from scripts.vocabulary import strip_html


def visible_text(value: str) -> str:
    without_comments = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    return strip_html(without_comments)


class ChineseSupportToneFieldTest(unittest.TestCase):
    def test_written_chinese_url_encodes_hanzi(self):
        self.assertEqual(
            written_chinese_url("我"),
            "https://dictionary.writtenchinese.com/#sk=%E6%88%91&svt=pinyin",
        )

    def test_chinese_advanced_back_template_includes_footer_link(self):
        template = chinese_advanced_back_template()

        self.assertIn(">◫</a>", template)
        self.assertIn("encodeURIComponent", template)
        self.assertIn("dictionary.writtenchinese.com", template)
        self.assertIn("{{text:Hanzi}}", template)
        self.assertIn('class="meta-row"', template)
        self.assertNotIn(">Character breakdown<", template)

    def test_written_chinese_footer_placeholder_keeps_footer_lane_without_link(self):
        template = written_chinese_footer_placeholder_html()

        self.assertIn('class="meta-row"', template)
        self.assertIn('class="written-chinese-placeholder"', template)
        self.assertNotIn('written-chinese-link', template)
        self.assertNotIn("encodeURIComponent", template)

    def test_updated_chinese_advanced_css_uses_neutral_hanzi_and_footer_link_styles(self):
        original = (
            ".chinese {\n  color: #ff6e67;\n}\n"
            ".night_mode .chinese { color: #ff79c6; }\n"
            ".tags {\n  font-size: 9pt;\n  opacity: 0.6;\n  margin-top: 20px;\n}\n"
        )

        updated = updated_chinese_advanced_css(original)

        self.assertIn("color: #6c757d;", updated)
        self.assertIn(".night_mode .chinese { color: #6272a4; }", updated)
        self.assertIn(".meta-row {", updated)
        self.assertIn(".written-chinese-link {", updated)
        self.assertIn(".night_mode .written-chinese-link {", updated)
        self.assertIn("color: #6272a4;", updated)

    def test_primary_citation_pinyin_keeps_first_variant(self):
        self.assertEqual(primary_citation_pinyin("shàng/shang"), "shàng")
        self.assertEqual(primary_citation_pinyin("shéi/shuí"), "shéi")

    def test_build_tone_fields_use_citation_tone_for_variant_readings(self):
        shang_fields = build_tone_fields("上", "shàng/shang")
        shei_fields = build_tone_fields("谁", "shéi/shuí")

        self.assertEqual(shang_fields["Color"], '<span class="tone4">上</span>')
        self.assertIn('<span class="tone4">shàng</span>', shang_fields["Pinyin"])
        self.assertEqual(shei_fields["Color"], '<span class="tone2">谁</span>')
        self.assertIn('<span class="tone2">shéi</span>', shei_fields["Pinyin"])

    def test_build_tone_fields_preserve_repo_display_formatting(self):
        compact = build_tone_fields("一起", "yìqǐ")
        spaced = build_tone_fields("为什么", "wèi shénme")
        variant = build_tone_fields("上", "shàng/shang")

        self.assertEqual(visible_text(compact["Pinyin"]), "yìqǐ")
        self.assertEqual(visible_text(spaced["Pinyin"]), "wèi shénme")
        self.assertEqual(visible_text(variant["Pinyin"]), "shàng/shang")

    def test_build_display_tone_fields_with_bulk_guides_preserve_repo_display_formatting(self):
        guides = bulk_latin_guide_syllables(["一起", "为什么", "上", "牛油果"])

        compact = build_display_tone_fields("一起", "yìqǐ", guide_syllables=guides["一起"])
        spaced = build_display_tone_fields("为什么", "wèi shénme", guide_syllables=guides["为什么"])
        variant = build_display_tone_fields("上", "shàng/shang", guide_syllables=guides["上"])
        custom = build_display_tone_fields("牛油果", "niúyóuguǒ", guide_syllables=guides["牛油果"])

        self.assertEqual(visible_text(compact["Pinyin"]), "yìqǐ")
        self.assertEqual(visible_text(spaced["Pinyin"]), "wèi shénme")
        self.assertEqual(visible_text(variant["Pinyin"]), "shàng/shang")
        self.assertEqual(visible_text(custom["Pinyin"]), "niúyóuguǒ")
        self.assertIn('class="tone2"', custom["Color"])

    def test_reconcile_generated_tags_replaces_lowercase_variants(self):
        to_add, to_remove = reconcile_generated_tags(
            ["hsk2", "custom", "added-2026", "keep-me"],
            ["HSK2", "CUSTOM", "ADDED-2026"],
        )

        self.assertEqual(to_add, ["HSK2", "CUSTOM", "ADDED-2026"])
        self.assertEqual(to_remove, ["hsk2", "custom", "added-2026"])


if __name__ == "__main__":
    unittest.main()
