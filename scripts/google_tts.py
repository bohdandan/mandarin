from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from scripts.chinese_support import latin_guide_syllables, primary_citation_pinyin, split_marked_pinyin_by_guide


GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_ADC_PATH = Path.home() / ".config/gcloud/application_default_credentials.json"
DEFAULT_VOICE_NAME = "cmn-CN-Wavenet-A"
DEFAULT_AUDIO_ENCODING = "MP3"
PINYIN_TONE_MARKS = {
    "ā": ("a", 1),
    "á": ("a", 2),
    "ǎ": ("a", 3),
    "à": ("a", 4),
    "ē": ("e", 1),
    "é": ("e", 2),
    "ě": ("e", 3),
    "è": ("e", 4),
    "ī": ("i", 1),
    "í": ("i", 2),
    "ǐ": ("i", 3),
    "ì": ("i", 4),
    "ō": ("o", 1),
    "ó": ("o", 2),
    "ǒ": ("o", 3),
    "ò": ("o", 4),
    "ū": ("u", 1),
    "ú": ("u", 2),
    "ǔ": ("u", 3),
    "ù": ("u", 4),
    "ǖ": ("ü", 1),
    "ǘ": ("ü", 2),
    "ǚ": ("ü", 3),
    "ǜ": ("ü", 4),
}


@dataclass(frozen=True)
class GoogleTtsConfig:
    project_id: str
    voice_name: str = DEFAULT_VOICE_NAME
    audio_encoding: str = DEFAULT_AUDIO_ENCODING


def load_adc_credentials(adc_path: Path = DEFAULT_ADC_PATH) -> dict[str, str]:
    if not adc_path.exists():
        raise RuntimeError("Google ADC credentials not found. Run `gcloud auth application-default login`.")
    data = json.loads(adc_path.read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in data.items() if value is not None}


def load_google_tts_config(
    env: Mapping[str, str] | None = None,
    *,
    adc_credentials: Mapping[str, str] | None = None,
) -> GoogleTtsConfig:
    values = env if env is not None else os.environ
    adc = adc_credentials if adc_credentials is not None else load_adc_credentials()
    project_id = str(values.get("GOOGLE_CLOUD_PROJECT") or adc.get("quota_project_id") or "").strip()
    if not project_id:
        raise RuntimeError("Missing GOOGLE_CLOUD_PROJECT for Google TTS.")
    voice_name = str(values.get("GOOGLE_TTS_VOICE_NAME") or DEFAULT_VOICE_NAME).strip() or DEFAULT_VOICE_NAME
    audio_encoding = str(values.get("GOOGLE_TTS_AUDIO_ENCODING") or DEFAULT_AUDIO_ENCODING).strip().upper() or DEFAULT_AUDIO_ENCODING
    return GoogleTtsConfig(project_id=project_id, voice_name=voice_name, audio_encoding=audio_encoding)


def numbered_pinyin_syllable(marked_syllable: str) -> str:
    tone = 5
    letters: list[str] = []
    for char in marked_syllable:
        replacement = PINYIN_TONE_MARKS.get(char)
        if replacement is not None:
            base, tone = replacement
            letters.append(base)
        else:
            letters.append(char)
    return f"{''.join(letters)}{tone}"


def marked_pinyin_to_numbered_pinyin(hanzi: str, marked_pinyin: str) -> str:
    citation = primary_citation_pinyin(marked_pinyin)
    guide = latin_guide_syllables(hanzi)
    tokens = split_marked_pinyin_by_guide(citation, guide)
    return " ".join(numbered_pinyin_syllable(token) for token in tokens)


def build_ssml(hanzi: str, marked_pinyin: str) -> str:
    numbered = marked_pinyin_to_numbered_pinyin(hanzi, marked_pinyin)
    return f'<speak><phoneme alphabet="pinyin" ph="{numbered}">{hanzi}</phoneme></speak>'


def google_media_filename(entry: dict[str, Any], config: GoogleTtsConfig) -> str:
    extension = config.audio_encoding.lower()
    voice_slug = re.sub(r"[^a-z0-9]+", "-", config.voice_name.lower()).strip("-")
    return f"{entry['id']}_google-{voice_slug}.{extension}"


def google_access_token(adc_credentials: Mapping[str, str] | None = None) -> str:
    adc = adc_credentials if adc_credentials is not None else load_adc_credentials()
    refresh_token = str(adc.get("refresh_token") or "").strip()
    client_id = str(adc.get("client_id") or "").strip()
    client_secret = str(adc.get("client_secret") or "").strip()
    if not refresh_token or not client_id or not client_secret:
        raise RuntimeError("Google ADC credentials are incomplete. Re-run `gcloud auth application-default login`.")

    payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    token = str(body.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Google ADC is configured, but no access token was returned.")
    return token


def synthesize_audio(entry: dict[str, Any], config: GoogleTtsConfig) -> tuple[str, bytes]:
    token = google_access_token()
    payload = json.dumps(
        {
            "input": {"ssml": build_ssml(str(entry["hanzi"]), str(entry["pinyin"]))},
            "voice": {
                "languageCode": "cmn-CN",
                "name": config.voice_name,
            },
            "audioConfig": {"audioEncoding": config.audio_encoding},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GOOGLE_TTS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "x-goog-user-project": config.project_id,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    audio_content = body.get("audioContent")
    if not audio_content:
        raise RuntimeError("Google TTS returned no audio content.")
    return google_media_filename(entry, config), base64.b64decode(audio_content)
