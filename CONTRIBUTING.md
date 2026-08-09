# Contributing

Contributions that improve correctness, transparency, evidence quality, or
reproducibility are welcome.

By submitting a contribution, you agree that software contributions are
provided under 0BSD and non-software contributions are provided under CC0 1.0
Universal, to the extent you have authority to grant those rights.

## Before opening an issue

Please identify whether the concern is about:

- code implementation;
- a model assumption or probability distribution;
- evidence transport or causal interpretation;
- economic accounting or double counting;
- a cited source or newer dataset; or
- manuscript language and presentation.

Include the relevant file, function, table, equation, or input name and explain
the expected direction of the problem when possible.

## Pull requests

1. Do not manually edit generated files in `results/`.
2. Make the source/input change first.
3. Regenerate all outputs:

   ```bash
   python -m pec_model.mortality_near_term
   python -m pec_model.mortality_mature
   python -m pec_model.economic
   ```

4. Run:

   ```bash
   python scripts/validate_repository.py --rerun --compile
   ```

5. Report changes to means, medians, P5--P95 intervals, benefit-cost ratios,
   and any threshold probabilities affected by the proposal.
6. Preserve the distinction between observed evidence and prospective priors.
7. Add or update source provenance for every changed empirical input.

Submissions must not describe scenario output as an observed PEC effect.

## Model-assumption proposals

For a replacement distribution or causal parameter, provide:

- parameter definition and unit;
- current and proposed distribution;
- primary source and data year;
- population, geography, and endpoint;
- transportability rationale;
- expected dependence with other inputs; and
- sensitivity results under both specifications.

## Generated-output review

Large numerical changes are not automatically errors, and small changes are not
automatically safe. Review the implementation, accounting identity, and
scientific justification independently of whether a change increases or
decreases estimated PEC value.