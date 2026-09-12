from __future__ import annotations

from pathlib import Path
import re
import subprocess


_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_BASELINE_RE = re.compile(
    r"FINAL / GOLDEN firmware SHA:\s*\n(?P<sha>[0-9a-fA-F]{40})"
    r".*?Pinned release ref:\s*\n(?P<ref>[^\r\n`]+)",
    re.S,
)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=check,
    )


def _git_output(repo: Path, *args: str) -> str:
    result = _git(repo, *args)
    return result.stdout.strip()


def repo_identity(repo: Path) -> dict:
    root = Path(repo).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"repository path not found: {root}")
    top = Path(_git_output(root, "rev-parse", "--show-toplevel")).resolve()
    if top != root:
        raise ValueError(f"configured repository root is not git top-level: {root}")
    sha = _git_output(root, "rev-parse", "HEAD")
    if not _SHA_RE.fullmatch(sha):
        raise ValueError("git HEAD is not a 40-hex SHA")
    return {
        "path": str(root),
        "sha": sha,
        "branch": _git_output(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(_git_output(root, "status", "--porcelain")),
    }


def parse_product_baseline(text: str) -> dict:
    match = _BASELINE_RE.search(text)
    if not match:
        raise ValueError("product baseline is missing labeled GOLDEN SHA or release ref")
    release_ref = match.group("ref").strip()
    if not release_ref or any(ch.isspace() for ch in release_ref):
        raise ValueError("product baseline release ref is invalid")
    return {
        "golden_sha": match.group("sha").lower(),
        "release_ref": release_ref,
        "source": "CURRENT_PRODUCT_BASELINE.md",
    }


def read_product_baseline(firmware_root: Path) -> dict:
    root = Path(firmware_root).expanduser().resolve()
    identity = repo_identity(root)
    committed_text = _git_output(
        root,
        "show",
        f"{identity['sha']}:CURRENT_PRODUCT_BASELINE.md",
    )
    parsed = parse_product_baseline(committed_text)
    parsed["firmware_repository_sha"] = identity["sha"]
    return parsed


def relation_to_golden(
    firmware_root: Path,
    current_sha: str,
    golden_sha: str,
) -> str:
    if not (_SHA_RE.fullmatch(current_sha or "") and _SHA_RE.fullmatch(golden_sha or "")):
        return "UNKNOWN"
    if current_sha == golden_sha:
        return "MATCH"
    root = Path(firmware_root).expanduser().resolve()
    try:
        repo_identity(root)
    except (OSError, ValueError, subprocess.SubprocessError):
        return "UNKNOWN"
    current_exists = _git(root, "cat-file", "-e", f"{current_sha}^{{commit}}", check=False)
    golden_exists = _git(root, "cat-file", "-e", f"{golden_sha}^{{commit}}", check=False)
    if current_exists.returncode != 0 or golden_exists.returncode != 0:
        return "UNKNOWN"
    ancestor = _git(root, "merge-base", "--is-ancestor", golden_sha, current_sha, check=False)
    if ancestor.returncode == 0:
        return "AHEAD"
    if ancestor.returncode == 1:
        return "DIVERGED"
    return "UNKNOWN"
