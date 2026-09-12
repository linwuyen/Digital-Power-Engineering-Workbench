from datetime import datetime, timezone
import unittest

from workbench.status_model import (
    GATES,
    bind_gate_to_sha,
    classify_freshness,
    derive_blockers,
    make_gate,
    validate_status_model,
)


SHA = "a" * 40
OTHER = "b" * 40


def valid_model() -> dict:
    return {
        "schema_version": "1.0",
        "mode": "LIVE",
        "generated_at": "2026-09-12T12:00:00+00:00",
        "health": "OK",
        "control_plane": {"repository": "linwuyen/ASR5K_AGENT", "sha": SHA, "branch": "main", "status": "CURRENT"},
        "execution_plane": {"repository": "linwuyen/ASR5K_v2_28384", "sha": SHA, "branch": "main", "dirty": False},
        "product_baseline": {"golden_sha": SHA, "release_ref": "release/final", "source": "CURRENT_PRODUCT_BASELINE.md"},
        "identity": {"relation_to_golden": "MATCH", "evidence_sha_match": True, "control_plane_revision_known": True},
        "qualification": [make_gate(gate, "UNKNOWN") for gate in GATES],
        "blockers": [],
        "freshness": {"status": "LIVE", "age_seconds": 0, "sources": []},
    }


class StatusModelTests(unittest.TestCase):
    def test_pass_requires_sha_and_evidence(self):
        with self.assertRaises(ValueError):
            make_gate("build", "PASS", sha=SHA, evidence=None)

    def test_evidence_for_other_sha_becomes_mismatch(self):
        row = make_gate("build", "PASS", sha=OTHER, evidence="run-17")
        bound = bind_gate_to_sha(row, SHA)
        self.assertEqual(bound["status"], "MISMATCH")
        self.assertEqual(bound["sha"], OTHER)

    def test_unknown_never_requires_fake_evidence(self):
        row = make_gate("hil", "UNKNOWN")
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertIsNone(row["evidence"])

    def test_snapshot_becomes_stale_after_threshold(self):
        now = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
        state = classify_freshness("2026-09-12T09:00:00+00:00", now, 3600)
        self.assertEqual(state, "STALE")

    def test_blockers_distinguish_fail_unknown_and_stale(self):
        model = {
            "qualification": [
                make_gate("build", "FAIL", sha=SHA, evidence="build.log"),
                make_gate("hil", "UNKNOWN"),
            ],
            "identity": {"relation_to_golden": "MATCH", "evidence_sha_match": True},
            "freshness": {"status": "STALE"},
        }
        categories = {x["category"] for x in derive_blockers(model)}
        self.assertIn("FIRMWARE_BLOCKER", categories)
        self.assertIn("UNKNOWN_EVIDENCE", categories)
        self.assertIn("STALE_SOURCE", categories)

    def test_golden_is_only_valid_for_production_gate(self):
        with self.assertRaises(ValueError):
            make_gate("build", "GOLDEN", sha=SHA, evidence="CURRENT_PRODUCT_BASELINE.md")

    def test_model_validation_rejects_pass_bound_to_wrong_execution_sha(self):
        model = valid_model()
        model["qualification"][GATES.index("build")] = make_gate("build", "PASS", sha=OTHER, evidence="build.log")
        with self.assertRaises(ValueError):
            validate_status_model(model)

    def test_model_validation_requires_every_gate_exactly_once(self):
        model = valid_model()
        model["qualification"] = model["qualification"][:-1]
        with self.assertRaises(ValueError):
            validate_status_model(model)

        model = valid_model()
        model["qualification"].append(make_gate("build", "UNKNOWN"))
        with self.assertRaises(ValueError):
            validate_status_model(model)


if __name__ == "__main__":
    unittest.main()
