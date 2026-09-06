from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from auto_common import changed_files, copy_immutable, resolve_path, scan_files, write_json


def normalize_collectors(config: dict, workbench_root: Path) -> list[dict]:
    rows = []
    for raw in config.get("collectors", []):
        collector_id = str(raw.get("id", "")).strip()
        if not collector_id:
            raise ValueError("collector id is required")
        patterns = raw.get("patterns", ["*"])
        if not isinstance(patterns, list) or not patterns:
            raise ValueError(f"collector {collector_id} requires patterns")
        rows.append({
            "id": collector_id,
            "path": resolve_path(raw["path"], workbench_root),
            "patterns": [str(item) for item in patterns],
            "recursive": bool(raw.get("recursive", True)),
            "required": bool(raw.get("required", False)),
        })
    return rows


def snapshot_collectors(config: dict, workbench_root: Path) -> dict[str, dict[str, tuple[int, int]]]:
    return {
        row["id"]: scan_files(row["path"], row["patterns"], row["recursive"])
        for row in normalize_collectors(config, workbench_root)
    }


def collect_changes(
    config: dict,
    workbench_root: Path,
    before: dict[str, dict[str, tuple[int, int]]],
    run_dir: Path,
) -> list[dict]:
    collected: list[dict] = []
    for row in normalize_collectors(config, workbench_root):
        after = scan_files(row["path"], row["patterns"], row["recursive"])
        for rel in changed_files(before.get(row["id"], {}), after):
            source = row["path"] / rel
            destination = run_dir / "raw" / row["id"] / rel
            info = copy_immutable(source, destination)
            info.update({
                "collector_id": row["id"],
                "source_path": str(source),
                "archive_relative_path": destination.relative_to(run_dir).as_posix(),
                "kind": "collector_output",
            })
            collected.append(info)
    return collected


def wait_for_change(
    config: dict,
    workbench_root: Path,
    before: dict[str, dict[str, tuple[int, int]]],
    collector_id: str,
    pattern: str,
    timeout_seconds: int,
    poll_seconds: float = 0.5,
) -> list[str]:
    rows = {row["id"]: row for row in normalize_collectors(config, workbench_root)}
    if collector_id not in rows:
        raise ValueError(f"unknown collector: {collector_id}")
    row = rows[collector_id]
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() <= deadline:
        after = scan_files(row["path"], row["patterns"], row["recursive"])
        names = [
            name for name in changed_files(before.get(collector_id, {}), after)
            if Path(name).match(pattern) or Path(name).name == pattern
        ]
        if names:
            return names
        time.sleep(poll_seconds)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect files created or modified during an active engineering run.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--workbench-root", default=".")
    parser.add_argument("--snapshot-out")
    args = parser.parse_args()

    import json
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    root = Path(args.workbench_root).resolve()
    snapshot = snapshot_collectors(config, root)
    serializable: dict[str, dict[str, list[int]]] = {
        cid: {name: [state[0], state[1]] for name, state in files.items()}
        for cid, files in snapshot.items()
    }
    if args.snapshot_out:
        write_json(args.snapshot_out, serializable)
    else:
        print(json.dumps(serializable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
