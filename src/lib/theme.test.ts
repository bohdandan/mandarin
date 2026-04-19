import { describe, expect, test } from "vitest";
import { getNextTheme, resolveInitialTheme, type ThemeName } from "./theme";

describe("resolveInitialTheme", () => {
  test("uses the saved theme when it is valid", () => {
    expect(resolveInitialTheme("dracula")).toBe("dracula");
    expect(resolveInitialTheme("light")).toBe("light");
  });

  test("falls back to dracula for missing or unknown values", () => {
    expect(resolveInitialTheme(null)).toBe("dracula");
    expect(resolveInitialTheme("midnight")).toBe("dracula");
  });
});

describe("getNextTheme", () => {
  test("toggles between light and dracula", () => {
    expect(getNextTheme("light" satisfies ThemeName)).toBe("dracula");
    expect(getNextTheme("dracula" satisfies ThemeName)).toBe("light");
  });
});
