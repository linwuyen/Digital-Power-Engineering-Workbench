import subprocess
import tempfile
import unittest
from pathlib import Path

from workbench.status_live import (
    parse_product_baseline,
    read_product_baseline,
    relation_to_golden,
    repo_identity,
)


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=check,
    )
    return result.stdout.strip()


class StatusLiveTests(unittest.TestCase):
    def make_repo(self, root: Path) -> str:
        git(root, "init")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "Status Test")
        (root / "file.txt").write_text("one\n", encoding="utf-8")
        git(root, "add", "file.txt")
        git(root, "commit", "-m", "one")
        return git(root, "rev-parse", "HEAD")

    def test_repo_identity_reports_dirty_without_mutating_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sha = self.make_repo(root)
            (root / "file.txt").write_text("two\n", encoding="utf-8")
            identity = repo_identity(root)
            self.assertEqual(identity["sha"], sha)
            self.assertTrue(identity["dirty"])
            self.assertEqual(git(root, "rev-parse", "HEAD"), sha)

    def test_product_baseline_parser_requires_exact_labeled_values(self):
        sha = "c31ecc57a54f9f84874af40234907be357638ebe"
        parsed = parse_product_baseline(
            "FINAL / GOLDEN firmware SHA:\n"
            f"{sha}\n\n"
            "Pinned release ref:\n"
            "release/final-c31ecc57-20260908\n"
        )
        self.assertEqual(parsed["golden_sha"], sha)
        self.assertEqual(parsed["release_ref"], "release/final-c31ecc57-20260908")

    def test_product_baseline_parser_fails_closed_when_release_ref_missing(self):
        with self.assertRaises(ValueError):
            parse_product_baseline(
                "FINAL / GOLDEN firmware SHA:\n"
                "c31ecc57a54f9f84874af40234907be357638ebe\n"
            )

    def test_product_baseline_comes_from_committed_head_not_dirty_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            committed_golden = "a" * 40
            dirty_golden = "b" * 40
            baseline = root / "CURRENT_PRODUCT_BASELINE.md"
            baseline.write_text(
                "FINAL / GOLDEN firmware SHA:\n"
                f"{committed_golden}\n\n"
                "Pinned release ref:\nrelease/committed\n",
                encoding="utf-8",
            )
            git(root, "add", "CURRENT_PRODUCT_BASELINE.md")
            git(root, "commit", "-m", "baseline")
            head = git(root, "rev-parse", "HEAD")

            baseline.write_text(
                "FINAL / GOLDEN firmware SHA:\n"
                f"{dirty_golden}\n\n"
                "Pinned release ref:\nrelease/dirty\n",
                encoding="utf-8",
            )

            parsed = read_product_baseline(root)
            self.assertEqual(parsed["golden_sha"], committed_golden)
            self.assertEqual(parsed["release_ref"], "release/committed")
            self.assertEqual(parsed["firmware_repository_sha"], head)

    def test_relation_is_match_then_ahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            golden = self.make_repo(root)
            self.assertEqual(relation_to_golden(root, golden, golden), "MATCH")
            (root / "file.txt").write_text("two\n", encoding="utf-8")
            git(root, "add", "file.txt")
            git(root, "commit", "-m", "two")
            head = git(root, "rev-parse", "HEAD")
            self.assertEqual(relation_to_golden(root, head, golden), "AHEAD")


if __name__ == "__main__":
    unittest.main()
