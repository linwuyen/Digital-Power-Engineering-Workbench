import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import auto_run_ext
import ccs_build
import hardware_bind

BASELINE = "2b72f50648d86c11547645882248eed69f12892f"


class HardwareBindingTest(unittest.TestCase):
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

    def test_ccs_command_builders_use_documented_application_ids(self):
        e_imp, e_build = ccs_build.cli_commands("eclipse", Path("eclipsec.exe"), Path("ws"), Path("proj"), "P", "FLASH")
        self.assertIn("com.ti.ccstudio.apps.projectImport", e_imp)
        self.assertIn("com.ti.ccstudio.apps.projectBuild", e_build)
        self.assertIn("FLASH", e_build)
        s_imp, s_build = ccs_build.cli_commands("server", Path("ccs-server-cli"), Path("ws"), Path("proj"), "P", "Debug")
        self.assertIn("com.ti.ccs.apps.importProject", s_imp)
        self.assertIn("com.ti.ccs.apps.buildProject", s_build)
        self.assertIn("Debug", s_build)

    def test_build_mode_cannot_smuggle_hardware_or_physical_claims(self):
        base = {"id":"B","baseline":BASELINE,"mode":"build","requirements":["REQ-X"],"steps":[{"id":"build","op":"command","command":["echo","x"]}],"evidence_claims":[{"id":"c","test_id":"T","requirement_ids":["REQ-X"],"depends_on_steps":["build"],"physical_evidence_required":False}]}
        auto_run_ext.validate_plan(base)
        bad_hil = json.loads(json.dumps(base)); bad_hil["steps"]=[{"id":"h","op":"hil","plan":"x.json"}]; bad_hil["evidence_claims"][0]["depends_on_steps"]=["h"]
        with self.assertRaises(ValueError): auto_run_ext.validate_plan(bad_hil)
        bad_phys = json.loads(json.dumps(base)); bad_phys["evidence_claims"][0]["physical_evidence_required"]=True
        with self.assertRaises(ValueError): auto_run_ext.validate_plan(bad_phys)

    def test_build_preflight_reuses_source_checks_without_hardware_enable(self):
        plan = {"id":"B","baseline":BASELINE,"mode":"build","requirements":["REQ-X"],"steps":[],"evidence_claims":[],"preflight":{}}
        observed = {}
        def fake_original(shadow, config): observed["shadow"] = shadow; return {"status":"PASS"}
        with mock.patch.object(auto_run_ext, "_original_preflight", fake_original): report = auto_run_ext.preflight(plan, {"allow_hardware":False})
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["run_mode"], "build")
        self.assertEqual(observed["shadow"]["mode"], "simulation")
        self.assertTrue(observed["shadow"]["preflight"]["production_repo_required"])

    def test_ccxml_detection_is_unambiguous_or_pending(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            with mock.patch.dict(os.environ, {}, clear=False):
                self.assertEqual(hardware_bind.detect_ccxml(repo,{})["status"],"PENDING")
                (repo/"a.ccxml").write_text("a"); self.assertEqual(hardware_bind.detect_ccxml(repo,{})["status"],"READY")
                (repo/"b.ccxml").write_text("b"); many=hardware_bind.detect_ccxml(repo,{}); self.assertEqual(many["status"],"PENDING"); self.assertEqual(len(many["candidates"]),2)

    def test_project_metadata_parser(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/".project").write_text("<?xml version='1.0'?><projectDescription><name>P</name></projectDescription>")
            (p/".cproject").write_text("<?xml version='1.0'?><cproject><configuration artifactExtension='out' artifactName='${ProjName}' name='FLASH'/><option name='Compiler version' value='22.6.1.LTS'/><listOptionValue value='PRODUCTS=C2000WARE:5.4.0.00;'/></cproject>")
            actual=hardware_bind.parse_project(p); self.assertEqual(actual["project_name"],"P"); self.assertIn("FLASH",actual["configurations"]); self.assertIn("22.6.1.LTS",actual["compilers"]); self.assertEqual(actual["artifacts"][0]["extension"],"out")

    def test_canonical_build_plans_are_frozen_legacy_snapshot_data(self):
        registry = json.loads((ROOT / "engineering_data/federation/deprecation_registry.json").read_text())
        paths = {item["path"]: item for item in registry["items"]}
        self.assertEqual(paths["engineering_data/automation/"]["status"], "frozen_legacy_snapshot_contracts")
        self.assertEqual(paths["engineering_data/automation/"]["replacement_owner"], "linwuyen/ASR5K_v2_28384")
        self.assertIn("production_build_owner", registry["forbidden_new_workbench_authority"])

    def test_windows_entrypoint_is_deprecated_execution_path(self):
        text=(ROOT/"asrtest.ps1").read_text()
        self.assertIn("execution entrypoint is deprecated", text)
        self.assertIn("View / Analysis Plane", text)
        self.assertIn("linwuyen/ASR5K_v2_28384", text)
        self.assertNotIn("auto_run_ext.py", text)
        self.assertNotIn("hardware_bind.py", text)


if __name__ == "__main__":
    unittest.main()
