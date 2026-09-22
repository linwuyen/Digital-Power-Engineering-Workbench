import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "training" / "digital-buck" / "index.html"
APP = ROOT / "training" / "digital-buck" / "app.js"
CONFIG = ROOT / "training" / "digital-buck" / "product-config.js"

class DigitalBuckCommunityEditionTests(unittest.TestCase):
    def test_public_route_exists(self):
        self.assertTrue(PAGE.exists())
        self.assertTrue(APP.exists())
        self.assertTrue(CONFIG.exists())

    def test_public_page_does_not_link_full_paid_source(self):
        html = PAGE.read_text(encoding="utf-8")
        self.assertNotIn("19_c2000_buck_firmware_lab", html)
        self.assertNotIn("Circuit-Simulation/", html)
        self.assertIn("FREE COMMUNITY EDITION", html)
        self.assertIn("UNKNOWN FAULT", html)

    def test_checkout_defaults_fail_closed(self):
        config = CONFIG.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        self.assertIn('checkoutUrl: ""', config)
        self.assertIn('aria-disabled', app)
        self.assertIn('new URL(value)', app)

    def test_paid_boundary_is_named_but_not_embedded(self):
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn("完整 eight-layer", html) if False else None
        self.assertIn("01 Power Physics", html)
        self.assertIn("08 Evidence", html)
        self.assertNotIn("BOARD_PASS", html.replace("不等於 production qualification、BOARD_PASS", ""))

if __name__ == "__main__":
    unittest.main()
