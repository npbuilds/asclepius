"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

import { getCurrentTheme, setTheme, type Theme } from "@/lib/theme";

export function ThemeToggle() {
  const [theme, setLocalTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  // Sync from DOM after hydration. We don't read in initial useState because
  // server-side rendering can't access document. The anti-FOUC inline script
  // has already set the correct data-theme; we just observe it.
  useEffect(() => {
    setLocalTheme(getCurrentTheme());
    setMounted(true);
  }, []);

  function toggle() {
    const next: Theme = theme === "light" ? "dark" : "light";
    setLocalTheme(next);
    setTheme(next);
  }

  // Render a neutral placeholder until mounted so the icon never flips.
  if (!mounted) {
    return (
      <button
        type="button"
        aria-label="Toggle theme"
        className="inline-flex h-8 w-8 items-center justify-center rounded border border-border-dim text-text-dim"
      >
        <Sun size={14} />
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={theme === "light" ? "Switch to dark theme" : "Switch to light theme"}
      title={theme === "light" ? "Switch to dark theme" : "Switch to light theme"}
      className="inline-flex h-8 w-8 items-center justify-center rounded border border-border-dim bg-bg-panel text-text-primary transition-colors hover:border-cyan-bright hover:text-cyan-bright"
    >
      {theme === "light" ? <Moon size={14} /> : <Sun size={14} />}
    </button>
  );
}
