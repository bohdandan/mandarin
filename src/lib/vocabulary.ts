export type VocabularyEntry = {
  id: string;
  hanzi: string;
  pinyin: string;
  english: string;
  example_sentence: string;
  sentence_pinyin: string;
  sentence_translation: string;
  hsk_level: number | null;
  source: string;
  lesson: string;
  tags?: string[];
  notes: string;
  created_at: string;
  updated_at: string;
};

export type VocabularyFilters = {
  search?: string;
  hskLevel?: number | "custom" | "";
  source?: string;
  lesson?: string;
  tag?: string;
};

export type VocabularyStats = {
  total: number;
  byHskLevel: Record<string, number>;
  custom: number;
};

function normalizeSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function compactSearch(value: string): string {
  return normalizeSearch(value).replace(/\s+/g, "");
}

function searchableText(entry: VocabularyEntry): string {
  const fields = [
    entry.hanzi,
    entry.pinyin,
    entry.english,
    entry.example_sentence,
    entry.sentence_pinyin,
    entry.sentence_translation,
    entry.source,
    entry.lesson,
    getDisplayTags(entry).join(" "),
    entry.notes,
  ];
  const spaced = normalizeSearch(fields.join(" "));
  const compactPinyin = [entry.pinyin, entry.sentence_pinyin].map(compactSearch).join(" ");
  return `${spaced} ${compactPinyin}`;
}

export function getVocabularyStats(entries: VocabularyEntry[]): VocabularyStats {
  const byHskLevel: Record<string, number> = {};
  let custom = 0;

  for (const entry of entries) {
    const key = entry.hsk_level === null ? "custom" : String(entry.hsk_level);
    byHskLevel[key] = (byHskLevel[key] ?? 0) + 1;
    if (entry.hsk_level === null || entry.source === "custom") {
      custom += 1;
    }
  }

  return { total: entries.length, byHskLevel, custom };
}

export function filterVocabulary(entries: VocabularyEntry[], filters: VocabularyFilters): VocabularyEntry[] {
  const query = normalizeSearch(filters.search?.trim() ?? "");
  const compactQuery = compactSearch(filters.search?.trim() ?? "");

  return entries.filter((entry) => {
    const haystack = searchableText(entry);
    if (query && !haystack.includes(query) && !haystack.includes(compactQuery)) {
      return false;
    }
    if (filters.hskLevel !== undefined && filters.hskLevel !== "") {
      if (filters.hskLevel === "custom") {
        if (entry.source !== "custom") return false;
      } else if (entry.hsk_level !== filters.hskLevel) {
        return false;
      }
    }
    if (filters.source && entry.source !== filters.source) {
      return false;
    }
    if (filters.lesson && entry.lesson !== filters.lesson) {
      return false;
    }
    if (filters.tag && !getDisplayTags(entry).includes(filters.tag)) {
      return false;
    }
    return true;
  });
}

function uniqueOrdered(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function formatHskLessonTag(level: string, lesson: string): string {
  return `HSK${level}::HSK:${level}.${lesson.padStart(2, "0")}`;
}

function parseHskLessonTags(value: string): string[] {
  const tags: string[] = [];
  for (const match of value.matchAll(/HSK(\d+)::HSK:(\d+)\.(\d+)/g)) {
    if (match[1] === match[2]) {
      tags.push(formatHskLessonTag(match[1], match[3]));
    }
  }
  for (const match of value.matchAll(/HSK:(\d+)\.(\d+)/g)) {
    tags.push(formatHskLessonTag(match[1], match[2]));
  }
  return uniqueOrdered(tags);
}

function addedYearTag(entry: VocabularyEntry): string {
  const lessonYear = entry.lesson.match(/^(\d{4})/)?.[1];
  const createdYear = entry.created_at.match(/^(\d{4})/)?.[1];
  const year = lessonYear ?? createdYear;
  return year ? `added-${year}` : "";
}

export function getDisplayTags(entry: VocabularyEntry): string[] {
  const tags: string[] = [];
  if (entry.hsk_level !== null) {
    tags.push(`hsk${entry.hsk_level}`);
  }
  tags.push(...parseHskLessonTags(entry.lesson));
  if (entry.source === "custom") {
    tags.push("custom");
    tags.push(addedYearTag(entry));
  }
  if (entry.lesson.startsWith("lesson-")) {
    tags.push(entry.lesson);
  }
  return uniqueOrdered(tags);
}
