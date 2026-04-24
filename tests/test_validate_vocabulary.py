import unittest

from scripts.validate_vocabulary import validate_entries


class ValidateVocabularyTest(unittest.TestCase):
    def test_entries_require_english(self):
        entries = [
            {
                "id": "hsk1-0001-ni",
                "hanzi": "你",
                "pinyin": "nǐ",
                "english": "",
                "source": "hsk-1",
                "hsk_level": 1,
                "lesson": "HSK:1.01",
                "example_sentence": "我<b>喜欢</b>你。",
                "created_at": "2026-04-24",
                "updated_at": "2026-04-24",
            }
        ]

        errors = validate_entries(entries)

        self.assertIn("hsk1-0001-ni: missing english", errors)

    def test_hsk_entries_require_example_sentences(self):
        entries = [
            {
                "id": "hsk1-0001-ni",
                "hanzi": "你",
                "pinyin": "nǐ",
                "english": "you",
                "source": "hsk-1",
                "hsk_level": 1,
                "lesson": "HSK:1.01",
                "example_sentence": "",
                "created_at": "2026-04-24",
                "updated_at": "2026-04-24",
            }
        ]

        errors = validate_entries(entries)

        self.assertIn("hsk1-0001-ni: missing example_sentence for HSK source", errors)

    def test_custom_entries_may_skip_example_sentences(self):
        entries = [
            {
                "id": "custom-word-jiayou",
                "hanzi": "加油",
                "pinyin": "jiāyóu",
                "english": "come on",
                "source": "custom",
                "hsk_level": 3,
                "lesson": "2026",
                "example_sentence": "",
                "created_at": "2026-04-24",
                "updated_at": "2026-04-24",
            }
        ]

        self.assertEqual(validate_entries(entries), [])

    def test_hsk_entries_must_follow_lesson_order(self):
        entries = [
            {
                "id": "hsk1-0002-shi",
                "hanzi": "是",
                "pinyin": "shì",
                "english": "to be",
                "source": "hsk-1",
                "hsk_level": 1,
                "lesson": "HSK:1.02",
                "example_sentence": "我<b>是</b>学生。",
                "created_at": "2026-04-24",
                "updated_at": "2026-04-24",
            },
            {
                "id": "hsk1-0001-nihao",
                "hanzi": "你好",
                "pinyin": "nǐ hǎo",
                "english": "hello",
                "source": "hsk-1",
                "hsk_level": 1,
                "lesson": "HSK:1.01",
                "example_sentence": "<b>你好</b>！",
                "created_at": "2026-04-24",
                "updated_at": "2026-04-24",
            },
        ]

        errors = validate_entries(entries)

        self.assertIn("hsk1-0001-nihao: out of lesson order", errors)


if __name__ == "__main__":
    unittest.main()
