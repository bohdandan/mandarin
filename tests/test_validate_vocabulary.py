import unittest

from scripts.validate_vocabulary import validate_entries


class ValidateVocabularyTest(unittest.TestCase):
    def test_accepts_clean_entries(self):
        errors = validate_entries([
            {
                "id": "hsk1-0001-ni-hao",
                "hanzi": "你好",
                "pinyin": "nǐ hǎo",
                "english": "hello",
                "example_sentence": "<b>你好</b>！",
                "sentence_pinyin": "nǐ hǎo",
                "sentence_translation": "",
                "hsk_level": 1,
                "source": "hsk-workbook",
                "lesson": "HSK:1.01",
                "notes": "",
                "created_at": "2026-04-19",
                "updated_at": "2026-04-19",
            }
        ])

        self.assertEqual(errors, [])

    def test_reports_missing_required_fields_and_duplicates(self):
        entries = [
            {
                "id": "same",
                "hanzi": "你好",
                "pinyin": "nǐ hǎo",
                "english": "hello",
                "example_sentence": "",
                "sentence_pinyin": "",
                "sentence_translation": "",
                "hsk_level": 1,
                "source": "hsk-workbook",
                "lesson": "",
                "notes": "",
                "created_at": "2026-04-19",
                "updated_at": "2026-04-19",
            },
            {
                "id": "same",
                "hanzi": "你好",
                "pinyin": "nǐ hǎo",
                "english": "hello",
                "example_sentence": "",
                "sentence_pinyin": "",
                "sentence_translation": "",
                "hsk_level": 1,
                "source": "hsk-workbook",
                "lesson": "",
                "notes": "",
                "created_at": "2026-04-19",
                "updated_at": "2026-04-19",
            },
            {
                "id": "missing-english",
                "hanzi": "谢谢",
                "pinyin": "xiè xiè",
                "english": "",
                "example_sentence": "",
                "sentence_pinyin": "",
                "sentence_translation": "",
                "hsk_level": 1,
                "source": "hsk-workbook",
                "lesson": "",
                "notes": "",
                "created_at": "2026-04-19",
                "updated_at": "2026-04-19",
            },
        ]

        errors = validate_entries(entries)

        self.assertFalse(any("missing english" in error for error in errors))
        self.assertTrue(any("duplicate id same" in error for error in errors))
        self.assertTrue(any("duplicate hanzi/pinyin 你好 / nǐ hǎo" in error for error in errors))

    def test_allows_missing_english_when_source_material_has_no_translation(self):
        entries = [
            {
                "id": "hsk1-0001-ai",
                "hanzi": "爱",
                "pinyin": "ài",
                "english": "",
                "source": "hsk-1",
                "created_at": "2026-04-19",
                "updated_at": "2026-04-19",
            }
        ]

        self.assertEqual(validate_entries(entries), [])

    def test_allows_same_hanzi_and_pinyin_when_meaning_differs(self):
        entries = [
            {
                "id": "hsk2-0057-hua",
                "hanzi": "花",
                "pinyin": "huā",
                "english": "to spend",
                "source": "hsk-2",
                "created_at": "2026-04-19",
                "updated_at": "2026-04-19",
            },
            {
                "id": "hsk2-0058-hua",
                "hanzi": "花",
                "pinyin": "huā",
                "english": "flower",
                "source": "hsk-2",
                "created_at": "2026-04-19",
                "updated_at": "2026-04-19",
            },
        ]

        self.assertEqual(validate_entries(entries), [])

    def test_rejects_stored_tags_because_tags_are_generated(self):
        errors = validate_entries([
            {
                "id": "hsk1-0001-ni-hao",
                "hanzi": "你好",
                "pinyin": "nǐ hǎo",
                "english": "hello",
                "source": "hsk-1",
                "lesson": "HSK:1.01",
                "tags": ["hsk1"],
                "created_at": "2026-04-19",
                "updated_at": "2026-04-19",
            }
        ])

        self.assertTrue(any("tags are generated" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
