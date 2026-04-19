import tempfile
import unittest
from pathlib import Path

from scripts.import_hsk_html import import_hsk_html, parse_hsk_html
from scripts.vocabulary import derive_tags, read_source_vocabulary, write_source_vocabulary
from scripts.validate_vocabulary import validate_entries


class ImportHskHtmlTest(unittest.TestCase):
    def test_parses_hsk_table_rows_and_colspan_rows(self):
        html = """
        <table>
          <tr><td><strong>No.</strong></td><td><strong>Word</strong></td><td><strong>Pinyin</strong></td><td><strong>Part of Speech</strong></td><td><strong>Translation</strong></td></tr>
          <tr><td>1</td><td>啊</td><td>a</td><td>auxiliary</td><td>ah, oh</td></tr>
          <tr><td>57</td><td>花</td><td>huā</td><td>verb</td><td>to spend</td></tr>
          <tr><td>58</td><td>花2</td><td>huā</td><td>noun</td><td>flower</td></tr>
          <tr><td>154</td><td>为什么</td><td colspan="2">wèi shénme</td><td>why</td></tr>
        </table>
        """

        entries = parse_hsk_html(html, level=2, source_url="https://example.com/hsk2")

        self.assertEqual([entry["hanzi"] for entry in entries], ["啊", "花", "花", "为什么"])
        self.assertEqual(entries[0]["id"], "hsk2-0001-a")
        self.assertEqual(entries[0]["lesson"], "HSK:2.02")
        self.assertNotIn("tags", entries[0])
        self.assertEqual(derive_tags(entries[0]), ["hsk2", "HSK2::HSK:2.02"])
        self.assertEqual(entries[2]["notes"], "Part of speech: noun; Source marker: 花2")
        self.assertEqual(entries[2]["lesson"], "HSK:2.08; HSK:2.13")
        self.assertEqual(derive_tags(entries[2]), ["hsk2", "HSK2::HSK:2.08", "HSK2::HSK:2.13"])
        self.assertEqual(entries[3]["pinyin"], "wèi shénme")
        self.assertEqual(entries[3]["lesson"], "HSK:2.03")
        self.assertEqual(derive_tags(entries[3]), ["hsk2", "HSK2::HSK:2.03"])
        self.assertEqual(validate_entries(entries), [])

    def test_import_replaces_target_and_removed_sources(self):
        html = """
        <table>
          <tr><td><strong>No.</strong></td><td><strong>Word</strong></td><td><strong>Pinyin</strong></td><td><strong>Part of Speech</strong></td><td><strong>Translation</strong></td></tr>
          <tr><td>1</td><td>啊</td><td>a</td><td>auxiliary</td><td>ah, oh</td></tr>
        </table>
        """

        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "sources"
            write_source_vocabulary(
                source_dir,
                [
                    {"id": "old", "source": "hsk-workbook", "hsk_level": 1, "hanzi": "旧", "pinyin": "jiù", "english": "old"},
                    {"id": "custom", "source": "custom", "hsk_level": 2, "hanzi": "杯子", "pinyin": "bēi zi", "english": "cup"},
                ],
            )

            import_hsk_html(html, source_dir=source_dir, level=2, remove_sources=["hsk-workbook"], source_url="https://example.com/hsk2")
            entries = read_source_vocabulary(source_dir)

        self.assertEqual([entry["source"] for entry in entries], ["custom", "hsk-2"])
        self.assertEqual([entry["hanzi"] for entry in entries], ["杯子", "啊"])


if __name__ == "__main__":
    unittest.main()
