# Where the framework is silent — aducanumab and the political-approval case

The first three pre-staged assets ([/05 adagrasib](05-worked-example-adagrasib.md),
[/19 lifileucel](19-lifileucel-cell-therapy-retrospective.md),
[/18 divarasib](18-divarasib-live-forward-prediction.md),
[/20 tulisokibart](20-tulisokibart-forward-prediction.md)) all share
one feature: the framework's output and the actual outcome are
*reconcilable in principle*. The math composes; the call is defensible.

Aducanumab is different. It is the asset where the framework was
**honest and wrong** — pre-approval bare-chain PoS ~54% <!-- parity-allow: superseded -->
(now ~14% under the v1.7.7 hard-cap, see below), FDA approved
Aducanumab in June 2021 over a 10-0 Advisory Committee vote
*against*, and voluntary withdrawn by Biogen in January 2024. This writeup walks
through what the framework would have said in March 2019 (after the
ENGAGE/EMERGE futility analyses) and uses the framework's miss to
delineate **where the framework is silent and why that silence is
acceptable**.

## Why this asset

The framework's design commitment is that it should never *invent* a
PoS for things it doesn't know how to price. Aducanumab is the cleanest
test of that commitment: at the March 2019 information cutoff, the
science was *contested* (Phase 3 futility on the original analysis,
positive post-hoc reanalysis of the high-dose EMERGE arm), and the
actual approval ran through a political process the framework
does not model (FDA Center Director Janet Woodcock's accelerated
approval over the Advisory Committee's 10-0 reject vote, the surrogate
amyloid endpoint reinterpretation, the post-approval CMS coverage
restriction).

The asset is interesting because:

1. **The framework gets the science approximately right.** Anti-amyloid
   in AD has a deep cohort base rate of ~5-8% at Phase 3 (CNS · biologic
   cohort). With `target_validated: false` (the amyloid hypothesis was
   contested in 2019) and `biomarker_enrichment: false` for the
   original Phase 3 designs, the bare multiplier chain would produce
   **PoS ~50-55% <!-- parity-allow: superseded --> conditional on a positive read** — and the read was
   *not* clearly positive at the cutoff. The v1.7.7 hard-cap pulls
   the framework's output down to ~14%, which is the honest
   population-anchored read for an asset where neither validation
   lever is on.
2. **The framework is silent on political process.** No multiplier in
   the multiplier chain corresponds to "FDA Center Director will
   accelerate-approve over a unanimous AdCom reject." That outcome
   path is unmodeled, and *should be* unmodeled. A framework that
   tried to price political risk would be untrustworthy.
3. **The framework's downside signal is the `downside_failed_p3`
   line, not the success-conditional base case.** This is a subtle
   read but it matters. With the inputs documented below, post-cap
   rNPV base case is **$1,983M** (what the asset is worth *if* Phase 3
   succeeds — the framework can't model the political accelerated-
   approval-and-withdrawal arc, so a successful Phase 3 is the only
   path to commercialization it sees). The base case is large because
   the bullish peak ($4.5B) and well-capitalized launch economics
   compound through the PoS-gated cash flows. The framework's *actual*
   downside line is `downside_failed_p3 = $106M` — what's left if
   ENGAGE/EMERGE failure terminates the program. The realized outcome
   (peak revenue ~$5M before 2024 withdrawal) sat *below* even this
   downside line, because the framework prices a clean failure
   (program terminates) but reality was a contested approval that
   limped along consuming SG&A before being killed. The framework
   honestly under-priced the *political-process tail risk* on the
   downside — see "Where the framework is silent" below.

Information cutoff: **March 2019**, immediately post-ENGAGE/EMERGE
futility analyses. Pre-Biogen-restart-announcement (October 2019),
pre-Center-Director-approval (June 2021), pre-withdrawal (January 2024).

## The asset

| Field | Value | Source |
|---|---|---|
| Asset name | aducanumab (BIIB037) | Biogen/Eisai pipeline disclosures |
| Sponsor | Biogen / Eisai | Biogen 10-K FY2018 |
| Phase | Phase 3 (post-futility analysis) | ENGAGE + EMERGE protocol status March 2019 |
| Therapeutic area | CNS (Alzheimer's) | Clinical program |
| Modality | Monoclonal antibody | Biogen disclosures |
| Capital position | Well-capitalized | Biogen 10-K FY2018 ($5.4B cash) |
| Mechanism | Anti-amyloid-β mAb | Sevigny 2016 Nature |
| Indication | Mild cognitive impairment / mild Alzheimer's disease | ENGAGE/EMERGE protocols |
| Regulatory designations | Fast Track | FDA designations registry |
| Competitors | 0 anti-amyloid approved (multiple discontinued: solanezumab, bapineuzumab, crenezumab) | Public landscape March 2019 |
| Target validated | false (amyloid hypothesis contested as of March 2019; positive validation came with Lecanemab CLARITY-AD 2022) | Field consensus March 2019 |
| Biomarker enrichment | false (CSF/PET amyloid required for enrollment but did not predict efficacy) | ENGAGE/EMERGE design |
| Lead trial | NCT02484547 (ENGAGE) | ClinicalTrials.gov |

## rNPV inputs

These mirror the workbench staging at
`web/app/diligence/[asset]/page.tsx` (constants `ADUCANUMAB_RNPV`) so the
methodology numbers below reconstruct exactly when you visit
`/diligence/aducanumab`.

| Field | Value | Rationale |
|---|---|---|
| Peak sales (USD M) | 4,500 | Bullish-side 2019 sell-side high: ~$4-5B peak for mild AD if approved. Tracking the bullish case stress-tests whether the framework's downside line still bounds the disappointment when revenue actually peaks at ~$5M. |
| WACC | 10% | Big-pharma single-asset rate. Biogen was well-capitalized in 2019. |
| COGS % | 15% | Naked mAb at scale (compare lecanemab / donanemab COGS bands). |
| Launch costs (USD M) | 200 | Standard biologic launch + AD-specific PET / amyloid testing infrastructure. |
| Phase 3 dev cost | 200 | Two Phase 3s residual; futility had been declared but the data were still being parsed. |
| Years phase 3 | 2 | Reflects the post-futility, pre-BLA timeline as actually played out. |

## Framework outputs (what March 2019 inputs produce)

- **PoS final LOA: ~14%** (post-v1.7.7 hard-cap) — down from the
  pre-cap ~54% <!-- parity-allow: superseded --> that the bare multiplier chain produces. The CNS ·
  biologic cohort base rate is ~5-8%; with `target_validated: false`
  the modality multiplier should drag PoS down hard, but the bare
  chain (Fast Track + well-capitalized reflexivity + mAb modality
  default) pushed back up to ~54% <!-- parity-allow: superseded -->. **This was the framework's first
  honest signal**: when `target_validated` is false AND
  `biomarker_enrichment` is false, no other lever should be able to
  push PoS above cohort-base-rate × 3. **Shipped in v1.7.7**: a
  post-multiplier-chain hard-cap implemented in
  `api/app/modules/pos/engine.py`. The cap anchors on the long-run
  P1→approval cohort LOA (modality-adjusted) rather than the
  phase-conditional base rate, because the phase-conditional rate
  already absorbs the survival bias of having reached the current
  phase — exactly what the cap is intended to push back against. For
  CNS · mAb that's 0.041 × 1.15 × 3 ≈ 0.14, which is where
  aducanumab's PoS now lands. The cap is recorded as an explicit row
  in the audit-trail waterfall so the final number remains
  reconstructable.
- **rNPV base case: $1,983M** (post-cap; success-conditional, not risk-adjusted further) <!-- parity-allow: model-output -->.
  Computed live by `api/app/modules/rnpv/engine.py` against the input
  table above. Pre-cap rNPV (bare multiplier chain at ~54% PoS) would
  have been ~$4,300M <!-- parity-allow: model-output --> — the v1.7.7 cap pulls rNPV down by ~$2.3B.
  Monte Carlo P25/P50/P75 = $1,109M / $1,829M / $2,850M <!-- parity-allow: model-output -->.
  These numbers are what they are: at a $4.5B bullish peak with a 14% LOA,
  the success branch is still worth ~$2B in expected present value.
- **The honest downside signal is `downside_failed_p3`, not the base
  case.** Reading rNPV as the "downside bound" mistakes the
  framework's outputs. The base case is **success-conditional** —
  what the asset is worth *if* Phase 3 succeeds and the asset reaches
  market. The framework's actual downside line is the
  `downside_failed_p3` field, which prices the Phase 3 failure path
  separately. For aducanumab with the inputs above:
  `downside_failed_p3 = $106M` <!-- parity-allow: model-output -->. That's the framework's
  honest read on "what's this asset worth if the Phase 3 trials fail" —
  small, positive, reflecting residual IP value. The actual outcome
  (peak revenue ~$5M before withdrawal) was *even worse* than this
  downside line predicted, because the framework prices a clean failure
  (program terminates) rather than a contested approval-and-withdrawal
  (program limps along consuming SG&A before being killed). That's a
  framework limitation, not a framework failure — see "Where the
  framework is silent" below.
- **Comparables cohort**: CNS · biologic (currently falls back —
  insufficient deal density at the precise CNS · biologic cohort in
  the comparable database; this is a known limitation called out in
  the Limitations Panel)
- **Implied value**: bounded by the rNPV — the comparables fallback
  denies an EV/peak-sales upside multiplier, which is appropriate
  for an asset where the science is contested

## What actually happened (the political path the framework cannot see)

- **October 2019**: Biogen announces post-hoc reanalysis of the
  EMERGE high-dose arm with a 22% reduction in clinical decline. <!-- parity-allow: external-stat --> The
  ENGAGE arm did not show the same effect. The reanalysis is
  *controversial* — the prespecified analysis was futile; the new
  analysis re-cut the data.
- **November 2020**: FDA AdCom votes **10-0 against** approval
  (with 1 uncertain). The AdCom reads the post-hoc analysis as
  insufficient.
- **June 2021**: FDA Center Director Janet Woodcock invokes
  **accelerated approval** based on the surrogate amyloid PET
  endpoint, over the AdCom's reject vote. Three AdCom members resign
  in protest.
- **April 2022**: CMS issues a National Coverage Determination
  restricting Aducanumab to CMS-approved clinical trials, effectively
  blocking commercial coverage.
- **January 2024**: Biogen voluntarily withdraws aducanumab from the
  market. Peak revenue: ~$5M (vs. the $3-5B sell-side bull case).

## What the framework correctly does not model

1. **Accelerated approval on contested surrogate endpoints.** The
   framework's modality and TA multipliers do not contain a "FDA will
   approve on surrogate endpoint despite AdCom reject" branch. **This
   is intentional**. A framework that priced political-process risk
   would be illegitimate for a tool meant to encode *scientific* PoS.
2. **Post-hoc reanalysis as evidence.** The framework does not
   reweight PoS based on subgroup analyses generated after primary
   endpoint failure. Doing so would invite reflexive reasoning.
3. **Reimbursement battles as PoS proxies.** The CMS coverage
   determination was the actual commercial death blow. The framework
   bounds peak-sales downside (~$80M rNPV at the post-v1.7.7 ~14%
   PoS <!-- parity-allow: model-output -->) but does not model the CMS-approval-vs-FDA-approval gap.
   **This *is* a known framework limitation**, documented in the
   LimitationsPanel.

## What the framework should do better

1. **Tighter target_validated × cohort-base-rate coupling. SHIPPED in
   v1.7.7.** When `target_validated: false` AND
   `biomarker_enrichment: false`, the framework now caps PoS at the
   long-run P1→approval cohort LOA (modality-adjusted) × 3. For
   CNS · mAb the cap is ~14%, replacing the previous bare-chain ~54%
   <!-- parity-allow: superseded -->. Implementation: a post-multiplier-chain ceiling applied at
   the end of `_compute_for_asset` in
   `api/app/modules/pos/engine.py`, emitted as an explicit
   `unvalidated target + no biomarker enrichment cap` row in the
   audit-trail waterfall so the final number remains
   reconstructable. The cap is anchored on the cohort cumulative LOA
   (not the phase-conditional `base_rate`) because the
   phase-conditional rate already absorbs the survival bias of
   having reached the current phase — exactly what the cap is
   intended to push back against.
2. **CNS · biologic comparables cohort.** Currently the framework
   falls back when this cohort is queried — there's not enough deal
   density. *Adding aducanumab itself* as a comparable (peak ~$5M,
   withdrawn) would be honest but tiny. The honest fix: keep the
   fallback but tag the implied-value cell with "no cohort —
   estimate not reliable."

## Cross-references

- The framework-limits discussion in this writeup is the empirical
  anchor for the existing LimitationsPanel content. Edits to the
  panel should cross-reference this writeup so the limitation +
  example travel together.
- [/05 adagrasib](05-worked-example-adagrasib.md) and
  [/19 lifileucel](19-lifileucel-cell-therapy-retrospective.md) both
  retrospectively *match* their outcomes within tolerance.
  Aducanumab is the counterpoint that demonstrates the framework's
  honest silence on a class of risks it cannot price.

## Sources

- [Biogen 10-K FY2018](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000875045&type=10-K)
- [ENGAGE (NCT02484547)](https://clinicaltrials.gov/study/NCT02484547)
- [EMERGE (NCT02484547 paired arm)](https://clinicaltrials.gov/study/NCT02484547)
- [Sevigny J et al. The antibody aducanumab reduces Aβ plaques in Alzheimer's disease. *Nature* 537, 50-56 (2016)](https://www.nature.com/articles/nature19323)
- [FDA accelerated approval of Aduhelm, June 7 2021](https://www.fda.gov/news-events/press-announcements/fda-grants-accelerated-approval-alzheimers-drug)
- [CMS National Coverage Determination, April 2022](https://www.cms.gov/medicare/coverage/national-coverage-determinations/monoclonal-antibodies-directed-against-amyloid-treatment-alzheimers-disease)
- [Biogen withdrawal announcement, January 31 2024](https://investors.biogen.com/news-releases/news-release-details/biogen-realign-resources-alzheimers-disease-franchise)
