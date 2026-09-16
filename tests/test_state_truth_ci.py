from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StateTruthCiTests(unittest.TestCase):
    def test_state_truth_module_is_syntax_checked_by_ci(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("node --check static/eng/state_truth.js", workflow)


if __name__ == "__main__":
    unittest.main()
