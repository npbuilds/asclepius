"use client";

// Saved-analyses library — lists persisted diligence records as cards, each
// linking back into the full workbench via /diligence/<slug>?analysis_id=<id>.
// Reads from the gated /api/analyses endpoint (attaches the access token).

import Link from "next/link";
import { useEffect, useState } from "react";

import { deleteAnalysis, listAnalyses } from "@/lib/api-client";
import type { AnalysisSummary } from "@/lib/types";

function slugify(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "") || "asset"
  );
}

function fmtUsd(v: number | null): string {
  if (v == null) return "—";
  return `$${Math.round(v).toLocaleString()}M`;
}

function fmtPct(v: number | null): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function fmtDate(unixSec: number): string {
  return new Date(unixSec * 1000).toISOString().slice(0, 10);
}

export default function AnalysesPage() {
  const [items, setItems] = useState<AnalysisSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listAnalyses()
      .then((data) => !cancelled && setItems(data))
      .catch((e) => {
        if (cancelled) return;
        const err = e as { status?: number; message?: string };
        setError(
          err.status === 403
            ? "Access required — open the app via your ?access= link first."
            : err.message ?? "Could not load saved analyses.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function remove(id: string) {
    await deleteAnalysis(id).catch(() => {});
    setItems((prev) => prev?.filter((a) => a.id !== id) ?? null);
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-6 border-b border-border-dim pb-3">
        <div className="flex items-center justify-between gap-3">
          <h1 className="font-display text-lg uppercase tracking-wider text-text-bright">
            Saved analyses
          </h1>
          <Link
            href="/"
            className="font-mono text-[11px] uppercase tracking-wider text-text-dim hover:text-cyan-bright"
          >
            [ ← home ]
          </Link>
        </div>
        <p className="mt-1 font-prose text-[13px] text-text-dim">
          A library of researched assets — reload any to revisit the full workbench.
        </p>
      </header>

      {error ? (
        <div className="rounded border border-red-bright/30 bg-red-bright/10 p-3 font-mono text-[12px] text-red-bright">
          {error}
        </div>
      ) : null}

      {items && items.length === 0 ? (
        <p className="font-prose text-[13px] text-text-dim">
          No saved analyses yet. Run a diligence and click{" "}
          <span className="text-magenta-bright">save analysis</span> in the
          Take-action section.
        </p>
      ) : null}

      {items === null && !error ? (
        <p className="font-mono text-[11px] uppercase tracking-wider text-text-dim">
          loading…
        </p>
      ) : null}

      <ul className="space-y-2">
        {(items ?? []).map((a) => (
          <li
            key={a.id}
            className="rounded border border-border-dim bg-bg-panel p-3"
          >
            <div className="flex items-center justify-between gap-3">
              <Link
                href={`/diligence/${slugify(a.asset_name)}?analysis_id=${a.id}`}
                className="font-display text-[14px] text-cyan-bright hover:underline"
              >
                {a.asset_name}
                {a.label ? ` — ${a.label}` : ""}
              </Link>
              <button
                type="button"
                onClick={() => remove(a.id)}
                className="font-mono text-[10px] uppercase tracking-wider text-text-dim hover:text-red-bright"
              >
                [ delete ]
              </button>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[10px] uppercase tracking-wider text-text-dim">
              <span>
                {a.phase ?? "—"} · {a.therapeutic_area ?? "—"} ·{" "}
                {a.modality ?? "—"}
              </span>
              <span>LOA {fmtPct(a.final_loa)}</span>
              <span>rNPV {fmtUsd(a.rnpv_base_usd_m)}</span>
              {a.recommendation ? (
                <span className="text-text-primary">
                  {a.recommendation.replace(/_/g, " ")}
                </span>
              ) : null}
              <span className="ml-auto">{fmtDate(a.created_at)}</span>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
