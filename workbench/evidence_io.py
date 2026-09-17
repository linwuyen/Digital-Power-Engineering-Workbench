from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class EvidenceRecord:
    source_type: str
    execution_sha: str | None
    result: str
    gate: str | None
    evidence_ref: str | None
    evidence_id: str | None
    timestamp: str | None
    golden_sha: str | None
    requirement_ids: tuple[str, ...]
    raw: dict


def _optional_text(value) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _gate(value) -> str | None:
    text = _optional_text(value)
    return text.lower() if text else None


def _result(value) -> str:
    return str(value or "").upper()


def _requirement_ids(row: dict) -> tuple[str, ...]:
    value = row.get("requirement_ids", [])
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def read_ledger(path: str | Path) -> tuple[dict | None, list[dict]]:
    ledger = Path(path)
    if not ledger.exists():
        return None, []

    meta: dict | None = None
    rows: list[dict] = []
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
            if value.get("record_type") == "ledger_meta" and meta is None:
                meta = dict(value)
            else:
                rows.append(dict(value))
    return meta, rows


def _read_index(path: Path) -> list[dict]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    rows = value.get("records", [])
    if not isinstance(rows, list):
        raise ValueError(f"records must be a list: {path}")
    return [dict(row) for row in rows if isinstance(row, dict)]


def _ledger_record(row: dict) -> EvidenceRecord:
    return EvidenceRecord(
        source_type="evidence_ledger",
        execution_sha=_optional_text(row.get("baseline")),
        result=_result(row.get("result")),
        gate=_gate(row.get("gate")),
        evidence_ref=_optional_text(row.get("evidence_id")),
        evidence_id=_optional_text(row.get("evidence_id")),
        timestamp=_optional_text(row.get("timestamp_utc") or row.get("timestamp")),
        golden_sha=None,
        requirement_ids=_requirement_ids(row),
        raw=dict(row),
    )


def _regression_record(row: dict) -> EvidenceRecord:
    return EvidenceRecord(
        source_type="regression_history",
        execution_sha=_optional_text(row.get("commit")),
        result=_result(row.get("result")),
        gate=_gate(row.get("gate")),
        evidence_ref=_optional_text(row.get("evidence_id") or row.get("artifact_or_log")),
        evidence_id=_optional_text(row.get("evidence_id")),
        timestamp=_optional_text(row.get("timestamp_utc") or row.get("timestamp")),
        golden_sha=_optional_text(row.get("golden_sha")),
        requirement_ids=_requirement_ids(row),
        raw=dict(row),
    )


def _hardware_record(row: dict) -> EvidenceRecord:
    return EvidenceRecord(
        source_type="hardware_results",
        execution_sha=_optional_text(row.get("dut_commit")),
        result=_result(row.get("result")),
        gate=_gate(row.get("gate")),
        evidence_ref=_optional_text(row.get("evidence_id") or row.get("evidence")),
        evidence_id=_optional_text(row.get("evidence_id")),
        timestamp=_optional_text(row.get("timestamp_utc") or row.get("timestamp")),
        golden_sha=None,
        requirement_ids=_requirement_ids(row),
        raw=dict(row),
    )


def load_evidence_records(data_root: str | Path) -> list[EvidenceRecord]:
    root = Path(data_root)
    records: list[EvidenceRecord] = []

    _, ledger_rows = read_ledger(root / "evidence" / "evidence_ledger.jsonl")
    records.extend(
        _ledger_record(row)
        for row in ledger_rows
        if row.get("record_type") == "evidence"
    )

    records.extend(
        _regression_record(row)
        for row in _read_index(root / "verification" / "regression_history" / "index.json")
    )
    records.extend(
        _hardware_record(row)
        for row in _read_index(root / "verification" / "hardware_results" / "index.json")
    )
    return records


def detail_row(record: EvidenceRecord) -> dict:
    row = dict(record.raw)
    if record.source_type == "regression_history":
        row["record_type"] = "regression"
    elif record.source_type == "hardware_results":
        row["record_type"] = "hardware"
    return row
