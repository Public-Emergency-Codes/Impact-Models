# Public Emergency Codes prospective impact models

This repository contains two pre-deployment research models for Public
Emergency Codes (PEC):

1. a prospective mortality planning analysis; and
2. a prospective U.S. economic-value analysis coupled to the mortality model.

The models do **not** estimate an observed PEC causal effect. PEC has not yet
generated deployment outcome data. The reported distributions are conditional
scenario outputs under published interim assumptions and should not be quoted as
verified lives saved, financial savings, or deployment probabilities.

## Quick start

Python 3.13 and the packages in `requirements.txt` are required.

```bash
python -m pec_model.mortality_near_term
python -m pec_model.mortality_mature
python -m pec_model.economic
python scripts/validate_repository.py --rerun
```

The model writes reproducible JSON and CSV outputs to `results/`.

## Repository structure

```text
config/           Machine-readable model inputs
docs/             Reproducibility and software-environment records
pec_model/        Executable mortality and economic model code
results/          Generated JSON and CSV results
reviews/          Historical technical reviews and response
scripts/          Repository, deployment-export, and text-proofing validators
source-materials/ Provenance-preserving source transcriptions
validation/       Prospective trial, elicitation, and data specifications
```

## How to review or suggest changes

Use GitHub Issues for:

- reproducibility or implementation defects;
- challenges to a probability distribution, causal transport, or cost input;
- proposed primary-source replacements;
- overlap, dependence, or accounting concerns; and
- documentation or presentation corrections.

Use pull requests for concrete code or manuscript changes. Follow
`CONTRIBUTING.md`, rerun the complete validator, and report how the change affects
the headline outputs and uncertainty intervals.

## Reproducibility

See `docs/reproducibility.md`. The release validator checks JSON integrity,
runtime accounting identities, deployment-data schema tests, exact regenerated
outputs, LaTeX compilation, and `release-manifest.sha256`.

Computational reproduction does not validate the interim priors. Independent
expert elicitation, linked episode data, procurement costing, randomized
deployment evaluation, and external statistical reproduction remain pending.

## Generated files

Files under `results/` are generated artifacts but are intentionally versioned
so reviewers can inspect changes without rerunning the full Monte Carlo model.
Do not edit them manually.

## License

- Software is released under the Zero-Clause BSD license (`0BSD`). It may be
  used, copied, modified, and distributed for any purpose, with or without fee.
- Documentation, configuration, results, validation material,
  reviews, and source transcriptions are dedicated under CC0 1.0 Universal to
  the extent Public Emergency Codes owns the applicable rights.

Attribution is not required, although citation is appreciated for scientific
traceability. The licenses cannot grant third-party, trademark, privacy,
publicity, or patent rights that Public Emergency Codes does not own. See
`LICENSE`.