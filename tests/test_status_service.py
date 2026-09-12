import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from workbench.status_service import build_live_status


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True)
    return result.stdout.strip()


def init_repo(root: Path, *, baseline: bool = False) -> str:
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Status Test")
    (root / "file.txt").write_text("one\n", encoding="utf-8")
    if baseline:
        (root / "CURRENT_PRODUCT_BASELINE.md").write_text("placeholder\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "initial")
    sha = git(root, "rev-parse", "HEAD")
    if baseline:
        (root / "CURRENT_PRODUCT_BASELINE.md").write_text(
            "FINAL / GOLDEN firmware SHA:\n"
            f"{sha}\n\n"
            "Pinned release ref:\nrelease/final-test\n",
            encoding="utf-8",
        )
        git(root, "add", "CURRENT_PRODUCT_BASELINE.md")
        git(root, "commit", "-m", "baseline declaration")
        # Current HEAD is intentionally one commit ahead of the declared GOLDEN.
        return git(root, "rev-parse", "HEAD")
    return sha


def write_empty_data(root: Path) -> None:
    (root / "evidence").mkdir(parents=True)
    (root / "verification" / "regression_history").mkdir(parents=True)
    (root / "verification" / "hardware_results").mkdir(parents=True)
    (root / "evidence" / "evidence_ledger.jsonl").write_text(
        json.dumps({"record_type": "ledger_meta", "baseline": "0" * 40}) + "\n",
        encoding="utf-8",
    )
    (root / "verification" / "regression_history" / "index.json").write_text('{"records":[]}\n', encoding="utf-8")
    (root / "verification" / "hardware_results" / "index.json").write_text('{"records":[]}\n', encoding="utf-8")


class StatusServiceTests(unittest.TestCase):
    def test_live_model_reports_current_sources_and_unknown_unproven_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            agent = base / "agent"; agent.mkdir()
            firmware = base / "firmware"; firmware.mkdir()
            data = base / "data"
            init_repo(agent)
            init_repo(firmware, baseline=True)
            write_empty_data(data)
            model = build_live_status(agent, firmware, data, now=datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc))
            self.assertEqual(model["mode"], "LIVE")
            self.assertEqual(model["freshness"]["status"], "LIVE")
            self.assertIn(model["identity"]["relation_to_golden"], {"MATCH", "AHEAD"})
            build = next(x for x in model["qualification"] if x["gate"] == "build")
            self.assertEqual(build["status"], "UNKNOWN")

    def test_missing_agent_degrades_without_erasing_firmware(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            firmware = base / "firmware"; firmware.mkdir()
            data = base / "data"
            init_repo(firmware, baseline=True)
            write_empty_data(data)
            model = build_live_status(base / "missing-agent", firmware, data)
            self.assertEqual(model["health"], "DEGRADED")
            self.assertIsNone(model["control_plane"]["sha"])
            self.assertIsNotNone(model["execution_plane"]["sha"])

    def test_missing_firmware_has_unknown_relation_and_no_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            agent = base / "agent"; agent.mkdir()
            data = base / "data"
            init_repo(agent)
            write_empty_data(data)
            model = build_live_status(agent, base / "missing-firmware", data)
            self.assertEqual(model["identity"]["relation_to_golden"], "UNKNOWN")
            self.assertIsNone(model["identity"]["evidence_sha_match"])
            self.assertTrue(all(x["status"] == "UNKNOWN" for x in model["qualification"]))
            self.assertFalse(any(x["category"] == "IDENTITY_MISMATCH" for x in model["blockers"]))

    def test_dirty_firmware_is_reported_but_not_auto_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            agent = base / "agent"; agent.mkdir()
            firmware = base / "firmware"; firmware.mkdir()
            data = base / "data"
            init_repo(agent)
            init_repo(firmware, baseline=True)
            write_empty_data(data)
            (firmware / "file.txt").write_text("dirty\n", encoding="utf-8")
            model = build_live_status(agent, firmware, data)
            self.assertTrue(model["execution_plane"]["dirty"])
            source = next(x for x in model["qualification"] if x["gate"] == "source")
            self.assertEqual(source["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
