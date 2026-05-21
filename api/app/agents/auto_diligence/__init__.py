"""Auto-Diligence agent — asset name → structured AssetInput + citations.

Uses Anthropic's web_search_20250305 server tool restricted to a high-signal
domain allowlist (CT.gov, SEC EDGAR, FDA, EMA, top medical journals, major
newswires). Single-pass extractor; v1.1.4 will add a separate validator pass
and custom client-side tools for CT.gov v2 + EDGAR XBRL.

Architectural grounding: Bioptic (arXiv 2508.16571v4) ReAct+validator pattern,
scaled down to the single extractor pass for the v1.1 MVP.
"""
