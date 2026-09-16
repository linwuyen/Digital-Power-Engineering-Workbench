# Engineering OS Read / Analysis Pipeline

## Current ownership

As of 2026-09-16, Workbench is the **View / Analysis Plane**. Production build, flash, physical HIL, hardware binding, evidence capture orchestration and qualification transactions belong to `linwuyen/ASR5K_v2_28384`.

Workbench keeps only read/normalize/compare/derive/view behavior plus explicitly frozen historical datasets.

## Active pipeline

```text
Exact ASR5K source / execution evidence
        |
        +--> extract_source_truth.py
        |        |
        |        v
        |    pinned source snapshot
        |        |
        |        +--> verify_truth_drift.py
        |
        +--> status/evidence readers
                 |
                 +--> traceability.py
                 |
                 v
        normalized derived status / UI
```

The active read-only / analysis tools are:

- `tools/extract_source_truth.py` — extract high-confidence source facts from an explicitly selected exact firmware baseline;
- `tools/verify_truth_drift.py` — compare source-verified facts against the checked-in historical snapshot model;
- `tools/traceability.py` — derive requirement status from requirement/evidence data;
- `tools/generate_status_snapshot.py` — generate a sanitized derived status snapshot from configured owner repositories;
- `tools/validate_federation.py` — enforce the three-repository authority boundary;
- `tools/truth_common.py` — shared read/serialization helpers.

`tools/import_evidence.py` remains temporarily as a **frozen legacy snapshot writer/validator** for the historical checked-in evidence ledger. It is not the owner of current production evidence capture. New production evidence must be emitted by the Execution Plane.

## Retired execution helpers

The following duplicated Workbench execution helpers were removed after three-repository convergence:

```text
tools/auto_common.py
tools/auto_run.py
tools/auto_run_ext.py
tools/ccs_build.py
tools/evidence_agent.py
tools/hardware_bind.py
tools/hil_runner.py
```

Their production responsibilities now belong to `linwuyen/ASR5K_v2_28384`.

Checked-in data under `engineering_data/automation/` and `engineering_data/hil/` is retained only as frozen historical/reference material. It does not restore execution authority to Workbench.

## Source truth and drift policy

The source extractor reads only explicitly listed authoritative production files and extracts high-confidence contracts such as SystemState/FaultState vocabulary, stable fault bits, timeout constants, temporary bench gates, scalar SPIB addresses, queue depth/types and parser diagnostic identifiers.

It intentionally does **not** infer ADC analog calibration, formal SPIB deadlines, hardware protection shutdown latency, board qualification or production control/SFRA measurements.

A mismatch in a field marked source-verified is a snapshot-consistency failure. Pending values remain unavailable until evidence exists. Diagnostic counters must never be promoted into hardware-performance limits by inference.

## Evidence and traceability boundary

A Workbench-derived status cannot be stronger than its source identity. In particular:

```text
source present != build PASS
build PASS != flash PASS
flash PASS != board PASS
board PASS != HIL PASS
HIL PASS != Production qualification
```

Exact-SHA evidence does not transfer to another SHA. Regression evidence that depends on a GOLDEN baseline is valid only for the exact candidate + exact GOLDEN pair. Missing or stale identity fails closed and remains visible.

## Safety boundary

Workbench never owns OVP/OCP/OTP, PWM Trip, interlock, emergency safe-off, physical actuator authority or deterministic protection timing. Browser/network actions remain operator intent or reference simulation only.

Removing the legacy execution helpers therefore does not change firmware WCET, ISR timing, control-loop behavior, physical fault latency or hardware safety authority.

## Current CI contract

Workbench CI verifies:

1. Python regression tests;
2. Python syntax for the remaining Workbench/read-only tools;
3. engineering JSON/JSONL integrity;
4. federated repository ownership boundaries;
5. historical requirement traceability consistency;
6. pinned source-snapshot truth-drift consistency;
7. browser JavaScript syntax.

The CI proves Workbench consistency. It does not claim production build, flash, board, HIL or protection qualification.
