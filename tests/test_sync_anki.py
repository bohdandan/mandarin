import unittest
from unittest.mock import Mock

from scripts.sync_anki import (
    ANKI_FIELDS,
    build_anki_note,
    deck_name_for_entry,
    duplicate_query,
    equivalent_tags,
    mandarin_vocabulary_css,
    mandarin_vocabulary_templates,
    match_stale_note,
    ordered_card_ids_for_entries,
    resolve_sound_ref,
)
from scripts.vocabulary import strip_html


class SyncAnkiTest(unittest.TestCase):
    def test_equivalent_tags_ignores_anki_tag_order(self):
        self.assertTrue(equivalent_tags(["ADDED-2026", "CUSTOM", "HSK3"], ["HSK3", "CUSTOM", "ADDED-2026"]))
        self.assertFalse(equivalent_tags(["CUSTOM", "HSK3"], ["HSK3", "CUSTOM", "ADDED-2026"]))

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
            "sentence_translation": "This is my watch.",
            "hsk_level": 2,
            "source": "hsk-2",
            "lesson": "HSK:2.08",
            "notes": "",
            "created_at": "2026-04-19",
            "updated_at": "2026-04-19",
        }

        note = build_anki_note(
            entry,
            model_name="Mandarin Vocabulary",
            sound_ref="[sound:watch.mp3]",
            example_sound_ref="[sound:sentence.mp3]",
        )

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
                "Sentence Pinyin",
                "Sentence Translation",
                "Example Sound",
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
        self.assertEqual(note["fields"]["Sentence Pinyin"], "zhè shì wǒ de shǒu biǎo")
        self.assertEqual(note["fields"]["Sentence Translation"], "This is my watch.")
        self.assertEqual(note["fields"]["Example Sound"], "[sound:sentence.mp3]")
        self.assertEqual(note["fields"]["Silhouette"], "_ _")
        self.assertEqual(note["fields"]["Sound"], "[sound:watch.mp3]")
        self.assertEqual(note["tags"], ["HSK2", "HSK2::HSK:2.08"])

    def test_deck_name_routes_hsk_and_custom_entries_into_hsk30_subdecks(self):
        self.assertEqual(deck_name_for_entry({"source": "hsk-1", "hsk_level": 1}), "HSK3.0::HSK1")
        self.assertEqual(deck_name_for_entry({"source": "hsk-2", "hsk_level": 2}), "HSK3.0::HSK2")
        self.assertEqual(deck_name_for_entry({"source": "custom", "hsk_level": 4}), "HSK3.0::CUSTOM")

    def test_deck_name_routes_series_entries_to_top_level_decks(self):
        self.assertEqual(deck_name_for_entry({"source": "Pursuit of Jade", "hsk_level": 4}), "Pursuit of Jade")
        self.assertEqual(deck_name_for_entry({"source": "Scissor Seven", "hsk_level": 5}), "Scissor Seven")

    def test_builds_pursuit_of_jade_note_with_episode_tag_and_series_deck(self):
        entry = {
            "id": "pursuit-of-jade-e1-001-xiang-sheng-ban",
            "hanzi": "祥胜班",
            "pinyin": "xiáng shèng bān",
            "english": "Xiangsheng troupe",
            "example_sentence": "<b>祥胜班</b>在村里演出。",
            "hsk_level": 4,
            "source": "Pursuit of Jade",
            "lesson": "E1",
            "created_at": "2026-05-28",
            "updated_at": "2026-05-28",
        }

        note = build_anki_note(entry, model_name="Mandarin Vocabulary")

        self.assertEqual(note["deckName"], "Pursuit of Jade")
        self.assertEqual(note["tags"], ["HSK4", "poj-1"])

    def test_builds_scissor_seven_note_with_episode_tag_and_series_deck(self):
        entry = {
            "id": "scissor-seven-e1-001-ci-ke",
            "hanzi": "刺客",
            "pinyin": "cì kè",
            "english": "assassin; killer",
            "example_sentence": "我们去做<b>刺客</b>吧。",
            "hsk_level": 5,
            "source": "Scissor Seven",
            "lesson": "S1E1",
            "created_at": "2026-05-28",
            "updated_at": "2026-05-28",
        }

        note = build_anki_note(entry, model_name="Mandarin Vocabulary")

        self.assertEqual(note["deckName"], "Scissor Seven")
        self.assertEqual(note["tags"], ["HSK5", "ss-s1-e1"])

    def test_duplicate_query_uses_stable_vocabulary_id(self):
        query = duplicate_query("hsk2-0200-shou-biao", model_name="Mandarin Vocabulary")

        self.assertEqual(query, 'note:"Mandarin Vocabulary" "Vocabulary ID:hsk2-0200-shou-biao"')

    def test_match_stale_note_preserves_unique_word_when_source_ownership_changes(self):
        stale_note = {"noteId": 42, "fields": {"Hanzi": {"value": "啤酒"}}}

        matched = match_stale_note(
            {"id": "hsk3-0001-pijiu", "hanzi": "啤酒"},
            desired_hanzi_counts={"啤酒": 1},
            stale_notes_by_hanzi={"啤酒": [stale_note]},
        )

        self.assertEqual(matched, stale_note)

    def test_match_stale_note_avoids_ambiguous_cross_source_words(self):
        stale_note = {"noteId": 42, "fields": {"Hanzi": {"value": "病人"}}}

        matched = match_stale_note(
            {"id": "hsk3-0001-bingren", "hanzi": "病人"},
            desired_hanzi_counts={"病人": 2},
            stale_notes_by_hanzi={"病人": [stale_note]},
        )

        self.assertIsNone(matched)

    def test_ordered_card_ids_follow_entry_order_and_card_order(self):
        entries = [
            {"id": "scissor-seven-e1-001-ren-wu"},
            {"id": "scissor-seven-e1-002-huai-ren"},
        ]
        notes_by_id = {
            "scissor-seven-e1-002-huai-ren": {"cards": [22, 21]},
            "scissor-seven-e1-001-ren-wu": {"cards": [12, 11]},
        }

        card_ids = ordered_card_ids_for_entries(entries, notes_by_id)

        self.assertEqual(card_ids, [11, 12, 21, 22])

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
        self.assertIn("{{#Sentence Pinyin}}", recall_back)
        self.assertIn("{{Sentence Pinyin}}", recall_back)
        self.assertIn("{{#Sentence Translation}}", recall_back)
        self.assertIn("{{Sentence Translation}}", recall_back)
        self.assertIn("{{Example Sound}}", recall_back)
        self.assertIn("{{Sound}}", recall_back)

    def test_templates_label_word_and_example_audio_controls(self):
        templates = mandarin_vocabulary_templates()

        recognition_front = templates["Recognition"]["Front"]
        recognition_back = templates["Recognition"]["Back"]
        recall_back = templates["Recall"]["Back"]

        self.assertIn('class="audio-control word-audio"', recognition_front)
        self.assertIn('aria-label="Word audio"', recognition_front)
        self.assertIn('<span class="audio-label">Word</span>', recognition_front)
        self.assertIn('class="card-actions"', recognition_front)
        self.assertIn('class="audio-control word-audio"', recognition_back)
        self.assertIn('class="card-actions"', recognition_back)
        self.assertIn('class="audio-control example-audio"', recognition_back)
        self.assertIn('aria-label="Example sentence audio"', recognition_back)
        self.assertIn('<span class="audio-label">Example</span>', recognition_back)
        self.assertIn('class="example-block"', recognition_back)
        self.assertIn('class="audio-control word-audio"', recall_back)
        self.assertIn('class="card-actions"', recall_back)
        self.assertIn('class="audio-control example-audio"', recall_back)
        self.assertIn('class="example-block"', recall_back)

    def test_css_uses_tighter_top_and_divider_spacing_with_mobile_fallback(self):
        css = mandarin_vocabulary_css()

        self.assertIn("padding: 16px 20px 18px;", css)
        self.assertIn("margin-top: 8px;", css)
        self.assertIn("margin: 14px 0;", css)
        self.assertIn("justify-content: flex-start;", css)
        self.assertIn("@media (max-width: 600px)", css)
        self.assertIn("padding: 10px 14px 14px;", css)
        self.assertIn("margin: 10px 0;", css)

    def test_css_styles_labeled_audio_controls(self):
        css = mandarin_vocabulary_css()

        self.assertIn(".audio-control", css)
        self.assertIn(".audio-label", css)
        self.assertIn("grid-template-columns: auto auto;", css)
        self.assertIn("border: 1px solid", css)
        self.assertIn(".example-audio", css)
        self.assertIn(".example-block", css)
        self.assertIn(".example-sound-row", css)
        self.assertIn("background: rgba(98, 114, 164, 0.08);", css)
        self.assertIn("border-left: 3px solid rgba(255, 184, 108, 0.65);", css)
        self.assertIn("background: rgba(98, 114, 164, 0.08);\n  text-align: center;", css)
        self.assertIn(".example-block {\n    padding: 10px 10px 12px;\n    text-align: left;", css)

    def test_css_keeps_word_audio_in_bottom_action_row_without_overlay(self):
        css = mandarin_vocabulary_css()

        self.assertIn(".card-actions", css)
        self.assertIn("justify-content: center;", css)
        self.assertIn("margin-top: 10px;", css)
        self.assertIn("margin-bottom: 0;", css)
        self.assertIn("order: 98;", css)
        self.assertIn("justify-content: flex-end;", css)
        self.assertIn("margin-top: auto;", css)
        self.assertIn("margin-bottom: 8px;", css)
        self.assertIn("min-height: calc(100vh - 190px);", css)
        self.assertIn("min-height: calc(100dvh - 190px);", css)
        self.assertIn(".card-content {", css)
        self.assertIn("order: 99;", css)
        self.assertIn("margin-top: 8px;", css)
        self.assertIn(".example-sound-row {", css)
        self.assertNotIn("position: fixed;", css)

    def test_css_makes_written_chinese_link_large_tap_target(self):
        css = mandarin_vocabulary_css()

        self.assertIn("display: inline-flex;", css)
        self.assertIn("min-width: 44px;", css)
        self.assertIn("min-height: 44px;", css)
        self.assertIn("font-size: 22px;", css)


if __name__ == "__main__":
    unittest.main()
