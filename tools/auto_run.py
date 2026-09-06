from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_common import (
    copy_immutable,
    expand_placeholders,
    generate_run_id,
    git_identity,
    load_json,
    machine_identity,
    newest_glob,
    resolve_path,
    run_command,
    sha256_file,
    utc_now,
    write_json,
)
from evidence_agent import collect_changes, normalize_collectors, snapshot_collectors, wait_for_change
from hil_runner import MockAdapter, ProcessAdapter, run_plan
from import_evidence import append_record, ledger_baseline, read_ledger, validate_evidence
from traceability import build_traceability, markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / ".engineering_local" / "auto_run.json"
PLAN_DIR = ROOT / "engineering_data" / "automation" / "plans"
REQUIREMENTS = ROOT / "engineering_data" / "requirements" / "requirement_ledger.json"
LEDGER = ROOT / "engineering_data" / "evidence" / "evidence_ledger.jsonl"
TRACEABILITY_JSON = ROOT / "engineering_data" / "verification" / "traceability_status.json"
TRACEABILITY_MD = ROOT / "docs" / "TRACEABILITY_STATUS.md"


def canonical_baseline() -> str:
    return load_json(REQUIREMENTS)["baseline"]


def load_config(path: str | Path | None = None) -> tuple[dict, Path]:
    target = Path(path).resolve() if path else DEFAULT_CONFIG
    if not target.exists():
        raise FileNotFoundError(f"local auto-run config not found: {target}; run 'asrtest init' once")
    return load_json(target), target


def init_local(path: str | Path | None = None) -> Path:
    target = Path(path).resolve() if path else DEFAULT_CONFIG
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(ROOT / "config" / "auto_run.local.example.json", target)
    config = load_json(target)
    for key in ("archive_root", "runtime_root"):
        resolve_path(config[key], ROOT).mkdir(parents=True, exist_ok=True)
    for collector in normalize_collectors(config, ROOT):
        collector["path"].mkdir(parents=True, exist_ok=True)
    print(f"auto-run config: {target}")
    print(f"archive: {resolve_path(config['archive_root'], ROOT)}")
    print("collector inboxes are ready; point instrument exports at those folders once")
    return target


def find_plan(value: str) -> tuple[dict, Path]:
    candidate = Path(value)
    if candidate.exists():
        path = candidate.resolve()
        plan = load_json(path)
        validate_plan(plan)
        return plan, path
    for path in sorted(PLAN_DIR.glob("*.json")):
        plan = load_json(path)
        if plan.get("id") == value or path.stem == value:
            validate_plan(plan)
            return plan, path
    raise FileNotFoundError(f"unknown plan: {value}")


def validate_plan(plan: dict) -> None:
    for name in ("id", "baseline", "mode", "requirements", "steps", "evidence_claims"):
        if name not in plan:
            raise ValueError(f"auto plan missing {name}")
    if plan["mode"] not in {"simulation", "hardware"}:
        raise ValueError("plan mode must be simulation or hardware")
    if not isinstance(plan["requirements"], list) or not plan["requirements"]:
        raise ValueError("plan requires at least one requirement")
    known_step_ids: set[str] = set()
    for step in plan["steps"]:
        step_id = str(step.get("id", "")).strip()
        if not step_id or step_id in known_step_ids:
            raise ValueError(f"invalid/duplicate step id: {step_id!r}")
        known_step_ids.add(step_id)
        op = step.get("op")
        if op not in {"command", "hil", "wait_for_file", "note"}:
            raise ValueError(f"unsupported auto-run op: {op}")
        if op == "command" and not step.get("command"):
            raise ValueError(f"command step {step_id} has no command")
        if op == "hil" and not step.get("plan"):
            raise ValueError(f"hil step {step_id} has no HIL plan")
        if op == "wait_for_file" and not step.get("collector_id"):
            raise ValueError(f"wait_for_file step {step_id} has no collector_id")
    artifact_ids = {str(row["id"]) for row in plan.get("artifacts", [])}
    plan_requirements = set(plan["requirements"])
    for claim in plan["evidence_claims"]:
        if not claim.get("id") or not claim.get("test_id"):
            raise ValueError("evidence claim requires id and test_id")
        refs = set(claim.get("depends_on_steps", []))
        unknown = refs - known_step_ids
        if unknown:
            raise ValueError(f"claim {claim['id']} references unknown steps: {sorted(unknown)}")
        requirement_ids = set(claim.get("requirement_ids", []))
        if not requirement_ids or not requirement_ids <= plan_requirements:
            raise ValueError(f"claim {claim['id']} requirements must be a non-empty subset of plan requirements")
        if claim.get("artifact") and claim["artifact"] not in artifact_ids:
            raise ValueError(f"claim {claim['id']} references unknown artifact {claim['artifact']}")


def placeholders(run_dir: Path, production_repo: Path | None) -> dict[str, str]:
    return {
        "workbench_repo": str(ROOT),
        "production_repo": str(production_repo) if production_repo else "",
        "run_dir": str(run_dir),
        "python": sys.executable,
    }


def preflight(plan: dict, config: dict) -> dict:
    checks: list[dict] = []
    baseline = canonical_baseline()
    if plan["baseline"] != baseline:
        checks.append({"id": "plan_baseline", "status": "BLOCKED", "detail": f"{plan['baseline']} != {baseline}"})
    else:
        checks.append({"id": "plan_baseline", "status": "PASS", "detail": baseline})

    production_repo = resolve_path(config.get("production_repo", "../ASR5K_v2_28384"), ROOT)
    production_identity = None
    required = bool(plan.get("preflight", {}).get("production_repo_required", plan["mode"] == "hardware"))
    if required:
        try:
            production_identity = git_identity(production_repo)
            if production_identity["sha"] != baseline:
                checks.append({"id": "production_sha", "status": "BLOCKED", "detail": production_identity["sha"]})
            else:
                checks.append({"id": "production_sha", "status": "PASS", "detail": baseline})
            require_clean = bool(plan.get("preflight", {}).get("require_clean_production_repo", True))
            if require_clean and production_identity["dirty"]:
                checks.append({"id": "production_clean", "status": "BLOCKED", "detail": "working tree is dirty"})
            else:
                checks.append({"id": "production_clean", "status": "PASS", "detail": str(not production_identity["dirty"])})
        except Exception as exc:
            checks.append({"id": "production_repo", "status": "BLOCKED", "detail": str(exc)})
    else:
        checks.append({"id": "production_repo", "status": "SKIPPED", "detail": "plan does not require production checkout"})

    publish = config.get("publish", {})
    if publish.get("mode", "commit") == "commit":
        try:
            wb = git_identity(ROOT)
            if wb["dirty"]:
                checks.append({"id": "workbench_clean", "status": "BLOCKED", "detail": "refusing to auto-commit with unrelated working-tree changes"})
            else:
                checks.append({"id": "workbench_clean", "status": "PASS", "detail": wb["sha"]})
        except Exception as exc:
            checks.append({"id": "workbench_repo", "status": "BLOCKED", "detail": str(exc)})

    if plan["mode"] == "hardware" and not bool(config.get("allow_hardware", False)):
        checks.append({"id": "hardware_enable", "status": "BLOCKED", "detail": "set allow_hardware=true once in local config"})

    return {
        "baseline": baseline,
        "production_repo": str(production_repo),
        "production_identity": production_identity,
        "checks": checks,
        "status": "PASS" if not any(row["status"] == "BLOCKED" for row in checks) else "BLOCKED",
    }


def write_step_log(run_dir: Path, step_id: str, report: dict) -> None:
    logs = run_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    text = []
    if "command" in report:
        text.append("COMMAND: " + json.dumps(report["command"]))
    if report.get("stdout"):
        text.extend(["", "STDOUT:", str(report["stdout"])])
    if report.get("stderr"):
        text.extend(["", "STDERR:", str(report["stderr"])])
    if report.get("error"):
        text.extend(["", "ERROR:", str(report["error"])])
    (logs / f"{step_id}.log").write_text("\n".join(text) + "\n", encoding="utf-8")


def execute_step(
    step: dict,
    plan: dict,
    config: dict,
    run_dir: Path,
    production_repo: Path | None,
    collector_before: dict,
) -> dict:
    step_id = step["id"]
    op = step["op"]
    row: dict[str, Any] = {"id": step_id, "op": op, "started_utc": utc_now(), "status": "PASS", "physical": False}
    values = placeholders(run_dir, production_repo)
    try:
        if op == "command":
            if step.get("hardware", False) and not config.get("allow_hardware", False):
                raise RuntimeError("hardware command blocked by local config")
            command = expand_placeholders(step["command"], values)
            cwd = resolve_path(expand_placeholders(step.get("cwd", "{workbench_repo}"), values), ROOT)
            result = run_command(command, cwd=cwd, timeout_seconds=int(step.get("timeout_seconds", 300)))
            row.update(result)
            accepted = [int(item) for item in step.get("accepted_exit_codes", [0])]
            if result["timed_out"] or result["exit_code"] not in accepted:
                row["status"] = "FAIL"
            row["physical"] = bool(step.get("hardware", False))
            write_step_log(run_dir, step_id, row)
        elif op == "hil":
            hil_plan_path = resolve_path(expand_placeholders(step["plan"], values), ROOT)
            hil_plan = load_json(hil_plan_path)
            mode = step.get("mode", "mock")
            if mode == "process":
                if plan["mode"] != "hardware" or not config.get("allow_hardware", False):
                    raise RuntimeError("process HIL requires hardware plan and allow_hardware=true")
                gateway = step.get("gateway_command") or config.get("gateway_command")
                if not gateway:
                    raise RuntimeError("process HIL requires gateway_command in plan or local config")
                adapter = ProcessAdapter(expand_placeholders(gateway, values))
                row["physical"] = True
            else:
                adapter = MockAdapter()
            report = run_plan(hil_plan, adapter, mode)
            write_json(run_dir / "results" / f"{step_id}.json", report)
            row["hil_result"] = report["result"]
            row["hil_run_id"] = report["run_id"]
            if report["result"] not in {"SIMULATION_PASS", "HARDWARE_RUN_PASS_UNQUALIFIED"}:
                row["status"] = "FAIL"
        elif op == "wait_for_file":
            names = wait_for_change(
                config,
                ROOT,
                collector_before,
                str(step["collector_id"]),
                str(step.get("pattern", "*")),
                int(step.get("timeout_seconds", 60)),
                float(step.get("poll_seconds", 0.5)),
            )
            row["files"] = names
            if not names:
                row["status"] = "FAIL"
                row["error"] = "no matching new/modified file before timeout"
        elif op == "note":
            row["text"] = str(step.get("text", ""))
    except Exception as exc:
        row["status"] = "FAIL"
        row["error"] = str(exc)
        write_step_log(run_dir, step_id, row)
    row["completed_utc"] = utc_now()
    return row


def collect_artifacts(plan: dict, run_dir: Path, production_repo: Path | None) -> tuple[list[dict], list[str]]:
    values = placeholders(run_dir, production_repo)
    rows: list[dict] = []
    missing: list[str] = []
    for spec in plan.get("artifacts", []):
        root = resolve_path(expand_placeholders(spec.get("root", "{production_repo}"), values), ROOT)
        pattern = expand_placeholders(spec["glob"], values)
        source = newest_glob(root, pattern)
        if source is None:
            if spec.get("required", True):
                missing.append(spec["id"])
            continue
        destination = run_dir / "artifacts" / spec["id"] / source.name
        info = copy_immutable(source, destination)
        info.update({
            "id": spec["id"],
            "role": spec.get("role", "artifact"),
            "source_path": str(source),
            "archive_relative_path": destination.relative_to(run_dir).as_posix(),
        })
        rows.append(info)
    return rows, missing


def hash_run_files(run_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        rows.append({
            "path": path.relative_to(run_dir).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return rows


def evaluate_claim(
    claim: dict,
    plan: dict,
    steps: list[dict],
    artifacts: list[dict],
    collected: list[dict],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    step_map = {row["id"]: row for row in steps}
    dependencies = [step_map[name] for name in claim.get("depends_on_steps", [])]
    if any(row["status"] == "FAIL" for row in dependencies):
        return "FAIL", ["one or more depended-on test steps failed"]

    artifact_ids = {row["id"] for row in artifacts}
    if claim.get("artifact") and claim["artifact"] not in artifact_ids:
        reasons.append(f"required artifact missing: {claim['artifact']}")

    if plan["mode"] == "simulation":
        reasons.append("simulation run cannot qualify production")

    if claim.get("physical_evidence_required", False):
        required_collectors = set(claim.get("required_collector_ids", []))
        if required_collectors:
            seen = {row.get("collector_id") for row in collected}
            missing = sorted(required_collectors - seen)
            if missing:
                reasons.append("missing physical collector output: " + ", ".join(missing))
        elif not any(row.get("physical") and row.get("status") == "PASS" for row in dependencies):
            reasons.append("no successful physical depended-on step")

    return ("PASS", []) if not reasons else ("BLOCKED", reasons)


def build_evidence_records(
    plan: dict,
    run_id: str,
    steps: list[dict],
    artifacts: list[dict],
    collected: list[dict],
    manifest_hash: str,
    completed_utc: str,
) -> list[dict]:
    artifact_map = {row["id"]: row for row in artifacts}
    attachments = [row["archive_relative_path"] for row in artifacts + collected]
    records = []
    for claim in plan["evidence_claims"]:
        result, reasons = evaluate_claim(claim, plan, steps, artifacts, collected)
        artifact = artifact_map.get(claim.get("artifact"))
        record = {
            "evidence_id": f"EVD-{run_id}-{claim['id']}",
            "baseline": plan["baseline"],
            "run_id": run_id,
            "artifact_id": artifact["name"] if artifact else "manifest.json",
            "test_id": claim["test_id"],
            "requirement_ids": claim["requirement_ids"],
            "result": result,
            "timestamp_utc": completed_utc,
            "source_or_instrument": claim.get("source_or_instrument", f"auto_run:{plan['id']}"),
            "artifact_sha256": artifact["sha256"] if artifact else manifest_hash,
            "attachments": attachments,
            "qualification_claimed": result == "PASS",
            "notes": "; ".join(reasons) if reasons else "auto-qualified only after exact preflight, depended-on steps and artifact/evidence gates passed",
        }
        records.append(record)
    return records


def refresh_traceability() -> dict:
    requirements = load_json(REQUIREMENTS)
    rows = read_ledger(LEDGER)
    report = build_traceability(requirements, rows)
    write_json(TRACEABILITY_JSON, report)
    TRACEABILITY_MD.write_text(markdown(report), encoding="utf-8")
    return report


def publish_metadata(config: dict, run_id: str, plan_id: str) -> dict:
    publish = config.get("publish", {})
    mode = publish.get("mode", "commit")
    if mode == "none":
        return {"mode": "none", "status": "SKIPPED"}
    if mode != "commit":
        raise ValueError(f"unsupported publish mode: {mode}")

    paths = [
        str(LEDGER.relative_to(ROOT)),
        str(TRACEABILITY_JSON.relative_to(ROOT)),
        str(TRACEABILITY_MD.relative_to(ROOT)),
    ]
    subprocess.run(["git", "-C", str(ROOT), "add", "--", *paths], check=True)
    staged = subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        return {"mode": "commit", "status": "NO_CHANGES"}
    message = str(publish.get("message_template", "evidence: {run_id} {plan_id}"))
    message = message.replace("{run_id}", run_id).replace("{plan_id}", plan_id)
    completed = subprocess.run(["git", "-C", str(ROOT), "commit", "-m", message], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    identity = git_identity(ROOT)
    result = {"mode": "commit", "status": "COMMITTED", "sha": identity["sha"], "branch": identity["branch"]}
    if publish.get("push", False):
        if identity["branch"] == "main" and not publish.get("allow_push_main", False):
            result["push"] = "SKIPPED_MAIN_PROTECTED_BY_LOCAL_POLICY"
        else:
            push = subprocess.run(["git", "-C", str(ROOT), "push", "origin", "HEAD"], capture_output=True, text=True, check=False)
            if push.returncode != 0:
                raise RuntimeError(push.stderr.strip() or push.stdout.strip())
            result["push"] = "PUSHED"
    return result


def run_auto(plan: dict, config: dict) -> dict:
    run_id = generate_run_id()
    started = datetime.now(timezone.utc)
    archive_root = resolve_path(config["archive_root"], ROOT)
    run_dir = archive_root / started.strftime("%Y") / started.strftime("%m") / started.strftime("%d") / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    runtime_root = resolve_path(config["runtime_root"], ROOT)
    runtime_root.mkdir(parents=True, exist_ok=True)

    pf = preflight(plan, config)
    context = {
        "schema_version": "1.0",
        "run_id": run_id,
        "plan_id": plan["id"],
        "mode": plan["mode"],
        "baseline": plan["baseline"],
        "started_utc": started.isoformat().replace("+00:00", "Z"),
        "machine": machine_identity(),
        "preflight": pf,
        "archive_path": str(run_dir),
    }
    write_json(run_dir / "run_context.json", context)
    write_json(runtime_root / "active_run.json", context)

    if pf["status"] != "PASS":
        summary = {**context, "result": "BLOCKED_PREFLIGHT", "completed_utc": utc_now()}
        write_json(run_dir / "summary.json", summary)
        (runtime_root / "active_run.json").unlink(missing_ok=True)
        write_json(runtime_root / "latest_run.json", summary)
        return summary

    production_repo = Path(pf["production_repo"]) if pf.get("production_repo") else None
    collector_before = snapshot_collectors(config, ROOT)
    steps: list[dict] = []
    for step in plan["steps"]:
        row = execute_step(step, plan, config, run_dir, production_repo, collector_before)
        steps.append(row)
        if row["status"] == "FAIL" and step.get("continue_on_fail", False) is not True:
            break

    time.sleep(float(config.get("collect_settle_seconds", 1.0)))
    collected = collect_changes(config, ROOT, collector_before, run_dir)
    artifacts, missing_artifacts = collect_artifacts(plan, run_dir, production_repo)

    preliminary = {
        **context,
        "completed_utc": utc_now(),
        "steps": steps,
        "collected": collected,
        "artifacts": artifacts,
        "missing_required_artifacts": missing_artifacts,
    }
    write_json(run_dir / "run_result.json", preliminary)
    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "baseline": plan["baseline"],
        "files": hash_run_files(run_dir),
    }
    write_json(run_dir / "manifest.json", manifest)
    manifest_hash = sha256_file(run_dir / "manifest.json")

    records = build_evidence_records(
        plan,
        run_id,
        steps,
        artifacts,
        collected,
        manifest_hash,
        preliminary["completed_utc"],
    )
    existing = read_ledger(LEDGER)
    expected = ledger_baseline(existing)
    checked_records = []
    for record in records:
        checked = validate_evidence(record, expected, existing + checked_records)
        append_record(LEDGER, checked)
        checked_records.append(checked)

    traceability = refresh_traceability()
    all_claims_pass = all(row["result"] == "PASS" for row in checked_records)
    any_test_fail = any(row["result"] == "FAIL" for row in checked_records)
    if any_test_fail:
        overall = "FAIL"
    elif all_claims_pass:
        overall = "QUALIFIED_BY_EVIDENCE"
    else:
        overall = "COMPLETED_UNQUALIFIED"

    final = {
        **preliminary,
        "result": overall,
        "manifest_sha256": manifest_hash,
        "evidence_ids": [row["evidence_id"] for row in checked_records],
        "qualification_claimed": overall == "QUALIFIED_BY_EVIDENCE",
        "traceability_summary": traceability["summary"],
    }
    write_json(run_dir / "summary.json", final)
    (runtime_root / "active_run.json").unlink(missing_ok=True)
    write_json(runtime_root / "latest_run.json", final)
    final["publish"] = publish_metadata(config, run_id, plan["id"])
    write_json(run_dir / "summary.json", final)
    write_json(runtime_root / "latest_run.json", final)
    return final


def doctor(config: dict, plan: dict | None = None) -> int:
    problems = []
    print(f"Workbench: {ROOT}")
    print(f"Baseline: {canonical_baseline()}")
    try:
        wb = git_identity(ROOT)
        print(f"Workbench git: {wb['branch']} @ {wb['sha'][:12]} dirty={wb['dirty']}")
    except Exception as exc:
        problems.append(f"Workbench git: {exc}")
    prod = resolve_path(config.get("production_repo", "../ASR5K_v2_28384"), ROOT)
    try:
        identity = git_identity(prod)
        print(f"Production git: {identity['branch']} @ {identity['sha'][:12]} dirty={identity['dirty']}")
        if identity["sha"] != canonical_baseline():
            problems.append("production repo is not at canonical baseline")
    except Exception as exc:
        print(f"Production git: unavailable ({exc})")
        if plan and plan.get("preflight", {}).get("production_repo_required", plan["mode"] == "hardware"):
            problems.append("selected plan requires production repo")
    archive = resolve_path(config["archive_root"], ROOT)
    archive.mkdir(parents=True, exist_ok=True)
    print(f"Archive: {archive}")
    for row in normalize_collectors(config, ROOT):
        row["path"].mkdir(parents=True, exist_ok=True)
        print(f"Collector {row['id']}: {row['path']}")
    if plan:
        pf = preflight(plan, config)
        for row in pf["checks"]:
            print(f"[{row['status']}] {row['id']}: {row['detail']}")
        if pf["status"] != "PASS":
            problems.append("plan preflight is blocked")
    for problem in problems:
        print(f"BLOCKED: {problem}")
    return 2 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="asrtest", description="One-command ASR5K engineering run/evidence/qualification pipeline.")
    parser.add_argument("--config", help="local config path; default .engineering_local/auto_run.json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="one-time local setup")
    sub.add_parser("list", help="list available run plans")
    doctor_p = sub.add_parser("doctor", help="check local environment and optional plan preflight")
    doctor_p.add_argument("plan", nargs="?")
    run_p = sub.add_parser("run", help="run one plan end-to-end")
    run_p.add_argument("plan")
    args = parser.parse_args()

    if args.command == "init":
        init_local(args.config)
        return 0
    if args.command == "list":
        for path in sorted(PLAN_DIR.glob("*.json")):
            plan = load_json(path)
            print(f"{plan['id']}\t{plan['mode']}\t{path.name}")
        return 0

    try:
        config, _ = load_config(args.config)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.command == "doctor":
        plan = find_plan(args.plan)[0] if args.plan else None
        return doctor(config, plan)
    if args.command == "run":
        plan, _ = find_plan(args.plan)
        result = run_auto(plan, config)
        print(json.dumps({
            "run_id": result["run_id"],
            "result": result["result"],
            "archive_path": result["archive_path"],
            "qualification_claimed": result.get("qualification_claimed", False),
            "evidence_ids": result.get("evidence_ids", []),
            "publish": result.get("publish"),
        }, indent=2, sort_keys=True))
        return 0 if result["result"] in {"QUALIFIED_BY_EVIDENCE", "COMPLETED_UNQUALIFIED"} else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
