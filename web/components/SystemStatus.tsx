"use client";

// Terminal-style system readout for the landing page.
// Three rows with ● status dots: live API ping, current theme, build date.
// Reads as a CLI tool's status output. Each row is mono, fixed-width-ish via
// a 3-column grid: dot · label · value.

import { useEffect, useRef, useState } from "react";

import { getCurrentTheme, type Theme } from "@/lib/theme";

export type HealthStatus = "checking" | "online" | "offline";
type ApiStatus = HealthStatus;

const BUILD_DATE = "2026-05-20";

interface SystemStatusProps {
  /** Optional callback fired whenever the live API health status changes.
   * Lets a parent (e.g. the landing page) render a degraded-mode banner
   * without duplicating the /health ping. */
  onStatusChange?: (status: HealthStatus) => void;
}

export function SystemStatus({ onStatusChange }: SystemStatusProps = {}) {
  const [api, setApi] = useState<ApiStatus>("checking");
  const [theme, setThemeState] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  // Stash the latest callback in a ref so the mount effect can stay
  // dependency-free — we don't want to re-ping /health if the parent
  // passes a fresh inline closure on every render.
  const onStatusChangeRef = useRef(onStatusChange);
  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
  }, [onStatusChange]);

  useEffect(() => {
    setMounted(true);
    setThemeState(getCurrentTheme());

    // Ping /api/health via the Next.js proxy. Aborts on unmount.
    const ctrl = new AbortController();
    const report = (s: ApiStatus) => {
      setApi(s);
      onStatusChangeRef.current?.(s);
    };
    fetch("/health", { signal: ctrl.signal, cache: "no-store" })
      .then((r) => report(r.ok ? "online" : "offline"))
      .catch(() => report("offline"));

    // Watch for theme changes via a MutationObserver on the <html> data-theme attr.
    const obs = new MutationObserver(() => setThemeState(getCurrentTheme()));
    obs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    return () => {
      ctrl.abort();
      obs.disconnect();
    };
  }, []);

  const apiDot =
    api === "online"
      ? "text-green-bright"
      : api === "offline"
        ? "text-red-bright"
        : "text-text-dim";
  const apiText =
    api === "online" ? "ONLINE" : api === "offline" ? "OFFLINE" : "CHECKING";

  return (
    <div className="font-mono text-[11px] uppercase tracking-wider text-text-primary">
      <div className="mb-2 text-text-dim">
        ── SYSTEM ────────────────────────────────────
      </div>
      <div className="grid grid-cols-[auto_auto_1fr] gap-x-3 gap-y-1">
        <span className={apiDot}>●</span>
        <span className="text-text-dim">API</span>
        <span className="text-text-bright">
          {mounted ? "asclepius-api.fly.dev " : ""}
          <span className={apiDot}>{apiText}</span>
        </span>

        <span className="text-cyan-bright">●</span>
        <span className="text-text-dim">Theme</span>
        <span className="text-text-bright">{mounted ? theme : "—"}</span>

        <span className="text-cyan-faded">●</span>
        <span className="text-text-dim">Build</span>
        <span className="text-text-bright">{BUILD_DATE}</span>
      </div>
    </div>
  );
}
