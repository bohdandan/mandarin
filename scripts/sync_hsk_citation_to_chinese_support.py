from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.error
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.chinese_support import build_tone_fields, primary_citation_pinyin, reconcile_generated_tags
from scripts.sync_anki import invoke_anki, normalize_generated_tag_case
from scripts.vocabulary import derive_tags, read_source_vocabulary, strip_html


DEFAULT_DECK = "HSK [Chinese Support]::HSK1-4"
DEFAULT_MODEL = "Chinese (Advanced)"
TONE_FIELD_NAMES = ["Color", "Pinyin", "Bopomofo", "Ruby", "Ruby (Bopomofo)"]


def repo_hsk_entries(data_path: Path, levels: tuple[int, ...]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    entries = [
        entry
        for entry in read_source_vocabulary(data_path)
        if entry.get("hsk_level") in levels and str(entry.get("source") or "").startswith("hsk-")
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[str(entry["hanzi"])].append(entry)

    selected: dict[str, dict[str, Any]] = {}
    ambiguous: list[str] = []
    for hanzi, hanzi_entries in grouped.items():
        citations = {primary_citation_pinyin(str(entry["pinyin"])) for entry in hanzi_entries}
        if len(citations) > 1:
            ambiguous.append(hanzi)
            continue
        selected[hanzi] = sorted(
            hanzi_entries,
            key=lambda entry: (int(entry.get("hsk_level") or 99), str(entry.get("source") or ""), str(entry.get("id") or "")),
        )[0]
    return selected, sorted(ambiguous)


def existing_hsk_notes(deck_name: str, model_name: str) -> dict[str, list[dict[str, Any]]]:
    note_ids = invoke_anki("findNotes", {"query": f'deck:"{deck_name}" note:"{model_name}"'})
    if not note_ids:
        return {}
    notes: list[dict[str, Any]] = []
    for index in range(0, len(note_ids), 200):
        notes.extend(invoke_anki("notesInfo", {"notes": note_ids[index : index + 200]}))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for note in notes:
        grouped[strip_html(note["fields"]["Hanzi"]["value"])].append(note)
    return grouped


def current_tone_fields(note: dict[str, Any]) -> dict[str, str]:
    return {field: note["fields"][field]["value"] for field in TONE_FIELD_NAMES}


def sync_hsk_citation_tones(
    *,
    data_path: Path,
    deck_name: str,
    model_name: str,
    levels: tuple[int, ...],
    dry_run: bool = False,
) -> dict[str, Any]:
    repo_entries, ambiguous_repo = repo_hsk_entries(data_path, levels)
    note_groups = existing_hsk_notes(deck_name, model_name)

    summary: dict[str, Any] = {
        "matched": 0,
        "updated": 0,
        "unchanged": 0,
        "missing": 0,
        "ambiguous_repo": len(ambiguous_repo),
        "ambiguous_deck": 0,
        "updated_hanzi": [],
        "missing_hanzi": [],
        "ambiguous_repo_hanzi": ambiguous_repo,
        "ambiguous_deck_hanzi": [],
    }

    for hanzi, entry in repo_entries.items():
        note_group = note_groups.get(hanzi, [])
        if not note_group:
            summary["missing"] += 1
            summary["missing_hanzi"].append(hanzi)
            continue
        if len(note_group) > 1:
            summary["ambiguous_deck"] += 1
            summary["ambiguous_deck_hanzi"].append(hanzi)
            continue

        note = note_group[0]
        summary["matched"] += 1
        desired_fields = build_tone_fields(hanzi, str(entry["pinyin"]))
        tags_to_add, tags_to_remove = reconcile_generated_tags(note.get("tags", []), derive_tags(entry))
        if current_tone_fields(note) == desired_fields and not tags_to_add and not tags_to_remove:
            summary["unchanged"] += 1
            continue

        if not dry_run:
            if current_tone_fields(note) != desired_fields:
                invoke_anki("updateNoteFields", {"note": {"id": note["noteId"], "fields": desired_fields}})
            if tags_to_remove:
                invoke_anki("removeTags", {"notes": [note["noteId"]], "tags": " ".join(tags_to_remove)})
            if tags_to_add:
                invoke_anki("addTags", {"notes": [note["noteId"]], "tags": " ".join(tags_to_add)})
        summary["updated"] += 1
        summary["updated_hanzi"].append(hanzi)

    summary["updated_hanzi"].sort()
    summary["missing_hanzi"].sort()
    summary["ambiguous_deck_hanzi"].sort()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync citation-tone fields for repo HSK words into the Chinese Support HSK deck.")
    parser.add_argument("--data", type=Path, default=Path("data/sources"))
    parser.add_argument("--deck", default=DEFAULT_DECK)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--levels", nargs="+", type=int, default=[1, 2])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        summary = sync_hsk_citation_tones(
            data_path=args.data,
            deck_name=args.deck,
            model_name=args.model,
            levels=tuple(args.levels),
            dry_run=args.dry_run,
        )
    except (subprocess.CalledProcessError, urllib.error.URLError, RuntimeError) as error:
        print(f"HSK citation sync failed: {error}")
        print("Open Anki with AnkiConnect enabled, then run this script again.")
        return 1

    normalize_generated_tag_case()
    print(f"HSK citation sync summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
