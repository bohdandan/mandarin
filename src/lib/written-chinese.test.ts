import { describe, expect, test } from "vitest";

import { writtenChineseUrl } from "./written-chinese";

describe("writtenChineseUrl", () => {
  test("builds the dictionary url with encoded hanzi", () => {
    expect(writtenChineseUrl("我")).toBe("https://dictionary.writtenchinese.com/#sk=%E6%88%91&svt=pinyin");
    expect(writtenChineseUrl("可以")).toBe("https://dictionary.writtenchinese.com/#sk=%E5%8F%AF%E4%BB%A5&svt=pinyin");
  });
});
