import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { VocabularyDetailDialog } from "./vocabulary-detail";
import type { VocabularyEntry } from "./lib/vocabulary";

const entry: VocabularyEntry = {
  id: "custom-keyi",
  hanzi: "可以",
  pinyin: "kěyǐ",
  english: "can / may",
  example_sentence: "我<b>可以</b>去。",
  sentence_pinyin: "wǒ kěyǐ qù",
  sentence_translation: "I can go.",
  hsk_level: 1,
  source: "custom",
  lesson: "2026",
  notes: "Example note",
  created_at: "2026-04-22",
  updated_at: "2026-04-22",
};

describe("VocabularyDetailDialog", () => {
  test("renders the compact character breakdown link in the footer meta row", () => {
    const markup = renderToStaticMarkup(<VocabularyDetailDialog entry={entry} onClose={() => undefined} />);

    const footerStart = markup.indexOf('class="detail-meta-row"');
    const linkStart = markup.indexOf('class="detail-meta-link"');
    const pinyinStart = markup.indexOf('class="detail-pinyin-row"');
    const pinyinEnd = markup.indexOf("</div>", pinyinStart);

    expect(footerStart).toBeGreaterThan(-1);
    expect(linkStart).toBeGreaterThan(footerStart);
    expect(markup).toContain(">◫</a>");
    expect(markup).toContain('aria-label="Character breakdown"');
    expect(markup.slice(pinyinStart, pinyinEnd)).not.toContain("◫");
  });
});
