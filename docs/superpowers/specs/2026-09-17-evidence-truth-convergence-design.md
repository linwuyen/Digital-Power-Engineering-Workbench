# Evidence Truth Convergence Design

## Purpose

Converge Workbench evidence ingestion onto one read-only normalized record boundary without moving historical data or changing qualification policy.

The Workbench remains a View / Analysis Plane. ASR5K_v2_28384 remains the owner of build, flash, HIL, qualification, and physical evidence. This change only normalizes how existing evidence is read and identified.

## Current problem

Evidence currently arrives in three schemas:

1. `engineering_data/evidence/evidence_ledger.jsonl`
2. `engineering_data/verification/regression_history/index.json`
3. `engineering_data/verification/hardware_results/index.json`

`workbench/status_evidence.py` parses all three directly and maps their source-specific identity fields. `tools/traceability.py` separately consumes the JSONL ledger through `tools/import_evidence.py::read_ledger`, coupling a read-only consumer to a writer tool. This creates multiple parsing and identity interpretations for the same engineering evidence domain.

## Architecture

Introduce `workbench/evidence_io.py` as the single read-only evidence adapter boundary.

```text
raw ledger JSONL ───────────────┐
regression_history/index.json ──┼─> evidence_io adapters ─> EvidenceRecord
hardware_results/index.json ────┘                           │
                                                           ├─> status gate resolver
                                                           ├─> requirement traceability resolver
                                                           └─> evidence detail view
```

### EvidenceRecord

Use an immutable Python dataclass with source-neutral identity fields:

- `source_type`: `evidence_ledger`, `regression_history`, or `hardware_results`
- `execution_sha`: exact candidate/DUT/baseline SHA represented by the source record
- `result`: canonical uppercase raw result (`PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, `MEASURED`, etc.)
- `gate`: explicit gate or `None`; adapters never infer a gate from test names
- `evidence_ref`: evidence ID, artifact/log reference, or hardware evidence reference
- `evidence_id`: explicit evidence ID when present
- `timestamp`: source timestamp
- `golden_sha`: regression baseline identity when present
- `requirement_ids`: immutable tuple of explicit requirement links
- `raw`: original record for backward-compatible evidence-detail rendering

Normalization does **not** decide PASS/PENDING/STALE/GOLDEN. Those remain consumer policies.

## Source adapters

### Evidence ledger

- `execution_sha <- baseline`
- `evidence_ref <- evidence_id`
- `timestamp <- timestamp_utc or timestamp`
- preserve explicit `gate`, `result`, `requirement_ids`
- ignore `ledger_meta` as an `EvidenceRecord`, but expose it through the ledger reader for writer validation

### Regression history

- `execution_sha <- commit`
- `evidence_ref <- evidence_id or artifact_or_log`
- `timestamp <- timestamp_utc or timestamp`
- `golden_sha <- golden_sha`
- preserve explicit `gate` and raw result

### Hardware results

- `execution_sha <- dut_commit`
- `evidence_ref <- evidence_id or evidence`
- `timestamp <- timestamp_utc or timestamp`
- preserve explicit `gate` and raw result

## Policy boundaries

### Status / qualification

`workbench/status_evidence.py` remains the owner of gate policy:

- exact execution SHA required
- explicit gate required
- `PASS -> PASS`
- `FAIL -> FAIL`
- `BLOCKED/INCONCLUSIVE/MEASURED -> PENDING`
- regression PASS remains bound to current GOLDEN; mismatch remains `STALE`, unavailable GOLDEN remains `UNKNOWN`
- conflict resolution remains unchanged
- explicit product baseline remains the only source of `GOLDEN`

### Requirement traceability

`tools/traceability.py` remains the owner of requirement policy:

- only explicit `requirement_ids` are linked
- only exact-baseline PASS upgrades to `QUALIFIED_BY_EVIDENCE`
- FAIL remains FAIL
- regression/hardware records without requirement IDs cannot silently qualify requirements

Traceability imports the read-only adapter, never the writer tool.

### Evidence detail endpoint

`build_live_evidence()` continues to return source-specific raw detail rows for UI compatibility. Filtering by exact execution SHA is performed from normalized `EvidenceRecord.execution_sha`; presentation uses the preserved `raw` record plus the existing `record_type` annotation.

## Failure semantics

- Missing evidence files produce an empty source, as today.
- Malformed JSON/JSONL raises `ValueError`; `status_service` continues to degrade health and fail gates closed to UNKNOWN.
- Non-object JSONL records are rejected centrally.
- Adapters do not invent missing identity, gate, evidence reference, requirement links, or timestamps.
- Unknown raw result values remain unqualified by status policy.

## Scope

Create:
- `workbench/evidence_io.py`
- focused adapter tests

Modify:
- `workbench/status_evidence.py`
- `tools/traceability.py`
- `tools/import_evidence.py` to reuse the shared ledger reader while retaining writer validation/append behavior
- existing tests where necessary

Do not modify:
- firmware repositories or MCU code
- ISR/PWM/ADC/control/protection behavior
- gate precedence or GOLDEN semantics
- evidence storage files or schemas
- public status schema
- physical qualification authority

## Definition of Done

1. All three raw evidence schemas normalize through `workbench/evidence_io.py`.
2. `status_evidence.py` no longer contains duplicate JSONL/JSON index readers or source-specific SHA-field plumbing.
3. `traceability.py` no longer imports `read_ledger` from `import_evidence.py`.
4. Existing qualification behavior is unchanged, including exact-SHA filtering, GOLDEN mismatch STALE, missing GOLDEN UNKNOWN, HIL BLOCKED -> PENDING, and conflict fail-closed behavior.
5. Existing traceability behavior is unchanged: only exact-baseline linked PASS evidence qualifies a requirement.
6. Evidence detail API remains compatible with current raw detail rows.
7. Full Workbench CI passes: Python regression/syntax, engineering JSON integrity, federation, traceability, truth-drift, and browser JS syntax.
8. No firmware timing, fault latency, hardware safety, or execution-plane behavior changes.
