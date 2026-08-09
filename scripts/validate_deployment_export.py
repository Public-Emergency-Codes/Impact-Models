#!/usr/bin/env python3
"""Validate future PEC deployment exports against the prespecified schema."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DICTIONARY = ROOT / "validation" / "deployment-data-dictionary.csv"
PRIMARY_KEYS = {
    "episodes": ("episode_id",),
    "function_use": ("function_event_id",),
    "system_contacts": ("contact_id",),
    "outcomes": ("episode_id",),
    "resources": ("resource_id",),
    "deployment": ("cluster_period_id",),
    "queue_intervals": ("queue_interval_id",),
}
EPISODE_CHILDREN = ("function_use", "system_contacts", "outcomes", "resources")
BOOLEAN_VALUES = {"0", "1"}


def read_dictionary() -> dict[str, list[dict[str, str]]]:
    with DICTIONARY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required_columns = {
        "table",
        "variable",
        "type",
        "required",
        "unit",
        "allowed_values",
        "description",
        "validation_role",
    }
    if not rows or set(rows[0]) != required_columns:
        raise AssertionError("validation data dictionary columns are incomplete")
    seen: set[tuple[str, str]] = set()
    tables: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = (row["table"], row["variable"])
        if key in seen:
            raise AssertionError(f"duplicate dictionary entry: {key}")
        seen.add(key)
        tables.setdefault(row["table"], []).append(row)
    if set(tables) != set(PRIMARY_KEYS):
        raise AssertionError("dictionary table set differs from prespecified export")
    for table, keys in PRIMARY_KEYS.items():
        variables = {row["variable"] for row in tables[table]}
        if not set(keys) <= variables:
            raise AssertionError(f"primary key missing from dictionary: {table}")
    return tables


def parse_datetime(value: str, label: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"invalid ISO-8601 datetime for {label}: {value}") from exc


def numeric(value: str, label: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise AssertionError(f"nonnumeric value for {label}: {value}") from exc


def validate_value(row: dict[str, str], spec: dict[str, str], label: str) -> None:
    value = row.get(spec["variable"], "")
    if not value:
        if spec["required"] == "yes":
            raise AssertionError(f"missing required value: {label}")
        return
    kind = spec["type"]
    allowed = spec["allowed_values"]
    if kind == "boolean" and value not in BOOLEAN_VALUES:
        raise AssertionError(f"invalid boolean for {label}: {value}")
    if kind == "datetime":
        parse_datetime(value, label)
    if kind in {"number", "integer"}:
        number = numeric(value, label)
        if kind == "integer" and not number.is_integer():
            raise AssertionError(f"noninteger value for {label}: {value}")
        if allowed == ">=0" and number < 0:
            raise AssertionError(f"negative value for {label}: {value}")
        if allowed == ">=2000" and number < 2000:
            raise AssertionError(f"invalid dollar year for {label}: {value}")
        if allowed == "0..1" and not 0 <= number <= 1:
            raise AssertionError(f"proportion outside [0,1] for {label}: {value}")
        if allowed == "1..23" and not 1 <= number <= 23:
            raise AssertionError(f"PEC function outside 1..23 for {label}: {value}")
    if kind == "enum" and allowed and value not in allowed.split("|"):
        raise AssertionError(f"invalid category for {label}: {value}")


def load_table(data_dir: Path, table: str, specs: list[dict[str, str]]) -> list[dict[str, str]]:
    path = data_dir / f"{table}.csv"
    if not path.is_file():
        raise AssertionError(f"required deployment export is missing: {path.name}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {row["variable"] for row in specs if row["required"] == "yes"}
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise AssertionError(f"{path.name} missing required columns: {missing}")
        rows = list(reader)
    if not rows:
        raise AssertionError(f"deployment export contains no rows: {path.name}")
    keys = PRIMARY_KEYS[table]
    seen: set[tuple[str, ...]] = set()
    for index, row in enumerate(rows, start=2):
        key = tuple(row.get(item, "") for item in keys)
        if "" in key or key in seen:
            raise AssertionError(f"missing or duplicate key in {path.name} row {index}: {key}")
        seen.add(key)
        for spec in specs:
            validate_value(row, spec, f"{path.name}:{index}:{spec['variable']}")
    return rows


def validate_temporal_order(tables: dict[str, list[dict[str, str]]]) -> None:
    for row in tables["system_contacts"]:
        start = parse_datetime(row["contact_start_utc"], "contact_start_utc")
        for field in ("contact_end_utc", "patient_contact_utc", "definitive_treatment_utc"):
            if row.get(field) and parse_datetime(row[field], field) < start:
                raise AssertionError(f"{field} precedes contact start for {row['contact_id']}")
    for row in tables["deployment"]:
        if parse_datetime(row["period_end_utc"], "period_end_utc") <= parse_datetime(
            row["period_start_utc"], "period_start_utc"
        ):
            raise AssertionError(f"deployment period is not positive: {row['cluster_period_id']}")


def validate_data(data_dir: Path, dictionary: dict[str, list[dict[str, str]]]) -> None:
    tables = {
        table: load_table(data_dir, table, specs)
        for table, specs in dictionary.items()
    }
    episode_ids = {row["episode_id"] for row in tables["episodes"]}
    for table in EPISODE_CHILDREN:
        orphaned = {row["episode_id"] for row in tables[table]} - episode_ids
        if orphaned:
            raise AssertionError(f"orphan episode identifiers in {table}: {sorted(orphaned)[:5]}")
    outcome_ids = {row["episode_id"] for row in tables["outcomes"]}
    if outcome_ids != episode_ids:
        raise AssertionError("outcomes.csv must contain exactly one row per episode")
    validate_temporal_order(tables)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    if bool(args.schema_only) == bool(args.data_dir):
        parser.error("choose exactly one of --schema-only or --data-dir")
    dictionary = read_dictionary()
    if args.data_dir:
        validate_data(args.data_dir, dictionary)
        print("[OK] PEC deployment export conforms to the prespecified structural checks.")
    else:
        print("[OK] PEC deployment validation schema is internally consistent.")


if __name__ == "__main__":
    main()