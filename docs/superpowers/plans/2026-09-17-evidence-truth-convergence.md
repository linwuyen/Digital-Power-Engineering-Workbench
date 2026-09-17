# Evidence Truth Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route all Workbench evidence reads through one source-neutral `EvidenceRecord` adapter boundary while preserving existing qualification, traceability, API, safety, and fail-closed semantics.

**Architecture:** `workbench/evidence_io.py` owns parsing and source-field normalization only. `workbench/status_evidence.py` keeps gate/GOLDEN/conflict policy; `tools/traceability.py` keeps requirement qualification policy; `tools/import_evidence.py` keeps write-time validation and append behavior but reuses the read-only ledger reader.

**Tech Stack:** Python 3.12 stdlib (`dataclasses`, `json`, `pathlib`, `unittest`), existing GitHub Actions Workbench CI.

**Spec:** `docs/superpowers/specs/2026-09-17-evidence-truth-convergence-design.md`

## Global Constraints

- Workbench remains View / Analysis Plane only.
- Do not modify C2000/MSPM0 firmware, ISR/PWM/ADC/control/protection timing, physical safety authority, or fault latency.
- Do not move or rewrite historical evidence storage files.
- Do not change gate precedence, RESULT_MAP semantics, GOLDEN binding, public status schema, or requirement qualification policy.
- Missing/malformed evidence must continue to fail closed.
- No inferred gate, requirement link, evidence identity, or execution SHA.
- Each task must preserve compilability/testability and be independently reviewable/rollbackable.

---

### Task 1: Add the normalized read-only evidence adapter

**Files:**
- Create: `workbench/evidence_io.py`
- Create: `tests/test_evidence_io.py`

**Interfaces:**
- Produces immutable `EvidenceRecord` with fields: `source_type`, `execution_sha`, `result`, `gate`, `evidence_ref`, `evidence_id`, `timestamp`, `golden_sha`, `requirement_ids`, `raw`.
- Produces `read_ledger(path: Path) -> tuple[dict | None, list[dict]]`.
- Produces `load_evidence_records(data_root: Path) -> list[EvidenceRecord]`.
- Produces `detail_row(record: EvidenceRecord) -> dict` for backward-compatible display rows.

- [ ] **Step 1: Write failing adapter tests**

Add tests covering all three raw schemas:

```python
records = load_evidence_records(root)
by_source = {record.source_type: record for record in records}
self.assertEqual(by_source["evidence_ledger"].execution_sha, SHA)
self.assertEqual(by_source["regression_history"].execution_sha, SHA)
self.assertEqual(by_source["regression_history"].golden_sha, GOLDEN)
self.assertEqual(by_source["hardware_results"].execution_sha, SHA)
self.assertEqual(by_source["hardware_results"].result, "BLOCKED")
```

Add a malformed JSONL test requiring `ValueError`, and a non-object JSONL test requiring `ValueError`.

Add a detail-compatibility test requiring regression rows to expose `record_type="regression"`, hardware rows `record_type="hardware"`, and ledger rows to preserve their original raw fields.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python -m unittest tests.test_evidence_io -v
```

Expected: import/module failure because `workbench.evidence_io` does not yet exist.

- [ ] **Step 3: Implement the minimal adapter**

Implement a frozen dataclass and three explicit adapters. Parsing functions reject malformed/non-object data but do not apply qualification policy.

Required mapping:

```python
@dataclass(frozen=True)
class EvidenceRecord:
    source_type: str
    execution_sha: str | None
    result: str
    gate: str | None
    evidence_ref: str | None
    evidence_id: str | None
    timestamp: str | None
    golden_sha: str | None
    requirement_ids: tuple[str, ...]
    raw: dict
```

`load_evidence_records()` must read:

```text
evidence/evidence_ledger.jsonl
verification/regression_history/index.json
verification/hardware_results/index.json
```

Only ledger rows with `record_type == "evidence"` become `EvidenceRecord`s. Missing files return no records for that source.

- [ ] **Step 4: Run focused tests and verify GREEN**

```bash
python -m unittest tests.test_evidence_io -v
```

Expected: all adapter tests PASS.

- [ ] **Step 5: Commit**

```bash
git add workbench/evidence_io.py tests/test_evidence_io.py
git commit -m "refactor: normalize evidence source records"
```

---

### Task 2: Migrate status qualification and evidence details to the adapter

**Files:**
- Modify: `workbench/status_evidence.py`
- Test: `tests/test_status_evidence.py`
- Test: `tests/test_real_qualification_evidence.py`
- Test: `tests/test_status_service.py`

**Interfaces:**
- Consumes: `load_evidence_records(data_root)` and `detail_row(record)` from Task 1.
- Keeps existing public functions: `qualification_for_sha(data_root, execution_sha, golden)` and `evidence_details_for_sha(data_root, execution_sha)`.
- Keeps existing gate dictionary schema produced by `make_gate()`.

- [ ] **Step 1: Add failing migration/behavior tests**

Add a test proving mixed-source normalization preserves gate behavior:

```python
# ledger PASS + regression FAIL for the same explicit gate must still fail closed
self.assertEqual(gate["status"], "UNKNOWN")
self.assertIn("conflicting evidence", gate["note"])
```

Add/retain assertions that:

```text
exact regression PASS + same GOLDEN -> PASS
exact regression PASS + changed GOLDEN -> STALE with visible reason
exact regression PASS + missing current GOLDEN -> UNKNOWN with visible reason
hardware BLOCKED -> PENDING
other execution SHA -> ignored for current gate
PASS/FAIL without evidence reference -> cannot become strong gate evidence
```

Add a detail endpoint compatibility test verifying exact-SHA filtering still returns source-specific raw fields.

- [ ] **Step 2: Run status-focused tests and verify the new contract is RED before migration**

```bash
python -m unittest tests.test_status_evidence tests.test_real_qualification_evidence tests.test_status_service -v
```

Expected: new migration-specific test fails because status code still owns raw source parsing/source-specific SHA plumbing.

- [ ] **Step 3: Replace raw parsing with EvidenceRecord consumption**

In `workbench/status_evidence.py`:

- remove local `read_jsonl()` and `_json()`
- replace `_record_gate(row, sha_field, ...)` with a helper accepting `EvidenceRecord`
- filter current evidence with `record.execution_sha == execution_sha`
- use `record.gate`, `record.result`, `record.evidence_ref`, `record.timestamp`
- preserve current RESULT_MAP and conflict resolution exactly
- apply GOLDEN staleness only to normalized `regression_history` PASS records using `record.golden_sha`
- implement `evidence_details_for_sha()` by filtering normalized records and calling `detail_row()`

Do not change `GATES`, `make_gate`, blocker semantics, or `status_service` schema.

- [ ] **Step 4: Run status-focused tests and verify GREEN**

```bash
python -m unittest tests.test_evidence_io tests.test_status_evidence tests.test_real_qualification_evidence tests.test_status_service -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add workbench/status_evidence.py tests/test_status_evidence.py tests/test_real_qualification_evidence.py tests/test_status_service.py
git commit -m "refactor: resolve gates from normalized evidence"
```

---

### Task 3: Decouple traceability from the evidence writer

**Files:**
- Modify: `tools/traceability.py`
- Modify: `tools/import_evidence.py`
- Modify/Test: `tests/test_engineering_os.py`
- Test: `tests/test_evidence_io.py`

**Interfaces:**
- Consumes: `read_ledger()` / normalized ledger records from `workbench.evidence_io`.
- Keeps `validate_evidence()`, `ledger_baseline()`, and `append_record()` behavior in `tools/import_evidence.py`.
- Keeps `build_traceability(requirements, evidence_rows)` externally compatible for existing tests/callers.

- [ ] **Step 1: Write a failing dependency-boundary test**

Add a source-level boundary assertion:

```python
traceability_source = (ROOT / "tools" / "traceability.py").read_text(encoding="utf-8")
self.assertNotIn("from import_evidence import read_ledger", traceability_source)
self.assertIn("workbench.evidence_io", traceability_source)
```

Add a behavioral test that exact-baseline linked PASS still qualifies, other-baseline PASS remains stale-only, and unlinked regression/hardware records cannot qualify a requirement.

- [ ] **Step 2: Run traceability tests and verify RED**

```bash
python -m unittest tests.test_engineering_os tests.test_evidence_io -v
```

Expected: dependency-boundary assertion FAIL because traceability still imports the writer.

- [ ] **Step 3: Migrate readers without changing writer policy**

- `tools/traceability.py` imports the read-only evidence adapter instead of `import_evidence.py`.
- `tools/import_evidence.py` reuses the shared JSONL ledger reader for existing records/meta, but retains `RESULTS`, required-field validation, digest/run/requirement checks, duplicate evidence ID checks, and append behavior.
- Keep traceability output schema and policy string unchanged unless a wording-only update is required to reflect the shared adapter.

Because tools are executed as scripts from repository root, explicitly ensure repository-root imports work under GitHub Actions; do not rely on accidental current-working-directory behavior without a test.

- [ ] **Step 4: Run traceability/import tests and verify GREEN**

```bash
python -m unittest tests.test_engineering_os tests.test_evidence_io -v
python tools/traceability.py
```

Expected: unit tests PASS and traceability exits 0 with no orphan evidence requirement references.

- [ ] **Step 5: Commit**

```bash
git add tools/traceability.py tools/import_evidence.py tests/test_engineering_os.py tests/test_evidence_io.py
git commit -m "refactor: share read-only evidence adapter"
```

---

### Task 4: Full verification and scope review

**Files:**
- No intended production changes; update docs only if verification exposes a contract mismatch.

**Interfaces:**
- Verifies all interfaces from Tasks 1-3.

- [ ] **Step 1: Run full Python regression**

```bash
python -m unittest discover -s tests -v
```

Expected: 0 failures / 0 errors.

- [ ] **Step 2: Run syntax and engineering-data checks**

```bash
python -m py_compile server.py workbench/*.py tools/*.py tests/*.py
python tools/validate_federation.py
python tools/traceability.py
python tools/verify_truth_drift.py
```

Expected: all commands exit 0; federation and truth-drift report PASS.

- [ ] **Step 3: Run browser JavaScript syntax checks**

Run the repository's existing CI `node --check` suite exactly as defined in `.github/workflows`.

Expected: all JavaScript syntax checks PASS.

- [ ] **Step 4: Inspect the diff boundary**

Confirm changed production files are limited to evidence read/normalization and consumer wiring. Reject any accidental changes to firmware data, gate policy, status schema, control/protection code, or execution-plane behavior.

- [ ] **Step 5: Create/update the PR with RED/GREEN evidence**

PR must state:

```text
View Plane only
no evidence storage migration
no gate/GOLDEN/traceability policy change
no firmware timing/safety/fault-latency impact
```

Include exact RED and GREEN CI run IDs and exact head SHA.
