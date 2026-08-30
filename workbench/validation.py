from __future__ import annotations
from typing import Any
from .remote import SafeMockPowerSupply, RemoteCommandError


class ValidationError(ValueError):
    pass


def run_sequence(steps: list[dict[str, Any]], psu: SafeMockPowerSupply | None = None) -> dict[str, Any]:
    if not isinstance(steps, list) or not steps:
        raise ValidationError("steps must be a non-empty array")
    psu = psu or SafeMockPowerSupply()
    results=[]
    passed=True
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValidationError(f"step {index} must be an object")
        action=step.get("action")
        try:
            if action in {"set_voltage","set_current"}:
                telemetry=psu.command(action, step.get("value"))
            elif action in {"output_on","output_off","clear_fault"}:
                telemetry=psu.command(action)
            elif action=="inject_fault":
                psu.inject_fault_for_test(str(step.get("fault","TEST_FAULT"))); telemetry=psu.telemetry()
            elif action=="assert":
                telemetry=psu.telemetry(); field=str(step.get("field","")); expected=step.get("equals")
                actual=telemetry.get(field)
                if actual != expected:
                    raise ValidationError(f"assert failed: {field}={actual!r}, expected {expected!r}")
            else:
                raise ValidationError(f"unsupported action: {action}")
            results.append({"index":index,"action":action,"pass":True,"telemetry":telemetry})
        except (RemoteCommandError, ValidationError) as exc:
            passed=False; results.append({"index":index,"action":action,"pass":False,"error":str(exc),"telemetry":psu.telemetry()})
            if not step.get("continue_on_fail", False):
                break
    return {"pass":passed,"steps":results,"final_telemetry":psu.telemetry(),
            "boundary":"Sequence runner verifies command policy against the mock. Real hardware validation still requires independent measurements and local protection authority."}
