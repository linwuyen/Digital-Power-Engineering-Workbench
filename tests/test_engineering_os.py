import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from extract_source_truth import SOURCE_FILES, extract  # noqa: E402
from hil_runner import MockAdapter, run_plan, validate_plan  # noqa: E402
from import_evidence import validate_evidence  # noqa: E402
from traceability import build_traceability  # noqa: E402
from truth_common import load_json  # noqa: E402
from verify_truth_drift import compare  # noqa: E402


BASELINE = "2b72f50648d86c11547645882248eed69f12892f"


class EngineeringOsAutomationTest(unittest.TestCase):
    def test_extractor_parses_high_confidence_c_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixtures = {
                "system_state_h": """
                    #define ASR5K_CPU2_FAULT_BENCH_BYPASS (1U)
                    #define ASR5K_AC_FAIL_BENCH_BYPASS (1U)
                    #define ASR5K_DC_OVP_BENCH_BYPASS (1U)
                    #define ASR5K_BENCH_BYPASS_M0_TIMEOUT (1U)
                    typedef enum { SYSTEM_STATE_BOOT=0U, SYSTEM_STATE_INIT, SYSTEM_STATE_IDLE, SYSTEM_STATE_RUN, SYSTEM_STATE_FAULT, SYSTEM_STATE_MAINTENANCE, SYSTEM_STATE_OTA } E_SYSTEM_STATE;
                    typedef enum { FAULT_STATE_CLEAR=0U, FAULT_STATE_ACTIVE, FAULT_STATE_LATCHED, FAULT_STATE_RECOVERY_WAIT } E_FAULT_STATE;
                    typedef enum { POWER_SEQUENCE_OFF=0U, POWER_SEQUENCE_RUN, POWER_SEQUENCE_FAULT } E_POWER_SEQUENCE_STATE;
                    typedef enum { SYSTEM_CMD_OUTPUT_ON=0U, SYSTEM_CMD_OUTPUT_OFF, SYSTEM_CMD_READ_STATUS } E_SYSTEM_COMMAND;
                    typedef enum { SYSTEM_FAULT_NONE=0x0UL, SYSTEM_FAULT_INIT=0x1UL, SYSTEM_FAULT_EXTERNAL=0x80000000UL } E_SYSTEM_FAULT_SOURCE;
                """,
                "system_state_impl": """
                    #define SYSTEM_AC_ACK_TIMEOUT_MS (500U)
                    #define SYSTEM_OUTPUT_ACK_TIMEOUT_MS (500U)
                    #define SYSTEM_OUTPUT_RELAY_SETTLE_MS (20U)
                    #define SYSTEM_OUTPUT_DDS_START_TIMEOUT_MS (500U)
                """,
                "host_queue": """
                    #define HOST_COMMAND_QUEUE_DEPTH (8U)
                    typedef enum { HOST_COMMAND_NONE=0U, HOST_COMMAND_OUTPUT_SET, HOST_COMMAND_FREQUENCY_SET } E_HOST_COMMAND_TYPE;
                """,
                "spib_contract": """
                    #define SPIB_CONTROL_FREQUENCY_SET_MSB_ADDR 0x0910U
                    #define SPIB_CONTROL_FREQUENCY_SET_LSB_ADDR 0x0911U
                    #define SPIB_CONTROL_FREQ_COMP_ON_OFF_ADDR 0x0929U
                    #define SPIB_CONTROL_DCV_SET_MSB_ADDR 0x0939U
                    #define SPIB_CONTROL_DCV_SET_LSB_ADDR 0x093AU
                    #define SPIB_CONTROL_ACV_SET_MSB_ADDR 0x093BU
                    #define SPIB_CONTROL_ACV_SET_LSB_ADDR 0x093CU
                """,
                "spib_diag": "uint32_t u32SpiBParserOver500Count; uint32_t u32SpiBParserOver1000Count;",
            }
            for key, relative in SOURCE_FILES.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(fixtures[key], encoding="utf-8")

            snapshot = extract(root, BASELINE)
            self.assertEqual(snapshot["facts"]["host_queue_depth"], 8)
            self.assertEqual(snapshot["facts"]["scalar_registers"]["SPIB_CONTROL_DCV_SET_MSB_ADDR"], "0x0939")
            self.assertEqual(snapshot["facts"]["spib_parser_diagnostic_threshold_ticks"], [500, 1000])
            self.assertEqual(snapshot["facts"]["fault_bitmap"][-1]["mask"], "0x80000000")

    def canonical_snapshot(self):
        state = load_json(ROOT / "engineering_data/firmware/state_machine.json")
        protection = load_json(ROOT / "engineering_data/protection/protection_matrix.json")
        timing = load_json(ROOT / "engineering_data/timing/timing_budget.json")
        commands = load_json(ROOT / "engineering_data/protocol/command_dictionary.json")
        by_name = {row["name"]: row for row in commands["intent_types"]}
        freq_comp = next(row for row in commands["additional_verified_registers"] if row["name"] == "FREQ_COMP_ON_OFF")
        budgets = {row["id"]: row["budget"] for row in timing["budgets"]}
        return {
            "baseline": BASELINE,
            "facts": {
                "system_states": [{"name": row["id"], "value": row["value"]} for row in state["system_states"]],
                "fault_bitmap": [{"name": row["name"], "mask": f"0x{int(row['mask'], 16):08X}"} for row in protection["fault_sources"]],
                "bench_gates": {row["name"]: int(row["value"]) for row in protection["temporary_baseline_gates"]},
                "timing_ms": {
                    "SYSTEM_AC_ACK_TIMEOUT": budgets["SYSTEM_AC_ACK_TIMEOUT"],
                    "SYSTEM_OUTPUT_ACK_TIMEOUT": budgets["SYSTEM_OUTPUT_ACK_TIMEOUT"],
                    "SYSTEM_OUTPUT_RELAY_SETTLE": budgets["SYSTEM_OUTPUT_RELAY_SETTLE"],
                    "SYSTEM_OUTPUT_DDS_START_TIMEOUT": budgets["SYSTEM_OUTPUT_DDS_START_TIMEOUT"],
                },
                "spib_parser_diagnostic_threshold_ticks": [500, 1000],
                "host_queue_depth": commands["queue_depth"],
                "scalar_registers": {
                    "SPIB_CONTROL_FREQUENCY_SET_MSB_ADDR": by_name["FREQUENCY_SET"]["wire_addresses"][0],
                    "SPIB_CONTROL_FREQUENCY_SET_LSB_ADDR": by_name["FREQUENCY_SET"]["wire_addresses"][1],
                    "SPIB_CONTROL_FREQ_COMP_ON_OFF_ADDR": freq_comp["address"],
                    "SPIB_CONTROL_DCV_SET_MSB_ADDR": by_name["DCV_SET"]["wire_addresses"][0],
                    "SPIB_CONTROL_DCV_SET_LSB_ADDR": by_name["DCV_SET"]["wire_addresses"][1],
                    "SPIB_CONTROL_ACV_SET_MSB_ADDR": by_name["ACV_SET"]["wire_addresses"][0],
                    "SPIB_CONTROL_ACV_SET_LSB_ADDR": by_name["ACV_SET"]["wire_addresses"][1],
                },
            },
        }

    def test_drift_detector_passes_canonical_and_detects_mutation(self):
        snapshot = self.canonical_snapshot()
        report = compare(snapshot, ROOT / "engineering_data")
        self.assertEqual(report["status"], "PASS")
        mutated = copy.deepcopy(snapshot)
        mutated["facts"]["host_queue_depth"] = 9
        report = compare(mutated, ROOT / "engineering_data")
        self.assertEqual(report["status"], "DRIFT")
        self.assertTrue(any(row["check"] == "host_queue_depth" for row in report["errors"]))

    def test_pass_evidence_requires_hash_run_and_requirement(self):
        base = {
            "evidence_id": "EVD-TEST-1",
            "baseline": BASELINE,
            "artifact_id": "dut.out",
            "test_id": "TEST-1",
            "result": "PASS",
            "timestamp_utc": "2026-08-31T00:00:00Z",
            "source_or_instrument": "unit-test",
        }
        with self.assertRaises(ValueError):
            validate_evidence(base, BASELINE)
        base["artifact_sha256"] = "a" * 64
        base["run_id"] = "RUN-1"
        base["requirement_ids"] = ["REQ-SPIB-001"]
        checked = validate_evidence(base, BASELINE)
        self.assertEqual(checked["result"], "PASS")
        self.assertEqual(checked["record_type"], "evidence")

    def test_traceability_only_promotes_exact_evidence(self):
        requirements = load_json(ROOT / "engineering_data/requirements/requirement_ledger.json")
        empty = build_traceability(requirements, [])
        row = next(item for item in empty["requirements"] if item["id"] == "REQ-SPIB-001")
        self.assertEqual(row["status"], "SOURCE_VERIFIED_ONLY")
        evidence = [{
            "record_type": "evidence",
            "evidence_id": "EVD-1",
            "baseline": BASELINE,
            "result": "PASS",
            "requirement_ids": ["REQ-SPIB-001"],
        }]
        report = build_traceability(requirements, evidence)
        row = next(item for item in report["requirements"] if item["id"] == "REQ-SPIB-001")
        self.assertEqual(row["status"], "QUALIFIED_BY_EVIDENCE")

    def test_hil_mock_can_never_claim_qualification(self):
        plan = load_json(ROOT / "engineering_data/hil/reference_mock_plan.json")
        report = run_plan(plan, MockAdapter(), "mock")
        self.assertEqual(report["result"], "SIMULATION_PASS")
        self.assertFalse(report["qualification_claimed"])

    def test_hil_rejects_host_safety_authority(self):
        plan = {
            "id": "BAD",
            "baseline": BASELINE,
            "requirements": ["REQ-AUTH-001"],
            "steps": [{"op": "send", "request": {"action": "disable_ocp"}}],
        }
        with self.assertRaises(ValueError):
            validate_plan(plan)


if __name__ == "__main__":
    unittest.main()
