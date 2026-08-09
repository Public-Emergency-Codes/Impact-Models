# PEC prospective deployment validation analysis plan

Status: protocol-ready; no PEC deployment outcome dataset has yet been analyzed.

## Objective and design

The preferred design is a cluster-randomized rollout, with a stepped-wedge
cluster-randomized design acceptable when simultaneous implementation is not
operationally possible. Clusters should be defined before randomization at the
level at which contamination can be controlled: PSAP, dispatch center, platform
region, or an explicitly justified linked implementation unit.

Randomization, rollout dates, exclusions, primary outcomes, covariates, and the
analysis code hash must be registered before outcome unblinding. A contemporaneous
control is required; before-after comparisons alone are not sufficient for the
primary causal claim.

## Analysis population and time zero

- The master unit is a unique emergency episode, not a call, administrative
  record, device notification, or person-year.
- One person may contribute multiple episodes; standard errors must account for
  clustering by person linkage token when repeated episodes can be linked.
- Episode time zero is the earliest qualifying request, sensor detection, or
  emergency-system contact under the prespecified incident-family rule.
- Cross-system records must be linked before analysis so that transfers,
  callbacks, duplicate calls, EMS records, and hospital encounters are not
  counted as separate episodes.
- Intention-to-treat assignment is determined by cluster and rollout period,
  regardless of whether an individual activates a PEC function.

## Primary estimands

1. Intention-to-treat 30-day all-cause mortality risk difference per 100,000
   eligible episodes.
2. Intention-to-treat potential variable public expenditure difference per
   eligible episode, in a prespecified dollar year.
3. Intention-to-treat emergency-system workload difference: call-taker minutes,
   responder minutes, transfers, duplicate/status calls, and queue occupancy.

Secondary estimands include survival to discharge, favorable neurological
outcome, major disability, ED treatment, hospitalization, ICU use, rehabilitation,
long-term care, work loss, property loss, receiving-system workload, and adverse
events. Per-protocol and function-activated analyses are secondary because
activation is post-randomization.

## Statistical models

- Binary outcomes: generalized linear mixed models with identity-link risk
  differences as primary and log-link risk ratios as secondary; fixed effects
  for rollout period and prespecified baseline strata; random cluster intercepts.
- Time outcomes: accelerated failure-time or prespecified robust quantile models,
  with competing events handled explicitly.
- Counts and workload: negative-binomial or Poisson mixed models selected from
  blinded dispersion diagnostics.
- Cost outcomes: two-part models where structural zeros are material, otherwise
  generalized linear models with prespecified link/family selected using blinded
  residual diagnostics.
- Repeated episodes: cluster-robust inference at both implementation-cluster and
  person-linkage levels where technically feasible.

The primary effect is not adjusted for PEC function activation. Missing outcomes,
record-linkage uncertainty, contamination, noncompliance, and cluster attrition
must each receive a prespecified sensitivity analysis. Bayesian updating of the
planning priors is secondary to the randomized comparison and must publish both
prior and likelihood contributions.

## Multiplicity, safety, and stopping

Mortality, public expenditure, and workload are a three-outcome primary family.
A prespecified gatekeeping or false-discovery procedure must be chosen before
unblinding. Safety reporting includes delayed or failed connection, mistranslation,
wrong location, incorrect medical information, privacy/security events, false
alarms, inappropriate dispatch or non-dispatch, and receiving-system overload.
Any interim monitoring boundary must be set by an independent data and safety
monitoring body; the planning model is not a stopping rule.

## Sample size

No numerical sample size is asserted before pilot estimates of eligible-episode
frequency, baseline outcome risk, intracluster correlation, cluster size
variation, contamination, and linkage loss are available. The final calculation
must publish those inputs, target power, two-sided type-I error, detectable risk
difference, number of clusters, and design effect.

## Replacement of planning priors

Planning inputs are replaced only after data definitions pass
`scripts/validate_deployment_export.py`, the analysis is reproduced from frozen
exports, and the trial report distinguishes observed effects from updated
forecasting distributions. Null or harmful findings are retained; they are not
truncated to preserve a favorable planning result.