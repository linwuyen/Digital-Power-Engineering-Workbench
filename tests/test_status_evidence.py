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
            json.dumps({"records": [], "status": "no_result_claimed"}) + "\n",
            encoding="utf-8",
        )
        (root / "verification" / "hardware_results" / "index.json").write_text(
            json.dumps({"records": [], "status": "no_result_claimed"}) + "\n",
            encoding="utf-8",
        )

    def test_no_records_means_unknown_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, [])
            gates = {
                x["gate"]: x
                for x in qualification_for_sha(
                    root, SHA, {"golden_sha": OTHER, "source": "baseline.md"}
                )
            }
            self.assertEqual(gates["build"]["status"], "UNKNOWN")
            self.assertEqual(gates["hil"]["status"], "UNKNOWN")

    def test_matching_explicit_gate_pass_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(
                root,
                [
                    {
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
                        "run_id": "RUN-1",
                    }
                ],
            )
            gates = {
                x["gate"]: x
                for x in qualification_for_sha(
                    root, SHA, {"golden_sha": OTHER, "source": "baseline.md"}
                )
            }
            self.assertEqual(gates["build"]["status"], "PASS")
            self.assertEqual(gates["build"]["sha"], SHA)
            self.assertEqual(gates["build"]["evidence"], "EVD-1")

    def test_other_sha_pass_is_historical_not_current_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(
                root,
                [
                    {
                        "record_type": "evidence",
                        "evidence_id": "OLD",
                        "baseline": OTHER,
                        "gate": "build",
                        "artifact_id": "old.out",
                        "test_id": "CPU1-BUILD",
                        "result": "PASS",
                        "timestamp_utc": "2026-09-01T10:00:00Z",
                        "source_or_instrument": "CCS",
                        "artifact_sha256": "2" * 64,
                        "requirement_ids": ["REQ-BUILD-CPU1-001"],
                        "run_id": "RUN-OLD",
                    }
                ],
            )
            gates = {
                x["gate"]: x
                for x in qualification_for_sha(
                    root, SHA, {"golden_sha": OTHER, "source": "baseline.md"}
                )
            }
            self.assertEqual(gates["build"]["status"], "UNKNOWN")

    def test_matching_golden_sets_only_production_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, [])
            gates = {
                x["gate"]: x
                for x in qualification_for_sha(
                    root,
                    SHA,
                    {
                        "golden_sha": SHA,
                        "source": "CURRENT_PRODUCT_BASELINE.md",
                        "release_ref": "release/final",
                    },
                )
            }
            self.assertEqual(gates["production"]["status"], "GOLDEN")
            self.assertEqual(gates["board"]["status"], "UNKNOWN")

    def test_record_without_explicit_gate_cannot_upgrade_any_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(
                root,
                [{
                    "record_type": "evidence",
                    "evidence_id": "AMBIG",
                    "baseline": SHA,
                    "test_id": "looks-like-hil-build-pass",
                    "result": "PASS",
                    "timestamp_utc": "2026-09-12T10:00:00Z",
                }],
            )
            gates = {x["gate"]: x for x in qualification_for_sha(root, SHA, {"golden_sha": OTHER, "source": "baseline.md"})}
            self.assertTrue(all(row["status"] == "UNKNOWN" for gate, row in gates.items() if gate != "production"))


if __name__ == "__main__":
    unittest.main()
