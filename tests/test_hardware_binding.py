import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "2b72f50648d86c11547645882248eed69f12892f"


class FrozenExecutionReferenceTest(unittest.TestCase):
    def test_build_contract_is_exact_and_source_bounded(self):
        data = json.loads((ROOT / "engineering_data/automation/asr5k_build_contract.json").read_text())
        self.assertEqual(data["baseline"]["commit"], BASELINE)
        p = data["projects"]
        self.assertEqual(p["cpu1"]["configuration"], "FLASH")
        self.assertEqual(p["cpu1"]["compiler"], "22.6.1.LTS")
        self.assertEqual(p["cpu1"]["artifact_name"], "ASR5K_F28384D_CPU1.out")
        self.assertEqual(p["cpu2"]["configuration"], "FLASH")
        self.assertEqual(p["cpu2"]["compiler"], "22.6.1.LTS")
        self.assertEqual(p["m0"]["configuration"], "Debug")
        self.assertEqual(p["m0"]["compiler"], "TICLANG_3.2.2.LTS")
        self.assertEqual(p["m0"]["products"]["MSPM0-SDK"], "2.8.0.03")
        self.assertEqual(data["flash_binding"]["status"], "pending_local_detection")
        self.assertIsNone(data["flash_binding"]["target_config_ccxml"])
        self.assertEqual(data["hil_gateway_binding"]["status"], "pending_local_detection")
        self.assertIsNone(data["hil_gateway_binding"]["gateway_command"])

    def test_canonical_build_plans_are_frozen_legacy_snapshot_data(self):
        registry = json.loads((ROOT / "engineering_data/federation/deprecation_registry.json").read_text())
        paths = {item["path"]: item for item in registry["items"]}
        self.assertEqual(paths["engineering_data/automation/"]["status"], "frozen_legacy_snapshot_contracts")
        self.assertEqual(paths["engineering_data/automation/"]["replacement_owner"], "linwuyen/ASR5K_v2_28384")
        self.assertIn("production_build_owner", registry["forbidden_new_workbench_authority"])

    def test_windows_entrypoint_is_deprecated_execution_path(self):
        text = (ROOT / "asrtest.ps1").read_text()
        self.assertIn("execution entrypoint is deprecated", text)
        self.assertIn("View / Analysis Plane", text)
        self.assertIn("linwuyen/ASR5K_v2_28384", text)
        self.assertNotIn("auto_run_ext.py", text)
        self.assertNotIn("hardware_bind.py", text)


if __name__ == "__main__":
    unittest.main()
