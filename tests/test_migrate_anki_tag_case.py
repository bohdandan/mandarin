from __future__ import annotations

import unittest

from scripts.migrate_anki_tag_case import TAG_CASE_MAP, normalize_note_tags


class MigrateAnkiTagCaseTests(unittest.TestCase):
    def test_normalize_note_tags_replaces_standalone_tokens(self) -> None:
        self.assertEqual(
            normalize_note_tags(" added-2026 custom hsk2 HSK2::HSK:2.03 ", TAG_CASE_MAP),
            " ADDED-2026 CUSTOM HSK2 HSK2::HSK:2.03 ",
        )

    def test_normalize_note_tags_leaves_substrings_alone(self) -> None:
        self.assertEqual(
            normalize_note_tags(" HSK2::HSK:2.03 lesson-customized ", TAG_CASE_MAP),
            " HSK2::HSK:2.03 lesson-customized ",
        )


if __name__ == "__main__":
    unittest.main()
