from __future__ import annotations
import csv
import io
import math
from typing import Any


class SfraError(ValueError):
    pass


def _normalize(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def parse_sfra_csv(text: str) -> list[dict[str, float]]:
    if not isinstance(text, str) or not text.strip():
        raise SfraError("CSV text is empty")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise SfraError("CSV header is missing")
    aliases = {_normalize(name): name for name in reader.fieldnames}
    def find(candidates: tuple[str, ...]) -> str:
        for candidate in candidates:
            if _normalize(candidate) in aliases:
                return aliases[_normalize(candidate)]
        raise SfraError(f"missing column; expected one of {candidates}")
    fcol = find(("frequency_hz", "frequency", "freq_hz", "freq"))
    mcol = find(("magnitude_db", "gain_db", "mag_db", "magnitude"))
    pcol = find(("phase_deg", "phase", "phase_degrees"))
    rows: list[dict[str, float]] = []
    for line_no, row in enumerate(reader, start=2):
        try:
            f = float(row[fcol]); m = float(row[mcol]); p = float(row[pcol])
        except (TypeError, ValueError) as exc:
            raise SfraError(f"invalid numeric value at CSV line {line_no}") from exc
        if not all(math.isfinite(v) for v in (f, m, p)) or f <= 0:
            raise SfraError(f"invalid SFRA point at CSV line {line_no}")
        rows.append({"frequency_hz": f, "magnitude_db": m, "phase_deg": p})
    if len(rows) < 2:
        raise SfraError("at least two SFRA points are required")
    rows.sort(key=lambda x: x["frequency_hz"])
    return rows


def _interp_log(freqs: list[float], values: list[float], f: float) -> float | None:
    if f < freqs[0] or f > freqs[-1]:
        return None
    x = math.log10(f)
    for i in range(1, len(freqs)):
        if f <= freqs[i]:
            x0, x1 = math.log10(freqs[i-1]), math.log10(freqs[i])
            if x1 == x0:
                return values[i]
            a = (x - x0) / (x1 - x0)
            return values[i-1] + a * (values[i] - values[i-1])
    return values[-1]


def compare_theory_to_sfra(theory: dict[str, Any], measured: list[dict[str, float]]) -> dict[str, Any]:
    freqs = [float(v) for v in theory.get("frequency_hz", [])]
    mags = [float(v) for v in theory.get("loop_mag_db", theory.get("plant_mag_db", []))]
    phases = [float(v) for v in theory.get("loop_phase_deg", theory.get("plant_phase_deg", []))]
    if len(freqs) < 2 or len(freqs) != len(mags) or len(freqs) != len(phases):
        raise SfraError("theory response arrays are missing or inconsistent")
    aligned = []
    for point in measured:
        tm = _interp_log(freqs, mags, point["frequency_hz"])
        tp = _interp_log(freqs, phases, point["frequency_hz"])
        if tm is not None and tp is not None:
            aligned.append({**point, "theory_magnitude_db": tm, "theory_phase_deg": tp,
                            "magnitude_error_db": point["magnitude_db"] - tm,
                            "phase_error_deg": point["phase_deg"] - tp})
    if not aligned:
        raise SfraError("measured and theory frequency ranges do not overlap")
    rms_mag = math.sqrt(sum(x["magnitude_error_db"]**2 for x in aligned) / len(aligned))
    rms_phase = math.sqrt(sum(x["phase_error_deg"]**2 for x in aligned) / len(aligned))
    return {"aligned": aligned, "rms_magnitude_error_db": rms_mag, "rms_phase_error_deg": rms_phase,
            "warning": "Large theory/measurement error is a model-mismatch signal; do not tune hardware from the theoretical model alone."}
