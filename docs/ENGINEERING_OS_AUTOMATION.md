# Engineering OS Automation

This layer turns `engineering_data/` from a manually curated knowledge base into a CI-protected derivative truth system.

## Pipeline

```text
Exact ASR5K production source
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

## Pinned Snapshot and Live Private Recheck

`ASR5K_v2_28384` is a private repository. A workflow token issued to this Workbench repository does not automatically have read access to another private repository.

Therefore CI has two explicit layers:

1. **Always-on pinned check** — `engineering_data/source_truth/snapshot-2b72f506.json` is a commit-pinned snapshot extracted from the authoritative source files at `2b72f50648d86c11547645882248eed69f12892f`. Every CI run compares this snapshot with the canonical engineering dataset and fails on drift.
2. **Optional live private-source recheck** — if a read-only repository secret named `ASR5K_READ_TOKEN` is configured, CI clones the private production branch read-only, verifies that its HEAD is still the pinned SHA, re-runs the extractor, and compares the live extraction with the canonical dataset.

If `ASR5K_READ_TOKEN` is absent, the live check prints an explicit GitHub Actions notice and exits successfully as **SKIPPED**. That skip is not represented as a live-source PASS. The pinned source-snapshot drift gate still runs and must pass.

If the production branch later moves away from the pinned SHA, a configured live check deliberately fails until a new baseline is reviewed and qualified.

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

Every CI run performs:

1. Python/invariant regression;
2. Python syntax checks for Workbench and automation tools;
3. JSON/JSONL integrity checks;
4. requirement traceability resolution;
5. a non-qualifying HIL mock contract run;
6. pinned exact-source snapshot drift comparison;
7. optional live private ASR5K extraction when `ASR5K_READ_TOKEN` exists;
8. browser JavaScript syntax checks.

The automation layer is a verification and evidence framework. It does not claim board, HIL, AM3352 A/B, protection-latency or control-loop qualification until exact measured evidence is appended to the evidence ledger.
