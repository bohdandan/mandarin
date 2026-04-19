export type ThemeName = "light" | "dracula";

export function resolveInitialTheme(savedTheme: string | null): ThemeName {
  return savedTheme === "dracula" || savedTheme === "light" ? savedTheme : "dracula";
}

export function getNextTheme(theme: ThemeName): ThemeName {
  return theme === "light" ? "dracula" : "light";
}
