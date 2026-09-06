from __future__ import annotations

import fnmatch
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from truth_common import sha256_file


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    return f"RUN-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_path(value: str | Path, base: str | Path) -> Path:
    raw = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(raw)
    if not path.is_absolute():
        path = Path(base) / path
    return path.resolve()


def command_argv(command: str | list[str]) -> list[str]:
    if isinstance(command, list):
        return [str(item) for item in command]
    return shlex.split(command, posix=os.name != "nt")


def expand_placeholders(value: Any, values: dict[str, str]) -> Any:
    if isinstance(value, str):
        for key, replacement in values.items():
            value = value.replace("{" + key + "}", replacement)
        return value
    if isinstance(value, list):
        return [expand_placeholders(item, values) for item in value]
    if isinstance(value, dict):
        return {key: expand_placeholders(item, values) for key, item in value.items()}
    return value


def run_command(
    command: str | list[str],
    *,
    cwd: str | Path | None = None,
    timeout_seconds: int = 300,
    env: dict[str, str] | None = None,
) -> dict:
    argv = command_argv(command)
    if not argv:
        raise ValueError("empty command")
    started = utc_now()
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            env={**os.environ, **(env or {})},
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "command": argv,
            "started_utc": started,
            "completed_utc": utc_now(),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": argv,
            "started_utc": started,
            "completed_utc": utc_now(),
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }


def git_output(repo: str | Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def git_identity(repo: str | Path) -> dict:
    root = Path(repo)
    return {
        "path": str(root.resolve()),
        "sha": git_output(root, "rev-parse", "HEAD"),
        "branch": git_output(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git_output(root, "status", "--porcelain")),
    }


def machine_identity() -> dict:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
    }


def file_state(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def scan_files(root: Path, patterns: list[str], recursive: bool = True) -> dict[str, tuple[int, int]]:
    if not root.exists():
        return {}
    iterator = root.rglob("*") if recursive else root.glob("*")
    found: dict[str, tuple[int, int]] = {}
    for path in iterator:
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(rel, pattern) for pattern in patterns):
            found[rel] = file_state(path)
    return found


def changed_files(before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]]) -> list[str]:
    return sorted(name for name, state in after.items() if before.get(name) != state)


def copy_immutable(source: Path, destination: Path) -> dict:
    import shutil

    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = sha256_file(source)
    if destination.exists():
        destination_hash = sha256_file(destination)
        if source_hash != destination_hash:
            raise RuntimeError(f"immutable archive collision: {destination}")
    else:
        shutil.copy2(source, destination)
    return {
        "path": str(destination),
        "name": destination.name,
        "size": destination.stat().st_size,
        "sha256": source_hash,
    }


def newest_glob(root: Path, pattern: str) -> Path | None:
    matches = [path for path in root.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime_ns)
