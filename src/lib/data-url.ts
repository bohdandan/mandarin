function resolveDataUrl(baseUrl: string, path: string): string {
  const trimmed = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
  return `${trimmed}${path}`;
}

export function resolveSourceIndexUrl(baseUrl: string): string {
  return resolveDataUrl(baseUrl, "/data/sources/index.json");
}

export function resolveSourceFileUrl(baseUrl: string, fileName: string): string {
  return resolveDataUrl(baseUrl, `/data/sources/${fileName}`);
}
