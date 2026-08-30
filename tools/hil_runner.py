from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from truth_common import load_json, write_json


FORBIDDEN_ACTIONS = {
    "direct_pwm",
    "disable_ovp",
    "disable_ocp",
    "disable_otp",
    "disable_trip",
    "clear_hardware_interlock",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_path(value: Any, path: str):
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(path)
    return current


class MockAdapter:
    name = "mock"

    def transact(self, request: dict, step: dict) -> dict:
        return dict(step.get("mock_response", {"status": "MOCK_OK", "echo": request}))

    def close(self) -> None:
        pass


class ProcessAdapter:
    name = "process-jsonl"

    def __init__(self, command: str):
        self.process = subprocess.Popen(
            shlex.split(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def transact(self, request: dict, step: dict) -> dict:
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("gateway process pipes are unavailable")
        self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"gateway closed without response: {stderr.strip()}")
        return json.loads(line)

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()


def validate_plan(plan: dict) -> None:
    for name in ("id", "baseline", "requirements", "steps"):
        if name not in plan:
            raise ValueError(f"HIL plan missing {name}")
    if not isinstance(plan["requirements"], list) or not plan["requirements"]:
        raise ValueError("HIL plan must link at least one requirement")
    if not isinstance(plan["steps"], list) or not plan["steps"]:
        raise ValueError("HIL plan must contain steps")
    for index, step in enumerate(plan["steps"]):
        op = step.get("op")
        if op not in {"send", "expect", "wait_ms", "note"}:
            raise ValueError(f"unsupported HIL op at step {index}: {op}")
        if op == "send":
            request = step.get("request")
            if not isinstance(request, dict):
                raise ValueError(f"send step {index} requires request object")
            action = str(request.get("action", "")).lower()
            if action in FORBIDDEN_ACTIONS:
                raise ValueError(f"forbidden browser/host safety-authority action: {action}")
        if op == "wait_ms":
            value = int(step.get("value", -1))
            if value < 0 or value > 10000:
                raise ValueError(f"wait_ms step {index} must be within 0..10000")


def run_plan(plan: dict, adapter, mode: str) -> dict:
    validate_plan(plan)
    started = utc_now()
    run_id = f"HILRUN-{uuid.uuid4()}"
    steps_out = []
    last_response = None
    passed = True

    try:
        for index, step in enumerate(plan["steps"]):
            op = step["op"]
            row = {"index": index, "op": op, "status": "PASS"}
            try:
                if op == "send":
                    last_response = adapter.transact(step["request"], step)
                    row["response"] = last_response
                elif op == "expect":
                    if last_response is None:
                        raise RuntimeError("expect has no preceding response")
                    actual = get_path(last_response, step["path"])
                    expected = step["equals"]
                    row.update({"actual": actual, "expected": expected})
                    if actual != expected:
                        raise AssertionError(f"{step['path']}: {actual!r} != {expected!r}")
                elif op == "wait_ms":
                    time.sleep(int(step["value"]) / 1000.0)
                elif op == "note":
                    row["text"] = str(step.get("text", ""))
            except Exception as exc:  # report exact step and stop
                row["status"] = "FAIL"
                row["error"] = str(exc)
                steps_out.append(row)
                passed = False
                break
            steps_out.append(row)
    finally:
        adapter.close()

    if mode == "mock":
        result = "SIMULATION_PASS" if passed else "SIMULATION_FAIL"
    else:
        result = "HARDWARE_RUN_PASS_UNQUALIFIED" if passed else "HARDWARE_RUN_FAIL_UNQUALIFIED"

    return {
        "schema_version": "1.0",
        "record_type": "hil_run",
        "run_id": run_id,
        "test_id": plan["id"],
        "baseline": plan["baseline"],
        "requirements": plan["requirements"],
        "adapter": adapter.name,
        "mode": mode,
        "started_utc": started,
        "completed_utc": utc_now(),
        "result": result,
        "qualification_claimed": False,
        "steps": steps_out,
        "next_action": "Bind this run to exact DUT/build/evidence artifacts and import through tools/import_evidence.py before any qualification PASS claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a host-intent HIL plan without granting the harness protection authority.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--mode", choices=["mock", "process"], default="mock")
    parser.add_argument("--gateway-command")
    parser.add_argument("--allow-hardware", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    plan = load_json(args.plan)
    if args.mode == "process":
        if not args.allow_hardware:
            raise SystemExit("process HIL requires explicit --allow-hardware")
        if not args.gateway_command:
            raise SystemExit("process HIL requires --gateway-command")
        adapter = ProcessAdapter(args.gateway_command)
    else:
        adapter = MockAdapter()

    report = run_plan(plan, adapter, args.mode)
    write_json(args.out, report)
    print(f"{report['test_id']}: {report['result']} (qualification_claimed=false)")
    return 0 if report["result"].endswith("PASS") or "PASS_" in report["result"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
