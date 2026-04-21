from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.chinese_support import is_generated_tag
from scripts.vocabulary import derive_tags, read_source_vocabulary, read_vocabulary


ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DEFAULT_DECK = "Mandarin"
DEFAULT_MODEL = "Mandarin Vocabulary"

ANKI_FIELDS = [
    "Vocabulary ID",
    "Hanzi",
    "Pinyin",
    "English",
    "Example Sentence",
    "Sentence Pinyin",
    "Sentence Translation",
    "HSK Level",
    "Source",
    "Lesson",
    "Tags",
    "Notes",
]


def anki_tags(entry: dict[str, Any]) -> list[str]:
    return derive_tags(entry)


def entry_fields(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "Vocabulary ID": str(entry.get("id") or ""),
        "Hanzi": str(entry.get("hanzi") or ""),
        "Pinyin": str(entry.get("pinyin") or ""),
        "English": str(entry.get("english") or ""),
        "Example Sentence": str(entry.get("example_sentence") or ""),
        "Sentence Pinyin": str(entry.get("sentence_pinyin") or ""),
        "Sentence Translation": str(entry.get("sentence_translation") or ""),
        "HSK Level": "" if entry.get("hsk_level") is None else str(entry.get("hsk_level")),
        "Source": str(entry.get("source") or ""),
        "Lesson": str(entry.get("lesson") or ""),
        "Tags": " ".join(anki_tags(entry)),
        "Notes": str(entry.get("notes") or ""),
    }


def build_anki_note(entry: dict[str, Any], deck_name: str, model_name: str) -> dict[str, Any]:
    return {
        "deckName": deck_name,
        "modelName": model_name,
        "fields": entry_fields(entry),
        "tags": anki_tags(entry),
        "options": {"allowDuplicate": False, "duplicateScope": "deck"},
    }


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


def ensure_model(model_name: str) -> None:
    existing = invoke_anki("modelNames")
    if model_name in existing:
        return
    invoke_anki(
        "createModel",
        {
            "modelName": model_name,
            "inOrderFields": ANKI_FIELDS,
            "css": ".card { font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 20px; } .hanzi { font-size: 42px; }",
            "cardTemplates": [
                {
                    "Name": "Recognition",
                    "Front": '<div class="hanzi">{{Hanzi}}</div>',
                    "Back": "{{FrontSide}}<hr><div>{{Pinyin}}</div><div>{{English}}</div><p>{{Example Sentence}}</p><p>{{Sentence Pinyin}}</p>",
                }
            ],
        },
    )


def sync_entries(entries: list[dict[str, Any]], deck_name: str, model_name: str, dry_run: bool = False) -> dict[str, int]:
    summary = {"added": 0, "updated": 0, "unchanged": 0}
    if not dry_run:
        ensure_deck(deck_name)
        ensure_model(model_name)

    for entry in entries:
        query = duplicate_query(str(entry["id"]), model_name)
        note_ids = [] if dry_run else invoke_anki("findNotes", {"query": query})
        if not note_ids:
            summary["added"] += 1
            if not dry_run:
                invoke_anki("addNote", {"note": build_anki_note(entry, deck_name, model_name)})
            continue
        summary["updated"] += 1
        if not dry_run:
            note_id = note_ids[0]
            invoke_anki("updateNoteFields", {"note": {"id": note_id, "fields": entry_fields(entry)}})
            invoke_anki("addTags", {"notes": [note_id], "tags": " ".join(anki_tags(entry))})

    if not dry_run:
        normalize_generated_tag_case()
    return summary


def write_sync_log(summary: dict[str, int], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Anki Sync", "", *[f"- {key}: {value}" for key, value in summary.items()]]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync canonical vocabulary data to Anki through AnkiConnect.")
    parser.add_argument("--data", type=Path, default=Path("data/sources"))
    parser.add_argument("--deck", default=DEFAULT_DECK)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log", type=Path, default=Path("logs/sync/latest.md"))
    args = parser.parse_args()

    entries = read_source_vocabulary(args.data) if args.data.is_dir() else read_vocabulary(args.data)
    summary = sync_entries(entries, deck_name=args.deck, model_name=args.model, dry_run=args.dry_run)
    write_sync_log(summary, args.log)
    print(f"Anki sync summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
