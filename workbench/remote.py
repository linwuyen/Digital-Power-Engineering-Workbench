from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import threading
import time


class RemoteCommandError(ValueError):
    pass


@dataclass
class RemoteState:
    voltage_set_v: float = 0.0
    current_limit_a: float = 1.0
    output_enabled: bool = False
    state: str = "STANDBY"
    mode: str = "CV"
    fault: str = "NONE"
    interlock_ok: bool = True


class SafeMockPowerSupply:
    """Deterministic mock transport. It demonstrates command boundaries, not hardware control."""

    def __init__(self, max_voltage_v: float = 700.0, max_current_a: float = 15.0) -> None:
        self.max_voltage_v = max_voltage_v
        self.max_current_a = max_current_a
        self._state = RemoteState()
        self._lock = threading.Lock()
        self._updated_at = time.time()

    def _bounded(self, name: str, value: float, lower: float, upper: float) -> float:
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise RemoteCommandError(f"{name} must be finite")
        value = float(value)
        if not lower <= value <= upper:
            raise RemoteCommandError(f"{name} must be in [{lower}, {upper}]")
        return value

    def command(self, action: str, value: float | None = None) -> dict:
        with self._lock:
            if action == "set_voltage":
                self._state.voltage_set_v = self._bounded("voltage", value, 0.0, self.max_voltage_v)
            elif action == "set_current":
                self._state.current_limit_a = self._bounded("current", value, 0.0, self.max_current_a)
            elif action == "output_on":
                if self._state.fault != "NONE":
                    raise RemoteCommandError("output_on blocked: fault is latched")
                if not self._state.interlock_ok:
                    raise RemoteCommandError("output_on blocked: interlock is open")
                self._state.output_enabled = True
                self._state.state = "RUN"
            elif action == "output_off":
                self._state.output_enabled = False
                self._state.state = "STANDBY"
            elif action == "clear_fault":
                if self._state.output_enabled:
                    raise RemoteCommandError("clear_fault blocked while output is enabled")
                self._state.fault = "NONE"
                self._state.state = "STANDBY"
            else:
                raise RemoteCommandError(f"unsupported action: {action}")
            self._updated_at = time.time()
            return self.telemetry_unlocked()

    def inject_fault_for_test(self, fault: str) -> None:
        with self._lock:
            self._state.fault = fault
            self._state.output_enabled = False
            self._state.state = "FAULT"
            self._updated_at = time.time()

    def telemetry_unlocked(self) -> dict:
        enabled = self._state.output_enabled
        vout = self._state.voltage_set_v if enabled else 0.0
        iout = min(self._state.current_limit_a * 0.35, vout / 100.0) if enabled else 0.0
        data = asdict(self._state)
        data.update({
            "vout_v": vout,
            "iout_a": iout,
            "pout_w": vout * iout,
            "updated_at": self._updated_at,
            "transport": "MOCK",
            "safety_boundary": "UI/host requests are non-safety authority. Real OVP/OCP/OTP/trip/interlock must remain local to hardware/firmware."
        })
        return data

    def telemetry(self) -> dict:
        with self._lock:
            return self.telemetry_unlocked()
