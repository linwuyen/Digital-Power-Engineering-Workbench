import unittest
from pathlib import Path

from workbench.status_evidence import qualification_for_sha

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "engineering_data"
SHA = "69919ddcaec1be5f0cf6fba24a21acc738587290"
EVIDENCE_GOLDEN = "c31ecc57a54f9f84874af40234907be357638ebe"
DIFFERENT_GOLDEN = "1111111111111111111111111111111111111111"


class RealQualificationEvidenceTests(unittest.TestCase):
    def gates(self, golden_sha: str | None = EVIDENCE_GOLDEN) -> dict[str, dict]:
        return {
            row["gate"]: row
            for row in qualification_for_sha(
                DATA_ROOT,
                SHA,
                {
                    "golden_sha": golden_sha,
                    "source": "CURRENT_PRODUCT_BASELINE.md",
                    "release_ref": "historical-golden",
                },
            )
        }

    def test_69919dd_regression_uses_exact_firmware_ci_evidence(self):
        gate = self.gates()["regression"]
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["sha"], SHA)
        self.assertEqual(gate["evidence_type"], "regression_history")
        self.assertEqual(
            gate["evidence"],
            "github-actions://linwuyen/ASR5K_v2_28384/runs/34588402658#host-regression",
        )

    def test_regression_pass_becomes_stale_after_golden_changes_with_visible_reason(self):
        gate = self.gates(DIFFERENT_GOLDEN)["regression"]
        self.assertEqual(gate["status"], "STALE")
        self.assertEqual(gate["sha"], SHA)
        self.assertEqual(gate["evidence_type"], "regression_history")
        self.assertEqual(
            gate["evidence"],
            "github-actions://linwuyen/ASR5K_v2_28384/runs/34588402658#host-regression",
        )
        self.assertIn(EVIDENCE_GOLDEN, gate["note"])
        self.assertIn(DIFFERENT_GOLDEN, gate["note"])

    def test_regression_pass_is_unknown_when_current_golden_is_unavailable_with_visible_reason(self):
        gate = self.gates(None)["regression"]
        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(gate["sha"], SHA)
        self.assertEqual(gate["evidence_type"], "regression_history")
        self.assertEqual(
            gate["evidence"],
            "github-actions://linwuyen/ASR5K_v2_28384/runs/34588402658#host-regression",
        )
        self.assertIn("current GOLDEN is unavailable", gate["note"])
        self.assertIn(EVIDENCE_GOLDEN, gate["note"])

    def test_69919dd_hil_is_pending_on_real_debug_infrastructure_blocker(self):
        gate = self.gates()["hil"]
        self.assertEqual(gate["status"], "PENDING")
        self.assertEqual(gate["sha"], SHA)
        self.assertEqual(gate["evidence_type"], "hardware_results")
        self.assertEqual(
            gate["evidence"],
            "github-actions://linwuyen/ASR5K_v2_28384/runs/34588487809#hardware-preflight",
        )
        self.assertEqual(gate["note"], "source result: BLOCKED")


if __name__ == "__main__":
    unittest.main()
