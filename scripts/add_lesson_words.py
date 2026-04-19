from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.vocabulary import build_entry, read_source_vocabulary, write_source_vocabulary


def add_lesson_words(data_path: Path, lesson_csv: Path, lesson: str) -> dict[str, int]:
    entries = read_source_vocabulary(data_path)
    by_word = {(entry["hanzi"], entry["pinyin"]): entry for entry in entries}
    added = 0
    updated = 0

    with lesson_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            entry = build_entry(
                hanzi=row.get("hanzi"),
                pinyin=row.get("pinyin"),
                english=row.get("english") or row.get("translation"),
                example_sentence=row.get("example_sentence"),
                sentence_pinyin=row.get("sentence_pinyin"),
                sentence_translation=row.get("sentence_translation"),
                source="custom",
                lesson=lesson,
                tags_raw="",
            )
            key = (entry["hanzi"], entry["pinyin"])
            if key in by_word:
                existing = by_word[key]
                existing.update({field: value for field, value in entry.items() if value not in ("", [], None)})
                updated += 1
            else:
                entries.append(entry)
                by_word[key] = entry
                added += 1

    write_source_vocabulary(data_path, entries)
    return {"added": added, "updated": updated}


def main() -> int:
    parser = argparse.ArgumentParser(description="Add lesson words from a CSV file.")
    parser.add_argument("lesson_csv", type=Path)
    parser.add_argument("--lesson", required=True)
    parser.add_argument("--data", type=Path, default=Path("data/sources"))
    args = parser.parse_args()

    summary = add_lesson_words(args.data, args.lesson_csv, args.lesson)
    print(f"Lesson import summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
