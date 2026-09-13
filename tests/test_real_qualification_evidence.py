import unittest
from pathlib import Path

from workbench.status_evidence import qualification_for_sha

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "engineering_data"
SHA = "69919ddcaec1be5f0cf6fba24a21acc738587290"
OTHER_GOLDEN = "c31ecc57a54f9f84874af40234907be357638ebe"


class RealQualificationEvidenceTests(unittest.TestCase):
    def gates(self) -> dict[str, dict]:
        return {
            row["gate"]: row
            for row in qualification_for_sha(
                DATA_ROOT,
                SHA,
                {
                    "golden_sha": OTHER_GOLDEN,
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
