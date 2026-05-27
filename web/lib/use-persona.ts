"use client";

// useCurrentPersona — React hook that returns the current persona and
// re-renders the consumer when the user changes it via PersonaToggle.
//
// Why a separate file from lib/persona.ts: that module is plain TypeScript
// utilities + an inline anti-FOUC script. Mixing React in there would force
// every consumer (including the inline script generator) to pull in React
// types unnecessarily. This file is the React-side façade over the storage
// + event contract.
//
// Behavior:
//   - Initial render: returns DEFAULT_PERSONA. The anti-FOUC script has
//     already set <html data-persona="...">, but on the FIRST render
//     (during SSR or client hydration) we don't read from document
//     because the values must match between SSR + client to avoid
//     hydration warnings.
//   - Post-mount: useEffect reads getCurrentPersona() from the DOM and
//     updates state. From this point forward, the displayed persona
//     matches the DOM.
//   - On persona change: PersonaToggle calls setPersona() which
//     dispatches PERSONA_CHANGE_EVENT. We listen and re-read from DOM,
//     triggering a re-render in every component that uses this hook.

import { useEffect, useState } from "react";

import {
  DEFAULT_PERSONA,
  getCurrentPersona,
  PERSONA_CHANGE_EVENT,
  type PersonaId,
} from "./persona";

export function useCurrentPersona(): PersonaId {
  const [persona, setPersona] = useState<PersonaId>(DEFAULT_PERSONA);

  useEffect(() => {
    // Sync from DOM on mount (the anti-FOUC script has run, so the DOM
    // value is authoritative).
    setPersona(getCurrentPersona());

    function onChange() {
      setPersona(getCurrentPersona());
    }

    window.addEventListener(PERSONA_CHANGE_EVENT, onChange);
    return () => {
      window.removeEventListener(PERSONA_CHANGE_EVENT, onChange);
    };
  }, []);

  return persona;
}
