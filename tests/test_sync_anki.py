import unittest

from scripts.sync_anki import build_anki_note, duplicate_query


class SyncAnkiTest(unittest.TestCase):
    def test_builds_anki_note_with_repo_owned_fields_and_tags(self):
        entry = {
            "id": "hsk2-0200-shou-biao",
            "hanzi": "手表",
            "pinyin": "shǒu biǎo",
            "english": "watch",
            "example_sentence": "这是我的<b>手表</b>。",
            "sentence_pinyin": "zhè shì wǒ de shǒu biǎo",
            "sentence_translation": "",
            "hsk_level": 2,
            "source": "hsk-2",
            "lesson": "HSK:2.08",
            "notes": "",
            "created_at": "2026-04-19",
            "updated_at": "2026-04-19",
        }

        note = build_anki_note(entry, deck_name="Mandarin", model_name="Mandarin Vocabulary")

        self.assertEqual(note["deckName"], "Mandarin")
        self.assertEqual(note["modelName"], "Mandarin Vocabulary")
        self.assertEqual(note["fields"]["Vocabulary ID"], "hsk2-0200-shou-biao")
        self.assertEqual(note["fields"]["Hanzi"], "手表")
        self.assertEqual(note["tags"], ["HSK2", "HSK2::HSK:2.08"])

    def test_duplicate_query_uses_stable_vocabulary_id(self):
        query = duplicate_query("hsk2-0200-shou-biao", model_name="Mandarin Vocabulary")

        self.assertEqual(query, 'note:"Mandarin Vocabulary" "Vocabulary ID:hsk2-0200-shou-biao"')


if __name__ == "__main__":
    unittest.main()
