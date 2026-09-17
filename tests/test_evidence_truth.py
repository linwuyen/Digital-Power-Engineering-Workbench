import json
import tempfile
import unittest
from pathlib import Path

from workbench.evidence_io import evidence_records_for_sha, load_evidence_records


SHA = "a" * 40
OTHER = "b" * 40
GOLDEN = "c" * 40


class EvidenceTruthTests(unittest.TestCase):
    def write_dataset(self, root: Path) -> None:
        (root / "evidence").mkdir(parents=True)
        (root / "verification" / "regression_history").mkdir(parents=True)
        (root / "verification" / "hardware_results").mkdir(parents=True)

        ledger_rows = [
            {"record_type": "ledger_meta", "schema_version": "1.0", "baseline": SHA},
            {
                "record_type": "evidence",
                "evidence_id": "EVD-BUILD-1",
                "baseline": SHA,
                "gate": "build",
                "artifact_id": "cpu1.out",
                "test_id": "CPU1-BUILD",
                "result": "PASS",
                "timestamp_utc": "2026-09-17T00:00:00Z",
                "source_or_instrument": "CCS",
                "requirement_ids": ["REQ-BUILD-001"],
                "run_id": "RUN-BUILD-1",
            },
        ]
        (root / "evidence" / "evidence_ledger.jsonl").write_text(
            "\n".join(json.dumps(row) for row in ledger_rows) + "\n",
            encoding="utf-8",
        )
        (root / "verification" / "regression_history" / "index.json").write_text(
            json.dumps({
                "records": [{
                    "commit": SHA,
                    "gate": "regression",
                    "result": "PASS",
                    "timestamp": "2026-09-17T00:01:00Z",
                    "artifact_or_log": "github-actions://firmware/regression/1",
                    "run_id": "RUN-REG-1",
                    "golden_sha": GOLDEN,
                }]
            }) + "\n",
            encoding="utf-8",
        )
        (root / "verification" / "hardware_results" / "index.json").write_text(
            json.dumps({
                "records": [
                    {
                        "dut_commit": SHA,
                        "gate": "hil",
                        "result": "BLOCKED",
                        "timestamp": "2026-09-17T00:02:00Z",
                        "evidence": "github-actions://firmware/hil/1",
                        "run_id": "RUN-HIL-1",
                    },
                    {
                        "dut_commit": OTHER,
                        "gate": "hil",
                        "result": "PASS",
                        "timestamp": "2026-09-16T00:00:00Z",
                        "evidence": "github-actions://firmware/hil/old",
                    },
                ]
            }) + "\n",
            encoding="utf-8",
        )

    def test_all_sources_normalize_to_one_core_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root)
            records = load_evidence_records(root)

            self.assertEqual(len(records), 4)
            required = {
                "source", "execution_sha", "gate", "result", "evidence_id",
                "evidence", "timestamp", "golden_sha", "requirement_ids",
                "run_id", "details",
            }
            for record in records:
                self.assertTrue(required.issubset(record), record)

            by_source = {record["source"]: record for record in records if record["execution_sha"] == SHA}
            self.assertEqual(by_source["evidence_ledger"]["evidence_id"], "EVD-BUILD-1")
            self.assertEqual(by_source["evidence_ledger"]["requirement_ids"], ["REQ-BUILD-001"])
            self.assertEqual(by_source["regression_history"]["evidence"], "github-actions://firmware/regression/1")
            self.assertEqual(by_source["regression_history"]["golden_sha"], GOLDEN)
            self.assertEqual(by_source["hardware_results"]["result"], "BLOCKED")

    def test_exact_sha_filter_is_shared_across_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root)
            records = evidence_records_for_sha(root, SHA)
            self.assertEqual({row["source"] for row in records}, {
                "evidence_ledger", "regression_history", "hardware_results"
            })
            self.assertTrue(all(row["execution_sha"] == SHA for row in records))

    def test_status_and_traceability_do_not_parse_source_specific_evidence(self):
        repo = Path(__file__).resolve().parents[1]
        status = (repo / "workbench" / "status_evidence.py").read_text(encoding="utf-8")
        traceability = (repo / "tools" / "traceability.py").read_text(encoding="utf-8")

        self.assertIn("load_evidence_records", status)
        self.assertNotIn('regression_history" / "index.json', status)
        self.assertNotIn('hardware_results" / "index.json', status)
        self.assertNotIn("from import_evidence import read_ledger", traceability)
        self.assertIn("load_evidence_records", traceability)
        self.assertFalse((repo / "tools" / "import_evidence.py").exists())


if __name__ == "__main__":
    unittest.main()
