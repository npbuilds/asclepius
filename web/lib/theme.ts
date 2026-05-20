// Theme utility — single source for theme name / persistence / DOM application.
//
// `setTheme` writes to localStorage AND applies the `data-theme` attribute on
// <html>. The anti-FOUC inline script in layout.tsx reads the same key on
// first paint so the page never flashes the wrong theme.

export type Theme = "light" | "dark";

export const THEME_KEY = "asclepius_theme";
export const DEFAULT_THEME: Theme = "light";

export function setTheme(theme: Theme): void {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = theme;
  }
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(THEME_KEY, theme);
    } catch {
      // localStorage may be unavailable (private mode, iframe, etc.) — ignore.
    }
  }
}

export function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(THEME_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

export function getCurrentTheme(): Theme {
  if (typeof document === "undefined") return DEFAULT_THEME;
  const attr = document.documentElement.dataset.theme;
  return attr === "dark" ? "dark" : "light";
}

// Inline script that runs in <head> before any paint. Reads localStorage and
// sets data-theme on <html> synchronously, eliminating the flash-of-wrong-theme.
// Returned as a string so it can be injected via dangerouslySetInnerHTML.
export const ANTI_FOUC_SCRIPT = `
(function(){
  try {
    var t = localStorage.getItem(${JSON.stringify(THEME_KEY)});
    if (t === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.setAttribute("data-theme", "light");
    }
  } catch(e) {
    document.documentElement.setAttribute("data-theme", "light");
  }
})();
`.trim();
