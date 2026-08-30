from __future__ import annotations

import argparse
import re
from pathlib import Path

from truth_common import (
    extract_define_int,
    extract_enum,
    require_files,
    write_json,
)


SOURCE_FILES = {
    "system_state_h": "ASR5K_F28384D_CPU1/System_module/system_state.h",
    "system_state_impl": "ASR5K_F28384D_CPU1/System_module/system_state_base.inc",
    "host_queue": "ASR5K_F28384D_CPU1/Command_module/host_command_queue.h",
    "spib_contract": "ASR5K_F28384D_CPU1/SPIB_module/spib_control_register_contract.h",
    "spib_diag": "ASR5K_F28384D_CPU1/SPIB_module/spi_slave.h",
}

TIMING_MACROS = {
    "SYSTEM_AC_ACK_TIMEOUT": "SYSTEM_AC_ACK_TIMEOUT_MS",
    "SYSTEM_OUTPUT_ACK_TIMEOUT": "SYSTEM_OUTPUT_ACK_TIMEOUT_MS",
    "SYSTEM_OUTPUT_RELAY_SETTLE": "SYSTEM_OUTPUT_RELAY_SETTLE_MS",
    "SYSTEM_OUTPUT_DDS_START_TIMEOUT": "SYSTEM_OUTPUT_DDS_START_TIMEOUT_MS",
}

BENCH_GATES = [
    "ASR5K_CPU2_FAULT_BENCH_BYPASS",
    "ASR5K_AC_FAIL_BENCH_BYPASS",
    "ASR5K_DC_OVP_BENCH_BYPASS",
    "ASR5K_BENCH_BYPASS_M0_TIMEOUT",
]

REGISTER_MACROS = [
    "SPIB_CONTROL_FREQUENCY_SET_MSB_ADDR",
    "SPIB_CONTROL_FREQUENCY_SET_LSB_ADDR",
    "SPIB_CONTROL_FREQ_COMP_ON_OFF_ADDR",
    "SPIB_CONTROL_DCV_SET_MSB_ADDR",
    "SPIB_CONTROL_DCV_SET_LSB_ADDR",
    "SPIB_CONTROL_ACV_SET_MSB_ADDR",
    "SPIB_CONTROL_ACV_SET_LSB_ADDR",
]


def _rename(rows, prefix: str, skip: set[str] | None = None):
    skip = skip or set()
    output = []
    for row in rows:
        name = str(row["name"])
        if name in skip:
            continue
        if not name.startswith(prefix):
            raise ValueError(f"unexpected enum item {name!r}; expected prefix {prefix!r}")
        output.append({"name": name[len(prefix):], "value": row["value"]})
    return output


def extract(source_root: str | Path, baseline: str) -> dict:
    files = require_files(source_root, list(SOURCE_FILES.values()))
    text = {key: files[path].read_text(encoding="utf-8", errors="strict") for key, path in SOURCE_FILES.items()}

    states = _rename(extract_enum(text["system_state_h"], "E_SYSTEM_STATE"), "SYSTEM_STATE_")
    fault_states = _rename(extract_enum(text["system_state_h"], "E_FAULT_STATE"), "FAULT_STATE_")
    power_sequence = _rename(extract_enum(text["system_state_h"], "E_POWER_SEQUENCE_STATE"), "POWER_SEQUENCE_")
    commands = _rename(extract_enum(text["system_state_h"], "E_SYSTEM_COMMAND"), "SYSTEM_CMD_")
    faults = _rename(
        extract_enum(text["system_state_h"], "E_SYSTEM_FAULT_SOURCE"),
        "SYSTEM_FAULT_",
        {"SYSTEM_FAULT_NONE"},
    )
    fault_bitmap = [
        {"name": row["name"], "mask": f"0x{int(row['value']):08X}"}
        for row in faults
    ]

    timing = {
        fact_id: extract_define_int(text["system_state_impl"], macro)
        for fact_id, macro in TIMING_MACROS.items()
    }
    bench_gates = {
        name: extract_define_int(text["system_state_h"], name)
        for name in BENCH_GATES
    }
    registers = {
        name: f"0x{extract_define_int(text['spib_contract'], name):04X}"
        for name in REGISTER_MACROS
    }
    queue_depth = extract_define_int(text["host_queue"], "HOST_COMMAND_QUEUE_DEPTH")
    host_commands = _rename(extract_enum(text["host_queue"], "E_HOST_COMMAND_TYPE"), "HOST_COMMAND_")

    diagnostic_thresholds = sorted({
        int(value)
        for value in re.findall(r"u32SpiBParserOver(\d+)Count", text["spib_diag"])
    })
    if not diagnostic_thresholds:
        raise ValueError("no SPIB parser diagnostic threshold identifiers extracted")

    return {
        "schema_version": "1.0",
        "baseline": baseline,
        "extractor": "tools/extract_source_truth.py",
        "source_files": SOURCE_FILES,
        "facts": {
            "system_states": states,
            "fault_states": fault_states,
            "power_sequence_states": power_sequence,
            "system_commands": commands,
            "fault_bitmap": fault_bitmap,
            "timing_ms": timing,
            "bench_gates": bench_gates,
            "scalar_registers": registers,
            "host_queue_depth": queue_depth,
            "host_command_types": host_commands,
            "spib_parser_diagnostic_threshold_ticks": diagnostic_thresholds,
        },
        "policy": {
            "source_only": True,
            "unknown_values_are_not_inferred": True,
            "diagnostic_thresholds_are_not_deadlines": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract high-confidence ASR5K engineering facts from an exact source checkout.")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    write_json(args.out, extract(args.source_root, args.baseline))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
