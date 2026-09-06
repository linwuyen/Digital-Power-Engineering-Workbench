from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD_CONTRACT = ROOT / "engineering_data" / "automation" / "asr5k_build_contract.json"
DEFAULT_CONFIG = ROOT / ".engineering_local" / "auto_run.json"


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or f"git {' '.join(args)} failed")
    return done.stdout.strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def cli_commands(kind: str, executable: Path, workspace: Path, project_dir: Path, project_name: str, configuration: str) -> tuple[list[str], list[str]]:
    exe = str(executable)
    ws = str(workspace)
    location = str(project_dir)
    if kind == "eclipse":
        return ([exe, "-noSplash", "-data", ws, "-application", "com.ti.ccstudio.apps.projectImport", "-ccs.location", location], [exe, "-noSplash", "-data", ws, "-application", "com.ti.ccstudio.apps.projectBuild", "-ccs.projects", project_name, "-ccs.configuration", configuration, "-ccs.buildType", "full", "-ccs.listProblems"])
    if kind == "server":
        return ([exe, "-noSplash", "-workspace", ws, "-application", "com.ti.ccs.apps.importProject", "-ccs.location", location], [exe, "-noSplash", "-workspace", ws, "-application", "com.ti.ccs.apps.buildProject", "-ccs.projects", project_name, "-ccs.configuration", configuration, "-ccs.buildType", "full", "-ccs.listProblems"])
    raise ValueError(f"unsupported CCS CLI kind: {kind}")


def run(command: list[str], timeout: int) -> dict:
    started = utc_now()
    try:
        done = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        return {"command": command, "started_utc": started, "completed_utc": utc_now(), "exit_code": done.returncode, "stdout": done.stdout, "stderr": done.stderr, "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "started_utc": started, "completed_utc": utc_now(), "exit_code": None, "stdout": exc.stdout or "", "stderr": exc.stderr or "", "timed_out": True}


def probe_cli(kind: str, executable: Path, workspace: Path, timeout: int) -> dict:
    if kind == "eclipse":
        command = [str(executable), "-noSplash", "-data", str(workspace), "-application", "com.ti.ccstudio.apps.projectBuild", "-ccs.help"]
    elif kind == "server":
        command = [str(executable), "-noSplash", "-workspace", str(workspace), "-application", "com.ti.ccs.apps.buildProject", "-ccs.help"]
    else:
        raise ValueError(kind)
    result = run(command, timeout)
    combined = (result.get("stdout") or "") + "\n" + (result.get("stderr") or "")
    result["recognized"] = result["exit_code"] == 0 and "ccs" in combined.lower()
    return result


def locate_artifact(project_dir: Path, configuration: str, artifact_name: str, build_started_ns: int) -> tuple[Path | None, list[str]]:
    freshness_floor = build_started_ns - 2_000_000_000
    exact = project_dir / configuration / artifact_name
    if exact.is_file() and exact.stat().st_mtime_ns >= freshness_floor:
        return exact, [str(exact)]
    candidates = [item for item in project_dir.rglob(artifact_name) if item.is_file()]
    fresh = [item for item in candidates if item.stat().st_mtime_ns >= freshness_floor]
    chosen = fresh[0] if len(fresh) == 1 else None
    return chosen, [str(item) for item in candidates]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one exact ASR5K CCS project and emit an artifact-bound report.")
    parser.add_argument("--project", required=True, choices=["cpu1", "cpu2", "m0"])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    contract = load_json(BUILD_CONTRACT)
    config = load_json(args.config)
    baseline = contract["baseline"]["commit"]
    repo = Path(os.path.expandvars(os.path.expanduser(config["production_repo"]))).resolve()
    actual_sha = git_output(repo, "rev-parse", "HEAD")
    dirty = bool(git_output(repo, "status", "--porcelain"))
    if actual_sha != baseline:
        raise SystemExit(f"BLOCKED: production SHA {actual_sha} != {baseline}")
    if dirty:
        raise SystemExit("BLOCKED: production working tree is dirty")
    cli_value = config.get("ccs_cli")
    kind = config.get("ccs_cli_kind")
    if not cli_value or not kind:
        raise SystemExit("BLOCKED: CCS CLI not bound; run '.\\asrtest.ps1 bind'")
    cli = Path(cli_value)
    if not cli.is_file():
        found = shutil.which(cli_value)
        if found:
            cli = Path(found)
        else:
            raise SystemExit(f"BLOCKED: CCS CLI does not exist: {cli_value}")
    spec = contract["projects"][args.project]
    project_dir = repo / spec["project_path"]
    if not (project_dir / ".project").is_file() or not (project_dir / ".cproject").is_file():
        raise SystemExit(f"BLOCKED: CCS project metadata missing: {project_dir}")
    workspace = Path(args.workspace).resolve()
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    probe_workspace = workspace.parent / (workspace.name + "-probe")
    if probe_workspace.exists():
        shutil.rmtree(probe_workspace)
    probe_workspace.mkdir(parents=True, exist_ok=True)
    probe = probe_cli(kind, cli, probe_workspace, min(args.timeout_seconds, 120))
    shutil.rmtree(probe_workspace, ignore_errors=True)
    if not probe["recognized"]:
        write_json(args.out, {"schema_version": "1.0", "status": "BLOCKED_CCS_CLI_PROBE", "baseline": baseline, "project": args.project, "probe": probe})
        return 2
    import_cmd, build_cmd = cli_commands(kind, cli, workspace, project_dir, spec["project_name"], spec["configuration"])
    imported = run(import_cmd, args.timeout_seconds)
    if imported["exit_code"] != 0 or imported["timed_out"]:
        write_json(args.out, {"schema_version": "1.0", "status": "FAIL_IMPORT", "baseline": baseline, "project": args.project, "project_spec": spec, "cli": str(cli), "cli_kind": kind, "probe": probe, "import": imported})
        return 2
    build_started_ns = __import__("time").time_ns()
    built = run(build_cmd, args.timeout_seconds)
    artifact, candidates = locate_artifact(project_dir, spec["configuration"], spec["artifact_name"], build_started_ns)
    status = "PASS" if built["exit_code"] == 0 and not built["timed_out"] and artifact else "FAIL_BUILD_OR_ARTIFACT"
    report = {"schema_version": "1.0", "status": status, "qualification_claimed": False, "baseline": baseline, "production_sha": actual_sha, "project": args.project, "project_spec": spec, "cli": str(cli), "cli_kind": kind, "workspace": str(workspace), "probe": probe, "import": imported, "build": built, "artifact_candidates": candidates, "artifact": None if artifact is None else {"path": str(artifact), "name": artifact.name, "size": artifact.stat().st_size, "sha256": sha256_file(artifact)}, "completed_utc": utc_now(), "next_action": "The auto-run evidence layer must bind this exact .out hash before any build qualification claim."}
    write_json(args.out, report)
    if artifact:
        print(f"ARTIFACT={artifact}")
        print(f"SHA256={report['artifact']['sha256']}")
    print(f"BUILD_STATUS={status}")
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
