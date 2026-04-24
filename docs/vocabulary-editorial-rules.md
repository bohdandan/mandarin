# Vocabulary Editorial Rules

This file records the durable rules for adding and maintaining vocabulary in this repo, so future word drops follow the same shape without re-deciding everything.

## Source Of Truth

- The repository is canonical.
- Anki is the review target.
- Source files live in `data/sources/`.
- Current maintained sources:
  - `data/sources/hsk-1.json`
  - `data/sources/hsk-2.json`
  - `data/sources/custom.json`

## Current Anki Targets

- Decks:
  - `HSK3.0::HSK1`
  - `HSK3.0::HSK2`
  - `HSK3.0::CUSTOM`
- Note type:
  - `Mandarin Vocabulary`

## Entry Shape

Each vocabulary entry should keep the current schema:

- `id`
- `hanzi`
- `pinyin`
- `english`
- `example_sentence`
- `sentence_pinyin`
- `sentence_translation`
- `hsk_level`
- `source`
- `lesson`
- `notes`
- `created_at`
- `updated_at`

Do not store generated tags in source JSON.

## Custom Words

When adding new personal words:

- add them to `data/sources/custom.json`
- set `source` to `custom`
- set an approximate `hsk_level`
- set `lesson` to the year, for example `2026`
- add one example sentence

Approximate HSK for custom words is fine. The goal is useful filtering, not exam-perfect labeling.

## Generated Tags

Tags are generated from source fields and should stay uppercase.

Examples:

- `HSK1`
- `HSK2`
- `CUSTOM`
- `ADDED-2026`
- `HSK1::HSK:1.09`
- `HSK2::HSK:2.10`

Rules:

- HSK entries get the level tag and lesson tags
- custom entries get:
  - approximate HSK tag
  - `CUSTOM`
  - `ADDED-<year>`

## Example Sentence Rules

Every HSK and custom word should have exactly one example sentence.

Editorial standard:

- keep it short, natural, and everyday
- include the target word clearly
- bold the target word with `<b>...</b>`
- prefer vocabulary from the same HSK level or lower
- allow an occasional slightly harder helper word when it makes the sentence much more natural
- keep grammar appropriate to the level
- avoid awkward dictionary-style sentences
- use the most useful common sense of the word for now

Formatting rules:

- store the sentence in `example_sentence`
- do not leave the target word unbolded
- avoid duplicate example sentences across many entries when a distinct simple sentence is easy to write

## Ordering Rules

HSK source files should follow lesson flow, not old ID order.

Sort rule for HSK files:

1. earliest lesson in `lesson`
2. Hanzi
3. entry ID

If an entry belongs to multiple lessons, use the earliest lesson for ordering.

`custom.json` does not need lesson-order sorting beyond staying clean and stable.

## HSK Lesson Metadata

If an HSK import leaves a word with an empty `lesson`, fix the lesson mapping instead of letting it drift.

Current lesson mappings live in:

- `scripts/hsk_lessons.py`

That file should be updated when imported HSK words are missing lesson assignments.

## Audio Rules

Preferred voice for repo-managed Mandarin audio:

- Google TTS voice `cmn-CN-Wavenet-C`

Rules:

- use this voice when audio is added or regenerated
- do not bulk-regenerate audio casually
- prefer targeted regeneration when a word sounds wrong
- if pronunciation is awkward for a specific word, handle it as a one-off override instead of changing the whole deck voice

## Validation Rules

Before considering a vocab pass complete:

- HSK entries should have example sentences
- HSK files should be in lesson order
- generated tags should still derive cleanly from `source`, `hsk_level`, `lesson`, and dates

Useful commands:

```bash
python3 scripts/validate_vocabulary.py
python3 scripts/sync_anki.py
```

## Default Workflow For New Words

When new words are dropped into the chat:

1. add them to `data/sources/custom.json`
2. assign approximate `hsk_level`
3. set `lesson` to the current year
4. write one natural example sentence with the target word bolded
5. validate the source data
6. sync Anki
7. regenerate audio only when needed, using `cmn-CN-Wavenet-C`

## Default Workflow For New HSK Source Updates

When a new HSK source is imported or corrected:

1. make sure every entry has a lesson
2. fix `scripts/hsk_lessons.py` if lesson mapping is missing
3. curate example sentences
4. reorder by earliest lesson
5. validate
6. sync Anki
