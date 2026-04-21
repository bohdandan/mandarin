from __future__ import annotations

import re
import subprocess
import tempfile
import unicodedata
from typing import Any


PINYIN_TOKEN_RE = re.compile(r"[A-Za-züÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛńňǹḿŃŇǸḾ]+")
GENERATED_TAG_PATTERNS = [
    re.compile(r"^HSK\d+$", re.I),
    re.compile(r"^HSK\d+::HSK:\d+\.\d{2}$", re.I),
    re.compile(r"^CUSTOM$", re.I),
    re.compile(r"^ADDED-\d{4}$", re.I),
    re.compile(r"^LESSON-.*$", re.I),
]


def swift_string_literal(text: str) -> str:
    escaped = (
        str(text)
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def ascii_pinyin(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-züv]", "", without_marks).replace("ü", "u").replace("v", "u")


def ascii_pinyin_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    result: list[str] = []
    for char in normalized:
        if unicodedata.category(char) == "Mn":
            continue
        if char in ("ü", "Ü", "v", "V"):
            result.append("u" if char.islower() else "U")
            continue
        result.append(char)
    return "".join(result)


def primary_citation_pinyin(marked_pinyin: str) -> str:
    tokens = [token for token in str(marked_pinyin).strip().split() if token]
    if not tokens:
        return ""
    return " ".join(token.split("/", 1)[0] for token in tokens)


def tone_number_from_pinyin(syllable: str) -> int:
    if any(char in syllable for char in "āēīōūǖĀĒĪŌŪǕ"):
        return 1
    if any(char in syllable for char in "áéíóúǘÁÉÍÓÚǗ"):
        return 2
    if any(char in syllable for char in "ǎěǐǒǔǚǍĚǏǑǓǙ"):
        return 3
    if any(char in syllable for char in "àèìòùǜÀÈÌÒÙǛ"):
        return 4
    return 5


def tone_number_from_bopomofo(syllable: str) -> int:
    if "˙" in syllable:
        return 5
    if "ˋ" in syllable:
        return 4
    if "ˇ" in syllable:
        return 3
    if "ˊ" in syllable:
        return 2
    return 1


def split_marked_pinyin_by_guide(marked_pinyin: str, guide_syllables: list[str]) -> list[str]:
    citation = primary_citation_pinyin(marked_pinyin)
    tokens = PINYIN_TOKEN_RE.findall(citation)
    if not tokens:
        return []
    if not guide_syllables:
        return tokens
    if len(tokens) == len(guide_syllables):
        return tokens

    compact = "".join(tokens)
    result: list[str] = []
    index = 0
    for guide in guide_syllables:
        target = len(ascii_pinyin(guide))
        start = index
        count = 0
        while index < len(compact) and count < target:
            count += len(ascii_pinyin(compact[index]))
            index += 1
        result.append(compact[start:index] or guide)
    if index < len(compact) and result:
        result[-1] += compact[index:]
    return result


def tone_span(text: str, tone: int) -> str:
    return f'<span class="tone{tone}">{text}</span>'


def pinyin_comment(syllables: list[str]) -> str:
    return " ".join(ascii_pinyin(syllable) for syllable in syllables)


def is_generated_tag(tag: str) -> bool:
    return any(pattern.match(tag) for pattern in GENERATED_TAG_PATTERNS)


def reconcile_generated_tags(existing_tags: list[str], desired_tags: list[str]) -> tuple[list[str], list[str]]:
    desired = list(dict.fromkeys(desired_tags))
    existing = list(dict.fromkeys(existing_tags))
    desired_set = set(desired)
    existing_set = set(existing)
    to_remove = [tag for tag in existing if is_generated_tag(tag) and tag not in desired_set]
    to_add = [tag for tag in desired if tag not in existing_set]
    return to_add, to_remove


def ruby_text(hanzi: str, readings: list[str]) -> str:
    result: list[str] = []
    reading_index = 0
    for char in hanzi:
        if "\u4e00" <= char <= "\u9fff" and reading_index < len(readings):
            result.append(f"<ruby>{char}<rt>{readings[reading_index]}</rt></ruby>")
            reading_index += 1
        else:
            result.append(char)
    return "".join(result)


def color_text(hanzi: str, pinyin_syllables: list[str]) -> str:
    result: list[str] = []
    syllable_index = 0
    for char in hanzi:
        if "\u4e00" <= char <= "\u9fff" and syllable_index < len(pinyin_syllables):
            result.append(tone_span(char, tone_number_from_pinyin(pinyin_syllables[syllable_index])))
            syllable_index += 1
        else:
            result.append(char)
    return "".join(result)


def silhouette_text(hanzi: str) -> str:
    marks = ["_" for char in hanzi if "\u4e00" <= char <= "\u9fff"]
    return " ".join(marks)


def split_display_token(token: str, remaining_guide: list[str]) -> tuple[list[str], int]:
    if not remaining_guide:
        return [token], 0
    parts: list[str] = []
    index = 0
    consumed = 0
    for guide in remaining_guide:
        if index >= len(token):
            break
        start = index
        target = len(ascii_pinyin(guide))
        count = 0
        while index < len(token) and count < target:
            count += len(ascii_pinyin(token[index]))
            index += 1
        parts.append(token[start:index] or guide)
        consumed += 1
    if index < len(token) and parts:
        parts[-1] += token[index:]
    return parts or [token], consumed


def pinyin_field_html(marked_pinyin: str, guide_syllables: list[str]) -> str:
    rendered: list[str] = []
    remaining_guide = list(guide_syllables)
    last_end = 0
    for match in PINYIN_TOKEN_RE.finditer(marked_pinyin):
        if match.start() > last_end:
            rendered.append(marked_pinyin[last_end:match.start()])
        parts, consumed = split_display_token(match.group(0), remaining_guide)
        rendered.extend(tone_span(part, tone_number_from_pinyin(part)) for part in parts)
        if consumed:
            remaining_guide = remaining_guide[consumed:]
        last_end = match.end()
    if last_end < len(marked_pinyin):
        rendered.append(marked_pinyin[last_end:])
    field = "".join(rendered)
    return f"{field} <!-- {ascii_pinyin_text(marked_pinyin)} -->"


def bopomofo_field_html(bopomofo_syllables: list[str]) -> str:
    field = " ".join(tone_span(syllable, tone_number_from_bopomofo(syllable)) for syllable in bopomofo_syllables)
    return f"{field} <!-- {' '.join(bopomofo_syllables)} -->"


def build_tone_fields(hanzi: str, marked_pinyin: str) -> dict[str, str]:
    pinyin_syllables = split_marked_pinyin_by_guide(marked_pinyin, latin_guide_syllables(hanzi))
    bopomofo = bopomofo_syllables(pinyin_syllables)
    return {
        "Color": color_text(hanzi, pinyin_syllables),
        "Pinyin": pinyin_field_html(marked_pinyin, pinyin_syllables),
        "Bopomofo": bopomofo_field_html(bopomofo),
        "Ruby": ruby_text(hanzi, pinyin_syllables),
        "Ruby (Bopomofo)": ruby_text(hanzi, bopomofo),
    }


def build_chinese_advanced_fields(
    entry: dict[str, Any],
    *,
    pinyin_syllables: list[str],
    bopomofo_syllables: list[str],
    traditional: str,
    sound_ref: str,
) -> dict[str, str]:
    return {
        "Hanzi": str(entry["hanzi"]),
        "Color": color_text(str(entry["hanzi"]), pinyin_syllables),
        "Pinyin": pinyin_field_html(str(entry["pinyin"]), pinyin_syllables),
        "Bopomofo": bopomofo_field_html(bopomofo_syllables),
        "Ruby": ruby_text(str(entry["hanzi"]), pinyin_syllables),
        "Ruby (Bopomofo)": ruby_text(str(entry["hanzi"]), bopomofo_syllables),
        "English": str(entry.get("english") or ""),
        "Classifier": "",
        "Simplified": str(entry["hanzi"]),
        "Traditional": traditional,
        "Also Written": str(entry.get("example_sentence") or ""),
        "Frequency": '<div class="freq freq-unknown">unknown</div>',
        "Silhouette": silhouette_text(str(entry["hanzi"])),
        "Sound": sound_ref,
    }


def swift_transform(text: str, transform: str) -> str:
    with tempfile.TemporaryDirectory() as module_cache:
        swift_args = ["swift", "-module-cache-path", module_cache]
        if transform == "toLatin":
            code = f'import Foundation; let s = {swift_string_literal(text)}; print((s as NSString).applyingTransform(.toLatin, reverse: false) ?? s)'
        else:
            code = (
                "import Foundation; "
                f"let s = {swift_string_literal(text)}; "
                f'let t = StringTransform(rawValue: {swift_string_literal(transform)}); '
                "print((s as NSString).applyingTransform(t, reverse: false) ?? s)"
            )
        result = subprocess.run(swift_args + ["-e", code], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def latin_guide_syllables(hanzi: str) -> list[str]:
    return PINYIN_TOKEN_RE.findall(swift_transform(hanzi, "toLatin"))


def bopomofo_syllables(pinyin_syllables: list[str]) -> list[str]:
    transformed = swift_transform(" ".join(pinyin_syllables), "Latin-Bopomofo")
    return [part for part in transformed.split() if part]


def traditional_hanzi(hanzi: str) -> str:
    return swift_transform(hanzi, "Hans-Hant")
