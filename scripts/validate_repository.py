#!/usr/bin/env python3
"""Validate the public PEC research repository and reproducible release."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RELEASE_TAG = "pec-prospective-2026-08-09-r9"

JSON_FILES = (
    "config/mortality-model-inputs.json",
    "results/mortality-near-term-results.json",
    "results/mortality-mature-results.json",
    "results/economic-results.json",
)

GENERATED_FILES = (
    "results/mortality-near-term-results.json",
    "results/mortality-mature-results.json",
    "results/economic-results.json",
    "results/economic-feature-breakdown.csv",
    "results/economic-incident-breakdown.csv",
    "results/economic-pathway-breakdown.csv",
    "results/economic-sensitivity.csv",
    "results/economic-system-breakdown.csv",
    "results/economic-morris-screening.csv",
    "results/economic-adoption-projection.csv",
)

RERUN_INPUTS = (
    "config/mortality-model-inputs.json",
    "pec_model/__init__.py",
    "pec_model/common.py",
    "pec_model/mortality_near_term.py",
    "pec_model/mortality_mature.py",
    "pec_model/economic_inputs.py",
    "pec_model/economic.py",
)

VALIDATION_READINESS_FILES = (
    "docs/reproducibility.md",
    "scripts/validate_deployment_export.py",
    "scripts/test_deployment_validator.py",
    "validation/deployment-analysis-plan.md",
    "validation/deployment-data-dictionary.csv",
)

REPOSITORY_FILES = (
    ".gitignore",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "CITATION.cff",
    "requirements.txt",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/validate.yml",
    ".github/ISSUE_TEMPLATE/implementation-bug.yml",
    ".github/ISSUE_TEMPLATE/model-assumption.yml",
    "docs/software-environment.txt",
    "validation/expert-elicitation-protocol.md",
    "scripts/validate_repository.py",
    "scripts/scan_paper_text.py",
    "source-materials/README.md",
    "source-materials/pec-functions-transcription.md",
    "source-materials/pec-statistical-lives-inputs-transcription.md",
    "reviews/README.md",
    "reviews/technical-review-2026-08-08-004134.tex",
    "reviews/technical-review-2026-08-08-034257.tex",
    "reviews/technical-review-2026-08-08-153439.tex",
    "reviews/technical-review-2026-08-08-173317.tex",
    "reviews/technical-review-2026-08-08-185512.tex",
    "reviews/technical-review-response-2026-08-08.md",
)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    counts = Counter(key for key, _ in pairs)
    duplicates = [key for key, count in counts.items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate JSON keys: {duplicates}")
    return dict(pairs)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_structure() -> None:
    for filename in JSON_FILES:
        load_json(ROOT / filename)

    for filename in VALIDATION_READINESS_FILES:
        if not (ROOT / filename).is_file():
            raise AssertionError(f"validation-readiness file is missing: {filename}")
    for filename in REPOSITORY_FILES:
        if not (ROOT / filename).is_file():
            raise AssertionError(f"public repository file is missing: {filename}")
    subprocess.run(
        ["python", "scripts/validate_deployment_export.py", "--schema-only"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["python", "scripts/test_deployment_validator.py"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    ignore_lines = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if "*" in ignore_lines:
        raise AssertionError("blanket repository ignore rule would hide research files")

    config = load_json(ROOT / "config/mortality-model-inputs.json")
    if config["metadata"]["release_tag"] != RELEASE_TAG:
        raise AssertionError("mortality input release tag mismatch")
    if "resident-year" in config["future_mature_scenario"]["master_unit"]:
        raise AssertionError("resident-year remains the mature master unit")
    if "unique emergency episode" not in config["future_mature_scenario"]["master_unit"]:
        raise AssertionError("unique emergency episode master unit is missing")
    paths = config["future_mature_scenario"]["pathways"]
    if len(paths) != 9 or len({path["name"] for path in paths}) != 9:
        raise AssertionError("expected nine unique mature mortality pathways")
    for path in paths:
        for key in (
            "unique_episode_factor",
            "beneficial_effect_nonzero_probability",
            "adverse_effect_nonzero_probability",
        ):
            values = path[key]
            if len(values) != 3 or not values[0] <= values[1] <= values[2]:
                raise AssertionError(f"invalid {key} for {path['name']}")
    near_inputs = config["near_term_prospective_scenario"]
    if not abs(sum(near_inputs["cpr_category_weights"]) - 1.0) < 1e-12:
        raise AssertionError("CPR category weights do not sum to one")
    survival = near_inputs["cpr_category_survival_rates"]
    if any(a < b for a, b in zip(survival, survival[1:])):
        raise AssertionError("CPR category survival is not nonincreasing")
    if near_inputs["causal_fraction_of_988_association"][
        "slab_low_mode_high"
    ][0] != 0.0:
        raise AssertionError("988 causal slab does not include zero")
    if near_inputs["language_minutes_recovered"][2] > 2.0:
        raise AssertionError("one-category CPR transition cap can bind")
    if "cpr_timing_association_causal_attenuation" not in near_inputs:
        raise AssertionError("CPR association attenuation is missing")
    if near_inputs["access_mortality_primary"] != "zero":
        raise AssertionError("access mortality is not zero in the primary case")
    if "prospective_988_affected_episode_model" not in near_inputs:
        raise AssertionError("near-term 988 affected-episode model is missing")
    common_keys = set(config["future_mature_scenario"]["common_multipliers"])
    if not {
        "national_reach_index",
        "user_activation_index",
        "technical_reliability_index",
        "receiver_compatibility_index",
    } <= common_keys:
        raise AssertionError("nonserial implementation indices are incomplete")

    near = load_json(ROOT / "results/mortality-near-term-results.json")
    near_summary = near["primary_pert"]["summaries"]["primary_gross_benefit"]
    if near_summary["probability_zero"] <= 0.0:
        raise AssertionError("near-term spike-and-slab model has no zero mass")
    if near["metadata"]["access_mortality_treatment"].startswith("zero") is False:
        raise AssertionError("near-term access mortality is not zero in primary")
    if near["primary_pert"]["summaries"]["988_affected_episodes"]["mean"] <= 0.0:
        raise AssertionError("near-term 988 affected-episode array is missing")
    if "full_988_sign_reversal_stress" not in near["primary_pert"]["summaries"]:
        raise AssertionError("988 sign-reversal stress is missing")
    if "cpr_causal_attenuation" not in near["primary_pert"]["summaries"]:
        raise AssertionError("CPR causal attenuation output is missing")
    if "passed unchanged to the economic model" not in near["metadata"]["988_pairing"]:
        raise AssertionError("near-term 988 mortality/economic pairing is not explicit")

    mature = load_json(ROOT / "results/mortality-mature-results.json")
    if mature["metadata"]["release_tag"] != RELEASE_TAG:
        raise AssertionError("mature result release tag mismatch")
    if "unique emergency episode" not in mature["metadata"]["master_unit"]:
        raise AssertionError("mature output master unit is not unique episodes")
    if "conditional future-deployment predictive interval" not in mature["metadata"]["predictive_interval_label"]:
        raise AssertionError("predictive interval label is incomplete")
    primary_mortality = mature["primary_pert_medium_dependence"]
    if not 0.40 <= primary_mortality["common_multiplier_dependence"][
        "benefit_harm_multiplier_correlation"
    ] <= 0.60:
        raise AssertionError("benefit/harm multiplier dependence is not coupled")
    path_summaries = primary_mortality["pathways"].values()
    path_net_mean = sum(path["net_lives"]["mean"] for path in path_summaries)
    if abs(
        path_net_mean
        - primary_mortality["summaries"]["all_pathway_parameter"]["mean"]
    ) > 1e-6:
        raise AssertionError("mortality pathway means do not sum to the total")
    path_episode_mean = sum(
        path["unique_relevant_episodes"]["mean"]
        for path in primary_mortality["pathways"].values()
    )
    if abs(
        path_episode_mean
        - primary_mortality["summaries"]["unique_relevant_episode_total"]["mean"]
    ) > 1e-5:
        raise AssertionError("unique-episode pathway means do not sum")
    if set(mature["distribution_form_sensitivity"]) != {
        "pert",
        "triangular",
        "uniform",
        "logit_normal",
    }:
        raise AssertionError("mortality distribution-form sensitivity is incomplete")
    if set(mature["moment_matched_distribution_sensitivity"]) != {
        "triangular_moment_matched",
        "uniform_moment_matched",
        "logit_normal_moment_matched",
    }:
        raise AssertionError("mortality moment-matched sensitivity is incomplete")
    if mature["metadata"].get("student_t_degrees_of_freedom") != 4:
        raise AssertionError("mortality Student-t degrees of freedom are not explicit")
    predictive_algorithm = mature["metadata"].get("predictive_count_algorithm", "")
    for token in ("Poisson", "Multinomial", "Binomial", "benefit/harm/none"):
        if token not in predictive_algorithm:
            raise AssertionError(f"mortality predictive-count algorithm omits {token}")
    if "shape 8" not in mature["metadata"].get(
        "marginal_distribution_algorithm", ""
    ):
        raise AssertionError("mortality PERT shape is not explicit")
    if set(mature["copula_family_sensitivity"]) != {"gaussian", "t"}:
        raise AssertionError("mortality copula-family sensitivity is incomplete")
    if "low_unique_episode_factor_stress" not in mature:
        raise AssertionError("low unique-episode-factor stress is missing")

    economic = load_json(ROOT / "results/economic-results.json")
    if economic["metadata"]["release_tag"] != RELEASE_TAG:
        raise AssertionError("economic result release tag mismatch")
    required = {
        "direct_process_conservative_benchmark",
    }
    if required - set(economic["mature"]["summaries"]):
        raise AssertionError("economic conservative output is incomplete")
    if economic["metadata"]["primary_accounting"].find("QALYs are reported unmonetized") < 0:
        raise AssertionError("primary QALY accounting is not explicit")
    if "adverse direct-resource changes are retained fully" not in economic[
        "metadata"
    ]["direct_process_benchmark_rule"]:
        raise AssertionError("restricted direct-process scenario discounts adverse costs")
    if "residual operational value excluded from expenditure" not in economic[
        "metadata"
    ]["public_capacity_partition"]:
        raise AssertionError("public expenditure/capacity partition is not explicit")
    if len(economic["metadata"]["near_term_pathway_scale"]) != 10:
        raise AssertionError("near-term pathway scales are incomplete")
    if len(economic["metadata"]["pathway_evidence_weights"]) != 10:
        raise AssertionError("economic evidence weights are incomplete")
    if len(economic["metadata"]["receiver_resource_cost_inputs_per_affected_episode"]) != 10:
        raise AssertionError("receiver-cost inputs are incomplete")
    if "D_jp=G_jp-R_jp" not in economic["metadata"]["receiver_cost_rule"]:
        raise AssertionError("receiver gross/net accounting rule is incomplete")
    traveler = economic["metadata"].get("traveler_abroad_mortality_module")
    if traveler is None:
        raise AssertionError("traveler-abroad mortality module metadata is missing")
    if abs(
        sum(group["trip_share"] for group in traveler["destination_groups"])
        - 1.0
    ) > 1e-12:
        raise AssertionError("traveler destination shares do not sum to one")
    for key in (
        "exposure_departures_low_mode_high",
        "beneficial_activation_probability_low_mode_high",
        "adverse_activation_probability_low_mode_high",
        "beneficial_arr_low_mode_high",
        "adverse_arr_low_mode_high",
        "beneficial_effect_multiplier_low_mode_high",
        "adverse_effect_multiplier_low_mode_high",
        "equation",
    ):
        if key not in traveler:
            raise AssertionError(f"traveler mortality metadata missing: {key}")
    if set(economic["distribution_form_sensitivity"]) != {
        "pert",
        "triangular",
        "uniform",
        "logit_normal",
    }:
        raise AssertionError("economic distribution-form sensitivity is incomplete")
    if set(economic["moment_matched_distribution_sensitivity"]) != {
        "triangular_moment_matched",
        "uniform_moment_matched",
        "logit_normal_moment_matched",
    }:
        raise AssertionError("economic moment-matched sensitivity is incomplete")
    if set(economic["dependence_sensitivity"]) != {
        "gaussian_rho_0.0",
        "gaussian_rho_0.5",
        "gaussian_rho_0.8",
        "student_t_rho_0.5",
    }:
        raise AssertionError("economic dependence sensitivity is incomplete")

    mature_economic = economic["mature"]
    summaries = mature_economic["summaries"]
    if not (
        summaries["traveler_lives"]["p5"] < 0.0
        and summaries["traveler_lives"]["p95"] > 0.0
    ):
        raise AssertionError("traveler mortality is not genuinely signed")
    path_rows = mature_economic["path_means"].values()
    if abs(
        sum(row["resource_total_excluding_vsl"] for row in path_rows)
        - summaries["mortality_neutral_societal"]["mean"]
    ) > 1e-3:
        raise AssertionError("economic pathway resources do not sum to total")
    if abs(
        sum(row["lives"] for row in mature_economic["path_means"].values())
        - summaries["lives"]["mean"]
    ) > 1e-6:
        raise AssertionError("economic pathway lives do not sum to total")
    for name, row in mature_economic["path_means"].items():
        for key in (
            "receiver_public_cost_per_changed_episode_mean",
            "receiver_capacity_cost_per_changed_episode_mean",
            "receiver_private_cost_per_changed_episode_mean",
            "receiver_other_direct_cost_per_changed_episode_mean",
            "receiver_total_direct_cost_per_changed_episode_mean",
        ):
            if key not in row:
                raise AssertionError(f"receiver-cost category missing for {name}")
    if summaries["direct_process_conservative_benchmark"]["mean"] > summaries["direct_resource"]["mean"]:
        raise AssertionError("restricted benchmark exceeds full direct-resource value")
    for name, row in mature_economic["path_means"].items():
        if abs(
            row["gross_public_resource_value"]
            - row["potential_variable_public_expenditure_avoided"]
            - row["capacity_value"]
        ) > 1e-6:
            raise AssertionError(f"public resource partition fails for {name}")
    mortality_parameter = primary_mortality["summaries"]["all_pathway_parameter"]
    for statistic in ("mean", "median", "p5", "p95"):
        if abs(
            summaries["domestic_lives"][statistic]
            - mortality_parameter[statistic]
        ) > 1e-9:
            raise AssertionError(
                "economic domestic mortality does not match mortality parameter draws"
            )
    if abs(
        sum(
            row["linear_shapley_resource_allocation"]
            for row in mature_economic["features"]
        )
        - summaries["mortality_neutral_societal"]["mean"]
    ) > 1e-3:
        raise AssertionError("feature resource allocation does not conserve value")
    if not all(
        earlier["mean"] <= later["mean"]
        for earlier, later in zip(
            mature_economic["stochastic_adoption"],
            mature_economic["stochastic_adoption"][1:],
        )
    ):
        raise AssertionError("stochastic adoption is not monotone by year")


def validate_manifest() -> None:
    manifest = ROOT / "release-manifest.sha256"
    if not manifest.exists():
        raise AssertionError("release-manifest.sha256 is missing")
    listed: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        relative = relative.lstrip("*")
        listed.add(relative)
        path = ROOT / relative
        if not path.is_file():
            raise AssertionError(f"manifest file missing: {relative}")
        if sha256(path) != expected:
            raise AssertionError(f"manifest hash mismatch: {relative}")
    for required in (
        RERUN_INPUTS
        + GENERATED_FILES
        + VALIDATION_READINESS_FILES
        + REPOSITORY_FILES
    ):
        if required not in listed:
            raise AssertionError(f"manifest does not list required file: {required}")


def clean_rerun() -> None:
    with tempfile.TemporaryDirectory(prefix="pec-prospective-release-") as tmp:
        tmpdir = Path(tmp)
        def copy(relative: str) -> None:
            destination = tmpdir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

        for filename in RERUN_INPUTS:
            copy(filename)
        for module in (
            "pec_model.mortality_near_term",
            "pec_model.mortality_mature",
            "pec_model.economic",
        ):
            subprocess.run(
                ["python", "-m", module],
                cwd=tmpdir,
                check=True,
                stdout=subprocess.DEVNULL,
            )
        for filename in GENERATED_FILES:
            if (tmpdir / filename).read_bytes() != (ROOT / filename).read_bytes():
                raise AssertionError(f"clean rerun differs: {filename}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args()

    validate_structure()
    validate_manifest()
    if args.rerun:
        clean_rerun()
    print("[OK] PEC prospective release validation passed.")


if __name__ == "__main__":
    main()