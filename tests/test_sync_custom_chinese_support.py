import unittest
import re

from scripts.sync_custom_to_chinese_support import (
    build_chinese_advanced_fields,
    latin_guide_syllables,
    should_regenerate_audio,
    split_marked_pinyin_by_guide,
)
from scripts.vocabulary import strip_html


def visible_text(value: str) -> str:
    without_comments = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    return strip_html(without_comments)


class SyncCustomToChineseSupportTest(unittest.TestCase):
    def test_should_regenerate_audio_only_for_selected_entries(self):
        entry = {"id": "custom-keyi", "hanzi": "可以"}

        self.assertFalse(should_regenerate_audio(entry, regenerate_audio=False, audio_targets=set()))
        self.assertFalse(should_regenerate_audio(entry, regenerate_audio=True, audio_targets=set()))
        self.assertTrue(should_regenerate_audio(entry, regenerate_audio=True, audio_targets={"可以"}))
        self.assertTrue(should_regenerate_audio(entry, regenerate_audio=True, audio_targets={"custom-keyi"}))
        self.assertFalse(should_regenerate_audio(entry, regenerate_audio=True, audio_targets={"地方"}))

    def test_latin_guide_syllables_keep_accented_vowels_inside_syllables(self):
        self.assertEqual(latin_guide_syllables("订票"), ["dìng", "piào"])
        self.assertEqual(latin_guide_syllables("加油"), ["jiā", "yóu"])
        self.assertEqual(latin_guide_syllables("牛油果"), ["niú", "yóu", "guǒ"])

    def test_splits_compact_pinyin_using_hanzi_guide(self):
        self.assertEqual(split_marked_pinyin_by_guide("dìfāng", ["de", "fang"]), ["dì", "fāng"])
        self.assertEqual(split_marked_pinyin_by_guide("jiāyóu", ["jia", "you"]), ["jiā", "yóu"])
        self.assertEqual(split_marked_pinyin_by_guide("niúyóuguǒ", ["niu", "you", "guo"]), ["niú", "yóu", "guǒ"])
        self.assertEqual(
            split_marked_pinyin_by_guide("niúyóuguǒ", latin_guide_syllables("牛油果")),
            ["niú", "yóu", "guǒ"],
        )
        self.assertEqual(split_marked_pinyin_by_guide("shàng/shang", ["shang"]), ["shàng"])
        self.assertEqual(split_marked_pinyin_by_guide("shéi/shuí", ["shei"]), ["shéi"])

    def test_builds_non_empty_chinese_advanced_fields_for_custom_word(self):
        entry = {
            "hanzi": "地方",
            "pinyin": "dìfāng",
            "english": "place",
            "example_sentence": "这个<b>地方</b>很安静。",
        }

        fields = build_chinese_advanced_fields(
            entry,
            pinyin_syllables=["dì", "fāng"],
            bopomofo_syllables=["ㄉㄧˋ", "ㄈㄤ"],
            traditional="地方",
            sound_ref="[sound:custom-word-difang.aiff]",
        )

        self.assertEqual(fields["Hanzi"], "地方")
        self.assertIn("tone4", fields["Color"])
        self.assertIn("tone1", fields["Color"])
        self.assertIn("<!-- difang -->", fields["Pinyin"])
        self.assertIn("ㄉㄧˋ", fields["Bopomofo"])
        self.assertIn("<ruby>地<rt>dì</rt></ruby>", fields["Ruby"])
        self.assertIn("<ruby>地<rt>ㄉㄧˋ</rt></ruby>", fields["Ruby (Bopomofo)"])
        self.assertEqual(fields["English"], "place")
        self.assertEqual(fields["Classifier"], "")
        self.assertEqual(fields["Simplified"], "地方")
        self.assertEqual(fields["Traditional"], "地方")
        self.assertEqual(fields["Also Written"], "这个<b>地方</b>很安静。")
        self.assertEqual(fields["Frequency"], '<div class="freq freq-unknown">unknown</div>')
        self.assertEqual(fields["Silhouette"], "_ _")
        self.assertEqual(fields["Sound"], "[sound:custom-word-difang.aiff]")
        self.assertEqual(visible_text(fields["Pinyin"]), "dìfāng")


if __name__ == "__main__":
    unittest.main()
