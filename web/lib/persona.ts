// Persona utility — single source for persona name / persistence / DOM application.
//
// `setPersona` writes to localStorage AND applies the `data-persona` attribute
// on <html>. The anti-FOUC inline script in layout.tsx reads the same key on
// first paint so the page never flashes the wrong persona — same pattern as
// the theme system in lib/theme.ts.
//
// v1.8.0: introduced with the persona views feature. Four personas map the
// same diligence data to different presentations:
//   - vc_associate (default): the v1.7.0 memo-reader layout
//   - ic_voter: 1-page summary mode for senior partners / IC voters
//   - scientific_reviewer: mechanism + trial design focus, hides rNPV/comps
//   - quant: calibration-elevated raw-numbers mode
//
// Persona config (module ordering, hidden modules, banner variant) lives in
// lib/persona-config.ts. This module is JUST the persistence + DOM contract.

export type PersonaId =
  | "vc_associate"
  | "ic_voter"
  | "scientific_reviewer"
  | "quant";

export const PERSONA_KEY = "asclepius_persona";
export const DEFAULT_PERSONA: PersonaId = "vc_associate";

const VALID_PERSONAS: PersonaId[] = [
  "vc_associate",
  "ic_voter",
  "scientific_reviewer",
  "quant",
];

function isValidPersona(value: string): value is PersonaId {
  return (VALID_PERSONAS as string[]).includes(value);
}

export function setPersona(persona: PersonaId): void {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.persona = persona;
  }
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(PERSONA_KEY, persona);
    } catch {
      // localStorage may be unavailable (private mode, iframe, etc.) — ignore.
    }
  }
}

export function getStoredPersona(): PersonaId | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(PERSONA_KEY);
    if (value && isValidPersona(value)) return value;
    return null;
  } catch {
    return null;
  }
}

export function getCurrentPersona(): PersonaId {
  if (typeof document === "undefined") return DEFAULT_PERSONA;
  const attr = document.documentElement.dataset.persona;
  if (attr && isValidPersona(attr)) return attr;
  return DEFAULT_PERSONA;
}

// Inline script that runs in <head> before any paint. Reads localStorage and
// sets data-persona on <html> synchronously, eliminating the flash-of-wrong-
// persona on a deep-link page load. Returned as a string so it can be
// injected via dangerouslySetInnerHTML alongside the theme equivalent.
//
// The script is intentionally small (no JSON.stringify of the valid list,
// no fancy validation) — it runs on every page load and we don't want any
// possibility of it being slow or throwing. Worst-case bad localStorage
// value just falls through to the default.
export const PERSONA_ANTI_FOUC_SCRIPT = `
(function(){
  try {
    var p = localStorage.getItem(${JSON.stringify(PERSONA_KEY)});
    var valid = ${JSON.stringify(VALID_PERSONAS)};
    if (p && valid.indexOf(p) !== -1) {
      document.documentElement.setAttribute("data-persona", p);
    } else {
      document.documentElement.setAttribute("data-persona", ${JSON.stringify(DEFAULT_PERSONA)});
    }
  } catch(e) {
    document.documentElement.setAttribute("data-persona", ${JSON.stringify(DEFAULT_PERSONA)});
  }
})();
`.trim();
