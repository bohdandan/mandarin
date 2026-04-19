from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.vocabulary import read_source_vocabulary, read_vocabulary


REQUIRED_FIELDS = ["id", "hanzi", "pinyin", "source", "created_at", "updated_at"]


def validate_entries(entries: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_words: set[tuple[str, str]] = set()

    for index, entry in enumerate(entries, start=1):
        label = entry.get("id") or f"row {index}"
        for field in REQUIRED_FIELDS:
            if entry.get(field) in (None, ""):
                errors.append(f"{label}: missing {field}")

        entry_id = str(entry.get("id", ""))
        if entry_id in seen_ids:
            errors.append(f"duplicate id {entry_id}")
        seen_ids.add(entry_id)

        word_key = (str(entry.get("hanzi", "")), str(entry.get("pinyin", "")), str(entry.get("english", "")))
        if all(word_key):
            if word_key in seen_words:
                errors.append(f"duplicate hanzi/pinyin {word_key[0]} / {word_key[1]}")
            seen_words.add(word_key)

        if "tags" in entry:
            errors.append(f"{label}: tags are generated from source, hsk_level, lesson, and dates")

        hsk_level = entry.get("hsk_level")
        if hsk_level is not None and (not isinstance(hsk_level, int) or hsk_level < 1):
            errors.append(f"{label}: hsk_level must be a positive integer or null")

    return errors


def write_validation_log(errors: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Vocabulary Validation", "", f"Errors: {len(errors)}", ""]
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("No validation errors.")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical Mandarin vocabulary data.")
    parser.add_argument("--data", type=Path, default=Path("data/sources"))
    parser.add_argument("--log", type=Path, default=Path("logs/validation/latest.md"))
    args = parser.parse_args()

    entries = read_source_vocabulary(args.data) if args.data.is_dir() else read_vocabulary(args.data)
    errors = validate_entries(entries)
    write_validation_log(errors, args.log)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Validated {args.data}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
