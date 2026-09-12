from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

from .status_evidence import evidence_details_for_sha, qualification_for_sha
from .status_live import read_product_baseline, relation_to_golden, repo_identity
from .status_model import GATES, derive_blockers, make_gate, validate_status_model


CONTROL_REPO = "linwuyen/ASR5K_AGENT"
EXECUTION_REPO = "linwuyen/ASR5K_v2_28384"
EVIDENCE_UNAVAILABLE_NOTE = "evidence source malformed or unreadable"


def _unknown_repo(repository: str) -> dict:
    return {
        "repository": repository,
        "sha": None,
        "branch": None,
        "dirty": None,
        "status": "UNAVAILABLE",
    }


def _read_identity(repository: str, root: Path) -> dict:
    return {"repository": repository, **repo_identity(root), "status": "CURRENT"}


def _unknown_evidence_qualification(note: str) -> list[dict]:
    return [make_gate(gate, "UNKNOWN", note=note) for gate in GATES]


def build_live_status(
    agent_root: Path,
    firmware_root: Path,
    data_root: Path,
    *,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    health = "OK"

    try:
        agent = _read_identity(CONTROL_REPO, Path(agent_root))
    except (OSError, ValueError, subprocess.SubprocessError):
        agent = _unknown_repo(CONTROL_REPO)
        health = "DEGRADED"

    try:
        firmware = _read_identity(EXECUTION_REPO, Path(firmware_root))
    except (OSError, ValueError, subprocess.SubprocessError):
        firmware = _unknown_repo(EXECUTION_REPO)
        health = "DEGRADED"

    golden = {
        "golden_sha": None,
        "release_ref": None,
        "source": "CURRENT_PRODUCT_BASELINE.md",
    }
    if firmware.get("sha"):
        try:
            golden = read_product_baseline(Path(firmware_root))
        except (OSError, ValueError, subprocess.SubprocessError):
            health = "DEGRADED"

    relation = "UNKNOWN"
    if firmware.get("sha") and golden.get("golden_sha"):
        relation = relation_to_golden(
            Path(firmware_root), firmware["sha"], golden["golden_sha"]
        )
        if relation in {"DIVERGED", "UNKNOWN"}:
            health = "DEGRADED"

    if firmware.get("sha"):
        try:
            qualification = qualification_for_sha(
                Path(data_root), firmware["sha"], golden
            )
        except (OSError, ValueError):
            health = "DEGRADED"
            qualification = _unknown_evidence_qualification(EVIDENCE_UNAVAILABLE_NOTE)
        by_gate = {row["gate"]: row for row in qualification}
        by_gate["source"] = make_gate(
            "source",
            "PASS",
            sha=firmware["sha"],
            evidence="git rev-parse HEAD",
            evidence_type="git_identity",
            timestamp=now.isoformat(),
        )
        qualification = [by_gate[gate] for gate in GATES]
    else:
        qualification = [make_gate(gate, "UNKNOWN") for gate in GATES]

    execution_sha = firmware.get("sha")
    strong_rows = [
        row
        for row in qualification
        if row.get("status") in {"PASS", "FAIL", "GOLDEN"}
    ]
    evidence_sha_match = (
        all(row.get("sha") == execution_sha for row in strong_rows)
        if execution_sha
        else None
    )

    model = {
        "schema_version": "1.0",
        "mode": "LIVE",
        "generated_at": now.isoformat(),
        "health": health,
        "control_plane": agent,
        "execution_plane": firmware,
        "product_baseline": golden,
        "identity": {
            "relation_to_golden": relation,
            "evidence_sha_match": evidence_sha_match,
            "control_plane_revision_known": bool(agent.get("sha")),
        },
        "qualification": qualification,
        "blockers": [],
        "freshness": {
            "status": "LIVE",
            "age_seconds": 0,
            "sources": [
                {"repository": CONTROL_REPO, "available": bool(agent.get("sha"))},
                {"repository": EXECUTION_REPO, "available": bool(firmware.get("sha"))},
            ],
        },
    }
    model["blockers"] = derive_blockers(model)
    validate_status_model(model)
    return model


def build_live_evidence(
    agent_root: Path,
    firmware_root: Path,
    data_root: Path,
) -> dict:
    status = build_live_status(agent_root, firmware_root, data_root)
    execution_sha = status.get("execution_plane", {}).get("sha")
    note = None
    try:
        records = (
            evidence_details_for_sha(Path(data_root), execution_sha)
            if execution_sha
            else []
        )
    except (OSError, ValueError):
        records = []
        note = EVIDENCE_UNAVAILABLE_NOTE
    return {
        "schema_version": "1.0",
        "mode": "LIVE",
        "health": "DEGRADED" if note else status.get("health", "OK"),
        "execution_sha": execution_sha,
        "control_plane_sha": status.get("control_plane", {}).get("sha"),
        "records": records,
        "note": note,
    }
