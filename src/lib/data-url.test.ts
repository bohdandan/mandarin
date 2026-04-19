import { describe, expect, test } from "vitest";
import { resolveSourceFileUrl, resolveSourceIndexUrl } from "./data-url";

describe("source data URLs", () => {
  test("resolves source index and source files for local and GitHub Pages base paths", () => {
    expect(resolveSourceIndexUrl("/")).toBe("/data/sources/index.json");
    expect(resolveSourceIndexUrl("/Mandarin/")).toBe("/Mandarin/data/sources/index.json");
    expect(resolveSourceFileUrl("/", "hsk-workbook.json")).toBe("/data/sources/hsk-workbook.json");
    expect(resolveSourceFileUrl("/Mandarin/", "custom.json")).toBe("/Mandarin/data/sources/custom.json");
  });
});
