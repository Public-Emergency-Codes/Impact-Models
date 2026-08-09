"""Future mature PEC mortality planning model using unique emergency episodes.

The model is prospective and conditional on future deployment.  A person may
contribute multiple emergency episodes per year.  Each latent unique episode
may use multiple PEC functions but receives one benefit/harm/none outcome.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .common import (
    draw_bounded,
    exclusive_outcome_counts,
    gaussian_copula_uniforms,
    summarize,
    t_copula_uniforms,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "config" / "mortality-model-inputs.json"
RESULT_FILE = PROJECT_ROOT / "results" / "mortality-mature-results.json"


def _common_multipliers(
    full: dict[str, object],
    rng: np.random.Generator,
    draws: int,
    shape: float,
    form: str,
    dependence_rho: float,
    copula_family: str,
) -> dict[str, np.ndarray]:
    specs = full["common_multipliers"]
    copula_draw = (
        gaussian_copula_uniforms
        if copula_family == "gaussian"
        else t_copula_uniforms
    )
    uniforms = copula_draw(rng, draws, len(specs), dependence_rho)
    return {
        name: draw_bounded(
            rng,
            values,
            draws,
            shape,
            form,
            uniforms=uniforms[:, index],
        )
        for index, (name, values) in enumerate(specs.items())
    }


def _allocate_unique_episode_counts(
    rng: np.random.Generator,
    expected_counts: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Poisson total followed by one multinomial pathway assignment per episode."""

    names = tuple(expected_counts)
    total_expected = sum(expected_counts.values())
    total_count = rng.poisson(np.maximum(total_expected, 0.0)).astype(np.int64)
    remaining_count = total_count.copy()
    remaining_probability = np.ones(len(total_count))
    allocated: dict[str, np.ndarray] = {}
    for name in names:
        probability = np.divide(
            expected_counts[name],
            total_expected,
            out=np.zeros_like(total_expected),
            where=total_expected > 0.0,
        )
        conditional = np.divide(
            probability,
            remaining_probability,
            out=np.zeros_like(probability),
            where=remaining_probability > 0.0,
        )
        count = rng.binomial(remaining_count, np.clip(conditional, 0.0, 1.0))
        allocated[name] = count
        remaining_count -= count
        remaining_probability = np.maximum(remaining_probability - probability, 0.0)
    if np.any(sum(allocated.values()) != total_count):
        raise AssertionError("unique emergency episodes were not allocated exactly once")
    return allocated


def simulate(
    full: dict[str, object],
    rng: np.random.Generator,
    draws: int,
    shape: float,
    form: str = "pert",
    dependence_rho: float = 0.5,
    copula_family: str = "gaussian",
    outcome_rng: np.random.Generator | None = None,
    deduplication_mode: str = "sampled",
    return_path_arrays: bool = False,
) -> dict[str, object]:
    paths = tuple(full["pathways"])
    names = tuple(path["name"] for path in paths)
    n_paths = len(paths)
    if copula_family not in {"gaussian", "t"}:
        raise ValueError(f"unknown copula family: {copula_family}")
    common = _common_multipliers(
        full,
        rng,
        draws,
        shape,
        form,
        dependence_rho,
        copula_family,
    )

    copula_draw = (
        gaussian_copula_uniforms
        if copula_family == "gaussian"
        else t_copula_uniforms
    )
    copulas = {
        family: copula_draw(rng, draws, n_paths, dependence_rho)
        for family in (
            "episode",
            "relevance",
            "success",
            "benefit_probability",
            "benefit_arr",
            "benefit_activation",
            "harm_probability",
            "harm_arr",
            "harm_activation",
        )
    }

    implementation = (
        common["national_reach_index"]
        * common["user_activation_index"]
        * common["technical_reliability_index"]
        * common["receiver_compatibility_index"]
    ) ** 0.25
    h_plus = common["beneficial_clinical_effect"]
    h_minus = common["adverse_clinical_effect"]

    raw_episode_counts: dict[str, np.ndarray] = {}
    success_arrays: dict[str, np.ndarray] = {}
    benefit_probability_arrays: dict[str, np.ndarray] = {}
    harm_probability_arrays: dict[str, np.ndarray] = {}
    episode_factor_arrays: dict[str, np.ndarray] = {}
    effect_activation: dict[str, dict[str, float]] = {}

    for i, path in enumerate(paths):
        opportunities = (
            draw_bounded(
                rng,
                path["opportunity_range"],
                draws,
                shape,
                form,
            )
            if "opportunity_range" in path
            else np.full(draws, float(path["opportunities"]))
        )
        if deduplication_mode == "low_unique_episode_factor_stress":
            episode_factor = np.full(draws, float(path["unique_episode_factor"][0]))
        else:
            episode_factor = draw_bounded(
                rng,
                path["unique_episode_factor"],
                draws,
                shape,
                form,
                uniforms=copulas["episode"][:, i],
            )
        relevance = draw_bounded(
            rng,
            path["relevance"],
            draws,
            shape,
            form,
            uniforms=copulas["relevance"][:, i],
        )
        success = np.clip(
            draw_bounded(
                rng,
                path["success"],
                draws,
                shape,
                form,
                uniforms=copulas["success"][:, i],
            )
            * implementation,
            0.0,
            0.995,
        )
        positive_nonzero_probability = draw_bounded(
            rng,
            path["beneficial_effect_nonzero_probability"],
            draws,
            shape,
            form,
            uniforms=copulas["benefit_probability"][:, i],
        )
        positive_active = (
            copulas["benefit_activation"][:, i] < positive_nonzero_probability
        )
        benefit_arr = (
            draw_bounded(
                rng,
                path["beneficial_arr"],
                draws,
                shape,
                form,
                uniforms=copulas["benefit_arr"][:, i],
            )
            * h_plus
            * positive_active.astype(float)
        )
        adverse_nonzero_probability = draw_bounded(
            rng,
            path["adverse_effect_nonzero_probability"],
            draws,
            shape,
            form,
            uniforms=copulas["harm_probability"][:, i],
        )
        adverse_active = (
            copulas["harm_activation"][:, i] < adverse_nonzero_probability
        )
        harm_arr = (
            draw_bounded(
                rng,
                path["adverse_arr"],
                draws,
                shape,
                form,
                uniforms=copulas["harm_arr"][:, i],
            )
            * h_minus
            * adverse_active.astype(float)
        )
        benefit_arr = np.clip(benefit_arr, 0.0, 0.5)
        harm_arr = np.clip(harm_arr, 0.0, 0.5 - benefit_arr)

        raw_episode_counts[path["name"]] = opportunities * episode_factor * relevance
        success_arrays[path["name"]] = success
        benefit_probability_arrays[path["name"]] = benefit_arr
        harm_probability_arrays[path["name"]] = harm_arr
        episode_factor_arrays[path["name"]] = episode_factor
        effect_activation[path["name"]] = {
            "beneficial_nonzero_frequency": float(np.mean(positive_active)),
            "adverse_nonzero_frequency": float(np.mean(adverse_active)),
        }

    expected_total_unique_episodes = sum(raw_episode_counts.values())
    affected_arrays: dict[str, np.ndarray] = {}
    beneficial_arrays: dict[str, np.ndarray] = {}
    adverse_arrays: dict[str, np.ndarray] = {}
    path_net_arrays: dict[str, np.ndarray] = {}
    tier_c_zero_arrays: dict[str, np.ndarray] = {}
    access_zero_arrays: dict[str, np.ndarray] = {}
    adverse_only_arrays: dict[str, np.ndarray] = {}
    path_summaries: dict[str, object] = {}

    planning_expected = np.zeros(draws)
    tier_c_zero_expected = np.zeros(draws)
    access_zero_expected = np.zeros(draws)
    adverse_only_expected = np.zeros(draws)

    for path in paths:
        name = path["name"]
        affected = raw_episode_counts[name] * success_arrays[name]
        beneficial = affected * benefit_probability_arrays[name]
        adverse = affected * harm_probability_arrays[name]
        net = beneficial - adverse
        tier_c_net = -adverse if path["tier"] == "C" else net
        access_zero_net = -adverse if name == "location/responder access" else net

        affected_arrays[name] = affected
        beneficial_arrays[name] = beneficial
        adverse_arrays[name] = adverse
        path_net_arrays[name] = net
        tier_c_zero_arrays[name] = tier_c_net
        access_zero_arrays[name] = access_zero_net
        adverse_only_arrays[name] = -adverse
        planning_expected += net
        tier_c_zero_expected += tier_c_net
        access_zero_expected += access_zero_net
        adverse_only_expected -= adverse

        path_summaries[name] = {
            "tier": path["tier"],
            "functions_allowed_to_act_jointly": path["functions"],
            "opportunity_unit": path["opportunity_unit"],
            "unique_episode_factor": summarize(episode_factor_arrays[name]),
            "unique_relevant_episodes": summarize(raw_episode_counts[name]),
            "affected_episodes": summarize(affected),
            "beneficial_lives": summarize(beneficial),
            "adverse_lives": summarize(adverse),
            "net_lives": summarize(net),
            "beneficial_probability_per_affected_episode": summarize(
                benefit_probability_arrays[name]
            ),
            "adverse_probability_per_affected_episode": summarize(
                harm_probability_arrays[name]
            ),
            **effect_activation[name],
        }

    predictive = planning_expected
    tier_c_predictive = tier_c_zero_expected
    access_zero_predictive = access_zero_expected
    adverse_only_predictive = adverse_only_expected
    if outcome_rng is not None:
        episode_counts = _allocate_unique_episode_counts(
            outcome_rng, raw_episode_counts
        )
        predictive = np.zeros(draws, dtype=np.int64)
        tier_c_predictive = np.zeros(draws, dtype=np.int64)
        access_zero_predictive = np.zeros(draws, dtype=np.int64)
        adverse_only_predictive = np.zeros(draws, dtype=np.int64)
        for path in paths:
            name = path["name"]
            affected_count = outcome_rng.binomial(
                episode_counts[name], success_arrays[name]
            )
            benefit_count, harm_count = exclusive_outcome_counts(
                outcome_rng,
                affected_count,
                benefit_probability_arrays[name],
                harm_probability_arrays[name],
            )
            predictive += benefit_count - harm_count
            tier_benefit_probability = (
                np.zeros(draws)
                if path["tier"] == "C"
                else benefit_probability_arrays[name]
            )
            tier_benefit, tier_harm = exclusive_outcome_counts(
                outcome_rng,
                affected_count,
                tier_benefit_probability,
                harm_probability_arrays[name],
            )
            tier_c_predictive += tier_benefit - tier_harm
            access_benefit_probability = (
                np.zeros(draws)
                if name == "location/responder access"
                else benefit_probability_arrays[name]
            )
            access_benefit, access_harm = exclusive_outcome_counts(
                outcome_rng,
                affected_count,
                access_benefit_probability,
                harm_probability_arrays[name],
            )
            access_zero_predictive += access_benefit - access_harm
            _, stress_harm = exclusive_outcome_counts(
                outcome_rng,
                affected_count,
                np.zeros(draws),
                harm_probability_arrays[name],
            )
            adverse_only_predictive -= stress_harm

    mortality_neutral = np.zeros(draws)
    result: dict[str, object] = {
        "summaries": {
            "all_pathway_parameter": summarize(planning_expected),
            "all_pathway_predictive": summarize(predictive),
            "tier_c_positive_zero_parameter": summarize(tier_c_zero_expected),
            "tier_c_positive_zero_predictive": summarize(tier_c_predictive),
            "access_mortality_zero_parameter": summarize(access_zero_expected),
            "access_mortality_zero_predictive": summarize(access_zero_predictive),
            "mortality_neutral": summarize(mortality_neutral),
            "adverse_only_parameter": summarize(adverse_only_expected),
            "adverse_only_predictive": summarize(adverse_only_predictive),
            "unique_relevant_episode_total": summarize(expected_total_unique_episodes),
        },
        "pathways": path_summaries,
        "dependence_rho": dependence_rho,
        "copula_family": copula_family,
        "distribution_form": form,
        "deduplication_mode": deduplication_mode,
        "common_multiplier_dependence": {
            "rho": dependence_rho,
            "copula_family": copula_family,
            "benefit_harm_multiplier_correlation": float(
                np.corrcoef(h_plus, h_minus)[0, 1]
            ),
        },
    }
    if return_path_arrays:
        result["arrays"] = {
            "all_pathway": planning_expected,
            "tier_c_positive_zero": tier_c_zero_expected,
            "access_mortality_zero": access_zero_expected,
            "mortality_neutral": mortality_neutral,
            "adverse_only": adverse_only_expected,
            "affected_episodes": affected_arrays,
            "path_net_lives": path_net_arrays,
            "tier_c_positive_zero_path_lives": tier_c_zero_arrays,
            "access_mortality_zero_path_lives": access_zero_arrays,
            "adverse_only_path_lives": adverse_only_arrays,
            "beneficial_lives": beneficial_arrays,
            "adverse_lives": adverse_arrays,
        }
    return result


def serializable(result: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in result.items() if key != "arrays"}


def main() -> None:
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    config = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    metadata = config["metadata"]
    full = config["future_mature_scenario"]
    draws = int(metadata["mature_draws"])
    sensitivity_draws = int(metadata["sensitivity_draws"])
    shape = float(metadata["pert_shape"])
    seed = int(metadata["mature_parameter_rng_seed"])
    predictive_seed = int(metadata["mature_predictive_rng_seed"])

    primary = simulate(
        full,
        np.random.default_rng(seed),
        draws,
        shape,
        form="pert",
        dependence_rho=0.5,
        outcome_rng=np.random.default_rng(predictive_seed),
    )

    dependence_sensitivity: dict[str, object] = {}
    for offset, rho in enumerate(metadata["dependence_rhos"]):
        run = simulate(
            full,
            np.random.default_rng(seed + 100 + offset),
            sensitivity_draws,
            shape,
            form="pert",
            dependence_rho=float(rho),
        )
        dependence_sensitivity[str(rho)] = run["summaries"]

    distribution_sensitivity: dict[str, object] = {}
    for offset, form in enumerate(metadata["distribution_forms"]):
        run = simulate(
            full,
            np.random.default_rng(seed + 200 + offset),
            sensitivity_draws,
            shape,
            form=form,
            dependence_rho=0.5,
        )
        distribution_sensitivity[form] = run["summaries"]

    moment_matched_sensitivity: dict[str, object] = {}
    for offset, form in enumerate(metadata["moment_matched_distribution_forms"]):
        run = simulate(
            full,
            np.random.default_rng(seed + 225 + offset),
            sensitivity_draws,
            shape,
            form=form,
            dependence_rho=0.5,
        )
        moment_matched_sensitivity[form] = run["summaries"]

    copula_sensitivity: dict[str, object] = {}
    for offset, family in enumerate(("gaussian", "t")):
        run = simulate(
            full,
            np.random.default_rng(seed + 250 + offset),
            sensitivity_draws,
            shape,
            form="pert",
            dependence_rho=0.5,
            copula_family=family,
        )
        copula_sensitivity[family] = run["summaries"]

    low_unique_episode_factor = simulate(
        full,
        np.random.default_rng(seed + 300),
        sensitivity_draws,
        shape,
        form="pert",
        dependence_rho=0.5,
        deduplication_mode="low_unique_episode_factor_stress",
    )

    output = {
        "metadata": {
            "release_tag": metadata["release_tag"],
            "parameter_seed": seed,
            "predictive_seed": predictive_seed,
            "draws": draws,
            "master_unit": full["master_unit"],
            "episode_rule": full["episode_rule"],
            "implementation_index_rule": full["implementation_index_rule"],
            "predictive_interval_label": "conditional future-deployment predictive interval under the stated model",
            "dependence_model": full["dependence_model"],
            "copula_algorithm": "For each dependence block, latent equicorrelated variables are Z_j=sqrt(rho) Z_0+sqrt(1-rho) epsilon_j. Gaussian uniforms are Phi(Z_j). Student-t uniforms divide the same correlated normals by sqrt(ChiSq_4/4) and apply the t_4 CDF. Separate blocks cover common multipliers and each pathway family: episode factor, relevance, success, benefit-presence probability, benefit ARR, benefit activation, harm-presence probability, harm ARR, and harm activation. Bernoulli indicators equal one when the activation uniform is below the sampled presence probability.",
            "predictive_count_algorithm": "For every parameter draw, K~Poisson(sum_j N_j); pathway counts C~Multinomial(K, N_j/sum N_j), implemented by sequential binomials; affected counts A_j~Binomial(C_j, success_j); and benefit/harm/none counts are multinomial with probabilities Delta_j^+, Delta_j^-, and 1-Delta_j^+-Delta_j^-, implemented by sequential conditional binomials.",
            "marginal_distribution_algorithm": "PERT uses shape 8 with alpha=1+8(mode-low)/(high-low) and beta=1+8(high-mode)/(high-low). Triangular uses the same low/mode/high. Uniform uses only low/high. Bounded logit-normal centers at logit(mode) and sets latent SD=(logit(high)-logit(low))/(2*1.6448536269514722), then clips; nonprobability quantities use a bounded normal centered at mode with SD=(high-low)/(2*1.6448536269514722). Moment-matched sensitivities monotonically affine-standardize each alternative to the PERT mean and SD with iterative hard-bound clipping.",
            "student_t_degrees_of_freedom": 4,
            "expert_elicitation": metadata["elicitation_status"],
        },
        "primary_pert_medium_dependence": serializable(primary),
        "dependence_sensitivity": dependence_sensitivity,
        "distribution_form_sensitivity": distribution_sensitivity,
        "moment_matched_distribution_sensitivity": moment_matched_sensitivity,
        "copula_family_sensitivity": copula_sensitivity,
        "low_unique_episode_factor_stress": serializable(
            low_unique_episode_factor
        ),
    }
    RESULT_FILE.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    headline = primary["summaries"]["all_pathway_predictive"]
    print(
        "future_mature_all_pathway "
        f"mean={headline['mean']:.3f} median={headline['median']:.3f} "
        f"p5={headline['p5']:.3f} p95={headline['p95']:.3f}"
    )


if __name__ == "__main__":
    main()