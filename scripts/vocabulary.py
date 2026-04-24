from __future__ import annotations

import html
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


@dataclass
class ImportResult:
    entries: list[dict[str, Any]]
    skipped_duplicates: list[str]
    suspicious_rows: list[str]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def strip_html(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", "", value)
    return html.unescape(no_tags).strip()


def pinyin_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    without_marks = without_marks.replace("ü", "u").replace("v", "u")
    slug = re.sub(r"[^a-z0-9]+", "-", without_marks).strip("-")
    return slug or "word"


def parse_hsk_level(tags: str) -> int | None:
    match = re.search(r"HSK(\d+)", tags)
    return int(match.group(1)) if match else None


def parse_lesson(tags: str) -> str:
    match = re.search(r"HSK:(\d+\.\d+)", tags)
    return f"HSK:{match.group(1)}" if match else ""


def unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def format_hsk_lesson(level: int, lesson_number: int | str) -> str:
    return f"HSK:{level}.{int(lesson_number):02d}"


def format_hsk_lesson_tag(level: int, lesson_number: int | str) -> str:
    return f"HSK{level}::{format_hsk_lesson(level, lesson_number)}"


def parse_hsk_lesson_tags(value: str) -> list[str]:
    tags: list[str] = []
    for match in re.finditer(r"HSK(\d+)::HSK:(\d+)\.(\d+)", value):
        tag_level = int(match.group(1))
        lesson_level = int(match.group(2))
        lesson_number = int(match.group(3))
        if tag_level == lesson_level:
            tags.append(format_hsk_lesson_tag(tag_level, lesson_number))
    for match in re.finditer(r"HSK:(\d+)\.(\d+)", value):
        lesson_level = int(match.group(1))
        lesson_number = int(match.group(2))
        tags.append(format_hsk_lesson_tag(lesson_level, lesson_number))
    return unique_ordered(tags)


def earliest_hsk_lesson_sort_key(value: str) -> tuple[int, int] | None:
    lessons: list[tuple[int, int]] = []
    for match in re.finditer(r"HSK:(\d+)\.(\d+)", value):
        lessons.append((int(match.group(1)), int(match.group(2))))
    return min(lessons) if lessons else None


def added_year_tag(created_at: str) -> str:
    match = re.match(r"^(\d{4})", created_at)
    return f"ADDED-{match.group(1)}" if match else ""


def custom_year_tag(lesson: str, created_at: str) -> str:
    match = re.match(r"^(\d{4})", lesson)
    if match:
        return f"ADDED-{match.group(1)}"
    return added_year_tag(created_at)


def derive_tags(entry: dict[str, Any]) -> list[str]:
    source = str(entry.get("source") or "")
    lesson = str(entry.get("lesson") or "")
    created_at = str(entry.get("created_at") or "")
    hsk_level = entry.get("hsk_level")
    tags: list[str] = []
    if hsk_level is not None:
        tags.append(f"HSK{hsk_level}")
    tags.extend(parse_hsk_lesson_tags(lesson))
    if source == "custom":
        tags.append("CUSTOM")
        tags.append(custom_year_tag(lesson, created_at))
    if lesson and lesson.startswith("lesson-"):
        tags.append(lesson.upper())
    return unique_ordered(tags)


def make_entry_id(source: str, raw_id: Any, hanzi: str, pinyin: str, hsk_level: int | None) -> str:
    prefix = source if source == "custom" else f"hsk{hsk_level}" if hsk_level is not None else source
    raw = clean_text(raw_id)
    if raw:
        number_match = re.match(r"^(\d+)(?:\.0)?$", raw)
        if number_match:
            raw = number_match.group(1).zfill(4)
        else:
            raw = pinyin_slug(raw)
        return f"{prefix}-{raw}-{pinyin_slug(pinyin)}"
    return f"{prefix}-{pinyin_slug(hanzi)}-{pinyin_slug(pinyin)}"


def build_entry(
    *,
    raw_id: Any = "",
    hanzi: Any,
    pinyin: Any,
    english: Any,
    example_sentence: Any = "",
    sentence_pinyin: Any = "",
    sentence_translation: Any = "",
    source: str,
    lesson: str = "",
    tags_raw: str = "",
    hsk_level: int | None = None,
    notes: str = "",
    today: str | None = None,
) -> dict[str, Any]:
    created = today or date.today().isoformat()
    clean_hanzi = clean_text(hanzi)
    clean_pinyin = clean_text(pinyin)
    level = hsk_level if hsk_level is not None else parse_hsk_level(tags_raw)
    parsed_lesson = lesson or parse_lesson(tags_raw)
    if source == "custom" and parsed_lesson in ("", "custom"):
        parsed_lesson = created[:4]
    return {
        "id": make_entry_id(source, raw_id, clean_hanzi, clean_pinyin, level),
        "hanzi": clean_hanzi,
        "pinyin": clean_pinyin,
        "english": clean_text(english),
        "example_sentence": clean_text(example_sentence),
        "sentence_pinyin": clean_text(sentence_pinyin),
        "sentence_translation": clean_text(sentence_translation),
        "hsk_level": level,
        "source": source,
        "lesson": parsed_lesson,
        "notes": notes,
        "created_at": created,
        "updated_at": created,
    }


def read_vocabulary(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def write_vocabulary(path: Path, entries: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = [entry_without_generated_fields(entry) for entry in entries]
    ordered = sorted(cleaned, key=lambda entry: (entry.get("hsk_level") is None, entry.get("hsk_level") or 99, entry["id"]))
    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_filename(source: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-")
    return f"{normalized or 'unknown'}.json"


def source_sort_key(entry: dict[str, Any]) -> tuple[bool, int, str]:
    earliest_lesson = earliest_hsk_lesson_sort_key(str(entry.get("lesson") or ""))
    if earliest_lesson is not None:
        lesson_level, lesson_number = earliest_lesson
        return (False, lesson_level * 100 + lesson_number, str(entry.get("hanzi") or ""), entry["id"])
    return (entry.get("hsk_level") is None, (entry.get("hsk_level") or 99) * 100, str(entry.get("hanzi") or ""), entry["id"])


def entry_without_generated_fields(entry: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(entry)
    cleaned.pop("tags", None)
    return cleaned


def write_source_vocabulary(output_dir: Path, entries: Iterable[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_json in output_dir.glob("*.json"):
        old_json.unlink()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(str(entry.get("source") or "unknown"), []).append(entry)

    index_sources = []
    for source in sorted(grouped):
        file_name = source_filename(source)
        source_entries = [entry_without_generated_fields(entry) for entry in sorted(grouped[source], key=source_sort_key)]
        (output_dir / file_name).write_text(json.dumps(source_entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index_sources.append({"source": source, "file": file_name})

    (output_dir / "index.json").write_text(
        json.dumps({"sources": index_sources}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_source_vocabulary(source_dir: Path) -> list[dict[str, Any]]:
    index_path = source_dir / "index.json"
    if not index_path.exists():
        return []
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    for source in index.get("sources", []):
        source_path = source_dir / source["file"]
        entries.extend(json.loads(source_path.read_text(encoding="utf-8")))
    return entries
