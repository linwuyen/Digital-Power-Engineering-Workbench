import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from workbench.status_model import GATES, make_gate
from workbench.status_snapshot import (
    load_snapshot,
    sanitize_public_status,
    validate_public_snapshot,
)

SHA = "a" * 40


def live_model() -> dict:
    qualification = [make_gate(gate, "UNKNOWN") for gate in GATES]
    qualification[GATES.index("source")] = make_gate(
        "source",
        "PASS",
        sha=SHA,
        evidence="git rev-parse HEAD",
        evidence_type="git_identity",
        timestamp="2026-09-12T10:00:00+00:00",
    )
    return {
        "schema_version": "1.0",
        "mode": "LIVE",
        "generated_at": "2026-09-12T10:00:00+00:00",
        "health": "OK",
        "control_plane": {
            "repository": "linwuyen/ASR5K_AGENT",
            "sha": SHA,
            "branch": "main",
            "dirty": False,
            "status": "CURRENT",
            "path": "/home/user/ASR5K_AGENT",
        },
        "execution_plane": {
            "repository": "linwuyen/ASR5K_v2_28384",
            "sha": SHA,
            "branch": "main",
            "dirty": False,
            "status": "CURRENT",
            "path": "C:\\work\\ASR5K_v2_28384",
        },
        "product_baseline": {
            "golden_sha": SHA,
            "release_ref": "release/final-test",
            "source": "CURRENT_PRODUCT_BASELINE.md",
        },
        "identity": {
            "relation_to_golden": "MATCH",
            "evidence_sha_match": True,
            "control_plane_revision_known": True,
        },
        "qualification": qualification,
        "blockers": [],
        "freshness": {"status": "LIVE", "age_seconds": 0, "sources": []},
    }


class StatusSnapshotTests(unittest.TestCase):
    def test_sanitizer_removes_local_only_fields_and_marks_snapshot(self):
        public = sanitize_public_status(live_model(), generated_at="2026-09-12T10:00:00+00:00")
        self.assertEqual(public["mode"], "SNAPSHOT")
        self.assertFalse(public["authoritative_engineering_truth"])
        self.assertNotIn("path", public["control_plane"])
        self.assertNotIn("path", public["execution_plane"])
        self.assertIsNone(public["execution_plane"]["dirty"])
        self.assertEqual(public["freshness"]["status"], "SNAPSHOT")

    def test_sanitizer_does_not_publish_absolute_local_paths_in_strings(self):
        model = live_model()
        model["qualification"][GATES.index("build")] = make_gate(
            "build",
            "PASS",
            sha=SHA,
            evidence="C:\\Users\\private\\build.log",
            evidence_type="regression_history",
            note="local source /home/private/asr5k/build.log",
        )
        public = sanitize_public_status(model, generated_at="2026-09-12T10:00:00+00:00")
        encoded = json.dumps(public)
        self.assertNotIn("C:\\\\Users\\\\private", encoded)
        self.assertNotIn("/home/private/asr5k", encoded)

    def test_stale_snapshot_is_downgraded_and_gets_blocker(self):
        public = sanitize_public_status(live_model(), generated_at="2026-09-12T10:00:00+00:00")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.json"
            path.write_text(json.dumps(public), encoding="utf-8")
            loaded = load_snapshot(
                path,
                now=datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc),
                stale_after_seconds=3600,
            )
        self.assertEqual(loaded["freshness"]["status"], "STALE")
        self.assertEqual(loaded["freshness"]["age_seconds"], 7200)
        self.assertTrue(any(x["category"] == "STALE_SOURCE" for x in loaded["blockers"]))

    def test_snapshot_rejects_authoritative_claim(self):
        public = sanitize_public_status(live_model(), generated_at="2026-09-12T10:00:00+00:00")
        public["authoritative_engineering_truth"] = True
        with self.assertRaises(ValueError):
            validate_public_snapshot(public)


if __name__ == "__main__":
    unittest.main()
