from __future__ import annotations

import unittest

from scripts.backfill_sentence_translations import apply_translations, missing_translation_items


class BackfillSentenceTranslationsTests(unittest.TestCase):
    def test_missing_translation_items_strip_html_and_skip_existing_translations(self) -> None:
        entries = [
            {
                "id": "word-1",
                "example_sentence": "她今天的<b>表现</b>很好。",
                "sentence_translation": "",
            },
            {
                "id": "word-2",
                "example_sentence": "我喜欢喝茶。",
                "sentence_translation": "I like drinking tea.",
            },
            {
                "id": "word-3",
                "example_sentence": "",
                "sentence_translation": "",
            },
        ]

        self.assertEqual(
            missing_translation_items(entries),
            [(0, "她今天的表现很好。")],
        )

    def test_apply_translations_updates_matching_entries_only(self) -> None:
        entries = [
            {"id": "word-1", "sentence_translation": ""},
            {"id": "word-2", "sentence_translation": "Existing"},
        ]

        count = apply_translations(entries, [(0, "Her performance today was very good.")])

        self.assertEqual(count, 1)
        self.assertEqual(entries[0]["sentence_translation"], "Her performance today was very good.")
        self.assertEqual(entries[1]["sentence_translation"], "Existing")


if __name__ == "__main__":
    unittest.main()
