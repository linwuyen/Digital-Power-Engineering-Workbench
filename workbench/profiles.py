from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .measurement import SignalChainConfig


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class SignalChainProfile:
    profile_id: str
    name: str
    unit: str
    config: SignalChainConfig
    notes: str = ""
    source: str = "User/reference profile; verify against the actual schematic and datasheet before hardware decisions."

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["config"] = asdict(self.config)
        return data


_BUILTINS = (
    SignalChainProfile(
        "generic-unipolar-3v3-12b", "Generic 0–3.3 V / 12-bit ADC", "V",
        SignalChainConfig(1.0, 0.0, 1.0, 0.0, 1.0, 3.3, 12),
        "Direct unipolar ADC reference profile."
    ),
    SignalChainProfile(
        "generic-bipolar-current-centered", "Generic bipolar current / 1.65 V centered", "A",
        SignalChainConfig(0.04, 0.0, 2.5, 1.65, 1.0, 3.3, 12),
        "Reference current-sense chain with midscale offset; replace coefficients with measured values."
    ),
    SignalChainProfile(
        "generic-0-10v-divider", "Generic 0–10 V input → 3.3 V ADC", "V",
        SignalChainConfig(1.0, 0.0, 1.0, 0.0, 0.30, 3.3, 12),
        "Reference divider model only; resistor tolerance and protection network are not included."
    ),
)


def builtin_profiles() -> list[dict[str, Any]]:
    return [p.to_dict() for p in _BUILTINS]


def profile_from_dict(data: dict[str, Any]) -> SignalChainProfile:
    if not isinstance(data, dict):
        raise ProfileError("profile must be an object")
    required = ("profile_id", "name", "unit", "config")
    missing = [key for key in required if key not in data]
    if missing:
        raise ProfileError(f"missing profile fields: {', '.join(missing)}")
    cfg = data["config"]
    if not isinstance(cfg, dict):
        raise ProfileError("config must be an object")
    try:
        config = SignalChainConfig(**cfg)
    except TypeError as exc:
        raise ProfileError(f"invalid signal-chain config: {exc}") from exc
    config.validate()
    profile_id = str(data["profile_id"]).strip()
    name = str(data["name"]).strip()
    unit = str(data["unit"]).strip()
    if not profile_id or not name or not unit:
        raise ProfileError("profile_id, name and unit must be non-empty")
    return SignalChainProfile(
        profile_id=profile_id,
        name=name,
        unit=unit,
        config=config,
        notes=str(data.get("notes", "")),
        source=str(data.get("source", "User supplied; verify before hardware use.")),
    )
