export function writtenChineseUrl(hanzi: string): string {
  return `https://dictionary.writtenchinese.com/#sk=${encodeURIComponent(hanzi)}&svt=pinyin`;
}
