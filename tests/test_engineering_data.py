import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "engineering_data"
BASELINE = "2b72f50648d86c11547645882248eed69f12892f"


def load_json(relative_path: str):
    with (DATA / relative_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class EngineeringDataIntegrityTest(unittest.TestCase):
    def test_all_json_files_parse(self):
        files = sorted(DATA.rglob("*.json"))
        self.assertGreater(len(files), 10)
        for path in files:
            with self.subTest(path=path.relative_to(ROOT)):
                with path.open("r", encoding="utf-8") as handle:
                    json.load(handle)

    def test_index_baseline_and_resources_exist(self):
        index = load_json("index.json")
        self.assertEqual(index["baseline"]["commit"], BASELINE)
        self.assertFalse(index["consumer_policy"]["browser_safety_authority"])
        self.assertFalse(index["consumer_policy"]["production_repository_mutated"])
        for name, relative in index["resources"].items():
            with self.subTest(resource=name):
                self.assertTrue((DATA / relative).is_file(), relative)

    def test_manifest_is_identity_not_qualification_claim(self):
        manifest = load_json("baselines/manifest-2b72f506.json")
        self.assertEqual(manifest["commit"], BASELINE)
        self.assertEqual(manifest["qualification_status"], "not_claimed_by_dataset")
        self.assertEqual(
            set(manifest["qualification_claims"].values()), {None}
        )
        self.assertEqual(manifest["production_repository_access"], "read_only")

    def test_pending_scaling_is_not_guessed(self):
        scaling = load_json("firmware/scaling.json")
        pending = [x for x in scaling["scalings"] if x["trust"] == "pending_verification"]
        self.assertGreater(len(pending), 0)
        for item in pending:
            with self.subTest(id=item["id"]):
                self.assertIsNone(item["scale"])
                self.assertIsNone(item["offset"])

    def test_pending_protection_thresholds_and_latency_are_null(self):
        matrix = load_json("firmware/protection_matrix.json")
        pending = [x for x in matrix["protections"] if x["trust"] == "governance_contract" and x.get("verification") == "pending_verification"]
        self.assertGreater(len(pending), 0)
        for item in pending:
            with self.subTest(id=item["id"]):
                self.assertIsNone(item["threshold"])
                self.assertIsNone(item["latency_us"])

    def test_pending_timing_values_are_null(self):
        timing = load_json("firmware/timing_budget.json")
        pending = [x for x in timing["timing"] if x["trust"] == "pending_verification"]
        self.assertGreater(len(pending), 0)
        for item in pending:
            with self.subTest(id=item["id"]):
                self.assertIsNone(item["value"])

    def test_wire_contract_exact_invariants(self):
        protocol = load_json("protocol/host_protocol.json")
        self.assertEqual(protocol["transport"]["request_bits"], 32)
        self.assertEqual(protocol["transport"]["response_bits"], 32)
        self.assertEqual(protocol["null_frame"]["value"], "0xFFFF0000")
        self.assertIn("next master transaction", protocol["transport"]["response_timing"])

        commands = load_json("protocol/command_dictionary.json")
        self.assertEqual(commands["queue_depth"], 8)
        by_name = {item["name"]: item for item in commands["intent_types"]}
        self.assertEqual(by_name["FREQUENCY_SET"]["wire_addresses"], ["0x0910", "0x0911"])
        self.assertEqual(by_name["DCV_SET"]["wire_addresses"], ["0x0939", "0x093A"])
        self.assertEqual(by_name["ACV_SET"]["wire_addresses"], ["0x093B", "0x093C"])

    def test_state_contract_does_not_claim_unextracted_complete_graph(self):
        state = load_json("firmware/state_machine.json")
        self.assertEqual(state["baseline"], BASELINE)
        self.assertEqual(state["owner"], "CPU1")
        self.assertEqual(state["transition_completeness"], "partial")
        self.assertEqual(
            [x["id"] for x in state["system_states"]],
            ["BOOT", "INIT", "IDLE", "RUN", "FAULT", "MAINTENANCE", "OTA"],
        )

    def test_production_evidence_urls_are_commit_pinned(self):
        evidence = load_json("ai/evidence_index.json")
        production = [x for x in evidence["sources"] if x["tier"] == "production_source"]
        self.assertGreater(len(production), 0)
        for item in production:
            with self.subTest(id=item["id"]):
                self.assertIn(BASELINE, item["url"])

    def test_empty_evidence_ledgers_do_not_claim_results(self):
        hardware = load_json("verification/hardware_results/index.json")
        regression = load_json("verification/regression_history/index.json")
        self.assertEqual(hardware["records"], [])
        self.assertEqual(hardware["status"], "no_result_claimed")
        self.assertEqual(regression["records"], [])
        self.assertEqual(regression["status"], "no_result_claimed")


if __name__ == "__main__":
    unittest.main()
