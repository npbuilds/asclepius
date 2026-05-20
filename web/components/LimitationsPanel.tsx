// Always-visible Known Limitations panel. A senior VC looks for this — showing
// the edges is the difference between analyst and associate. Cited in the
// methodology folder's 04-scorecard-pillars.md.

const ITEMS = [
  {
    title: "Rare disease (small N)",
    detail:
      "BIO/Informa rare-disease base rate (~16% from P1) is built on a small population of approvals. Cumulative LOA estimates are noisier for indications with <20 historical approvals.",
  },
  {
    title: "Platform companies",
    detail:
      "Single-asset LOA doesn't capture portfolio effects. A platform with 6 correlated programs has a different risk profile than 6 independent shots-on-goal. v2 portfolio view addresses this.",
  },
  {
    title: "China-origin assets",
    detail:
      "BIO base rates reflect FDA/EMA cohorts. NMPA development paths differ; cross-jurisdictional risk profiles are not yet modeled. Treat outputs as US/EU-only.",
  },
  {
    title: "Pre-2018 capital-position data",
    detail:
      "Reflexivity multipliers are calibrated to post-2018 trial-design and biomarker-enrichment norms. Older comparables may understate the gap between well-capitalized and constrained sponsors.",
  },
];

export function LimitationsPanel() {
  return (
    <details className="rounded-lg border border-ink-200 bg-white p-4">
      <summary className="cursor-pointer text-sm font-medium text-ink-900">
        Known limitations
      </summary>
      <ul className="mt-3 space-y-3 text-sm text-ink-600">
        {ITEMS.map((item) => (
          <li key={item.title}>
            <div className="font-medium text-ink-900">{item.title}</div>
            <div>{item.detail}</div>
          </li>
        ))}
      </ul>
    </details>
  );
}
