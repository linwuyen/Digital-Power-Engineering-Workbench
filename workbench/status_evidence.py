from __future__ import annotations

import json
from pathlib import Path

from .status_model import GATES, make_gate


RESULT_MAP = {
    "PASS": "PASS",
    "FAIL": "FAIL",
    "BLOCKED": "PENDING",
    "INCONCLUSIVE": "PENDING",
    "MEASURED": "PENDING",
}


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL record must be object at {path}:{line_number}")
            rows.append(value)
    return rows


def _json(path: Path) -> dict:
    if not path.exists():
        return {"records": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def _record_gate(
    row: dict,
    sha_field: str,
    execution_sha: str,
    evidence_id: str,
    evidence_type: str,
) -> dict | None:
    gate = str(row.get("gate", "")).lower()
    result = str(row.get("result", "")).upper()
    if gate not in GATES:
        return None
    if row.get(sha_field) != execution_sha:
        return None
    if result not in RESULT_MAP:
        return None
    status = RESULT_MAP[result]
    return make_gate(
        gate,
        status,
        sha=execution_sha,
        evidence=evidence_id or None,
        evidence_type=evidence_type,
        timestamp=row.get("timestamp_utc") or row.get("timestamp"),
        note=None if status in {"PASS", "FAIL"} else f"source result: {result}",
    )


def evidence_details_for_sha(data_root: Path, execution_sha: str) -> list[dict]:
    root = Path(data_root)
    details: list[dict] = []

    for row in read_jsonl(root / "evidence" / "evidence_ledger.jsonl"):
        if row.get("record_type") == "evidence" and row.get("baseline") == execution_sha:
            details.append(dict(row))

    regression = _json(root / "verification" / "regression_history" / "index.json")
    for row in regression.get("records", []):
        if isinstance(row, dict) and row.get("commit") == execution_sha:
            details.append(dict(row, record_type="regression"))

    hardware = _json(root / "verification" / "hardware_results" / "index.json")
    for row in hardware.get("records", []):
        if isinstance(row, dict) and row.get("dut_commit") == execution_sha:
            details.append(dict(row, record_type="hardware"))

    return details


def qualification_for_sha(
    data_root: Path,
    execution_sha: str,
    golden: dict,
) -> list[dict]:
    root = Path(data_root)
    by_gate = {gate: make_gate(gate, "UNKNOWN") for gate in GATES}

    for row in read_jsonl(root / "evidence" / "evidence_ledger.jsonl"):
        if row.get("record_type") != "evidence":
            continue
        normalized = _record_gate(
            row,
            "baseline",
            execution_sha,
            str(row.get("evidence_id", "")),
            "evidence_ledger",
        )
        if normalized:
            by_gate[normalized["gate"]] = normalized

    regression = _json(root / "verification" / "regression_history" / "index.json")
    for index, row in enumerate(regression.get("records", [])):
        if not isinstance(row, dict):
            continue
        normalized = _record_gate(
            row,
            "commit",
            execution_sha,
            str(row.get("evidence_id") or row.get("artifact_or_log") or f"regression:{index}"),
            "regression_history",
        )
        if normalized:
            by_gate[normalized["gate"]] = normalized

    hardware = _json(root / "verification" / "hardware_results" / "index.json")
    for index, row in enumerate(hardware.get("records", [])):
        if not isinstance(row, dict):
            continue
        normalized = _record_gate(
            row,
            "dut_commit",
            execution_sha,
            str(row.get("evidence_id") or row.get("evidence") or f"hardware:{index}"),
            "hardware_results",
        )
        if normalized:
            by_gate[normalized["gate"]] = normalized

    if golden.get("golden_sha") == execution_sha:
        source = str(golden.get("source") or "CURRENT_PRODUCT_BASELINE.md")
        release_ref = golden.get("release_ref")
        evidence = f"{source}: {release_ref}" if release_ref else source
        by_gate["production"] = make_gate(
            "production",
            "GOLDEN",
            sha=execution_sha,
            evidence=evidence,
            evidence_type="product_baseline",
            note="explicit owner-selected product baseline",
        )

    return [by_gate[gate] for gate in GATES]
