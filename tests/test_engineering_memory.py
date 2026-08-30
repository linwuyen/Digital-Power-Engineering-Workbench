import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "engineering_data"
BASELINE = "2b72f50648d86c11547645882248eed69f12892f"


def load_json(relative_path: str):
    with (DATA / relative_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class EngineeringMemorySsotTest(unittest.TestCase):
    def test_core_memory_sources_are_indexed(self):
        index = load_json("index.json")
        expected = {
            "requirement_ledger": "requirements/requirement_ledger.json",
            "signal_dictionary": "hardware/signal_dictionary.json",
            "timing_budget": "timing/timing_budget.json",
            "protection_matrix": "protection/protection_matrix.json",
            "evidence_ledger": "evidence/evidence_ledger.jsonl",
        }
        for key, relative in expected.items():
            with self.subTest(key=key):
                self.assertEqual(index["resources"][key], relative)
                self.assertTrue((DATA / relative).is_file())
        self.assertTrue(index["consumer_policy"]["pass_claim_requires_evidence_ledger_record"])
        self.assertFalse(index["consumer_policy"]["test_file_presence_is_pass"])

    def test_requirement_ledger_is_baseline_bound_and_traceable(self):
        ledger = load_json("requirements/requirement_ledger.json")
        self.assertEqual(ledger["baseline"], BASELINE)
        ids = [item["id"] for item in ledger["requirements"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("REQ-SPIB-001", ids)
        self.assertIn("REQ-ADC-001", ids)
        for item in ledger["requirements"]:
            with self.subTest(id=item["id"]):
                self.assertTrue(item["implementation_refs"])
                self.assertIn(item["trust"], {"verified_source", "governance_contract", "pending_verification", "not_claimed"})

    def test_pending_analog_signal_fields_fail_closed(self):
        dictionary = load_json("hardware/signal_dictionary.json")
        pending = [x for x in dictionary["signals"] if x["trust"] == "pending_verification"]
        self.assertGreaterEqual(len(pending), 4)
        for item in pending:
            with self.subTest(id=item["id"]):
                self.assertIsNone(item["raw_type"])
                self.assertIsNone(item["adc_module"])
                self.assertIsNone(item["adc_channel"])
                self.assertIsNone(item["scale"])
                self.assertIsNone(item["offset"])

    def test_formal_timing_claims_need_budget_and_measurement(self):
        timing = load_json("timing/timing_budget.json")
        by_id = {item["id"]: item for item in timing["budgets"]}
        self.assertEqual(by_id["SPIB_PARSER_500_TICK_DIAGNOSTIC"]["classification"], "diagnostic_threshold_not_acceptance_deadline")
        self.assertIsNone(by_id["SPIB_RESPONSE_DEADLINE"]["budget"])
        self.assertIsNone(by_id["SPIB_RESPONSE_DEADLINE"]["measured_worst_case"])
        self.assertIsNone(by_id["HARDWARE_PROTECTION_SHUTDOWN_LATENCY"]["budget"])
        self.assertIsNone(by_id["HARDWARE_PROTECTION_SHUTDOWN_LATENCY"]["measured_worst_case"])

    def test_protection_matrix_separates_authorities_and_unknowns(self):
        matrix = load_json("protection/protection_matrix.json")
        by_id = {item["id"]: item for item in matrix["protection_paths"]}
        c28 = by_id["C28_LOCAL_HW_PROTECTION"]
        self.assertIsNotNone(c28["detection_authority"])
        self.assertIsNotNone(c28["shutdown_authority"])
        self.assertIsNone(c28["threshold"])
        self.assertIsNone(c28["latency_us"])
        self.assertEqual(c28["verification"], "pending_verification")

    def test_evidence_ledger_contains_only_metadata_until_real_evidence(self):
        path = DATA / "evidence/evidence_ledger.jsonl"
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(records), 1)
        meta = records[0]
        self.assertEqual(meta["record_type"], "ledger_meta")
        self.assertEqual(meta["baseline"], BASELINE)
        self.assertEqual(meta["status"], "no_result_claimed")
        self.assertTrue(meta["append_only"])

    def test_current_status_exists_and_carries_baseline(self):
        status = (ROOT / "docs/CURRENT_STATUS.md").read_text(encoding="utf-8")
        self.assertIn(BASELINE, status)
        self.assertIn("Explicit pending verification", status)
        self.assertIn("Definition of Done", status)


if __name__ == "__main__":
    unittest.main()
