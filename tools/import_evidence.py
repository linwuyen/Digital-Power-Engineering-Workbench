from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from truth_common import sha256_file


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


def read_ledger(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    ledger = Path(path)
    if not ledger.exists():
        return rows
    with ledger.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {ledger}:{line_number}: {exc}") from exc
    return rows


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
    record = dict(record)
    record["result"] = result
    record["record_type"] = "evidence"

    if any(row.get("evidence_id") == record["evidence_id"] for row in existing):
        raise ValueError(f"duplicate evidence_id: {record['evidence_id']}")

    requirement_ids = record.get("requirement_ids", [])
    if not isinstance(requirement_ids, list):
        raise ValueError("requirement_ids must be a list")

    if result == "PASS":
        digest = str(record.get("artifact_sha256", ""))
        if not HEX64.fullmatch(digest):
            raise ValueError("PASS evidence requires artifact_sha256 as 64 hex characters")
        if not requirement_ids:
            raise ValueError("PASS evidence requires at least one requirement_id")
        if not record.get("run_id"):
            raise ValueError("PASS evidence requires an exact run_id")

    return record


def append_record(ledger: str | Path, record: dict) -> None:
    path = Path(ledger)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and append exact engineering evidence to the JSONL ledger.")
    parser.add_argument("--input", required=True, help="JSON evidence record")
    parser.add_argument("--ledger", default="engineering_data/evidence/evidence_ledger.jsonl")
    parser.add_argument("--artifact-file", help="Compute artifact_sha256 from this file before validation")
    parser.add_argument("--append", action="store_true", help="Append to the canonical ledger; otherwise validation only")
    args = parser.parse_args()

    record = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.artifact_file:
        record["artifact_sha256"] = sha256_file(args.artifact_file)
        record.setdefault("artifact_id", Path(args.artifact_file).name)

    existing = read_ledger(args.ledger)
    checked = validate_evidence(record, ledger_baseline(existing), existing)
    if args.append:
        append_record(args.ledger, checked)
        print(f"appended {checked['evidence_id']} -> {args.ledger}")
    else:
        print(json.dumps(checked, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
