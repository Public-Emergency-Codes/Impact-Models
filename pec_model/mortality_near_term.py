"""Near-term prospective PEC mortality-benefit scenarios.

This is a pre-deployment planning model.  It does not estimate an observed PEC
effect.  Every unvalidated positive transport includes an explicit point mass
at zero, and access-related mortality is excluded from the primary scenario.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .common import (
    categorical_cpr_gain,
    draw_bounded,
    spike_slab,
    summarize,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "config" / "mortality-model-inputs.json"
RESULT_FILE = PROJECT_ROOT / "results" / "mortality-near-term-results.json"


def sampled_external_association(
    rng: np.random.Generator,
    specification: dict[str, object],
    draws: int,
) -> np.ndarray:
    point = float(specification["point_estimate"])
    low, high = (float(v) for v in specification["confidence_interval_95"])
    standard_error = (high - low) / (2.0 * 1.96)
    return np.maximum(0.0, rng.normal(point, standard_error, draws))


def logistic_gain(
    baseline: np.ndarray,
    log_odds_gain: np.ndarray,
) -> np.ndarray:
    baseline = np.clip(baseline, 1e-9, 1.0 - 1e-9)
    odds = baseline / (1.0 - baseline)
    updated = odds * np.exp(log_odds_gain)
    return updated / (1.0 + updated) - baseline


def simulate_near_term(
    inputs: dict[str, object],
    rng: np.random.Generator,
    draws: int,
    shape: float,
    form: str = "pert",
) -> dict[str, object]:
    external_988 = sampled_external_association(
        rng, inputs["annual_988_external_association"], draws
    )

    share_spec = inputs["pec_share_of_988_association"]
    share_probability = draw_bounded(
        rng, share_spec["nonzero_probability"], draws, shape, form
    )
    share_slab = draw_bounded(
        rng, share_spec["slab_low_mode_high"], draws, shape, form
    )
    pec_share, share_active = spike_slab(rng, share_probability, share_slab)

    causal_spec = inputs["causal_fraction_of_988_association"]
    causal_probability = draw_bounded(
        rng, causal_spec["nonzero_probability"], draws, shape, form
    )
    causal_slab = draw_bounded(
        rng, causal_spec["slab_low_mode_high"], draws, shape, form
    )
    causal_fraction, causal_active = spike_slab(
        rng, causal_probability, causal_slab
    )
    benefit_988 = external_988 * pec_share * causal_fraction
    affected_988_spec = inputs["prospective_988_affected_episode_model"]
    affected_988 = (
        draw_bounded(
            rng, affected_988_spec["annual_contacts"], draws, shape, form
        )
        * draw_bounded(
            rng,
            affected_988_spec["unique_episode_factor"],
            draws,
            shape,
            form,
        )
        * draw_bounded(
            rng,
            affected_988_spec["pathway_relevance"],
            draws,
            shape,
            form,
        )
        * draw_bounded(
            rng,
            affected_988_spec["end_to_end_success"],
            draws,
            shape,
            form,
        )
    )
    effect_per_affected_988 = np.divide(
        benefit_988,
        affected_988,
        out=np.zeros(draws),
        where=affected_988 > 0.0,
    )

    annual_ohca = draw_bounded(
        rng,
        inputs["annual_ems_treated_nontraumatic_ohca"],
        draws,
        shape,
        form,
    )
    witnessed = draw_bounded(
        rng, inputs["bystander_witnessed_fraction"], draws, shape, form
    )
    layperson_cpr = draw_bounded(
        rng, inputs["layperson_cpr_given_witnessed"], draws, shape, form
    )
    language_prevalence = draw_bounded(
        rng,
        inputs["language_barrier_prevalence_in_ohca"],
        draws,
        shape,
        form,
    )
    language_success = draw_bounded(
        rng, inputs["language_end_to_end_success"], draws, shape, form
    )
    language_minutes = draw_bounded(
        rng, inputs["language_minutes_recovered"], draws, shape, form
    )
    language_transport_probability = draw_bounded(
        rng,
        inputs["language_transport_nonzero_probability"],
        draws,
        shape,
        form,
    )
    language_transport_active = (
        rng.random(draws) < language_transport_probability
    )
    cpr_causal_attenuation = draw_bounded(
        rng,
        inputs["cpr_timing_association_causal_attenuation"],
        draws,
        shape,
        form,
    )
    language_relevant_episodes = (
        annual_ohca * witnessed * layperson_cpr * language_prevalence
    )
    language_affected_episodes = language_relevant_episodes * language_success
    category_gain = categorical_cpr_gain(
        inputs["cpr_category_weights"],
        inputs["cpr_category_survival_rates"],
        language_minutes,
    )
    language_benefit = (
        language_affected_episodes
        * category_gain
        * cpr_causal_attenuation
        * language_transport_active.astype(float)
    )

    access = inputs["access_sensitivity"]
    access_probability = draw_bounded(
        rng, access["nonzero_probability"], draws, shape, form
    )
    access_active = rng.random(draws) < access_probability
    access_prevalence = draw_bounded(
        rng, access["material_access_problem_prevalence"], draws, shape, form
    )
    access_success = draw_bounded(
        rng, access["access_end_to_end_success"], draws, shape, form
    )
    access_minutes = draw_bounded(
        rng, access["scene_to_patient_minutes_recovered"], draws, shape, form
    )
    response_beta = draw_bounded(
        rng,
        access["dispatch_to_scene_log_odds_gain_per_minute"],
        draws,
        shape,
        form,
    )
    endpoint_transport = draw_bounded(
        rng, access["scene_to_patient_transport_factor"], draws, shape, form
    )
    access_baseline = draw_bounded(
        rng, access["all_ohca_baseline_survival"], draws, shape, form
    )
    access_relevant_episodes = annual_ohca * access_prevalence
    access_affected_episodes = access_relevant_episodes * access_success
    access_gain = logistic_gain(
        access_baseline, response_beta * endpoint_transport * access_minutes
    )
    access_benefit_sensitivity = (
        access_affected_episodes * access_gain * access_active.astype(float)
    )

    primary_gross_benefit = benefit_988 + language_benefit
    with_access_sensitivity = primary_gross_benefit + access_benefit_sensitivity
    full_988_sign_reversal_stress = language_benefit - benefit_988
    mortality_neutral = np.zeros(draws)

    return {
        "arrays": {
            "external_988_association": external_988,
            "988_benefit": benefit_988,
            "988_affected_episodes": affected_988,
            "988_effect_per_affected_episode": effect_per_affected_988,
            "language_benefit": language_benefit,
            "access_benefit_sensitivity": access_benefit_sensitivity,
            "primary_gross_benefit": primary_gross_benefit,
            "with_access_sensitivity": with_access_sensitivity,
            "full_988_sign_reversal_stress": full_988_sign_reversal_stress,
            "zero_988_attribution": language_benefit,
            "zero_language_mortality_transport": benefit_988,
            "mortality_neutral": mortality_neutral,
            "language_relevant_episodes": language_relevant_episodes,
            "language_affected_episodes": language_affected_episodes,
            "cpr_causal_attenuation": cpr_causal_attenuation,
            "access_relevant_episodes": access_relevant_episodes,
            "access_affected_episodes": access_affected_episodes,
        },
        "activation": {
            "988_share_active": float(np.mean(share_active)),
            "988_causal_active": float(np.mean(causal_active)),
            "language_transport_active": float(np.mean(language_transport_active)),
            "access_transport_active": float(np.mean(access_active)),
        },
        "summaries": {
            "external_988_association": summarize(external_988),
            "988_benefit": summarize(benefit_988),
            "988_affected_episodes": summarize(affected_988),
            "988_effect_per_affected_episode": summarize(
                effect_per_affected_988
            ),
            "language_benefit": summarize(language_benefit),
            "cpr_causal_attenuation": summarize(cpr_causal_attenuation),
            "access_benefit_sensitivity": summarize(access_benefit_sensitivity),
            "primary_gross_benefit": summarize(primary_gross_benefit),
            "with_access_sensitivity": summarize(with_access_sensitivity),
            "full_988_sign_reversal_stress": summarize(
                full_988_sign_reversal_stress
            ),
            "zero_988_attribution": summarize(language_benefit),
            "zero_language_mortality_transport": summarize(benefit_988),
            "mortality_neutral": summarize(mortality_neutral),
        },
    }


def serializable(result: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in result.items() if key != "arrays"}


def main() -> None:
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    config = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    metadata = config["metadata"]
    inputs = config["near_term_prospective_scenario"]
    draws = int(metadata["near_term_draws"])
    sensitivity_draws = int(metadata["sensitivity_draws"])
    seed = int(metadata["near_term_rng_seed"])
    shape = float(metadata["pert_shape"])

    primary = simulate_near_term(
        inputs, np.random.default_rng(seed), draws, shape, form="pert"
    )
    distribution_sensitivity: dict[str, object] = {}
    for offset, form in enumerate(metadata["distribution_forms"]):
        result = simulate_near_term(
            inputs,
            np.random.default_rng(seed + 1000 + offset),
            sensitivity_draws,
            shape,
            form=form,
        )
        distribution_sensitivity[form] = result["summaries"]

    output = {
        "metadata": {
            "release_tag": metadata["release_tag"],
            "seed": seed,
            "draws": draws,
            "estimand": "near-term prospective gross mortality benefit conditional on future deployment; beneficial effects only",
            "primary_interpretation": metadata["interpretation"],
            "access_mortality_treatment": "zero in the primary scenario; prospective cross-endpoint sensitivity reported separately",
            "cpr_model": "published delay categories and category-specific observed absolute survival rates; no constant per-minute slope",
            "cpr_causal_attenuation": "A separate bounded attenuation factor applies to the observational timing-category survival contrast after the language-transport spike activates.",
            "988_pairing": "The prospective 988 affected-episode denominator is generated in this module and passed unchanged to the economic model. The external association attribution remains an aggregate sensitivity, not an observed incident-level effect.",
            "988_sign_stress": "The primary near-term scenario follows the beneficial sign of the cited external association. A deliberately hostile stress reverses the entire activated PEC-attributed 988 component at the same magnitude; it is a bound, not a probability model.",
            "expert_elicitation": metadata["elicitation_status"],
        },
        "primary_pert": serializable(primary),
        "distribution_form_sensitivity": distribution_sensitivity,
    }
    RESULT_FILE.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    headline = primary["summaries"]["primary_gross_benefit"]
    print(
        "near_term_prospective_gross_benefit "
        f"mean={headline['mean']:.3f} median={headline['median']:.3f} "
        f"p5={headline['p5']:.3f} p95={headline['p95']:.3f} "
        f"p_zero={headline['probability_zero']:.4f}"
    )


if __name__ == "__main__":
    main()