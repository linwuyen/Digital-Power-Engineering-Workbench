import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StateTruthBoundaryTests(unittest.TestCase):
    def test_production_state_has_no_reference_fallback_owner(self):
        app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        server = (ROOT / "server.py").read_text(encoding="utf-8")

        self.assertNotIn("const STATE_MACHINE", app)
        self.assertNotIn("/api/state-machine", app)
        self.assertNotIn("get_state_machine", server)
        self.assertNotIn('route == "/api/state-machine"', server)
        self.assertFalse((ROOT / "workbench" / "state_machine.py").exists())

    def test_production_state_fails_closed_when_truth_is_unavailable(self):
        source = (ROOT / "static" / "eng" / "data_source.js").read_text(encoding="utf-8")

        self.assertIn("function renderProductionStateUnavailable", source)
        self.assertIn("STATE VIEW UNAVAILABLE", source)
        self.assertIn("renderProductionStateUnavailable(error.message)", source)

    def test_production_state_uses_only_extracted_snapshot_vocabulary(self):
        source = (ROOT / "static" / "eng" / "data_source.js").read_text(encoding="utf-8")
        snapshot = (ROOT / "engineering_data" / "firmware" / "state_machine.json").read_text(encoding="utf-8")

        self.assertIn("renderProductionState(loaded)", source)
        self.assertIn('"transition_completeness":"partial"', snapshot)
        for invented_reference_state in ["STANDBY", "PRECHARGE", "SOFT_START", "STOP"]:
            self.assertNotIn(f'"id":"{invented_reference_state}"', snapshot)


if __name__ == "__main__":
    unittest.main()
