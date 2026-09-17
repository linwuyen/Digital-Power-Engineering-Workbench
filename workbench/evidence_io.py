from __future__ import annotations

import json
import re
from pathlib import Path


RESULTS = {"PASS", "FAIL", "MEASURED", "INCONCLUSIVE", "BLOCKED"}
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
REQUIRED = [
    "evidence_id",
    "baseline",
    "artifact_id",
    "test_id",
    "result",
    "timestamp_utc",
    "source_or_instrument",
]


def read_jsonl(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    ledger = Path(path)
    if not ledger.exists():
        return rows
    with ledger.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {ledger}:{line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL record must be object at {ledger}:{line_number}")
            rows.append(value)
    return rows


def read_index(path: str | Path) -> list[dict]:
    source = Path(path)
    if not source.exists():
        return []
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {source}")
    records = value.get("records", [])
    if not isinstance(records, list):
        raise ValueError(f"records must be a list: {source}")
    return [row for row in records if isinstance(row, dict)]


def _requirement_ids(row: dict) -> list[str]:
    value = row.get("requirement_ids", [])
    if not isinstance(value, list):
        raise ValueError("requirement_ids must be a list")
    return [str(item) for item in value]


def _normalized(
    row: dict,
    *,
    source: str,
    execution_sha: str | None,
    evidence: str | None,
) -> dict:
    result = str(row.get("result") or "").upper()
    return {
        "source": source,
        "execution_sha": execution_sha,
        "gate": str(row.get("gate") or "").lower() or None,
        "result": result,
        "evidence_id": row.get("evidence_id"),
        "evidence": evidence,
        "timestamp": row.get("timestamp_utc") or row.get("timestamp"),
        "golden_sha": row.get("golden_sha"),
        "requirement_ids": _requirement_ids(row),
        "run_id": row.get("run_id"),
        "details": dict(row),
    }


def load_evidence_records(data_root: str | Path) -> list[dict]:
    root = Path(data_root)
    records: list[dict] = []

    for row in read_jsonl(root / "evidence" / "evidence_ledger.jsonl"):
        if row.get("record_type") != "evidence":
            continue
        records.append(_normalized(
            row,
            source="evidence_ledger",
            execution_sha=row.get("baseline"),
            evidence=row.get("evidence") or row.get("evidence_id"),
        ))

    for row in read_index(root / "verification" / "regression_history" / "index.json"):
        records.append(_normalized(
            row,
            source="regression_history",
            execution_sha=row.get("commit"),
            evidence=row.get("evidence_id") or row.get("artifact_or_log"),
        ))

    for row in read_index(root / "verification" / "hardware_results" / "index.json"):
        records.append(_normalized(
            row,
            source="hardware_results",
            execution_sha=row.get("dut_commit"),
            evidence=row.get("evidence_id") or row.get("evidence"),
        ))

    return records


def evidence_records_for_sha(data_root: str | Path, execution_sha: str) -> list[dict]:
    return [
        record
        for record in load_evidence_records(data_root)
        if record.get("execution_sha") == execution_sha
    ]


def ledger_baseline(rows: list[dict]) -> str:
    meta = next((row for row in rows if row.get("record_type") == "ledger_meta"), None)
    if not meta:
        raise ValueError("evidence ledger is missing ledger_meta")
    return str(meta["baseline"])


def validate_evidence(record: dict, expected_baseline: str, existing: list[dict] | None = None) -> dict:
    existing = existing or []
    missing = [name for name in REQUIRED if record.get(name) in (None, "")]
    if missing:
        raise ValueError("missing required evidence fields: " + ", ".join(missing))
    if record["baseline"] != expected_baseline:
        raise ValueError(f"baseline mismatch: {record['baseline']} != {expected_baseline}")

    result = str(record["result"]).upper()
    if result not in RESULTS:
        raise ValueError(f"unsupported evidence result: {record['result']}")
    checked = dict(record)
    checked["result"] = result
    checked["record_type"] = "evidence"

    if any(row.get("evidence_id") == checked["evidence_id"] for row in existing):
        raise ValueError(f"duplicate evidence_id: {checked['evidence_id']}")

    requirement_ids = checked.get("requirement_ids", [])
    if not isinstance(requirement_ids, list):
        raise ValueError("requirement_ids must be a list")

    if result == "PASS":
        digest = str(checked.get("artifact_sha256", ""))
        if not HEX64.fullmatch(digest):
            raise ValueError("PASS evidence requires artifact_sha256 as 64 hex characters")
        if not requirement_ids:
            raise ValueError("PASS evidence requires at least one requirement_id")
        if not checked.get("run_id"):
            raise ValueError("PASS evidence requires an exact run_id")

    return checked
