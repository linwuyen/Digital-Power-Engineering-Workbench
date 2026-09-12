from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re

from .status_model import classify_freshness, derive_blockers, validate_status_model


FORBIDDEN_KEYS = {"path", "local_path", "workspace", "secret", "token"}
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


def _forbidden_key(key: object) -> bool:
    lowered = str(key).lower()
    return lowered in FORBIDDEN_KEYS or any(
        fragment in lowered for fragment in ("password", "secret", "token", "workspace")
    )


def _redact_string(value: str) -> str:
    parts = re.split(r"(\s+)", value)
    for index, part in enumerate(parts):
        if not part or part.isspace():
            continue
        token = part.strip("()[]{}<>,;\"'")
        if (
            token.startswith("/")
            or token.startswith("~/")
            or token.startswith("\\\\")
            or _WINDOWS_ABSOLUTE.match(token)
        ):
            prefix_len = part.find(token)
            suffix_start = prefix_len + len(token)
            parts[index] = part[:prefix_len] + "[REDACTED_LOCAL_PATH]" + part[suffix_start:]
    return "".join(parts)


def _strip(value):
    if isinstance(value, dict):
        return {
            key: _strip(item)
            for key, item in value.items()
            if not _forbidden_key(key)
        }
    if isinstance(value, list):
        return [_strip(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def sanitize_public_status(model: dict, *, generated_at: str) -> dict:
    public = _strip(deepcopy(model))
    public["mode"] = "SNAPSHOT"
    public["generated_at"] = generated_at
    public["authoritative_engineering_truth"] = False
    public.setdefault("execution_plane", {})["dirty"] = None
    public.setdefault("control_plane", {})["dirty"] = None
    public.setdefault("freshness", {})["status"] = "SNAPSHOT"
    public["freshness"]["age_seconds"] = 0
    validate_public_snapshot(public)
    return public


def validate_public_snapshot(model: dict) -> None:
    if model.get("mode") != "SNAPSHOT":
        raise ValueError("public status must be SNAPSHOT")
    if model.get("authoritative_engineering_truth") is not False:
        raise ValueError("public Workbench snapshot cannot claim authority")
    validate_status_model(model)


def load_snapshot(
    path: Path,
    *,
    now: datetime,
    stale_after_seconds: int,
) -> dict:
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_public_snapshot(model)
    generated = model.get("generated_at")
    freshness = classify_freshness(generated, now, stale_after_seconds)
    generated_dt = (
        datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        if generated
        else None
    )
    age_seconds = (
        int(max(0, (now - generated_dt).total_seconds()))
        if generated_dt is not None
        else None
    )
    model["freshness"]["status"] = freshness
    model["freshness"]["age_seconds"] = age_seconds
    model["blockers"] = derive_blockers(model)
    return model
