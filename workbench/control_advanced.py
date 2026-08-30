from __future__ import annotations
from dataclasses import dataclass
import cmath
import math


class AdvancedControlError(ValueError):
    pass


@dataclass(frozen=True)
class PlantModel:
    model: str = "second_order_rhpz"
    dc_gain: float = 1.0
    resonance_hz: float = 1000.0
    q: float = 0.707
    rhpz_hz: float | None = None

    def validate(self) -> None:
        if self.model != "second_order_rhpz":
            raise AdvancedControlError("supported model: second_order_rhpz")
        if not math.isfinite(self.dc_gain):
            raise AdvancedControlError("dc_gain must be finite")
        if self.resonance_hz <= 0 or self.q <= 0:
            raise AdvancedControlError("resonance_hz and q must be > 0")
        if self.rhpz_hz is not None and self.rhpz_hz <= 0:
            raise AdvancedControlError("rhpz_hz must be > 0 when supplied")


@dataclass(frozen=True)
class PoleZeroController:
    gain: float
    zeros_hz: tuple[float, ...] = ()
    poles_hz: tuple[float, ...] = ()
    integrator: bool = True

    def validate(self) -> None:
        if not math.isfinite(self.gain) or self.gain < 0:
            raise AdvancedControlError("controller gain must be finite and >= 0")
        if any(x <= 0 or not math.isfinite(x) for x in self.zeros_hz + self.poles_hz):
            raise AdvancedControlError("controller pole/zero frequencies must be finite and > 0")


def _plant(s: complex, cfg: PlantModel) -> complex:
    w0 = 2 * math.pi * cfg.resonance_hz
    denominator = 1 + s / (cfg.q * w0) + (s / w0) ** 2
    numerator = complex(cfg.dc_gain, 0)
    if cfg.rhpz_hz:
        numerator *= 1 - s / (2 * math.pi * cfg.rhpz_hz)
    return numerator / denominator


def _controller(s: complex, cfg: PoleZeroController) -> complex:
    value = complex(cfg.gain, 0)
    if cfg.integrator:
        value /= s
    for f in cfg.zeros_hz:
        value *= 1 + s / (2 * math.pi * f)
    for f in cfg.poles_hz:
        value /= 1 + s / (2 * math.pi * f)
    return value


def analyze_pole_zero_loop(plant: PlantModel, controller: PoleZeroController, sampling_hz: float,
                           delay_samples: float = 1.0, points: int = 240) -> dict:
    plant.validate(); controller.validate()
    if sampling_hz <= 0 or delay_samples < 0:
        raise AdvancedControlError("sampling_hz must be > 0 and delay_samples >= 0")
    fmin = max(1.0, plant.resonance_hz / 1000)
    fmax = sampling_hz * 0.45
    freqs = [10 ** (math.log10(fmin) + (math.log10(fmax)-math.log10(fmin))*i/(points-1)) for i in range(points)]
    pmag=[]; pphase=[]; lmag=[]; lphase_raw=[]
    delay_s = delay_samples / sampling_hz
    for f in freqs:
        s = complex(0, 2*math.pi*f)
        p = _plant(s, plant)
        c = _controller(s, controller)
        loop = p*c*cmath.exp(-s*delay_s)
        pmag.append(20*math.log10(max(abs(p), 1e-30)))
        pphase.append(math.degrees(cmath.phase(p)))
        lmag.append(20*math.log10(max(abs(loop), 1e-30)))
        lphase_raw.append(math.degrees(cmath.phase(loop)))
    lphase=[lphase_raw[0]]
    for v in lphase_raw[1:]:
        prev=lphase[-1]
        while v-prev>180: v-=360
        while v-prev<-180: v+=360
        lphase.append(v)
    crossover=pm=None
    for i in range(1,len(freqs)):
        if (lmag[i-1]>=0>=lmag[i]) or (lmag[i-1]<=0<=lmag[i]):
            a=0 if lmag[i]==lmag[i-1] else -lmag[i-1]/(lmag[i]-lmag[i-1])
            crossover=10**(math.log10(freqs[i-1])+a*(math.log10(freqs[i])-math.log10(freqs[i-1])))
            phase=lphase[i-1]+a*(lphase[i]-lphase[i-1]); pm=180+phase; break
    warnings=[]
    if crossover is None: warnings.append("No 0 dB crossover found.")
    elif crossover > sampling_hz/10: warnings.append("Crossover exceeds sampling/10; delay and discrete implementation require measured verification.")
    if pm is not None and pm < 45: warnings.append("Phase margin is below 45 degrees.")
    if plant.rhpz_hz and crossover and crossover > plant.rhpz_hz/3:
        warnings.append("Crossover approaches the RHP zero; controller authority should be reduced or plant re-modelled.")
    return {"frequency_hz":freqs,"plant_mag_db":pmag,"plant_phase_deg":pphase,"loop_mag_db":lmag,"loop_phase_deg":lphase,
            "crossover_hz":crossover,"phase_margin_deg":pm,"warnings":warnings,
            "model_boundary":"Topology-agnostic second-order + optional RHP-zero model. Identify parameters from design equations or SFRA; do not treat it as a topology-specific truth source."}
