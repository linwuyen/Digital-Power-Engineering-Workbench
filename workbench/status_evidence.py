from __future__ import annotations

from pathlib import Path

from .evidence_io import evidence_records_for_sha, load_evidence_records
from .status_model import GATES, make_gate


RESULT_MAP = {
    "PASS": "PASS",
    "FAIL": "FAIL",
    "BLOCKED": "PENDING",
    "INCONCLUSIVE": "PENDING",
    "MEASURED": "PENDING",
}
STRONG_STATES = {"PASS", "FAIL", "GOLDEN"}


def _record_gate(row: dict, execution_sha: str) -> dict | None:
    gate = str(row.get("gate") or "").lower()
    result = str(row.get("result") or "").upper()
    if gate not in GATES:
        return None
    if row.get("execution_sha") != execution_sha:
        return None
    if result not in RESULT_MAP:
        return None
    status = RESULT_MAP[result]
    evidence = str(row.get("evidence") or "").strip() or None
    if status in {"PASS", "FAIL"} and not evidence:
        return None
    return make_gate(
        gate,
        status,
        sha=execution_sha,
        evidence=evidence,
        evidence_type=str(row.get("source") or "normalized_evidence"),
        timestamp=row.get("timestamp"),
        note=None if status in {"PASS", "FAIL"} else f"source result: {result}",
    )


def _candidate_key(row: dict) -> tuple[str, str, str, str]:
    return (
        str(row.get("status") or ""),
        str(row.get("evidence_type") or ""),
        str(row.get("evidence") or ""),
        str(row.get("timestamp") or ""),
    )


def _resolve_gate(gate: str, candidates: list[dict]) -> dict:
    if not candidates:
        return make_gate(gate, "UNKNOWN")
    ordered = sorted(candidates, key=_candidate_key)
    strong = [row for row in ordered if row.get("status") in STRONG_STATES]
    strong_states = {row["status"] for row in strong}
    if "FAIL" in strong_states and ("PASS" in strong_states or "GOLDEN" in strong_states):
        return make_gate(
            gate,
            "UNKNOWN",
            note="conflicting evidence: " + ", ".join(sorted(strong_states)),
        )
    if "GOLDEN" in strong_states:
        return next(row for row in strong if row["status"] == "GOLDEN")
    if "FAIL" in strong_states:
        return next(row for row in strong if row["status"] == "FAIL")
    if "PASS" in strong_states:
        return next(row for row in strong if row["status"] == "PASS")
    pending = [row for row in ordered if row.get("status") == "PENDING"]
    if pending:
        return pending[0]
    stale = [row for row in ordered if row.get("status") == "STALE"]
    if stale:
        return stale[0]
    mismatch = [row for row in ordered if row.get("status") == "MISMATCH"]
    if mismatch:
        return mismatch[0]
    unknown = [row for row in ordered if row.get("status") == "UNKNOWN"]
    if unknown:
        return unknown[0]
    return make_gate(gate, "UNKNOWN")


def evidence_details_for_sha(data_root: Path, execution_sha: str) -> list[dict]:
    return evidence_records_for_sha(data_root, execution_sha)


def qualification_for_sha(
    data_root: Path,
    execution_sha: str,
    golden: dict,
) -> list[dict]:
    candidates: dict[str, list[dict]] = {gate: [] for gate in GATES}
    current_golden_sha = golden.get("golden_sha")

    for row in load_evidence_records(data_root):
        normalized = _record_gate(row, execution_sha)
        if not normalized:
            continue

        if row.get("source") == "regression_history" and normalized["status"] == "PASS":
            evidence_golden_sha = row.get("golden_sha")
            if not current_golden_sha:
                normalized = make_gate(
                    normalized["gate"],
                    "UNKNOWN",
                    sha=normalized["sha"],
                    evidence=normalized["evidence"],
                    evidence_type=normalized["evidence_type"],
                    timestamp=normalized["timestamp"],
                    note=(
                        f"regression evidence GOLDEN {evidence_golden_sha or 'UNKNOWN'} cannot be qualified: "
                        "current GOLDEN is unavailable"
                    ),
                )
            elif evidence_golden_sha != current_golden_sha:
                normalized = make_gate(
                    normalized["gate"],
                    "STALE",
                    sha=normalized["sha"],
                    evidence=normalized["evidence"],
                    evidence_type=normalized["evidence_type"],
                    timestamp=normalized["timestamp"],
                    note=(
                        f"regression evidence GOLDEN {evidence_golden_sha or 'UNKNOWN'} "
                        f"!= current GOLDEN {current_golden_sha}"
                    ),
                )
        candidates[normalized["gate"]].append(normalized)

    if golden.get("golden_sha") == execution_sha:
        source = str(golden.get("source") or "CURRENT_PRODUCT_BASELINE.md")
        release_ref = golden.get("release_ref")
        evidence = f"{source}: {release_ref}" if release_ref else source
        candidates["production"].append(
            make_gate(
                "production",
                "GOLDEN",
                sha=execution_sha,
                evidence=evidence,
                evidence_type="product_baseline",
                note="explicit owner-selected product baseline",
            )
        )

    return [_resolve_gate(gate, candidates[gate]) for gate in GATES]
