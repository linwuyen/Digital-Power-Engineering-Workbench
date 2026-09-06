from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "engineering_data" / "federation" / "source_manifest.json"
INDEX = ROOT / "engineering_data" / "index.json"
DEPRECATIONS = ROOT / "engineering_data" / "federation" / "deprecation_registry.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    errors: list[str] = []
    manifest = load(MANIFEST)
    index = load(INDEX)
    deprecations = load(DEPRECATIONS)

    if manifest.get("workbench_role") != "view_analysis_plane":
        errors.append("Workbench role must be view_analysis_plane")
    if manifest.get("authoritative_engineering_truth") is not False:
        errors.append("Workbench must not claim authoritative engineering truth")

    sources = manifest.get("sources", {})
    if sources.get("control_plane", {}).get("repository") != "linwuyen/ASR5K_AGENT":
        errors.append("Control Plane owner mismatch")
    if sources.get("execution_plane", {}).get("repository") != "linwuyen/ASR5K_v2_28384":
        errors.append("Execution Plane owner mismatch")
    if sources.get("view_plane", {}).get("repository") != "linwuyen/Digital-Power-Engineering-Workbench":
        errors.append("View Plane owner mismatch")

    policy = manifest.get("snapshot_policy", {})
    if policy.get("engineering_data_role") != "derived_snapshot_cache":
        errors.append("engineering_data must be a derived snapshot/cache")
    if policy.get("may_override_control_plane") is not False:
        errors.append("snapshot may not override Control Plane")
    if policy.get("may_override_execution_plane") is not False:
        errors.append("snapshot may not override Execution Plane")
    if policy.get("exact_sha_evidence_transfers_to_descendants") is not False:
        errors.append("exact-SHA evidence inheritance must remain false")

    if index.get("authoritative_engineering_truth") is not False:
        errors.append("index must not claim authoritative engineering truth")
    if index.get("role") != "view_analysis_plane_snapshot":
        errors.append("index role mismatch")
    if index.get("baseline", {}).get("freshness") != "historical_snapshot":
        errors.append("checked-in ASR5K dataset must be marked historical_snapshot")
    if index.get("consumer_policy", {}).get("new_execution_plane_automation_allowed_in_workbench") is not False:
        errors.append("new execution-plane automation must be disallowed in Workbench")

    forbidden = set(deprecations.get("forbidden_new_workbench_authority", []))
    required_forbidden = {
        "production_build_owner",
        "production_flash_owner",
        "physical_hil_owner",
        "qualification_transaction_owner",
        "durable_product_contract_owner",
        "durable_current_status_owner",
    }
    if not required_forbidden.issubset(forbidden):
        errors.append("deprecation registry is missing required forbidden authority classes")

    for item in deprecations.get("items", []):
        if item.get("replacement_owner") != "linwuyen/ASR5K_v2_28384":
            errors.append(f"deprecated execution item has wrong replacement owner: {item.get('path')}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"FEDERATION_BOUNDARY_FAIL: {error}")
        return 2
    print("FEDERATION_BOUNDARY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
