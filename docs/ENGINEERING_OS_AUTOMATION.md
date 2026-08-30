# Engineering OS Automation

This layer turns `engineering_data/` from a manually curated knowledge base into a CI-protected derivative truth system.

## Pipeline

```text
Exact ASR5K production checkout
        |
        v
extract_source_truth.py
        |
        v
source snapshot
        |
        +--> verify_truth_drift.py --> CI FAIL on verified-source drift
        |
Build / HIL / SFRA / scope evidence
        |
        v
import_evidence.py
        |
        v
append-only evidence ledger
        |
        v
traceability.py
        |
        v
Requirement -> implementation -> verification -> evidence -> qualification
```

`hil_runner.py` is the host-intent automation shell. Mock success is reported only as `SIMULATION_PASS`. Process/hardware success is reported as `HARDWARE_RUN_PASS_UNQUALIFIED`; it does not become qualification evidence until the run is bound to exact DUT/build artifacts and imported through the evidence gate.

## Source Truth Extractor

The extractor reads only explicitly listed authoritative production files and extracts high-confidence C contracts:

- SystemState / FaultState / power-sequence / command enum values
- stable fault bitmap values
- software timeout/settle constants
- temporary bench gates
- authoritative scalar SPIB addresses
- host command queue depth/types
- SPIB parser diagnostic threshold identifiers

It intentionally does **not** infer ADC analog scaling, hardware protection latency, formal SPIB acceptance deadlines, SFRA models or board qualification.

Example:

```bash
python tools/extract_source_truth.py \
  --source-root /path/to/ASR5K_v2_28384 \
  --baseline 2b72f50648d86c11547645882248eed69f12892f \
  --out /tmp/asr5k-source-truth.json

python tools/verify_truth_drift.py \
  --snapshot /tmp/asr5k-source-truth.json \
  --data-root engineering_data
```

## Drift Policy

A mismatch between exact production source and a field marked source-verified is a release blocker. Pending fields are excluded from equality comparison until they are promoted with evidence.

Diagnostic counters such as `Over500` / `Over1000` remain diagnostic thresholds and cannot be reclassified as a formal response deadline by the extractor.

## Evidence Import

Evidence is append-only JSONL. A `PASS` import requires:

- exact baseline
- evidence ID
- test ID
- run ID
- artifact ID
- SHA-256 artifact/evidence-bundle identity
- at least one linked requirement ID
- timestamp
- source/instrument

Validation-only mode is the default. `--append` must be explicit.

```bash
python tools/import_evidence.py --input run.json
python tools/import_evidence.py --input run.json --artifact-file CPU1_FLASH.out --append
```

## Traceability

```bash
python tools/traceability.py \
  --out /tmp/traceability.json \
  --markdown /tmp/traceability.md
```

A requirement becomes `QUALIFIED_BY_EVIDENCE` only when an exact-baseline `PASS` evidence record explicitly links that requirement ID. Source code or test-file existence alone never qualifies it.

## HIL Runner

Mock contract check:

```bash
python tools/hil_runner.py \
  --plan engineering_data/hil/reference_mock_plan.json \
  --mode mock \
  --out /tmp/hil-mock.json
```

Local physical gateway:

```bash
python tools/hil_runner.py \
  --plan my-hardware-plan.json \
  --mode process \
  --gateway-command "python local_gateway.py" \
  --allow-hardware \
  --out /tmp/hil-run.json
```

The process adapter speaks newline-delimited JSON to a local gateway. The harness is limited to host intent and observation. Protection, PWM Trip, interlock and emergency shutdown remain DUT-local deterministic authority.

## CI Contract

CI performs two different truth checks:

1. unit/invariant regression against the checked-in engineering dataset;
2. a read-only clone of the pinned ASR5K branch, exact-HEAD verification, source extraction and drift comparison.

If the production branch moves away from the pinned baseline, the source-truth step fails instead of silently evaluating a different DUT.
