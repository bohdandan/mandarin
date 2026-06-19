from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from scripts.google_tts import GoogleTtsConfig, google_access_token, load_google_tts_config
from scripts.vocabulary import strip_html


GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/v3/projects/{project_id}:translateText"
DEFAULT_SOURCE_DIR = Path("data/sources")


def source_paths(source_dir: Path = DEFAULT_SOURCE_DIR) -> list[Path]:
    return sorted(path for path in source_dir.glob("*.json") if path.name != "index.json")


def missing_translation_items(entries: list[dict[str, Any]]) -> list[tuple[int, str]]:
    items: list[tuple[int, str]] = []
    for index, entry in enumerate(entries):
        if str(entry.get("sentence_translation") or "").strip():
            continue
        example = strip_html(str(entry.get("example_sentence") or ""))
        if example:
            items.append((index, example))
    return items


def apply_translations(entries: list[dict[str, Any]], translations: Iterable[tuple[int, str]]) -> int:
    changed = 0
    for index, translation in translations:
        clean_translation = str(translation or "").strip()
        if not clean_translation:
            continue
        if str(entries[index].get("sentence_translation") or "").strip():
            continue
        entries[index]["sentence_translation"] = clean_translation
        changed += 1
    return changed


def translate_batch(texts: list[str], config: GoogleTtsConfig, *, target_language: str = "en") -> list[str]:
    if not texts:
        return []
    token = google_access_token()
    url = GOOGLE_TRANSLATE_URL.format(project_id=urllib.parse.quote(config.project_id, safe=""))
    payload = json.dumps(
        {
            "contents": texts,
            "mimeType": "text/plain",
            "sourceLanguageCode": "zh-CN",
            "targetLanguageCode": target_language,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "x-goog-user-project": config.project_id,
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))
    translations = body.get("translations") or []
    translated_texts = [str(item.get("translatedText") or "").strip() for item in translations]
    if len(translated_texts) != len(texts):
        raise RuntimeError(f"Google Translate returned {len(translated_texts)} translations for {len(texts)} inputs.")
    return translated_texts


def backfill_path(path: Path, config: GoogleTtsConfig, *, batch_size: int, dry_run: bool) -> int:
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise RuntimeError(f"{path} must contain a JSON list.")
    missing = missing_translation_items(entries)
    changed = 0
    for start in range(0, len(missing), batch_size):
        batch = missing[start : start + batch_size]
        translations = translate_batch([text for _, text in batch], config)
        changed += apply_translations(entries, [(index, translation) for (index, _), translation in zip(batch, translations)])
    if changed and not dry_run:
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill sentence_translation fields with Google Cloud Translation.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_google_tts_config()
    total = 0
    for path in source_paths(args.source_dir):
        changed = backfill_path(path, config, batch_size=args.batch_size, dry_run=args.dry_run)
        total += changed
        print(f"{path}: {changed}")
    print(f"Total translations backfilled: {total}")


if __name__ == "__main__":
    main()
