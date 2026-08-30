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


class FinalWorkbenchIntegrationTests(unittest.TestCase):
    def test_browser_loader_reaches_truth_layer(self):
        i18n = (ROOT / "static" / "i18n.js").read_text(encoding="utf-8")
        loader = (ROOT / "static" / "eng" / "loader.js").read_text(encoding="utf-8")
        source = (ROOT / "static" / "eng" / "data_source.js").read_text(encoding="utf-8")
        self.assertIn("./eng/loader.js", i18n)
        self.assertIn("./eng/data_source.js", loader)
        self.assertIn("../engineering_data/", source)
        self.assertIn("FAIL CLOSED", source)
        self.assertIn("PRODUCTION VOCABULARY · PARTIAL TRANSITIONS", source)

    def test_truth_baselines_are_identical(self):
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

    def test_local_server_exposes_truth_data_and_blocks_traversal(self):
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

            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"http://{host}:{port}/engineering_data/%2e%2e/server.py", timeout=3)
            self.assertEqual(ctx.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_pending_hardware_truth_remains_unqualified(self):
        matrix = json.loads((ROOT / "engineering_data" / "verification" / "verification_matrix.json").read_text(encoding="utf-8"))
        status = {row["item"]: row["status"] for row in matrix["scope"]}
        self.assertEqual(status["ADC measurement scaling/calibration"], "PENDING")
        self.assertEqual(status["formal numerical SPIB response deadline"], "PENDING")
        self.assertEqual(status["hardware protection shutdown latency"], "PENDING")
        self.assertEqual(status["board/HIL/AM3352 A-B qualification at baseline"], "NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()
