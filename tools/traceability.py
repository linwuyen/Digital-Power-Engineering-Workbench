from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from import_evidence import read_ledger
from truth_common import load_json, write_json


def build_traceability(requirements: dict, evidence_rows: list[dict]) -> dict:
    baseline = requirements["baseline"]
    evidence_by_requirement: dict[str, list[dict]] = defaultdict(list)
    known_requirements = {row["id"] for row in requirements["requirements"]}
    orphan_refs: list[dict] = []

    for evidence in evidence_rows:
        if evidence.get("record_type") != "evidence":
            continue
        for requirement_id in evidence.get("requirement_ids", []):
            if requirement_id not in known_requirements:
                orphan_refs.append({"evidence_id": evidence.get("evidence_id"), "requirement_id": requirement_id})
                continue
            evidence_by_requirement[requirement_id].append(evidence)

    rows = []
    for requirement in requirements["requirements"]:
        linked = evidence_by_requirement.get(requirement["id"], [])
        exact = [row for row in linked if row.get("baseline") == baseline]
        pass_rows = [row for row in exact if row.get("result") == "PASS"]
        fail_rows = [row for row in exact if row.get("result") == "FAIL"]

        if fail_rows:
            status = "FAIL"
        elif pass_rows:
            status = "QUALIFIED_BY_EVIDENCE"
        elif requirement["trust"] == "verified_source":
            status = "SOURCE_VERIFIED_ONLY"
        elif requirement["trust"] == "governance_contract":
            status = "ARCHITECTURE_CONTRACT_ONLY"
        elif requirement["trust"] == "pending_verification":
            status = "BLOCKED_PENDING_EVIDENCE"
        else:
            status = "NOT_CLAIMED"

        rows.append({
            "id": requirement["id"],
            "owner": requirement["owner"],
            "trust": requirement["trust"],
            "status": status,
            "implementation_refs": requirement.get("implementation_refs", []),
            "verification_refs": requirement.get("verification_refs", []),
            "evidence_ids": [row["evidence_id"] for row in exact],
            "stale_or_other_baseline_evidence_ids": [row["evidence_id"] for row in linked if row.get("baseline") != baseline],
        })

    counts = Counter(row["status"] for row in rows)
    return {
        "schema_version": "1.0",
        "baseline": baseline,
        "summary": dict(sorted(counts.items())),
        "requirements": rows,
        "orphan_evidence_requirement_refs": orphan_refs,
        "policy": "Only exact-baseline PASS evidence linked by requirement_id upgrades a requirement to QUALIFIED_BY_EVIDENCE.",
    }


def markdown(report: dict) -> str:
    lines = [
        "# Requirement Traceability Status",
        "",
        f"Baseline: `{report['baseline']}`",
        "",
        "| Requirement | Status | Owner | Evidence |",
        "|---|---|---|---|",
    ]
    for row in report["requirements"]:
        evidence = ", ".join(row["evidence_ids"]) or "—"
        lines.append(f"| {row['id']} | {row['status']} | {row['owner']} | {evidence} |")
    lines.extend(["", "Generated from canonical requirement/evidence data. Do not edit qualification status by hand.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve requirement qualification from the canonical evidence ledger.")
    parser.add_argument("--requirements", default="engineering_data/requirements/requirement_ledger.json")
    parser.add_argument("--ledger", default="engineering_data/evidence/evidence_ledger.jsonl")
    parser.add_argument("--out")
    parser.add_argument("--markdown")
    args = parser.parse_args()

    report = build_traceability(load_json(args.requirements), read_ledger(args.ledger))
    if args.out:
        write_json(args.out, report)
    if args.markdown:
        Path(args.markdown).write_text(markdown(report), encoding="utf-8")
    if report["orphan_evidence_requirement_refs"]:
        print(json.dumps(report["orphan_evidence_requirement_refs"], indent=2))
        return 2
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
