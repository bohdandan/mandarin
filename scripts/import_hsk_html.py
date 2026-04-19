from __future__ import annotations

import argparse
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.request import urlopen

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.hsk_lessons import hsk_lesson_numbers
from scripts.vocabulary import (
    build_entry,
    clean_text,
    format_hsk_lesson,
    pinyin_slug,
    read_source_vocabulary,
    write_source_vocabulary,
)


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_td = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "td":
            self.in_td = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self.in_td:
            self.current_row.append(html.unescape("".join(self.current_cell)).strip())
            self.current_cell = []
            self.in_td = False
        elif tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []

    def handle_data(self, data: str) -> None:
        if self.in_td:
            self.current_cell.append(data)


def clean_hanzi_marker(word: str) -> tuple[str, str]:
    match = re.match(r"^(.+?)(\d+)$", word)
    if match:
        return match.group(1), word
    return word, ""


def parse_hsk_html(html_text: str, level: int, source_url: str) -> list[dict[str, Any]]:
    parser = TableParser()
    parser.feed(html_text)
    entries: list[dict[str, Any]] = []

    for row in parser.rows:
        if not row or not row[0].isdigit():
            continue
        if len(row) < 4:
            continue

        sequence = int(row[0])
        raw_word = clean_text(row[1])
        hanzi, source_marker = clean_hanzi_marker(raw_word)
        pinyin = clean_text(row[2])
        part_of_speech = clean_text(row[3]) if len(row) >= 5 else ""
        translation = clean_text(row[4]) if len(row) >= 5 else clean_text(row[3])
        notes = []
        if part_of_speech:
            notes.append(f"Part of speech: {part_of_speech}")
        if source_marker:
            notes.append(f"Source marker: {source_marker}")
        lesson_numbers = hsk_lesson_numbers(level, hanzi, pinyin)
        lesson = "; ".join(format_hsk_lesson(level, lesson_number) for lesson_number in lesson_numbers)
        entry = build_entry(
            raw_id=str(sequence).zfill(4),
            hanzi=hanzi,
            pinyin=pinyin,
            english=translation,
            example_sentence="",
            sentence_pinyin="",
            sentence_translation="",
            source=f"hsk-{level}",
            lesson=lesson,
            tags_raw="",
            hsk_level=level,
            notes="; ".join(notes),
        )
        entry["id"] = f"hsk{level}-{sequence:04d}-{pinyin_slug(pinyin)}"
        entries.append(entry)

    return entries


def import_hsk_html(
    html_text: str,
    *,
    source_dir: Path,
    level: int,
    remove_sources: list[str],
    source_url: str,
) -> list[dict[str, Any]]:
    imported_entries = parse_hsk_html(html_text, level=level, source_url=source_url)
    target_source = f"hsk-{level}"
    existing_entries = [
        entry
        for entry in read_source_vocabulary(source_dir)
        if entry.get("source") not in set(remove_sources + [target_source])
    ]
    next_entries = existing_entries + imported_entries
    write_source_vocabulary(source_dir, next_entries)
    return imported_entries


def read_input(path_or_url: str) -> str:
    if path_or_url.startswith(("http://", "https://")):
        with urlopen(path_or_url, timeout=15) as response:
            return response.read().decode("utf-8")
    return Path(path_or_url).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a New HSK HTML vocabulary table into a source-specific JSON file.")
    parser.add_argument("input", help="HTML file path or URL")
    parser.add_argument("--level", type=int, required=True)
    parser.add_argument("--source-dir", type=Path, default=Path("data/sources"))
    parser.add_argument("--source-url", default="")
    parser.add_argument("--remove-source", action="append", default=[])
    args = parser.parse_args()

    source_url = args.source_url or args.input
    imported = import_hsk_html(
        read_input(args.input),
        source_dir=args.source_dir,
        level=args.level,
        remove_sources=args.remove_source,
        source_url=source_url,
    )
    print(f"Imported {len(imported)} entries into {args.source_dir / f'hsk-{args.level}.json'}")
    if len(imported) == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
