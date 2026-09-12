import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StatusFrontendTests(unittest.TestCase):
    def test_status_is_default_panel_and_tools_remain_present(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-panel="status"', html)
        self.assertIn('id="status" class="panel active"', html)
        self.assertIn('data-panel="measurement"', html)
        self.assertIn('data-panel="control"', html)
        self.assertIn('data-panel="state"', html)

    def test_status_loader_has_live_then_snapshot_fallback(self):
        js = (ROOT / "static" / "eng" / "status_console.js").read_text(encoding="utf-8")
        self.assertIn("/api/status/summary", js)
        self.assertIn("../engineering_data/status/status_snapshot.json", js)
        self.assertNotIn("ASR5K_READ_TOKEN", js)

    def test_remote_is_not_primary_nav(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        primary = html.split('id="engineering-tools"', 1)[0]
        self.assertNotIn('data-panel="remote"', primary)


if __name__ == "__main__":
    unittest.main()
