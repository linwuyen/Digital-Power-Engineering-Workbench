# ASR5K Engineering Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refocus Digital-Power-Engineering-Workbench into an ASR5K-first engineering status console that shows exact source identities, GOLDEN relation, evidence-typed qualification state, blockers, and freshness while preserving the existing engineering tools as secondary views.

**Architecture:** Keep all engineering truth outside the Workbench. A Python normalization layer builds one JSON-safe status model from read-only local repository inspection plus existing Workbench evidence ledgers; the local server exposes that model through a read-only API. A sanitized committed snapshot uses the same model contract for GitHub Pages, while the browser renders either source without changing status semantics.

**Tech Stack:** Python 3.10+ standard library, `unittest`, `http.server`, Git CLI read-only queries, vanilla HTML/CSS/JavaScript, Node syntax/smoke checks, existing `engineering_data/` JSON/JSONL contracts.

**Spec:** `docs/superpowers/specs/2026-09-12-asr5k-engineering-console-design.md`

## Global Constraints

- Workbench remains the View / Analysis Plane and never becomes the source of product, implementation, build, flash, HIL, or qualification truth.
- Exact-SHA evidence never transfers to another SHA by inference.
- `PASS` requires explicit evidence for the named SHA; missing evidence is `UNKNOWN` or `PENDING`, never inferred PASS.
- `GOLDEN` is valid only for the Production gate and requires an explicit product-baseline source plus matching exact identity.
- Public/static browser code must never contain or request a private GitHub token.
- Local status inspection is read-only: no merge, rebase, reset, checkout, clean, stash, commit, push, flash, HIL, label mutation, or other state-changing command.
- Browser requests never supply filesystem paths; repository paths are backend configuration only.
- Existing Signal Chain, Control/Bode, SFRA, State, and Protocol tools remain reachable.
- The mock remote-control surface is removed from primary navigation and remains clearly non-production if retained.
- No new production execution authority is added to Workbench.
- Python runtime remains dependency-free beyond the standard library.
- Existing repository checks remain runnable: `python -m unittest discover -s tests -v`, `python -m py_compile server.py workbench/*.py tools/*.py tests/*.py`, and Node syntax checks.

---

## File Structure

### New files

- `workbench/status_model.py` — normalized status schema, gate validation, freshness, blocker derivation, fail-closed helpers.
- `workbench/status_live.py` — read-only local Git/repository inspection and product-baseline parsing.
- `workbench/status_evidence.py` — exact-SHA evidence normalization from existing Workbench ledgers; never executes qualification.
- `workbench/status_service.py` — composes identities, baseline, evidence, freshness, and blockers into one status model.
- `workbench/status_snapshot.py` — public sanitization plus committed snapshot loading/validation.
- `tools/generate_status_snapshot.py` — explicit operator command that creates the sanitized public status snapshot from configured local sources.
- `static/eng/status_console.js` — status API/snapshot loading and rendering only; no qualification inference.
- `tests/test_status_model.py` — policy-model unit tests.
- `tests/test_status_live.py` — local Git/baseline parser tests using temporary repositories.
- `tests/test_status_evidence.py` — evidence binding and no-inference tests.
- `tests/test_status_service.py` — complete/missing-source composition tests.
- `tests/test_status_api.py` — `/api/status/summary` integration tests.
- `tests/test_status_snapshot.py` — sanitization and snapshot consistency tests.
- `tests/test_status_frontend.py` — static frontend contract tests.
- `engineering_data/status/status_snapshot.json` — generated, sanitized public status view.

### Modified files

- `server.py` — add read-only `/api/status/summary` and `/api/status/evidence` GET routes.
- `static/index.html` — make ASR5K Status the default panel and regroup old tools under Engineering Tools.
- `static/eng/loader.js` — load the status renderer before other engineering-view modules.
- `static/styles.css` — status cards, gate matrix, blockers, source/freshness styling, nav-group styling.
- `static/i18n.js` — labels for status navigation and status sections; retain existing language behavior.
- `engineering_data/index.json` — register `status_snapshot` as a derived view resource.
- `tests/test_engineering_data.py` — require the new snapshot resource to parse and remain non-authoritative.
- `tests/test_final_integration.py` — assert Status is the landing view and the old tools remain reachable.
- `README.md` — document ASR5K Engineering Console role, LIVE/SNAPSHOT operation, and verification commands.
- `docs/CURRENT_STATUS.md` — record the new dashboard role without changing source authority.

---

### Task 1: Build the normalized status policy model

**Files:**
- Create: `workbench/status_model.py`
- Create: `tests/test_status_model.py`

**Interfaces:**
- Produces: `GATES: tuple[str, ...]`
- Produces: `VALID_GATE_STATES: frozenset[str]`
- Produces: `make_gate(gate: str, status: str, *, sha: str | None = None, evidence: str | None = None, evidence_type: str | None = None, timestamp: str | None = None, note: str | None = None) -> dict`
- Produces: `bind_gate_to_sha(row: dict, expected_sha: str | None) -> dict`
- Produces: `classify_freshness(generated_at: str | None, now: datetime, stale_after_seconds: int) -> str`
- Produces: `derive_blockers(model: dict) -> list[dict]`
- Produces: `validate_status_model(model: dict) -> None`
- Consumes: no project-specific modules; only Python standard library.

- [ ] **Step 1: Write failing gate and fail-closed tests**

Create `tests/test_status_model.py` with focused tests like:

```python
from datetime import datetime, timezone
import unittest

from workbench.status_model import (
    bind_gate_to_sha,
    classify_freshness,
    derive_blockers,
    make_gate,
    validate_status_model,
)


SHA = "a" * 40
OTHER = "b" * 40


class StatusModelTests(unittest.TestCase):
    def test_pass_requires_sha_and_evidence(self):
        with self.assertRaises(ValueError):
            make_gate("build", "PASS", sha=SHA, evidence=None)

    def test_evidence_for_other_sha_becomes_mismatch(self):
        row = make_gate("build", "PASS", sha=OTHER, evidence="run-17")
        bound = bind_gate_to_sha(row, SHA)
        self.assertEqual(bound["status"], "MISMATCH")
        self.assertEqual(bound["sha"], OTHER)

    def test_unknown_never_requires_fake_evidence(self):
        row = make_gate("hil", "UNKNOWN")
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertIsNone(row["evidence"])

    def test_snapshot_becomes_stale_after_threshold(self):
        now = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
        state = classify_freshness("2026-09-12T09:00:00+00:00", now, 3600)
        self.assertEqual(state, "STALE")

    def test_blockers_distinguish_fail_unknown_and_stale(self):
        model = {
            "qualification": [
                make_gate("build", "FAIL", sha=SHA, evidence="build.log"),
                make_gate("hil", "UNKNOWN"),
            ],
            "identity": {"relation_to_golden": "MATCH", "evidence_sha_match": True},
            "freshness": {"status": "STALE"},
        }
        categories = {x["category"] for x in derive_blockers(model)}
        self.assertIn("FIRMWARE_BLOCKER", categories)
        self.assertIn("UNKNOWN_EVIDENCE", categories)
        self.assertIn("STALE_SOURCE", categories)

    def test_golden_is_only_valid_for_production_gate(self):
        with self.assertRaises(ValueError):
            make_gate("build", "GOLDEN", sha=SHA, evidence="CURRENT_PRODUCT_BASELINE.md")

    def test_model_validation_rejects_pass_bound_to_wrong_execution_sha(self):
        model = {
            "schema_version": "1.0",
            "mode": "LIVE",
            "generated_at": "2026-09-12T12:00:00+00:00",
            "health": "DEGRADED",
            "control_plane": {"repository": "linwuyen/ASR5K_AGENT", "sha": SHA, "branch": "main", "status": "CURRENT"},
            "execution_plane": {"repository": "linwuyen/ASR5K_v2_28384", "sha": SHA, "branch": "main", "dirty": False},
            "product_baseline": {"golden_sha": SHA, "release_ref": "release/final", "source": "CURRENT_PRODUCT_BASELINE.md"},
            "identity": {"relation_to_golden": "MATCH", "evidence_sha_match": False, "control_plane_revision_known": True},
            "qualification": [make_gate("build", "PASS", sha=OTHER, evidence="build.log")],
            "blockers": [],
            "freshness": {"status": "LIVE", "age_seconds": 0, "sources": []},
        }
        with self.assertRaises(ValueError):
            validate_status_model(model)
```

- [ ] **Step 2: Run the new tests and confirm they fail before implementation**

Run:

```bash
python -m unittest tests.test_status_model -v
```

Expected: import failure because `workbench.status_model` does not exist.

- [ ] **Step 3: Implement the minimal status policy module**

Create `workbench/status_model.py` with the fixed gate vocabulary and explicit validation:

```python
from __future__ import annotations

from copy import deepcopy
from datetime import datetime


GATES = (
    "source", "build", "regression", "artifact", "flash",
    "board", "hil", "protection", "production",
)
VALID_GATE_STATES = frozenset({
    "PASS", "FAIL", "PENDING", "UNKNOWN", "NOT_RUN",
    "NOT_REQUIRED", "STALE", "MISMATCH", "GOLDEN",
})


def make_gate(gate: str, status: str, *, sha: str | None = None,
              evidence: str | None = None, evidence_type: str | None = None,
              timestamp: str | None = None, note: str | None = None) -> dict:
    gate = str(gate).lower()
    status = str(status).upper()
    if gate not in GATES:
        raise ValueError(f"unsupported qualification gate: {gate}")
    if status not in VALID_GATE_STATES:
        raise ValueError(f"unsupported gate status: {status}")
    if status in {"PASS", "GOLDEN", "FAIL"} and (not sha or not evidence):
        raise ValueError(f"{status} requires exact sha and evidence")
    if status == "GOLDEN" and gate != "production":
        raise ValueError("GOLDEN is valid only for production")
    return {
        "gate": gate,
        "status": status,
        "sha": sha,
        "evidence": evidence,
        "evidence_type": evidence_type,
        "timestamp": timestamp,
        "note": note,
    }


def bind_gate_to_sha(row: dict, expected_sha: str | None) -> dict:
    bound = deepcopy(row)
    if expected_sha and bound.get("status") in {"PASS", "FAIL", "GOLDEN"}:
        if bound.get("sha") != expected_sha:
            bound["status"] = "MISMATCH"
            bound["note"] = f"evidence SHA {bound.get('sha')} != execution SHA {expected_sha}"
    return bound


def classify_freshness(generated_at: str | None, now: datetime,
                       stale_after_seconds: int) -> str:
    if not generated_at:
        return "UNKNOWN"
    generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    age = max(0.0, (now - generated).total_seconds())
    return "STALE" if age > stale_after_seconds else "SNAPSHOT"
```

Implement `derive_blockers()` so `FAIL`, `MISMATCH`, `PENDING`, `UNKNOWN`, and `STALE` remain distinct categories, and implement `validate_status_model()` so it rejects PASS/GOLDEN/FAIL rows not bound to the execution SHA.

- [ ] **Step 4: Run model tests**

```bash
python -m unittest tests.test_status_model -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run existing workbench unit tests to prove no regression**

```bash
python -m unittest tests.test_workbench -v
```

Expected: existing measurement/control/remote/state tests PASS.

- [ ] **Step 6: Commit**

```bash
git add workbench/status_model.py tests/test_status_model.py
git commit -m "feat: add ASR5K status policy model"
```

---

### Task 2: Add read-only local repository identity and GOLDEN parsing

**Files:**
- Create: `workbench/status_live.py`
- Create: `tests/test_status_live.py`

**Interfaces:**
- Consumes: standard-library `subprocess`, `pathlib`, `re`.
- Produces: `repo_identity(repo: Path) -> dict`
- Produces: `parse_product_baseline(text: str) -> dict`
- Produces: `read_product_baseline(firmware_root: Path) -> dict`
- Produces: `relation_to_golden(firmware_root: Path, current_sha: str, golden_sha: str) -> str`
- Produces: `resolve_live_sources(agent_root: Path, firmware_root: Path) -> dict`

- [ ] **Step 1: Write temporary-Git-repository tests**

Use `tempfile.TemporaryDirectory()` and real local `git init` so behavior matches production Git semantics:

```python
import subprocess
import tempfile
import unittest
from pathlib import Path

from workbench.status_live import (
    parse_product_baseline,
    relation_to_golden,
    repo_identity,
)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True,
                            capture_output=True, check=True)
    return result.stdout.strip()


class StatusLiveTests(unittest.TestCase):
    def make_repo(self, root: Path) -> str:
        git(root, "init")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "Status Test")
        (root / "file.txt").write_text("one\n", encoding="utf-8")
        git(root, "add", "file.txt")
        git(root, "commit", "-m", "one")
        return git(root, "rev-parse", "HEAD")

    def test_repo_identity_reports_dirty_without_mutating(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sha = self.make_repo(root)
            (root / "file.txt").write_text("two\n", encoding="utf-8")
            identity = repo_identity(root)
            self.assertEqual(identity["sha"], sha)
            self.assertTrue(identity["dirty"])
            self.assertEqual(git(root, "rev-parse", "HEAD"), sha)

    def test_product_baseline_parser_requires_40_hex_sha_and_release_ref(self):
        sha = "c31ecc57a54f9f84874af40234907be357638ebe"
        parsed = parse_product_baseline(
            f"FINAL / GOLDEN firmware SHA:\n{sha}\n\nPinned release ref:\nrelease/final-c31ecc57-20260908\n"
        )
        self.assertEqual(parsed["golden_sha"], sha)
        self.assertEqual(parsed["release_ref"], "release/final-c31ecc57-20260908")

    def test_relation_is_match_then_ahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            golden = self.make_repo(root)
            self.assertEqual(relation_to_golden(root, golden, golden), "MATCH")
            (root / "file.txt").write_text("two\n", encoding="utf-8")
            git(root, "add", "file.txt")
            git(root, "commit", "-m", "two")
            head = git(root, "rev-parse", "HEAD")
            self.assertEqual(relation_to_golden(root, head, golden), "AHEAD")
```

Add tests for missing repo, malformed `CURRENT_PRODUCT_BASELINE.md`, and a diverged history created from an orphan branch.

- [ ] **Step 2: Run tests and confirm import failure**

```bash
python -m unittest tests.test_status_live -v
```

Expected: FAIL because `workbench.status_live` does not exist.

- [ ] **Step 3: Implement only read-only Git commands**

Implement a private `_git(repo, *args, allow_failure=False)` that invokes only queries. `repo_identity()` should call:

```text
git rev-parse --show-toplevel
git rev-parse HEAD
git branch --show-current
git status --porcelain
```

Do not call checkout/reset/fetch/pull/merge/rebase/stash/clean.

Implement baseline parsing with strict regexes:

```python
SHA_RE = re.compile(r"(?im)^FINAL / GOLDEN firmware SHA:\s*\n([0-9a-f]{40})\s*$")
REF_RE = re.compile(r"(?im)^Pinned release ref:\s*\n([^\s]+)\s*$")
```

`read_product_baseline()` reads only `<firmware_root>/CURRENT_PRODUCT_BASELINE.md` after resolving the path and verifying it remains under the configured firmware root.

`relation_to_golden()` rules:

```python
if current_sha == golden_sha:
    return "MATCH"
if _git(repo, "merge-base", "--is-ancestor", golden_sha, current_sha, allow_failure=True).returncode == 0:
    return "AHEAD"
return "DIVERGED"
```

Return `UNKNOWN` only when Git cannot establish the relation; do not reinterpret command errors as `DIVERGED` when object identity is unavailable.

- [ ] **Step 4: Run live-source tests**

```bash
python -m unittest tests.test_status_live -v
```

Expected: PASS.

- [ ] **Step 5: Run compile check**

```bash
python -m py_compile workbench/status_live.py tests/test_status_live.py
```

Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add workbench/status_live.py tests/test_status_live.py
git commit -m "feat: inspect ASR5K source identities read only"
```

---

### Task 3: Normalize exact-SHA evidence without inventing qualification

**Files:**
- Create: `workbench/status_evidence.py`
- Create: `tests/test_status_evidence.py`

**Interfaces:**
- Consumes: `make_gate()` and `bind_gate_to_sha()` from `workbench.status_model`.
- Consumes existing derived data only:
  - `engineering_data/evidence/evidence_ledger.jsonl`
  - `engineering_data/verification/regression_history/index.json`
  - `engineering_data/verification/hardware_results/index.json`
- Produces: `read_jsonl(path: Path) -> list[dict]`
- Produces: `qualification_for_sha(data_root: Path, execution_sha: str, golden: dict) -> list[dict]`
- Produces: `evidence_details_for_sha(data_root: Path, execution_sha: str) -> list[dict]`

**Evidence rule for V1:** historical records for other SHAs remain historical and do not poison the current SHA as `MISMATCH`. `MISMATCH` is reserved for a currently selected claim whose explicit evidence identity differs from the execution SHA. Absence of matching evidence remains `UNKNOWN`.

- [ ] **Step 1: Write failing exact-SHA evidence tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from workbench.status_evidence import qualification_for_sha


SHA = "a" * 40
OTHER = "b" * 40


class StatusEvidenceTests(unittest.TestCase):
    def write_dataset(self, root: Path, evidence_rows: list[dict]) -> None:
        (root / "evidence").mkdir(parents=True)
        (root / "verification" / "regression_history").mkdir(parents=True)
        (root / "verification" / "hardware_results").mkdir(parents=True)
        meta = {"record_type": "ledger_meta", "schema_version": "1.0", "baseline": SHA}
        lines = [json.dumps(meta), *[json.dumps(x) for x in evidence_rows]]
        (root / "evidence" / "evidence_ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (root / "verification" / "regression_history" / "index.json").write_text(
            json.dumps({"records": [], "status": "no_result_claimed"}) + "\n", encoding="utf-8")
        (root / "verification" / "hardware_results" / "index.json").write_text(
            json.dumps({"records": [], "status": "no_result_claimed"}) + "\n", encoding="utf-8")

    def test_no_records_means_unknown_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, [])
            gates = {x["gate"]: x for x in qualification_for_sha(root, SHA, {"golden_sha": OTHER, "source": "baseline.md"})}
            self.assertEqual(gates["build"]["status"], "UNKNOWN")
            self.assertEqual(gates["hil"]["status"], "UNKNOWN")

    def test_explicit_matching_gate_pass_can_be_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, [{
                "record_type": "evidence",
                "evidence_id": "EVD-1",
                "baseline": SHA,
                "gate": "build",
                "artifact_id": "cpu1.out",
                "test_id": "CPU1-BUILD",
                "result": "PASS",
                "timestamp_utc": "2026-09-12T10:00:00Z",
                "source_or_instrument": "CCS",
                "artifact_sha256": "1" * 64,
                "requirement_ids": ["REQ-BUILD-CPU1-001"],
                "run_id": "RUN-1"
            }])
            gates = {x["gate"]: x for x in qualification_for_sha(root, SHA, {"golden_sha": OTHER, "source": "baseline.md"})}
            self.assertEqual(gates["build"]["status"], "PASS")
            self.assertEqual(gates["build"]["sha"], SHA)
            self.assertEqual(gates["build"]["evidence"], "EVD-1")

    def test_other_sha_pass_is_historical_not_current_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, [{
                "record_type": "evidence", "evidence_id": "OLD",
                "baseline": OTHER, "gate": "build", "artifact_id": "old.out",
                "test_id": "CPU1-BUILD", "result": "PASS",
                "timestamp_utc": "2026-09-01T10:00:00Z",
                "source_or_instrument": "CCS", "artifact_sha256": "2" * 64,
                "requirement_ids": ["REQ-BUILD-CPU1-001"], "run_id": "RUN-OLD"
            }])
            gates = {x["gate"]: x for x in qualification_for_sha(root, SHA, {"golden_sha": OTHER, "source": "baseline.md"})}
            self.assertEqual(gates["build"]["status"], "UNKNOWN")

    def test_matching_golden_sha_sets_only_production_to_golden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, [])
            gates = {x["gate"]: x for x in qualification_for_sha(root, SHA, {
                "golden_sha": SHA,
                "source": "CURRENT_PRODUCT_BASELINE.md",
                "release_ref": "release/final"
            })}
            self.assertEqual(gates["production"]["status"], "GOLDEN")
            self.assertEqual(gates["board"]["status"], "UNKNOWN")
```

- [ ] **Step 2: Run and confirm failure**

```bash
python -m unittest tests.test_status_evidence -v
```

Expected: FAIL because `workbench.status_evidence` does not exist.

- [ ] **Step 3: Implement conservative evidence mapping**

Start all gates as `UNKNOWN`. Set:

```text
source      -> assigned later by status_service from live source identity
production  -> GOLDEN only when execution SHA == parsed GOLDEN SHA
```

For evidence ledger rows, consume only rows where all are true:

```python
row.get("record_type") == "evidence"
row.get("baseline") == execution_sha
row.get("gate") in GATES
row.get("result") in {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}
```

Map results:

```text
PASS         -> PASS
FAIL         -> FAIL
BLOCKED      -> PENDING
INCONCLUSIVE -> PENDING
MEASURED     -> PENDING unless another explicit result contract promotes it
```

Do not infer a gate from `test_id`, requirement name, filename, or prose. Evidence without an explicit `gate` stays visible in evidence details but does not upgrade a gate.

Regression/hardware ledger records may be shown in evidence details. They may upgrade a gate only if the record itself has an explicit supported `gate` and exact matching SHA (`commit` for regression, `dut_commit` for hardware).

- [ ] **Step 4: Run evidence tests**

```bash
python -m unittest tests.test_status_evidence -v
```

Expected: PASS.

- [ ] **Step 5: Prove existing evidence importer semantics still pass**

```bash
python -m unittest tests.test_engineering_os.EngineeringOsAutomationTest.test_pass_evidence_requires_hash_run_and_requirement -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add workbench/status_evidence.py tests/test_status_evidence.py
git commit -m "feat: normalize exact SHA qualification evidence"
```

---

### Task 4: Compose the LIVE status service with explicit degraded states

**Files:**
- Create: `workbench/status_service.py`
- Create: `tests/test_status_service.py`

**Interfaces:**
- Consumes: `repo_identity`, `read_product_baseline`, `relation_to_golden` from `status_live`.
- Consumes: `qualification_for_sha`, `evidence_details_for_sha` from `status_evidence`.
- Consumes: `derive_blockers`, `make_gate`, `validate_status_model` from `status_model`.
- Produces: `build_live_status(agent_root: Path, firmware_root: Path, data_root: Path, *, now: datetime | None = None) -> dict`
- Produces: `build_live_evidence(agent_root: Path, firmware_root: Path, data_root: Path) -> dict`

- [ ] **Step 1: Write service tests for complete and missing sources**

Use temporary Git repos for both Agent and firmware. Write a strict `CURRENT_PRODUCT_BASELINE.md` into firmware before committing it.

```python
class StatusServiceTests(unittest.TestCase):
    def test_live_status_reports_match_and_unknown_evidence_without_guessing(self):
        # Create agent + firmware repositories and empty evidence dataset.
        model = build_live_status(agent, firmware, data_root, now=fixed_now)
        self.assertEqual(model["mode"], "LIVE")
        self.assertEqual(model["identity"]["relation_to_golden"], "MATCH")
        self.assertEqual(model["qualification"][-1]["status"], "GOLDEN")
        build = next(x for x in model["qualification"] if x["gate"] == "build")
        self.assertEqual(build["status"], "UNKNOWN")
        self.assertTrue(any(x["category"] == "UNKNOWN_EVIDENCE" for x in model["blockers"]))

    def test_missing_agent_is_degraded_but_does_not_fallback_to_fake_live_identity(self):
        model = build_live_status(Path("missing-agent"), firmware, data_root, now=fixed_now)
        self.assertEqual(model["mode"], "LIVE")
        self.assertEqual(model["health"], "DEGRADED")
        self.assertIsNone(model["control_plane"]["sha"])
        self.assertFalse(model["identity"]["control_plane_revision_known"])

    def test_missing_firmware_fails_closed(self):
        model = build_live_status(agent, Path("missing-fw"), data_root, now=fixed_now)
        self.assertEqual(model["health"], "DEGRADED")
        self.assertIsNone(model["execution_plane"]["sha"])
        self.assertEqual(model["identity"]["relation_to_golden"], "UNKNOWN")
        self.assertTrue(all(x["status"] != "PASS" for x in model["qualification"]))
```

Also test dirty firmware tree is reported but does not itself change a valid gate from PASS/GOLDEN to FAIL.

- [ ] **Step 2: Run service tests and confirm failure**

```bash
python -m unittest tests.test_status_service -v
```

Expected: import failure.

- [ ] **Step 3: Implement status composition**

The service should always return the same top-level keys:

```python
{
    "schema_version": "1.0",
    "mode": "LIVE",
    "generated_at": now.isoformat(),
    "health": "OK" | "DEGRADED",
    "control_plane": {...},
    "execution_plane": {...},
    "product_baseline": {...},
    "identity": {...},
    "qualification": [...],
    "blockers": [...],
    "freshness": {"status": "LIVE", "age_seconds": 0, "sources": [...]},
}
```

Rules:

1. Query Agent and firmware independently so one missing source does not erase the readable other source.
2. Product baseline comes only from firmware `CURRENT_PRODUCT_BASELINE.md`.
3. `source` gate is PASS only when current firmware SHA was actually resolved; evidence string is `git rev-parse HEAD` and SHA is the resolved execution SHA.
4. `production` gate is GOLDEN only when execution SHA exactly equals parsed GOLDEN SHA.
5. Build/Regression/Artifact/Flash/Board/HIL/Protection are provided by `qualification_for_sha()` and remain UNKNOWN without exact records.
6. `health` is `DEGRADED` when required identity/baseline parsing fails, any identity is mismatched, or source availability is incomplete. UNKNOWN qualification alone does not falsely become system FAIL.
7. Run `validate_status_model(model)` before returning.

- [ ] **Step 4: Run service tests**

```bash
python -m unittest tests.test_status_service -v
```

Expected: PASS.

- [ ] **Step 5: Run Tasks 1–4 tests together**

```bash
python -m unittest tests.test_status_model tests.test_status_live tests.test_status_evidence tests.test_status_service -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add workbench/status_service.py tests/test_status_service.py
git commit -m "feat: compose ASR5K live engineering status"
```

---

### Task 5: Expose read-only local status APIs

**Files:**
- Modify: `server.py`
- Create: `tests/test_status_api.py`

**Interfaces:**
- Consumes: `build_live_status()` and `build_live_evidence()`.
- Produces HTTP GET: `/api/status/summary`
- Produces HTTP GET: `/api/status/evidence`
- Backend-only configuration:
  - `ASR5K_AGENT_ROOT`, default `ROOT.parent / "ASR5K_AGENT"`
  - `ASR5K_FIRMWARE_ROOT`, default `ROOT.parent / "ASR5K_v2_28384"`
- Browser cannot override either path by query string or request body.

- [ ] **Step 1: Write API tests before routes exist**

Follow the existing `ThreadingHTTPServer` integration-test pattern:

```python
from http.server import ThreadingHTTPServer
import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from server import WorkbenchHandler


class StatusApiTests(unittest.TestCase):
    def test_summary_route_is_json_and_read_only(self):
        with patch.dict(os.environ, {
            "ASR5K_AGENT_ROOT": str(self.agent),
            "ASR5K_FIRMWARE_ROOT": str(self.firmware),
        }, clear=False):
            server = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                with urlopen(f"http://{host}:{port}/api/status/summary", timeout=3) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["mode"], "LIVE")
                self.assertIn("execution_plane", payload)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
```

Add tests verifying a query such as `/api/status/summary?firmware_root=C:\other` does not alter configured roots and POST `/api/status/summary` remains unsupported.

- [ ] **Step 2: Run API test and confirm 404**

```bash
python -m unittest tests.test_status_api -v
```

Expected: FAIL because route returns 404.

- [ ] **Step 3: Add environment-only root resolution and GET routes**

At module scope:

```python
AGENT_ROOT = Path(os.environ.get("ASR5K_AGENT_ROOT", ROOT.parent / "ASR5K_AGENT")).expanduser().resolve()
FIRMWARE_ROOT = Path(os.environ.get("ASR5K_FIRMWARE_ROOT", ROOT.parent / "ASR5K_v2_28384")).expanduser().resolve()
```

Prefer resolving these inside a helper called per request so tests can patch environment safely:

```python
def _status_roots() -> tuple[Path, Path]:
    agent = Path(os.environ.get("ASR5K_AGENT_ROOT", ROOT.parent / "ASR5K_AGENT")).expanduser().resolve()
    firmware = Path(os.environ.get("ASR5K_FIRMWARE_ROOT", ROOT.parent / "ASR5K_v2_28384")).expanduser().resolve()
    return agent, firmware
```

In `do_GET()` before generic static fallback:

```python
if self.path.split("?", 1)[0] == "/api/status/summary":
    agent, firmware = _status_roots()
    return self._json(200, build_live_status(agent, firmware, ENGINEERING_DATA))
if self.path.split("?", 1)[0] == "/api/status/evidence":
    agent, firmware = _status_roots()
    return self._json(200, build_live_evidence(agent, firmware, ENGINEERING_DATA))
```

Do not add POST status routes.

- [ ] **Step 4: Run API and existing server tests**

```bash
python -m unittest tests.test_status_api tests.test_final_integration -v
```

Expected: PASS.

- [ ] **Step 5: Compile server and status modules**

```bash
python -m py_compile server.py workbench/status_*.py tests/test_status_*.py
```

Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_status_api.py
git commit -m "feat: expose read only ASR5K status API"
```

---

### Task 6: Generate and validate a sanitized public SNAPSHOT

**Files:**
- Create: `workbench/status_snapshot.py`
- Create: `tools/generate_status_snapshot.py`
- Create: `tests/test_status_snapshot.py`
- Create/generated: `engineering_data/status/status_snapshot.json`
- Modify: `engineering_data/index.json`
- Modify: `tests/test_engineering_data.py`

**Interfaces:**
- Consumes: `build_live_status()` only in the operator-side generator.
- Produces: `sanitize_public_status(model: dict, *, generated_at: str) -> dict`
- Produces: `load_snapshot(path: Path, *, now: datetime, stale_after_seconds: int) -> dict`
- CLI:

```text
python tools/generate_status_snapshot.py \
  --agent-root ../ASR5K_AGENT \
  --firmware-root ../ASR5K_v2_28384 \
  --output engineering_data/status/status_snapshot.json
```

- [ ] **Step 1: Write sanitization and stale tests**

```python
class StatusSnapshotTests(unittest.TestCase):
    def test_public_snapshot_removes_local_only_fields(self):
        live = self.sample_live_model()
        live["control_plane"]["path"] = "C:/secret/ASR5K_AGENT"
        live["execution_plane"]["path"] = "C:/secret/ASR5K_v2_28384"
        live["execution_plane"]["dirty"] = True
        public = sanitize_public_status(live, generated_at="2026-09-12T10:00:00Z")
        self.assertEqual(public["mode"], "SNAPSHOT")
        self.assertNotIn("path", public["control_plane"])
        self.assertNotIn("path", public["execution_plane"])
        self.assertIsNone(public["execution_plane"]["dirty"])

    def test_snapshot_loader_marks_old_data_stale_without_erasing_historical_rows(self):
        # Write snapshot generated two hours earlier and use 1-hour threshold.
        loaded = load_snapshot(path, now=fixed_now, stale_after_seconds=3600)
        self.assertEqual(loaded["freshness"]["status"], "STALE")
        self.assertTrue(any(x["category"] == "STALE_SOURCE" for x in loaded["blockers"]))

    def test_snapshot_rejects_authoritative_claim(self):
        payload = self.sample_snapshot()
        payload["authoritative_engineering_truth"] = True
        with self.assertRaises(ValueError):
            validate_public_snapshot(payload)
```

Also test snapshot source SHAs remain present while local absolute paths and secrets do not.

- [ ] **Step 2: Run snapshot tests and confirm import failure**

```bash
python -m unittest tests.test_status_snapshot -v
```

Expected: FAIL.

- [ ] **Step 3: Implement public sanitization and loader**

The public snapshot must include:

```python
{
    **normalized_status,
    "mode": "SNAPSHOT",
    "authoritative_engineering_truth": False,
    "generated_at": explicit_generation_time,
}
```

Strip recursively any keys named:

```text
path
local_path
workspace
secret
token
```

Set `execution_plane.dirty` to `None` because the public artifact describes the generated snapshot, not the current local working tree.

`load_snapshot()` recalculates freshness from `generated_at`; it may change top-level freshness to STALE, but must not rewrite historical evidence rows to current PASS.

- [ ] **Step 4: Implement explicit generator CLI**

`tools/generate_status_snapshot.py` should:

1. parse `--agent-root`, `--firmware-root`, `--output`;
2. resolve all paths;
3. call `build_live_status()` read-only;
4. call `sanitize_public_status()`;
5. write JSON with sorted keys, two-space indentation, final newline;
6. print output path, Agent SHA, firmware SHA, mode, and health;
7. never commit, push, fetch, build, flash, or run HIL.

- [ ] **Step 5: Generate the checked-in snapshot deliberately**

Run from a machine with both sibling private repositories available:

```bash
python tools/generate_status_snapshot.py --agent-root ../ASR5K_AGENT --firmware-root ../ASR5K_v2_28384 --output engineering_data/status/status_snapshot.json
```

If either private repo is unavailable, do **not** fabricate a current snapshot. Instead generate from known readable local sources only if the command returns a DEGRADED snapshot that visibly carries `UNKNOWN` fields; review the output before committing.

- [ ] **Step 6: Register the resource in `engineering_data/index.json`**

Add exactly:

```json
"status_snapshot": "status/status_snapshot.json"
```

under `resources`. Do not change `authoritative_engineering_truth`, `snapshot_baseline_is_current`, or other existing authority policy values.

- [ ] **Step 7: Extend engineering-data integrity tests**

Add assertions that:

```python
snapshot = load_json("status/status_snapshot.json")
self.assertFalse(snapshot["authoritative_engineering_truth"])
self.assertIn(snapshot["mode"], {"SNAPSHOT"})
self.assertNotIn("path", snapshot["execution_plane"])
```

- [ ] **Step 8: Run snapshot/data tests**

```bash
python -m unittest tests.test_status_snapshot tests.test_engineering_data -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add workbench/status_snapshot.py tools/generate_status_snapshot.py tests/test_status_snapshot.py tests/test_engineering_data.py engineering_data/index.json engineering_data/status/status_snapshot.json
git commit -m "feat: add sanitized ASR5K status snapshot"
```

---

### Task 7: Make ASR5K Status the landing UI without duplicating truth logic

**Files:**
- Create: `static/eng/status_console.js`
- Modify: `static/index.html`
- Modify: `static/eng/loader.js`
- Modify: `static/styles.css`
- Modify: `static/i18n.js`
- Create: `tests/test_status_frontend.py`

**Interfaces:**
- Browser first tries: `GET /api/status/summary`
- On network/404 failure only, browser loads: `../engineering_data/status/status_snapshot.json`
- Produces DOM population for IDs prefixed `status-`.
- Frontend does not decide PASS/GOLDEN from raw evidence; it renders the already normalized backend/snapshot model.

- [ ] **Step 1: Add failing static frontend contract tests**

Create tests that read source files and assert the intended information architecture:

```python
class StatusFrontendTests(unittest.TestCase):
    def test_status_is_default_panel_and_tools_remain_present(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-panel="status"', html)
        self.assertIn('id="status" class="panel active"', html)
        self.assertIn('data-panel="measurement"', html)
        self.assertIn('data-panel="control"', html)
        self.assertIn('data-panel="state"', html)

    def test_status_loader_has_explicit_live_then_snapshot_fallback(self):
        js = (ROOT / "static" / "eng" / "status_console.js").read_text(encoding="utf-8")
        self.assertIn("/api/status/summary", js)
        self.assertIn("../engineering_data/status/status_snapshot.json", js)
        self.assertIn("SNAPSHOT", js)
        self.assertNotIn("ASR5K_READ_TOKEN", js)

    def test_remote_is_not_primary_nav(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        primary = html.split('id="engineering-tools"', 1)[0]
        self.assertNotIn('data-panel="remote"', primary)
```

- [ ] **Step 2: Run and confirm failure**

```bash
python -m unittest tests.test_status_frontend -v
```

Expected: FAIL because the status landing markup/module does not exist.

- [ ] **Step 3: Add Status nav and five-section landing skeleton to `static/index.html`**

Before existing tool buttons, add:

```html
<div class="nav-group-label" data-i18n="nav.statusGroup">ASR5K STATUS</div>
<button class="nav active" data-panel="status" data-i18n="nav.status">Overview</button>
<button class="nav" data-panel="status-qualification" data-i18n="nav.qualification">Qualification</button>
<button class="nav" data-panel="status-evidence" data-i18n="nav.evidence">Evidence</button>
<button class="nav" data-panel="status-changes" data-i18n="nav.changes">Changes</button>
<div id="engineering-tools" class="nav-group-label" data-i18n="nav.toolsGroup">ENGINEERING TOOLS</div>
```

Remove `active` from Measurement. Move the remote button below Engineering Tools and label it `Demo / Mock Remote`, or omit its nav button while retaining the panel code for compatibility.

Add a default status panel with stable mount points:

```html
<section id="status" class="panel active">
  <div class="panel-head">
    <div><div class="eyebrow">IDENTITY → EVIDENCE → TRUST</div><h2>ASR5K Engineering Status</h2></div>
    <span id="status-mode" class="badge">LOADING</span>
  </div>
  <div id="status-alert"></div>
  <div id="status-baseline" class="status-baseline-grid"></div>
  <div id="status-gates" class="status-gate-grid"></div>
  <div class="grid two">
    <div class="card"><h3>Blockers / Unknowns</h3><div id="status-blockers"></div></div>
    <div class="card"><h3>Source Identity / Data Health</h3><div id="status-sources"></div></div>
  </div>
</section>
<section id="status-qualification" class="panel"><div id="status-qualification-body"></div></section>
<section id="status-evidence" class="panel"><div id="status-evidence-body"></div></section>
<section id="status-changes" class="panel"><div id="status-changes-body"></div></section>
```

- [ ] **Step 4: Load the new renderer first in `static/eng/loader.js`**

Change source order to:

```javascript
const sources = [
  './eng/common.js',
  './eng/status_console.js',
  './eng/data_source.js',
  './eng/profiles.js',
  './eng/control_sfra.js',
  './eng/system_tools.js'
];
```

- [ ] **Step 5: Implement renderer with no status inference**

`static/eng/status_console.js` should contain:

```javascript
(() => {
  'use strict';
  const D = window.DPWE;
  if (!D) return;

  const esc = value => String(value ?? '—')
    .replaceAll('&','&amp;').replaceAll('<','&lt;')
    .replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');

  const cls = status => ({
    PASS:'status-ok', GOLDEN:'status-ok',
    FAIL:'status-fail', MISMATCH:'status-fail',
    PENDING:'status-warn', STALE:'status-warn',
    UNKNOWN:'status-unknown', NOT_RUN:'status-unknown', NOT_REQUIRED:'status-neutral'
  }[String(status || '').toUpperCase()] || 'status-unknown');

  async function loadModel() {
    try {
      const response = await fetch('/api/status/summary', {cache:'no-store'});
      if (!response.ok) throw new Error(`status API HTTP ${response.status}`);
      return await response.json();
    } catch (liveError) {
      const response = await fetch('../engineering_data/status/status_snapshot.json', {cache:'no-store'});
      if (!response.ok) throw new Error(`snapshot HTTP ${response.status}`);
      const model = await response.json();
      model.mode = 'SNAPSHOT';
      return model;
    }
  }
```

Render status exactly as supplied. For example, a gate row displays `gate.status`; it must never turn UNKNOWN into PASS based on the presence of an evidence filename.

Evidence and Changes views may reuse the summary payload in V1. If `/api/status/evidence` is available in LIVE mode, load it on first opening Evidence; otherwise show the snapshot evidence references included in the summary.

- [ ] **Step 6: Add status styling and navigation grouping**

Add CSS classes using existing CSS variables only, for example:

```css
.nav-group-label{margin:18px 12px 7px;color:var(--muted);font-size:10px;letter-spacing:.16em;font-weight:800}
.status-baseline-grid,.status-gate-grid{display:grid;gap:12px;margin-bottom:18px}
.status-baseline-grid{grid-template-columns:repeat(4,minmax(0,1fr))}
.status-gate-grid{grid-template-columns:repeat(5,minmax(120px,1fr))}
.status-gate{border:1px solid var(--line);border-radius:12px;padding:14px;background:#0d151d}
.status-ok{border-color:#285e55}.status-fail{border-color:#74343e}.status-warn{border-color:#6a5725}.status-unknown{border-color:#465463}
```

Add responsive rules so status grids collapse on smaller widths.

- [ ] **Step 7: Add i18n keys for new status/navigation labels**

Add `nav.statusGroup`, `nav.status`, `nav.qualification`, `nav.evidence`, `nav.changes`, and `nav.toolsGroup` in both languages. Do not translate SHA, gate-state tokens, repository names, or evidence IDs.

- [ ] **Step 8: Run frontend contract and JavaScript syntax checks**

```bash
python -m unittest tests.test_status_frontend -v
node --check static/eng/status_console.js
node --check static/eng/loader.js
node --check static/app.js
node --check static/i18n.js
```

Expected: PASS / exit 0.

- [ ] **Step 9: Commit**

```bash
git add static/index.html static/eng/status_console.js static/eng/loader.js static/styles.css static/i18n.js tests/test_status_frontend.py
git commit -m "feat: make ASR5K status the Workbench landing view"
```

---

### Task 8: Finish integration, documentation, and full regression verification

**Files:**
- Modify: `tests/test_final_integration.py`
- Modify: `README.md`
- Modify: `docs/CURRENT_STATUS.md`

**Interfaces:**
- Consumes all previous tasks.
- Produces one documented operator flow for local LIVE and public SNAPSHOT modes.

- [ ] **Step 1: Extend final integration tests before documentation changes**

Add assertions covering the full boundary:

```python
def test_status_console_is_primary_view_and_remains_view_only(self):
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    status_js = (ROOT / "static" / "eng" / "status_console.js").read_text(encoding="utf-8")
    snapshot = json.loads((ROOT / "engineering_data" / "status" / "status_snapshot.json").read_text(encoding="utf-8"))

    self.assertIn('id="status" class="panel active"', html)
    self.assertFalse(snapshot["authoritative_engineering_truth"])
    self.assertNotIn("ASR5K_READ_TOKEN", status_js)
    self.assertNotIn("qualification-ready", status_js)
    self.assertNotIn("flash", status_js.lower().split("fetch(")[0])
```

Also assert old engineering tools are present and status snapshot is listed by `engineering_data/index.json`.

- [ ] **Step 2: Run final integration test and fix only task-owned integration defects**

```bash
python -m unittest tests.test_final_integration -v
```

Expected: PASS after the integration assertions match the implemented UI/data contract.

- [ ] **Step 3: Rewrite README opening around the new daily workflow**

The first operational section should state:

```text
ASR5K Engineering Console answers:
- what firmware SHA is being viewed;
- what the GOLDEN SHA is;
- whether current source is MATCH/AHEAD/DIVERGED/UNKNOWN;
- what exact-SHA evidence exists per gate;
- what remains FAIL/PENDING/UNKNOWN/STALE.
```

Document local mode:

```powershell
$env:ASR5K_AGENT_ROOT="C:\path\to\ASR5K_AGENT"
$env:ASR5K_FIRMWARE_ROOT="C:\path\to\ASR5K_v2_28384"
python server.py
```

Then open `http://localhost:8000` and expect `LIVE` in the status badge.

Document Pages behavior as `SNAPSHOT`, never LIVE.

Keep the existing authority hierarchy and engineering-tool documentation, but move it after the status-console introduction.

- [ ] **Step 4: Update `docs/CURRENT_STATUS.md`**

Record that Workbench now has a dashboard-first UI while preserving this statement verbatim in meaning:

```text
ASR5K_AGENT = Control / Knowledge Plane
ASR5K_v2_28384 = Execution Plane
Workbench = View / Analysis Plane
```

State that the dashboard may show UNKNOWN for gates even when a human remembers a successful run; that is expected until exact evidence is imported/bound.

- [ ] **Step 5: Run the full Python regression suite**

```bash
python -m unittest discover -s tests -v
```

Expected: all tests PASS.

- [ ] **Step 6: Run Python compile checks**

```bash
python -m py_compile server.py workbench/*.py tools/*.py tests/*.py
```

Expected: exit 0.

- [ ] **Step 7: Run all JavaScript syntax checks, including the new module**

```bash
node --check static/app.js
node --check static/i18n.js
node --check static/eng/loader.js
node --check static/eng/common.js
node --check static/eng/status_console.js
node --check static/eng/data_source.js
node --check static/eng/profiles.js
node --check static/eng/control_sfra.js
node --check static/eng/system_tools.js
```

Expected: every command exits 0.

- [ ] **Step 8: Run a local smoke test against real sibling repos without mutating them**

Before starting, record:

```bash
git -C ../ASR5K_AGENT rev-parse HEAD
git -C ../ASR5K_AGENT status --porcelain
git -C ../ASR5K_v2_28384 rev-parse HEAD
git -C ../ASR5K_v2_28384 status --porcelain
```

Start:

```bash
python server.py
```

Verify in the browser or with HTTP GET:

```text
/api/status/summary
```

Check that:

- mode is `LIVE`;
- firmware SHA equals `git -C ../ASR5K_v2_28384 rev-parse HEAD`;
- Agent SHA equals `git -C ../ASR5K_AGENT rev-parse HEAD`;
- parsed GOLDEN is sourced from `CURRENT_PRODUCT_BASELINE.md`;
- current-vs-GOLDEN relation is displayed;
- unknown qualification gates remain UNKNOWN;
- no status request changes either repository.

After the smoke test, rerun the four Git commands above and confirm HEAD/status are unchanged.

- [ ] **Step 9: Inspect generated public snapshot for accidental private data**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('engineering_data/status/status_snapshot.json').read_text(encoding='utf-8')
for forbidden in ['C:\\', '/Users/', '/home/', 'ASR5K_READ_TOKEN', 'token=', 'Authorization:']:
    assert forbidden not in text, forbidden
print('public snapshot sanitization scan: PASS')
PY
```

Expected: `public snapshot sanitization scan: PASS`.

- [ ] **Step 10: Commit final integration/docs**

```bash
git add tests/test_final_integration.py README.md docs/CURRENT_STATUS.md
git commit -m "docs: document ASR5K Engineering Console workflow"
```

- [ ] **Step 11: Verify branch diff is scoped before review**

```bash
git status --short
git log --oneline --decorate -10
git diff --stat design/asr5k-engineering-console...HEAD
```

Expected: clean working tree; changes are limited to status model/adapters/API/snapshot/UI/tests/docs; no ASR5K firmware or Agent repository mutation.

---

## Review Gates During Execution

Each task is independently reviewable. Reject a task if any of these occur:

- a PASS/GOLDEN status is inferred from file presence or prose rather than exact evidence;
- a different SHA's evidence is reused as current evidence;
- the browser gains access to a private token or filesystem path configuration;
- local status collection executes state-changing Git or hardware commands;
- Workbench starts claiming it owns qualification or Production truth;
- the existing engineering calculators become unavailable before the Status view is verified;
- public SNAPSHOT is visually represented as LIVE;
- one broad refactor mixes unrelated cleanup with the status-console change.

## Expected V1 Result

After all tasks pass, opening the local Workbench immediately answers:

```text
Mode             LIVE
Control Plane    ASR5K_AGENT @ <exact SHA>
Execution Plane  ASR5K_v2_28384 @ <exact SHA>
GOLDEN           <exact SHA from CURRENT_PRODUCT_BASELINE.md>
Relation         MATCH / AHEAD / DIVERGED / UNKNOWN
Qualification    source/build/regression/artifact/flash/board/HIL/protection/production
Blockers         FAIL/PENDING/MISMATCH/UNKNOWN separated by category
Freshness        LIVE with current query time
```

Opening GitHub Pages answers the same questions from the deliberately generated sanitized `SNAPSHOT`, with age/freshness visible and no private credential requirement.
