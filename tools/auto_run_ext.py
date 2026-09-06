from __future__ import annotations

import copy

import auto_run as core


_original_validate_plan = core.validate_plan
_original_preflight = core.preflight


def validate_plan(plan: dict) -> None:
    if plan.get("mode") != "build":
        _original_validate_plan(plan)
        return
    shadow = copy.deepcopy(plan)
    shadow["mode"] = "hardware"
    _original_validate_plan(shadow)
    for step in plan.get("steps", []):
        if step.get("op") == "hil":
            raise ValueError("build mode cannot execute HIL")
        if step.get("op") == "wait_for_file":
            raise ValueError("build mode cannot wait for physical collector output")
        if step.get("hardware", False):
            raise ValueError("build mode cannot execute hardware command steps")
    for claim in plan.get("evidence_claims", []):
        if claim.get("physical_evidence_required", False):
            raise ValueError("build mode cannot satisfy physical evidence claims")


def preflight(plan: dict, config: dict) -> dict:
    if plan.get("mode") != "build":
        return _original_preflight(plan, config)
    shadow = copy.deepcopy(plan)
    shadow["mode"] = "simulation"
    shadow.setdefault("preflight", {})
    shadow["preflight"]["production_repo_required"] = True
    shadow["preflight"].setdefault("require_clean_production_repo", True)
    report = _original_preflight(shadow, config)
    report["run_mode"] = "build"
    return report


core.validate_plan = validate_plan
core.preflight = preflight


if __name__ == "__main__":
    raise SystemExit(core.main())
