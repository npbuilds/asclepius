"""ClinicalTrials.gov v2 eligibility-criteria fetcher.

Used by the v1.5.2 ML PoS Prior engine when the caller supplies an
nct_id without explicit criteria_text. Fetches the trial's eligibility
criteria text directly from
https://clinicaltrials.gov/api/v2/studies/<nct_id> and returns the
raw text suitable for PubMedBERT embedding.

Two design choices worth flagging:

1. No retry / no backoff. CT.gov v2 is generous (~50 req/min per the
   v1.1 Auto-Diligence research dive) but a single failed fetch just
   bubbles a 503 to the caller. The user can re-supply criteria_text
   verbatim as fallback. This avoids hidden retry loops that would
   make the engine's latency unpredictable.

2. Synchronous httpx call inside the FastAPI request handler.
   For a portfolio-traffic-volume app this is fine; the alternative
   (async + worker pool) is over-engineering for the current load.
"""

from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)

CTGOV_V2_BASE = "https://clinicaltrials.gov/api/v2/studies"
CTGOV_TIMEOUT_SECONDS = 5.0

# CT.gov v2 (like SEC EDGAR) rejects requests without an identifying
# User-Agent header — anonymous requests get HTTP 403. Per the v2 API
# docs and NLM's general access policy, a UA naming the consuming
# application + a contact email is appropriate. The contact email is
# the project owner's public address.
CTGOV_USER_AGENT = (
    "Asclepius/0.1 (biotech-venture-valuation; "
    "https://github.com/npbuilds/asclepius)"
)


class CtGovFetchError(Exception):
    """Wraps any failure path from the CT.gov v2 fetch so callers can
    surface a consistent HTTPException(503) with a helpful detail."""


def fetch_eligibility_criteria(nct_id: str) -> str:
    """Returns the eligibility-criteria text for the given NCT ID.

    Raises CtGovFetchError on:
      - Non-2xx HTTP response (study not found, server error, etc.)
      - Network failures (timeout, DNS, connection refused)
      - Response shape that doesn't contain the expected field
      - Empty criteria text (CT.gov returned the trial but the field
        was blank — e.g., terminated trials with no published criteria)
    """
    if not nct_id or not nct_id.strip().upper().startswith("NCT"):
        raise CtGovFetchError(
            f"invalid nct_id {nct_id!r}; expected format 'NCT12345678'"
        )

    url = f"{CTGOV_V2_BASE}/{nct_id.strip().upper()}"
    params = {
        # Project just the eligibility module to minimize payload
        "fields": "protocolSection.eligibilityModule.eligibilityCriteria",
        "format": "json",
    }

    log.info("ct.gov fetch: %s", url)
    try:
        resp = httpx.get(
            url,
            params=params,
            timeout=CTGOV_TIMEOUT_SECONDS,
            headers={"User-Agent": CTGOV_USER_AGENT, "Accept": "application/json"},
        )
    except httpx.HTTPError as exc:
        raise CtGovFetchError(f"ct.gov network error for {nct_id}: {exc}") from exc

    if resp.status_code == 404:
        raise CtGovFetchError(f"ct.gov has no study with id {nct_id}")
    if resp.status_code != 200:
        raise CtGovFetchError(
            f"ct.gov returned {resp.status_code} for {nct_id}: "
            f"{resp.text[:200]}"
        )

    try:
        payload = resp.json()
    except ValueError as exc:
        raise CtGovFetchError(f"ct.gov returned non-JSON for {nct_id}: {exc}") from exc

    # Navigate the v2 schema: protocolSection.eligibilityModule.eligibilityCriteria
    try:
        criteria = (
            payload["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
        )
    except (KeyError, TypeError) as exc:
        raise CtGovFetchError(
            f"ct.gov response for {nct_id} missing eligibilityCriteria field "
            f"(study may be terminated/withdrawn with no criteria posted): {exc}"
        ) from exc

    if not criteria or not str(criteria).strip():
        raise CtGovFetchError(
            f"ct.gov returned blank eligibility criteria for {nct_id}"
        )

    return str(criteria).strip()
