import { describe, expect, test } from "vitest";
import { filterVocabulary, getDisplayTags, getVocabularyStats, type VocabularyEntry } from "./vocabulary";

const entries: VocabularyEntry[] = [
  {
    id: "hsk1-0001-ni-hao",
    hanzi: "你好",
    pinyin: "nǐ hǎo",
    english: "hello",
    example_sentence: "<b>你好</b>！",
    sentence_pinyin: "nǐ hǎo",
    sentence_translation: "",
    hsk_level: 1,
    source: "hsk-workbook",
    lesson: "HSK:1.01",
    notes: "",
    created_at: "2026-04-19",
    updated_at: "2026-04-19",
  },
  {
    id: "custom-bei-zi",
    hanzi: "杯子",
    pinyin: "bēi zi",
    english: "cup",
    example_sentence: "这是我的<b>杯子</b>。",
    sentence_pinyin: "",
    sentence_translation: "",
    hsk_level: 2,
    source: "custom",
    lesson: "2026",
    notes: "",
    created_at: "2026-04-19",
    updated_at: "2026-04-19",
  },
];

describe("getVocabularyStats", () => {
  test("counts total entries, HSK levels, and custom entries", () => {
    expect(getVocabularyStats(entries)).toEqual({
      total: 2,
      byHskLevel: { "1": 1, "2": 1 },
      custom: 1,
    });
  });
});

describe("filterVocabulary", () => {
  test("searches hanzi, pinyin, english, examples, and generated tags", () => {
    expect(filterVocabulary(entries, { search: "bei" }).map((entry) => entry.hanzi)).toEqual(["杯子"]);
    expect(filterVocabulary(entries, { search: "hello" }).map((entry) => entry.hanzi)).toEqual(["你好"]);
    expect(filterVocabulary(entries, { search: "added-2026" }).map((entry) => entry.hanzi)).toEqual(["杯子"]);
  });

  test("matches pinyin when the search query omits spaces and tone marks", () => {
    expect(filterVocabulary(entries, { search: "nihao" }).map((entry) => entry.hanzi)).toEqual(["你好"]);
    expect(filterVocabulary(entries, { search: "beizi" }).map((entry) => entry.hanzi)).toEqual(["杯子"]);
  });

  test("filters by HSK level, source, lesson, and tag", () => {
    expect(filterVocabulary(entries, { hskLevel: 1 }).map((entry) => entry.hanzi)).toEqual(["你好"]);
    expect(filterVocabulary(entries, { hskLevel: 2 }).map((entry) => entry.hanzi)).toEqual(["杯子"]);
    expect(filterVocabulary(entries, { hskLevel: "custom" }).map((entry) => entry.hanzi)).toEqual(["杯子"]);
    expect(filterVocabulary(entries, { source: "custom" }).map((entry) => entry.hanzi)).toEqual(["杯子"]);
    expect(filterVocabulary(entries, { lesson: "HSK:1.01" }).map((entry) => entry.hanzi)).toEqual(["你好"]);
    expect(filterVocabulary(entries, { tag: "added-2026" }).map((entry) => entry.hanzi)).toEqual(["杯子"]);
  });
});

describe("getDisplayTags", () => {
  test("generates HSK tags from level and lesson", () => {
    expect(getDisplayTags(entries[0])).toEqual(["hsk1", "HSK1::HSK:1.01"]);
  });

  test("generates custom and added-year tags without stored tags", () => {
    expect(
      getDisplayTags({
        ...entries[1],
      }),
    ).toEqual(["hsk2", "custom", "added-2026"]);
  });
});
