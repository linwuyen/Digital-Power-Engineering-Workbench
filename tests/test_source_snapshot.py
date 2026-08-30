import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from truth_common import load_json  # noqa: E402
from verify_truth_drift import compare  # noqa: E402


BASELINE = "2b72f50648d86c11547645882248eed69f12892f"


class PinnedSourceSnapshotTest(unittest.TestCase):
    def test_snapshot_is_exact_baseline_and_matches_canonical_truth(self):
        snapshot = load_json(ROOT / "engineering_data/source_truth/snapshot-2b72f506.json")
        self.assertEqual(snapshot["baseline"], BASELINE)
        self.assertTrue(snapshot["policy"]["source_only"])
        self.assertTrue(snapshot["policy"]["unknown_values_are_not_inferred"])
        self.assertTrue(snapshot["policy"]["diagnostic_thresholds_are_not_deadlines"])
        report = compare(snapshot, ROOT / "engineering_data")
        self.assertEqual(report["status"], "PASS", report["errors"])

    def test_index_declares_live_private_check_as_optional_secret_gate(self):
        index = load_json(ROOT / "engineering_data/index.json")
        self.assertEqual(index["resources"]["source_truth_snapshot"], "source_truth/snapshot-2b72f506.json")
        policy = index["consumer_policy"]
        self.assertTrue(policy["pinned_source_snapshot_check_required"])
        self.assertTrue(policy["live_private_source_check_requires_secret"])
        self.assertEqual(policy["live_private_source_check_secret_name"], "ASR5K_READ_TOKEN")
        self.assertEqual(policy["missing_live_private_source_secret_action"], "explicit_skip_without_live_claim")


if __name__ == "__main__":
    unittest.main()
