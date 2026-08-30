import unittest

from workbench.control_advanced import PlantModel, PoleZeroController, analyze_pole_zero_loop
from workbench.contracts import ContractError, validate_state_contract
from workbench.profiles import builtin_profiles, profile_from_dict
from workbench.protocol import Frame, ProtocolError, decode_frame
from workbench.sfra import compare_theory_to_sfra, parse_sfra_csv
from workbench.validation import run_sequence


class ProfileTests(unittest.TestCase):
    def test_builtin_profiles_validate(self):
        profiles = builtin_profiles()
        self.assertGreaterEqual(len(profiles), 3)
        for profile in profiles:
            parsed = profile_from_dict(profile)
            parsed.config.validate()


class AdvancedControlTests(unittest.TestCase):
    def test_second_order_loop_has_consistent_arrays(self):
        result = analyze_pole_zero_loop(
            PlantModel(dc_gain=1.0, resonance_hz=1000.0, q=0.707, rhpz_hz=10000.0),
            PoleZeroController(gain=2000.0, zeros_hz=(200.0,), poles_hz=(5000.0,)),
            sampling_hz=100000.0,
        )
        n = len(result["frequency_hz"])
        self.assertGreater(n, 100)
        self.assertEqual(n, len(result["loop_mag_db"]))
        self.assertEqual(n, len(result["loop_phase_deg"]))


class ProtocolTests(unittest.TestCase):
    def test_frame_round_trip(self):
        encoded = Frame(0x10, bytes.fromhex("64 00 00 00")).encode()
        decoded = decode_frame(encoded)
        self.assertEqual(decoded.command_id, 0x10)
        self.assertEqual(decoded.payload, bytes.fromhex("64 00 00 00"))

    def test_crc_rejects_corruption(self):
        encoded = bytearray(Frame(1, b"abc").encode())
        encoded[6] ^= 0x01
        with self.assertRaises(ProtocolError):
            decode_frame(bytes(encoded))


class ContractTests(unittest.TestCase):
    def test_contract_reports_unreachable(self):
        contract = {
            "states": [{"id": "BOOT"}, {"id": "RUN"}, {"id": "ORPHAN"}],
            "transitions": [{"from": "BOOT", "to": "RUN", "event": "GO"}],
            "authority_boundaries": {"hardware_protection": "highest"},
        }
        result = validate_state_contract(contract)
        self.assertEqual(result["unreachable_states"], ["ORPHAN"])

    def test_unknown_transition_state_is_rejected(self):
        with self.assertRaises(ContractError):
            validate_state_contract({
                "states": [{"id": "BOOT"}],
                "transitions": [{"from": "BOOT", "to": "RUN", "event": "GO"}],
                "authority_boundaries": {"hardware_protection": "highest"},
            })


class SfraTests(unittest.TestCase):
    def test_csv_parse_and_compare(self):
        measured = parse_sfra_csv("frequency_hz,magnitude_db,phase_deg\n10,0,-90\n100,-10,-120\n1000,-20,-150\n")
        theory = {
            "frequency_hz": [10.0, 100.0, 1000.0],
            "loop_mag_db": [0.0, -9.0, -21.0],
            "loop_phase_deg": [-90.0, -118.0, -152.0],
        }
        result = compare_theory_to_sfra(theory, measured)
        self.assertEqual(len(result["aligned"]), 3)
        self.assertLess(result["rms_magnitude_error_db"], 2.0)


class ValidationTests(unittest.TestCase):
    def test_fault_sequence_passes_policy_assertions(self):
        result = run_sequence([
            {"action": "set_voltage", "value": 100.0},
            {"action": "set_current", "value": 5.0},
            {"action": "output_on"},
            {"action": "assert", "field": "state", "equals": "RUN"},
            {"action": "inject_fault", "fault": "OCP"},
            {"action": "assert", "field": "output_enabled", "equals": False},
            {"action": "assert", "field": "state", "equals": "FAULT"},
        ])
        self.assertTrue(result["pass"])
        self.assertEqual(result["final_telemetry"]["fault"], "OCP")


if __name__ == "__main__":
    unittest.main()
