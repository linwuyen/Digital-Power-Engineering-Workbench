from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / ".engineering_local" / "auto_run.json"
DEFAULT_BINDING = ROOT / ".engineering_local" / "binding.json"
EXAMPLE_CONFIG = ROOT / "config" / "auto_run.local.example.json"
BUILD_CONTRACT = ROOT / "engineering_data" / "automation" / "asr5k_build_contract.json"


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_output(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or f"git {' '.join(args)} failed")
    return done.stdout.strip()


def git_identity(repo: Path) -> dict:
    return {
        "path": str(repo.resolve()),
        "sha": git_output(repo, "rev-parse", "HEAD"),
        "branch": git_output(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git_output(repo, "status", "--porcelain")),
    }


def resolve_local(value: str | Path, base: Path = ROOT) -> Path:
    raw = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def ensure_config(path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        shutil.copy2(EXAMPLE_CONFIG, path)
    return load_json(path)


def unique_existing(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = os.path.normcase(str(resolved))
        if key in seen or not resolved.exists():
            continue
        seen.add(key)
        result.append(resolved)
    return result


def production_candidates(config: dict) -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []
    if os.environ.get("ASR5K_REPO"):
        candidates.append(Path(os.environ["ASR5K_REPO"]))
    if config.get("production_repo"):
        candidates.append(resolve_local(config["production_repo"]))
    candidates.extend([
        ROOT.parent / "ASR5K_v2_28384",
        home / "Documents" / "GitHub" / "ASR5K_v2_28384",
        home / "Documents" / "GITHUB_WP" / "ASR5K_v2_28384",
        Path("D:/GITHUB/ASR5K_v2_28384"),
    ])
    return unique_existing(candidates)


def choose_production_repo(config: dict, baseline: str) -> tuple[Path | None, list[dict]]:
    probes: list[dict] = []
    exact: list[Path] = []
    for path in production_candidates(config):
        try:
            identity = git_identity(path)
            row = {"path": str(path), **identity, "exact_baseline": identity["sha"] == baseline}
            probes.append(row)
            if row["exact_baseline"]:
                exact.append(path)
        except Exception as exc:
            probes.append({"path": str(path), "error": str(exc), "exact_baseline": False})
    if len(exact) == 1:
        return exact[0], probes
    if exact:
        unique = {os.path.normcase(str(path.resolve())): path for path in exact}
        if len(unique) == 1:
            return next(iter(unique.values())), probes
    return None, probes


def executable_candidates(config: dict) -> list[Path]:
    candidates: list[Path] = []
    if os.environ.get("CCS_CLI"):
        candidates.append(Path(os.environ["CCS_CLI"]))
    if config.get("ccs_cli"):
        candidates.append(Path(str(config["ccs_cli"])))
    if os.environ.get("CCS_ROOT"):
        base = Path(os.environ["CCS_ROOT"])
        candidates.extend([
            base / "ccs" / "eclipse" / "eclipsec.exe",
            base / "ccs" / "eclipse" / "eclipsec",
            base / "ccs" / "eclipse" / "ccs-server-cli.exe",
            base / "ccs" / "eclipse" / "ccs-server-cli",
        ])
    for name in ("eclipsec.exe", "eclipsec", "ccs-server-cli.exe", "ccs-server-cli"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for pattern in (
        "C:/ti/ccs*/ccs/eclipse/eclipsec.exe",
        "C:/ti/ccs*/ccs/eclipse/eclipsec",
        "C:/ti/ccs*/ccs/eclipse/ccs-server-cli.exe",
        "C:/ti/ccs*/ccs/eclipse/ccs-server-cli",
        "C:/ti/ccs*/ccs/ccs-server-cli.exe",
        "C:/ti/ccs*/ccs/ccs-server-cli",
    ):
        candidates.extend(Path(item) for item in sorted(glob.glob(pattern), reverse=True))
    return unique_existing(candidates)


def cli_kind(path: Path) -> str | None:
    name = path.name.lower()
    if "eclipsec" in name:
        return "eclipse"
    if "ccs-server-cli" in name:
        return "server"
    return None


def choose_ccs_cli(config: dict) -> tuple[Path | None, str | None, list[dict]]:
    probes = []
    for path in executable_candidates(config):
        kind = cli_kind(path)
        if not kind:
            probes.append({"path": str(path), "status": "REJECTED", "reason": "unknown CCS CLI family"})
            continue
        probes.append({"path": str(path), "status": "CANDIDATE", "kind": kind})
        return path, kind, probes
    return None, None, probes


def parse_project(path: Path) -> dict:
    project_file = path / ".project"
    cproject_file = path / ".cproject"
    if not project_file.is_file() or not cproject_file.is_file():
        raise FileNotFoundError(f"missing CCS metadata under {path}")
    project_root = ET.parse(project_file).getroot()
    name = (project_root.findtext("name") or "").strip()
    croot = ET.parse(cproject_file).getroot()
    configs = []
    compilers = set()
    products = set()
    artifacts = []
    for node in croot.iter():
        if node.tag == "configuration" and node.get("artifactExtension") is not None:
            configs.append(node.get("name"))
            artifacts.append((node.get("artifactName"), node.get("artifactExtension")))
        if node.tag == "option" and node.get("name") == "Compiler version":
            compilers.add(node.get("value"))
        if node.tag == "listOptionValue":
            value = node.get("value", "")
            if value.startswith("PRODUCTS="):
                products.add(value[len("PRODUCTS="):])
    return {
        "project_name": name,
        "configurations": sorted(item for item in configs if item),
        "compilers": sorted(item for item in compilers if item),
        "products_raw": sorted(products),
        "artifacts": [{"name": a, "extension": b} for a, b in artifacts],
    }


def verify_projects(repo: Path, contract: dict) -> list[dict]:
    rows = []
    for project_id, spec in contract["projects"].items():
        try:
            actual = parse_project(repo / spec["project_path"])
            checks = {
                "project_name": actual["project_name"] == spec["project_name"],
                "configuration": spec["configuration"] in actual["configurations"],
                "compiler": spec["compiler"] in actual["compilers"],
                "artifact": any(row["name"] == "${ProjName}" and row["extension"] == spec["artifact_extension"] for row in actual["artifacts"]),
            }
            rows.append({"id": project_id, "status": "PASS" if all(checks.values()) else "BLOCKED", "checks": checks, "actual": actual})
        except Exception as exc:
            rows.append({"id": project_id, "status": "BLOCKED", "error": str(exc)})
    return rows


def detect_dslite(config: dict) -> tuple[str | None, list[str]]:
    candidates: list[Path] = []
    if os.environ.get("DSLITE"):
        candidates.append(Path(os.environ["DSLITE"]))
    if config.get("dslite_path"):
        candidates.append(Path(str(config["dslite_path"])))
    for name in ("dslite.bat", "dslite.exe", "dslite"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for pattern in ("C:/ti/uniflash*/dslite.bat", "C:/ti/uniflash*/dslite.exe", "C:/ti/uniflash*/ccs_base/DebugServer/bin/DSLite.exe"):
        candidates.extend(Path(item) for item in glob.glob(pattern))
    existing = unique_existing(candidates)
    return (str(existing[0]) if existing else None), [str(item) for item in existing]


def detect_ccxml(repo: Path | None, config: dict) -> dict:
    override = os.environ.get("ASR_CCXML") or config.get("target_config_ccxml")
    if override:
        path = resolve_local(override)
        return {"status": "READY" if path.is_file() else "BLOCKED", "path": str(path), "source": "override"}
    if not repo:
        return {"status": "PENDING", "path": None, "reason": "production repo unavailable"}
    matches = sorted(repo.rglob("*.ccxml"))
    if len(matches) == 1:
        return {"status": "READY", "path": str(matches[0]), "source": "unique_production_repo_candidate"}
    return {"status": "PENDING", "path": None, "candidates": [str(item) for item in matches], "reason": "no unambiguous target configuration in production checkout"}


def apply_collector_overrides(config: dict) -> None:
    env_map = {"scope": "ASR_SCOPE_EXPORT", "sfra": "ASR_SFRA_EXPORT", "logic": "ASR_LOGIC_EXPORT", "logs": "ASR_LOG_EXPORT"}
    for row in config.get("collectors", []):
        env_name = env_map.get(row.get("id"))
        if env_name and os.environ.get(env_name):
            row["path"] = os.environ[env_name]
        resolve_local(row["path"]).mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-detect and bind local ASR5K/CCS/instrument prerequisites without guessing.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--binding", default=str(DEFAULT_BINDING))
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = ensure_config(config_path)
    contract = load_json(BUILD_CONTRACT)
    baseline = contract["baseline"]["commit"]
    repo, repo_probes = choose_production_repo(config, baseline)
    ccs, kind, ccs_probes = choose_ccs_cli(config)
    project_checks = verify_projects(repo, contract) if repo else []
    dslite, dslite_candidates = detect_dslite(config)
    ccxml = detect_ccxml(repo, config)
    if repo:
        config["production_repo"] = str(repo)
    if ccs:
        config["ccs_cli"] = str(ccs)
        config["ccs_cli_kind"] = kind
    config.setdefault("ccs_workspace", ".engineering_local/ccs_workspace")
    resolve_local(config["ccs_workspace"]).mkdir(parents=True, exist_ok=True)
    gateway = os.environ.get("ASR_GATEWAY_COMMAND") or config.get("gateway_command")
    config["gateway_command"] = gateway or None
    if dslite:
        config["dslite_path"] = dslite
    if ccxml.get("status") == "READY":
        config["target_config_ccxml"] = ccxml["path"]
    apply_collector_overrides(config)
    write_json(config_path, config)
    build_ready = bool(repo and ccs and project_checks and all(row["status"] == "PASS" for row in project_checks))
    flash_ready = bool(dslite and ccxml.get("status") == "READY")
    gateway_ready = bool(gateway)
    report = {
        "schema_version": "1.0",
        "baseline": baseline,
        "production": {"status": "READY" if repo else "BLOCKED", "selected": str(repo) if repo else None, "candidates": repo_probes},
        "ccs": {"status": "READY" if ccs else "BLOCKED", "selected": str(ccs) if ccs else None, "kind": kind, "candidates": ccs_probes, "projects": project_checks},
        "build": {"status": "READY" if build_ready else "BLOCKED"},
        "flash": {"status": "READY" if flash_ready else "PENDING", "dslite": dslite, "dslite_candidates": dslite_candidates, "ccxml": ccxml},
        "hil_gateway": {"status": "READY" if gateway_ready else "PENDING", "command": gateway or None, "reason": None if gateway_ready else "set ASR_GATEWAY_COMMAND only when a real process-JSONL gateway exists"},
        "hardware_enable": {"status": "ENABLED" if config.get("allow_hardware") else "DISABLED", "note": "The binder never enables physical hardware authority automatically."},
        "config_path": str(config_path),
    }
    write_json(Path(args.binding), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    print("BUILD_BINDING=READY" if build_ready else "BUILD_BINDING=BLOCKED")
    if not flash_ready:
        print("FLASH_BINDING=PENDING")
    if not gateway_ready:
        print("HIL_GATEWAY_BINDING=PENDING")
    return 0 if build_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
