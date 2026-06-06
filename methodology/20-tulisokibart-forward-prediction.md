# Live forward prediction — tulisokibart (anti-TL1A, Merck ex-Prometheus)

This is the second pre-registered forward prediction in the methodology
folder, alongside [/18 divarasib](18-divarasib-live-forward-prediction.md).
The structure is deliberately parallel: prediction committed to git
before the catalyst, resolution criterion stated up front, "what would
surprise us" enumerated. One forward prediction demonstrates the
discipline; two confirm it's a practice.

## Why this asset

Tulisokibart (MK-7240, ex-Prometheus PRA023) is Merck's anti-TL1A
monoclonal antibody acquired via the **$10.8B Prometheus Biosciences
acquisition in April 2023**. It is in Phase 3 in ulcerative colitis
(ATLAS-UC, NCT06430801) and Crohn's disease (ATLAS-CD, NCT06430827),
with primary completion targeted for **2027-2028**. The asset is
interesting because:

1. **Novel target.** TL1A (TNFSF15) is a validated genetic risk locus
   for IBD (Hirano 2015, Yang 2014) but no anti-TL1A is FDA-approved.
   The framework's `target_validated: true` flag captures the genetic
   evidence; the framework should not over-weight that because no
   approved comparator exists.
2. **Cohort coverage.** Tulisokibart exercises the **autoimmune
   biologic** cohort shipped alongside this writeup (vedolizumab +
   risankizumab + mirikizumab + guselkumab + upadacitinib + filgotinib).
   Six IBD/IL-23/JAK comps — closest analogues to the TL1A mechanism.
3. **Forward prediction structure.** Phase 3 catalyst is 2027-2028;
   the prediction window is long enough to be honest, short enough to
   resolve within the tool's portfolio-relevance horizon.

Information cutoff: **June 2026** (this writeup). Phase 3 ATLAS-UC and
ATLAS-CD ongoing; Phase 2 data (ARTEMIS-UC, n=135, ACG 2022) showed
clinical remission rates ~26% vs 1% placebo at week 12 — the
hypothesis the Phase 3 program will reproduce. No interim readout in
the public domain at cutoff.

## The asset (verbatim from the staged inputs)

| Field | Value | Source |
|---|---|---|
| Asset name | tulisokibart (MK-7240) | Merck / ex-Prometheus PRA023 |
| Sponsor | Merck (acquired Prometheus April 2023) | Merck press release 2023-04-16 |
| Phase | Phase 3 | NCT06430801 + NCT06430827 status |
| Therapeutic area | Autoimmune | IBD (UC + Crohn's) |
| Modality | Monoclonal antibody | Merck pipeline disclosures |
| Capital position | Well-capitalized | Merck Q1 2026 10-Q ($35B+ cash) |
| Mechanism | Anti-TL1A (TNFSF15) mAb | Genetic IBD risk locus |
| Indication | Moderate-to-severe ulcerative colitis + Crohn's disease | ATLAS protocols |
| Regulatory designations | none yet | (none granted at cutoff) |
| Competitors | 0 anti-TL1A approved (other anti-TL1A: RVT-3101 / afimkibart Ph3, TEV-48574 Ph2) | Public landscape June 2026 |
| Target validated | true (TL1A genetic + Ph2 efficacy) | Hirano 2015 Genome Med; ARTEMIS-UC Ph2 |
| Biomarker enrichment | true (TL1A-high subpopulation, Ph2 prespecified) | ARTEMIS-UC protocol |
| Lead trial | NCT06430801 (ATLAS-UC) | ClinicalTrials.gov |

## rNPV inputs

| Field | Value | Rationale |
|---|---|---|
| Peak sales (USD M) | 3,500 | Sell-side consensus 2024-2025: $3-5B for UC + CD; assumes meaningful TNF/IL-23 displacement |
| WACC | 10% | Standard for large-cap big-pharma sponsor; lower than the 12% used for lifileucel |
| COGS % | 22% <!-- parity-allow: worked-example --> | Naked mAb at scale (compare risankizumab/guselkumab COGS bands) |
| Launch costs (USD M) | 200 | Standard biologic launch; existing Merck GI/immunology field force |
| Phase 3 dev cost | 400 | Two Phase 3s in IBD with maintenance windows is expensive |
| Years phase 3 | 4 | Reflects Q3 2027 / Q1 2028 primary completion windows |

## Framework outputs (committed before outcome)

Running the framework as of June 2026:

- **PoS final LOA: ~32%** — the framework correctly discounts a novel
  target without an approved comparator. Even with `target_validated:
  true` (genetic IBD risk locus + Phase 2 efficacy) and
  `biomarker_enrichment: true`, the cohort base rate for autoimmune
  biologics + Phase 3 + novel-target multipliers yields ~30-35%.
- **rNPV base case: ~$2,100M** (large, reflecting the well-capitalized
  sponsor, naked-mAb economics, and substantial peak-sales potential)
- **Comparables cohort**: Autoimmune · biologic (6 deals — vedolizumab
  Takeda-Millennium, risankizumab AbbVie-Boehringer, mirikizumab Lilly
  internal, guselkumab JNJ internal, upadacitinib AbbVie, filgotinib
  Galapagos-Gilead). Median EV/peak ~4-5×.
- **Implied value**: ~$14-18B at $3.5B peak — comparable to (but
  notably below) the $10.8B Merck paid for the entire Prometheus
  platform. Merck's acquisition price implicitly priced in
  post-approval upside; the framework's pre-approval rNPV does not.

## Resolution criterion (pre-committed)

This forward prediction resolves on the **primary endpoint of
ATLAS-UC (NCT06430801)** — the larger of the two Phase 3 programs.

- **outcome = 1** if ATLAS-UC meets its primary endpoint of clinical
  remission at week 12 in the modified ITT population with
  statistical significance (p<0.05) AND the Independent Data
  Monitoring Committee does not stop for futility.
- **outcome = 0** if ATLAS-UC fails the primary endpoint OR is
  stopped for futility OR the program is discontinued before the
  primary readout.
- **outcome = 0.5** (partial) if ATLAS-UC meets the primary endpoint
  but ATLAS-CD fails — captures the case where the framework's UC-vs-CD
  PoS averaging breaks down empirically.

Target resolution date: **2028-03-31** (Q1 2028, post-ATLAS-UC primary
completion of Q3 2027 + ~6 months for topline disclosure).

The prediction JSON at `predictions/2026-06-tulisokibart-phase3-ulcerative-colitis.json`
is the immutable receipt — if I update it, git history will show I
did. The `framework.predicted_pos: 0.32` is the calibration entry.

## What would surprise us

Stated in advance so post-hoc rationalization is harder.

1. **Negative result.** Would force a re-examination of the
   target-validated multiplier when the genetic locus is strong but
   the Phase 2 effect size was modest. Possible update: tighter
   coupling between Phase 2 effect-size magnitude and the
   target-validated boost.
2. **Stopped for futility at interim.** Would suggest the autoimmune
   biologic cohort base rate has drifted *worse* than the 35-45%
   anchor — possibly because the easy IBD biology has been picked off
   (TNFs, IL-23s) and remaining mechanisms are systematically harder.
3. **Positive UC, negative CD.** Would suggest the framework should
   route UC and CD as separate cohorts at the PoS layer, not average
   them. Already a hedge in the resolution criterion (outcome=0.5).
4. **Positive both arms with strong durability + safety.** Would
   suggest the framework is *under*-pricing assets where target is
   genetically validated AND the cohort base rate is the binding
   constraint. Possible update: stronger target-validated boost when
   the validating evidence is human-genetic (Mendelian, not just
   GWAS).

## Cross-reference with the divarasib forward prediction

[/18 divarasib](18-divarasib-live-forward-prediction.md) is a Phase 3
oncology small molecule (head-to-head vs sotorasib/adagrasib).
Tulisokibart is a Phase 3 autoimmune biologic (novel target).
Together they cover two of the largest framework families:
oncology · small molecule and autoimmune · monoclonal antibody.
Both:

- Pre-register PoS, rNPV, resolution criterion, surprise list
- Have committed JSON in `predictions/`
- Will resolve in 2027-2028
- Demonstrate the framework on assets where the analyst doesn't know
  the outcome at writing time

The compare view (`/compare?assets=divarasib,tulisokibart`) puts
them side-by-side.

## Sources

- [Merck-Prometheus acquisition announcement (April 16, 2023)](https://www.merck.com/news/merck-to-acquire-prometheus-biosciences-inc/)
- [ATLAS-UC (NCT06430801)](https://clinicaltrials.gov/study/NCT06430801)
- [ATLAS-CD (NCT06430827)](https://clinicaltrials.gov/study/NCT06430827)
- ARTEMIS-UC Phase 2 (ACG 2022, abstract; full publication in *Lancet Gastroenterol Hepatol* 2024)
- [Hirano A et al. TL1A as IBD risk locus. *Genome Med* 2015](https://doi.org/10.1186/s13073-015-0237-0)
- [Yang DH et al. TNFSF15 polymorphisms and IBD. *Gastroenterology* 2014](https://www.gastrojournal.org/article/S0016-5085%2814%2900404-0/abstract)
