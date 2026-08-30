from __future__ import annotations
from typing import Any


class ContractError(ValueError):
    pass


def validate_state_contract(contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ContractError("state contract must be an object")
    states = contract.get("states")
    transitions = contract.get("transitions")
    boundaries = contract.get("authority_boundaries")
    if not isinstance(states, list) or not states:
        raise ContractError("states must be a non-empty array")
    if not isinstance(transitions, list):
        raise ContractError("transitions must be an array")
    if not isinstance(boundaries, dict) or "hardware_protection" not in boundaries:
        raise ContractError("authority_boundaries.hardware_protection is required")

    ids: list[str] = []
    for state in states:
        if not isinstance(state, dict) or not str(state.get("id", "")).strip():
            raise ContractError("every state requires a non-empty id")
        sid = str(state["id"])
        if sid in ids:
            raise ContractError(f"duplicate state id: {sid}")
        ids.append(sid)
        for field in ("authority", "entry", "exit"):
            if field in state and not isinstance(state[field], list):
                raise ContractError(f"state {sid}.{field} must be an array")
    known = set(ids)
    for transition in transitions:
        if not isinstance(transition, dict):
            raise ContractError("transition must be an object")
        for key in ("from", "to", "event"):
            if not str(transition.get(key, "")).strip():
                raise ContractError(f"transition requires {key}")
        if transition["from"] not in known or transition["to"] not in known:
            raise ContractError(f"transition references unknown state: {transition}")
    reachable = {ids[0]}
    changed = True
    while changed:
        changed = False
        for transition in transitions:
            if transition["from"] in reachable and transition["to"] not in reachable:
                reachable.add(transition["to"])
                changed = True
    unreachable = sorted(known - reachable)
    return {"valid": True, "state_count": len(states), "transition_count": len(transitions), "unreachable_states": unreachable}
