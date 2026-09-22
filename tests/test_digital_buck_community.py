import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "training" / "digital-buck"
PAGE = LAB / "index.html"
APP = LAB / "app.js"
LOCALIZED_APP = LAB / "localized-app.js"
CONFIG = LAB / "product-config.js"
EN_PAGE = LAB / "en" / "index.html"
ZH_CN_PAGE = LAB / "zh-cn" / "index.html"


class DigitalBuckCommunityEditionTests(unittest.TestCase):
    def test_public_routes_exist(self):
        for path in (PAGE, APP, LOCALIZED_APP, CONFIG, EN_PAGE, ZH_CN_PAGE):
            self.assertTrue(path.exists(), path)

    def test_each_public_page_exposes_exactly_four_previews(self):
        for path in (PAGE, EN_PAGE, ZH_CN_PAGE):
            html = path.read_text(encoding="utf-8")
            self.assertIn("FREE COMMUNITY EDITION", html)
            self.assertEqual(html.count("PREVIEW "), 4, path)
            self.assertNotIn("19_c2000_buck_firmware_lab", html)
            self.assertNotIn("Circuit-Simulation/", html)

    def test_localized_pages_share_checkout_config(self):
        en = EN_PAGE.read_text(encoding="utf-8")
        zh = ZH_CN_PAGE.read_text(encoding="utf-8")
        self.assertIn('src="../product-config.js"', en)
        self.assertIn('src="../product-config.js"', zh)
        self.assertIn('src="../localized-app.js"', en)
        self.assertIn('src="../localized-app.js"', zh)

    def test_checkout_defaults_fail_closed(self):
        config = CONFIG.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        localized = LOCALIZED_APP.read_text(encoding="utf-8")
        self.assertIn('checkoutUrl: ""', config)
        for script in (app, localized):
            self.assertIn('aria-disabled', script)
            self.assertIn('if (!value) return false;', script)
            self.assertIn('new URL(value)', script)

    def test_paid_scope_is_described_without_embedding_full_lab(self):
        for path in (PAGE, EN_PAGE, ZH_CN_PAGE):
            html = path.read_text(encoding="utf-8")
            self.assertIn("01 Power Physics", html)
            self.assertIn("08 Evidence", html)
            self.assertNotIn("Host SIL", html)
            self.assertNotIn("CONTROL_VALIDATION_PASS", html)

    def test_market_positioning_is_outcome_driven(self):
        en = EN_PAGE.read_text(encoding="utf-8")
        zh = ZH_CN_PAGE.read_text(encoding="utf-8")
        self.assertIn("Debug the whole digital-power loop", en)
        self.assertIn("会写 C，不代表会调数字电源", zh)
        self.assertIn("symptom → hypothesis → measurement → falsification → fix", en)
        self.assertIn("现象 → 假设 → 测量 → 反证 → 修正", zh)


if __name__ == "__main__":
    unittest.main()
