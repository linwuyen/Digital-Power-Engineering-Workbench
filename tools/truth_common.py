from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


_C_SUFFIX = re.compile(r"(?i)(?:u|l)+$")


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, value: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//.*?$", "", text, flags=re.M)


def parse_c_int(expression: str) -> int:
    value = expression.strip()
    while value.startswith("(") and value.endswith(")"):
        value = value[1:-1].strip()
    value = _C_SUFFIX.sub("", value).strip()
    if not re.fullmatch(r"(?:0[xX][0-9A-Fa-f]+|[0-9]+)", value):
        raise ValueError(f"unsupported C integer expression: {expression!r}")
    return int(value, 0)


def extract_define_int(text: str, name: str) -> int:
    clean = strip_c_comments(text)
    match = re.search(
        rf"^\s*#\s*define\s+{re.escape(name)}\s+([^\r\n]+)$",
        clean,
        flags=re.M,
    )
    if not match:
        raise KeyError(f"missing #define {name}")
    return parse_c_int(match.group(1))


def extract_enum(text: str, typedef_name: str) -> list[dict[str, int | str]]:
    clean = strip_c_comments(text)
    match = re.search(
        rf"typedef\s+enum\s*\{{(?P<body>.*?)\}}\s*{re.escape(typedef_name)}\s*;",
        clean,
        flags=re.S,
    )
    if not match:
        raise KeyError(f"missing enum {typedef_name}")

    rows: list[dict[str, int | str]] = []
    current = -1
    for raw in match.group("body").split(","):
        token = raw.strip()
        if not token:
            continue
        if "=" in token:
            name, expression = token.split("=", 1)
            current = parse_c_int(expression)
        else:
            name = token
            current += 1
        rows.append({"name": name.strip(), "value": current})
    return rows


def require_files(root: str | Path, paths: list[str]) -> dict[str, Path]:
    base = Path(root)
    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for relative in paths:
        path = base / relative
        if path.is_file():
            resolved[relative] = path
        else:
            missing.append(relative)
    if missing:
        raise FileNotFoundError("missing source files: " + ", ".join(missing))
    return resolved
