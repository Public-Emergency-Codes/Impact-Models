# Response to technical review dated August 8, 2026

This response covers `review-2026-08-08-034257.tex`. The mortality manuscript,
economic companion paper, three simulations, machine-readable inputs, and
archived outputs were revised together.

1. **Unidentified is no longer assigned the value zero.** The paper now reports
   the evidence-only PEC mortality effect as “not identified or estimable from
   current PEC data.” A separately named evidence-only benefit-credit decision
   rule is set to zero and explicitly described as bookkeeping, not an estimate
   of the true effect.
2. **The current OHCA model uses a clinically compatible denominator and
   baseline.** The CPR-delay curve is applied only to the sampled
   bystander-witnessed, layperson-CPR subgroup. Its baseline survival is 19.2%,
   the observed value in the Nguyen et al. study population, rather than the
   10.5% all-registry baseline. The revised current-deployment attribution
   median is 53.4 lives/year (P5--P95: 27.7--89.8).
3. **Operational time endpoints are explicit.** Dispatch-to-scene,
   scene-to-patient, and patient-to-treatment clocks are defined separately.
   The vertical-response study is used only for scene-to-patient time. Any
   mortality conversion from that time is labeled as a cross-endpoint transport
   sensitivity with a zero lower bound.
4. **Mature acute-pathway overlap is executable.** Cardiac arrest, earlier 911,
   language, location/access, and medical-data/video rows now share one
   36.367261-million acute-EMS partition. Cardiac-arrest opportunity is
   converted to a share of that denominator, all five shares are jointly
   normalized if necessary, and a runtime assertion enforces a total allocation
   no greater than one.
5. **Mortality-credit sensitivities are separated precisely.** The former
   “Tier-C-zero” result is labeled
   “designated-Tier-C-positive-effects-zero.” A symmetric mortality-neutral
   sensitivity removes both beneficial and adverse mortality effects. The
   asymmetric case is labeled “adverse-only model-assumption stress test” so
   its negative result cannot reasonably be mistaken for an estimated PEC harm.
   The economic paper carries all sensitivities while preserving nonmortality
   operational benefits.
6. **Reproducibility metadata and deposit were repaired.** The JSON distinguishes
   base, current, mature-primary, and mature-independent RNG seeds. The mature
   equations display the shared clinical-effect multiplier. Python and CSV
   files are no longer ignored and have been added to the Git index. A SHA-256
   manifest covers the papers, code, inputs, results, and source-material
   transcriptions. The original binary source documents were unavailable, so
   the deposited transcriptions are labeled honestly rather than presented as
   originals.
7. **Independent Poisson benefit/harm counts were removed.** Conditional annual
   outcomes now use a finite-population binomial affected count followed by
   mutually exclusive benefit/harm/none multinomial categories. Reported
   predictive intervals are labeled “conditional annual-count predictive
   intervals.”

Editorial fixes include the matched predictive median in the abstract; the
Silverman et al. vertical-response citation; the corrected pediatric journal
title; removal of the dangling list conjunction; and an exact NEMSIS 2025 PRRD
record of 63,635,893 activations, 14,801 agencies, 54 states/territories, and a
May 6, 2026 release date.

Both LaTeX papers compile without errors or unresolved references. All three
simulations rerun from the published inputs, their JSON outputs validate, and
`sha256sum -c reproducibility-manifest.sha256` passes for every archived file.