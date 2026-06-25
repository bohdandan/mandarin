from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.chinese_support import (
    build_display_tone_fields,
    bulk_latin_guide_syllables,
    is_generated_tag,
    silhouette_text,
    written_chinese_footer_html,
    written_chinese_footer_placeholder_html,
)
from scripts.google_tts import load_google_tts_config, synthesize_audio, synthesize_text_audio
from scripts.vocabulary import derive_tags, pinyin_slug, read_source_vocabulary, read_vocabulary, strip_html


ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DEFAULT_DECK_PREFIX = "HSK3.0"
DEFAULT_MODEL = "Mandarin Vocabulary"
DEFAULT_GOOGLE_TTS_VOICE = "cmn-CN-Wavenet-C"
LEGACY_MODEL = "Chinese (Advanced)"
LEGACY_DECKS = ("HSK [Chinese Support]::HSK1-4", "HSK [Chinese Support]::Custom")

ANKI_FIELDS = [
    "Vocabulary ID",
    "Hanzi",
    "Color",
    "Pinyin",
    "English",
    "Example Sentence",
    "Sentence Pinyin",
    "Sentence Translation",
    "Example Sound",
    "Example Audio Key",
    "Silhouette",
    "Sound",
]

OBSOLETE_ANKI_FIELDS = [
]


def anki_tags(entry: dict[str, Any]) -> list[str]:
    return derive_tags(entry)


def equivalent_tags(current_tags: list[str], desired_tags: list[str]) -> bool:
    return set(current_tags) == set(desired_tags)


def deck_name_for_entry(entry: dict[str, Any], deck_prefix: str = DEFAULT_DECK_PREFIX) -> str:
    source = str(entry.get("source") or "")
    if source == "custom":
        return f"{deck_prefix}::CUSTOM"
    if source == "Pursuit of Jade":
        return "Pursuit of Jade"
    if source == "Scissor Seven":
        return "Scissor Seven"

    hsk_level = entry.get("hsk_level")
    if isinstance(hsk_level, int):
        return f"{deck_prefix}::HSK{hsk_level}"

    return deck_prefix


def entry_fields(
    entry: dict[str, Any],
    sound_ref: str = "",
    example_sound_ref: str = "",
    *,
    guide_syllables: list[str] | None = None,
) -> dict[str, str]:
    tone_fields = build_display_tone_fields(
        str(entry.get("hanzi") or ""),
        str(entry.get("pinyin") or ""),
        guide_syllables=guide_syllables,
    )
    return {
        "Vocabulary ID": str(entry.get("id") or ""),
        "Hanzi": str(entry.get("hanzi") or ""),
        "Color": tone_fields["Color"],
        "Pinyin": tone_fields["Pinyin"],
        "English": str(entry.get("english") or ""),
        "Example Sentence": str(entry.get("example_sentence") or ""),
        "Sentence Pinyin": str(entry.get("sentence_pinyin") or ""),
        "Sentence Translation": str(entry.get("sentence_translation") or ""),
        "Example Sound": example_sound_ref,
        "Example Audio Key": example_audio_key(entry),
        "Silhouette": silhouette_text(str(entry.get("hanzi") or "")),
        "Sound": sound_ref,
    }


def build_anki_note(
    entry: dict[str, Any],
    model_name: str,
    deck_prefix: str = DEFAULT_DECK_PREFIX,
    sound_ref: str = "",
    example_sound_ref: str = "",
    *,
    guide_syllables: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "deckName": deck_name_for_entry(entry, deck_prefix=deck_prefix),
        "modelName": model_name,
        "fields": entry_fields(
            entry,
            sound_ref=sound_ref,
            example_sound_ref=example_sound_ref,
            guide_syllables=guide_syllables,
        ),
        "tags": anki_tags(entry),
        "options": {"allowDuplicate": False, "duplicateScope": "deck"},
    }


def generate_sound_ref(entry: dict[str, Any], config: Any) -> str:
    filename, audio_bytes = synthesize_audio(entry, config)
    payload = base64.b64encode(audio_bytes).decode("ascii")
    invoke_anki("storeMediaFile", {"filename": filename, "data": payload})
    return f"[sound:{filename}]"


def generate_example_sound_ref(entry: dict[str, Any], config: Any) -> str:
    example_sentence = strip_html(str(entry.get("example_sentence") or ""))
    if not example_sentence:
        return ""
    filename, audio_bytes = synthesize_text_audio(f"{entry['id']}_example", example_sentence, config)
    payload = base64.b64encode(audio_bytes).decode("ascii")
    invoke_anki("storeMediaFile", {"filename": filename, "data": payload})
    return f"[sound:{filename}]"


def example_audio_key(entry: dict[str, Any]) -> str:
    example_sentence = strip_html(str(entry.get("example_sentence") or "")).strip()
    if not example_sentence:
        return ""
    return hashlib.sha1(example_sentence.encode("utf-8")).hexdigest()[:16]


def resolve_sound_ref(
    entry: dict[str, Any],
    current_sound: str,
    sound_generator: Any,
) -> str:
    if str(current_sound or "").strip():
        return current_sound
    return sound_generator(entry)


def resolve_example_sound_ref(
    entry: dict[str, Any],
    current_sound: str,
    current_audio_key: str,
    sound_generator: Any,
    *,
    force_refresh: bool = False,
) -> str:
    if not str(entry.get("example_sentence") or "").strip():
        return ""
    desired_audio_key = example_audio_key(entry)
    if force_refresh or (current_audio_key and current_audio_key != desired_audio_key):
        return sound_generator(entry)
    if str(current_sound or "").strip():
        return current_sound
    return sound_generator(entry)


def duplicate_query(vocabulary_id: str, model_name: str) -> str:
    return f'note:"{model_name}" "Vocabulary ID:{vocabulary_id}"'


def invoke_anki(action: str, params: dict[str, Any] | None = None) -> Any:
    payload = json.dumps({"action": action, "version": 6, "params": params or {}}).encode("utf-8")
    request = urllib.request.Request(ANKI_CONNECT_URL, payload, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result.get("result")


def flush_actions(pending_actions: list[dict[str, Any]]) -> None:
    if not pending_actions:
        return
    invoke_anki("multi", {"actions": pending_actions})
    pending_actions.clear()


def normalize_generated_tag_case() -> None:
    for tag in invoke_anki("getTags"):
        if not is_generated_tag(tag):
            continue
        upper = tag.upper()
        if tag == upper:
            continue
        invoke_anki("replaceTagsInAllNotes", {"tag_to_replace": tag, "replace_with_tag": upper})
    invoke_anki("clearUnusedTags")


def ensure_deck(deck_name: str) -> None:
    invoke_anki("createDeck", {"deck": deck_name})


def mandarin_vocabulary_css() -> str:
    return """
.card {
  font-family: Arial, sans-serif;
  font-size: 20px;
  line-height: 1.6;
  text-align: center;
  padding: 16px 20px 18px;
  min-height: 360px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.card { background-color: #f8f8f2; color: #282a36; }
.night_mode .card { background-color: #282a36; color: #f8f8f2; }

.top {
  margin-top: 8px;
}

.divider {
  margin: 14px 0;
  opacity: 0.2;
}

.chinese {
  font-size: 56px;
  margin: 20px 0;
  color: #6c757d;
  line-height: 1.2;
}
.night_mode .chinese { color: #6272a4; }

.pinyin {
  font-size: 18px;
  color: #8be9fd;
  margin-bottom: 8px;
}
.night_mode .pinyin { color: #50fa7b; }

.english,
.comment {
  font-size: 18px;
  line-height: 1.6;
}

.meaning-block {
  margin: 18px 0;
}

.english {
  margin-bottom: 18px;
  font-weight: 500;
}

.comment {
  color: #6272a4;
  margin-top: 12px;
}

.example-block {
  margin-top: 14px;
  padding: 10px 12px 12px;
  border-left: 3px solid rgba(255, 184, 108, 0.65);
  border-radius: 6px;
  background: rgba(98, 114, 164, 0.08);
  text-align: center;
}

.example-block .comment {
  margin-top: 0;
}

.example-sound-row {
  display: flex;
  justify-content: center;
}

.sentence-pinyin,
.sentence-translation {
  font-size: 16px;
  line-height: 1.45;
  margin-top: 8px;
  opacity: 0.82;
}

.sentence-translation {
  color: #6c757d;
}

.night_mode .sentence-translation {
  color: #6272a4;
}

.tags {
  font-size: 9pt;
  opacity: 0.6;
  margin-top: 0;
}

.sound { margin-top: 10px; }

.audio-control {
  display: inline-grid;
  grid-template-columns: auto auto;
  gap: 8px;
  align-items: center;
  justify-content: center;
  margin-top: 10px;
  padding: 4px 10px;
  border: 1px solid rgba(108, 117, 125, 0.35);
  border-radius: 999px;
}

.audio-control .sound {
  margin-top: 0;
  line-height: 1;
}

.audio-label {
  font-size: 12px;
  line-height: 1;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #6c757d;
}

.word-audio .audio-label {
  color: #0077b6;
}

.example-audio {
  margin-top: 14px;
}

.example-audio .audio-label {
  color: #c05600;
}

.night_mode .audio-control {
  border-color: rgba(248, 248, 242, 0.28);
}

.night_mode .audio-label {
  color: #f8f8f2;
}

.night_mode .word-audio .audio-label {
  color: #8be9fd;
}

.night_mode .example-audio .audio-label {
  color: #ffb86c;
}

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.card-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 10px;
  margin-bottom: 0;
}

.tone1 { color: #0077b6; }
.tone2 { color: #2b9348; }
.tone3 { color: #c05600; }
.tone4 { color: #b00020; }
.tone5 { color: #6c757d; }

.night_mode .tone1 { color: #8be9fd; }
.night_mode .tone2 { color: #50fa7b; }
.night_mode .tone3 { color: #ffb86c; }
.night_mode .tone4 { color: #ff5555; }
.night_mode .tone5 { color: #6272a4; }

.meta-row {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 10px;
}

.meta-row .tags {
  flex: 1;
  margin-top: 0;
  text-align: left;
  font-size: 8.5pt;
  opacity: 0.55;
}

.written-chinese-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  color: #6c757d;
  text-decoration: none;
  font-size: 22px;
  line-height: 1;
  opacity: 0.85;
}

.night_mode .written-chinese-link {
  color: #6272a4;
}

.written-chinese-link:hover,
.written-chinese-link:focus {
  opacity: 1;
}

.written-chinese-placeholder {
  visibility: hidden;
  display: inline-flex;
  min-width: 44px;
  min-height: 44px;
  font-size: 22px;
  line-height: 1;
}

@media (max-width: 600px) {
  .card {
    padding: 10px 14px 14px;
    min-height: calc(100vh - 190px);
    min-height: calc(100dvh - 190px);
  }

  .card-content {
    min-height: calc(100vh - 190px);
    min-height: calc(100dvh - 190px);
  }

  .top {
    margin-top: 2px;
  }

  .divider {
    margin: 10px 0;
  }

  .meaning-block {
    margin: 12px 0;
  }

  .example-block {
    padding: 10px 10px 12px;
    text-align: left;
  }

  .example-sound-row {
    justify-content: flex-end;
  }

  .meta-row {
    order: 99;
    margin-top: 8px;
    padding-top: 8px;
  }

  .card-actions {
    order: 98;
    justify-content: flex-end;
    margin-top: auto;
    margin-bottom: 8px;
  }
}
""".strip()


def mandarin_vocabulary_templates() -> dict[str, dict[str, str]]:
    placeholder_footer = written_chinese_footer_placeholder_html()
    back_footer = written_chinese_footer_html()
    word_audio = """
<div class="audio-control word-audio" aria-label="Word audio">
  <span class="audio-label">Word</span>
  <div class="sound">{{Sound}}</div>
</div>
""".strip()
    example_audio = """
<div class="audio-control example-audio" aria-label="Example sentence audio">
  <span class="audio-label">Example</span>
  <div class="sound">{{Example Sound}}</div>
</div>
""".strip()
    return {
        "Recognition": {
            "Front": f"""
<div class="card-content">
  <div class="top">
    <div class="pinyin">&nbsp;</div>
    <span class="chinese">{{{{Hanzi}}}}</span>
  </div>

  <hr class="divider">
  <div class="card-actions">{word_audio}</div>
  {placeholder_footer}
</div>
""".strip(),
            "Back": f"""
<div class="card-content">
  <div class="top">
    <div class="pinyin">{{{{Pinyin}}}}</div>
    <div class="chinese">{{{{Color}}}}</div>
  </div>

  <hr class="divider">

  <div class="meaning-block">
    <div class="english">{{{{English}}}}</div>

    {{{{#Example Sentence}}}}
    <div class="example-block">
      <div class="comment">{{{{Example Sentence}}}}</div>
      <div class="example-sound-row">{example_audio}</div>
      {{{{#Sentence Pinyin}}}}
      <div class="sentence-pinyin">{{{{Sentence Pinyin}}}}</div>
      {{{{/Sentence Pinyin}}}}
      {{{{#Sentence Translation}}}}
      <div class="sentence-translation">{{{{Sentence Translation}}}}</div>
      {{{{/Sentence Translation}}}}
    </div>
    {{{{/Example Sentence}}}}
  </div>
  <div class="card-actions">{word_audio}</div>
  {back_footer}
</div>
""".strip(),
        },
        "Recall": {
            "Front": f"""
<div class="card-content">
  <div class="top">
    <div class="english prompt">{{{{English}}}}</div>
  </div>

  <hr class="divider">

  <div class="meaning-block">
    <div class="pinyin">&nbsp;</div>
    <div class="chinese">{{{{Silhouette}}}}</div>
  </div>
  {placeholder_footer}
</div>
""".strip(),
            "Back": f"""
<div class="card-content">
  <div class="top">
    <div class="english">{{{{English}}}}</div>
  </div>

  <hr class="divider">

  <div class="meaning-block">
    <div class="pinyin">{{{{Pinyin}}}}</div>
    <div class="chinese">{{{{Color}}}}</div>
    {{{{#Example Sentence}}}}
    <div class="example-block">
      <div class="comment">{{{{Example Sentence}}}}</div>
      <div class="example-sound-row">{example_audio}</div>
      {{{{#Sentence Pinyin}}}}
      <div class="sentence-pinyin">{{{{Sentence Pinyin}}}}</div>
      {{{{/Sentence Pinyin}}}}
      {{{{#Sentence Translation}}}}
      <div class="sentence-translation">{{{{Sentence Translation}}}}</div>
      {{{{/Sentence Translation}}}}
    </div>
    {{{{/Example Sentence}}}}
  </div>

  <div class="card-actions">{word_audio}</div>
  {back_footer}
</div>
""".strip(),
        },
    }


def ensure_model(model_name: str) -> None:
    existing = invoke_anki("modelNames")
    templates = mandarin_vocabulary_templates()
    css = mandarin_vocabulary_css()
    if model_name not in existing:
        invoke_anki(
            "createModel",
            {
                "modelName": model_name,
                "inOrderFields": ANKI_FIELDS,
                "css": css,
                "cardTemplates": [
                    {"Name": name, "Front": template["Front"], "Back": template["Back"]}
                    for name, template in templates.items()
                ],
            },
        )
        return

    for index, field_name in enumerate(ANKI_FIELDS):
        invoke_anki("modelFieldAdd", {"modelName": model_name, "fieldName": field_name, "index": index})

    existing_fields = invoke_anki("modelFieldNames", {"modelName": model_name})
    for field_name in OBSOLETE_ANKI_FIELDS:
        if field_name in existing_fields:
            invoke_anki("modelFieldRemove", {"modelName": model_name, "fieldName": field_name})

    invoke_anki("updateModelTemplates", {"model": {"name": model_name, "templates": templates}})
    invoke_anki("updateModelStyling", {"model": {"name": model_name, "css": css}})


def model_note_infos(model_name: str) -> list[dict[str, Any]]:
    note_ids = invoke_anki("findNotes", {"query": f'note:"{model_name}"'})
    if not note_ids:
        return []
    return invoke_anki("notesInfo", {"notes": note_ids})


def legacy_note_infos() -> list[dict[str, Any]]:
    note_ids: list[int] = []
    for deck_name in LEGACY_DECKS:
        note_ids.extend(invoke_anki("findNotes", {"query": f'deck:"{deck_name}" note:"{LEGACY_MODEL}"'}))
    if not note_ids:
        return []
    return invoke_anki("notesInfo", {"notes": sorted(set(note_ids))})


def note_field_value(note: dict[str, Any], field_name: str) -> str:
    return str(note.get("fields", {}).get(field_name, {}).get("value") or "")


def normalize_legacy_pinyin(value: str) -> str:
    return pinyin_slug(strip_html(value).split("/", 1)[0])


def legacy_example_sentence(note: dict[str, Any]) -> str:
    return note_field_value(note, "Also Written") or note_field_value(note, "Example Sentence")


def legacy_custom_index(notes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        note_field_value(note, "Hanzi"): note
        for note in notes
        if "CUSTOM" in note.get("tags", [])
    }


def legacy_hsk_index(notes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    for note in notes:
        hanzi = note_field_value(note, "Hanzi")
        if hanzi:
            indexed.setdefault(hanzi, []).append(note)
    return indexed


def match_legacy_note(
    entry: dict[str, Any],
    *,
    custom_notes_by_hanzi: dict[str, dict[str, Any]],
    hsk_notes_by_hanzi: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    hanzi = str(entry.get("hanzi") or "")
    if str(entry.get("source") or "") == "custom":
        return custom_notes_by_hanzi.get(hanzi)

    candidates = [
        note
        for note in hsk_notes_by_hanzi.get(hanzi, [])
        if f'HSK{entry.get("hsk_level")}' in note.get("tags", [])
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    target_pinyin = pinyin_slug(str(entry.get("pinyin") or "").split("/", 1)[0])
    pinyin_matches = [note for note in candidates if normalize_legacy_pinyin(note_field_value(note, "Pinyin")) == target_pinyin]
    if len(pinyin_matches) == 1:
        return pinyin_matches[0]

    target_english = str(entry.get("english") or "").strip().lower()
    english_matches = [note for note in candidates if note_field_value(note, "English").strip().lower() == target_english]
    if len(english_matches) == 1:
        return english_matches[0]

    return None


def match_stale_note(
    entry: dict[str, Any],
    *,
    desired_hanzi_counts: dict[str, int],
    stale_notes_by_hanzi: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    hanzi = str(entry.get("hanzi") or "")
    candidates = stale_notes_by_hanzi.get(hanzi, [])
    if desired_hanzi_counts.get(hanzi) == 1 and len(candidates) == 1:
        return candidates[0]
    return None


def ordered_card_ids_for_entries(entries: list[dict[str, Any]], notes_by_vocabulary_id: dict[str, dict[str, Any]]) -> list[int]:
    ordered_card_ids: list[int] = []
    for entry in entries:
        note = notes_by_vocabulary_id.get(str(entry.get("id") or ""))
        if not note:
            continue
        ordered_card_ids.extend(sorted(int(card_id) for card_id in note.get("cards", [])))
    return ordered_card_ids


def supported_reposition_action() -> str | None:
    try:
        reflected = invoke_anki("apiReflect", {"scopes": ["actions"], "actions": ["repositionNewCards", "repositionCards"]})
    except RuntimeError:
        return None
    actions = set(reflected.get("actions", []))
    if "repositionNewCards" in actions:
        return "repositionNewCards"
    if "repositionCards" in actions:
        return "repositionCards"
    return None


def reposition_new_cards(entries: list[dict[str, Any]], notes_by_vocabulary_id: dict[str, dict[str, Any]]) -> None:
    action = supported_reposition_action()
    if action is None:
        print(
            "WARNING: AnkiConnect does not support new-card repositioning; source JSON remains ordered for future imports.",
            file=sys.stderr,
        )
        return

    entries_by_deck: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        entries_by_deck.setdefault(deck_name_for_entry(entry), []).append(entry)

    for deck_entries in entries_by_deck.values():
        card_ids = ordered_card_ids_for_entries(deck_entries, notes_by_vocabulary_id)
        if not card_ids:
            continue
        invoke_anki(
            action,
            {
                "cards": card_ids,
                "startingFrom": 1,
                "step": 1,
                "randomize": False,
                "shiftPositionOfExistingCards": True,
            },
        )


def sync_entries(
    entries: list[dict[str, Any]],
    deck_name: str,
    model_name: str,
    dry_run: bool = False,
    refresh_example_audio_ids: set[str] | None = None,
) -> dict[str, int]:
    del deck_name
    summary = {"added": 0, "migrated": 0, "updated": 0, "unchanged": 0}
    pending_actions: list[dict[str, Any]] = []
    refresh_example_audio_ids = refresh_example_audio_ids or set()
    guide_map = bulk_latin_guide_syllables([str(entry.get("hanzi") or "") for entry in entries])
    desired_ids = {str(entry["id"]) for entry in entries}
    desired_hanzi_counts: dict[str, int] = {}
    for entry in entries:
        hanzi = str(entry.get("hanzi") or "")
        desired_hanzi_counts[hanzi] = desired_hanzi_counts.get(hanzi, 0) + 1
    tts_config: Any | None = None

    def custom_sound_generator(entry: dict[str, Any]) -> str:
        nonlocal tts_config
        if tts_config is None:
            env = dict(os.environ)
            env.setdefault("GOOGLE_TTS_VOICE_NAME", DEFAULT_GOOGLE_TTS_VOICE)
            tts_config = load_google_tts_config(env)
        return generate_sound_ref(entry, tts_config)

    def example_sound_generator(entry: dict[str, Any]) -> str:
        nonlocal tts_config
        if tts_config is None:
            env = dict(os.environ)
            env.setdefault("GOOGLE_TTS_VOICE_NAME", DEFAULT_GOOGLE_TTS_VOICE)
            tts_config = load_google_tts_config(env)
        return generate_example_sound_ref(entry, tts_config)

    if not dry_run:
        ensure_model(model_name)
        for entry in entries:
            ensure_deck(deck_name_for_entry(entry))
        current_notes = model_note_infos(model_name)
        existing_notes = {note_field_value(note, "Vocabulary ID"): note for note in current_notes}
        stale_notes_by_hanzi: dict[str, list[dict[str, Any]]] = {}
        for note in current_notes:
            if note_field_value(note, "Vocabulary ID") not in desired_ids:
                stale_notes_by_hanzi.setdefault(note_field_value(note, "Hanzi"), []).append(note)
        if len(existing_notes) < len(entries):
            legacy_notes = legacy_note_infos()
        else:
            legacy_notes = []
        custom_notes_by_hanzi = legacy_custom_index(legacy_notes)
        hsk_notes_by_hanzi = legacy_hsk_index(legacy_notes)
    else:
        existing_notes = {}
        stale_notes_by_hanzi = {}
        custom_notes_by_hanzi = {}
        hsk_notes_by_hanzi = {}

    for entry in entries:
        entry_id = str(entry["id"])
        target_deck = deck_name_for_entry(entry)
        existing = existing_notes.get(entry_id)

        if existing is not None:
            desired_tags = anki_tags(entry)
            current_fields = {field_name: note_field_value(existing, field_name) for field_name in ANKI_FIELDS}
            existing_example = note_field_value(existing, "Example Sentence")
            enriched_entry = dict(entry)
            if not enriched_entry.get("example_sentence") and existing_example:
                enriched_entry["example_sentence"] = existing_example
            resolved_sound = resolve_sound_ref(entry, note_field_value(existing, "Sound"), custom_sound_generator)
            resolved_example_sound = resolve_example_sound_ref(
                enriched_entry,
                note_field_value(existing, "Example Sound"),
                note_field_value(existing, "Example Audio Key"),
                example_sound_generator,
                force_refresh=entry_id in refresh_example_audio_ids,
            )
            desired_fields = entry_fields(
                enriched_entry,
                sound_ref=resolved_sound,
                example_sound_ref=resolved_example_sound,
                guide_syllables=guide_map.get(str(entry.get("hanzi") or "")),
            )
            if current_fields == desired_fields and equivalent_tags(existing.get("tags", []), desired_tags):
                summary["unchanged"] += 1
            else:
                summary["updated"] += 1
                if not dry_run:
                    pending_actions.append({"action": "updateNoteFields", "params": {"note": {"id": existing["noteId"], "fields": desired_fields}}})
                    pending_actions.append({"action": "updateNoteTags", "params": {"note": existing["noteId"], "tags": desired_tags}})
            if not dry_run and str(entry.get("source") or "") in {"Pursuit of Jade", "Scissor Seven"} and existing.get("cards"):
                pending_actions.append({"action": "changeDeck", "params": {"cards": existing["cards"], "deck": target_deck}})
            if not dry_run and len(pending_actions) >= 150:
                flush_actions(pending_actions)
            continue

        stale = match_stale_note(
            entry,
            desired_hanzi_counts=desired_hanzi_counts,
            stale_notes_by_hanzi=stale_notes_by_hanzi,
        )
        if stale is not None:
            summary["migrated"] += 1
            if not dry_run:
                resolved_sound = resolve_sound_ref(entry, note_field_value(stale, "Sound"), custom_sound_generator)
                resolved_example_sound = resolve_example_sound_ref(
                    entry,
                    note_field_value(stale, "Example Sound"),
                    note_field_value(stale, "Example Audio Key"),
                    example_sound_generator,
                    force_refresh=entry_id in refresh_example_audio_ids,
                )
                pending_actions.append(
                    {
                        "action": "updateNoteFields",
                        "params": {
                            "note": {
                                "id": stale["noteId"],
                                "fields": entry_fields(
                                    entry,
                                    sound_ref=resolved_sound,
                                    example_sound_ref=resolved_example_sound,
                                    guide_syllables=guide_map.get(str(entry.get("hanzi") or "")),
                                ),
                            }
                        },
                    }
                )
                pending_actions.append({"action": "updateNoteTags", "params": {"note": stale["noteId"], "tags": anki_tags(entry)}})
                if stale.get("cards"):
                    pending_actions.append({"action": "changeDeck", "params": {"cards": stale["cards"], "deck": target_deck}})
                stale_notes_by_hanzi[str(entry.get("hanzi") or "")].remove(stale)
                if len(pending_actions) >= 120:
                    flush_actions(pending_actions)
            continue

        legacy = match_legacy_note(
            entry,
            custom_notes_by_hanzi=custom_notes_by_hanzi,
            hsk_notes_by_hanzi=hsk_notes_by_hanzi,
        )
        if legacy is not None:
            summary["migrated"] += 1
            if not dry_run:
                enriched_entry = dict(entry)
                if not enriched_entry.get("example_sentence"):
                    enriched_entry["example_sentence"] = legacy_example_sentence(legacy)
                resolved_example_sound = resolve_example_sound_ref(
                    enriched_entry,
                    note_field_value(legacy, "Example Sound"),
                    note_field_value(legacy, "Example Audio Key"),
                    example_sound_generator,
                    force_refresh=entry_id in refresh_example_audio_ids,
                )
                pending_actions.append(
                    {
                        "action": "updateNoteModel",
                        "params": {
                            "note": {
                                "id": legacy["noteId"],
                                "modelName": model_name,
                                "fields": entry_fields(
                                    enriched_entry,
                                    sound_ref=resolve_sound_ref(entry, note_field_value(legacy, "Sound"), custom_sound_generator),
                                    example_sound_ref=resolved_example_sound,
                                    guide_syllables=guide_map.get(str(entry.get("hanzi") or "")),
                                ),
                                "tags": anki_tags(entry),
                            }
                        },
                    }
                )
                if legacy.get("cards"):
                    pending_actions.append({"action": "changeDeck", "params": {"cards": legacy["cards"], "deck": target_deck}})
                if len(pending_actions) >= 120:
                    flush_actions(pending_actions)
            continue

        summary["added"] += 1
        if not dry_run:
            flush_actions(pending_actions)
            invoke_anki(
                "addNote",
                {
                    "note": build_anki_note(
                        entry,
                        model_name=model_name,
                        sound_ref=resolve_sound_ref(entry, "", custom_sound_generator),
                        example_sound_ref=resolve_example_sound_ref(
                            entry,
                            "",
                            "",
                            example_sound_generator,
                            force_refresh=entry_id in refresh_example_audio_ids,
                        ),
                        guide_syllables=guide_map.get(str(entry.get("hanzi") or "")),
                    )
                },
            )

    if not dry_run:
        flush_actions(pending_actions)
        current_notes = model_note_infos(model_name)
        notes_by_vocabulary_id = {note_field_value(note, "Vocabulary ID"): note for note in current_notes}
        reposition_new_cards(entries, notes_by_vocabulary_id)
        normalize_generated_tag_case()
    return summary


def write_sync_log(summary: dict[str, int], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Anki Sync", "", *[f"- {key}: {value}" for key, value in summary.items()]]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_refresh_example_audio_ids(path: Path | None) -> set[str]:
    if path is None:
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync canonical vocabulary data to Anki through AnkiConnect.")
    parser.add_argument("--data", type=Path, default=Path("data/sources"))
    parser.add_argument("--deck", default=DEFAULT_DECK_PREFIX)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log", type=Path, default=Path("logs/sync/latest.md"))
    parser.add_argument(
        "--refresh-example-audio-ids",
        type=Path,
        help="Path to a newline-delimited list of vocabulary ids whose example sentence audio should be regenerated.",
    )
    args = parser.parse_args()

    entries = read_source_vocabulary(args.data) if args.data.is_dir() else read_vocabulary(args.data)
    summary = sync_entries(
        entries,
        deck_name=args.deck,
        model_name=args.model,
        dry_run=args.dry_run,
        refresh_example_audio_ids=read_refresh_example_audio_ids(args.refresh_example_audio_ids),
    )
    write_sync_log(summary, args.log)
    print(f"Anki sync summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
