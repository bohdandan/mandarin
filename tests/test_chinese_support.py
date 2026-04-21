import re
import unittest

from scripts.chinese_support import build_tone_fields, primary_citation_pinyin, reconcile_generated_tags
from scripts.vocabulary import strip_html


def visible_text(value: str) -> str:
    without_comments = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    return strip_html(without_comments)


class ChineseSupportToneFieldTest(unittest.TestCase):
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

    def test_reconcile_generated_tags_replaces_lowercase_variants(self):
        to_add, to_remove = reconcile_generated_tags(
            ["hsk2", "custom", "added-2026", "keep-me"],
            ["HSK2", "CUSTOM", "ADDED-2026"],
        )

        self.assertEqual(to_add, ["HSK2", "CUSTOM", "ADDED-2026"])
        self.assertEqual(to_remove, ["hsk2", "custom", "added-2026"])


if __name__ == "__main__":
    unittest.main()
