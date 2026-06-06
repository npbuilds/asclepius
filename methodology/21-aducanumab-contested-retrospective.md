# Where the framework is silent — aducanumab and the political-approval case

The first three pre-staged assets ([/05 adagrasib](05-worked-example-adagrasib.md),
[/19 lifileucel](19-lifileucel-cell-therapy-retrospective.md),
[/18 divarasib](18-divarasib-live-forward-prediction.md),
[/20 tulisokibart](20-tulisokibart-forward-prediction.md)) all share
one feature: the framework's output and the actual outcome are
*reconcilable in principle*. The math composes; the call is defensible.

Aducanumab is different. It is the asset where the framework was
**honest and wrong** — pre-approval PoS ~54%, FDA approved Aducanumab
in June 2021 over a 10-0 Advisory Committee vote *against*, and
voluntary withdrawn by Biogen in January 2024. This writeup walks
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
   original Phase 3 designs, the framework would produce **PoS ~50-55%
   conditional on a positive read** — and the read was *not* clearly
   positive at the cutoff.
2. **The framework is silent on political process.** No multiplier in
   the multiplier chain corresponds to "FDA Center Director will
   accelerate-approve over a unanimous AdCom reject." That outcome
   path is unmodeled, and *should be* unmodeled. A framework that
   tried to price political risk would be untrustworthy.
3. **The framework correctly bounds the *rNPV* downside.** Peak sales
   never materialized. The framework's downside scenario at low PoS
   * cell-therapy-like launch costs would have put rNPV near zero.
   Biogen's actual aducanumab revenues peaked at ~$5M before
   withdrawal — the framework's downside bound was right.

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

| Field | Value | Rationale |
|---|---|---|
| Peak sales (USD M) | 3,000 | Bullish-side 2019 sell-side: $3-5B peak for mild AD if approved; the framework should track the bullish case to show what was being priced |
| WACC | 11% | Large-cap-pharma single-asset rate (slightly above Roche/BMS 10% to reflect Biogen's CNS pipeline concentration risk) |
| COGS % | 25% | Naked mAb at scale |
| Launch costs (USD M) | 250 | Standard biologic launch + AD-specific infrastructure (PET scan + amyloid testing) |
| Phase 3 dev cost | 200 | Two Phase 3s residual; futility had been declared but the data were still being parsed |
| Years phase 3 | 2 | Reflects the post-futility, pre-BLA timeline as actually played out |

## Framework outputs (what March 2019 inputs produce)

- **PoS final LOA: ~54%** — the framework is *too high*. The CNS ·
  biologic cohort base rate is ~5-8%; with target_validated: false
  the modality multiplier should drag PoS down hard. But the
  framework's Fast Track designation boost + the well-capitalized
  reflexivity adjustment + the modality default for Phase 3
  anti-amyloid biologic together push it back up. **This is the
  framework's first honest signal**: when target_validated is false
  AND biomarker_enrichment is false, no other lever should be able to
  push PoS above ~25-30%. The framework's current multiplier chain
  doesn't fully enforce this. *Possible v1.5.10+ update*: hard cap
  PoS at cohort-base-rate × 3 when both target_validated and
  biomarker_enrichment are false.
- **rNPV base case: ~$300M** (the framework's rNPV is correctly *low*
  even at 54% PoS <!-- parity-allow: model-output --> — reflecting the heavy discount rate, the long
  development arc, and the framework's downside scenario weighting)
- **Comparables cohort**: CNS · biologic (currently falls back —
  insufficient deal density at the precise CNS · biologic cohort in
  the comparable database; this is a known limitation called out in
  the Limitations Panel)
- **Implied value**: bounded by the rNPV ($300M) — the comparables
  fallback denies an EV/peak-sales upside multiplier, which is
  appropriate for an asset where the science is contested

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
   bounds peak-sales downside ($300M rNPV at 54% PoS) <!-- parity-allow: model-output --> but does not
   model the CMS-approval-vs-FDA-approval gap. **This *is* a known
   framework limitation**, documented in the LimitationsPanel.

## What the framework should do better (real v1.5.10+ work)

1. **Tighter target_validated × cohort-base-rate coupling.** When
   `target_validated: false` AND `biomarker_enrichment: false`, the
   framework should cap PoS at cohort base rate × 3 (e.g., for CNS ·
   biologic that's ~25%, not the current ~54%). Possible
   implementation: a post-multiplier-chain ceiling applied at the
   `pos_engine.compute()` step.
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
