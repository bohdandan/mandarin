import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.vocabulary import (
    build_entry,
    derive_tags,
    earliest_hsk_lesson_sort_key,
    read_source_vocabulary,
    source_sort_key,
    source_filename,
    write_source_vocabulary,
)


class SourceVocabularyTest(unittest.TestCase):
    def test_custom_words_store_year_lesson_and_generate_tags(self):
        entry = build_entry(
            hanzi="杯子",
            pinyin="bēi zi",
            english="cup",
            source="custom",
            lesson="custom",
            hsk_level=2,
            today="2026-04-19",
        )

        self.assertEqual(entry["id"], "custom-word-bei-zi")
        self.assertNotIn("tags", entry)
        self.assertEqual(entry["lesson"], "2026")
        self.assertEqual(derive_tags(entry), ["HSK2", "CUSTOM", "ADDED-2026"])

    def test_source_filename_is_stable_and_safe(self):
        self.assertEqual(source_filename("hsk-workbook"), "hsk-workbook.json")
        self.assertEqual(source_filename("Lesson April 19"), "lesson-april-19.json")

    def test_extracts_earliest_hsk_lesson_sort_key(self):
        self.assertEqual(earliest_hsk_lesson_sort_key("HSK:1.04"), (1, 4))
        self.assertEqual(earliest_hsk_lesson_sort_key("HSK:1.09; HSK:1.14"), (1, 9))
        self.assertIsNone(earliest_hsk_lesson_sort_key("2026"))

    def test_writes_index_and_one_json_file_per_source(self):
        entries = [
            {"id": "1", "source": "hsk-workbook", "hsk_level": 1, "lesson": "HSK:1.03", "hanzi": "中"},
            {"id": "2", "source": "custom", "hsk_level": None},
            {"id": "3", "source": "hsk-workbook", "hsk_level": 2, "lesson": "HSK:1.01", "hanzi": "啊"},
            {"id": "4", "source": "hsk-workbook", "hsk_level": 1, "lesson": "HSK:1.01; HSK:1.08", "hanzi": "八"},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "sources"
            output_dir.mkdir(parents=True)
            (output_dir / "stale.json").write_text("[]", encoding="utf-8")
            write_source_vocabulary(output_dir, entries)

            index = json.loads((output_dir / "index.json").read_text(encoding="utf-8"))
            hsk = json.loads((output_dir / "hsk-workbook.json").read_text(encoding="utf-8"))
            custom = json.loads((output_dir / "custom.json").read_text(encoding="utf-8"))
            round_trip = read_source_vocabulary(output_dir)

            self.assertEqual(
                index,
                {
                    "sources": [
                        {"source": "custom", "file": "custom.json"},
                        {"source": "hsk-workbook", "file": "hsk-workbook.json"},
                    ]
                },
            )
            self.assertEqual([entry["id"] for entry in hsk], ["4", "3", "1"])
            self.assertEqual([entry["id"] for entry in custom], ["2"])
            self.assertEqual([entry["id"] for entry in round_trip], ["2", "4", "3", "1"])
            self.assertFalse((output_dir / "stale.json").exists())

    def test_committed_sources_generate_anki_ready_tags(self):
        source_dir = Path("data/sources")
        index = json.loads((source_dir / "index.json").read_text(encoding="utf-8"))
        hsk1_entries = json.loads((source_dir / "hsk-1.json").read_text(encoding="utf-8"))
        hsk2_entries = json.loads((source_dir / "hsk-2.json").read_text(encoding="utf-8"))
        custom_entries = json.loads((source_dir / "custom.json").read_text(encoding="utf-8"))
        hsk1_lesson_tag = re.compile(r"^HSK1::HSK:1\.\d{2}$")
        hsk2_lesson_tag = re.compile(r"^HSK2::HSK:2\.\d{2}$")

        self.assertIn({"source": "hsk-1", "file": "hsk-1.json"}, index["sources"])
        self.assertEqual(len(hsk1_entries), 316)
        self.assertEqual(
            [entry["id"] for entry in hsk1_entries],
            [entry["id"] for entry in sorted(hsk1_entries, key=source_sort_key)],
        )
        self.assertTrue(all(entry["english"] for entry in hsk1_entries))
        self.assertTrue(all(entry["example_sentence"] for entry in hsk1_entries))

        for entry in hsk1_entries:
            self.assertNotIn("tags", entry)
            self.assertEqual(entry["source"], "hsk-1")
            self.assertEqual(entry["hsk_level"], 1)
            tags = derive_tags(entry)
            self.assertTrue(tags)
            self.assertEqual(tags[0], "HSK1")
            self.assertTrue(all(tag == "HSK1" or hsk1_lesson_tag.match(tag) for tag in tags))

        hsk1_by_hanzi = {entry["hanzi"]: entry for entry in hsk1_entries}
        self.assertEqual(derive_tags(hsk1_by_hanzi["上"]), ["HSK1", "HSK1::HSK:1.09", "HSK1::HSK:1.14"])
        self.assertIn("Proper noun", hsk1_by_hanzi["大兴机场"]["notes"])
        self.assertIn("beyond the syllabus", hsk1_by_hanzi["病人"]["notes"])

        for entry in hsk2_entries:
            self.assertNotIn("tags", entry)
            tags = derive_tags(entry)
            self.assertTrue(tags)
            self.assertEqual(tags[0], "HSK2")
            self.assertTrue(all(tag == "HSK2" or hsk2_lesson_tag.match(tag) for tag in tags))
        self.assertEqual(
            [entry["id"] for entry in hsk2_entries],
            [entry["id"] for entry in sorted(hsk2_entries, key=source_sort_key)],
        )
        self.assertTrue(all(entry["english"] for entry in hsk2_entries))
        self.assertTrue(all(entry["example_sentence"] for entry in hsk2_entries))

        for entry in custom_entries:
            self.assertNotIn("tags", entry)
            self.assertEqual(entry["source"], "custom")
            self.assertEqual(entry["lesson"], "2026")
            self.assertIsInstance(entry["hsk_level"], int)
            self.assertIn("CUSTOM", derive_tags(entry))
            self.assertIn("ADDED-2026", derive_tags(entry))


if __name__ == "__main__":
    unittest.main()
