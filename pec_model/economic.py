"""Prospective PEC economic model coupled to unique emergency episodes."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from .economic_inputs import (
    CALL_MIX,
    NEAR_TERM_ECONOMIC_SEED,
    DRAWS,
    DRIVER_RANGES,
    FEATURE_NAMES,
    MATURE_ECONOMIC_SEED,
    MEDICAL_RESOURCE_SHARES,
    MONEY_CATEGORIES,
    MORTALITY_INPUT_FILE,
    NEAR_TERM_PATHWAY_SCALE,
    PATHWAYS,
    PERT_SHAPE,
    PROPERTY_MIX,
    RECEIVER_RESOURCE_COSTS,
    SEED,
    SYSTEMS,
    TRAVEL_REGIONS,
    TRAVELER_MORTALITY_INPUTS,
    Pathway,
)
from .mortality_near_term import simulate_near_term
from .mortality_mature import simulate as simulate_mature_mortality
from .common import (
    draw_bounded,
    gaussian_copula_uniforms,
    summarize,
    t_copula_uniforms,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
RESULT_FILE = RESULTS_DIR / "economic-results.json"
_ACTIVE_DISTRIBUTION_FORM = "pert"


def draw(
    rng: np.random.Generator,
    values: tuple[float, float, float],
    form: str | None = None,
    uniforms: np.ndarray | None = None,
) -> np.ndarray:
    selected = _ACTIVE_DISTRIBUTION_FORM if form is None else form
    return draw_bounded(
        rng,
        values,
        DRAWS,
        PERT_SHAPE,
        selected,
        uniforms=uniforms,
    )


def weighted_geometric(
    drivers: dict[str, np.ndarray], weights: dict[str, float]
) -> np.ndarray:
    out = np.zeros(DRAWS)
    for name, weight in weights.items():
        out += weight * np.log(np.maximum(drivers[name], 1e-9))
    return np.exp(out)


def economic_driver_draws(
    rng: np.random.Generator,
    dependence_rho: float,
    copula_family: str,
) -> dict[str, np.ndarray]:
    if copula_family not in {"gaussian", "t"}:
        raise ValueError(f"unknown copula family: {copula_family}")
    copula = (
        gaussian_copula_uniforms
        if copula_family == "gaussian"
        else t_copula_uniforms
    )
    uniforms = copula(rng, DRAWS, len(DRIVER_RANGES), dependence_rho)
    return {
        name: draw(rng, values, uniforms=uniforms[:, index])
        for index, (name, values) in enumerate(DRIVER_RANGES.items())
    }


def mortality_coupling(
    scenario: str,
    form: str,
    dependence_rho: float,
    copula_family: str,
) -> dict[str, object]:
    config = json.loads(MORTALITY_INPUT_FILE.read_text(encoding="utf-8"))
    metadata = config["metadata"]
    shape = float(metadata["pert_shape"])
    if scenario == "near_term":
        run = simulate_near_term(
            config["near_term_prospective_scenario"],
            np.random.default_rng(int(metadata["near_term_rng_seed"])),
            DRAWS,
            shape,
            form=form,
        )
        arrays = run["arrays"]
        return {
            "path_lives": {
                "988/crisis connection": arrays["988_benefit"],
                "silent/language access": arrays["language_benefit"],
                "location/responder access": np.zeros(DRAWS),
            },
            "affected_episodes": {
                "988/crisis connection": arrays["988_affected_episodes"],
                "silent/language access": arrays["language_affected_episodes"],
                "location/responder access": arrays["access_affected_episodes"],
            },
            "tier_c_path_lives": {},
            "adverse_only_path_lives": {},
        }

    run = simulate_mature_mortality(
        config["future_mature_scenario"],
        np.random.default_rng(int(metadata["mature_parameter_rng_seed"])),
        DRAWS,
        shape,
        form=form,
        dependence_rho=dependence_rho,
        copula_family=copula_family,
        return_path_arrays=True,
    )
    arrays = run["arrays"]
    mappings = (
        arrays["affected_episodes"],
        arrays["path_net_lives"],
        arrays["tier_c_positive_zero_path_lives"],
        arrays["adverse_only_path_lives"],
    )
    for mapping in mappings:
        mapping["cardiac-arrest rapid assistance"] = mapping.pop(
            "cardiac-arrest bystander assistance"
        )
    return {
        "path_lives": arrays["path_net_lives"],
        "affected_episodes": arrays["affected_episodes"],
        "tier_c_path_lives": arrays["tier_c_positive_zero_path_lives"],
        "adverse_only_path_lives": arrays["adverse_only_path_lives"],
    }


def scenario_affected(
    rng: np.random.Generator,
    path: Pathway,
    scenario: str,
    drivers: dict[str, np.ndarray],
    coupled: dict[str, object],
) -> tuple[np.ndarray, np.ndarray | float]:
    coupled_affected = coupled["affected_episodes"].get(path.name)
    if coupled_affected is not None:
        return coupled_affected, 1.0

    regional_cost_factor: np.ndarray | float = 1.0
    if path.name == "U.S. traveler abroad":
        opportunities = draw(rng, TRAVELER_MORTALITY_INPUTS["exposure_departures"])
        unfamiliar = np.zeros(DRAWS)
        weighted_consequence = np.zeros(DRAWS)
        for _, share, unfamiliarity, consequence in TRAVEL_REGIONS:
            unfamiliar_draw = draw(rng, unfamiliarity)
            unfamiliar += share * unfamiliar_draw
            weighted_consequence += share * unfamiliar_draw * draw(rng, consequence)
        regional_cost_factor = weighted_consequence / np.maximum(unfamiliar, 1e-9)
        relevance = draw(rng, path.relevance) * unfamiliar
    elif path.name == "cardiac-arrest rapid assistance":
        opportunities = draw(rng, (220000.0, 250000.0, 300000.0))
        relevance = draw(rng, path.relevance)
    else:
        opportunities = np.full(DRAWS, path.opportunities)
        relevance = draw(rng, path.relevance)
    success = draw(rng, path.success)
    unique_episode_factor = draw(rng, path.overlap)
    modifier = weighted_geometric(drivers, path.driver_weights)
    deployment_scale = (
        NEAR_TERM_PATHWAY_SCALE[path.name] if scenario == "near_term" else 1.0
    )
    completion = np.clip(success * modifier * deployment_scale, 0.0, 1.0)
    affected = opportunities * unique_episode_factor * relevance * completion
    return np.minimum(affected, opportunities), regional_cost_factor


def stochastic_adoption(
    rng: np.random.Generator,
) -> tuple[list[dict[str, float]], dict[str, np.ndarray]]:
    asymptote = draw(rng, (0.55, 0.82, 0.97))
    midpoint = draw(rng, (3.5, 5.5, 8.0))
    slope = draw(rng, (0.45, 0.8, 1.25))
    arrays: dict[str, np.ndarray] = {}
    rows: list[dict[str, float]] = []
    for year in range(1, 11):
        adoption = asymptote / (1.0 + np.exp(-slope * (year - midpoint)))
        arrays[str(year)] = adoption
        rows.append({"year": year, **summarize(adoption)})
    return rows, arrays


def named_adoption_scenarios() -> list[dict[str, float | str]]:
    specifications = {
        "delayed": (0.65, 7.0, 0.55),
        "central": (0.85, 5.5, 0.80),
        "accelerated": (0.95, 4.0, 1.10),
    }
    rows: list[dict[str, float | str]] = []
    for name, (asymptote, midpoint, slope) in specifications.items():
        values = {
            year: asymptote / (1.0 + np.exp(-slope * (year - midpoint)))
            for year in (1, 5, 10)
        }
        rows.append(
            {
                "scenario": name,
                "asymptote": asymptote,
                "midpoint_year": midpoint,
                "slope": slope,
                "year_1": values[1],
                "year_5": values[5],
                "year_10": values[10],
            }
        )
    return rows


def morris_emulator_screening(component_means: dict[str, float]) -> list[dict[str, float]]:
    names = (
        "deployment_reach",
        "receiver_compatibility",
        "medical_resource_cost",
        "public_operating_cost",
        "productivity_value",
        "property_value",
        "mortality_effect",
        "vsl",
    )
    rng = np.random.default_rng(20261212)
    delta = 0.2

    def evaluate(x: np.ndarray) -> float:
        reach, compatibility, medical, public_op, productivity, property, mortality, vsl = x
        implementation = reach * compatibility
        direct = component_means["direct"] * implementation * (0.6 + 0.4 * medical)
        capacity = component_means["capacity"] * implementation * public_op
        prod = component_means["productivity"] * implementation * productivity
        prop = component_means["property"] * implementation * property
        mort = component_means["mortality"] * implementation * mortality * vsl
        return direct + capacity + prod + prop + mort

    effects = {name: [] for name in names}
    for _ in range(240):
        base = rng.uniform(0.2, 0.8, len(names))
        y0 = evaluate(base)
        for i, name in enumerate(names):
            shifted = base.copy()
            shifted[i] = min(1.0, shifted[i] + delta)
            effects[name].append((evaluate(shifted) - y0) / delta)
    rows = []
    for name, values in effects.items():
        rows.append(
            {
                "assumption": name,
                "mu_star": float(np.mean(np.abs(values))),
                "sigma": float(np.std(values)),
            }
        )
    total = sum(row["mu_star"] for row in rows)
    for row in rows:
        row["normalized_mu_star"] = row["mu_star"] / total if total else 0.0
    return sorted(rows, key=lambda row: row["mu_star"], reverse=True)


def simulate(
    scenario: str,
    seed: int,
    distribution_form: str = "pert",
    dependence_rho: float = 0.5,
    copula_family: str = "gaussian",
) -> dict[str, object]:
    global _ACTIVE_DISTRIBUTION_FORM
    _ACTIVE_DISTRIBUTION_FORM = distribution_form
    rng = np.random.default_rng(seed)
    drivers = economic_driver_draws(rng, dependence_rho, copula_family)
    coupled = mortality_coupling(
        scenario,
        distribution_form,
        dependence_rho,
        copula_family,
    )
    adoption_rows, adoption_arrays = stochastic_adoption(rng)
    vsl = draw(rng, (6.6e6, 14.1e6, 21.5e6))
    vqaly = draw(rng, (0.340e6, 0.726e6, 1.107e6))

    money = {category: np.zeros(DRAWS) for category in MONEY_CATEGORIES}
    direct_process_benchmark = np.zeros(DRAWS)
    qaly_gain = np.zeros(DRAWS)
    qaly_valuation_sensitivity = np.zeros(DRAWS)
    call_hours = np.zeros(DRAWS)
    workdays = np.zeros(DRAWS)
    lives = np.zeros(DRAWS)
    domestic_lives = np.zeros(DRAWS)
    traveler_lives = np.zeros(DRAWS)
    tier_c_zero_lives = np.zeros(DRAWS)
    adverse_only_lives = np.zeros(DRAWS)

    feature_resource = {number: 0.0 for number in FEATURE_NAMES}
    feature_vsl = {number: 0.0 for number in FEATURE_NAMES}
    system_public = {name: 0.0 for name in SYSTEMS}
    system_capacity = {name: 0.0 for name in SYSTEMS}
    family_resource: dict[str, float] = {}
    family_vsl: dict[str, float] = {}
    path_means: dict[str, dict[str, float]] = {}

    for path in PATHWAYS:
        affected, regional_cost_factor = scenario_affected(
            rng, path, scenario, drivers, coupled
        )
        medical_share = MEDICAL_RESOURCE_SHARES[path.name]
        medical_multiplier = 1.0 + medical_share * (drivers["medical_cost"] - 1.0)
        public_gross_unit = draw(rng, path.economics["public_fiscal"])
        capacity_gross_unit = draw(rng, path.economics["capacity"])
        receiver_cost = {
            category: draw(rng, values)
            for category, values in RECEIVER_RESOURCE_COSTS[path.name].items()
        }
        if path.name == "U.S. traveler abroad":
            public_gross_unit *= regional_cost_factor
            capacity_gross_unit *= regional_cost_factor
            receiver_cost = {
                category: values * regional_cost_factor
                for category, values in receiver_cost.items()
            }
        path_money: dict[str, np.ndarray] = {
            "public_fiscal": affected
            * (
                public_gross_unit * medical_multiplier
                - receiver_cost["public_fiscal"]
            ),
            "capacity": affected
            * (
                capacity_gross_unit * drivers["public_operating_cost"]
                - receiver_cost["capacity"]
            ),
        }
        for category in (
            "private_household",
            "other_direct_resource",
            "productivity_morbidity",
            "property",
        ):
            gross_unit = draw(rng, path.economics[category])
            if path.name == "U.S. traveler abroad":
                gross_unit *= regional_cost_factor
            if category in {"private_household", "other_direct_resource"}:
                net_unit = gross_unit * medical_multiplier - receiver_cost[category]
            elif category == "productivity_morbidity":
                net_unit = gross_unit * drivers["productivity_value"]
            elif category == "property":
                net_unit = gross_unit * drivers["property_loss"]
            path_money[category] = affected * net_unit
        for category, values in path_money.items():
            money[category] += values

        path_gross_public_resource = (
            path_money["public_fiscal"] + path_money["capacity"]
        )
        if not np.allclose(
            path_gross_public_resource,
            path_money["public_fiscal"] + path_money["capacity"],
        ):
            raise AssertionError("public expenditure/capacity partition failed")

        path_qaly = affected * draw(rng, path.qaly) * drivers["disability_cost"]
        qaly_gain += path_qaly
        qaly_valuation_sensitivity += path_qaly * vqaly
        call_hours += affected * draw(rng, path.call_minutes) / 60.0
        workdays += affected * draw(rng, path.workdays)

        if path.name == "U.S. traveler abroad" and scenario == "mature":
            benefit_active = rng.random(DRAWS) < draw(
                rng,
                TRAVELER_MORTALITY_INPUTS[
                    "beneficial_activation_probability"
                ],
            )
            harm_active = rng.random(DRAWS) < draw(
                rng,
                TRAVELER_MORTALITY_INPUTS["adverse_activation_probability"],
            )
            benefit_arr = draw(rng, path.benefit_arr)
            harm_arr = draw(rng, path.harm_arr)
            h_plus = draw(
                rng,
                TRAVELER_MORTALITY_INPUTS["beneficial_effect_multiplier"],
            )
            h_minus = draw(
                rng,
                TRAVELER_MORTALITY_INPUTS["adverse_effect_multiplier"],
            )
            traveler_benefit_lives = (
                affected * benefit_active.astype(float) * benefit_arr * h_plus
            )
            traveler_harm_lives = (
                affected * harm_active.astype(float) * harm_arr * h_minus
            )
            path_lives = traveler_benefit_lives - traveler_harm_lives
            tier_path_lives = path_lives
            adverse_path_lives = -traveler_harm_lives
        else:
            path_lives = coupled["path_lives"].get(path.name, np.zeros(DRAWS))
            tier_path_lives = coupled["tier_c_path_lives"].get(
                path.name, path_lives
            )
            adverse_path_lives = coupled["adverse_only_path_lives"].get(
                path.name, np.zeros(DRAWS)
            )
        lives += path_lives
        if path.name == "U.S. traveler abroad":
            traveler_lives += path_lives
        else:
            domestic_lives += path_lives
        tier_c_zero_lives += tier_path_lives
        adverse_only_lives += adverse_path_lives

        path_direct = (
            path_money["public_fiscal"]
            + path_money["capacity"]
            + path_money["private_household"]
            + path_money["other_direct_resource"]
        )
        path_resource_total = (
            path_direct
            + path_money["productivity_morbidity"]
            + path_money["property"]
        )
        direct_process_benchmark += np.where(
            path_direct >= 0.0,
            path_direct * path.evidence_weight,
            path_direct,
        )
        path_vsl = path_lives * vsl

        path_means[path.name] = {
            "affected_unique_episodes": float(np.mean(affected)),
            "potential_variable_public_expenditure_avoided": float(
                np.mean(path_money["public_fiscal"])
            ),
            "capacity_value": float(np.mean(path_money["capacity"])),
            "gross_public_resource_value": float(
                np.mean(path_gross_public_resource)
            ),
            "private_household": float(np.mean(path_money["private_household"])),
            "other_direct_resource": float(
                np.mean(path_money["other_direct_resource"])
            ),
            "productivity": float(np.mean(path_money["productivity_morbidity"])),
            "property": float(np.mean(path_money["property"])),
            "qaly_unmonetized": float(np.mean(path_qaly)),
            "lives": float(np.mean(path_lives)),
            "resource_total_excluding_vsl": float(np.mean(path_resource_total)),
            "mortality_risk_value": float(np.mean(path_vsl)),
            "receiver_public_cost_per_changed_episode_mean": float(
                np.mean(receiver_cost["public_fiscal"])
            ),
            "receiver_capacity_cost_per_changed_episode_mean": float(
                np.mean(receiver_cost["capacity"])
            ),
            "receiver_private_cost_per_changed_episode_mean": float(
                np.mean(receiver_cost["private_household"])
            ),
            "receiver_other_direct_cost_per_changed_episode_mean": float(
                np.mean(receiver_cost["other_direct_resource"])
            ),
            "receiver_total_direct_cost_per_changed_episode_mean": float(
                sum(np.mean(values) for values in receiver_cost.values())
            ),
        }

        for feature, weight in path.features.items():
            feature_resource[feature] += float(np.mean(path_resource_total)) * weight
            feature_vsl[feature] += float(np.mean(path_vsl)) * weight
        for system, weight in path.systems.items():
            system_public[system] += float(
                np.mean(path_money["public_fiscal"])
            ) * weight
            system_capacity[system] += float(np.mean(path_money["capacity"])) * weight
        for family, weight in path.families.items():
            family_resource[family] = family_resource.get(family, 0.0) + float(
                np.mean(path_resource_total)
            ) * weight
            family_vsl[family] = family_vsl.get(family, 0.0) + float(
                np.mean(path_vsl)
            ) * weight

    direct_resource = (
        money["public_fiscal"]
        + money["capacity"]
        + money["private_household"]
        + money["other_direct_resource"]
    )
    gross_public_resource = money["public_fiscal"] + money["capacity"]
    if not np.allclose(
        gross_public_resource,
        money["public_fiscal"] + money["capacity"],
    ):
        raise AssertionError("aggregate public resource partition failed")
    mortality_neutral_societal = (
        direct_resource + money["productivity_morbidity"] + money["property"]
    )
    mortality_vsl = lives * vsl
    tier_c_zero_vsl = tier_c_zero_lives * vsl
    adverse_only_vsl = adverse_only_lives * vsl
    societal_excluding_vsl = mortality_neutral_societal
    societal_including_vsl = mortality_neutral_societal + mortality_vsl
    tier_c_zero_societal_including_vsl = mortality_neutral_societal + tier_c_zero_vsl
    adverse_only_societal_including_vsl = mortality_neutral_societal + adverse_only_vsl

    fiscal_realization = {
        str(int(share * 100)): summarize(
            np.where(
                money["public_fiscal"] >= 0.0,
                share * money["public_fiscal"],
                money["public_fiscal"],
            )
        )
        for share in (0.0, 0.25, 0.5, 0.75, 1.0)
    }
    projection_rows = []
    for year in range(1, 11):
        adoption = adoption_arrays[str(year)]
        gross_year = societal_excluding_vsl * adoption
        projection_rows.append(
            {
                "year": year,
                "adoption_mean": float(np.mean(adoption)),
                "adoption_p5": float(np.quantile(adoption, 0.05)),
                "adoption_p95": float(np.quantile(adoption, 0.95)),
                "gross_excluding_vsl_mean": float(np.mean(gross_year)),
            }
        )

    arrays = {
        "potential_variable_public_expenditure_avoided": money["public_fiscal"],
        "capacity": money["capacity"],
        "private_household": money["private_household"],
        "other_direct_resource": money["other_direct_resource"],
        "productivity": money["productivity_morbidity"],
        "property": money["property"],
        "direct_resource": direct_resource,
        "direct_process_conservative_benchmark": direct_process_benchmark,
        "qaly_unmonetized": qaly_gain,
        "qaly_valuation_sensitivity": qaly_valuation_sensitivity,
        "call_taker_hours": call_hours,
        "workdays_preserved": workdays,
        "lives": lives,
        "domestic_lives": domestic_lives,
        "traveler_lives": traveler_lives,
        "tier_c_zero_lives": tier_c_zero_lives,
        "adverse_only_lives": adverse_only_lives,
        "mortality_vsl": mortality_vsl,
        "mortality_neutral_societal": mortality_neutral_societal,
        "societal_excluding_vsl": societal_excluding_vsl,
        "societal_including_vsl": societal_including_vsl,
        "tier_c_zero_societal_including_vsl": tier_c_zero_societal_including_vsl,
        "adverse_only_societal_including_vsl": adverse_only_societal_including_vsl,
    }
    summaries = {name: summarize(values) for name, values in arrays.items()}

    sensitivity_drivers = {
        "mortality": lives,
        "VSL": vsl,
        "medical resource cost": drivers["medical_cost"],
        "public operating cost": drivers["public_operating_cost"],
        "productivity": drivers["productivity_value"],
        "property": drivers["property_loss"],
    }
    sensitivity = {
        name: {
            "correlation_excluding_vsl": float(
                np.corrcoef(driver, societal_excluding_vsl)[0, 1]
            ),
            "correlation_including_vsl": float(
                np.corrcoef(driver, societal_including_vsl)[0, 1]
            ),
        }
        for name, driver in sensitivity_drivers.items()
    }

    features = [
        {
            "number": number,
            "feature": FEATURE_NAMES[number],
            "linear_shapley_resource_allocation": feature_resource[number],
            "linear_shapley_mortality_risk_allocation": feature_vsl[number],
            "linear_shapley_total_allocation": feature_resource[number]
            + feature_vsl[number],
        }
        for number in FEATURE_NAMES
    ]
    systems = [
        {
            "system": name,
            "potential_variable_public_expenditure_avoided": system_public[name],
            "capacity_value": system_capacity[name],
            "combined_public_resource": system_public[name] + system_capacity[name],
        }
        for name in SYSTEMS
    ]
    families = [
        {
            "family": name,
            "resource_value": family_resource.get(name, 0.0),
            "mortality_risk_value": family_vsl.get(name, 0.0),
            "total_value": family_resource.get(name, 0.0)
            + family_vsl.get(name, 0.0),
        }
        for name in sorted(set(family_resource) | set(family_vsl))
    ]

    morris = morris_emulator_screening(
        {
            "direct": float(np.mean(direct_resource - money["capacity"])),
            "capacity": float(np.mean(money["capacity"])),
            "productivity": float(np.mean(money["productivity_morbidity"])),
            "property": float(np.mean(money["property"])),
            "mortality": float(np.mean(lives)) * 14.1e6,
        }
    )
    return {
        "scenario": scenario,
        "summaries": summaries,
        "distribution_form": distribution_form,
        "dependence_rho": dependence_rho,
        "copula_family": copula_family,
        "path_means": path_means,
        "features": features,
        "systems": systems,
        "families": families,
        "local_correlation_sensitivity": sensitivity,
        "morris_global_screening": morris,
        "fiscal_realization_sensitivity": fiscal_realization,
        "stochastic_adoption": adoption_rows,
        "named_adoption_scenarios": named_adoption_scenarios(),
        "ten_year_projection": projection_rows,
        "arrays": arrays,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def serializable(result: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in result.items() if key != "arrays"}


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    near_term = simulate("near_term", NEAR_TERM_ECONOMIC_SEED, "pert")
    mature = simulate("mature", MATURE_ECONOMIC_SEED, "pert")
    distribution_form_sensitivity: dict[str, object] = {}
    sensitivity_keys = (
        "direct_process_conservative_benchmark",
        "mortality_neutral_societal",
        "societal_including_vsl",
    )
    for offset, form in enumerate(
        ("pert", "triangular", "uniform", "logit_normal")
    ):
        run = simulate("mature", MATURE_ECONOMIC_SEED + 1000 + offset, form)
        distribution_form_sensitivity[form] = {
            key: run["summaries"][key] for key in sensitivity_keys
        }
    moment_matched_distribution_sensitivity: dict[str, object] = {}
    for offset, form in enumerate(
        (
            "triangular_moment_matched",
            "uniform_moment_matched",
            "logit_normal_moment_matched",
        )
    ):
        run = simulate("mature", MATURE_ECONOMIC_SEED + 1500 + offset, form)
        moment_matched_distribution_sensitivity[form] = {
            key: run["summaries"][key] for key in sensitivity_keys
        }
    dependence_sensitivity: dict[str, object] = {}
    dependence_cases = (
        ("gaussian_rho_0.0", 0.0, "gaussian"),
        ("gaussian_rho_0.5", 0.5, "gaussian"),
        ("gaussian_rho_0.8", 0.8, "gaussian"),
        ("student_t_rho_0.5", 0.5, "t"),
    )
    for offset, (label, rho, family) in enumerate(dependence_cases):
        run = simulate(
            "mature",
            MATURE_ECONOMIC_SEED + 2000 + offset,
            "pert",
            dependence_rho=rho,
            copula_family=family,
        )
        dependence_sensitivity[label] = {
            key: run["summaries"][key] for key in sensitivity_keys
        }
    mortality_config = json.loads(MORTALITY_INPUT_FILE.read_text(encoding="utf-8"))
    traveler_path = next(
        path for path in PATHWAYS if path.name == "U.S. traveler abroad"
    )
    output = {
        "metadata": {
            "release_tag": mortality_config["metadata"]["release_tag"],
            "base_seed": SEED,
            "near_term_economic_seed": NEAR_TERM_ECONOMIC_SEED,
            "mature_economic_seed": MATURE_ECONOMIC_SEED,
            "draws_per_scenario": DRAWS,
            "dollar_year": 2026,
            "model_definition": mortality_config["metadata"]["interpretation"],
            "primary_accounting": "QALYs are reported unmonetized and excluded from the primary monetary total; mortality production is excluded; VSL is a separate societal mortality-risk valuation.",
            "direct_process_benchmark_rule": "Mortality, monetized QALYs, productivity, and property are zero. Positive direct-resource changes are multiplied by pathway evidence weights; adverse direct-resource changes are retained fully. This is a restricted scenario, not a demonstrated mathematical floor.",
            "public_fiscal_label": "potential variable public expenditure avoided before realization; realization percentages apply only to positive avoided expenditure, while modeled added public costs remain fully counted",
            "public_capacity_partition": "Each primitive public resource element is assigned once: expenditure contains only potentially expenditure-changing units, capacity contains only residual operational value excluded from expenditure, and gross public resource equals expenditure plus residual capacity. Runtime assertions enforce the reconciliation identity.",
            "receiver_cost_rule": "G_jp is the gross paired delta before receiving-system cost, R_jp is the separately drawn receiving-system offset, D_jp=G_jp-R_jp is the net paired delta, and B_jp=A_j D_jp is aggregated once.",
            "feature_allocation": "Linear Shapley reporting allocation under the prespecified additive pathway feature game; not a causal effect.",
            "adoption_model": "Stochastic logistic rollout fraction relative to the mature scenario, with uncertain slope, midpoint, and attainable asymptote.",
            "sensitivity": "Local correlation diagnostics, Morris elementary-effects screening of a documented median-input emulator, and low/medium/high Gaussian plus Student-t copula dependence sensitivities within the mortality/implementation and economic-driver blocks.",
            "copula_algorithm": "Economic-driver marginals use a separate equicorrelated Gaussian or Student-t(df=4) block with Z_j=sqrt(rho)Z_0+sqrt(1-rho)epsilon_j; uniforms are obtained from the matching CDF. Mortality arrays are imported from a separately generated mortality block, so no unestimated cross-block copula is imposed beyond the shared affected-episode and mortality arrays.",
            "distribution_form_robustness": "Endpoint-based beta-PERT, triangular, uniform/bounded, and bounded logit-normal or normal marginals are rerun, followed by approximately PERT-moment-matched versions of the three alternatives.",
            "near_term_scaling": "Near-term pathway deployment scales are separate from restricted-scenario weights; the two concepts are never represented by one variable.",
            "near_term_pathway_scale": NEAR_TERM_PATHWAY_SCALE,
            "pathway_evidence_weights": {
                path.name: path.evidence_weight for path in PATHWAYS
            },
            "receiver_resource_cost_inputs_per_affected_episode": RECEIVER_RESOURCE_COSTS,
            "traveler_abroad_mortality_module": {
                "exposure_departures_low_mode_high": list(
                    TRAVELER_MORTALITY_INPUTS["exposure_departures"]
                ),
                "destination_groups": [
                    {
                        "name": name,
                        "trip_share": share,
                        "unfamiliar_or_wrong_number_probability": list(unfamiliarity),
                        "relative_economic_consequence": list(consequence),
                    }
                    for name, share, unfamiliarity, consequence in TRAVEL_REGIONS
                ],
                "base_relevance_low_mode_high": list(traveler_path.relevance),
                "successful_use_low_mode_high": list(traveler_path.success),
                "unique_episode_factor_low_mode_high": list(traveler_path.overlap),
                "beneficial_activation_probability_low_mode_high": list(
                    TRAVELER_MORTALITY_INPUTS[
                        "beneficial_activation_probability"
                    ]
                ),
                "adverse_activation_probability_low_mode_high": list(
                    TRAVELER_MORTALITY_INPUTS["adverse_activation_probability"]
                ),
                "beneficial_arr_low_mode_high": list(traveler_path.benefit_arr),
                "adverse_arr_low_mode_high": list(traveler_path.harm_arr),
                "beneficial_effect_multiplier_low_mode_high": list(
                    TRAVELER_MORTALITY_INPUTS["beneficial_effect_multiplier"]
                ),
                "adverse_effect_multiplier_low_mode_high": list(
                    TRAVELER_MORTALITY_INPUTS["adverse_effect_multiplier"]
                ),
                "implementation_driver_weights": traveler_path.driver_weights,
                "equation": "U=sum_r w_r u_r; A=min(I*d*r*U*s*M,I); Z_plus~Bernoulli(p_plus), Z_minus~Bernoulli(p_minus); L=A*(Z_plus*H_plus*Delta_plus-Z_minus*H_minus*Delta_minus). Regional consequence Q=(sum_r w_r u_r q_r)/max(U,1e-9) scales economic deltas and receiving costs only.",
                "near_term_treatment": "traveler mortality set to zero",
            },
            "adoption_parameter_inputs": {
                "asymptote": [0.55, 0.82, 0.97],
                "midpoint_year": [3.5, 5.5, 8.0],
                "slope": [0.45, 0.8, 1.25],
            },
            "call_mix": CALL_MIX,
            "property_mix": PROPERTY_MIX,
        },
        "near_term": serializable(near_term),
        "mature": serializable(mature),
        "distribution_form_sensitivity": distribution_form_sensitivity,
        "moment_matched_distribution_sensitivity": moment_matched_distribution_sensitivity,
        "dependence_sensitivity": dependence_sensitivity,
    }
    RESULT_FILE.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    write_csv(RESULTS_DIR / "economic-feature-breakdown.csv", mature["features"])
    write_csv(RESULTS_DIR / "economic-system-breakdown.csv", mature["systems"])
    write_csv(RESULTS_DIR / "economic-incident-breakdown.csv", mature["families"])
    write_csv(
        RESULTS_DIR / "economic-pathway-breakdown.csv",
        [{"pathway": name, **values} for name, values in mature["path_means"].items()],
    )
    write_csv(
        RESULTS_DIR / "economic-sensitivity.csv",
        [
            {"assumption": name, **values}
            for name, values in mature["local_correlation_sensitivity"].items()
        ],
    )
    write_csv(
        RESULTS_DIR / "economic-morris-screening.csv",
        mature["morris_global_screening"],
    )
    write_csv(
        RESULTS_DIR / "economic-adoption-projection.csv",
        mature["ten_year_projection"],
    )

    for label, result in (("near_term", near_term), ("mature", mature)):
        print(f"[{label}]")
        for key in (
            "potential_variable_public_expenditure_avoided",
            "capacity",
            "direct_process_conservative_benchmark",
            "mortality_neutral_societal",
            "societal_excluding_vsl",
            "societal_including_vsl",
        ):
            summary = result["summaries"][key]
            print(
                f"{key}: mean={summary['mean']:.3f} median={summary['median']:.3f} "
                f"p5={summary['p5']:.3f} p95={summary['p95']:.3f}"
            )


if __name__ == "__main__":
    main()