# Mandarin Vocabulary

A personal Mandarin vocabulary library for keeping lesson words clean, browsable, and synced into Anki.

The repository is the source of truth. Anki is the spaced-repetition target, updated through AnkiConnect.

## Goals

- Keep canonical vocabulary datasets in `data/sources/`, split by source.
- Browse vocabulary through a React/Vite GitHub Pages app.
- Import HSK book vocabulary into separate source files.
- Add lesson vocabulary incrementally.
- Validate entries before syncing.
- Sync notes to Anki through AnkiConnect, without storing generated TSV exports.

## Local Workflow

```bash
npm install
npm run test
npm run build

python3 scripts/import_hsk_html.py /tmp/new-hsk-2.html --level 2 --source-url https://mandarinbean.com/new-hsk-2-word-list/ --remove-source hsk-workbook
python3 scripts/validate_vocabulary.py
python3 scripts/sync_anki.py
```

Anki must be open with the AnkiConnect add-on installed before running `sync_anki.py`.

## Data

Current source files:

- `data/sources/hsk-1.json`
- `data/sources/hsk-2.json`
- `data/sources/custom.json`
- `data/sources/index.json`

`index.json` lists source files only. Counts are derived by the app.

Vocabulary entries do not store tags. The app and Anki sync generate tags from `source`, `hsk_level`, `lesson`,
and dates. HSK lesson tags follow the Anki hierarchy format, for example `hsk1` and `HSK1::HSK:1.09`.
Custom words use `source: "custom"`, an approximate `hsk_level`, and the year in `lesson`.

`hsk-1.json` was populated from HSK Standard Course 1 pages 137-143.

## GitHub Pages

This repo already includes a GitHub Actions workflow for Pages deployment.

Live site: [bohdandan.github.io/mandarin](https://bohdandan.github.io/mandarin/)

1. Create an empty public GitHub repository.
2. Add it as `origin`.
3. Push `main`.
4. In GitHub, open `Settings` -> `Pages`.
5. Set `Build and deployment` to `GitHub Actions`.
6. Open the `Actions` tab and wait for `Deploy GitHub Pages`.
