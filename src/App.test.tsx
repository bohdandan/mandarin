import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import App from "./App";

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
    expect(markup).not.toContain("复习 words that are ready for Anki.");
    expect(markup).not.toContain('class="header-image"');
    expect(markup).not.toContain('class="eyebrow"');
  });
});
