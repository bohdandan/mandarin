import unittest
from unittest.mock import Mock

from scripts.sync_anki import (
    ANKI_FIELDS,
    build_anki_note,
    deck_name_for_entry,
    duplicate_query,
    mandarin_vocabulary_css,
    mandarin_vocabulary_templates,
    resolve_sound_ref,
)
from scripts.vocabulary import strip_html


class SyncAnkiTest(unittest.TestCase):
    def test_resolve_sound_ref_generates_audio_for_custom_entries_without_sound(self):
        entry = {"id": "custom-word-xinwen", "hanzi": "新闻", "source": "custom"}
        generator = Mock(return_value="[sound:custom-word-xinwen_google-cmn-cn-wavenet-c.mp3]")

        sound = resolve_sound_ref(entry, "", generator)

        self.assertEqual(sound, "[sound:custom-word-xinwen_google-cmn-cn-wavenet-c.mp3]")
        generator.assert_called_once_with(entry)

    def test_resolve_sound_ref_keeps_existing_sound_for_custom_entries(self):
        entry = {"id": "custom-word-xinwen", "hanzi": "新闻", "source": "custom"}
        generator = Mock()

        sound = resolve_sound_ref(entry, "[sound:existing.mp3]", generator)

        self.assertEqual(sound, "[sound:existing.mp3]")
        generator.assert_not_called()

    def test_resolve_sound_ref_generates_audio_for_non_custom_entries_without_sound(self):
        entry = {"id": "hsk1-0001-ai", "hanzi": "爱", "source": "hsk-1"}
        generator = Mock(return_value="[sound:hsk1-0001-ai_google-cmn-cn-wavenet-c.mp3]")

        sound = resolve_sound_ref(entry, "", generator)

        self.assertEqual(sound, "[sound:hsk1-0001-ai_google-cmn-cn-wavenet-c.mp3]")
        generator.assert_called_once_with(entry)

    def test_builds_hsk_note_with_generated_display_fields_and_hsk30_deck(self):
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

        note = build_anki_note(entry, model_name="Mandarin Vocabulary", sound_ref="[sound:watch.mp3]")

        self.assertEqual(note["deckName"], "HSK3.0::HSK2")
        self.assertEqual(note["modelName"], "Mandarin Vocabulary")
        self.assertEqual(
            ANKI_FIELDS,
            [
                "Vocabulary ID",
                "Hanzi",
                "Color",
                "Pinyin",
                "English",
                "Example Sentence",
                "Silhouette",
                "Sound",
            ],
        )
        self.assertEqual(note["fields"]["Vocabulary ID"], "hsk2-0200-shou-biao")
        self.assertEqual(note["fields"]["Hanzi"], "手表")
        self.assertIn("tone3", note["fields"]["Color"])
        self.assertEqual(strip_html(note["fields"]["Pinyin"]).strip(), "shǒu biǎo")
        self.assertEqual(note["fields"]["English"], "watch")
        self.assertEqual(note["fields"]["Example Sentence"], "这是我的<b>手表</b>。")
        self.assertEqual(note["fields"]["Silhouette"], "_ _")
        self.assertEqual(note["fields"]["Sound"], "[sound:watch.mp3]")
        self.assertEqual(note["tags"], ["HSK2", "HSK2::HSK:2.08"])

    def test_deck_name_routes_hsk_and_custom_entries_into_hsk30_subdecks(self):
        self.assertEqual(deck_name_for_entry({"source": "hsk-1", "hsk_level": 1}), "HSK3.0::HSK1")
        self.assertEqual(deck_name_for_entry({"source": "hsk-2", "hsk_level": 2}), "HSK3.0::HSK2")
        self.assertEqual(deck_name_for_entry({"source": "custom", "hsk_level": 4}), "HSK3.0::CUSTOM")

    def test_duplicate_query_uses_stable_vocabulary_id(self):
        query = duplicate_query("hsk2-0200-shou-biao", model_name="Mandarin Vocabulary")

        self.assertEqual(query, 'note:"Mandarin Vocabulary" "Vocabulary ID:hsk2-0200-shou-biao"')

    def test_templates_keep_single_meta_footer_lane_on_front_and_back(self):
        templates = mandarin_vocabulary_templates()

        for card_name in ("Recognition", "Recall"):
            front = templates[card_name]["Front"]
            back = templates[card_name]["Back"]

            self.assertIn('class="meta-row"', front)
            self.assertIn('class="meta-row"', back)
            self.assertIn('class="written-chinese-placeholder"', front)
            self.assertIn('class="written-chinese-link"', back)
            self.assertNotIn('class="card-footer"', front)
            self.assertNotIn('class="card-footer"', back)

    def test_templates_keep_anki_placeholders_escaped_after_footer_injection(self):
        templates = mandarin_vocabulary_templates()

        recognition_front = templates["Recognition"]["Front"]
        recall_front = templates["Recall"]["Front"]
        recall_back = templates["Recall"]["Back"]

        self.assertIn("{{Hanzi}}", recognition_front)
        self.assertIn("{{Sound}}", recognition_front)
        self.assertIn("{{English}}", recall_front)
        self.assertIn("{{Silhouette}}", recall_front)
        self.assertIn("{{English}}", recall_back)
        self.assertIn("{{Pinyin}}", recall_back)
        self.assertIn("{{Color}}", recall_back)
        self.assertIn("{{#Example Sentence}}", recall_back)
        self.assertIn("{{Example Sentence}}", recall_back)
        self.assertIn("{{/Example Sentence}}", recall_back)
        self.assertIn("{{Sound}}", recall_back)

    def test_css_uses_tighter_top_and_divider_spacing_with_mobile_fallback(self):
        css = mandarin_vocabulary_css()

        self.assertIn("padding: 16px 20px 18px;", css)
        self.assertIn("margin-top: 8px;", css)
        self.assertIn("margin: 14px 0;", css)
        self.assertIn("justify-content: flex-start;", css)
        self.assertIn("@media (max-width: 600px)", css)
        self.assertIn("padding: 10px 14px 14px;", css)
        self.assertIn("margin: 10px 0;", css)


if __name__ == "__main__":
    unittest.main()
