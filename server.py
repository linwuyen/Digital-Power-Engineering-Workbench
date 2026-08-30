from __future__ import annotations

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path

from workbench.control import BuckPlantConfig, ControlError, analyze_buck_pi
from workbench.measurement import MeasurementError, SignalChainConfig, physical_to_adc
from workbench.remote import RemoteCommandError, SafeMockPowerSupply
from workbench.state_machine import get_state_machine

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
REMOTE = SafeMockPowerSupply()


class WorkbenchHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            raise ValueError("invalid request body size")
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def do_GET(self):
        if self.path == "/api/health":
            return self._json(200, {"ok": True, "service": "digital-power-engineering-workbench"})
        if self.path == "/api/state-machine":
            return self._json(200, get_state_machine())
        if self.path == "/api/remote/telemetry":
            return self._json(200, REMOTE.telemetry())
        return super().do_GET()

    def do_POST(self):
        try:
            payload = self._read_json()
            if self.path == "/api/datasheet/signal-chain":
                cfg = SignalChainConfig(
                    sensor_gain_v_per_unit=float(payload["sensor_gain_v_per_unit"]),
                    sensor_offset_v=float(payload.get("sensor_offset_v", 0.0)),
                    opamp_gain=float(payload.get("opamp_gain", 1.0)),
                    opamp_offset_v=float(payload.get("opamp_offset_v", 0.0)),
                    divider_ratio=float(payload.get("divider_ratio", 1.0)),
                    adc_vref_v=float(payload["adc_vref_v"]),
                    adc_bits=int(payload["adc_bits"])
                )
                result = physical_to_adc(float(payload["physical_value"]), cfg)
                return self._json(200, result.to_dict())

            if self.path == "/api/control/buck-pi":
                cfg = BuckPlantConfig(
                    vin_v=float(payload["vin_v"]),
                    inductance_h=float(payload["inductance_h"]),
                    capacitance_f=float(payload["capacitance_f"]),
                    load_ohm=float(payload["load_ohm"]),
                    switching_hz=float(payload["switching_hz"]),
                    sampling_hz=float(payload["sampling_hz"]),
                    kp=float(payload["kp"]),
                    ki=float(payload["ki"]),
                    delay_samples=float(payload.get("delay_samples", 1.0))
                )
                return self._json(200, analyze_buck_pi(cfg))

            if self.path == "/api/remote/command":
                result = REMOTE.command(str(payload["action"]), payload.get("value"))
                return self._json(200, result)

            return self._json(404, {"error": "unknown API route"})
        except (KeyError, ValueError, TypeError, json.JSONDecodeError, MeasurementError, ControlError, RemoteCommandError) as exc:
            return self._json(400, {"error": str(exc)})
        except Exception:
            return self._json(500, {"error": "internal server error"})


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Digital Power Engineering Workbench: http://{host}:{port}")
    ThreadingHTTPServer((host, port), WorkbenchHandler).serve_forever()
