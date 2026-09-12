# ASR5K Engineering Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refocus Digital-Power-Engineering-Workbench into an ASR5K-first engineering status console that shows exact source identities, GOLDEN relation, evidence-typed qualification state, blockers, and freshness while preserving the existing engineering tools as secondary views.

**Architecture:** Keep all engineering truth outside the Workbench. A Python normalization layer builds one JSON-safe status model from read-only local repository inspection plus existing Workbench evidence ledgers; the local server exposes that model through a read-only API. A sanitized committed snapshot uses the same model contract for GitHub Pages, while the browser renders either source without changing status semantics.

**Tech Stack:** Python 3.10+ standard library, `unittest`, `http.server`, read-only Git CLI queries, vanilla HTML/CSS/JavaScript, Node syntax checks, existing `engineering_data/` JSON/JSONL contracts.

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
- `tests/test_status_model.py`
- `tests/test_status_live.py`
- `tests/test_status_evidence.py`
- `tests/test_status_service.py`
- `tests/test_status_api.py`
- `tests/test_status_snapshot.py`
- `tests/test_status_frontend.py`
- `engineering_data/status/status_snapshot.json` — generated, sanitized public status view.

### Modified files

- `server.py`
- `static/index.html`
- `static/eng/loader.js`
- `static/styles.css`
- `static/i18n.js`
- `engineering_data/index.json`
- `tests/test_engineering_data.py`
- `tests/test_final_integration.py`
- `README.md`
- `docs/CURRENT_STATUS.md`

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

- [ ] **Step 1: Write the failing policy tests**

Create `tests/test_status_model.py`:

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
        self.assertEqual(
            classify_freshness("2026-09-12T09:00:00+00:00", now, 3600),
            "STALE",
        )

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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify RED**

```bash
python -m unittest tests.test_status_model -v
```

Expected: import failure because `workbench.status_model` does not exist.

- [ ] **Step 3: Implement the complete minimal policy module**

Create `workbench/status_model.py`:

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
    if status in {"PASS", "FAIL", "GOLDEN"} and (not sha or not evidence):
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


def derive_blockers(model: dict) -> list[dict]:
    blockers: list[dict] = []
    for row in model.get("qualification", []):
        status = str(row.get("status", "UNKNOWN")).upper()
        if status == "FAIL":
            category = "PRODUCTION_BLOCKER" if row.get("gate") == "production" else "FIRMWARE_BLOCKER"
        elif status == "MISMATCH":
            category = "IDENTITY_MISMATCH"
        elif status == "PENDING":
            category = "QUALIFICATION_PENDING"
        elif status in {"UNKNOWN", "NOT_RUN"}:
            category = "UNKNOWN_EVIDENCE"
        elif status == "STALE":
            category = "STALE_SOURCE"
        else:
            continue
        blockers.append({
            "category": category,
            "gate": row.get("gate"),
            "status": status,
            "source": row.get("evidence"),
            "note": row.get("note"),
        })

    identity = model.get("identity", {})
    if identity.get("relation_to_golden") == "DIVERGED":
        blockers.append({"category": "IDENTITY_MISMATCH", "gate": "source", "status": "MISMATCH", "source": "git ancestry", "note": "execution SHA diverges from GOLDEN"})
    if model.get("freshness", {}).get("status") == "STALE":
        blockers.append({"category": "STALE_SOURCE", "gate": None, "status": "STALE", "source": "snapshot generated_at", "note": "snapshot freshness threshold exceeded"})
    return blockers


def validate_status_model(model: dict) -> None:
    execution_sha = model.get("execution_plane", {}).get("sha")
    mode = model.get("mode")
    if mode not in {"LIVE", "SNAPSHOT"}:
        raise ValueError(f"unsupported status mode: {mode}")
    for row in model.get("qualification", []):
        if row.get("gate") not in GATES:
            raise ValueError(f"unsupported qualification gate: {row.get('gate')}")
        if row.get("status") not in VALID_GATE_STATES:
            raise ValueError(f"unsupported gate status: {row.get('status')}")
        if row.get("status") in {"PASS", "FAIL", "GOLDEN"}:
            if not row.get("sha") or not row.get("evidence"):
                raise ValueError(f"{row.get('status')} requires exact evidence")
            if execution_sha and row.get("sha") != execution_sha:
                raise ValueError(f"{row.get('gate')} evidence does not match execution SHA")
        if row.get("status") == "GOLDEN" and row.get("gate") != "production":
            raise ValueError("GOLDEN is valid only for production")
```

- [ ] **Step 4: Run model tests**

```bash
python -m unittest tests.test_status_model -v
```

Expected: PASS.

- [ ] **Step 5: Run existing workbench tests**

```bash
python -m unittest tests.test_workbench -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add workbench/status_model.py tests/test_status_model.py
git commit -m "feat: add ASR5K status policy model"
```

---

### Task 2: Add read-only local identity and GOLDEN parsing

**Files:**
- Create: `workbench/status_live.py`
- Create: `tests/test_status_live.py`

**Interfaces:**
- Produces: `repo_identity(repo: Path) -> dict`
- Produces: `parse_product_baseline(text: str) -> dict`
- Produces: `read_product_baseline(firmware_root: Path) -> dict`
- Produces: `relation_to_golden(firmware_root: Path, current_sha: str, golden_sha: str) -> str`

- [ ] **Step 1: Write temporary Git repository tests**

```python
import subprocess
import tempfile
import unittest
from pathlib import Path

from workbench.status_live import parse_product_baseline, relation_to_golden, repo_identity


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True)
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

    def test_product_baseline_parser_requires_exact_fields(self):
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

Add tests for missing repo, malformed baseline text, and diverged history.

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_status_live -v
```

Expected: import failure.

- [ ] **Step 3: Implement read-only Git helpers and parser**

Create `workbench/status_live.py`:

```python
from __future__ import annotations

import re
import subprocess
from pathlib import Path

SHA_RE = re.compile(r"(?im)^FINAL / GOLDEN firmware SHA:\s*\n([0-9a-f]{40})\s*$")
REF_RE = re.compile(r"(?im)^Pinned release ref:\s*\n([^\s]+)\s*$")


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def repo_identity(repo: Path) -> dict:
    root = repo.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    top = _git(root, "rev-parse", "--show-toplevel").stdout.strip()
    sha = _git(root, "rev-parse", "HEAD").stdout.strip()
    branch = _git(root, "branch", "--show-current").stdout.strip() or "DETACHED"
    dirty = bool(_git(root, "status", "--porcelain").stdout.strip())
    return {"path": str(Path(top).resolve()), "sha": sha, "branch": branch, "dirty": dirty}


def parse_product_baseline(text: str) -> dict:
    sha_match = SHA_RE.search(text)
    ref_match = REF_RE.search(text)
    if not sha_match or not ref_match:
        raise ValueError("CURRENT_PRODUCT_BASELINE.md is missing exact GOLDEN SHA or release ref")
    return {
        "golden_sha": sha_match.group(1),
        "release_ref": ref_match.group(1),
        "source": "CURRENT_PRODUCT_BASELINE.md",
    }


def read_product_baseline(firmware_root: Path) -> dict:
    root = firmware_root.expanduser().resolve()
    source = (root / "CURRENT_PRODUCT_BASELINE.md").resolve()
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ValueError("baseline path escapes firmware root") from exc
    return parse_product_baseline(source.read_text(encoding="utf-8"))


def relation_to_golden(firmware_root: Path, current_sha: str, golden_sha: str) -> str:
    if current_sha == golden_sha:
        return "MATCH"
    try:
        object_check = _git(firmware_root, "cat-file", "-e", f"{golden_sha}^{{commit}}", check=False)
        if object_check.returncode != 0:
            return "UNKNOWN"
        ancestry = _git(firmware_root, "merge-base", "--is-ancestor", golden_sha, current_sha, check=False)
        return "AHEAD" if ancestry.returncode == 0 else "DIVERGED"
    except OSError:
        return "UNKNOWN"
```

Do not add any Git command beyond the read-only commands shown above.

- [ ] **Step 4: Run tests and compile check**

```bash
python -m unittest tests.test_status_live -v
python -m py_compile workbench/status_live.py tests/test_status_live.py
```

Expected: PASS / exit 0.

- [ ] **Step 5: Commit**

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
- Consumes: `GATES`, `make_gate()` from `workbench.status_model`.
- Produces: `read_jsonl(path: Path) -> list[dict]`
- Produces: `qualification_for_sha(data_root: Path, execution_sha: str, golden: dict) -> list[dict]`
- Produces: `evidence_details_for_sha(data_root: Path, execution_sha: str) -> list[dict]`

**V1 rule:** evidence upgrades a gate only when the record contains an explicit supported `gate` and exact matching execution SHA. Never infer a gate from `test_id`, requirement text, filename, or prose.

- [ ] **Step 1: Write exact-SHA evidence tests**

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
        (root / "evidence" / "evidence_ledger.jsonl").write_text(
            "\n".join(json.dumps(x) for x in [meta, *evidence_rows]) + "\n",
            encoding="utf-8",
        )
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

    def test_matching_explicit_gate_pass_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, [{
                "record_type": "evidence", "evidence_id": "EVD-1",
                "baseline": SHA, "gate": "build", "artifact_id": "cpu1.out",
                "test_id": "CPU1-BUILD", "result": "PASS",
                "timestamp_utc": "2026-09-12T10:00:00Z", "source_or_instrument": "CCS",
                "artifact_sha256": "1" * 64, "requirement_ids": ["REQ-BUILD-CPU1-001"],
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
                "timestamp_utc": "2026-09-01T10:00:00Z", "source_or_instrument": "CCS",
                "artifact_sha256": "2" * 64, "requirement_ids": ["REQ-BUILD-CPU1-001"],
                "run_id": "RUN-OLD"
            }])
            gates = {x["gate"]: x for x in qualification_for_sha(root, SHA, {"golden_sha": OTHER, "source": "baseline.md"})}
            self.assertEqual(gates["build"]["status"], "UNKNOWN")

    def test_matching_golden_sets_only_production_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, [])
            gates = {x["gate"]: x for x in qualification_for_sha(root, SHA, {
                "golden_sha": SHA, "source": "CURRENT_PRODUCT_BASELINE.md", "release_ref": "release/final"
            })}
            self.assertEqual(gates["production"]["status"], "GOLDEN")
            self.assertEqual(gates["board"]["status"], "UNKNOWN")
```

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_status_evidence -v
```

Expected: import failure.

- [ ] **Step 3: Implement conservative evidence normalization**

Create `workbench/status_evidence.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from .status_model import GATES, make_gate

RESULT_MAP = {
    "PASS": "PASS",
    "FAIL": "FAIL",
    "BLOCKED": "PENDING",
    "INCONCLUSIVE": "PENDING",
    "MEASURED": "PENDING",
}


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
    return rows


def _json(path: Path) -> dict:
    if not path.exists():
        return {"records": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _record_gate(row: dict, sha_field: str, execution_sha: str, evidence_id: str) -> dict | None:
    gate = str(row.get("gate", "")).lower()
    result = str(row.get("result", "")).upper()
    if gate not in GATES or row.get(sha_field) != execution_sha or result not in RESULT_MAP:
        return None
    status = RESULT_MAP[result]
    return make_gate(
        gate,
        status,
        sha=execution_sha if status in {"PASS", "FAIL"} else execution_sha,
        evidence=evidence_id if status in {"PASS", "FAIL"} else evidence_id,
        evidence_type=row.get("record_type", "evidence"),
        timestamp=row.get("timestamp_utc") or row.get("timestamp"),
        note=None if status in {"PASS", "FAIL"} else f"source result: {result}",
    )


def evidence_details_for_sha(data_root: Path, execution_sha: str) -> list[dict]:
    details: list[dict] = []
    for row in read_jsonl(data_root / "evidence" / "evidence_ledger.jsonl"):
        if row.get("record_type") == "evidence" and row.get("baseline") == execution_sha:
            details.append(dict(row))
    for row in _json(data_root / "verification" / "regression_history" / "index.json").get("records", []):
        if row.get("commit") == execution_sha:
            details.append(dict(row, record_type="regression"))
    for row in _json(data_root / "verification" / "hardware_results" / "index.json").get("records", []):
        if row.get("dut_commit") == execution_sha:
            details.append(dict(row, record_type="hardware"))
    return details


def qualification_for_sha(data_root: Path, execution_sha: str, golden: dict) -> list[dict]:
    by_gate = {gate: make_gate(gate, "UNKNOWN") for gate in GATES}

    ledger = read_jsonl(data_root / "evidence" / "evidence_ledger.jsonl")
    for row in ledger:
        if row.get("record_type") != "evidence":
            continue
        normalized = _record_gate(row, "baseline", execution_sha, str(row.get("evidence_id", "evidence")))
        if normalized:
            by_gate[normalized["gate"]] = normalized

    regression = _json(data_root / "verification" / "regression_history" / "index.json")
    for index, row in enumerate(regression.get("records", [])):
        normalized = _record_gate(row, "commit", execution_sha, str(row.get("artifact_or_log") or f"regression:{index}"))
        if normalized:
            by_gate[normalized["gate"]] = normalized

    hardware = _json(data_root / "verification" / "hardware_results" / "index.json")
    for index, row in enumerate(hardware.get("records", [])):
        normalized = _record_gate(row, "dut_commit", execution_sha, str(row.get("evidence") or f"hardware:{index}"))
        if normalized:
            by_gate[normalized["gate"]] = normalized

    if golden.get("golden_sha") == execution_sha:
        by_gate["production"] = make_gate(
            "production", "GOLDEN", sha=execution_sha,
            evidence=str(golden.get("source") or "CURRENT_PRODUCT_BASELINE.md"),
            evidence_type="product_baseline",
            note=golden.get("release_ref"),
        )
    return [by_gate[gate] for gate in GATES]
```

Important: `_record_gate()` must not promote a row that lacks explicit `gate`, and records for other SHAs remain historical detail only.

- [ ] **Step 4: Run evidence tests and existing importer test**

```bash
python -m unittest tests.test_status_evidence -v
python -m unittest tests.test_engineering_os.EngineeringOsAutomationTest.test_pass_evidence_requires_hash_run_and_requirement -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add workbench/status_evidence.py tests/test_status_evidence.py
git commit -m "feat: normalize exact SHA qualification evidence"
```

---

### Task 4: Compose LIVE status and detailed evidence views

**Files:**
- Create: `workbench/status_service.py`
- Create: `tests/test_status_service.py`

**Interfaces:**
- Consumes: `repo_identity`, `read_product_baseline`, `relation_to_golden`.
- Consumes: `qualification_for_sha`, `evidence_details_for_sha`.
- Consumes: `derive_blockers`, `make_gate`, `validate_status_model`.
- Produces: `build_live_status(agent_root: Path, firmware_root: Path, data_root: Path, *, now: datetime | None = None) -> dict`
- Produces: `build_live_evidence(agent_root: Path, firmware_root: Path, data_root: Path) -> dict`

- [ ] **Step 1: Write complete/missing-source tests**

Test these cases with temporary Git repos:

```python
model = build_live_status(agent, firmware, data_root, now=fixed_now)
self.assertEqual(model["mode"], "LIVE")
self.assertEqual(model["identity"]["relation_to_golden"], "MATCH")
self.assertEqual(next(x for x in model["qualification"] if x["gate"] == "production")["status"], "GOLDEN")
self.assertEqual(next(x for x in model["qualification"] if x["gate"] == "build")["status"], "UNKNOWN")
```

Also assert:

```python
missing_agent_model["health"] == "DEGRADED"
missing_agent_model["control_plane"]["sha"] is None
missing_firmware_model["identity"]["relation_to_golden"] == "UNKNOWN"
dirty_firmware_model["execution_plane"]["dirty"] is True
```

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_status_service -v
```

Expected: import failure.

- [ ] **Step 3: Implement service composition**

Create `workbench/status_service.py` around this exact control flow:

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .status_evidence import evidence_details_for_sha, qualification_for_sha
from .status_live import read_product_baseline, relation_to_golden, repo_identity
from .status_model import derive_blockers, make_gate, validate_status_model

CONTROL_REPO = "linwuyen/ASR5K_AGENT"
EXECUTION_REPO = "linwuyen/ASR5K_v2_28384"


def _unknown_repo(repository: str) -> dict:
    return {"repository": repository, "sha": None, "branch": None, "dirty": None, "status": "UNAVAILABLE"}


def build_live_status(agent_root: Path, firmware_root: Path, data_root: Path, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    health = "OK"

    try:
        agent = {"repository": CONTROL_REPO, **repo_identity(agent_root), "status": "CURRENT"}
    except (OSError, RuntimeError, FileNotFoundError, ValueError):
        agent = _unknown_repo(CONTROL_REPO)
        health = "DEGRADED"

    try:
        firmware = {"repository": EXECUTION_REPO, **repo_identity(firmware_root), "status": "CURRENT"}
    except (OSError, RuntimeError, FileNotFoundError, ValueError):
        firmware = _unknown_repo(EXECUTION_REPO)
        health = "DEGRADED"

    golden = {"golden_sha": None, "release_ref": None, "source": "CURRENT_PRODUCT_BASELINE.md"}
    if firmware.get("sha"):
        try:
            golden = read_product_baseline(firmware_root)
        except (OSError, ValueError):
            health = "DEGRADED"

    relation = "UNKNOWN"
    if firmware.get("sha") and golden.get("golden_sha"):
        relation = relation_to_golden(firmware_root, firmware["sha"], golden["golden_sha"])
        if relation in {"DIVERGED", "UNKNOWN"}:
            health = "DEGRADED"

    if firmware.get("sha"):
        qualification = qualification_for_sha(data_root, firmware["sha"], golden)
        qualification[0] = make_gate(
            "source", "PASS", sha=firmware["sha"], evidence="git rev-parse HEAD",
            evidence_type="git_identity", timestamp=now.isoformat()
        )
    else:
        qualification = [make_gate(gate, "UNKNOWN") for gate in (
            "source", "build", "regression", "artifact", "flash", "board", "hil", "protection", "production"
        )]

    model = {
        "schema_version": "1.0",
        "mode": "LIVE",
        "generated_at": now.isoformat(),
        "health": health,
        "control_plane": agent,
        "execution_plane": firmware,
        "product_baseline": golden,
        "identity": {
            "relation_to_golden": relation,
            "evidence_sha_match": all(
                x.get("sha") in {None, firmware.get("sha")}
                for x in qualification
                if x.get("status") in {"PASS", "FAIL", "GOLDEN"}
            ),
            "control_plane_revision_known": bool(agent.get("sha")),
        },
        "qualification": qualification,
        "blockers": [],
        "freshness": {
            "status": "LIVE",
            "age_seconds": 0,
            "sources": [
                {"repository": CONTROL_REPO, "available": bool(agent.get("sha"))},
                {"repository": EXECUTION_REPO, "available": bool(firmware.get("sha"))},
            ],
        },
    }
    model["blockers"] = derive_blockers(model)
    validate_status_model(model)
    return model


def build_live_evidence(agent_root: Path, firmware_root: Path, data_root: Path) -> dict:
    status = build_live_status(agent_root, firmware_root, data_root)
    sha = status.get("execution_plane", {}).get("sha")
    return {
        "schema_version": "1.0",
        "mode": "LIVE",
        "execution_sha": sha,
        "control_plane_sha": status.get("control_plane", {}).get("sha"),
        "records": evidence_details_for_sha(data_root, sha) if sha else [],
    }
```

The service deliberately reports readable sources independently: missing Agent does not erase firmware identity, and missing firmware prevents PASS/GOLDEN qualification claims.

- [ ] **Step 4: Run service tests and cumulative unit tests**

```bash
python -m unittest tests.test_status_service -v
python -m unittest tests.test_status_model tests.test_status_live tests.test_status_evidence tests.test_status_service -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

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
- GET `/api/status/summary`
- GET `/api/status/evidence`
- Backend config only:
  - `ASR5K_AGENT_ROOT`, default `ROOT.parent / "ASR5K_AGENT"`
  - `ASR5K_FIRMWARE_ROOT`, default `ROOT.parent / "ASR5K_v2_28384"`

- [ ] **Step 1: Write API tests before adding routes**

Follow `tests/test_final_integration.py`'s `ThreadingHTTPServer` pattern. Verify:

```python
payload["mode"] == "LIVE"
"execution_plane" in payload
```

Also request `/api/status/summary?firmware_root=C:\\other` and verify the payload still uses the environment-configured repo. POST `/api/status/summary` must not become a status write route.

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_status_api -v
```

Expected: 404 for the new route.

- [ ] **Step 3: Add backend-only root helper and routes**

Add imports:

```python
from workbench.status_service import build_live_evidence, build_live_status
```

Add helper:

```python
def _status_roots() -> tuple[Path, Path]:
    agent = Path(os.environ.get("ASR5K_AGENT_ROOT", ROOT.parent / "ASR5K_AGENT")).expanduser().resolve()
    firmware = Path(os.environ.get("ASR5K_FIRMWARE_ROOT", ROOT.parent / "ASR5K_v2_28384")).expanduser().resolve()
    return agent, firmware
```

Add at the start of `do_GET()` after `_serve_engineering_data()`:

```python
route = urlsplit(self.path).path
if route == "/api/status/summary":
    agent, firmware = _status_roots()
    return self._json(200, build_live_status(agent, firmware, ENGINEERING_DATA))
if route == "/api/status/evidence":
    agent, firmware = _status_roots()
    return self._json(200, build_live_evidence(agent, firmware, ENGINEERING_DATA))
```

Do not add status handling to `do_POST()`.

- [ ] **Step 4: Run API/integration/compile tests**

```bash
python -m unittest tests.test_status_api tests.test_final_integration -v
python -m py_compile server.py workbench/status_*.py tests/test_status_*.py
```

Expected: PASS / exit 0.

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_status_api.py
git commit -m "feat: expose read only ASR5K status API"
```

---

### Task 6: Generate and validate sanitized public SNAPSHOT mode

**Files:**
- Create: `workbench/status_snapshot.py`
- Create: `tools/generate_status_snapshot.py`
- Create: `tests/test_status_snapshot.py`
- Create/generated: `engineering_data/status/status_snapshot.json`
- Modify: `engineering_data/index.json`
- Modify: `tests/test_engineering_data.py`

**Interfaces:**
- Produces: `sanitize_public_status(model: dict, *, generated_at: str) -> dict`
- Produces: `validate_public_snapshot(model: dict) -> None`
- Produces: `load_snapshot(path: Path, *, now: datetime, stale_after_seconds: int) -> dict`
- CLI:

```text
python tools/generate_status_snapshot.py --agent-root ../ASR5K_AGENT --firmware-root ../ASR5K_v2_28384 --output engineering_data/status/status_snapshot.json
```

- [ ] **Step 1: Write sanitization/staleness tests**

Test:

```python
public = sanitize_public_status(live, generated_at="2026-09-12T10:00:00Z")
self.assertEqual(public["mode"], "SNAPSHOT")
self.assertFalse(public["authoritative_engineering_truth"])
self.assertNotIn("path", public["control_plane"])
self.assertNotIn("path", public["execution_plane"])
self.assertIsNone(public["execution_plane"]["dirty"])
```

Test a two-hour-old snapshot against a one-hour threshold and expect `freshness.status == "STALE"` plus `STALE_SOURCE` blocker. Test `validate_public_snapshot()` rejects `authoritative_engineering_truth=True`.

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_status_snapshot -v
```

Expected: import failure.

- [ ] **Step 3: Implement sanitizer, validator, and loader**

Create `workbench/status_snapshot.py`:

```python
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

from .status_model import classify_freshness, derive_blockers, validate_status_model

FORBIDDEN_KEYS = {"path", "local_path", "workspace", "secret", "token"}


def _strip(value):
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k.lower() not in FORBIDDEN_KEYS}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


def sanitize_public_status(model: dict, *, generated_at: str) -> dict:
    public = _strip(deepcopy(model))
    public["mode"] = "SNAPSHOT"
    public["generated_at"] = generated_at
    public["authoritative_engineering_truth"] = False
    public.setdefault("execution_plane", {})["dirty"] = None
    public.setdefault("freshness", {})["status"] = "SNAPSHOT"
    public["freshness"]["age_seconds"] = 0
    validate_public_snapshot(public)
    return public


def validate_public_snapshot(model: dict) -> None:
    if model.get("mode") != "SNAPSHOT":
        raise ValueError("public status must be SNAPSHOT")
    if model.get("authoritative_engineering_truth") is not False:
        raise ValueError("public Workbench snapshot cannot claim authority")
    validate_status_model(model)


def load_snapshot(path: Path, *, now: datetime, stale_after_seconds: int) -> dict:
    model = json.loads(path.read_text(encoding="utf-8"))
    validate_public_snapshot(model)
    generated = model.get("generated_at")
    freshness = classify_freshness(generated, now, stale_after_seconds)
    if freshness == "STALE":
        model["freshness"]["status"] = "STALE"
        generated_dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        model["freshness"]["age_seconds"] = int(max(0, (now - generated_dt).total_seconds()))
        model["blockers"] = derive_blockers(model)
    return model
```

- [ ] **Step 4: Implement explicit snapshot generator**

Create `tools/generate_status_snapshot.py` so it parses `--agent-root`, `--firmware-root`, and `--output`, calls `build_live_status()`, sanitizes with current UTC ISO timestamp, and writes sorted two-space JSON plus final newline. It must not call GitHub, build, flash, HIL, commit, or push.

Core body:

```python
model = build_live_status(agent_root, firmware_root, DATA_ROOT)
public = sanitize_public_status(model, generated_at=datetime.now(timezone.utc).isoformat())
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"snapshot={output}")
print(f"agent_sha={public['control_plane'].get('sha')}")
print(f"firmware_sha={public['execution_plane'].get('sha')}")
print(f"health={public['health']}")
```

- [ ] **Step 5: Generate the checked-in snapshot deliberately**

```bash
python tools/generate_status_snapshot.py --agent-root ../ASR5K_AGENT --firmware-root ../ASR5K_v2_28384 --output engineering_data/status/status_snapshot.json
```

If a private source is missing, a committed snapshot may be DEGRADED/UNKNOWN but must never be fabricated as LIVE or PASS.

- [ ] **Step 6: Register and test the resource**

Add to `engineering_data/index.json` resources:

```json
"status_snapshot": "status/status_snapshot.json"
```

Add to `tests/test_engineering_data.py`:

```python
snapshot = load_json("status/status_snapshot.json")
self.assertFalse(snapshot["authoritative_engineering_truth"])
self.assertEqual(snapshot["mode"], "SNAPSHOT")
self.assertNotIn("path", snapshot["execution_plane"])
```

- [ ] **Step 7: Run snapshot/data tests**

```bash
python -m unittest tests.test_status_snapshot tests.test_engineering_data -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add workbench/status_snapshot.py tools/generate_status_snapshot.py tests/test_status_snapshot.py tests/test_engineering_data.py engineering_data/index.json engineering_data/status/status_snapshot.json
git commit -m "feat: add sanitized ASR5K status snapshot"
```

---

### Task 7: Make ASR5K Status the landing UI

**Files:**
- Create: `static/eng/status_console.js`
- Modify: `static/index.html`
- Modify: `static/eng/loader.js`
- Modify: `static/styles.css`
- Modify: `static/i18n.js`
- Create: `tests/test_status_frontend.py`

**Interfaces:**
- First source: `GET /api/status/summary`
- Fallback source: `../engineering_data/status/status_snapshot.json`
- LIVE detailed evidence: `GET /api/status/evidence`
- Frontend only renders normalized statuses; it never decides qualification from raw evidence.

- [ ] **Step 1: Add failing frontend contract tests**

Create `tests/test_status_frontend.py`:

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StatusFrontendTests(unittest.TestCase):
    def test_status_is_default_panel_and_tools_remain_present(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-panel="status"', html)
        self.assertIn('id="status" class="panel active"', html)
        self.assertIn('data-panel="measurement"', html)
        self.assertIn('data-panel="control"', html)
        self.assertIn('data-panel="state"', html)

    def test_status_loader_has_live_then_snapshot_fallback(self):
        js = (ROOT / "static" / "eng" / "status_console.js").read_text(encoding="utf-8")
        self.assertIn("/api/status/summary", js)
        self.assertIn("../engineering_data/status/status_snapshot.json", js)
        self.assertNotIn("ASR5K_READ_TOKEN", js)

    def test_remote_is_not_primary_nav(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        primary = html.split('id="engineering-tools"', 1)[0]
        self.assertNotIn('data-panel="remote"', primary)
```

- [ ] **Step 2: Run and verify RED**

```bash
python -m unittest tests.test_status_frontend -v
```

Expected: FAIL.

- [ ] **Step 3: Add the status-first navigation and stable panel mount points**

Before current tool nav buttons in `static/index.html` add:

```html
<div class="nav-group-label" data-i18n="nav.statusGroup">ASR5K STATUS</div>
<button class="nav active" data-panel="status" data-i18n="nav.status">Overview</button>
<button class="nav" data-panel="status-qualification" data-i18n="nav.qualification">Qualification</button>
<button class="nav" data-panel="status-evidence" data-i18n="nav.evidence">Evidence</button>
<button class="nav" data-panel="status-changes" data-i18n="nav.changes">Changes</button>
<div id="engineering-tools" class="nav-group-label" data-i18n="nav.toolsGroup">ENGINEERING TOOLS</div>
```

Remove `active` from Measurement. Move Remote under Engineering Tools and label it as demo/mock, or hide its nav button while retaining its compatibility panel.

Add panels:

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

- [ ] **Step 4: Load renderer before other engineering-view modules**

Update `static/eng/loader.js`:

```javascript
const sources=[
  './eng/common.js',
  './eng/status_console.js',
  './eng/data_source.js',
  './eng/profiles.js',
  './eng/control_sfra.js',
  './eng/system_tools.js'
];
```

- [ ] **Step 5: Implement the renderer with explicit functions**

Create `static/eng/status_console.js` with these functions:

```javascript
(() => {
  'use strict';
  const D = window.DPWE;
  if (!D) return;

  const esc = value => String(value ?? '—')
    .replaceAll('&','&amp;').replaceAll('<','&lt;')
    .replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');

  const cls = status => ({
    PASS:'status-ok', GOLDEN:'status-ok', FAIL:'status-fail', MISMATCH:'status-fail',
    PENDING:'status-warn', STALE:'status-warn', UNKNOWN:'status-unknown',
    NOT_RUN:'status-unknown', NOT_REQUIRED:'status-neutral'
  }[String(status || '').toUpperCase()] || 'status-unknown');

  async function loadModel() {
    try {
      const response = await fetch('/api/status/summary', {cache:'no-store'});
      if (!response.ok) throw new Error(`status API HTTP ${response.status}`);
      return await response.json();
    } catch (liveError) {
      const response = await fetch('../engineering_data/status/status_snapshot.json', {cache:'no-store'});
      if (!response.ok) throw new Error(`snapshot HTTP ${response.status}`);
      return await response.json();
    }
  }

  function renderBaseline(m) {
    D.$('status-baseline').innerHTML = [
      ['GOLDEN', m.product_baseline?.golden_sha],
      ['Firmware', m.execution_plane?.sha],
      ['Relation', m.identity?.relation_to_golden],
      ['Agent', m.control_plane?.sha]
    ].map(([k,v]) => `<div class="card"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
  }

  function renderGates(m) {
    D.$('status-gates').innerHTML = (m.qualification || []).map(row =>
      `<div class="status-gate ${cls(row.status)}"><span>${esc(row.gate)}</span><strong>${esc(row.status)}</strong><small>${esc(row.sha)}</small></div>`
    ).join('');
    D.$('status-qualification-body').innerHTML = (m.qualification || []).map(row =>
      `<div class="card status-detail ${cls(row.status)}"><h3>${esc(row.gate)} · ${esc(row.status)}</h3><p>SHA: <code>${esc(row.sha)}</code></p><p>Evidence: ${esc(row.evidence)}</p><p>${esc(row.note)}</p></div>`
    ).join('');
  }

  function renderBlockers(m) {
    D.$('status-blockers').innerHTML = (m.blockers || []).length
      ? m.blockers.map(row => `<div class="status-blocker ${cls(row.status)}"><b>${esc(row.category)}</b><span>${esc(row.gate)} · ${esc(row.status)}</span><small>${esc(row.note || row.source)}</small></div>`).join('')
      : '<div class="note">No derived blockers in this view.</div>';
  }

  function renderSources(m) {
    D.$('status-sources').innerHTML = `
      <dl class="truth-dl">
        <dt>Mode</dt><dd>${esc(m.mode)}</dd>
        <dt>Health</dt><dd>${esc(m.health)}</dd>
        <dt>Generated</dt><dd>${esc(m.generated_at)}</dd>
        <dt>Firmware branch</dt><dd>${esc(m.execution_plane?.branch)}</dd>
        <dt>Dirty</dt><dd>${esc(m.execution_plane?.dirty)}</dd>
        <dt>Freshness</dt><dd>${esc(m.freshness?.status)}</dd>
      </dl>`;
  }

  function renderChanges(m) {
    D.$('status-changes-body').innerHTML = `
      <div class="card"><h3>Current vs GOLDEN</h3>
      <p>Current: <code>${esc(m.execution_plane?.sha)}</code></p>
      <p>GOLDEN: <code>${esc(m.product_baseline?.golden_sha)}</code></p>
      <p>Relation: <strong>${esc(m.identity?.relation_to_golden)}</strong></p></div>`;
  }

  async function renderEvidence(m) {
    if (m.mode !== 'LIVE') {
      D.$('status-evidence-body').innerHTML = '<div class="card"><p class="note">Snapshot mode shows only evidence references carried by the sanitized snapshot.</p></div>';
      return;
    }
    try {
      const response = await fetch('/api/status/evidence', {cache:'no-store'});
      const data = await response.json();
      D.$('status-evidence-body').innerHTML = (data.records || []).map(row =>
        `<div class="card"><h3>${esc(row.evidence_id || row.record_type || 'evidence')}</h3><pre>${esc(JSON.stringify(row, null, 2))}</pre></div>`
      ).join('') || '<div class="card"><p class="note">No exact-SHA evidence records found.</p></div>';
    } catch (error) {
      D.$('status-evidence-body').innerHTML = `<div class="card status-warn"><p>${esc(error.message)}</p></div>`;
    }
  }

  async function init() {
    try {
      const model = await loadModel();
      D.$('status-mode').textContent = model.freshness?.status || model.mode || 'UNKNOWN';
      D.$('status-mode').className = `badge ${cls(model.freshness?.status || model.mode)}`;
      renderBaseline(model);
      renderGates(model);
      renderBlockers(model);
      renderSources(model);
      renderChanges(model);
      await renderEvidence(model);
    } catch (error) {
      D.$('status-mode').textContent = 'UNKNOWN';
      D.$('status-alert').innerHTML = `<div class="truth-boundary truth-pending"><strong>FAIL CLOSED</strong><span>${esc(error.message)}</span></div>`;
    }
  }

  init();
})();
```

The frontend does not derive PASS/GOLDEN from evidence. It renders the status tokens already produced by Python/snapshot normalization.

- [ ] **Step 6: Add styles and i18n**

Use existing CSS variables; add:

```css
.nav-group-label{margin:18px 12px 7px;color:var(--muted);font-size:10px;letter-spacing:.16em;font-weight:800}
.status-baseline-grid,.status-gate-grid{display:grid;gap:12px;margin-bottom:18px}
.status-baseline-grid{grid-template-columns:repeat(4,minmax(0,1fr))}
.status-gate-grid{grid-template-columns:repeat(5,minmax(120px,1fr))}
.status-gate,.status-blocker{border:1px solid var(--line);border-radius:12px;padding:14px;background:#0d151d}
.status-gate span,.status-blocker span,.status-gate small,.status-blocker small{display:block;color:var(--muted);font-size:11px;margin-top:5px}
.status-ok{border-color:#285e55}.status-fail{border-color:#74343e}.status-warn{border-color:#6a5725}.status-unknown{border-color:#465463}.status-neutral{border-color:var(--line)}
@media(max-width:1000px){.status-baseline-grid{grid-template-columns:1fr 1fr}.status-gate-grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:620px){.status-baseline-grid,.status-gate-grid{grid-template-columns:1fr}}
```

Add bilingual keys for `nav.statusGroup`, `nav.status`, `nav.qualification`, `nav.evidence`, `nav.changes`, `nav.toolsGroup`. Do not translate SHA, repository names, evidence IDs, or state tokens.

- [ ] **Step 7: Run frontend and syntax checks**

```bash
python -m unittest tests.test_status_frontend -v
node --check static/eng/status_console.js
node --check static/eng/loader.js
node --check static/app.js
node --check static/i18n.js
```

Expected: PASS / exit 0.

- [ ] **Step 8: Commit**

```bash
git add static/index.html static/eng/status_console.js static/eng/loader.js static/styles.css static/i18n.js tests/test_status_frontend.py
git commit -m "feat: make ASR5K status the Workbench landing view"
```

---

### Task 8: Finish integration, docs, and full verification

**Files:**
- Modify: `tests/test_final_integration.py`
- Modify: `README.md`
- Modify: `docs/CURRENT_STATUS.md`

- [ ] **Step 1: Extend integration tests for the final boundary**

Add assertions:

```python
def test_status_console_is_primary_and_view_only(self):
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    status_js = (ROOT / "static" / "eng" / "status_console.js").read_text(encoding="utf-8")
    snapshot = json.loads((ROOT / "engineering_data" / "status" / "status_snapshot.json").read_text(encoding="utf-8"))
    index = json.loads((ROOT / "engineering_data" / "index.json").read_text(encoding="utf-8"))

    self.assertIn('id="status" class="panel active"', html)
    self.assertFalse(snapshot["authoritative_engineering_truth"])
    self.assertEqual(index["resources"]["status_snapshot"], "status/status_snapshot.json")
    self.assertNotIn("ASR5K_READ_TOKEN", status_js)
    self.assertIn('data-panel="measurement"', html)
    self.assertIn('data-panel="control"', html)
    self.assertIn('data-panel="state"', html)
```

- [ ] **Step 2: Run integration test and fix only status-integration defects**

```bash
python -m unittest tests.test_final_integration -v
```

Expected: PASS.

- [ ] **Step 3: Update README for the daily workflow**

The opening operational section must state that the Console answers:

```text
- exact firmware SHA being viewed
- exact GOLDEN SHA
- MATCH/AHEAD/DIVERGED/UNKNOWN relation
- exact-SHA evidence state per gate
- FAIL/PENDING/MISMATCH/UNKNOWN/STALE blockers
```

Document local mode:

```powershell
$env:ASR5K_AGENT_ROOT="C:\path\to\ASR5K_AGENT"
$env:ASR5K_FIRMWARE_ROOT="C:\path\to\ASR5K_v2_28384"
python server.py
```

Expected local badge: `LIVE`.

Document GitHub Pages as sanitized `SNAPSHOT`, never LIVE. Keep the existing authority hierarchy and engineering-tool documentation below this introduction.

- [ ] **Step 4: Update `docs/CURRENT_STATUS.md`**

State clearly:

```text
ASR5K_AGENT       = Control / Knowledge Plane
ASR5K_v2_28384    = Execution Plane
Workbench          = View / Analysis Plane
```

Also state that UNKNOWN is expected when exact evidence is absent even if a successful run is remembered informally.

- [ ] **Step 5: Run full Python regression**

```bash
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 6: Run Python compile checks**

```bash
python -m py_compile server.py workbench/*.py tools/*.py tests/*.py
```

Expected: exit 0.

- [ ] **Step 7: Run all JavaScript syntax checks**

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

- [ ] **Step 8: Run a local smoke test against real sibling repos without mutation**

Record before:

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

Check `/api/status/summary`:

```text
mode == LIVE
control_plane.sha == git -C ../ASR5K_AGENT rev-parse HEAD
execution_plane.sha == git -C ../ASR5K_v2_28384 rev-parse HEAD
product_baseline.source == CURRENT_PRODUCT_BASELINE.md
unknown gates remain UNKNOWN unless exact records exist
```

Run the four Git commands again after the smoke test and require identical HEAD plus unchanged working-tree status.

- [ ] **Step 9: Scan public snapshot for accidental local/private strings**

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

- [ ] **Step 10: Commit final docs/integration**

```bash
git add tests/test_final_integration.py README.md docs/CURRENT_STATUS.md
git commit -m "docs: document ASR5K Engineering Console workflow"
```

- [ ] **Step 11: Verify final diff scope**

```bash
git status --short
git log --oneline --decorate -10
git diff --stat design/asr5k-engineering-console...HEAD
```

Expected: clean working tree; only Workbench status model/adapters/API/snapshot/UI/tests/docs changed; Agent and firmware repositories were not mutated.

---

## Review Gates During Execution

Reject a task if any of these occur:

- PASS/GOLDEN is inferred from file presence, test presence, memory, or prose rather than exact evidence.
- A different SHA's evidence is reused as current evidence.
- The browser receives a private token or filesystem path configuration.
- Status collection executes state-changing Git, firmware, flash, or hardware commands.
- Workbench claims ownership of qualification or Production truth.
- Existing engineering calculators become unavailable before Status is verified.
- Public SNAPSHOT is visually represented as LIVE.
- Unrelated cleanup is mixed into the status-console change.

## Expected V1 Result

Local Workbench immediately answers:

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

GitHub Pages answers the same questions from an explicitly generated sanitized `SNAPSHOT`, with age/freshness visible and no private credential requirement.
