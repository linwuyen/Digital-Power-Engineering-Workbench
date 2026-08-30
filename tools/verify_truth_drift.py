from __future__ import annotations

import argparse
from pathlib import Path

from truth_common import load_json, write_json


REGISTER_BINDINGS = {
    "FREQUENCY_SET": ["SPIB_CONTROL_FREQUENCY_SET_MSB_ADDR", "SPIB_CONTROL_FREQUENCY_SET_LSB_ADDR"],
    "DCV_SET": ["SPIB_CONTROL_DCV_SET_MSB_ADDR", "SPIB_CONTROL_DCV_SET_LSB_ADDR"],
    "ACV_SET": ["SPIB_CONTROL_ACV_SET_MSB_ADDR", "SPIB_CONTROL_ACV_SET_LSB_ADDR"],
}

TIMING_BINDINGS = {
    "SYSTEM_AC_ACK_TIMEOUT": "SYSTEM_AC_ACK_TIMEOUT",
    "SYSTEM_OUTPUT_ACK_TIMEOUT": "SYSTEM_OUTPUT_ACK_TIMEOUT",
    "SYSTEM_OUTPUT_RELAY_SETTLE": "SYSTEM_OUTPUT_RELAY_SETTLE",
    "SYSTEM_OUTPUT_DDS_START_TIMEOUT": "SYSTEM_OUTPUT_DDS_START_TIMEOUT",
}


def _state_rows(state: dict) -> list[dict]:
    return [{"name": row["id"], "value": row["value"]} for row in state["system_states"]]


def _fault_rows(protection: dict) -> list[dict]:
    return [{"name": row["name"], "mask": row["mask"].upper()} for row in protection["fault_sources"]]


def compare(snapshot: dict, data_root: str | Path) -> dict:
    root = Path(data_root)
    index = load_json(root / "index.json")
    state = load_json(root / "firmware/state_machine.json")
    protection = load_json(root / "protection/protection_matrix.json")
    timing = load_json(root / "timing/timing_budget.json")
    commands = load_json(root / "protocol/command_dictionary.json")

    errors: list[dict] = []
    checks: list[dict] = []

    def check(name: str, source_value, canonical_value) -> None:
        ok = source_value == canonical_value
        checks.append({"check": name, "ok": ok})
        if not ok:
            errors.append({
                "check": name,
                "source": source_value,
                "canonical": canonical_value,
            })

    baseline = snapshot["baseline"]
    check("baseline.index", baseline, index["baseline"]["commit"])
    check("baseline.state", baseline, state["baseline"])
    check("baseline.protection", baseline, protection["baseline"])
    check("baseline.timing", baseline, timing["baseline"])

    facts = snapshot["facts"]
    check("system_states", facts["system_states"], _state_rows(state))
    check("fault_bitmap", facts["fault_bitmap"], _fault_rows(protection))

    gate_canonical = {row["name"]: int(row["value"]) for row in protection["temporary_baseline_gates"]}
    check("temporary_bench_gates", facts["bench_gates"], gate_canonical)

    timing_by_id = {row["id"]: row for row in timing["budgets"]}
    for source_key, canonical_id in TIMING_BINDINGS.items():
        check(
            f"timing.{canonical_id}",
            facts["timing_ms"][source_key],
            timing_by_id[canonical_id]["budget"],
        )

    diagnostic = set(facts["spib_parser_diagnostic_threshold_ticks"])
    check("spib_parser_diagnostic_500", 500 in diagnostic, True)
    check("spib_parser_diagnostic_1000", 1000 in diagnostic, True)
    check("timing.SPIB_PARSER_500_TICK_DIAGNOSTIC", 500, timing_by_id["SPIB_PARSER_500_TICK_DIAGNOSTIC"]["budget"])
    check("timing.SPIB_PARSER_1000_TICK_DIAGNOSTIC", 1000, timing_by_id["SPIB_PARSER_1000_TICK_DIAGNOSTIC"]["budget"])

    check("host_queue_depth", facts["host_queue_depth"], commands["queue_depth"])
    by_name = {row["name"]: row for row in commands["intent_types"]}
    registers = facts["scalar_registers"]
    for intent, macro_names in REGISTER_BINDINGS.items():
        check(
            f"registers.{intent}",
            [registers[name] for name in macro_names],
            [value.upper() for value in by_name[intent]["wire_addresses"]],
        )
    freq_comp = next(row for row in commands["additional_verified_registers"] if row["name"] == "FREQ_COMP_ON_OFF")
    check(
        "registers.FREQ_COMP_ON_OFF",
        registers["SPIB_CONTROL_FREQ_COMP_ON_OFF_ADDR"],
        freq_comp["address"].upper(),
    )

    return {
        "schema_version": "1.0",
        "baseline": baseline,
        "status": "PASS" if not errors else "DRIFT",
        "checks": checks,
        "errors": errors,
        "rule": "Source-verified facts may not drift from engineering_data silently. Pending facts remain outside this equality gate until promoted with evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare an extracted source snapshot with canonical engineering_data.")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--data-root", default="engineering_data")
    parser.add_argument("--report")
    args = parser.parse_args()

    report = compare(load_json(args.snapshot), args.data_root)
    if args.report:
        write_json(args.report, report)
    if report["errors"]:
        for error in report["errors"]:
            print(f"TRUTH DRIFT {error['check']}: source={error['source']!r} canonical={error['canonical']!r}")
        return 2
    print(f"truth drift check PASS ({len(report['checks'])} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
