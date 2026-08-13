## Description

<!-- Briefly describe the change and its motivation. -->

## Type

- [ ] Code implementation change
- [ ] Model assumption or probability distribution change
- [ ] Evidence transport or causal interpretation change
- [ ] Economic accounting or double-counting fix
- [ ] Cited source update or new dataset
- [ ] Manuscript language or presentation change
- [ ] Documentation or validation infrastructure

## Validation

- [ ] `python scripts/validate_repository.py --rerun --compile` passes
- [ ] Headline outputs and uncertainty intervals are reported below
- [ ] No generated files in `results/` were edited manually

## Impact on headline outputs

<!-- Report changes to means, medians, P5--P95 intervals, and any threshold
probabilities affected. -->

## Source provenance

<!-- For every changed empirical input, describe the primary source,
data year, population, geography, endpoint, and transportability rationale. -->

## Checklist

- [ ] This PR does not describe scenario output as an observed PEC effect
- [ ] The distinction between observed evidence and prospective priors is preserved
- [ ] `release-manifest.sha256` is regenerated
