from __future__ import annotations

import unittest

from scripts.google_tts import (
    GoogleTtsConfig,
    build_ssml,
    google_media_filename,
    load_google_tts_config,
    marked_pinyin_to_numbered_pinyin,
)


class GoogleTtsTests(unittest.TestCase):
    def test_load_google_tts_config_requires_project(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "GOOGLE_CLOUD_PROJECT"):
            load_google_tts_config({}, adc_credentials={})

    def test_load_google_tts_config_uses_defaults(self) -> None:
        config = load_google_tts_config({"GOOGLE_CLOUD_PROJECT": "mandarin-dev"}, adc_credentials={})

        self.assertEqual(
            config,
            GoogleTtsConfig(
                project_id="mandarin-dev",
                voice_name="cmn-CN-Wavenet-A",
                audio_encoding="MP3",
            ),
        )

    def test_load_google_tts_config_falls_back_to_adc_quota_project(self) -> None:
        config = load_google_tts_config({}, adc_credentials={"quota_project_id": "mandarin-dev"})

        self.assertEqual(config.project_id, "mandarin-dev")

    def test_marked_pinyin_to_numbered_pinyin(self) -> None:
        self.assertEqual(marked_pinyin_to_numbered_pinyin("可以", "kě yǐ"), "ke3 yi3")
        self.assertEqual(marked_pinyin_to_numbered_pinyin("加油", "jiāyóu"), "jia1 you2")
        self.assertEqual(marked_pinyin_to_numbered_pinyin("地方", "dìfāng"), "di4 fang1")

    def test_build_ssml_uses_mandarin_phoneme(self) -> None:
        ssml = build_ssml("可以", "kě yǐ")

        self.assertEqual(
            ssml,
            '<speak><phoneme alphabet="pinyin" ph="ke3 yi3">可以</phoneme></speak>',
        )

    def test_google_media_filename_uses_voice_and_encoding(self) -> None:
        config = GoogleTtsConfig(project_id="mandarin-dev", voice_name="cmn-CN-Wavenet-A", audio_encoding="MP3")
        entry = {"id": "custom-word", "hanzi": "可以", "pinyin": "kě yǐ"}

        self.assertEqual(
            google_media_filename(entry, config),
            "custom-word_google-cmn-cn-wavenet-a.mp3",
        )


if __name__ == "__main__":
    unittest.main()
