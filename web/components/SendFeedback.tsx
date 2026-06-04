"use client";

/**
 * v1.6 — feedback widget mounted in the global header.
 *
 * Click → modal opens with a textarea + auto-injected context (current
 * URL, asset name extracted from path, current persona from `data-persona`
 * on <html>). On submit, POST to /api/feedback. On success, the modal
 * collapses into a "thanks ✓" affordance for ~2s, then closes.
 *
 * Failure modes handled visibly:
 *   - empty body → button stays disabled (no network call)
 *   - 4xx/5xx → inline error message in the modal; the user can retry
 *     without losing their text
 *   - network failure (Fly cold start) → same as above
 *
 * Why a modal vs a route-level form: a generalist VC tester noticing
 * something mid-session shouldn't have to leave the page they're on to
 * report it. Capturing the URL automatically is how we preserve their
 * context for actionable follow-up.
 */

import { useEffect, useRef, useState } from "react";

type Status = "idle" | "sending" | "sent" | "error";

function currentAssetFromPath(pathname: string): string | null {
  // /diligence/<asset> → asset, otherwise null
  const m = pathname.match(/^\/diligence\/([^/?#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

function currentPersona(): string | null {
  if (typeof document === "undefined") return null;
  return document.documentElement.dataset.persona ?? null;
}

export function SendFeedback() {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus the textarea when the modal opens so the user can start typing
  // immediately. Small UX win that adds up in friend-test cadence.
  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  }, [open]);

  // Reset state when the modal closes so the next open is a clean slate.
  function closeModal() {
    setOpen(false);
    // Defer the body/status reset so the close transition reads cleanly.
    setTimeout(() => {
      setBody("");
      setStatus("idle");
      setErrorMsg(null);
    }, 200);
  }

  async function submit() {
    if (!body.trim() || status === "sending") return;
    setStatus("sending");
    setErrorMsg(null);
    try {
      const url = typeof window !== "undefined" ? window.location.href : null;
      const pathname = typeof window !== "undefined" ? window.location.pathname : "";
      const payload = {
        body: body.trim().slice(0, 5000),
        url,
        asset: currentAssetFromPath(pathname),
        persona: currentPersona(),
      };
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errText = await res.text().catch(() => "");
        throw new Error(errText || `HTTP ${res.status}`);
      }
      setStatus("sent");
      setTimeout(closeModal, 1800);
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Network error");
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded border border-border-dim bg-bg-panel px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-text-dim transition hover:border-magenta-bright hover:text-magenta-bright"
        aria-label="Send feedback about Asclepius"
      >
        [ feedback ]
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-bg-deep/80 backdrop-blur-sm"
          onClick={closeModal}
          role="dialog"
          aria-modal="true"
          aria-label="Send feedback"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg rounded border border-magenta-bright/40 bg-bg-panel p-4 shadow-lg"
          >
            <div className="mb-3 flex items-baseline justify-between gap-2">
              <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-magenta-bright">
                Send feedback
              </h2>
              <button
                type="button"
                onClick={closeModal}
                className="font-mono text-[11px] text-text-dim hover:text-text-bright"
                aria-label="Close feedback dialog"
              >
                [ esc ]
              </button>
            </div>

            <p className="mb-2 font-prose text-[12px] leading-snug text-text-dim">
              Any note — what surprised you, what was confusing, what you&apos;d
              want next. URL and asset are attached automatically.
            </p>

            <textarea
              ref={textareaRef}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              maxLength={5000}
              rows={6}
              placeholder="The reflexivity slider was the moment it clicked for me. But I wasn't sure what the LOA microsplit was showing in the IC Voter persona…"
              className="w-full rounded border border-border-dim bg-bg-deep p-2 font-prose text-[13px] text-text-primary placeholder:text-text-dim focus:border-magenta-bright focus:outline-none"
            />

            <div className="mt-2 flex items-center justify-between gap-2">
              <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
                {status === "sent"
                  ? "✓ sent — thanks"
                  : status === "error"
                    ? `⚠ ${errorMsg ?? "error"}`
                    : status === "sending"
                      ? "sending…"
                      : `${body.length}/5000`}
              </span>
              <button
                type="button"
                onClick={submit}
                disabled={!body.trim() || status === "sending" || status === "sent"}
                className="rounded border border-magenta-bright bg-magenta-bright/10 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-magenta-bright transition hover:bg-magenta-bright/20 disabled:cursor-not-allowed disabled:border-border-dim disabled:bg-bg-panel disabled:text-text-dim"
              >
                {status === "sending" ? "[ … ]" : status === "sent" ? "[ ✓ ]" : "[ send → ]"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
