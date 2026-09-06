import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from auto_common import changed_files, generate_run_id, scan_files  # noqa: E402
from auto_run import evaluate_claim, validate_plan  # noqa: E402
from evidence_agent import collect_changes, snapshot_collectors  # noqa: E402


BASELINE = "2b72f50648d86c11547645882248eed69f12892f"


class FullAutoPipelineTest(unittest.TestCase):
    def test_run_id_is_generated_without_operator_input(self):
        run_id = generate_run_id(datetime(2026, 9, 6, 9, 30, 0, tzinfo=timezone.utc))
        self.assertTrue(run_id.startswith("RUN-20260906-093000-"))
        self.assertEqual(len(run_id.split("-")[-1]), 6)

    def test_collector_only_archives_files_changed_during_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "scope"
            inbox.mkdir()
            old = inbox / "old.csv"
            old.write_text("old", encoding="utf-8")
            config = {"collectors": [{"id": "scope", "path": "scope", "patterns": ["*.csv"]}]}
            before = snapshot_collectors(config, root)
            old.write_text("changed", encoding="utf-8")
            new = inbox / "new.csv"
            new.write_text("new", encoding="utf-8")
            run_dir = root / "archive" / "RUN-X"
            rows = collect_changes(config, root, before, run_dir)
            names = {row["name"] for row in rows}
            self.assertEqual(names, {"old.csv", "new.csv"})
            self.assertTrue((run_dir / "raw" / "scope" / "new.csv").exists())
            self.assertTrue(all(len(row["sha256"]) == 64 for row in rows))

    def test_simulation_can_never_auto_qualify(self):
        plan = {"mode": "simulation"}
        claim = {"artifact": "a", "depends_on_steps": ["s"], "physical_evidence_required": False}
        steps = [{"id": "s", "status": "PASS", "physical": False}]
        artifacts = [{"id": "a"}]
        result, reasons = evaluate_claim(claim, plan, steps, artifacts, [])
        self.assertEqual(result, "BLOCKED")
        self.assertTrue(any("simulation" in reason for reason in reasons))

    def test_failed_dependency_becomes_fail_evidence(self):
        plan = {"mode": "hardware"}
        claim = {"artifact": "a", "depends_on_steps": ["s"], "physical_evidence_required": False}
        result, _ = evaluate_claim(claim, plan, [{"id": "s", "status": "FAIL"}], [{"id": "a"}], [])
        self.assertEqual(result, "FAIL")

    def test_physical_claim_needs_physical_output_or_step(self):
        plan = {"mode": "hardware"}
        claim = {
            "artifact": "a",
            "depends_on_steps": ["s"],
            "physical_evidence_required": True,
            "required_collector_ids": ["scope"],
        }
        steps = [{"id": "s", "status": "PASS", "physical": True}]
        artifacts = [{"id": "a"}]
        result, _ = evaluate_claim(claim, plan, steps, artifacts, [])
        self.assertEqual(result, "BLOCKED")
        result, _ = evaluate_claim(claim, plan, steps, artifacts, [{"collector_id": "scope"}])
        self.assertEqual(result, "PASS")

    def test_plan_validator_rejects_unknown_dependency(self):
        plan = {
            "id": "P",
            "baseline": BASELINE,
            "mode": "hardware",
            "requirements": ["REQ-X"],
            "steps": [{"id": "s", "op": "note"}],
            "artifacts": [{"id": "a", "glob": "x"}],
            "evidence_claims": [{
                "id": "c",
                "test_id": "T",
                "requirement_ids": ["REQ-X"],
                "depends_on_steps": ["missing"],
                "artifact": "a",
            }],
        }
        with self.assertRaises(ValueError):
            validate_plan(plan)


if __name__ == "__main__":
    unittest.main()
