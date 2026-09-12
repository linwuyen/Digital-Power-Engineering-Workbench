from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re


GATES = (
    "source",
    "build",
    "regression",
    "artifact",
    "flash",
    "board",
    "hil",
    "protection",
    "production",
)

VALID_GATE_STATES = frozenset(
    {
        "PASS",
        "FAIL",
        "PENDING",
        "UNKNOWN",
        "NOT_RUN",
        "NOT_REQUIRED",
        "STALE",
        "MISMATCH",
        "GOLDEN",
    }
)

_HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
_STRONG_STATES = frozenset({"PASS", "FAIL", "GOLDEN"})


def _valid_sha(value: str | None) -> bool:
    return bool(value and _HEX40.fullmatch(str(value)))


def make_gate(
    gate: str,
    status: str,
    *,
    sha: str | None = None,
    evidence: str | None = None,
    evidence_type: str | None = None,
    timestamp: str | None = None,
    note: str | None = None,
) -> dict:
    gate = str(gate).lower()
    status = str(status).upper()
    if gate not in GATES:
        raise ValueError(f"unsupported qualification gate: {gate}")
    if status not in VALID_GATE_STATES:
        raise ValueError(f"unsupported gate status: {status}")
    if status in _STRONG_STATES:
        if not _valid_sha(sha):
            raise ValueError(f"{status} requires an exact 40-hex sha")
        if not evidence:
            raise ValueError(f"{status} requires explicit evidence")
    if status == "GOLDEN" and gate != "production":
        raise ValueError("GOLDEN is valid only for production")
    return {
        "gate": gate,
        "status": status,
        "sha": sha,
        "evidence": evidence,
        "evidence_type": evidence_type,
        "timestamp": timestamp,
        "note": note,
    }


def bind_gate_to_sha(row: dict, expected_sha: str | None) -> dict:
    bound = deepcopy(row)
    if expected_sha and bound.get("status") in _STRONG_STATES:
        if bound.get("sha") != expected_sha:
            bound["status"] = "MISMATCH"
            bound["note"] = (
                f"evidence SHA {bound.get('sha')} != execution SHA {expected_sha}"
            )
    return bound


def classify_freshness(
    generated_at: str | None,
    now: datetime,
    stale_after_seconds: int,
) -> str:
    if stale_after_seconds < 0:
        raise ValueError("stale_after_seconds must be >= 0")
    if not generated_at:
        return "UNKNOWN"
    generated = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    if generated.tzinfo is None or now.tzinfo is None:
        raise ValueError("freshness timestamps must be timezone-aware")
    age = max(0.0, (now - generated).total_seconds())
    return "STALE" if age > stale_after_seconds else "SNAPSHOT"


def derive_blockers(model: dict) -> list[dict]:
    blockers: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(category: str, source: str, status: str, note: str | None = None) -> None:
        key = (category, source)
        if key in seen:
            return
        seen.add(key)
        blockers.append(
            {
                "category": category,
                "source": source,
                "status": status,
                "note": note,
            }
        )

    for row in model.get("qualification", []):
        gate = str(row.get("gate", "unknown"))
        status = str(row.get("status", "UNKNOWN")).upper()
        note = row.get("note")
        if status == "FAIL":
            category = "PRODUCTION_BLOCKER" if gate == "production" else "FIRMWARE_BLOCKER"
            add(category, gate, status, note)
        elif status == "MISMATCH":
            add("IDENTITY_MISMATCH", gate, status, note)
        elif status in {"PENDING", "NOT_RUN"}:
            add("QUALIFICATION_PENDING", gate, status, note)
        elif status == "UNKNOWN":
            add("UNKNOWN_EVIDENCE", gate, status, note)
        elif status == "STALE":
            add("STALE_SOURCE", gate, status, note)

    identity = model.get("identity", {})
    if identity.get("evidence_sha_match") is False:
        add("IDENTITY_MISMATCH", "evidence_sha", "MISMATCH")
    if identity.get("relation_to_golden") == "DIVERGED":
        add("IDENTITY_MISMATCH", "golden_relation", "DIVERGED")

    freshness = model.get("freshness", {})
    if str(freshness.get("status", "")).upper() == "STALE":
        add("STALE_SOURCE", "freshness", "STALE")

    return blockers


def validate_status_model(model: dict) -> None:
    required = {
        "schema_version",
        "mode",
        "generated_at",
        "health",
        "control_plane",
        "execution_plane",
        "product_baseline",
        "identity",
        "qualification",
        "blockers",
        "freshness",
    }
    missing = sorted(required.difference(model))
    if missing:
        raise ValueError("status model missing fields: " + ", ".join(missing))

    mode = str(model["mode"]).upper()
    if mode not in {"LIVE", "SNAPSHOT"}:
        raise ValueError(f"unsupported status mode: {mode}")

    execution_sha = model.get("execution_plane", {}).get("sha")
    if execution_sha is not None and not _valid_sha(execution_sha):
        raise ValueError("execution_plane.sha must be 40 hex characters or null")

    golden_sha = model.get("product_baseline", {}).get("golden_sha")
    if golden_sha is not None and not _valid_sha(golden_sha):
        raise ValueError("product_baseline.golden_sha must be 40 hex characters or null")

    for raw in model.get("qualification", []):
        gate = str(raw.get("gate", "")).lower()
        status = str(raw.get("status", "")).upper()
        if gate not in GATES:
            raise ValueError(f"unsupported qualification gate: {gate}")
        if status not in VALID_GATE_STATES:
            raise ValueError(f"unsupported gate status: {status}")
        if status == "GOLDEN" and gate != "production":
            raise ValueError("GOLDEN is valid only for production")
        if status in _STRONG_STATES:
            if not _valid_sha(raw.get("sha")) or not raw.get("evidence"):
                raise ValueError(f"{status} requires exact sha and evidence")
            if execution_sha and raw.get("sha") != execution_sha:
                raise ValueError(
                    f"{gate} {status} evidence SHA {raw.get('sha')} != execution SHA {execution_sha}"
                )

    if mode == "LIVE" and model.get("freshness", {}).get("status") == "SNAPSHOT":
        raise ValueError("LIVE mode cannot advertise SNAPSHOT freshness")
