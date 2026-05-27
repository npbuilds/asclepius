"use client";

// PersonaToggle — header dropdown for the v1.8.0 persona system.
//
// Mirrors the structure of ThemeToggle (mounted check to avoid icon flip
// on hydration, neutral placeholder until mounted), but uses a <select>
// dropdown instead of a single-button cycle because there are four
// personas, not two themes. The dropdown is small, mono-typography,
// and labels the personas with their short names (per persona-config.ts);
// hover/focus shows the full description as a tooltip.
//
// v1.8.0 Phase 1: this component is fully functional — selecting a
// persona persists to localStorage and updates document.documentElement
// dataset.persona. The diligence page doesn't YET branch on persona
// (Phases 3-5 wire the per-persona variations), so for the moment
// selecting IC Voter / Scientific Reviewer / Quant shows the same
// layout as VC Associate. Infrastructure first, behavior next.

import { useEffect, useState } from "react";
import { Users } from "lucide-react";

import {
  DEFAULT_PERSONA,
  getCurrentPersona,
  setPersona,
  type PersonaId,
} from "@/lib/persona";
import { PERSONA_CONFIGS } from "@/lib/persona-config";

const PERSONA_ORDER: PersonaId[] = [
  "vc_associate",
  "ic_voter",
  "scientific_reviewer",
  "quant",
];

export function PersonaToggle() {
  const [persona, setLocalPersona] = useState<PersonaId>(DEFAULT_PERSONA);
  const [mounted, setMounted] = useState(false);

  // Sync from DOM after hydration. Same pattern as ThemeToggle — the anti-FOUC
  // inline script has already set the correct data-persona; we just observe it.
  useEffect(() => {
    setLocalPersona(getCurrentPersona());
    setMounted(true);
  }, []);

  function onChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const next = e.target.value as PersonaId;
    setLocalPersona(next);
    setPersona(next);
  }

  // Render a neutral placeholder until mounted so the label never flips
  // (SSR may have rendered the default; client may switch to a different
  // persisted value).
  if (!mounted) {
    return (
      <span
        aria-label="Persona toggle"
        className="inline-flex h-8 items-center gap-1 rounded border border-border-dim px-2 font-mono text-[10px] uppercase tracking-wider text-text-dim"
      >
        <Users size={12} />
        <span>VC Assoc</span>
      </span>
    );
  }

  const config = PERSONA_CONFIGS[persona];
  return (
    <label
      className="inline-flex h-8 items-center gap-1.5 rounded border border-border-dim bg-bg-panel px-2 font-mono text-[10px] uppercase tracking-wider text-text-primary transition-colors hover:border-cyan-bright hover:text-cyan-bright"
      title={config.description}
    >
      <Users size={12} />
      <span className="sr-only">Persona</span>
      <select
        value={persona}
        onChange={onChange}
        aria-label="Select persona"
        className="cursor-pointer bg-transparent font-mono text-[10px] uppercase tracking-wider outline-none"
      >
        {PERSONA_ORDER.map((id) => {
          const c = PERSONA_CONFIGS[id];
          // VC Associate gets a "(default)" suffix so a user opening the
          // dropdown immediately understands which persona the v1.7.0
          // layout corresponds to. Other persona labels stay clean —
          // they're recognizable on their own (IC Voter, Scientific
          // Reviewer, Quant).
          const label =
            id === "vc_associate" ? `${c.label} (default)` : c.label;
          return (
            <option key={id} value={id} className="normal-case">
              {label}
            </option>
          );
        })}
      </select>
    </label>
  );
}
