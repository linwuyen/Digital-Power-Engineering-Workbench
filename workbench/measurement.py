from __future__ import annotations

from dataclasses import dataclass, asdict
import math


class MeasurementError(ValueError):
    pass


@dataclass(frozen=True)
class SignalChainConfig:
    sensor_gain_v_per_unit: float
    sensor_offset_v: float
    opamp_gain: float
    opamp_offset_v: float
    divider_ratio: float
    adc_vref_v: float
    adc_bits: int

    def validate(self) -> None:
        numeric = {
            "sensor_gain_v_per_unit": self.sensor_gain_v_per_unit,
            "sensor_offset_v": self.sensor_offset_v,
            "opamp_gain": self.opamp_gain,
            "opamp_offset_v": self.opamp_offset_v,
            "divider_ratio": self.divider_ratio,
            "adc_vref_v": self.adc_vref_v,
        }
        for name, value in numeric.items():
            if not math.isfinite(value):
                raise MeasurementError(f"{name} must be finite")
        if self.sensor_gain_v_per_unit == 0:
            raise MeasurementError("sensor_gain_v_per_unit must be non-zero")
        if self.opamp_gain == 0:
            raise MeasurementError("opamp_gain must be non-zero")
        if not 0 < self.divider_ratio <= 1:
            raise MeasurementError("divider_ratio must be in (0, 1]")
        if self.adc_vref_v <= 0:
            raise MeasurementError("adc_vref_v must be > 0")
        if not 1 <= self.adc_bits <= 32:
            raise MeasurementError("adc_bits must be in [1, 32]")


@dataclass(frozen=True)
class SignalChainResult:
    physical_value: float
    sensor_output_v: float
    opamp_output_v: float
    adc_input_v: float
    adc_code_ideal: float
    adc_code: int
    adc_lsb_v: float
    clipped: bool
    recovered_physical_value: float
    quantization_error_physical: float

    def to_dict(self) -> dict:
        return asdict(self)


def _adc_max_code(bits: int) -> int:
    return (1 << bits) - 1


def physical_to_adc(physical_value: float, cfg: SignalChainConfig) -> SignalChainResult:
    cfg.validate()
    if not math.isfinite(physical_value):
        raise MeasurementError("physical_value must be finite")

    sensor_output = physical_value * cfg.sensor_gain_v_per_unit + cfg.sensor_offset_v
    opamp_output = sensor_output * cfg.opamp_gain + cfg.opamp_offset_v
    adc_input = opamp_output * cfg.divider_ratio
    max_code = _adc_max_code(cfg.adc_bits)
    lsb = cfg.adc_vref_v / max_code
    ideal_code = adc_input / cfg.adc_vref_v * max_code
    clipped_code = min(max(ideal_code, 0.0), float(max_code))
    code = int(round(clipped_code))
    clipped = ideal_code < 0.0 or ideal_code > max_code
    recovered = adc_to_physical(code, cfg)

    return SignalChainResult(
        physical_value=physical_value,
        sensor_output_v=sensor_output,
        opamp_output_v=opamp_output,
        adc_input_v=adc_input,
        adc_code_ideal=ideal_code,
        adc_code=code,
        adc_lsb_v=lsb,
        clipped=clipped,
        recovered_physical_value=recovered,
        quantization_error_physical=recovered - physical_value,
    )


def adc_to_physical(adc_code: int, cfg: SignalChainConfig) -> float:
    cfg.validate()
    max_code = _adc_max_code(cfg.adc_bits)
    if not isinstance(adc_code, int):
        raise MeasurementError("adc_code must be an integer")
    if not 0 <= adc_code <= max_code:
        raise MeasurementError(f"adc_code must be in [0, {max_code}]")

    adc_input = adc_code / max_code * cfg.adc_vref_v
    opamp_output = adc_input / cfg.divider_ratio
    sensor_output = (opamp_output - cfg.opamp_offset_v) / cfg.opamp_gain
    return (sensor_output - cfg.sensor_offset_v) / cfg.sensor_gain_v_per_unit
