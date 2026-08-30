from __future__ import annotations

from dataclasses import dataclass, asdict
import cmath
import math


class ControlError(ValueError):
    pass


@dataclass(frozen=True)
class BuckPlantConfig:
    vin_v: float
    inductance_h: float
    capacitance_f: float
    load_ohm: float
    switching_hz: float
    sampling_hz: float
    kp: float
    ki: float
    delay_samples: float = 1.0

    def validate(self) -> None:
        positive = {
            "vin_v": self.vin_v,
            "inductance_h": self.inductance_h,
            "capacitance_f": self.capacitance_f,
            "load_ohm": self.load_ohm,
            "switching_hz": self.switching_hz,
            "sampling_hz": self.sampling_hz,
        }
        for name, value in positive.items():
            if not math.isfinite(value) or value <= 0:
                raise ControlError(f"{name} must be finite and > 0")
        for name, value in {"kp": self.kp, "ki": self.ki, "delay_samples": self.delay_samples}.items():
            if not math.isfinite(value):
                raise ControlError(f"{name} must be finite")
        if self.kp < 0 or self.ki < 0 or self.delay_samples < 0:
            raise ControlError("kp, ki, and delay_samples must be >= 0")


@dataclass(frozen=True)
class PiTustinCoefficients:
    b0: float
    b1: float
    sample_time_s: float

    def to_dict(self) -> dict:
        return asdict(self)


def pi_tustin(kp: float, ki: float, sampling_hz: float) -> PiTustinCoefficients:
    if sampling_hz <= 0:
        raise ControlError("sampling_hz must be > 0")
    ts = 1.0 / sampling_hz
    return PiTustinCoefficients(
        b0=kp + ki * ts / 2.0,
        b1=-kp + ki * ts / 2.0,
        sample_time_s=ts,
    )


def _logspace(start_hz: float, stop_hz: float, count: int) -> list[float]:
    a = math.log10(start_hz)
    b = math.log10(stop_hz)
    return [10 ** (a + (b - a) * i / (count - 1)) for i in range(count)]


def _unwrap_phase_deg(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for value in values[1:]:
        previous = result[-1]
        while value - previous > 180.0:
            value -= 360.0
        while value - previous < -180.0:
            value += 360.0
        result.append(value)
    return result


def _buck_gvd(s: complex, cfg: BuckPlantConfig) -> complex:
    # Ideal CCM buck, voltage-mode control-to-output plant.
    denominator = cfg.inductance_h * cfg.capacitance_f * s * s + (cfg.inductance_h / cfg.load_ohm) * s + 1.0
    return cfg.vin_v / denominator


def _pi(s: complex, cfg: BuckPlantConfig) -> complex:
    if abs(s) == 0:
        return complex(float("inf"), 0.0)
    return cfg.kp + cfg.ki / s


def analyze_buck_pi(cfg: BuckPlantConfig, points: int = 160) -> dict:
    cfg.validate()
    if not 40 <= points <= 2000:
        raise ControlError("points must be in [40, 2000]")

    f_min = max(1.0, cfg.switching_hz / 100000.0)
    f_max = min(cfg.sampling_hz * 0.45, cfg.switching_hz * 0.5)
    if f_max <= f_min:
        raise ControlError("frequency range is invalid; check sampling/switching frequencies")

    freqs = _logspace(f_min, f_max, points)
    plant_mag_db: list[float] = []
    plant_phase_deg: list[float] = []
    loop_mag_db: list[float] = []
    loop_phase_raw_deg: list[float] = []

    delay_s = cfg.delay_samples / cfg.sampling_hz
    for f in freqs:
        w = 2.0 * math.pi * f
        s = complex(0.0, w)
        plant = _buck_gvd(s, cfg)
        controller = _pi(s, cfg)
        delay = cmath.exp(-s * delay_s)
        loop = plant * controller * delay

        plant_mag_db.append(20.0 * math.log10(max(abs(plant), 1e-30)))
        plant_phase_deg.append(math.degrees(cmath.phase(plant)))
        loop_mag_db.append(20.0 * math.log10(max(abs(loop), 1e-30)))
        loop_phase_raw_deg.append(math.degrees(cmath.phase(loop)))

    loop_phase_deg = _unwrap_phase_deg(loop_phase_raw_deg)
    crossover_hz = None
    phase_margin_deg = None
    for i in range(1, len(freqs)):
        y0, y1 = loop_mag_db[i - 1], loop_mag_db[i]
        if (y0 >= 0.0 and y1 <= 0.0) or (y0 <= 0.0 and y1 >= 0.0):
            if y1 == y0:
                alpha = 0.0
            else:
                alpha = (0.0 - y0) / (y1 - y0)
            logf = math.log10(freqs[i - 1]) + alpha * (math.log10(freqs[i]) - math.log10(freqs[i - 1]))
            crossover_hz = 10 ** logf
            phase = loop_phase_deg[i - 1] + alpha * (loop_phase_deg[i] - loop_phase_deg[i - 1])
            phase_margin_deg = 180.0 + phase
            break

    coeff = pi_tustin(cfg.kp, cfg.ki, cfg.sampling_hz)
    resonance_hz = 1.0 / (2.0 * math.pi * math.sqrt(cfg.inductance_h * cfg.capacitance_f))
    warnings: list[str] = []
    if crossover_hz is None:
        warnings.append("No 0 dB loop crossover found in the evaluated frequency range.")
    else:
        if crossover_hz > cfg.sampling_hz / 10.0:
            warnings.append("Crossover exceeds fs/10; digital delay/model fidelity needs verification.")
        if crossover_hz > cfg.switching_hz / 10.0:
            warnings.append("Crossover exceeds fsw/10; averaged plant assumptions may be weak.")
    if phase_margin_deg is not None and phase_margin_deg < 45.0:
        warnings.append("Phase margin is below 45 degrees.")
    if phase_margin_deg is not None and phase_margin_deg <= 0.0:
        warnings.append("Computed phase margin is non-positive; do not apply these gains to hardware without loop re-design and measured verification.")

    return {
        "resonance_hz": resonance_hz,
        "crossover_hz": crossover_hz,
        "phase_margin_deg": phase_margin_deg,
        "pi_tustin": coeff.to_dict(),
        "frequency_hz": freqs,
        "plant_mag_db": plant_mag_db,
        "plant_phase_deg": plant_phase_deg,
        "loop_mag_db": loop_mag_db,
        "loop_phase_deg": loop_phase_deg,
        "warnings": warnings,
        "model_boundary": "Ideal CCM buck averaged plant with PI and pure computation/PWM delay. Validate against SFRA or measured loop gain before hardware authority changes.",
    }
