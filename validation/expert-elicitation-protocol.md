# PEC independent expert-elicitation protocol

Status: protocol specified; panel recruitment, elicitation, aggregation, and
independent sign-off are pending. No expert-panel estimates are claimed in the
August 9, 2026 release.

## Purpose

Replace interim author-specified pre-deployment priors with independently
elicited distributions for future PEC reach, adoption, activation, technical
completion, receiver compatibility, unique-episode allocation, beneficial and
adverse effects, receiving-system costs, and dependence.

## Required expertise

- 911/PSAP operations and quality assurance
- EMS operations and medical direction
- emergency medicine and resuscitation science
- suicide/crisis and 988 systems
- 211/community-resource systems
- NG911, platform, cybersecurity, and interoperability engineering
- health economics and public budgeting
- Bayesian elicitation, causal inference, and uncertainty analysis

At least two independent experts are required for each domain. Conflicts of
interest, financial relationships, PEC involvement, and prior access to model
headlines must be disclosed.

## Prespecified procedure

1. Freeze the model definitions, units, endpoints, and evidence dossiers before
   elicitation.
2. Train experts on probabilities, quantiles, calibration questions, and the
   distinction between an effect being absent and an effect being unknown.
3. Collect individual judgments before group discussion. Required judgments
   include a probability of exactly zero effect and conditional quantiles when
   the effect is nonzero.
4. Record rationales, source relevance, transportability concerns, and
   confidence separately from numerical judgments.
5. Conduct a facilitated SHELF/Delphi-style discussion without requiring
   consensus. Preserve anonymized individual distributions and disagreement.
6. Aggregate using a prespecified equal-weight linear pool as the primary rule;
   report performance-weighted and no-pooling sensitivities if calibration data
   permit them.
7. Elicit dependence separately: pairwise rank correlations, common national
   factors, and low/medium/high Gaussian- and t-copula cases.
8. Blind the modeling team to aggregate outcome headlines until judgments are
   frozen.
9. Rerun all models, publish the anonymized elicitation workbook, and document
   every change from the interim priors.
10. Obtain independent statistical reproduction and written sign-off before
    describing the new priors as independently elicited.

## Minimum outputs

- zero-effect probability and conditional distribution for every positive and
  adverse mortality effect
- unique-episode/repeat-record distributions for 988, 211, 911, EMS, OHCA, and
  passive monitoring
- sending- and receiving-system resource deltas
- rollout slope, midpoint, saturation, and deployment-realization probabilities
- full elicited correlation matrix and copula sensitivity specification
- transportability score and penalty for each external evidence source

## Replacement rule

Interim author priors remain visibly labeled until all minimum outputs and the
independent reproduction sign-off are deposited. Missing expert judgments are
not silently replaced by narrow defaults.