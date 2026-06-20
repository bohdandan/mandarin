import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import App, { VocabularyRow } from "./App";
import type { VocabularyEntry } from "./lib/vocabulary";

const rowEntry: VocabularyEntry = {
  id: "hsk1-nihao",
  hanzi: "你好",
  pinyin: "nǐ hǎo",
  english: "hello",
  example_sentence: "老师，<b>你好</b>！",
  sentence_pinyin: "",
  sentence_translation: "Hello, teacher!",
  hsk_level: 1,
  source: "hsk-1",
  lesson: "HSK:1.01",
  notes: "",
  created_at: "2026-04-01",
  updated_at: "2026-04-01",
};

describe("App header", () => {
  const originalLocalStorage = globalThis.localStorage;

  beforeEach(() => {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: {
        getItem: vi.fn(() => "dracula"),
        setItem: vi.fn(),
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: originalLocalStorage,
    });
  });

  test("renders the slim header without the old review title or image", () => {
    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain('<h1 id="page-title">普通话词汇</h1>');
    expect(markup).toContain('href="https://github.com/bohdandan/mandarin"');
    expect(markup).not.toContain("复习 words that are ready for Anki.");
    expect(markup).not.toContain('class="header-image"');
    expect(markup).not.toContain('class="eyebrow"');
  });

  test("renders example sentence translations in vocabulary rows", () => {
    const markup = renderToStaticMarkup(<VocabularyRow entry={rowEntry} onSelect={() => undefined} />);

    expect(markup).toContain('class="row-example-cell"');
    expect(markup).toContain("老师，<b>你好</b>！");
    expect(markup).toContain('class="row-translation"');
    expect(markup).toContain("Hello, teacher!");
  });
});
