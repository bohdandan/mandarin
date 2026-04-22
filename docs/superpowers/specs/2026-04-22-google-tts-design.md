# Google TTS Design

## Goal

Replace local macOS `say` generation for repo-managed custom-word audio with Google Cloud Text-to-Speech, while keeping regeneration explicit and limited to selected words.

## Scope

- Add a Google TTS provider for repo-generated audio.
- Use local Application Default Credentials through `gcloud auth application-default login`.
- Keep normal custom sync behavior unchanged unless audio regeneration is explicitly requested.
- Fail clearly when Google auth or required configuration is missing.

## Non-Goals

- Bulk-regenerating all existing custom audio by default
- Replacing legacy HSK deck audio
- Supporting multiple cloud providers in the same change

## Design

### Provider boundary

Create a small provider module responsible for:

- validating Google TTS configuration
- converting repo pinyin into Google-compatible Mandarin phoneme input
- fetching an access token from ADC
- calling the Google Cloud Text-to-Speech REST API
- returning a media filename and `[sound:...]` reference after storing the bytes in Anki

The custom sync script stays responsible for deciding when audio should be generated.

### Pronunciation strategy

Use SSML with a Mandarin phoneme tag so synthesis follows repo pinyin rather than guessing from Hanzi:

- wrap the Hanzi in `<phoneme alphabet="pinyin" ...>`
- convert marked pinyin such as `kě yǐ` into numbered pinyin such as `ke3 yi3`

This follows Google’s Mandarin phoneme support and should produce more stable single-word pronunciation than raw Hanzi input.

### Regeneration behavior

Normal sync keeps existing audio untouched.

Add explicit CLI targeting for regeneration:

- `--regenerate-audio` enables replacing audio for matching entries
- `--audio-target` accepts repeated Hanzi or entry ids

Without targets, regeneration is not attempted. This keeps the first rollout safe and reviewable.

### Configuration

Use environment variables:

- optional `GOOGLE_CLOUD_PROJECT`, with fallback to the ADC quota project
- optional `GOOGLE_TTS_VOICE_NAME`, default `cmn-CN-Wavenet-A`
- optional `GOOGLE_TTS_AUDIO_ENCODING`, default `MP3`

Authentication comes from ADC. Missing ADC or missing project id causes a hard failure with a clear message.

### File impacts

- add a focused Google TTS helper module in `scripts/`
- update `scripts/sync_custom_to_chinese_support.py`
- extend tests for config, phoneme conversion, targeting, and filename behavior
- document Google setup and regeneration usage in `README.md`
