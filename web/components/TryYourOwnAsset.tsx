"use client";

/**
 * v1.6 onboarding (Block 2): small client-component form that takes any
 * asset name and routes to /diligence/<slug>. This is the third
 * exploration mode on the landing page — the path a generalist visitor
 * uses to evaluate an arbitrary asset they're curious about.
 *
 * Behavior:
 *   - Slugifies the input (lowercase, replace non-alphanum with `_`).
 *   - Empty / whitespace-only input is a no-op (prevents routing to
 *     /diligence/ which would render the asset-list page).
 *   - Routes via next/navigation's router so the SPA transition stays
 *     fast — no full reload, no lost SystemStatus state, no flash.
 *
 * The text-input feedback (Enter to submit, button click) is identical:
 * we capture submit on the <form> rather than the button so keyboard
 * users get the same path as pointer users.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";

function slugify(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function TryYourOwnAsset() {
  const router = useRouter();
  const [name, setName] = useState("");

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const slug = slugify(name);
    if (!slug) return;
    router.push(`/diligence/${slug}`);
  }

  return (
    <form
      onSubmit={onSubmit}
      className="flex items-center gap-2"
      aria-label="Try your own asset"
    >
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="e.g., olomorasib"
        className="flex-1 rounded border border-border-dim bg-bg-deep px-2.5 py-1.5 font-mono text-[12px] text-text-primary placeholder:text-text-dim focus:border-cyan-bright focus:outline-none"
        spellCheck={false}
        autoComplete="off"
      />
      <button
        type="submit"
        disabled={!slugify(name)}
        className="rounded border border-cyan-bright bg-cyan-bright/10 px-3 py-1.5 font-mono text-[12px] uppercase tracking-wider text-cyan-bright transition hover:bg-cyan-bright/20 disabled:cursor-not-allowed disabled:border-border-dim disabled:bg-bg-panel disabled:text-text-dim"
      >
        [ go → ]
      </button>
    </form>
  );
}
