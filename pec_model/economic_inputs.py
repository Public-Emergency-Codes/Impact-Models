"""PEC annual U.S. economic-value simulation.

This model is a prospective pathway-level paired-counterfactual planning
analysis.  Each pathway samples a net expected difference between baseline and
PEC resource use for a changed incident; it is not an incident-level
microsimulation of individual severity, payer, and condition records.
Domestic mortality draws are imported directly from the corrected companion
mortality simulations; the traveler-abroad mortality pathway remains separate.
Potential variable public expenditure avoided, capacity, private costs,
productivity, property,
morbidity, and mortality-risk value remain separate to avoid hidden double
counting.

All monetary values are June 2026 U.S. dollars.  Numerical assumptions are
documented in this module and in ``config/mortality-model-inputs.json``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SEED = 20260808
NEAR_TERM_ECONOMIC_SEED = 20260909
MATURE_ECONOMIC_SEED = 20261010
DRAWS = 60_000
PERT_SHAPE = 8.0
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MORTALITY_INPUT_FILE = PROJECT_ROOT / "config" / "mortality-model-inputs.json"

MONEY_CATEGORIES = (
    "public_fiscal",
    "capacity",
    "private_household",
    "other_direct_resource",
    "productivity_morbidity",
    "property",
)

RECEIVER_RESOURCE_COSTS = {
    "988/crisis connection": {
        "public_fiscal": (25.0, 90.0, 260.0),
        "capacity": (5.0, 20.0, 80.0),
        "private_household": (5.0, 20.0, 100.0),
        "other_direct_resource": (5.0, 25.0, 120.0),
    },
    "211 social/health referral": {
        "public_fiscal": (5.0, 35.0, 140.0),
        "capacity": (2.0, 10.0, 40.0),
        "private_household": (0.0, 10.0, 60.0),
        "other_direct_resource": (2.0, 10.0, 50.0),
    },
    "911 diversion/capacity": {
        "public_fiscal": (0.10, 0.60, 2.50),
        "capacity": (0.10, 0.50, 2.00),
        "private_household": (0.0, 0.10, 0.50),
        "other_direct_resource": (0.0, 0.10, 0.50),
    },
    "earlier correct 911 access": {
        "public_fiscal": (0.0, 8.0, 35.0),
        "capacity": (0.0, 3.0, 15.0),
        "private_household": (0.0, 5.0, 30.0),
        "other_direct_resource": (0.0, 2.0, 15.0),
    },
    "cardiac-arrest rapid assistance": {
        "public_fiscal": (0.0, 15.0, 80.0),
        "capacity": (0.0, 5.0, 25.0),
        "private_household": (0.0, 15.0, 100.0),
        "other_direct_resource": (0.0, 5.0, 40.0),
    },
    "silent/language access": {
        "public_fiscal": (1.0, 8.0, 35.0),
        "capacity": (1.0, 4.0, 15.0),
        "private_household": (0.0, 4.0, 20.0),
        "other_direct_resource": (0.0, 2.0, 12.0),
    },
    "location/responder access": {
        "public_fiscal": (0.0, 5.0, 25.0),
        "capacity": (0.0, 3.0, 15.0),
        "private_household": (0.0, 3.0, 20.0),
        "other_direct_resource": (0.0, 2.0, 12.0),
    },
    "medical data/photo/video": {
        "public_fiscal": (2.0, 18.0, 80.0),
        "capacity": (1.0, 6.0, 30.0),
        "private_household": (1.0, 10.0, 60.0),
        "other_direct_resource": (1.0, 6.0, 30.0),
    },
    "contacts/passive monitoring": {
        "public_fiscal": (50.0, 300.0, 1500.0),
        "capacity": (10.0, 50.0, 250.0),
        "private_household": (10.0, 100.0, 800.0),
        "other_direct_resource": (10.0, 50.0, 300.0),
    },
    "U.S. traveler abroad": {
        "public_fiscal": (0.0, 0.0, 0.0),
        "capacity": (0.0, 0.0, 0.0),
        "private_household": (0.0, 50.0, 500.0),
        "other_direct_resource": (0.0, 20.0, 200.0),
    },
}

MEDICAL_RESOURCE_SHARES = {
    "988/crisis connection": 0.55,
    "211 social/health referral": 0.35,
    "911 diversion/capacity": 0.05,
    "earlier correct 911 access": 0.80,
    "cardiac-arrest rapid assistance": 0.90,
    "silent/language access": 0.75,
    "location/responder access": 0.70,
    "medical data/photo/video": 0.75,
    "contacts/passive monitoring": 0.85,
    "U.S. traveler abroad": 0.55,
}

DEPLOYMENT_COST_INPUTS = {
    "one_time_capital_and_integration": (1.0e9, 4.0e9, 12.0e9),
    "annual_operations_training_security": (0.30e9, 1.00e9, 3.00e9),
    "annual_replacement_and_upgrade": (0.05e9, 0.30e9, 0.90e9),
    "public_financing_share": (0.35, 0.65, 0.90),
    "fixed_predeployment_capital_share": (0.25, 0.40, 0.60),
    "fixed_recurring_operations_share": (0.20, 0.35, 0.55),
    "fixed_recurring_replacement_share": (0.20, 0.50, 0.80),
    "near_term_deployment_maturity": (0.15, 0.30, 0.50),
}

# Scope represented only inside the aggregate pre-procurement envelopes above.
# No line-item allocation is claimed until engineering estimates or bids exist.
DEPLOYMENT_COST_SCOPE = (
    "consumer-platform and operating-system integration",
    "PSAP software, hardware, interfaces, and testing",
    "cloud, network, storage, observability, and continuity",
    "implementation staffing, training, and change management",
    "cybersecurity, privacy, identity, and incident response",
    "legal, accessibility, compliance, insurance, and liability",
    "help desk, maintenance, vendor support, and quality assurance",
    "public education, localization, translation, and outreach",
    "replacement, upgrades, interoperability certification, and recertification",
)

NEAR_TERM_PATHWAY_SCALE = {
    "988/crisis connection": 1.0,
    "211 social/health referral": 0.35,
    "911 diversion/capacity": 0.35,
    "earlier correct 911 access": 0.25,
    "cardiac-arrest rapid assistance": 0.25,
    "silent/language access": 1.0,
    "location/responder access": 1.0,
    "medical data/photo/video": 0.25,
    "contacts/passive monitoring": 0.10,
    "U.S. traveler abroad": 0.15,
}

SYSTEMS = (
    "911/PSAP",
    "EMS",
    "fire",
    "police",
    "behavioral health",
    "Medicare",
    "Medicaid",
    "public hospitals",
    "long-term care/disability",
    "other public",
)

# Prospective destination mix for U.S. citizen departures.  The 98.5/105/115
# million exposure range is anchored by NTTO's 98.5 million 2023 and 107.7
# million 2024 departure totals.  North America is anchored near NTTO's roughly
# 49% 2025 share; the overseas split is grouped for modeling because national
# incident and emergency-number-error data are not available country by
# country.  Each tuple is region, trip share, unfamiliar/wrong-number
# probability, and relative consequence severity.
TRAVEL_REGIONS = (
    ("Mexico", 0.32, (0.08, 0.15, 0.30), (0.70, 0.90, 1.20)),
    ("Canada", 0.17, (0.00, 0.02, 0.08), (0.60, 0.75, 1.00)),
    ("Europe", 0.20, (0.12, 0.25, 0.45), (0.80, 1.00, 1.30)),
    ("Caribbean/Latin America", 0.13, (0.18, 0.35, 0.60), (0.85, 1.10, 1.50)),
    ("Asia", 0.10, (0.20, 0.40, 0.65), (0.90, 1.20, 1.65)),
    ("Other", 0.08, (0.22, 0.45, 0.72), (1.00, 1.30, 1.80)),
)

TRAVELER_MORTALITY_INPUTS = {
    "exposure_departures": (98.5e6, 105.0e6, 115.0e6),
    "beneficial_activation_probability": (0.10, 0.30, 0.60),
    "adverse_activation_probability": (0.05, 0.20, 0.45),
    "beneficial_effect_multiplier": (0.55, 1.00, 1.55),
    "adverse_effect_multiplier": (0.55, 1.00, 1.55),
}

# Interpretive decomposition of the 911 workload pathway.  The simulation
# values total minutes, so these shares describe the central operational mix
# without pretending that national subtype counts are currently measured.
CALL_MIX = {
    "duplicate_or_status": 0.45,
    "non_emergency_or_wrong_service": 0.25,
    "transfer_or_redirection": 0.20,
    "callback_or_abandonment_related": 0.10,
}

# Composition used to interpret the property bundle.  The simulation values a
# single net property delta per affected incident to avoid adding overlapping
# structure, contents, vehicle, infrastructure, and interruption losses.
PROPERTY_MIX = {
    "residential_structure_and_contents": 0.60,
    "commercial_structure_and_contents": 0.20,
    "vehicle_and_infrastructure": 0.10,
    "business_interruption": 0.10,
}

FEATURE_NAMES = {
    1: "Public emergency-number education",
    2: "School-based education",
    3: "County/local-government education",
    4: "Alternative-number reminder",
    5: "Helplines tab",
    6: "Direct 988 access",
    7: "Direct 211 access",
    8: "Direct local non-emergency access",
    9: "Global emergency numbers",
    10: "Silent emergency text access",
    11: "Language preference notification",
    12: "Two-way emergency text translation",
    13: "Enhanced location verification",
    14: "Saved address/access information",
    15: "Emergency medical profile",
    16: "Emergency caller photo",
    17: "Live emergency video",
    18: "Emergency contact alerts",
    19: "Secondary-call containment",
    20: "Safety check-ins/passive monitoring",
    21: "Zero-setup/low-friction design",
    22: "App/platform integration",
    23: "Emergency-system compatibility",
}


@dataclass(frozen=True)
class Pathway:
    name: str
    opportunities: float
    relevance: tuple[float, float, float]
    success: tuple[float, float, float]
    benefit_arr: tuple[float, float, float]
    harm_arr: tuple[float, float, float]
    overlap: tuple[float, float, float]
    evidence_weight: float
    economics: dict[str, tuple[float, float, float]]
    qaly: tuple[float, float, float]
    call_minutes: tuple[float, float, float]
    workdays: tuple[float, float, float]
    driver_weights: dict[str, float]
    features: dict[int, float]
    systems: dict[str, float]
    families: dict[str, float]


def econ(
    public: tuple[float, float, float],
    capacity: tuple[float, float, float],
    private: tuple[float, float, float],
    other: tuple[float, float, float],
    productivity: tuple[float, float, float],
    property_loss: tuple[float, float, float],
) -> dict[str, tuple[float, float, float]]:
    return {
        "public_fiscal": public,
        "capacity": capacity,
        "private_household": private,
        "other_direct_resource": other,
        "productivity_morbidity": productivity,
        "property": property_loss,
    }


PATHWAYS = (
    Pathway(
        "988/crisis connection",
        8.0e6,
        (0.03, 0.10, 0.25),
        (0.15, 0.45, 0.75),
        (5e-5, 3e-4, 1.2e-3),
        (1e-6, 5e-6, 2e-5),
        (0.80, 0.90, 0.98),
        1.00,
        econ((60, 180, 550), (15, 55, 150), (40, 150, 500),
             (10, 35, 120), (60, 260, 1000), (0, 0, 0)),
        (0.00005, 0.00050, 0.0030),
        (1.0, 2.4, 5.0),
        (0.15, 0.80, 3.0),
        {"adoption": 0.30, "education": 0.25, "routing_988": 0.30,
         "psap_compatibility": 0.15},
        {1: .10, 2: .05, 3: .05, 4: .15, 5: .10, 6: .20,
         21: .10, 22: .15, 23: .10},
        {"911/PSAP": .10, "EMS": .12, "police": .12,
         "behavioral health": .15, "Medicare": .12, "Medicaid": .20,
         "public hospitals": .12, "other public": .07},
        {"behavioral health/suicide": .90, "toxicologic/substance use": .10},
    ),
    Pathway(
        "211 social/health referral",
        19.0e6,
        (0.005, 0.03, 0.10),
        (0.10, 0.35, 0.65),
        (5e-6, 5e-5, 3e-4),
        (5e-7, 2e-6, 1e-5),
        (0.75, 0.85, 0.95),
        0.60,
        econ((-10, 70, 350), (5, 18, 60), (-5, 85, 500),
             (0, 20, 100), (20, 180, 1000), (0, 0, 0)),
        (-0.00005, 0.00025, 0.0020),
        (0.05, 0.30, 1.0),
        (0.05, 0.55, 3.0),
        {"adoption": .30, "education": .20, "diversion": .20,
         "psap_compatibility": .10, "routing_211": .20},
        {1: .10, 2: .05, 3: .05, 4: .12, 5: .10, 7: .23,
         21: .10, 22: .15, 23: .10},
        {"911/PSAP": .08, "EMS": .05, "behavioral health": .07,
         "Medicare": .15, "Medicaid": .30, "public hospitals": .15,
         "long-term care/disability": .08, "other public": .12},
        {"social/resource emergencies": .75, "environmental exposure": .10,
         "chronic/medication access": .10, "caregiver crisis": .05},
    ),
    Pathway(
        "911 diversion/capacity",
        240.0e6,
        (0.01, 0.05, 0.12),
        (0.15, 0.45, 0.75),
        (1e-7, 1e-6, 8e-6),
        (2e-8, 1e-7, 5e-7),
        (0.60, 0.75, 0.90),
        0.70,
        econ((0.10, 0.90, 3.50), (2.50, 5.00, 12.0), (0, .10, 1.0),
             (0, .10, 1.0), (0, .40, 3.0), (0, 0, 0)),
        (0, 0, 0),
        (3.0, 6.0, 12.0),
        (0, 0.01, 0.10),
        {"adoption": .25, "education": .10, "diversion": .35,
         "psap_compatibility": .20, "secondary_call": .10},
        {4: .25, 8: .30, 19: .20, 21: .05, 22: .10, 23: .10},
        {"911/PSAP": .70, "EMS": .10, "fire": .08, "police": .12},
        {"police/public safety": .45, "medical/EMS": .30,
         "fire": .10, "behavioral health/suicide": .15},
    ),
    Pathway(
        "earlier correct 911 access",
        36.367261e6,
        (0.01, 0.04, 0.10),
        (0.15, 0.45, 0.75),
        (5e-5, 5e-4, 2e-3),
        (5e-6, 2e-5, 1e-4),
        (0.50, 0.65, 0.80),
        0.15,
        econ((-50, 140, 1000), (5, 35, 150), (-40, 120, 800),
             (-10, 30, 200), (-100, 420, 4000), (0, 0, 0)),
        (-0.0002, 0.0012, 0.010),
        (0.05, 0.50, 2.0),
        (-0.20, 1.20, 10.0),
        {"adoption": .30, "education": .35, "psap_compatibility": .20,
         "early_activation": .15},
        {1: .20, 2: .10, 3: .10, 5: .10, 21: .15, 22: .20, 23: .15},
        {"EMS": .08, "Medicare": .25, "Medicaid": .18,
         "public hospitals": .25, "long-term care/disability": .18,
         "other public": .06},
        {"cardiovascular": .22, "stroke/neurologic": .18,
         "respiratory": .14, "trauma/hemorrhage": .14,
         "sepsis/infection": .10, "toxicologic/endocrine": .10,
         "obstetric/neonatal/pediatric": .07, "other time-critical": .05},
    ),
    Pathway(
        "cardiac-arrest rapid assistance",
        250_000.0,
        (0.10, 0.30, 0.60),
        (0.20, 0.55, 0.85),
        (0.001, 0.005, 0.020),
        (2e-5, 1e-4, 5e-4),
        (0.80, 0.90, 0.98),
        1.00,
        econ((-3000, 1700, 15000), (20, 80, 250),
             (-1500, 1100, 10000), (-500, 350, 3000),
             (100, 1800, 15000), (0, 0, 0)),
        (0.001, 0.008, 0.050),
        (-0.20, 0.10, 0.80),
        (0.20, 2.00, 12.0),
        {"adoption": .20, "psap_compatibility": .20,
         "responder_access": .25, "video": .15, "contacts": .20},
        {13: .15, 14: .15, 17: .15, 18: .15,
         21: .10, 22: .15, 23: .15},
        {"EMS": .08, "Medicare": .25, "Medicaid": .13,
         "public hospitals": .24, "long-term care/disability": .25,
         "other public": .05},
        {"cardiac arrest": 1.00},
    ),
    Pathway(
        "silent/language access",
        36.367261e6,
        (0.005, 0.02, 0.06),
        (0.15, 0.45, 0.75),
        (5e-5, 4e-4, 2e-3),
        (5e-6, 2e-5, 1e-4),
        (0.70, 0.85, 0.95),
        1.00,
        econ((-10, 30, 250), (5, 18, 80), (-10, 25, 200),
             (-2, 8, 50), (-20, 80, 800), (0, 0, 0)),
        (-0.0001, 0.0003, 0.0030),
        (0.10, 0.57, 2.0),
        (-0.05, 0.25, 2.0),
        {"adoption": .25, "psap_compatibility": .25,
         "language_support": .40, "education": .10},
        {10: .30, 11: .20, 12: .20, 21: .05, 22: .10, 23: .15},
        {"911/PSAP": .15, "EMS": .10, "Medicare": .18,
         "Medicaid": .20, "public hospitals": .25,
         "long-term care/disability": .08, "other public": .04},
        {"cardiovascular/cardiac arrest": .25, "stroke/neurologic": .20,
         "respiratory": .15, "trauma/hemorrhage": .12,
         "sepsis/infection": .10, "obstetric/neonatal/pediatric": .08,
         "other time-critical": .10},
    ),
    Pathway(
        "location/responder access",
        36.367261e6,
        (0.005, 0.03, 0.10),
        (0.20, 0.55, 0.85),
        (1e-4, 8e-4, 4e-3),
        (5e-6, 2e-5, 1e-4),
        (0.55, 0.70, 0.85),
        1.00,
        econ((-20, 55, 600), (10, 35, 160), (-15, 45, 500),
             (-5, 15, 120), (-50, 120, 1500), (0, 25, 500)),
        (-0.0001, 0.0006, 0.0060),
        (0.05, 0.20, 1.0),
        (-0.10, 0.50, 5.0),
        {"adoption": .20, "psap_compatibility": .20,
         "location_correction": .35, "responder_access": .25},
        {13: .45, 14: .30, 21: .05, 22: .10, 23: .10},
        {"911/PSAP": .08, "EMS": .18, "fire": .12, "police": .10,
         "Medicare": .14, "Medicaid": .12, "public hospitals": .14,
         "long-term care/disability": .08, "other public": .04},
        {"medical/EMS": .55, "cardiac arrest": .10, "fire": .18,
         "police/public safety": .17},
    ),
    Pathway(
        "medical data/photo/video",
        36.367261e6,
        (0.01, 0.05, 0.12),
        (0.15, 0.40, 0.70),
        (5e-5, 4e-4, 2e-3),
        (1e-5, 3e-5, 1.5e-4),
        (0.45, 0.60, 0.75),
        0.60,
        econ((-100, 65, 800), (-20, 30, 130), (-80, 50, 600),
             (-20, 15, 150), (-100, 120, 1500), (0, 2, 80)),
        (-0.0004, 0.0005, 0.0050),
        (-1.0, -0.50, 0.20),
        (-0.20, 0.40, 4.0),
        {"adoption": .20, "psap_compatibility": .25,
         "video": .35, "medical_data": .20},
        {15: .25, 16: .10, 17: .35, 21: .05, 22: .10, 23: .15},
        {"911/PSAP": .10, "EMS": .15, "Medicare": .18,
         "Medicaid": .16, "public hospitals": .25,
         "long-term care/disability": .11, "other public": .05},
        {"cardiac arrest": .15, "cardiovascular/stroke": .15,
         "trauma/hemorrhage": .20, "respiratory": .15,
         "neurologic/seizure": .10, "fire/public safety": .15,
         "other time-critical": .10},
    ),
    Pathway(
        "contacts/passive monitoring",
        341.8e6,
        (0.0001, 0.0005, 0.002),
        (0.10, 0.35, 0.65),
        (2e-4, 0.002, 0.010),
        (1e-5, 5e-5, 3e-4),
        (0.70, 0.85, 0.95),
        0.25,
        econ((-1000, 950, 8000), (-300, 20, 800),
             (-600, 550, 6000), (-200, 150, 1500),
             (-1000, 1200, 15000), (0, 0, 0)),
        (-0.003, 0.004, 0.040),
        (-1.0, 0.0, 0.50),
        (-1.0, 3.0, 30.0),
        {"adoption": .25, "psap_compatibility": .15,
         "passive_monitoring": .40, "contacts": .20},
        {18: .25, 19: .10, 20: .35, 21: .05, 22: .15, 23: .10},
        {"EMS": .12, "fire": .03, "police": .05, "Medicare": .25,
         "Medicaid": .15, "public hospitals": .18,
         "long-term care/disability": .18, "other public": .04},
        {"falls/TBI/hemorrhage": .30, "cardiovascular/stroke": .25,
         "endocrine/metabolic": .10, "neurologic/seizure": .10,
         "respiratory": .10, "police/public safety": .10,
         "other severe illness": .05},
    ),
    Pathway(
        "U.S. traveler abroad",
        105.0e6,
        (0.0010, 0.0030, 0.0060),
        (0.20, 0.45, 0.70),
        (5e-5, 2e-4, 1e-3),
        (1e-5, 1e-4, 1e-3),
        (0.80, 0.95, 1.00),
        0.20,
        econ((0, 10, 100), (0, 0, 0), (-200, 600, 6000),
             (-50, 100, 1000), (-300, 700, 8000), (0, 150, 5000)),
        (-0.0005, 0.0015, 0.015),
        (0, 0, 0),
        (-0.50, 1.00, 8.0),
        {"adoption": .30, "traveler_reach": .45,
         "global_numbers": .25},
        {9: .60, 21: .05, 22: .20, 23: .15},
        {"other public": 1.00},
        {"medical abroad": .50, "police/public safety abroad": .30,
         "fire abroad": .10, "other abroad": .10},
    ),
)


DRIVER_RANGES = {
    "adoption": (0.65, 1.00, 1.20),
    "education": (0.50, 1.00, 1.55),
    "diversion": (0.50, 1.00, 1.60),
    "psap_compatibility": (0.65, 1.00, 1.25),
    "location_correction": (0.45, 1.00, 1.70),
    "responder_access": (0.50, 1.00, 1.60),
    "language_support": (0.50, 1.00, 1.55),
    "video": (0.40, 1.00, 1.65),
    "routing_988": (0.45, 1.00, 1.55),
    "routing_211": (0.50, 1.00, 1.50),
    "passive_monitoring": (0.30, 1.00, 1.85),
    "secondary_call": (0.55, 1.00, 1.50),
    "early_activation": (0.50, 1.00, 1.60),
    "contacts": (0.50, 1.00, 1.60),
    "medical_data": (0.45, 1.00, 1.55),
    "traveler_reach": (0.45, 1.00, 1.45),
    "global_numbers": (0.50, 1.00, 1.50),
    "mortality_effect": (0.55, 1.00, 1.55),
    "medical_cost": (0.75, 1.00, 1.35),
    "public_operating_cost": (0.80, 1.00, 1.25),
    "disability_cost": (0.55, 1.00, 1.60),
    "productivity_value": (0.70, 1.00, 1.35),
    "property_loss": (0.45, 1.00, 1.80),
}