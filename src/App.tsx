import { useEffect, useMemo, useState } from "react";
import { resolveSourceFileUrl, resolveSourceIndexUrl } from "./lib/data-url";
import { getNextTheme, resolveInitialTheme, type ThemeName } from "./lib/theme";
import {
  filterVocabulary,
  getDisplayTags,
  getVocabularyStats,
  type VocabularyEntry,
  type VocabularyFilters,
} from "./lib/vocabulary";
import { VocabularyDetailDialog } from "./vocabulary-detail";

type SourceIndex = {
  sources: { source: string; file: string }[];
};

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) => a.localeCompare(b));
}

function levelLabel(level: string): string {
  return level === "custom" ? "Custom" : `HSK ${level}`;
}

function App() {
  const [entries, setEntries] = useState<VocabularyEntry[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [theme, setTheme] = useState<ThemeName>(() => resolveInitialTheme(localStorage.getItem("mandarin-theme")));
  const [search, setSearch] = useState("");
  const [hskLevel, setHskLevel] = useState<VocabularyFilters["hskLevel"]>("");
  const [source, setSource] = useState("");
  const [lesson, setLesson] = useState("");
  const [tag, setTag] = useState("");
  const [selectedEntry, setSelectedEntry] = useState<VocabularyEntry | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("mandarin-theme", theme);
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    fetch(resolveSourceIndexUrl(import.meta.env.BASE_URL))
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Source index request failed with ${response.status}`);
        }
        return response.json() as Promise<SourceIndex>;
      })
      .then((index) => {
        return Promise.all(
          index.sources.map((source) =>
            fetch(resolveSourceFileUrl(import.meta.env.BASE_URL, source.file)).then((response) => {
              if (!response.ok) {
                throw new Error(`Source request failed with ${response.status}`);
              }
              return response.json() as Promise<VocabularyEntry[]>;
            }),
          ),
        );
      })
      .then((sourceEntries) => sourceEntries.flat())
      .then((nextEntries) => {
        if (!cancelled) {
          setEntries(nextEntries);
          setLoadState("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoadState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => getVocabularyStats(entries), [entries]);
  const sources = useMemo(() => uniqueSorted(entries.map((entry) => entry.source)), [entries]);
  const lessons = useMemo(() => uniqueSorted(entries.map((entry) => entry.lesson)), [entries]);
  const tags = useMemo(() => uniqueSorted(entries.flatMap((entry) => getDisplayTags(entry))), [entries]);
  const hskLevels = useMemo(
    () =>
      Array.from(new Set(entries.map((entry) => entry.hsk_level).filter((level): level is number => level !== null))).sort(
        (a, b) => a - b,
      ),
    [entries],
  );

  const filteredEntries = useMemo(
    () => filterVocabulary(entries, { search, hskLevel, source, lesson, tag }),
    [entries, search, hskLevel, source, lesson, tag],
  );

  function applyLevelFilter(level: string) {
    setHskLevel((current) => {
      const next = level === "custom" ? "custom" : Number(level);
      return current === next ? "" : next;
    });
    setSource("");
    setLesson("");
    setTag("");
  }

  return (
    <main className="app-shell">
      <section className="library-header" aria-labelledby="page-title">
        <div className="header-copy">
          <div className="topline">
            <h1 id="page-title">普通话词汇</h1>
            <button
              aria-label={theme === "dracula" ? "Switch to light theme" : "Switch to Dracula theme"}
              className="theme-toggle"
              title={theme === "dracula" ? "Switch to light theme" : "Switch to Dracula theme"}
              type="button"
              onClick={() => setTheme(getNextTheme(theme))}
            >
              <span aria-hidden="true">{theme === "dracula" ? "☀" : "☾"}</span>
            </button>
          </div>
          <div className="search-row">
            <label className="search-label" htmlFor="search">
              Search
            </label>
            <input
              id="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Hanzi, pinyin, meaning, examples"
              type="search"
            />
          </div>
        </div>
      </section>

      <section className="summary-line" aria-label="Vocabulary summary">
        <p>
          <strong>{filteredEntries.length}</strong> shown from <strong>{stats.total}</strong> words
        </p>
        {(hskLevel || source || lesson || tag || search) && (
          <button
            type="button"
            onClick={() => {
              setSearch("");
              setHskLevel("");
              setSource("");
              setLesson("");
              setTag("");
            }}
          >
            Clear filters
          </button>
        )}
      </section>

      <section className="stats-strip" aria-label="Vocabulary level filters">
        {Object.entries(stats.byHskLevel)
          .filter(([level]) => level !== "custom")
          .map(([level, count]) => (
            <button
              className={hskLevel === Number(level) ? "active-stat" : ""}
              key={level}
              type="button"
              onClick={() => applyLevelFilter(level)}
            >
              <span>{count}</span>
              <p>{levelLabel(level)}</p>
            </button>
          ))}
        <button
          className={hskLevel === "custom" ? "active-stat" : ""}
          type="button"
          onClick={() => applyLevelFilter("custom")}
        >
          <span>{stats.custom}</span>
          <p>Custom</p>
        </button>
      </section>

      <section className="filters" aria-label="Vocabulary filters">
        <label>
          HSK
          <select
            value={String(hskLevel)}
            onChange={(event) => {
              const value = event.target.value;
              setHskLevel(value === "" ? "" : value === "custom" ? "custom" : Number(value));
            }}
          >
            <option value="">All levels</option>
            {hskLevels.map((level) => (
              <option key={level} value={level}>
                HSK {level}
              </option>
            ))}
            <option value="custom">Custom</option>
          </select>
        </label>

        <label>
          Source
          <select value={source} onChange={(event) => setSource(event.target.value)}>
            <option value="">All sources</option>
            {sources.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label>
          Lesson
          <select value={lesson} onChange={(event) => setLesson(event.target.value)}>
            <option value="">All lessons</option>
            {lessons.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label>
          Tag
          <select value={tag} onChange={(event) => setTag(event.target.value)}>
            <option value="">All tags</option>
            {tags.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="word-list" aria-live="polite">
        {loadState === "loading" ? <p className="status-message">Loading vocabulary...</p> : null}
        {loadState === "error" ? <p className="status-message">Vocabulary could not be loaded.</p> : null}
        {filteredEntries.map((entry) => (
          <button
            className="word-row"
            key={entry.id}
            type="button"
            onClick={() => setSelectedEntry(entry)}
          >
            <span className="row-hanzi">{entry.hanzi}</span>
            <span className="row-pinyin">{entry.pinyin}</span>
            <span className="row-meaning">{entry.english}</span>
            <span className="row-example" dangerouslySetInnerHTML={{ __html: entry.example_sentence }} />
            <span className="row-level">
              {entry.source === "custom"
                ? `Custom · HSK ${entry.hsk_level ?? "?"}`
                : entry.hsk_level
                  ? `HSK ${entry.hsk_level}`
                  : "HSK ?"}
            </span>
          </button>
        ))}
      </section>

      {selectedEntry ? (
        <div className="detail-backdrop" role="presentation" onClick={() => setSelectedEntry(null)}>
          <VocabularyDetailDialog entry={selectedEntry} onClose={() => setSelectedEntry(null)} />
        </div>
      ) : null}
    </main>
  );
}

export default App;
