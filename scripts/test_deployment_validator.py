#!/usr/bin/env python3
"""Self-test the PEC deployment-export validator with synthetic records."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import validate_deployment_export as validator


def example_value(spec: dict[str, str]) -> str:
    variable = spec["variable"]
    if spec["required"] != "yes":
        return ""
    overrides = {
        "episode_id": "E1",
        "cluster_id": "C1",
        "function_event_id": "F1",
        "contact_id": "S1",
        "resource_id": "R1",
        "cluster_period_id": "D1",
        "queue_interval_id": "Q1",
        "incident_start_utc": "2026-01-01T00:00:00+00:00",
        "event_utc": "2026-01-01T00:01:00+00:00",
        "contact_start_utc": "2026-01-01T00:02:00+00:00",
        "period_start_utc": "2026-01-01T00:00:00+00:00",
        "period_end_utc": "2026-02-01T00:00:00+00:00",
        "interval_start_utc": "2026-01-01T00:00:00+00:00",
        "function_number": "1",
        "rollout_period": "0",
        "dollar_year": "2026",
    }
    if variable in overrides:
        return overrides[variable]
    kind = spec["type"]
    allowed = spec["allowed_values"]
    if kind == "enum":
        return allowed.split("|")[0]
    if kind == "boolean":
        return "0"
    if kind == "datetime":
        return "2026-01-01T00:00:00+00:00"
    if kind == "integer":
        return "0"
    if kind == "number":
        return "0.5" if allowed == "0..1" else "0"
    return "x"


def write_valid_export(directory: Path) -> None:
    dictionary = validator.read_dictionary()
    for table, specs in dictionary.items():
        fieldnames = [spec["variable"] for spec in specs]
        row = {spec["variable"]: example_value(spec) for spec in specs}
        with (directory / f"{table}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row)


def main() -> None:
    dictionary = validator.read_dictionary()
    with tempfile.TemporaryDirectory(prefix="pec-validation-selftest-") as tmp:
        directory = Path(tmp)
        write_valid_export(directory)
        validator.validate_data(directory, dictionary)

        outcomes = directory / "outcomes.csv"
        text = outcomes.read_text(encoding="utf-8").replace("E1", "ORPHAN")
        outcomes.write_text(text, encoding="utf-8")
        try:
            validator.validate_data(directory, dictionary)
        except AssertionError as exc:
            if "orphan episode identifiers" not in str(exc):
                raise
        else:
            raise AssertionError("validator failed to reject an orphan outcome")
    print("[OK] PEC deployment-data validator accepts valid structure and rejects an orphan.")


if __name__ == "__main__":
    main()