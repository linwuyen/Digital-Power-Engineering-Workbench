import json
import tempfile
import unittest
from pathlib import Path

from workbench.evidence_io import detail_row, load_evidence_records, read_ledger


ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
GOLDEN = "b" * 40


class EvidenceIoTests(unittest.TestCase):
    def write_sources(self, root: Path) -> None:
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
                "result": "PASS",
                "timestamp_utc": "2026-09-17T00:00:00Z",
                "requirement_ids": ["REQ-BUILD-001"],
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
                    "artifact_or_log": "github-actions://run/regression",
                    "golden_sha": GOLDEN,
                }]
            }) + "\n",
            encoding="utf-8",
        )
        (root / "verification" / "hardware_results" / "index.json").write_text(
            json.dumps({
                "records": [{
                    "dut_commit": SHA,
                    "gate": "hil",
                    "result": "BLOCKED",
                    "timestamp": "2026-09-17T00:02:00Z",
                    "evidence": "github-actions://run/hil",
                }]
            }) + "\n",
            encoding="utf-8",
        )

    def test_all_three_sources_normalize_to_one_record_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_sources(root)
            records = load_evidence_records(root)
            by_source = {record.source_type: record for record in records}

            ledger = by_source["evidence_ledger"]
            self.assertEqual(ledger.execution_sha, SHA)
            self.assertEqual(ledger.result, "PASS")
            self.assertEqual(ledger.gate, "build")
            self.assertEqual(ledger.evidence_ref, "EVD-BUILD-1")
            self.assertEqual(ledger.requirement_ids, ("REQ-BUILD-001",))

            regression = by_source["regression_history"]
            self.assertEqual(regression.execution_sha, SHA)
            self.assertEqual(regression.golden_sha, GOLDEN)
            self.assertEqual(regression.evidence_ref, "github-actions://run/regression")

            hardware = by_source["hardware_results"]
            self.assertEqual(hardware.execution_sha, SHA)
            self.assertEqual(hardware.result, "BLOCKED")
            self.assertEqual(hardware.evidence_ref, "github-actions://run/hil")

    def test_detail_rows_preserve_existing_source_specific_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_sources(root)
            rows = {record.source_type: detail_row(record) for record in load_evidence_records(root)}

            self.assertEqual(rows["evidence_ledger"]["record_type"], "evidence")
            self.assertEqual(rows["evidence_ledger"]["evidence_id"], "EVD-BUILD-1")
            self.assertEqual(rows["regression_history"]["record_type"], "regression")
            self.assertEqual(rows["regression_history"]["commit"], SHA)
            self.assertEqual(rows["hardware_results"]["record_type"], "hardware")
            self.assertEqual(rows["hardware_results"]["dut_commit"], SHA)

    def test_read_ledger_returns_meta_separately_from_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_sources(root)
            meta, rows = read_ledger(root / "evidence" / "evidence_ledger.jsonl")
            self.assertEqual(meta["baseline"], SHA)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["record_type"], "evidence")

    def test_malformed_jsonl_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_text('{"record_type":"ledger_meta"}\n{not-json}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_ledger(path)

    def test_non_object_jsonl_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_text('{"record_type":"ledger_meta"}\n[]\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_ledger(path)

    def test_status_consumer_uses_shared_adapter_instead_of_raw_readers(self):
        source = (ROOT / "workbench" / "status_evidence.py").read_text(encoding="utf-8")
        self.assertIn("from .evidence_io import", source)
        self.assertNotIn("def read_jsonl(", source)
        self.assertNotIn("def _json(", source)
        self.assertIn("load_evidence_records", source)


if __name__ == "__main__":
    unittest.main()
