from __future__ import annotations

import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

from server import ROOT, WorkbenchHandler


BASELINE = "2b72f50648d86c11547645882248eed69f12892f"
# State truth convergence contract: production view has one evidence-bound source.


class FinalWorkbenchIntegrationTests(unittest.TestCase):
    def test_status_console_is_default_and_loader_reaches_both_status_layers(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        i18n = (ROOT / "static" / "i18n.js").read_text(encoding="utf-8")
        loader = (ROOT / "static" / "eng" / "loader.js").read_text(encoding="utf-8")
        status = (ROOT / "static" / "eng" / "status_console.js").read_text(encoding="utf-8")
        source = (ROOT / "static" / "eng" / "data_source.js").read_text(encoding="utf-8")
        self.assertIn('id="status" class="panel active"', html)
        self.assertIn("./eng/loader.js", i18n)
        self.assertIn("./eng/status_console.js", loader)
        self.assertIn("./eng/data_source.js", loader)
        self.assertIn("/api/status/summary", status)
        self.assertIn("../engineering_data/status/status_snapshot.json", status)
        self.assertNotIn("ASR5K_READ_TOKEN", status)
        self.assertIn("../engineering_data/", source)
        self.assertIn("FAIL CLOSED", source)
        self.assertIn("DERIVED SNAPSHOT", source)
        self.assertIn("SNAPSHOT VOCABULARY · PARTIAL TRANSITIONS", source)
        self.assertIn("federation/source_manifest.json", source)
        self.assertIn("authoritative_engineering_truth", source)

    def test_documentation_explains_live_snapshot_and_generator(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        status_doc = (ROOT / "docs" / "CURRENT_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("ASR5K Engineering Console", readme)
        self.assertIn("/api/status/summary", readme)
        self.assertIn("generate_status_snapshot.py", readme)
        self.assertIn("LIVE", readme)
        self.assertIn("SNAPSHOT", readme)
        self.assertIn("View / Analysis Plane", status_doc)
        self.assertIn("UNKNOWN", status_doc)

    def test_snapshot_baselines_are_identical(self):
        paths = [
            ROOT / "engineering_data" / "index.json",
            ROOT / "engineering_data" / "firmware" / "state_machine.json",
            ROOT / "engineering_data" / "verification" / "verification_matrix.json",
        ]
        values = []
        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            values.append(data["baseline"]["commit"] if path.name == "index.json" else data["baseline"])
        self.assertEqual(values, [BASELINE, BASELINE, BASELINE])

    def test_federation_marks_workbench_view_only(self):
        manifest = json.loads((ROOT / "engineering_data" / "federation" / "source_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["workbench_role"], "view_analysis_plane")
        self.assertFalse(manifest["authoritative_engineering_truth"])
        self.assertEqual(manifest["sources"]["control_plane"]["repository"], "linwuyen/ASR5K_AGENT")
        self.assertEqual(manifest["sources"]["execution_plane"]["repository"], "linwuyen/ASR5K_v2_28384")
        self.assertEqual(manifest["snapshot_policy"]["engineering_data_role"], "derived_snapshot_cache")
        self.assertFalse(manifest["snapshot_policy"]["may_override_control_plane"])
        self.assertFalse(manifest["snapshot_policy"]["may_override_execution_plane"])

    def test_view_plane_does_not_ship_execution_owners(self):
        retired_execution_paths = [
            "tools/auto_common.py",
            "tools/auto_run.py",
            "tools/auto_run_ext.py",
            "tools/ccs_build.py",
            "tools/evidence_agent.py",
            "tools/hardware_bind.py",
            "tools/hil_runner.py",
            "config/auto_run.ci.json",
            "config/auto_run.local.example.json",
        ]
        present = [path for path in retired_execution_paths if (ROOT / path).exists()]
        self.assertEqual(present, [])
        for retained_reader in [
            "tools/extract_source_truth.py",
            "tools/generate_status_snapshot.py",
            "tools/traceability.py",
            "tools/validate_federation.py",
            "tools/verify_truth_drift.py",
        ]:
            self.assertTrue((ROOT / retained_reader).is_file(), retained_reader)

    def test_production_state_view_has_one_snapshot_truth_and_no_reference_fallback(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        source = (ROOT / "static" / "eng" / "data_source.js").read_text(encoding="utf-8")
        system_tools = (ROOT / "static" / "eng" / "system_tools.js").read_text(encoding="utf-8")
        server_source = (ROOT / "server.py").read_text(encoding="utf-8")
        state_panel = html.split('<section id="state"', 1)[1].split('<section id="remote"', 1)[0]

        self.assertIn('id="stateTruthStatus"', state_panel)
        self.assertNotIn('id="simState"', state_panel)
        self.assertNotIn('data-i18n="state.simulator"', state_panel)
        self.assertNotIn("STATE_MACHINE", app)
        self.assertNotIn("loadStateMachine", app)
        self.assertNotIn("/api/state-machine", app)
        self.assertNotIn("/api/state-machine", server_source)
        self.assertNotIn("get_state_machine", server_source)
        self.assertFalse((ROOT / "workbench" / "state_machine.py").exists())
        self.assertIn("renderProductionStateUnavailable", source)
        self.assertIn("STATE TRUTH UNAVAILABLE", source)
        self.assertNotIn("REF_CONTRACT", system_tools)

    def test_state_machine_api_is_retired(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"http://{host}:{port}/api/state-machine", timeout=3)
            self.assertEqual(ctx.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_local_server_exposes_snapshot_data_and_blocks_traversal(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            with urlopen(f"http://{host}:{port}/engineering_data/index.json", timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertTrue(response.headers["Content-Type"].startswith("application/json"))
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["baseline"]["commit"], BASELINE)
                self.assertFalse(payload["authoritative_engineering_truth"])

            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"http://{host}:{port}/engineering_data/%2e%2e/server.py", timeout=3)
            self.assertEqual(ctx.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_pending_hardware_snapshot_remains_unqualified(self):
        matrix = json.loads((ROOT / "engineering_data" / "verification" / "verification_matrix.json").read_text(encoding="utf-8"))
        status = {row["item"]: row["status"] for row in matrix["scope"]}
        self.assertEqual(status["ADC measurement scaling/calibration"], "PENDING")
        self.assertEqual(status["formal numerical SPIB response deadline"], "PENDING")
        self.assertEqual(status["hardware protection shutdown latency"], "PENDING")
        self.assertEqual(status["board/HIL/AM3352 A-B qualification at baseline"], "NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()
