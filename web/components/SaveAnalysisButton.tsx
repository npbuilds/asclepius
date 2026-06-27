"use client";

// Save-analysis control for the ActionSection "Other" strip. Persists the
// current computed record to the saved-analyses store (gated behind the shared
// access passphrase). On success it flips to a link to the library.

import Link from "next/link";
import { useState } from "react";

import { saveAnalysis } from "@/lib/api-client";
import type { ClientDiligenceRecord } from "@/lib/module-registry";

type Status = "idle" | "saving" | "saved" | "error";

export function SaveAnalysisButton({ record }: { record: ClientDiligenceRecord }) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setStatus("saving");
    setError(null);
    try {
      await saveAnalysis(record as unknown as Record<string, unknown>);
      setStatus("saved");
    } catch (e) {
      const err = e as { status?: number; message?: string };
      setError(err.status === 403 ? "access required" : err.message ?? "save failed");
      setStatus("error");
    }
  }

  if (status === "saved") {
    return (
      <Link
        href="/analyses"
        className="rounded border border-green-bright/40 bg-green-bright/10 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-green-bright hover:bg-green-bright/20"
      >
        [ ✓ saved · view all → ]
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={save}
      disabled={status === "saving"}
      title={error ?? "Save this analysis to revisit later"}
      className="rounded border border-magenta-bright/40 bg-magenta-bright/10 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-magenta-bright hover:bg-magenta-bright/20 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {status === "saving"
        ? "[ saving… ]"
        : status === "error"
          ? `[ retry save${error ? ` · ${error}` : ""} ]`
          : "[ save analysis → ]"}
    </button>
  );
}
