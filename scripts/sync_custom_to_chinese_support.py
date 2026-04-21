from __future__ import annotations

import argparse
import base64
import subprocess
import sys
import tempfile
import urllib.error
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sync_anki import invoke_anki, normalize_generated_tag_case
from scripts.chinese_support import (
    bopomofo_syllables,
    build_chinese_advanced_fields,
    latin_guide_syllables,
    reconcile_generated_tags,
    split_marked_pinyin_by_guide,
    traditional_hanzi,
)
from scripts.vocabulary import derive_tags, pinyin_slug, read_source_vocabulary


DEFAULT_DECK = "HSK [Chinese Support]::Custom"
DEFAULT_MODEL = "Chinese (Advanced)"
DEFAULT_VOICE = "Tingting"


def generate_sound_ref(entry: dict[str, Any], voice: str) -> str:
    filename = f"{entry['id']}_{pinyin_slug(voice)}.aiff"
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as handle:
        tmp_path = Path(handle.name)
    try:
        subprocess.run(["say", "-v", voice, "-o", str(tmp_path), str(entry["hanzi"])], check=True, capture_output=True)
        payload = base64.b64encode(tmp_path.read_bytes()).decode("ascii")
        invoke_anki("storeMediaFile", {"filename": filename, "data": payload})
    finally:
        tmp_path.unlink(missing_ok=True)
    return f"[sound:{filename}]"


def repo_custom_entries(data_path: Path) -> list[dict[str, Any]]:
    return [entry for entry in read_source_vocabulary(data_path) if entry.get("source") == "custom"]


def existing_custom_notes(deck_name: str, model_name: str) -> dict[str, dict[str, Any]]:
    note_ids = invoke_anki("findNotes", {"query": f'deck:"{deck_name}" note:"{model_name}"'})
    if not note_ids:
        return {}
    notes = invoke_anki("notesInfo", {"notes": note_ids})
    return {note["fields"]["Hanzi"]["value"]: note for note in notes}


def sync_custom_deck(
    *,
    data_path: Path,
    deck_name: str,
    model_name: str,
    voice: str,
    update_existing: bool = False,
) -> dict[str, int]:
    summary = {"added": 0, "updated": 0, "unchanged": 0}
    repo_entries = repo_custom_entries(data_path)
    existing_notes = existing_custom_notes(deck_name, model_name)

    for entry in repo_entries:
        existing = existing_notes.get(str(entry["hanzi"]))
        if existing is not None and not update_existing:
            summary["unchanged"] += 1
            continue

        guide = latin_guide_syllables(str(entry["hanzi"]))
        pinyin_syllables = split_marked_pinyin_by_guide(str(entry["pinyin"]), guide)
        bopo_syllables = bopomofo_syllables(pinyin_syllables)
        sound_ref = (
            str(existing["fields"].get("Sound", {}).get("value") or "")
            if existing is not None
            else ""
        ) or generate_sound_ref(entry, voice)
        fields = build_chinese_advanced_fields(
            entry,
            pinyin_syllables=pinyin_syllables,
            bopomofo_syllables=bopo_syllables,
            traditional=traditional_hanzi(str(entry["hanzi"])),
            sound_ref=sound_ref,
        )
        tags = derive_tags(entry)
        if existing is None:
            invoke_anki(
                "addNote",
                {
                    "note": {
                        "deckName": deck_name,
                        "modelName": model_name,
                        "fields": fields,
                        "tags": tags,
                        "options": {"allowDuplicate": False, "duplicateScope": "deck"},
                    }
                },
            )
            summary["added"] += 1
            continue

        current_fields = {
            field_name: existing["fields"].get(field_name, {}).get("value", "")
            for field_name in fields
        }
        tags_to_add, tags_to_remove = reconcile_generated_tags(existing.get("tags", []), tags)
        if current_fields == fields and not tags_to_add and not tags_to_remove:
            summary["unchanged"] += 1
            continue

        if current_fields != fields:
            invoke_anki("updateNoteFields", {"note": {"id": existing["noteId"], "fields": fields}})
        if tags_to_remove:
            invoke_anki("removeTags", {"notes": [existing["noteId"]], "tags": " ".join(tags_to_remove)})
        if tags_to_add:
            invoke_anki("addTags", {"notes": [existing["noteId"]], "tags": " ".join(tags_to_add)})
        summary["updated"] += 1

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync repo custom words into the Chinese Support Custom Anki deck.")
    parser.add_argument("--data", type=Path, default=Path("data/sources"))
    parser.add_argument("--deck", default=DEFAULT_DECK)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--update-existing", action="store_true")
    args = parser.parse_args()

    try:
        summary = sync_custom_deck(
            data_path=args.data,
            deck_name=args.deck,
            model_name=args.model,
            voice=args.voice,
            update_existing=args.update_existing,
        )
    except (subprocess.CalledProcessError, urllib.error.URLError, RuntimeError) as error:
        print(f"Custom sync failed: {error}")
        print("Open Anki with AnkiConnect enabled, then run this script again.")
        return 1

    normalize_generated_tag_case()
    print(f"Custom sync summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
