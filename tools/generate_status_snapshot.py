from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workbench.status_service import build_live_status  # noqa: E402
from workbench.status_snapshot import sanitize_public_status  # noqa: E402

DATA_ROOT = ROOT / "engineering_data"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a sanitized, read-only ASR5K public status snapshot."
    )
    parser.add_argument("--agent-root", required=True)
    parser.add_argument("--firmware-root", required=True)
    parser.add_argument(
        "--output",
        default=str(DATA_ROOT / "status" / "status_snapshot.json"),
    )
    args = parser.parse_args()

    agent_root = Path(args.agent_root).expanduser().resolve()
    firmware_root = Path(args.firmware_root).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    model = build_live_status(agent_root, firmware_root, DATA_ROOT)
    public = sanitize_public_status(
        model,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(public, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"snapshot={output}")
    print(f"agent_sha={public['control_plane'].get('sha')}")
    print(f"firmware_sha={public['execution_plane'].get('sha')}")
    print(f"health={public['health']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
