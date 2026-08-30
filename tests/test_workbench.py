import math
import unittest

from workbench.control import BuckPlantConfig, analyze_buck_pi, pi_tustin
from workbench.measurement import SignalChainConfig, physical_to_adc
from workbench.remote import RemoteCommandError, SafeMockPowerSupply
from workbench.state_machine import get_state_machine


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.cfg = SignalChainConfig(
            sensor_gain_v_per_unit=0.04,
            sensor_offset_v=0.0,
            opamp_gain=2.5,
            opamp_offset_v=1.65,
            divider_ratio=1.0,
            adc_vref_v=3.3,
            adc_bits=12,
        )

    def test_round_trip_is_within_quantization(self):
        result = physical_to_adc(5.0, self.cfg)
        self.assertFalse(result.clipped)
        self.assertLess(abs(result.quantization_error_physical), 0.02)

    def test_adc_clipping_is_explicit(self):
        result = physical_to_adc(100.0, self.cfg)
        self.assertTrue(result.clipped)
        self.assertEqual(result.adc_code, 4095)


class ControlTests(unittest.TestCase):
    def test_tustin_incremental_coefficients(self):
        c = pi_tustin(0.2, 500.0, 100_000.0)
        self.assertAlmostEqual(c.b0, 0.2025)
        self.assertAlmostEqual(c.b1, -0.1975)

    def test_buck_analysis_produces_finite_resonance(self):
        result = analyze_buck_pi(BuckPlantConfig(
            vin_v=400.0,
            inductance_h=200e-6,
            capacitance_f=470e-6,
            load_ohm=10.0,
            switching_hz=100_000.0,
            sampling_hz=100_000.0,
            kp=0.01,
            ki=20.0,
        ))
        self.assertTrue(math.isfinite(result["resonance_hz"]))
        self.assertEqual(len(result["frequency_hz"]), 160)


class RemoteSafetyTests(unittest.TestCase):
    def test_out_of_range_voltage_is_rejected(self):
        psu = SafeMockPowerSupply(max_voltage_v=700.0)
        with self.assertRaises(RemoteCommandError):
            psu.command("set_voltage", 701.0)

    def test_fault_has_higher_authority_than_output_on(self):
        psu = SafeMockPowerSupply()
        psu.inject_fault_for_test("OCP")
        with self.assertRaises(RemoteCommandError):
            psu.command("output_on")
        self.assertFalse(psu.telemetry()["output_enabled"])


class StateMachineTests(unittest.TestCase):
    def test_run_has_protection_transition_to_fault(self):
        sm = get_state_machine()
        transitions = {(x["from"], x["to"], x["event"]) for x in sm["transitions"]}
        self.assertIn(("RUN", "FAULT", "PROTECTION"), transitions)
        self.assertIn("hardware_protection", sm["authority_boundaries"])


if __name__ == "__main__":
    unittest.main()
